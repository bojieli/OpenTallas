#!/usr/bin/env python3
"""DIE-S81-47 11-01 svc_rs class: refresh the S81 dead-input proof hash of dsdv_svc_sx after the SVC endpoint alias
fix (3d45bed4e2f, Codex: explicit module-local face_gout / face_sout aliases so production Yosys reads the module).

The selected proof results/token_pass/s81_dead_inputs_2148/proof_closing_s13obs_1029.json pins the exact source bytes
of every declared module (module_sha256).  The alias fix changed dsdv_svc_sx, so strict bind fails with "stale
dead-input source rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx.sv" on every svc_rs / pvso_entry type.  The proof was
re-run (tools/die_plan/s81_dead_prove.py, same instances / stubs / manifest asbuilt_b178_coll_h2_2249.json) on the
fixed source: same 36 declarations, same 21 specializations, same ports and bits; only the dsdv_svc_sx module hash
changes.  This delta republishes the per-type plan declarations from that proof (dead_inputs.plan_declaration) and
asserts nothing else in the plan changes.
usage (repo root): delta_svcsx_deadhash_1101.py PLAN_IN PLAN_OUT REPORT.json"""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import compact_plan as CP  # noqa: E402
import dead_inputs as DI  # noqa: E402

PROOF = "results/token_pass/s81_dead_inputs_2148/proof_closing_s13obs_1029.json"


def main():
    src, dst, rp = sys.argv[1:4]
    text = Path(src).read_text()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    rows = json.loads((ROOT / PROOF).read_text())["declarations"]
    want = {}
    for row in rows:
        want.setdefault(row["partition_type"], []).append(DI.plan_declaration(row, PROOF))
    changed, hashes = [], set()
    for tn, t in raw["partition_types"].items():
        old = [d for d in t.get("dead_inputs", []) if d.get("proof") == PROOF]
        new = want.get(tn, [])
        assert len(old) == len(new), (tn, len(old), len(new))
        if old == new:
            continue
        for a, b in zip(old, new):        # same declaration except the dsdv_svc_sx source hash
            assert {k: v for k, v in a.items() if k != "module_sha256"} == \
                   {k: v for k, v in b.items() if k != "module_sha256"}, tn
            assert a["module"] == "dsdv_svc_sx" or a == b, (tn, a["module"])
            if a != b:
                hashes.add((a["module_sha256"], b["module_sha256"]))
        others = [d for d in t["dead_inputs"] if d.get("proof") != PROOF]
        t["dead_inputs"] = others + new if t["dead_inputs"][:len(others)] == others else None
        assert t["dead_inputs"] is not None and len(t["dead_inputs"]) == len(old) + len(others), tn
        changed.append(tn)
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        a, b = raw["partition_types"][tn], orig["partition_types"][tn]
        assert {k: v for k, v in a.items() if k != "dead_inputs"} == {k: v for k, v in b.items() if k != "dead_inputs"}, tn
        if tn not in changed:
            assert a == b, tn
    for tn in changed:
        mm = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, mm.end())
        text = text[:mm.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    Path(dst).write_text(text)
    rep = dict(proof=PROOF, changed_types=sorted(changed), n_changed=len(changed),
               module="dsdv_svc_sx", sha256_old_new=sorted(hashes))
    Path(rp).write_text(json.dumps(rep, indent=1) + "\n")
    print("DELTA_SVCSX_DEADHASH", len(changed), "types", sorted(hashes))


if __name__ == "__main__":
    main()
