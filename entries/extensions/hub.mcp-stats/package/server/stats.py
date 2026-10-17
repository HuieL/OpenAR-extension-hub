#!/usr/bin/env python3
"""Offline MCP stdio server for benchmark statistics (standard library only).

Three tools a researcher reaches for when comparing accuracies on a fixed
benchmark:

- accuracy_interval: Wilson score interval for one accuracy (k of n correct).
- compare_paired: exact McNemar test for two systems scored on the same
  items, from the discordant counts (A right/B wrong, A wrong/B right).
- items_needed: benchmark size per system to detect an accuracy gap with a
  two-sided two-proportion z-test at the given power.

No network, no files, no subprocesses. Speaks newline-delimited JSON-RPC 2.0
over stdin/stdout (initialize, ping, tools/list, tools/call).
"""
import json
import math
import sys
from statistics import NormalDist

PROTOCOL_VERSION = "2025-06-18"
VERSION = "1.0.0"
NORMAL = NormalDist()


def obj(properties, required):
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


NUM = {"type": "number"}
BOOL = {"type": "boolean"}
INT = {"type": "integer"}

TOOLS = {
    "accuracy_interval": {
        "description": "Wilson score confidence interval for an accuracy of `correct` out of `total` items.",
        "inputSchema": obj({
            "correct": {"type": "integer", "minimum": 0, "maximum": 100000000},
            "total": {"type": "integer", "minimum": 1, "maximum": 100000000},
            "confidence": {"type": "number", "minimum": 0.5, "maximum": 0.999},
        }, ["correct", "total"]),
        "outputSchema": obj({"accuracy": NUM, "lower": NUM, "upper": NUM, "confidence": NUM}, ["accuracy", "lower", "upper", "confidence"]),
    },
    "compare_paired": {
        "description": "Exact McNemar test for two systems on the same items. Pass the discordant counts: "
                       "items only A got right, and items only B got right.",
        "inputSchema": obj({
            "only_a_correct": {"type": "integer", "minimum": 0, "maximum": 1000000},
            "only_b_correct": {"type": "integer", "minimum": 0, "maximum": 1000000},
            "alpha": {"type": "number", "minimum": 0.0001, "maximum": 0.5},
        }, ["only_a_correct", "only_b_correct"]),
        "outputSchema": obj({"discordant": INT, "p_value": NUM, "significant": BOOL, "alpha": NUM},
                            ["discordant", "p_value", "significant", "alpha"]),
    },
    "items_needed": {
        "description": "Items per system needed to detect an accuracy `gap` (e.g. 0.05) around a baseline "
                       "`accuracy`, two-sided two-proportion z-test.",
        "inputSchema": obj({
            "accuracy": {"type": "number", "minimum": 0.01, "maximum": 0.99},
            "gap": {"type": "number", "minimum": 0.001, "maximum": 0.98},
            "power": {"type": "number", "minimum": 0.5, "maximum": 0.99},
            "alpha": {"type": "number", "minimum": 0.0001, "maximum": 0.5},
        }, ["accuracy", "gap"]),
        "outputSchema": obj({"items_per_system": INT, "power": NUM, "alpha": NUM}, ["items_per_system", "power", "alpha"]),
    },
}


class InputError(ValueError):
    pass


def wilson(correct, total, confidence=0.95):
    if correct > total:
        raise InputError("correct cannot exceed total")
    z = NORMAL.inv_cdf(0.5 + confidence / 2)
    p = correct / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return {"accuracy": p, "lower": max(0.0, centre - half), "upper": min(1.0, centre + half), "confidence": confidence}


EXACT_LIMIT = 2000


def binomial_lower_tail(n, k):
    """P(X <= k) for X ~ Binomial(n, 1/2), k <= n / 2.

    Exact integer arithmetic for small n. Above EXACT_LIMIT the terms are
    summed relative to the largest one, C(n, k) / 2^n (taken from lgamma),
    walking down with C(n, i-1) = C(n, i) * i / (n - i + 1) and stopping once
    a term no longer changes the sum: a few thousand steps at the input bound.
    """
    if n <= EXACT_LIMIT:
        return sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    log_peak = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) - n * math.log(2)
    term, total = 1.0, 1.0
    for i in range(k, 0, -1):
        term *= i / (n - i + 1)
        total += term
        if term < total * 1e-17:
            break
    return math.exp(log_peak + math.log(total))


def mcnemar_exact(only_a, only_b, alpha=0.05):
    n = only_a + only_b
    if n == 0:
        return {"discordant": 0, "p_value": 1.0, "significant": False, "alpha": alpha}
    # Two-sided exact binomial test with p = 1/2: 2 * P(X <= min), capped at 1.
    p_value = min(1.0, 2 * binomial_lower_tail(n, min(only_a, only_b)))
    return {"discordant": n, "p_value": p_value, "significant": p_value < alpha, "alpha": alpha}


def items_needed(accuracy, gap, power=0.8, alpha=0.05):
    p1 = accuracy
    p2 = accuracy + gap
    if p2 >= 1:
        p2 = accuracy - gap
    if p2 <= 0:
        raise InputError("accuracy ± gap must stay inside (0, 1)")
    za = NORMAL.inv_cdf(1 - alpha / 2)
    zb = NORMAL.inv_cdf(power)
    pbar = (p1 + p2) / 2
    n = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p1 - p2) ** 2
    return {"items_per_system": math.ceil(n), "power": power, "alpha": alpha}


def check(arguments, schema):
    """The host validates input against the same schema; refuse anything off-shape here too."""
    if not isinstance(arguments, dict) or set(arguments) - set(schema["properties"]):
        raise InputError("unexpected arguments")
    for name in schema["required"]:
        if name not in arguments:
            raise InputError(f"missing {name}")
    for name, value in arguments.items():
        field = schema["properties"][name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InputError(f"{name} must be a number")
        if field["type"] == "integer" and not float(value).is_integer():
            raise InputError(f"{name} must be an integer")
        if not field["minimum"] <= value <= field["maximum"]:
            raise InputError(f"{name} is out of range")
    return arguments


def call(name, arguments):
    a = check(arguments, TOOLS[name]["inputSchema"])
    if name == "accuracy_interval":
        return wilson(int(a["correct"]), int(a["total"]), a.get("confidence", 0.95))
    if name == "compare_paired":
        return mcnemar_exact(int(a["only_a_correct"]), int(a["only_b_correct"]), a.get("alpha", 0.05))
    return items_needed(a["accuracy"], a["gap"], a.get("power", 0.8), a.get("alpha", 0.05))


def send(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def reply(request, result=None, error=None):
    message = {"jsonrpc": "2.0", "id": request.get("id")}
    message["error" if error else "result"] = error or result
    send(message)


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        if not isinstance(request, dict) or not isinstance(request.get("method"), str):
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}})
            continue
        method = request["method"]
        params = request.get("params", {})
        if not isinstance(params, dict):
            if "id" in request:
                reply(request, error={"code": -32602, "message": "params must be an object"})
            continue
        if method == "initialize":
            reply(request, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mcp-stats", "version": VERSION},
            })
        elif method == "notifications/initialized":
            pass
        elif method == "ping":
            reply(request, {})
        elif method == "tools/list":
            reply(request, {"tools": [{"name": name, **tool} for name, tool in TOOLS.items()]})
        elif method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str) or name not in TOOLS:
                reply(request, error={"code": -32602, "message": "unknown tool"})
                continue
            arguments = params.get("arguments", {})
            if not isinstance(arguments, dict):
                reply(request, error={"code": -32602, "message": "arguments must be an object"})
                continue
            try:
                result = call(name, arguments)
            except InputError as problem:
                reply(request, {"content": [{"type": "text", "text": str(problem)}], "isError": True})
                continue
            reply(request, {"content": [{"type": "text", "text": json.dumps(result)}], "structuredContent": result})
        elif "id" in request:
            reply(request, error={"code": -32601, "message": "method not found"})


if __name__ == "__main__":
    serve()
