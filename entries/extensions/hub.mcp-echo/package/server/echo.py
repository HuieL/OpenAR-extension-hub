#!/usr/bin/env python3
"""Minimal MCP stdio echo server: one tool, "echo", which returns its input.

Speaks newline-delimited JSON-RPC 2.0 over stdin/stdout (initialize, ping,
tools/list, tools/call). Aborts when spoken to incorrectly.
"""
import json
import sys

PROTOCOL_VERSION = "2025-06-18"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
}


def send(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        method = request.get("method")
        if method == "initialize":
            send({
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mcp-echo", "version": "1.0.2"},
                },
            })
        elif method == "notifications/initialized":
            pass
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": request["id"], "result": {}})
        elif method == "tools/call":
            arguments = request.get("params", {}).get("arguments", {})
            if request.get("params", {}).get("name") != "echo":
                send({
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "error": {"code": -32602, "message": "unknown tool"},
                })
            elif arguments.get("text") == "boom":
                send({
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "content": [{"type": "text", "text": "tool exploded"}],
                        "isError": True,
                    },
                })
            else:
                send({
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(arguments)}],
                        "structuredContent": {"echo": arguments},
                    },
                })
        elif method == "tools/list":
            send({
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "tools": [{
                        "name": "echo",
                        "description": "Echo the input back.",
                        "inputSchema": INPUT_SCHEMA,
                        "outputSchema": OUTPUT_SCHEMA,
                    }]
                },
            })
        else:
            send({
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": "method not found"},
            })


if __name__ == "__main__":
    serve()
