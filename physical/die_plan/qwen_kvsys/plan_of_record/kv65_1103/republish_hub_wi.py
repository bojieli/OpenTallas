#!/usr/bin/env python3
"""DIE-KV-65 11-03: republish the kv3_hub_Wi landing collector_tree.

RF-KV1 fold b90e037d531 shrank the HR hard cores of kv3_hub_Wi, so the reset tree solved from the plan moved, while
clock.landing_contract.collector_tree stayed the pre-fold snapshot.  bind then builds collector reset copies from
relays the wrapper does not declare (strict die bind: EMIT collector rst_rl_35: raw reset parent rst_rl_27 absent).
kv3_hub_Wi is the only type with a stale tree.  The landed sidecar keeps the same copy, and bind reads that copy.
Text span replace: every other byte stays identical.

    republish_hub_wi.py PLAN SIDECAR   (run from the repository root)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import reset_tree as RT
import schema

TYPE = "kv3_hub_Wi"
GUARD = ("depth", "own_depth", "entry", "taps", "outs", "n_clock_taps")


def replace_span(text, start, old, new):
    """replace the JSON object after offset start with new, at that object's own indent"""
    begin = text.index("{", start)
    dec, used = json.JSONDecoder().raw_decode(text[begin:])
    if dec != old:
        raise SystemExit("span is not the published tree")
    line = text[text.rindex("\n", 0, begin) + 1:begin]
    indent = len(line) - len(line.lstrip())
    body = json.dumps(new, indent=1).replace("\n", "\n" + " " * indent)
    return text[:begin] + body + text[begin + used:]


def main(plan_path, side_path):
    p, q = Path(plan_path), Path(side_path)
    text, side_text = p.read_text(), q.read_text()
    raw, side = json.loads(text), json.loads(side_text)
    new = json.loads(json.dumps(RT.for_type(schema.Plan(raw, p), TYPE)))
    old = raw["partition_types"][TYPE]["clock"]["landing_contract"]["collector_tree"]
    if side["collector"]["types"][TYPE]["tree"] != old:
        raise SystemExit("sidecar tree differs from the plan tree")
    for key in GUARD:
        if old.get(key) != new.get(key):
            raise SystemExit(f"{TYPE}: contract field {key} changed: {old.get(key)} -> {new.get(key)}")
    start = text.index('"collector_tree"', text.index(f'"{TYPE}": {{'))
    out = replace_span(text, start, old, new)
    chk = json.loads(out)
    chk["partition_types"][TYPE]["clock"]["landing_contract"]["collector_tree"] = old
    if chk != raw:
        raise SystemExit("delta touched another plan field")
    types = side_text.index('"types"', side_text.index('"collector"'))
    start = side_text.index('"tree"', side_text.index(f'"{TYPE}": {{', types))
    side_out = replace_span(side_text, start, old, new)
    chk = json.loads(side_out)
    chk["collector"]["types"][TYPE]["tree"] = old
    if chk != side:
        raise SystemExit("delta touched another sidecar field")
    p.write_text(out)
    q.write_text(side_out)
    print(f"{TYPE}: relays {len(old['relays'])} -> {len(new['relays'])}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
