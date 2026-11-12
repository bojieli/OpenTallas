#!/usr/bin/env python3
"""QC-EVENT-S26 11-11 (DIE-QC-99 QC event; COORD 21:46 ring-bond APPROVED + 22:14 hc1/hc2 density form ADOPTED):
plan_qc99_s26 = plan_qc99_s25 (e4820bd9d97c, the plan of record the wave runs with bind out_s25fix) + three items.
Clock / tap / landing-strip keys only: no RTL, no cycles, no core moves or core-shape change.

 (1) RING-BOND (claude/die-qc-97-ring-bond-1112@fd1477d9ce0b): clock.tap_pair_affinity.ring_depth = 3 and
     ring_pair_um = 70 on every type that already runs the pair affinity (29 types; COORD 21:46: 70 covers the 66-um
     STATUS_REG pair with less reach than the pilot's 80).  gen_phys exports OT_TAP_PAIR_RING_DEPTH / _UM.
 (2) HC1/HC2 DENSITY FORM (claude/die-qc-97-hc1-strip-1111@88e2ccc103ea, derive_hc_cland_1111.py; the 11-11 form is
     two passes, exactly as in that commit):
       --bases sle_hc2,slw_hc2 --rows 3 --widen            (+ --sidecar)
       --bases sle_hc1,slw_hc1 --rows 4 --widen --keep-band (+ --sidecar)
     Keys: budgets.cland_strip_rows_types sle_hc2 = 3, slw_hc2 = 3, sle_hc1 = 4, slw_hc1 = 4 (base names; gen_phys
     _cland_strip_rows resolves type, then base -> OT_CLAND_STRIP_ROWS); b_hw_i S-face window widened on the 11 hc1/hc2
     types (hc2 [4.32,276.288] -> [4.32,499.776], hc1 -> [4.32,409.344]) with every later window on that face shifted
     by the same delta; the 4 sle_ctl seam partners' N-face windows mapped through the placement frames; landing face
     pins and collector sources follow (sidecar copies them); hc2 b_hw_i band re-sited (6 types), hc1 bands kept.
     fw_v1 excluded by the script (two strikes).
 (3) TAP MERGE (COORD 21:46: a tap under 16 sinks "must not be left to padding"): clock.tap_post_merge_min_sinks = 16
     (new opt-in key, this branch: gen_phys.tap_post_merge_exports -> OT_TAP_POST_MIN_SINKS / _UM = tap_radius_um,
     clock_taps.tcl POST_MIN after the affinity passes: a tap with 0 < n < 16 sinks moves whole to its nearest tap with
     >= 16 sinks, room under the cap and every moved sink within tap_radius_um (200); hard-core and root taps never
     emptied).  The tap list is derived at gen time (taps.density_taps from the sink bins) and the near-empty taps the
     ring bond makes exist only after placement, so the merge is a kit-time rule set per type in the plan.  Set on the
     29 pair-affinity types plus every other type whose PLANNED taps predict a merge (mergesim on taps.density_taps).

    make_s26.py REPO PLAN_S25.json SIDECAR_S25.json OUT_DIR [--merge-types a,b,...]
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

RING = {"ring_depth": 3, "ring_pair_um": 70}
POST_MIN = 16
PASSES = [dict(bases=("sle_hc2", "slw_hc2"), rows=3, widen_face=True, keep_band=False),
          dict(bases=("sle_hc1", "slw_hc1"), rows=4, widen_face=True, keep_band=True)]
NOTE = (" | s26 (QC-EVENT-S26 11-11, DIE-QC-99 event, COORD 21:46 + 22:14): s25 + (1) ring-bond clock.tap_pair_affinity "
        "ring_depth 3 / ring_pair_um 70 on the 29 pair-affinity types + (2) hc1/hc2 density form (derive_hc_cland_1111 "
        "88e2ccc103ea: hc2 rows 3 widen, hc1 rows 4 widen keep-band; b_hw_i windows widened, sle_ctl partners mapped, "
        "hc2 bands re-sited) + (3) clock.tap_post_merge_min_sinks 16 (kit POST_MIN merge within tap_radius_um)")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo"); ap.add_argument("plan"); ap.add_argument("sidecar"); ap.add_argument("out")
    ap.add_argument("--merge-types", default="", help="extra (non pair-affinity) types that get the POST_MIN key")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    sys.path.insert(0, str(repo / "tools" / "die_plan"))
    spec = importlib.util.spec_from_file_location(
        "derive_hc", repo / "physical/die_plan/qwen_compute/derive_hc_cland_1111.py")
    D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
    src, sb = Path(a.plan).read_bytes(), Path(a.sidecar).read_bytes()
    raw, side = json.loads(src), json.loads(sb)
    rep = {"plan_in_sha256": sha(src), "sidecar_in_sha256": sha(sb), "passes": []}
    for ps in PASSES:
        raw, moved, wrep = D.apply(raw, ps["rows"], ps["bases"], ps["widen_face"], ps["keep_band"])
        n = D.sync_sidecar(raw, side, wrep)
        rep["passes"].append(dict(args={k: (list(v) if isinstance(v, tuple) else v) for k, v in ps.items()},
                                  moved=moved, widen=wrep, sidecar_changed=n))
    T = raw["partition_types"]
    tpa = sorted(t for t in T if "tap_pair_affinity" in T[t].get("clock", {}))
    for t in tpa:
        T[t]["clock"]["tap_pair_affinity"].update(RING)
    extra = sorted(x for x in a.merge_types.split(",") if x)
    bad = [x for x in extra if x not in T]
    if bad:
        raise SystemExit(f"unknown --merge-types {bad}")
    merge = sorted(set(tpa) | set(extra))
    for t in merge:
        T[t]["clock"]["tap_post_merge_min_sinks"] = POST_MIN
    raw["note"] = raw["note"] + NOTE
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pb = json.dumps(raw, indent=1).encode()
    so = json.dumps(side).encode()
    (out / "plan_qc99_s26.json").write_bytes(pb)
    (out / "sidecar_pv_s26.json").write_bytes(so)
    rep.update(ring_bond=dict(keys=RING, types=tpa), post_merge=dict(key="clock.tap_post_merge_min_sinks",
               value=POST_MIN, types=merge, extra_types=extra),
               strip_rows=raw["budgets"]["cland_strip_rows_types"],
               plan_out_sha256=sha(pb), sidecar_out_sha256=sha(so))
    (out / "make_s26_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("plan_in_sha256", "plan_out_sha256", "sidecar_in_sha256",
                                          "sidecar_out_sha256")}))


if __name__ == "__main__":
    main()
