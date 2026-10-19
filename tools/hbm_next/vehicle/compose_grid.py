#!/usr/bin/env python3
"""HBM-NEXT-VEH (10-19): combined re-time of the next HBM die (P = 4) on the UNCHANGED D1 compiler timing model.

The Phase-1 study (results/arch/hbm_next_1019/STUDY.md) varied one knob at a time.  The token composition needs the
knobs together, so this driver re-times DS single-user AR (P = 1 records on the P = 4 die), DS MTP verify (N = 6) and
DS 4-user (N = P = 4) over the grid
    COLL delivery lanes L   in {4 (d4g), 5 (adopted 5th lane)}
    HC further-row II       in {250 (HCP x6 measured), 600 (target), 950 (floor), 4385 (static engine measured),
                                'noHCrows' (per-position HC fallback)}
    VM                      in {'grown' (N resident columns, D1 headline), 'asbuilt' (per-layer column swaps)}
and the DSpark draft + seed overlap per (L, II).

PHYS axis (10-19 step 2, L = 5 only, II in PHYS_IIS): the measured next-die physical terms go INTO the schedule (not as
an after-the-fact bound), so the S2 scheduler hides what is off the critical path:
    'f4c_t5'        every relay class of the D1 plan_b stage set moved by (DIE f4c_t5 - DIE d4g) bit-weighted stages
                    (results/arch/hbm_next_1019/die/plan/plan_p4.json per_class; SM_HBM 2.88 -> 5.25, SM_X 11.25 ->
                    6.46, ...), the COLL ring/crossing knob re-derived from the moved stage set, PLUS the SM4 P-lane
                    tile latency on every SM record (measured, SM4 bench_summary.json: +1 lane front + 1 publish merge,
                    lane p result +8p -> +2 + 8 (lanes used - 1); P4 - P1 span = 24 at K16 and K4, 1.003x c_AR).
    'f4c_t5_smhbm'  only SM_HBM moved (+2.37) + the SM4 latency (conservative: SM_X shortening not credited).
UNITS measured HC row II 250 on the hnx RTL (= the 'II250' axis) and COLL N-row II 3K/2 (= the D1 price), so neither
needs a model change.  Every job runs in a FRESH forked child (maxtasksperchild=1) that
sets all knobs itself, so no compile cache or patched global leaks between grid points (the fleet Python 3.14
forkserver bug of Phase 1 cannot occur: the context is explicit 'fork' and the knobs are set inside the child).

Self-check (fails closed): (L4, II250, grown) must equal D1 run.json (AR 629,775.1 / MTP P4 1,338,146.6 /
MU P4 1,099,570.6 cycles); (L5, II250, grown) must equal Phase-1 coll_lanes L5; (L4, II4385, grown) must equal hc_ii.

    PYTHONPATH=tools python3 tools/hbm_next/vehicle/compose_grid.py --out DIR [--jobs N] [--quick]
"""
import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

P4 = 4
LANES = (4, 5)
IIS = ("250", "600", "950", "4385", "noHCrows")
VMS = ("grown", "asbuilt")
PHYS = ("f4c_t5", "f4c_t5_smhbm")
PHYS_IIS = ("250", "600")
DIE_PLAN = "results/arch/hbm_next_1019/die/plan/plan_p4.json"
SM4_FRONT, SM4_LANE_STEP = 2.0, 8.0     # SM4 bench_summary.json "latency"


def _phys(M, L, phys):
    """inside the forked child: move the relay stage set + SM4 lane latency (see module doc)"""
    import copy
    from hgi_sim import d4g_quadrant_1017 as Q
    from hgi_sim import plan_study_price_1017 as PS
    from hgi_sim import ds_mtp_verify as V
    plan = json.loads((M.ROOT / DIE_PLAN).read_text())
    ref = {k: v["stages_bw"] for k, v in plan["d4g"]["per_class"].items()}
    new = {k: v["stages_bw"] for k, v in plan["f4c_t5"]["per_class"].items()}
    env = M._ENV
    st = env["st"]
    o = dict(st["plan_b"])
    moved = {}
    for k in sorted(set(ref) & set(new)):
        if phys == "f4c_t5_smhbm" and k != "SM_HBM":
            continue
        if k in o and abs(new[k] - ref[k]) > 1e-9:
            moved[k] = [o[k], round(max(0.0, o[k] + new[k] - ref[k]), 3)]
            o[k] = moved[k][1]
    st["hnx_" + phys] = o
    vb = copy.deepcopy(PS.VARIANTS["b"])
    vb["stages"] = "hnx_" + phys
    vb["split"]["lanes"] = L
    env["vb"] = vb
    env["kn"] = dict(Q.knob(Q.ADDERS, st, plan="hnx_" + phys, ledger=Q.load_ledger()), rings=2, ag_qbg=True, lanes=L)
    M.d4g_env()
    prev = V.cost_fn
    n_sm = [0, 0.0]

    def cost_fn(scale=None):
        f = prev(scale)

        def cf(r, dyn, L_):
            c, g, how = f(r, dyn, L_)
            if r.unit == "SM":
                lanes = max(1, min(P4, int(getattr(r, "npos", 1) or 1)))
                add = SM4_FRONT + SM4_LANE_STEP * (lanes - 1)
                n_sm[0] += 1
                n_sm[1] += add
                c += add
            return c, g, how
        return cf
    V.cost_fn = cost_fn
    return dict(moved_stages=moved, sm4_latency=dict(front=SM4_FRONT, lane_step=SM4_LANE_STEP)), n_sm


def _job(spec):
    """runs in a fresh forked child: set every knob, then one model job"""
    from hgi_sim import hbm_plane_model as M
    from hgi_sim import ds_mtp_verify as V
    from hgi_sim import plan_study_price_1017 as PS
    L, ii, kind, name, kw = spec[:5]
    phys = spec[5] if len(spec) > 5 else None
    M.d4g_env()
    PS.VARIANTS["b"]["split"]["lanes"] = L
    M._ENV["kn"]["lanes"] = L
    M._ENV["vb"] = PS.VARIANTS["b"]
    M.d4g_env()
    info = n_sm = None
    if phys:
        info, n_sm = _phys(M, L, phys)
    if ii != "noHCrows":
        V.HCP_II = float(ii)
    t0 = time.time()
    _, res = M._any(("ds", name, kind, kw))
    res["wall_s"] = round(time.time() - t0, 1)
    if phys:
        res["phys"] = dict(info, sm_cost_calls=n_sm[0], sm4_latency_cycles_charged=round(n_sm[1], 1))
    return name, res


def specs(st, quick):
    from hgi_sim import hbm_plane_model as M
    u6, uu = st["verify_union"][M.N_MTP]["mean"], st["users_union"]
    lanes = (4,) if quick else LANES
    iis = ("250",) if quick else IIS
    J = []
    for L in lanes:
        J.append((L, "250", "verify", f"L{L}|AR", dict(P=1, N=1)))
        for ii in iis:
            drop_hc = ("HC",) if ii == "noHCrows" else ()
            J.append((L, ii if ii != "noHCrows" else "250", "draft", f"L{L}|II{ii}|draft",
                      dict(P=P4, overlap=True, union=u6)))
            for vm in VMS:
                drop = drop_hc + (("VM",) if vm == "asbuilt" else ())
                J.append((L, ii, "verify", f"L{L}|II{ii}|{vm}|MTP",
                          dict(P=P4, N=M.N_MTP, union=u6, kv="upper", drop=drop)))
                J.append((L, ii, "verify", f"L{L}|II{ii}|{vm}|MU",
                          dict(P=P4, N=P4, union=uu.get(P4, 6.0 * P4), users=True, drop=drop)))
    if not quick:
        for ph in PHYS:
            J.append((5, "250", "verify", f"{ph}|L5|AR", dict(P=1, N=1), ph))
            for ii in PHYS_IIS:
                J.append((5, ii, "draft", f"{ph}|L5|II{ii}|draft", dict(P=P4, overlap=True, union=u6), ph))
                for vm in VMS:
                    drop = ("VM",) if vm == "asbuilt" else ()
                    J.append((5, ii, "verify", f"{ph}|L5|II{ii}|{vm}|MTP",
                              dict(P=P4, N=M.N_MTP, union=u6, kv="upper", drop=drop), ph))
                    J.append((5, ii, "verify", f"{ph}|L5|II{ii}|{vm}|MU",
                              dict(P=P4, N=P4, union=uu.get(P4, 6.0 * P4), users=True, drop=drop), ph))
    return J


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=24)
    ap.add_argument("--quick", action="store_true", help="only the d4g reproduction point (L4, II250)")
    ap.add_argument("--stats", type=Path, default=None)
    a = ap.parse_args()
    from hgi_sim import hbm_plane_model as M
    stats = a.stats or M.ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json"
    st = M.load_stats(stats)
    mh = M._mh_ctl()
    J = specs(st, a.quick)
    t0 = time.time()
    with mp.get_context("fork").Pool(min(a.jobs, len(J)), maxtasksperchild=1) as pool:
        res = dict(pool.imap_unordered(_job, J, chunksize=1))
    def block(pre, L, iis):
        ar = res[f"{pre}L{L}|AR"]
        g = dict(ar_cycles=ar["cycles"], ar_tok_s=round(M.CLK / ar["cycles"], 1), ar_unit_busy=ar["unit_busy"],
                 ar_per_segment=ar["per_segment"], II={})
        if "phys" in ar:
            g["phys"] = ar["phys"]
        for ii in iis:
            d = res[f"{pre}L{L}|II{ii}|draft"]
            row = dict(draft_cycles=d["draft_cycles"], seed_cycles=d["seed_cycles"],
                       overlap_credit=d["overlap"]["credit"], mh_ctl_cycles=mh, VM={})
            for vm in VMS:
                v = res[f"{pre}L{L}|II{ii}|{vm}|MTP"]
                u = res[f"{pre}L{L}|II{ii}|{vm}|MU"]
                step = v["cycles"] + d["draft_cycles"] + d["seed_cycles"] + mh - d["overlap"]["credit"]
                row["VM"][vm] = dict(
                    mtp_verify_cycles=v["cycles"], mtp_step_cycles=round(step, 1),
                    ds_mtp_tok_s=round(M.TAU * M.CLK / step, 1), mtp_unit_busy=v["unit_busy"],
                    mtp_per_segment=v["per_segment"],
                    mu_step_cycles=u["cycles"], mu_per_user_tok_s=round(M.CLK / u["cycles"], 1),
                    mu_agg_tok_s=round(P4 * M.CLK / u["cycles"], 1), mu_unit_busy=u["unit_busy"],
                    mu_per_segment=u["per_segment"])
                if "phys" in v:
                    row["VM"][vm]["phys_sm4_latency_cycles_charged"] = dict(
                        mtp=v["phys"]["sm4_latency_cycles_charged"], mu=u["phys"]["sm4_latency_cycles_charged"])
            g["II"][ii] = row
        return g
    grid = {L: block("", L, IIS if not a.quick else ("250",)) for L in sorted({j[0] for j in J if len(j) == 5})}
    phys = {} if a.quick else {ph: {5: block(f"{ph}|", 5, PHYS_IIS)} for ph in PHYS}
    # self-check against the committed D1 / Phase-1 records
    R = M.ROOT
    d1 = json.loads((R / "results/arch/hbm_mtp_next_1018/model/run.json").read_text())["runs"]
    chk = [("D1 AR", grid[4]["ar_cycles"], d1["ds|AR"]["cycles"]),
           ("D1 MTP P4 verify", grid[4]["II"]["250"]["VM"]["grown"]["mtp_verify_cycles"], d1["ds|MTP|P4"]["cycles"]),
           ("D1 MU P4", grid[4]["II"]["250"]["VM"]["grown"]["mu_step_cycles"], d1["ds|MU|P4"]["cycles"])]
    if not a.quick:
        cl = json.loads((R / "results/arch/hbm_next_1019/runs/coll_lanes.json").read_text())["by_lanes"]["5"]
        hc = json.loads((R / "results/arch/hbm_next_1019/runs/hc_ii.json").read_text())["cases"]["II4385"]["4"]
        vmc = json.loads((R / "results/arch/hbm_next_1019/runs/vm_cap.json").read_text())["P"]["4"]
        chk += [("P1 coll L5 AR", grid[5]["ar_cycles"], cl["ds_ar_cycles"]),
                ("P1 coll L5 MTP P4 verify", grid[5]["II"]["250"]["VM"]["grown"]["mtp_verify_cycles"],
                 cl["P"]["4"]["mtp_verify_cycles"]),
                ("P1 coll L5 MU P4", grid[5]["II"]["250"]["VM"]["grown"]["mu_step_cycles"], cl["P"]["4"]["mu_step_cycles"]),
                ("P1 hc II4385 MTP P4 verify", grid[4]["II"]["4385"]["VM"]["grown"]["mtp_verify_cycles"],
                 hc["mtp_verify_cycles"]),
                ("P1 hc II4385 MU P4", grid[4]["II"]["4385"]["VM"]["grown"]["mu_step_cycles"], hc["mu_step_cycles"]),
                ("P1 vm asbuilt MTP P4 verify", grid[4]["II"]["250"]["VM"]["asbuilt"]["mtp_verify_cycles"],
                 vmc["mtp_noVM_verify"]),
                ("P1 vm asbuilt MU P4", grid[4]["II"]["250"]["VM"]["asbuilt"]["mu_step_cycles"], vmc["mu_noVM_cycles"])]
    checks = [dict(name=n, got=g_, ref=r_, ok=abs(g_ - r_) < 0.05) for n, g_, r_ in chk]
    out = dict(schema="opentallas.hbm_next_1019.veh.compose_grid.v1", lane="HBM-NEXT-VEH", rule=__doc__,
               model="tools/hgi_sim/hbm_plane_model.py (D1, unchanged)", stats=str(stats), clk_hz=M.CLK, tau=M.TAU,
               wall_s=round(time.time() - t0, 1), self_check=checks, self_check_pass=all(c["ok"] for c in checks),
               grid=grid, phys=phys)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "compose_grid.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    for c in checks:
        print(("OK  " if c["ok"] else "FAIL"), c["name"], c["got"], c["ref"], flush=True)
    for tag, gg in [("d4g-phys", grid)] + [(ph, x) for ph, x in phys.items()]:
      for L, g in gg.items():
        for ii, row in g["II"].items():
            for vm, r in row["VM"].items():
                print(f"{tag} L{L} II{ii} {vm}: AR {g['ar_tok_s']} MTP {r['ds_mtp_tok_s']} MU {r['mu_agg_tok_s']} / "
                      f"{r['mu_per_user_tok_s']}", flush=True)
    return 0 if out["self_check_pass"] else 3


if __name__ == "__main__":
    sys.exit(main())
