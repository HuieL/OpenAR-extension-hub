#!/usr/bin/env python3
"""Negative self-tests: each mutation of a valid entry must be rejected.

Not run by CI; run locally (python3 scripts/selftest-negative.py) before
changing scripts/validate.py. Each case mutates one fact of a known-good
entry and asserts the validator records at least one error for it.
"""

import copy
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("validate", HERE / "validate.py")
validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)

HEX64 = "a" * 64
SHA40 = "0" * 40


def base_entry() -> dict:
    return {
        "schemaVersion": 1,
        "id": "example.mcp-local",
        "kind": "extension",
        "name": "Echo MCP",
        "summary": "Local stdio echo MCP fixture.",
        "authors": [{"name": "Example Author", "github": "example-author"}],
        "source": {
            "repo": "https://github.com/example/echo-mcp",
            "path": ".",
            "revision": SHA40,
        },
        "version": "0.1.0",
        "license": "Apache-2.0",
        "review": {"status": "unreviewed"},
        "compat": {
            "minHost": "0.3.0",
            "hostApi": {"min": 1, "max": 2},
            "platforms": ["macos", "linux"],
        },
        "delivery": "mcp-local",
        "integration": "L1",
        "bindings": [
            {"kind": "mcp", "tool": "echo", "inputSchemaDigest": HEX64}
        ],
        "assets": [
            {
                "platform": "macos-arm64",
                "url": "https://github.com/example/echo-mcp/releases/download/v0.1.0/echo-macos.tar.gz",
                "sha256": "b" * 64,
                "bytes": 1024,
            }
        ],
        "mcp": {
            "transport": "stdio",
            "command": ["bin/echo-server", "--port", "8080"],
            "version": "0.1.0",
            "env": [],
        },
    }


def run_checks(entry: dict) -> list[str]:
    validate.errors = []
    if validate.check_common(entry, entry.get("id", "?")):
        validate.check_source(entry, entry["id"])
        validate.check_review(entry, entry["id"])
        validate.check_compat(entry, entry["id"])
        validate.check_declaration(entry, entry["id"])
        validate.check_bindings(entry, entry["id"])
        validate.check_assets(entry, entry["id"])
        validate.check_mcp(entry, entry["id"])
    return list(validate.errors)


CASES = []


def case(name):
    def register(fn):
        CASES.append((name, fn))
        return fn
    return register


@case("shell metacharacter in command word")
def _(e):
    e["mcp"]["command"] = ["bin/echo-server", "--port; rm -rf /"]


@case("absolute path as command[0]")
def _(e):
    e["mcp"]["command"] = ["/usr/bin/env", "python"]


@case("host binary (no slash) as command[0]")
def _(e):
    e["mcp"]["command"] = ["python", "server.py"]


@case("parent-directory component in command")
def _(e):
    e["mcp"]["command"] = ["../escape/server"]


@case("pipe in command argument")
def _(e):
    e["mcp"]["command"] = ["bin/echo-server", "8080|sh"]


@case("mcp binding missing inputSchemaDigest")
def _(e):
    del e["bindings"][0]["inputSchemaDigest"]


@case("asset url with userinfo credentials")
def _(e):
    e["assets"][0]["url"] = "https://token:secret@github.com/example/echo-mcp/echo.tar.gz"


@case("asset url on a private-network host")
def _(e):
    e["assets"][0]["url"] = "https://10.0.0.1/echo.tar.gz"


@case("mutable revision instead of commit SHA")
def _(e):
    e["source"]["revision"] = "main"


@case("bundled delivery (built-ins are not listed)")
def _(e):
    e["delivery"] = "bundled"


@case("uppercase id")
def _(e):
    e["id"] = "Example.Mcp-Local"


@case("unpinned cli binding version")
def _(e):
    e["bindings"] = [
        {"kind": "cli", "adapter": "ripgrep", "version": "latest", "hash": HEX64}
    ]


@case("mcp spec on a package delivery")
def _(e):
    e["delivery"] = "package"


@case("reviewed status without reviewedRevision")
def _(e):
    e["review"] = {"status": "reviewed"}


@case("missing authors")
def _(e):
    del e["authors"]


@case("empty authors list")
def _(e):
    e["authors"] = []


@case("env name outside the [A-Za-z0-9_] charset")
def _(e):
    e["mcp"]["env"] = [{"name": "API-KEY", "credentialRef": "echo/api-key"}]


@case("duplicate env names")
def _(e):
    e["mcp"]["env"] = [
        {"name": "API_KEY", "credentialRef": "echo/api-key"},
        {"name": "API_KEY", "credentialRef": "echo/other"},
    ]


@case("registrySubmitter with an @ prefix")
def _(e):
    e["registrySubmitter"] = "@example-author"


@case("inline = value in a command word")
def _(e):
    e["mcp"]["command"] = ["bin/echo-server", "--token=sk-live-123"]


@case("asset url on an alibaba metadata host")
def _(e):
    e["assets"][0]["url"] = "https://100.100.100.200/latest/meta-data/echo.tar.gz"


@case("asset url on an aws ipv6 metadata host")
def _(e):
    e["assets"][0]["url"] = "https://[fd00:ec2::254]/latest/meta-data/echo.tar.gz"


@case("asset url on a single-label domain")
def _(e):
    e["assets"][0]["url"] = "https://intranet/echo.tar.gz"


@case("cli binding adapter outside the identifier charset")
def _(e):
    e["bindings"] = [
        {"kind": "cli", "adapter": "ripgrep adapter", "version": "14.1.0", "hash": HEX64}
    ]


@case("mcp binding tool outside the plain-word charset")
def _(e):
    e["bindings"] = [
        {"kind": "mcp", "tool": "echo tool", "inputSchemaDigest": HEX64}
    ]


@case("mcp-local version outside the plain-word charset")
def _(e):
    e["mcp"]["version"] = "0.1.0 (nightly)"


def main() -> None:
    # The unmutated fixture must pass every check.
    clean = run_checks(base_entry())
    if clean:
        print("FAIL: base entry does not validate cleanly:")
        print("\n".join(clean))
        sys.exit(1)

    # The runtime definition-id grammar allows underscores in segments.
    underscored = base_entry()
    underscored["id"] = "example.mcp_echo"
    errors = run_checks(underscored)
    if errors:
        print("FAIL: underscore id segment must be accepted:")
        print("\n".join(errors))
        sys.exit(1)

    failures = 0
    for name, mutate in CASES:
        entry = base_entry()
        mutate(entry)
        errors = run_checks(entry)
        if errors:
            print(f"ok   {name} -> {errors[0]}")
        else:
            print(f"FAIL {name} -> accepted")
            failures += 1
    if failures:
        print(f"{failures} negative case(s) were accepted")
        sys.exit(1)
    print(f"OK: {len(CASES)} negative cases rejected, base entry clean")


if __name__ == "__main__":
    main()
