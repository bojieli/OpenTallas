#!/usr/bin/env python3
"""S81-UNBLOCK-2 10-27: carry the S81 dead-input proof onto the PD5 composed plan (d217c071).

PD5 renamed 12 of the 16 proof types (phy1026 fit: svc_hi_dsdv_svc_rs__t6 -> svc_hi_dsdv_svc_rs__t6_phy1026_svc_15 ...)
and dropped every per-type `dead_inputs` declaration, so the strict bind fails closed ("missing or mismatched per-type
plan dead-input declaration").  This re-keys the proof rows by partition MEMBERSHIP, never by name guess:
a main type maps to a PD5 type only when both hold exactly the same partition instances (checked both ways).
Every other proof field (module, parameters, source, module_sha256, ports, method, remaining_loads) is unchanged and is
re-verified by bind.py (dead_inputs.ProvenDead) against the selected RTL at bind time.

  python3 pd5_dead_inputs.py MAIN_PLAN PD5_PLAN PROOF OUT_PROOF OUT_PLAN    (PROOF / OUT_PROOF repository-relative)
"""
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools" / "die_plan"))
import dead_inputs as D  # noqa: E402


def members(plan):
    m = collections.defaultdict(set)
    for p in plan["partitions"]:
        m[p["type"]].add(p["name"])
    return m


def main(main_plan, pd5_plan, proof_rel, out_proof_rel, out_plan):
    repo = Path(__file__).resolve().parents[4]
    M, P = json.load(open(main_plan)), json.load(open(pd5_plan))
    proof = json.loads((repo / proof_rel).read_text())
    mm, pm = members(M), members(P)
    inv = {frozenset(v): k for k, v in pm.items()}
    ren = {}
    for row in proof["declarations"]:
        t = row["partition_type"]
        if t in ren:
            continue
        tgt = inv.get(frozenset(mm[t]))
        if tgt is None:
            raise SystemExit(f"main type {t}: no PD5 type with the same partition set {sorted(mm[t])}")
        ren[t] = tgt
    rows = []
    for row in proof["declarations"]:
        r = dict(row)
        r["partition_type"] = ren[row["partition_type"]]
        if r["partition_type"] != row["partition_type"]:
            r["rekeyed_from"] = row["partition_type"]
        rows.append(r)
    src_sha = hashlib.sha256((repo / proof_rel).read_bytes()).hexdigest()
    out = dict(proof, declarations=rows,
               note=proof.get("note", "") + f" | S81-UNBLOCK-2 10-27: rows re-keyed to PD5 composed type names by exact "
                    f"partition membership (pd5_dead_inputs.py) from {proof_rel} sha256 {src_sha}; proof content unchanged.")
    (repo / out_proof_rel).write_text(json.dumps(out, indent=1) + "\n")
    n = D.apply_plan_declarations(P, out_proof_rel, repo)
    Path(out_plan).write_text(json.dumps(P, indent=1) + "\n")
    print(json.dumps(dict(renamed={k: v for k, v in ren.items() if k != v}, kept=sorted(k for k, v in ren.items() if k == v),
                          declarations=n, out_proof=out_proof_rel, out_plan=str(out_plan),
                          out_plan_sha256=hashlib.sha256(Path(out_plan).read_bytes()).hexdigest())))


if __name__ == "__main__":
    main(*sys.argv[1:6])
