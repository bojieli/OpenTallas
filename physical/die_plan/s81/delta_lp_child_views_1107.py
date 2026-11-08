#!/usr/bin/env python3
"""S81 plan event, LP child views (S81-TYPES-5 11-07, COORD 17:40 (B) REAL VIEW CLASS).

The 4 LP slice types (dsdv_slice_lepe_mu_LP__t2, dsdv_slice_lepe_nh_mus_LP__t1, dsdv_slice_lepw_mu_LP__t2,
dsdv_slice_lepw_mus_LP__t2) name 28 hard cores of 4 masters with a plan stub LEF and no liberty, so gen_phys stops
"macros have LEF but no timing liberty".  All 4 masters are signed; their views are filed under
cores/views/<master>_signed_1107/ (export_view.py of the signed kit + its re-sign record, lib = the ORFS finish ETMs of
the signed 6_final.odb + 6_final.spef, LEF = the abstract of the same DB, view_lef bind receipt <master>.view.json).

Per row: lib -> the view TT ETM and lef -> the view's own LEF (view_lef.attach, the view_lef move rule).  Asserted:
outline = LEF SIZE, the plan pins_file names the same pin bits on the same layer and xy as the signed kit pins.json,
the view lib and LEF have exactly the same signal pin bits.  The core clock taps u_u_lnl*.ck_k / ck_n ("measured view
pending") take the signed boundary mean (insertion.json, signoff core_latency.measured), as the bk_g / vs5 events.
Origin, orient, track offset, pins_file, obs_max, reset trees: unchanged (asserted for reset trees).
    python3 delta_lp_child_views_1107.py PLAN_IN PLAN_OUT REPORT.json        (cwd = repo root)
PLAN_OUT is in plan_text form, which re-formats rows of earlier events; the committed plan_h2_2249.json is PLAN_IN with
only the changed lines edited (diff -U2 plan_text(PLAN_IN) PLAN_OUT | patch PLAN_IN, 32 hunks), json-equal to PLAN_OUT.
"""
import json
import sys
from pathlib import Path

sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import reset_tree as RT  # noqa: E402
import schema as S  # noqa: E402
import view_lef as VL  # noqa: E402
from plan_event_1104 import plan_text  # noqa: E402

TYPES = ("dsdv_slice_lepe_mu_LP__t2", "dsdv_slice_lepe_nh_mus_LP__t1", "dsdv_slice_lepw_mu_LP__t2",
         "dsdv_slice_lepw_mus_LP__t2")
MASTERS = ("dsfd_coll_lane_e_safe8_ntf", "dsfd_coll_lane_w_safe8_ntf", "ot_s81_mu72_lnland", "ot_s81_mu72_lnland_nst")
D = Path("physical/die_plan/s81")
VIEW = lambda m: f"physical/die_plan/s81/cores/views/{m}_signed_1107"


def plan_pins(pf):
    return {q["name"]: (q["layer"], round(q["x"], 4), round(q["y"], 4)) for q in json.loads((D / pf).read_text())["pins"]}


def kit_pins(m):
    out = {}
    for q in json.loads(Path(f"{VIEW(m)}/pins.json").read_text()):
        n = q["bus"] if q.get("bit") is None else f"{q['bus']}[{q['bit']}]"
        out[n] = (q["layer"], round(q["x"], 4), round(q["y"], 4))
    return out


def main():
    src, out, rep = sys.argv[1:]
    P = json.loads(Path(src).read_text())
    Ps = S.Plan(S.load(src), src)
    users = sorted({tn for tn, t in P["partition_types"].items() for k in ("hard_cores", "contents")
                    for c in t.get(k) or [] if (c.get("physical_master") or c.get("module")) in MASTERS})
    assert users == sorted(TYPES), users
    view = {}
    for m in MASTERS:
        lib, lef = f"{VIEW(m)}/{m}_tt.lib", f"{VIEW(m)}/{m}.lef"
        row = VL.compare(Path(lef).read_text(), lib)
        assert row["cell"] == m and not (row.get("unread") or row["lef_only"] or row["lib_only"]), (m, row)
        rec = json.loads(Path(VL.receipt_path(lib)).read_text())
        assert rec["lib_sha256"] == VL._sha(lib) and rec["lef_sha256"] == VL._sha(lef), m
        _, size = VL.lef_view(Path(lef).read_text(), m)
        view[m] = dict(lib=lib, lef=lef, size=[float(v) for v in size], pins=kit_pins(m),
                       ins=json.loads(Path(f"{VIEW(m)}/insertion.json").read_text()))
    report = {}
    for tn in TYPES:
        t = P["partition_types"][tn]
        rows = []
        for c in t["hard_cores"]:
            m = c.get("module")
            if m not in MASTERS:
                continue
            v = view[m]
            assert "lib" not in c and c["outline_um"] == v["size"], (tn, c["inst"])
            assert plan_pins(c["pins_file"]) == v["pins"], (tn, c["inst"], "plan pins differ from the signed kit pins")
            old_lef = c["lef"]
            VL.attach(c, v["lib"])
            assert c["lef"] == v["lef"], (tn, c["inst"])
            c["note"] = f"signed view {VIEW(m)} (S81-TYPES-5 11-07; record PROVENANCE.json there)"
            taps = []
            for x in t.get("clock", {}).get("taps", []):
                if x["name"].startswith(c["inst"] + "."):
                    old = (x.get("insertion_ps"), x.get("insertion_ff_ps"))
                    x.update(insertion_ps=v["ins"]["tt"]["boundary"]["mean"], insertion_ff_ps=v["ins"]["ff"]["boundary"]["mean"],
                             budget_owner=f"parent_budget pin_register_mean {VIEW(m)}/insertion.json",
                             note="H2 same-parent-clock dual-input LN; signed view insertion (S81-TYPES-5 11-07)")
                    taps.append(dict(tap=x["name"], old=old, new=(x["insertion_ps"], x["insertion_ff_ps"])))
            rows.append(dict(inst=c["inst"], module=m, old_lef=old_lef, lef=c["lef"], lib=c["lib"], taps=taps))
        report[tn] = rows
    assert sum(len(r) for r in report.values()) == 28, {k: len(r) for k, r in report.items()}
    Path(out).write_text(plan_text(P))
    Pn = S.Plan(S.load(out), out)
    moved = [tn for tn in TYPES if json.dumps(RT.for_type(Ps, tn), sort_keys=True, default=str)
             != json.dumps(RT.for_type(Pn, tn), sort_keys=True, default=str)]
    assert not moved, moved
    Path(rep).write_text(json.dumps(dict(types=report, reset_tree_moved=moved), indent=1) + "\n")
    print(json.dumps(dict(rows=sum(len(r) for r in report.values()),
                          taps=sum(len(x["taps"]) for r in report.values() for x in r), reset_tree_moved=len(moved))))


if __name__ == "__main__":
    main()
