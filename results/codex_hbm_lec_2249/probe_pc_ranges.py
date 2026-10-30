#!/usr/bin/env python3
"""Prove source-derived key ranges against retained AIGs, without RTL edits.

These are untrusted invariant proposals. Every range is an additional next-state
proof obligation; this script never changes the original failed verdict.
"""
import importlib.util
import itertools
import json
import os
import sys
from pathlib import Path

tool, kit, out = map(Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("lec", tool)
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)
work, log = kit / "lec", []
model = lec.Lec(lec.read_aig(work / "gold.aig"), lec.read_map(work / "gold.map"),
                lec.read_aig(work / "gate.aig"), lec.read_map(work / "gate.map"))
lec.normalize_gold_elements(model, lec.slang_elements(work / "gold.aliases.json"), log)
lec.json_alias_keys(model, log, work=work)
lec.slang_element_keys(model, log, work=work)
lec.alias_arrays(model, log, work=work)
model.hyp = {(side, key): tuple(hyp) for side, key, hyp in json.loads((work / "hyp.json").read_text())}
prefix = "ff:u_dut.u_fcore.controller.on."
rank = {s: i for i, s in enumerate([3, 4, 2, 5, 1, 6, 0, 7])}
ranges = []
for s in range(8):
    values = {127}  # Exact reset value and the refreshed-bank value.
    for k, last, nxt, streaming, opened, done, stale, busy, wset in itertools.product(
            range(8), range(8), *([range(2)] * 7)):
        d = (s - k) & 7
        ahead = (s >= k and s <= last) or nxt
        if wset and s == last and not opened:
            base = 20
        elif not streaming:
            base = rank[s] + (32 if opened else 0)
        elif opened:
            base = 24 if done or stale else 32
        elif ahead and d <= 2:
            base = 16 + 2 - d
        elif ahead:
            base = d
        else:
            base = 8 + s
        values.add((base + (64 if not opened and busy else 0)) & 127)
    ranges.append(values)

def add(keys, values):
    if not all(key in model.gp for key in keys):
        raise ValueError(f"missing source key: {keys}")
    assert 127 in values, "Every proposed range must contain the actual reset state"
    allowed = [[(value >> bit) & 1 for bit in range(7)] for value in sorted(values)]
    model.cons.append(("gold", keys, allowed))

for bank in range(32):
    add([prefix + f"keys_r[{bank * 7 + bit}]" for bit in range(7)], ranges[bank // 4])
geometry = lec.memory_geometry(work / "gold.aliases.json")
for base, groups in [("s1k", [[s] for s in range(8)]), ("s2k", [list(range(4)), list(range(4, 8))])]:
    width, size, offset = geometry[prefix + base]
    assert (width, size, offset) == (7, len(groups), 0)
    keys = [key for key in model.gp if key.startswith(prefix + base + "[")]
    words = {int(key.split(base + "[")[1].split("]")[0]) for key in keys}
    assert size % len(words) == 0
    factor = size // len(words)
    for word, sources in enumerate(groups):
        add([prefix + f"{base}[{word // factor}][{(word % factor) * 7 + bit}]" for bit in range(7)],
            set().union(*(ranges[s] for s in sources)))
os.environ["OT_LEC_RESET_CYCLES"] = "64"
(out / "range_proposals.json").write_text(json.dumps(model.cons, indent=2) + "\n")
miter, _ = model.build(with_compare=True, with_hyp=True)
status = lec.prove(miter, out, 1000, log, tag="source_ranges", single_cap=0)
result = dict(verdict="DIAGNOSTIC_ONLY", original=json.loads((work / "lec.json").read_text())["counts"],
              constraints=len(model.cons), outputs=len(status),
              proved=sum(s == "proved" for s in status.values()),
              failed_constraints={k: v for k, v in status.items() if k.startswith("cons:") and v != "proved"},
              remaining=[k for k, v in status.items() if v != "proved"])
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
(out / "probe.log").write_text("\n".join(log))
print(json.dumps({k: v for k, v in result.items() if k != "remaining"}))
