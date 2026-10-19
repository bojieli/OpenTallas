#!/usr/bin/env python3
"""HBM-NEXT-VEH (10-19 step 4b): token composition with ALL measured unit IIs (CMTP plane_compiler step 5, "ALL measured
v2" [+ frames]) AND the measured next-die physical terms in the same S2 schedule, per SM-area option -> OWNER input.

CMTP's step-5 re-time (results/arch/hbm_next_1019/cmtp/retime/meas5_retime.json) prices every unit at its measured row
II but keeps the D1 (d4g-class) relay stage set; VEH's compose_grid PHYS axis moved the stages but ran on the priced
unit IIs.  This driver does both at once, in the same forked-child discipline (fork context, knobs set before the fork):
  * unit IIs     plane_compiler.Knobs(meas=MEAS_ALL2 [+ idx_frame, fused_frame]): IDXN 1,297 + 232 (N-1), SU.VOP v2
                 2k ceil(e/512), ARGMAX 22, KVWB 8 +28/wrap, FUSED 81 / 103, HC II 250, IDX TOPK/UNION, COLL rows,
                 ATT4 merge, SM4 lane skew (+8 a further lane a pass), VM 2^19 (grown).
  * stage set    every relay class of the D1 plan_b stage set moved by (DIE <plan> - DIE d4g) bit-weighted stages
                 (results/arch/hbm_next_1019/die/plan/plan_p4.json per_class), the COLL ring / crossing knob re-derived
                 from the moved set (compose_grid._phys form).  Plans: P4 (a) re-shaped = f4c_t8_LaA, P3+(a) =
                 f4c_t8_Lp3a (DIE step 4 lever rows), f4c_t8 = the P = 4 base frame (reference).
  * SM4 front    +2 cycles (lane front + publish merge, SM4 bench_summary.json) on every SM record incl. AR; the +8p lane
                 skew is NOT added again (sm4skew already charges it).
Self-check (fails closed): stage 'd4g' + front 0 must reproduce meas5_retime.json for the same option / case.

    PYTHONPATH=tools python3 tools/hbm_next/vehicle/compose_meas_phys.py --out JSON [--only P4a,..] [--stages d4g,..]
"""
import argparse
import copy
import dataclasses
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/hbm_next"))
import plane_compiler as PC  # noqa: E402

DIE_PLAN = ROOT / "results/arch/hbm_next_1019/die/plan/plan_p4.json"
REF = ROOT / "results/arch/hbm_next_1019/cmtp/retime/meas5_retime.json"
SM4_FRONT = 2.0
OPT_STAGE = {"P4a": "f4c_t8_LaA", "P4a_rpl0": "f4c_t8_LaA", "P3a_u4": "f4c_t8_Lp3a", "P3a_u3": "f4c_t8_Lp3a"}
CASES = {"ALL measured v2": PC.MEAS_ALL2, "ALL measured v2 + frames": PC.MEAS_ALL2 + ("idx_frame", "fused_frame")}
PHYS = dict(stage="d4g", front=0.0, info=None)


def _apply_phys():
    """after plane_compiler.apply_knobs (before the pool forks): move the stage set + SM4 front"""
    from hgi_sim import hbm_plane_model as M
    from hgi_sim import d4g_quadrant_1017 as Q
    from hgi_sim import plan_study_price_1017 as PS
    from hgi_sim import ds_mtp_verify as V
    kn = PC.CUR["knobs"]
    L = kn.coll_lanes
    moved = {}
    if PHYS["stage"] == "d4g":          # reset the knob dict a previous moved case left in the module env
        env = M._ENV
        env["vb"] = PS.VARIANTS["b"]
        env["kn"] = dict(Q.knob(Q.ADDERS, env["st"], ledger=Q.load_ledger()), rings=2, ag_qbg=True, lanes=L)
        M.d4g_env()
    else:
        plan = json.loads(DIE_PLAN.read_text())
        ref = {k: v["stages_bw"] for k, v in plan["d4g"]["per_class"].items()}
        new = {k: v["stages_bw"] for k, v in plan[PHYS["stage"]]["per_class"].items()}
        env = M._ENV
        st = env["st"]
        o = dict(st["plan_b"])
        for k in sorted(set(ref) & set(new)):
            if k in o and abs(new[k] - ref[k]) > 1e-9:
                moved[k] = [o[k], round(max(0.0, o[k] + new[k] - ref[k]), 3)]
                o[k] = moved[k][1]
        nm = "hnx_" + PHYS["stage"]
        st[nm] = o
        vb = copy.deepcopy(PS.VARIANTS["b"])
        vb["stages"] = nm
        vb["split"]["lanes"] = L
        env["vb"] = vb
        env["kn"] = dict(Q.knob(Q.ADDERS, st, plan=nm, ledger=Q.load_ledger()), rings=2, ag_qbg=True, lanes=L)
        M.d4g_env()
    if not hasattr(V, "_veh_cost_fn0"):
        V._veh_cost_fn0 = V.cost_fn
    V.cost_fn = V._veh_cost_fn0
    if PHYS["front"]:
        prev = V._veh_cost_fn0

        def cost_fn(scale=None):
            f = prev(scale)

            def cf(r, dyn, L_):
                c, g, how = f(r, dyn, L_)
                if r.unit == "SM":
                    c += PHYS["front"]
                return c, g, how
            return cf
        V.cost_fn = cost_fn
    PHYS["info"] = dict(stage=PHYS["stage"], moved_stages=moved, sm4_front=PHYS["front"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default=None, help="options (P4a, P4a_rpl0, P3a_u4, P3a_u3)")
    ap.add_argument("--stages", default="d4g,plan,f4c_t8", help="'plan' = the option's DIE lever row")
    ap.add_argument("--cases", default="|".join(CASES))
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    from hgi_sim import hbm_plane_model as M
    PC.MODE5[0] = True
    st = M.load_stats(PC.STATS)
    PC.CUR["hist"] = PC.lane_hists()
    orig = PC.apply_knobs

    def apply_knobs(kn):
        orig(kn)
        _apply_phys()
    PC.apply_knobs = apply_knobs
    ref = json.loads(REF.read_text())["options"]
    out = dict(schema="opentallas.hbm_next_1019.veh.compose_meas_phys.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, targets=dict(
        ds_ar=1905.4, ds_mtp=3363.5, mu_agg=4365.3, mu_per_user_floor=1000.0), rows=[], selfcheck=[])
    if a.out.exists():
        old = json.loads(a.out.read_text())
        out["rows"], out["selfcheck"] = old.get("rows", []), old.get("selfcheck", [])
    done = {(r["option"], r["case"], r["stage"]) for r in out["rows"]}
    for key, label, kn0, mu_n in PC.MEAS_OPTIONS:
        if a.only and key not in a.only.split(","):
            continue
        for case in a.cases.split("|"):
            for sg in a.stages.split(","):
                stage = OPT_STAGE[key] if sg == "plan" else sg
                if (key, case, stage) in done:
                    continue
                PHYS.update(stage=stage, front=0.0 if stage == "d4g" else SM4_FRONT)
                kn = dataclasses.replace(kn0, meas=tuple(CASES[case]))
                t0 = time.time()
                r = PC.run_case(kn, st, a.jobs, kn.P, mu_n)
                row = dict(option=key, label=label, case=case, stage=stage, phys=PHYS["info"], users=mu_n,
                           ar_tok_s=r["ar_tok_s"], mtp_tok_s=r["mtp"]["tok_s"], mtp_step_cycles=r["mtp"]["step_cycles"],
                           mu_agg_tok_s=r["mu"]["agg_tok_s"], mu_per_user_tok_s=r["mu"]["per_user_tok_s"],
                           ar_cycles=r["ar_cycles"], wall_s=round(time.time() - t0, 1))
                out["rows"].append(row)
                if stage == "d4g":
                    rr = ref.get(key, {}).get("cases", {}).get(case)
                    if rr:
                        ok = (rr["ar_tok_s"], rr["mtp"]["tok_s"], rr["mu"]["agg_tok_s"]) == (
                            row["ar_tok_s"], row["mtp_tok_s"], row["mu_agg_tok_s"])
                        out["selfcheck"].append(dict(option=key, case=case, ok=ok, ref=[rr["ar_tok_s"], rr["mtp"]["tok_s"],
                                                     rr["mu"]["agg_tok_s"]], got=[row["ar_tok_s"], row["mtp_tok_s"],
                                                                                  row["mu_agg_tok_s"]]))
                print(f"{key:8s} {stage:12s} {case:26s} AR {row['ar_tok_s']:7.1f}  MTP {row['mtp_tok_s']:7.1f}  "
                      f"MU{mu_n} {row['mu_agg_tok_s']:7.1f} / {row['mu_per_user_tok_s']:7.1f}", flush=True)
                a.out.parent.mkdir(parents=True, exist_ok=True)
                a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    srcs = ["tools/hbm_next/plane_compiler.py", "tools/hbm_next/vehicle/compose_meas_phys.py",
            "tools/hgi_sim/hbm_plane_model.py", "tools/hgi_sim/ds_mtp_verify.py",
            "results/arch/hbm_next_1019/die/plan/plan_p4.json", "results/arch/hbm_next_1019/cmtp/retime/meas5_retime.json"]
    out["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    out["selfcheck_ok"] = all(s["ok"] for s in out["selfcheck"]) if out["selfcheck"] else None
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("selfcheck", out["selfcheck_ok"])
    return 0 if out["selfcheck_ok"] is not False else 3


if __name__ == "__main__":
    sys.exit(main())
