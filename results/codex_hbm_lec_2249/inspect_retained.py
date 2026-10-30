#!/usr/bin/env python3
"""Read retained failed proofs; propose candidates only, never a verdict."""
import collections
import importlib.util
import json
import sys
from pathlib import Path

tool, kit, output = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("lec", tool)
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)
work = kit / "lec"
record = json.loads((work / "lec.json").read_text())
model = lec.Lec(lec.read_aig(work / "gold.aig"), lec.read_map(work / "gold.map"),
                lec.read_aig(work / "gate.aig"), lec.read_map(work / "gate.map"))
log = []
lec.normalize_gold_elements(model, lec.slang_elements(work / "gold.aliases.json"), log)
lec.json_alias_keys(model, log, work=work)
lec.slang_element_keys(model, log, work=work)
lec.alias_arrays(model, log, work=work)
by_q, by_d = collections.defaultdict(list), collections.defaultdict(list)
for key in model.gp:
    by_q[model.gp[key]].append(key)
for key in model.gc:
    by_d[model.gc[key]].append(key)
failed = record["failing"]
keys = sorted({key for point in failed for key in point.get("cone_unmatched_keys", [])})
rows = []
for key in keys:
    if key not in model.gp:
        continue
    qaliases = by_q[model.gp[key]]
    daliases = by_d.get(model.gc.get(key), [])
    rows.append(dict(key=key, matched=key in model.matched,
                     q_aliases=[k for k in qaliases if k != key][:24],
                     d_aliases=[k for k in daliases if k != key][:24],
                     matched_q_aliases=[k for k in qaliases if k in model.matched],
                     matched_d_aliases=[k for k in daliases if k in model.matched]))
summary = dict(kit=str(kit), prior_counts=record["counts"],
               prior_verdict=record["verdict"], verdict="DIAGNOSTIC_ONLY",
               normalization=log, unmatched_keys=rows)
output.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(dict(counts=record["counts"], keys=len(rows),
                      q_candidates=sum(bool(r["matched_q_aliases"]) for r in rows),
                      d_candidates=sum(bool(r["matched_d_aliases"]) for r in rows))))
