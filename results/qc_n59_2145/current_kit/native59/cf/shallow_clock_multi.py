"""Explicit multi-root planner adapter; the default single-root planner is untouched."""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

NODE = re.compile(r"ot_dtsh_(\d+)$")


def offset_nodes(plan, offset):
    if offset < 0:
        raise ValueError("negative node offset")
    names = [n["name"] for n in plan["nodes"]]
    if len(names) != len(set(names)) or any(not NODE.fullmatch(n) for n in names):
        raise ValueError("invalid original node identities")
    mapping = {n: f"ot_dtsh_{int(NODE.fullmatch(n)[1]) + offset}" for n in names}
    def walk(value):
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, dict):
            return {mapping.get(k, k): walk(v) for k, v in value.items()}
        return value
    result = walk(plan)
    result["multi_root_node_offset"] = offset
    next_id = max(int(NODE.fullmatch(n)[1]) for n in mapping.values()) + 1
    return result, next_id


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--node-offset", type=int, required=True)
    a, args = ap.parse_known_args()
    # Every new phase and measured move runs the unchanged planner directly on
    # the already globally named plan; only initial construction is offset.
    if any(x in args for x in ("--cl-step", "--new-phase", "--restore-best")):
        raise ValueError("offset adapter is only for initial plan construction")
    def option(name):
        return args[args.index(name) + 1]
    out, apply = Path(option("--out")), Path(option("--apply"))
    base = Path(__file__).with_name("shallow_clock.py")
    subprocess.run([sys.executable, str(base), *args], check=True)
    plan, next_id = offset_nodes(json.loads(out.read_text()), a.node_offset)
    spec = importlib.util.spec_from_file_location("multi_root_base_planner", base)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.validate(plan)
    mod.emit_apply(plan, apply)
    out.write_text(json.dumps(plan, indent=2) + "\n")
    print(f"OT_DTSH_MULTI_NODE_IDS offset {a.node_offset} next {next_id}")


if __name__ == "__main__":
    main()
