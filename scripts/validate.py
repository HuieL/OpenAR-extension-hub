#!/usr/bin/env python3
"""Validate the registry: entry.json contract, extensions.json consistency.

Mirrors the OpenRA wire contract documented as
docs/extension-hub-entry-format.md in the OpenRA repository: the hub must
accept exactly what the OpenRA validator accepts. Aligned with the runtime
contract: HTTPS URLs reject userinfo, loopback/private/link-local and cloud
metadata hosts (169.254.0.0/16, 100.100.100.200, fd00:ec2::/32) and
single-label domains; mcp-local command words carry the runtime argv charset
(1-32 words, entry word names a path inside the package tree) and never an
inline = value; ids use the runtime definition-id grammar (underscore
allowed); cli adapter/version and mcp tool/version use the runtime
identifier and plain-word charsets; env references use the runtime field
name and bounds; entries carry the shared credit fields (authors required;
maintainers, contributors, adapters, registrySubmitter, categories). Zero
dependencies beyond the Python standard library; CI runs exactly this script
with no secrets and no install step.
"""

import ipaddress
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "entries" / "extensions"
MAX_INDEX_BYTES = 512 * 1024
MAX_ENTRY_BYTES = 256 * 1024
MAX_ASSET_BYTES = 512 * 1024 * 1024
LOCALES = {"en", "zh-CN", "ja", "ko", "es"}
REVIEW_STATUSES = {"unreviewed", "reviewed", "deprecated", "high-risk"}
DELIVERIES = {"package", "mcp-local", "mcp-remote", "cli"}
INSTALLABLE = {"package", "mcp-local", "cli"}
INTEGRATIONS = {"L0", "L1", "L2", "L3"}
UI_CONTRIBUTIONS = {"main-page", "right-panel", "commands", "preview"}
PLATFORMS = {"macos", "linux", "windows"}
BINDING_KINDS = {"builtin", "cli", "mcp"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
# Runtime definition-id grammar: dot-separated segments of [a-z0-9_-],
# no uppercase, each at most 64 chars, at least two segments.
NAMESPACED_ID = re.compile(r"^[a-z0-9_-]+(\.[a-z0-9_-]+)+$")
# Runtime argv-word charset: shell-free,
# no absolute paths, no parent-directory components.
ARGV_WORD = re.compile(r"^[A-Za-z0-9_./=:-]+$")
# Runtime identifier (cli adapter/version): [A-Za-z0-9_-], at most 64.
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# Runtime plain word (tool names, server versions): no separators that
# could smuggle a path or shell syntax.
PLAIN_WORD = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


def argv_word(value) -> bool:
    if not isinstance(value, str) or not value or len(value) > 128:
        return False
    if not ARGV_WORD.match(value):
        return False
    if value.startswith("/"):
        return False
    return all(part not in ("", "..") for part in value.split("/"))

# Cloud metadata ranges the runtime harness refuses (169.254.0.0/16,
# 100.100.100.200, fd00:ec2::/32), kept in step with harness/mcp.rs.
METADATA_V4_NETWORKS = [ipaddress.ip_network("169.254.0.0/16")]
METADATA_V4_HOSTS = [ipaddress.ip_address("100.100.100.200")]
METADATA_V6_NETWORKS = [ipaddress.ip_network("fd00:ec2::/32")]

GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9-]{1,39}$")
ENV_NAME = re.compile(r"^[A-Za-z0-9_]+$")

ENTRY_FIELDS = {
    "schemaVersion", "id", "kind", "name", "summary", "authors", "i18n",
    "source", "version", "license", "licenseFile", "review", "compat",
    "delivery", "integration", "capabilities", "uiContributions", "bindings",
    "auth", "artifacts", "dependencies", "assets", "mcp", "maintainers",
    "contributors", "adapters", "registrySubmitter", "categories",
}
INDEX_ENTRY_FIELDS = {
    "id", "name", "summary", "delivery", "integration", "version",
    "revision", "entryPath", "entrySha256",
}

errors: list[str] = []


def fail(entry_id: str, message: str) -> None:
    errors.append(f"{entry_id}: {message}")


def bounded(value, max_len: int) -> bool:
    return isinstance(value, str) and value != "" and len(value) <= max_len


def namespaced_id(value) -> bool:
    return (isinstance(value, str) and len(value) <= 128
            and bool(NAMESPACED_ID.match(value))
            and all(len(segment) <= 64 for segment in value.split(".")))


def safe_rel_path(raw) -> bool:
    if raw == ".":
        return True
    if not isinstance(raw, str) or not raw or raw.startswith("/") or "\\" in raw:
        return False
    parts = raw.split("/")
    return all(part not in ("", ".", "..") for part in parts)


def https_url(value) -> bool:
    if not bounded(value, 2048) or not value.startswith("https://"):
        return False
    if any(c.isspace() or ord(c) < 0x20 for c in value):
        return False
    rest = value[len("https://"):]
    host = rest.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if "@" in host:  # userinfo never rides a catalog URL
        return False
    if host.startswith("[") and host.endswith("]"):  # IPv6 literal
        host_name = host[1:-1]
    else:
        host_name = host.split(":", 1)[0].lower()
    try:
        address = ipaddress.ip_address(host_name)
    except ValueError:
        # Domain: public names have a dot and no local/internal suffix.
        return "." in host_name and not host_name.endswith((".local", ".internal"))
    if address.version == 4:
        return not (address.is_private or address.is_loopback
                    or address.is_link_local or address.is_unspecified
                    or any(address in net for net in METADATA_V4_NETWORKS)
                    or address in METADATA_V4_HOSTS)
    return not (address.is_loopback or address.is_unspecified
                or any(address in net for net in METADATA_V6_NETWORKS))


def observed_at_timestamp(value) -> bool:
    if not isinstance(value, str) or len(value) < 11:
        return False
    date, sep, time_part = value.partition("T")
    if not sep or not time_part:
        return False
    if len(date) != 10:
        return False
    for index, ch in enumerate(date):
        if index in (4, 7):
            if ch != "-":
                return False
        elif not ch.isdigit():
            return False
    return True


def check_common(entry: dict, entry_id: str) -> bool:
    unknown = set(entry) - ENTRY_FIELDS
    if unknown:
        fail(entry_id, f"unknown fields: {sorted(unknown)}")
    missing = {
        "schemaVersion", "id", "kind", "name", "summary", "authors", "source",
        "version", "license", "review", "compat", "delivery", "integration",
    } - set(entry)
    if missing:
        fail(entry_id, f"missing fields: {sorted(missing)}")
        return False
    if entry["schemaVersion"] != 1:
        fail(entry_id, "schemaVersion must be 1")
    if entry["kind"] != "extension":
        fail(entry_id, "kind must be 'extension'")
    if not namespaced_id(entry["id"]) or entry["id"] != entry_id:
        fail(entry_id, "id must be lowercase namespaced (>=2 dot segments) and equal the directory name")
    if not bounded(entry["name"], 64):
        fail(entry_id, "name must be a non-empty string of at most 64 chars")
    if not bounded(entry["summary"], 512):
        fail(entry_id, "summary must be a non-empty string of at most 512 chars")
    authors = entry.get("authors")
    if not isinstance(authors, list) or not authors:
        fail(entry_id, "authors must name at least the original creator(s)")
    else:
        for author in authors:
            if (not isinstance(author, dict) or set(author) - {"name", "github"}
                    or not bounded(author.get("name"), 64)):
                fail(entry_id, "each author has a name (at most 64 chars) and an optional github login")
            elif "github" in author and author["github"] is not None and not (
                    isinstance(author["github"], str) and GITHUB_LOGIN.match(author["github"])):
                fail(entry_id, "author github must be a login without '@'")
    for field in ("maintainers", "contributors", "adapters"):
        logins = entry.get(field, [])
        if not isinstance(logins, list) or any(
                not isinstance(login, str) or not GITHUB_LOGIN.match(login) for login in logins):
            fail(entry_id, f"{field} are github logins without '@'")
    submitter = entry.get("registrySubmitter")
    if submitter is not None and not (isinstance(submitter, str) and GITHUB_LOGIN.match(submitter)):
        fail(entry_id, "registrySubmitter must be a github login without '@'")
    categories = entry.get("categories", [])
    if not isinstance(categories, list) or any(
            not isinstance(category, str) or not 0 < len(category) <= 32 for category in categories):
        fail(entry_id, "categories are coarse tags of at most 32 chars")
    if "i18n" in entry:
        i18n = entry["i18n"]
        if not isinstance(i18n, dict) or set(i18n) - LOCALES or len(i18n) > len(LOCALES):
            fail(entry_id, "i18n keys must be a subset of " + ", ".join(sorted(LOCALES)))
        elif any(not bounded(v, 512) for v in i18n.values()):
            fail(entry_id, "i18n values must be non-empty strings of at most 512 chars")
    if not bounded(entry["version"], 64):
        fail(entry_id, "version must be a non-empty string of at most 64 chars")
    if not bounded(entry["license"], 128):
        fail(entry_id, "license (SPDX) is required, at most 128 chars")
    if "licenseFile" in entry and not safe_rel_path(entry["licenseFile"]):
        fail(entry_id, "licenseFile must be a safe relative path")
    return True


def check_source(entry: dict, entry_id: str) -> None:
    source = entry["source"]
    if not isinstance(source, dict) or set(source) != {"repo", "path", "revision"}:
        fail(entry_id, "source must have exactly repo, path, revision")
        return
    if not https_url(source["repo"]):
        fail(entry_id, "source.repo must be a public HTTPS URL (no userinfo, no loopback/private hosts)")
    if not safe_rel_path(source["path"]):
        fail(entry_id, "source.path must be '.' or a safe relative path")
    if not isinstance(source["revision"], str) or not HEX40.match(source["revision"]):
        fail(entry_id, "source.revision must be a 40-hex commit SHA (no main/latest/tags)")


def check_review(entry: dict, entry_id: str) -> None:
    review = entry["review"]
    if not isinstance(review, dict) or set(review) - {"status", "reviewedRevision", "reviewer"}:
        fail(entry_id, "review may only have status, reviewedRevision, reviewer")
        return
    if review.get("status") not in REVIEW_STATUSES:
        fail(entry_id, "review.status must be one of " + ", ".join(sorted(REVIEW_STATUSES)))
    if review.get("status") == "reviewed":
        revision = review.get("reviewedRevision")
        if not isinstance(revision, str) or not HEX40.match(revision):
            fail(entry_id, "review.status 'reviewed' requires a 40-hex reviewedRevision")
    reviewer = review.get("reviewer")
    if reviewer is not None and not bounded(reviewer, 128):
        fail(entry_id, "review.reviewer must be a non-empty string of at most 128 chars or null")


def check_compat(entry: dict, entry_id: str) -> None:
    compat = entry["compat"]
    if not isinstance(compat, dict) or set(compat) != {"minHost", "hostApi", "platforms"}:
        fail(entry_id, "compat must have exactly minHost, hostApi, platforms")
        return
    if not bounded(compat["minHost"], 32):
        fail(entry_id, "compat.minHost must be a non-empty string of at most 32 chars")
    host_api = compat["hostApi"]
    if isinstance(host_api, int) and not isinstance(host_api, bool):
        if host_api < 1:
            fail(entry_id, "compat.hostApi exact version must be >= 1")
    elif isinstance(host_api, dict):
        if set(host_api) != {"min", "max"}:
            fail(entry_id, "compat.hostApi range must have exactly min, max")
        elif not (isinstance(host_api["min"], int) and isinstance(host_api["max"], int)
                  and host_api["min"] >= 1 and host_api["min"] <= host_api["max"]):
            fail(entry_id, "compat.hostApi range must satisfy 1 <= min <= max")
    else:
        fail(entry_id, "compat.hostApi must be an exact number or a {min, max} range")
    platforms = compat["platforms"]
    if (not isinstance(platforms, list) or not platforms or len(platforms) > 3
            or len(set(platforms)) != len(platforms)
            or any(p not in PLATFORMS for p in platforms)):
        fail(entry_id, "compat.platforms must be a non-empty duplicate-free subset of macos/linux/windows")


def check_declaration(entry: dict, entry_id: str) -> None:
    if entry["delivery"] not in DELIVERIES:
        fail(entry_id, "delivery must be one of " + ", ".join(sorted(DELIVERIES)))
    if entry["integration"] not in INTEGRATIONS:
        fail(entry_id, "integration must be one of L0/L1/L2/L3")
    capabilities = entry.get("capabilities", [])
    if (not isinstance(capabilities, list) or len(capabilities) > 16
            or any(not bounded(c, 64) for c in capabilities)):
        fail(entry_id, "capabilities are display tags: at most 16, each at most 64 chars")
    ui = entry.get("uiContributions", [])
    if (not isinstance(ui, list) or len(ui) > 4 or len(set(ui)) != len(ui)
            or any(u not in UI_CONTRIBUTIONS for u in ui)):
        fail(entry_id, "uiContributions must be duplicate-free and drawn from " + ", ".join(sorted(UI_CONTRIBUTIONS)))
    auth = entry.get("auth", {})
    if not isinstance(auth, dict) or set(auth) - {"connections"}:
        fail(entry_id, "auth may only carry connections")
    else:
        connections = auth.get("connections", [])
        if (not isinstance(connections, list) or len(connections) > 8
                or any(not bounded(c, 64) for c in connections)):
            fail(entry_id, "auth.connections are connection type ids: at most 8, each at most 64 chars")
    artifacts = entry.get("artifacts", [])
    if not isinstance(artifacts, list) or len(artifacts) > 8 or any(not bounded(a, 64) for a in artifacts):
        fail(entry_id, "artifacts: at most 8 output types, each at most 64 chars")
    dependencies = entry.get("dependencies", [])
    if not isinstance(dependencies, list) or len(dependencies) > 8:
        fail(entry_id, "dependencies: at most 8, explicit; no dependency solving")
        return
    for dep in dependencies:
        if not isinstance(dep, dict) or set(dep) - {"id", "version", "optional"}:
            fail(entry_id, "each dependency has id, optional version, optional flag")
        elif not namespaced_id(dep.get("id")):
            fail(entry_id, f"dependency id {dep.get('id')!r} is not namespaced")
        elif "version" in dep and dep["version"] is not None and not bounded(dep["version"], 64):
            fail(entry_id, "dependency version must be a non-empty string of at most 64 chars")


def check_bindings(entry: dict, entry_id: str) -> None:
    bindings = entry.get("bindings", [])
    if not isinstance(bindings, list) or len(bindings) > 16:
        fail(entry_id, "bindings: at most 16 declarations")
        return
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get("kind") not in BINDING_KINDS:
            fail(entry_id, "binding kind must be builtin, cli or mcp (skill refs are dependencies)")
            continue
        kind = binding["kind"]
        if kind == "builtin":
            if set(binding) != {"kind", "id"} or not bounded(binding.get("id"), 128):
                fail(entry_id, "builtin binding carries exactly kind, id")
        elif kind == "cli":
            if set(binding) != {"kind", "adapter", "version", "hash"}:
                fail(entry_id, "cli binding carries exactly kind, adapter, version, hash")
            elif (not isinstance(binding.get("adapter"), str) or not IDENTIFIER.match(binding["adapter"])
                  or not isinstance(binding.get("version"), str) or not IDENTIFIER.match(binding["version"])
                  or binding.get("version") in ("active", "latest", "unpinned")
                  or not isinstance(binding.get("hash"), str) or not HEX64.match(binding["hash"])):
                fail(entry_id, "cli binding must pin adapter, version (identifiers, never active/latest/unpinned) and a sha256 hash")
        else:
            allowed = {"kind", "tool", "inputSchemaDigest", "outputSchemaDigest"}
            required = {"kind", "tool", "inputSchemaDigest"}
            if set(binding) - allowed or not required <= set(binding):
                fail(entry_id, "mcp binding carries kind, tool, inputSchemaDigest, optional outputSchemaDigest")
            elif (not isinstance(binding.get("tool"), str) or not PLAIN_WORD.match(binding["tool"])
                  or not isinstance(binding.get("inputSchemaDigest"), str)
                  or not HEX64.match(binding["inputSchemaDigest"])):
                fail(entry_id, "mcp binding tool (plain word) and inputSchemaDigest (64-hex) are required")
            elif "outputSchemaDigest" in binding and binding["outputSchemaDigest"] is not None:
                if not isinstance(binding["outputSchemaDigest"], str) or not HEX64.match(binding["outputSchemaDigest"]):
                    fail(entry_id, "mcp binding outputSchemaDigest must be 64-hex")


def check_assets(entry: dict, entry_id: str) -> None:
    assets = entry.get("assets", [])
    installable = entry.get("delivery") in INSTALLABLE
    if installable == (not assets):
        if installable:
            fail(entry_id, "installable deliveries (package/mcp-local/cli) require assets")
        else:
            fail(entry_id, "mcp-remote deliveries must not carry assets")
        return
    platforms = set()
    for asset in assets:
        if not isinstance(asset, dict) or set(asset) != {"platform", "url", "sha256", "bytes"}:
            fail(entry_id, "each asset has exactly platform, url, sha256, bytes")
            continue
        if (not bounded(asset["platform"], 32) or not https_url(asset["url"])
                or not isinstance(asset["sha256"], str) or not HEX64.match(asset["sha256"])
                or not isinstance(asset["bytes"], int) or isinstance(asset["bytes"], bool)
                or asset["bytes"] < 1 or asset["bytes"] > MAX_ASSET_BYTES):
            fail(entry_id, "asset must pin one public HTTPS artifact per platform with a sha256")
            continue
        if asset["platform"] in platforms:
            fail(entry_id, f"duplicate asset platform {asset['platform']!r}")
        platforms.add(asset["platform"])


def check_mcp(entry: dict, entry_id: str) -> None:
    delivery = entry.get("delivery")
    spec = entry.get("mcp")
    if delivery not in ("mcp-local", "mcp-remote"):
        if spec is not None:
            fail(entry_id, "only mcp deliveries may declare an mcp spec")
        return
    if not isinstance(spec, dict):
        fail(entry_id, "mcp deliveries must declare their matching mcp spec")
        return
    if delivery == "mcp-local":
        if set(spec) != {"transport", "command", "version", "env"}:
            fail(entry_id, "mcp-local spec has exactly transport, command, version, env")
            return
        if spec.get("transport") != "stdio":
            fail(entry_id, "mcp-local transport must be stdio")
        command = spec.get("command")
        if (not isinstance(command, list) or not command or len(command) > 32
                or any(not argv_word(word) for word in command)):
            fail(entry_id, "mcp-local command must be 1-32 argv words in the runtime charset (no shell metacharacters)")
            return
        if any("=" in word for word in command):
            fail(entry_id, "mcp-local command must not carry inline = values; configuration arrives by env reference")
            return
        if not safe_rel_path(command[0]) or "/" not in command[0]:
            fail(entry_id, "mcp-local command[0] must be a path inside the package tree, never a host binary or shell")
        if not isinstance(spec.get("version"), str) or not PLAIN_WORD.match(spec["version"]):
            fail(entry_id, "mcp-local version must be a plain word (at most 64 chars, no separators)")
        env_refs = spec.get("env", [])
        if not isinstance(env_refs, list) or len(env_refs) > 32:
            fail(entry_id, "mcp-local env carries at most 32 name-to-credential references")
            return
        names = set()
        for reference in env_refs:
            name = reference.get("name") if isinstance(reference, dict) else None
            if (not isinstance(reference, dict) or set(reference) != {"name", "credentialRef"}
                    or not isinstance(name, str) or not ENV_NAME.match(name) or len(name) > 64
                    or not argv_word(reference.get("credentialRef"))):
                fail(entry_id, "mcp-local env names are [A-Za-z0-9_] words and credentialRef an argv word, never a credential itself")
                break
            if name in names:
                fail(entry_id, f"mcp-local env name {name!r} declared twice")
                break
            names.add(name)
    else:
        if set(spec) != {"endpoint", "authRequirements", "observed"}:
            fail(entry_id, "mcp-remote spec has exactly endpoint, authRequirements, observed")
            return
        if not https_url(spec.get("endpoint")):
            fail(entry_id, "mcp-remote endpoint must be a public HTTPS URL")
        auth_reqs = spec.get("authRequirements", [])
        if not isinstance(auth_reqs, list) or len(auth_reqs) > 8 or any(not bounded(r, 64) for r in auth_reqs):
            fail(entry_id, "mcp-remote authRequirements: at most 8, each at most 64 chars")
        observed = spec.get("observed")
        if not isinstance(observed, dict) or set(observed) - {"tools", "resources", "observedAt", "serverVersion"}:
            fail(entry_id, "observed carries tools, resources, observedAt, optional serverVersion")
            return
        tools = observed.get("tools", [])
        resources = observed.get("resources", [])
        if (not isinstance(tools, list) or len(tools) > 64 or any(not bounded(t, 128) for t in tools)
                or not isinstance(resources, list) or len(resources) > 64
                or any(not bounded(r, 128) for r in resources)):
            fail(entry_id, "observed tools/resources: at most 64 each, names at most 128 chars")
        if not observed_at_timestamp(observed.get("observedAt")):
            fail(entry_id, "observed.observedAt must be an ISO-8601 date-time (observation, not a promise)")
        server_version = observed.get("serverVersion")
        if server_version is not None and not bounded(server_version, 64):
            fail(entry_id, "observed.serverVersion must be at most 64 chars")


def expected_entry_path(entry_id: str) -> str:
    return f"entries/extensions/{entry_id}/entry.json"


def validate_entries() -> dict:
    by_id = {}
    if not ENTRIES.is_dir():
        return by_id
    for entry_dir in sorted(ENTRIES.iterdir()):
        if not entry_dir.is_dir():
            fail(entry_dir.name, "entries/extensions must contain directories only")
            continue
        entry_path = entry_dir / "entry.json"
        if not entry_path.is_file():
            fail(entry_dir.name, "missing entry.json")
            continue
        if entry_path.stat().st_size > MAX_ENTRY_BYTES:
            fail(entry_dir.name, f"entry.json exceeds the {MAX_ENTRY_BYTES} byte cap")
            continue
        for real in entry_dir.rglob("*"):
            if real.is_symlink():
                fail(entry_dir.name, f"symlinks are not allowed: {real.relative_to(ROOT)}")
        try:
            entry = json.loads(entry_path.read_text())
        except json.JSONDecodeError as error:
            fail(entry_dir.name, f"entry.json is not valid JSON: {error}")
            continue
        if not isinstance(entry, dict):
            fail(entry_dir.name, "entry.json must be a JSON object")
            continue
        entry_id = entry.get("id") if isinstance(entry.get("id"), str) else entry_dir.name
        if not check_common(entry, entry_id):
            continue
        check_source(entry, entry_id)
        check_review(entry, entry_id)
        check_compat(entry, entry_id)
        check_declaration(entry, entry_id)
        check_bindings(entry, entry_id)
        check_assets(entry, entry_id)
        check_mcp(entry, entry_id)
        by_id[entry_id] = {
            "raw": entry_path.read_bytes(),
            "entry": entry,
        }
    return by_id


def validate_index(by_id: dict) -> None:
    index_path = ROOT / "extensions.json"
    if not index_path.is_file():
        fail("index", "extensions.json is missing")
        return
    if index_path.stat().st_size > MAX_INDEX_BYTES:
        fail("index", f"extensions.json exceeds the {MAX_INDEX_BYTES} byte cap")
        return
    try:
        index = json.loads(index_path.read_text())
    except json.JSONDecodeError as error:
        fail("index", f"extensions.json is not valid JSON: {error}")
        return
    if not isinstance(index, dict) or set(index) != {"schemaVersion", "entries"}:
        fail("index", "extensions.json must have exactly schemaVersion, entries")
        return
    if index["schemaVersion"] != 1:
        fail("index", "schemaVersion must be 1")
        return
    entries = index["entries"]
    if not isinstance(entries, list):
        fail("index", "entries must be a list")
        return
    ids = [row.get("id") for row in entries if isinstance(row, dict)]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        fail("index", "entries must be sorted by and unique in id")
    for row in entries:
        if not isinstance(row, dict) or set(row) != INDEX_ENTRY_FIELDS:
            fail("index", "each index row must have exactly " + ", ".join(sorted(INDEX_ENTRY_FIELDS)))
            continue
        entry_id = row["id"]
        found = by_id.get(entry_id)
        if found is None:
            fail("index", f"{entry_id} is in extensions.json but has no entry directory")
            continue
        import hashlib
        digest = hashlib.sha256(found["raw"]).hexdigest()
        entry = found["entry"]
        agrees = (
            row["id"] == entry["id"]
            and row["name"] == entry["name"]
            and row["summary"] == entry["summary"]
            and row["delivery"] == entry["delivery"]
            and row["integration"] == entry["integration"]
            and row["version"] == entry["version"]
            and row["revision"] == entry["source"]["revision"]
            and row["entryPath"] == expected_entry_path(entry["id"])
            and row["entrySha256"] == digest
        )
        if not agrees:
            fail("index", f"{entry_id} index row does not match its entry; run scripts/build-index.py")
    for entry_id in by_id:
        if entry_id not in ids:
            fail("index", f"{entry_id} has an entry directory but is missing from extensions.json")


def main() -> None:
    by_id = validate_entries()
    validate_index(by_id)
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print(f"OK: {len(by_id)} entries, index consistent")


if __name__ == "__main__":
    main()
