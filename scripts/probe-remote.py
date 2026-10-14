#!/usr/bin/env python3
"""Re-probe every mcp-remote entry and report drift from its `observed` block.

An mcp-remote entry records what this hub's own live probe saw (tools,
resources, server version). Services change; CONTRIBUTING says a drifted
observation is updated or deprecated, never quietly rewritten. This script
is the check: it performs the same anonymous handshake a reviewer did
(streamable HTTP: initialize -> notifications/initialized -> tools/list ->
resources/list, following nextCursor) and compares.

It only reads. No credentials are used, sent or logged; an entry whose
service requires auth is reported as such, not probed with secrets.

Exit status: 0 when every probed entry matches, 1 on drift or an
unreachable service, 2 on usage errors. `--json` prints the report.
"""

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROTOCOL = "2025-06-18"
TIMEOUT = 30
MAX_BYTES = 4 * 1024 * 1024
MAX_PAGES = 20


class ProbeError(Exception):
    pass


def post(endpoint, payload, session=None):
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": PROTOCOL,
        "user-agent": "openar-extension-hub-probe",
    }
    if session:
        headers["mcp-session-id"] = session
    request = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ProbeError("response exceeds the size cap")
            return response.headers.get("mcp-session-id"), response.headers.get_content_type(), body
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise ProbeError(f"HTTP {error.code}: the service requires auth") from None
        raise ProbeError(f"HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ProbeError(f"unreachable: {error}") from None


def decode(content_type, body, request_id):
    """A JSON-RPC result from a JSON body or an SSE stream."""
    text = body.decode("utf-8", errors="replace")
    messages = []
    if content_type == "text/event-stream":
        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    messages.append(json.loads(line[5:].strip()))
                except json.JSONDecodeError:
                    continue
    else:
        try:
            messages.append(json.loads(text))
        except json.JSONDecodeError:
            raise ProbeError("response is not JSON") from None
    for message in messages:
        if isinstance(message, dict) and message.get("id") == request_id:
            if "error" in message:
                raise ProbeError(f"JSON-RPC error: {message['error'].get('message', '?')}")
            return message.get("result") or {}
    raise ProbeError(f"no response to request {request_id}")


def listed(endpoint, session, method, key, field, start_id):
    names, cursor, request_id = [], None, start_id
    for _ in range(MAX_PAGES):
        params = {"cursor": cursor} if cursor else {}
        _, content_type, body = post(
            endpoint, {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}, session
        )
        result = decode(content_type, body, request_id)
        names += [item.get(field) for item in result.get(key, []) if isinstance(item, dict)]
        cursor = result.get("nextCursor")
        request_id += 1
        if not cursor:
            return names, request_id
    raise ProbeError(f"{method} did not finish within {MAX_PAGES} pages")


def probe(endpoint):
    session, content_type, body = post(endpoint, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                   "clientInfo": {"name": "openar-extension-hub-probe", "version": "1"}},
    })
    result = decode(content_type, body, 1)
    server_version = (result.get("serverInfo") or {}).get("version")
    capabilities = result.get("capabilities") or {}
    post(endpoint, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    tools, next_id = listed(endpoint, session, "tools/list", "tools", "name", 2) if "tools" in capabilities else ([], 2)
    resources = []
    if "resources" in capabilities:
        resources, _ = listed(endpoint, session, "resources/list", "resources", "uri", next_id)
    return {"tools": tools, "resources": resources, "serverVersion": server_version}


def compare(entry, seen):
    observed = entry["mcp"]["observed"]
    drift = []
    want_tools, got_tools = set(observed.get("tools", [])), set(seen["tools"])
    if want_tools != got_tools:
        drift.append({"field": "tools", "added": sorted(got_tools - want_tools),
                      "removed": sorted(want_tools - got_tools)})
    # An entry may record a documented subset of resources (e.g. one entry
    # point per skill, under the 64 cap); every recorded one must still exist.
    missing = sorted(set(observed.get("resources", [])) - set(seen["resources"]))
    if missing:
        drift.append({"field": "resources", "removed": missing})
    if observed.get("serverVersion") and seen["serverVersion"] != observed["serverVersion"]:
        drift.append({"field": "serverVersion", "observed": observed["serverVersion"],
                      "now": seen["serverVersion"]})
    return drift


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ids", nargs="*", help="limit to these entry ids")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args()
    entries = []
    for path in sorted((ROOT / "entries" / "extensions").glob("*/entry.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry.get("delivery") == "mcp-remote" and (not args.ids or entry["id"] in args.ids):
            entries.append(entry)
    if args.ids and len(entries) != len(set(args.ids)):
        print("unknown or non-remote entry id", file=sys.stderr)
        return 2
    report, failed = [], False
    for entry in entries:
        row = {"id": entry["id"], "endpoint": entry["mcp"]["endpoint"]}
        if entry["mcp"].get("authRequirements"):
            row["status"] = "skipped: requires auth"
        else:
            try:
                row["drift"] = compare(entry, probe(entry["mcp"]["endpoint"]))
                row["status"] = "drift" if row["drift"] else "ok"
            except ProbeError as error:
                row["status"] = f"error: {error}"
        failed |= row["status"] != "ok" and not row["status"].startswith("skipped")
        report.append(row)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for row in report:
            print(f"{row['status']:<8} {row['id']}")
            for item in row.get("drift", []):
                print(f"         {json.dumps(item)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
