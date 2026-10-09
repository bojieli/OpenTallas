#!/usr/bin/env python3
"""Compile explicitly owned native descriptors; missing bindings fail closed.

This is a compiler mechanism, not an engine opcode registry. Owners supply
schemas and job bindings using their real endpoint and address contracts.
No schedule ordinal, measured latency or generic arg24 becomes an opcode.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(value, context):
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, dict) and set(value) == {"ref"}:
        key = value["ref"]
        if key not in context:
            raise ValueError(f"missing explicit context field {key}")
        return resolve(context[key], {})
    raise ValueError("field requires literal integer or explicit context reference")


def pack(schema, binding, context):
    width = schema["width"]
    if not isinstance(width, int) or width <= 0:
        raise ValueError("invalid native width")
    fields = schema["fields"]
    names = [f["name"] for f in fields]
    if len(names) != len(set(names)) or set(binding) != set(names):
        raise ValueError("binding must name every native field exactly once")
    occupied = 0
    word = 0
    for field in fields:
        name, low, size = field["name"], field["lsb"], field["width"]
        if low < 0 or size <= 0 or low + size > width:
            raise ValueError(f"field bounds {name}")
        mask = ((1 << size) - 1) << low
        if occupied & mask:
            raise ValueError(f"overlapping native field {name}")
        occupied |= mask
        value = resolve(binding[name], context)
        if not 0 <= value < (1 << size):
            raise ValueError(f"native field {name} out of range")
        if "allowed" in field and value not in field["allowed"]:
            raise ValueError(f"unowned opcode/encoding {name}={value}")
        word |= value << low
    if occupied != (1 << width) - 1:
        raise ValueError("native schema must explicitly cover reserved bits")
    return word


def compile_jobs(request, registry, root):
    schemas = registry.get("schemas", {})
    bindings = registry.get("jobs", {})
    rows, rejected = [], []
    for job in request["jobs"]:
        ident = job["id"]
        try:
            entry = bindings.get(ident)
            if entry is None:
                raise ValueError("no owned native job binding")
            schema = schemas.get(entry["schema"])
            if schema is None:
                raise ValueError("no owned native endpoint schema")
            if schema.get("status") != "OWNER_NATIVE_CONTRACT":
                raise ValueError("endpoint schema not owner-qualified")
            if job["engine"] != schema["engine"]:
                raise ValueError("engine endpoint mismatch")
            # Both RTL and its separately owned port/address contract are pinned.
            for evidence in schema["evidence"]:
                if digest(root / evidence["path"]) != evidence["sha256"]:
                    raise ValueError("native evidence source changed")
            if not schema["evidence"]:
                raise ValueError("native schema has no pinned source/contract")
            context = dict(request.get("context", {}))
            context.update(job.get("context", {}))
            signals = schema["signals"]
            if set(entry["signals"]) != set(signals):
                raise ValueError("binding must name every native signal")
            values = {}
            for name, signal in signals.items():
                word = pack(signal, entry["signals"][name], context)
                values[name] = {"width": signal["width"],
                                "hex": f"{word:0{(signal['width']+3)//4}x}"}
            rows.append({"id": ident, "engine": job["engine"],
                         "endpoint": schema["endpoint"], "signals": values})
        except (ValueError, KeyError, OSError, TypeError) as error:
            rejected.append({"id": ident, "reason": str(error)})
    # Atomic whole program: partial native tables are never dispatch eligible.
    return {"status": "NATIVE_COMPILE_PASS" if not rejected and rows else "NATIVE_COMPILE_BLOCKED",
            "dispatch_eligible": not rejected and bool(rows),
            "rows": rows if not rejected else [], "rejected": rejected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compile_jobs(json.loads(args.request.read_text()),
                          json.loads(args.registry.read_text()), args.root)
    result["request_sha256"] = digest(args.request)
    result["registry_sha256"] = digest(args.registry)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(0 if result["dispatch_eligible"] else 2)


if __name__ == "__main__":
    main()
