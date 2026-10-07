"""Command-line access to all Aseprite MCP tools.

Every tool registered on the MCP server is exposed as a subcommand, so the
CLI stays in sync with the server automatically:

    asp                          list all commands (one line each)
    asp <command> --help         show parameters of a command
    asp <command> --param value  run a command
    asp <command> --json '{...}' run a command with JSON arguments
"""

import asyncio
import difflib
import json
import os
import sys
from collections import defaultdict

from . import mcp
from .tools import *  # noqa: F401,F403  registers all tools on `mcp`

MAC_ASEPRITE = "/Applications/Aseprite.app/Contents/MacOS/aseprite"
FAILURE_PREFIXES = ("Failed", "ERROR", "Error", "Invalid", "Script failed")


def _tools():
    return {t.name: t for t in mcp._tool_manager.list_tools()}


def _summary(tool):
    return (tool.description or "").strip().split("\n")[0]


def _type_name(schema):
    if "anyOf" in schema:
        types = [_type_name(s) for s in schema["anyOf"] if s.get("type") != "null"]
        return "|".join(types) + " (optional)"
    t = schema.get("type", "any")
    if t == "array":
        return f"json-array of {schema.get('items', {}).get('type', 'any')}"
    if t == "object":
        return "json-object"
    return t


def _accepts(schema, kind):
    if schema.get("type") == kind:
        return True
    return any(s.get("type") == kind for s in schema.get("anyOf", []))


def _convert(name, raw, schema):
    if raw == "null" and "anyOf" in schema:
        return None
    if _accepts(schema, "array") or _accepts(schema, "object"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"--{name} expects JSON, got {raw!r} ({e})")
    if _accepts(schema, "boolean"):
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise ValueError(f"--{name} expects true/false, got {raw!r}")
    if _accepts(schema, "integer"):
        return int(raw)
    if _accepts(schema, "number"):
        return float(raw)
    return raw


def print_overview():
    groups = defaultdict(list)
    for tool in _tools().values():
        groups[tool.fn.__module__.rsplit(".", 1)[-1]].append(tool)
    print("Usage: asp <command> [--param value ...]   |   asp <command> --help\n")
    for group in sorted(groups):
        print(f"[{group}]")
        for tool in sorted(groups[group], key=lambda t: t.name):
            print(f"  {tool.name:<28} {_summary(tool)}")
        print()


def print_command_help(tool):
    props = tool.parameters.get("properties", {})
    required = set(tool.parameters.get("required", []))
    print(f"asp {tool.name}\n")
    print((tool.description or "").strip())
    print("\nParameters:")
    for name, schema in props.items():
        if name in required:
            flag = "required"
        else:
            flag = f"default: {json.dumps(schema.get('default'))}"
        print(f"  --{name:<22} {_type_name(schema):<26} {flag}")
    print("\nBooleans: --flag (true), --no-flag (false) or --flag true/false.")
    print("Arrays/objects: pass JSON, e.g. --pixels '[{\"x\":0,\"y\":0,\"color\":\"#ff0000\"}]'")


def parse_args(tool, argv):
    props = tool.parameters.get("properties", {})
    args = {}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--json":
            args.update(json.loads(argv[i + 1]))
            i += 2
            continue
        if not token.startswith("--"):
            raise ValueError(f"Unexpected argument {token!r}; use --name value")
        key, _, inline = token[2:].partition("=")
        key = key.replace("-", "_")
        negate = key.startswith("no_") and key[3:] in props and key not in props
        if negate:
            key = key[3:]
        if key not in props:
            raise ValueError(f"Unknown parameter --{key} (see: asp {tool.name} --help)")
        schema = props[key]
        if negate:
            args[key] = False
            i += 1
        elif inline:
            args[key] = _convert(key, inline, schema)
            i += 1
        elif _accepts(schema, "boolean") and (
            i + 1 >= len(argv) or argv[i + 1].startswith("--")
        ):
            args[key] = True
            i += 1
        else:
            if i + 1 >= len(argv):
                raise ValueError(f"--{key} needs a value")
            args[key] = _convert(key, argv[i + 1], schema)
            i += 2
    missing = [n for n in tool.parameters.get("required", []) if n not in args]
    if missing:
        raise ValueError(
            "Missing required: " + ", ".join(f"--{m}" for m in missing)
            + f" (see: asp {tool.name} --help)"
        )
    return args


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not os.getenv("ASEPRITE_PATH") and os.path.exists(MAC_ASEPRITE):
        os.environ["ASEPRITE_PATH"] = MAC_ASEPRITE

    if not argv or argv[0] in ("-h", "--help", "help"):
        print_overview()
        return 0

    tools = _tools()
    name = argv[0].replace("-", "_")
    if name not in tools:
        close = difflib.get_close_matches(name, tools, n=5, cutoff=0.6)
        close += [t for t in tools if name in t and t not in close]
        hint = f" Did you mean: {', '.join(close[:5])}?" if close else ""
        print(f"Unknown command {argv[0]!r}.{hint} Run 'asp' for the list.", file=sys.stderr)
        return 2
    tool = tools[name]

    if any(a in ("-h", "--help") for a in argv[1:]):
        print_command_help(tool)
        return 0

    try:
        args = parse_args(tool, argv[1:])
        result = asyncio.run(tool.run(args))
    except Exception as e:  # report every failure as a short message for the LLM
        print(f"Error: {e}", file=sys.stderr)
        return 1
    text = result if isinstance(result, str) else json.dumps(result, indent=2, default=str)
    # Tools report failures as plain strings; turn them into a non-zero exit.
    if text.startswith(FAILURE_PREFIXES) or (text.startswith("File ") and text.endswith("not found")):
        print(f"Error: {text}", file=sys.stderr)
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
