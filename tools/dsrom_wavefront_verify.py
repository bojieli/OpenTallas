#!/usr/bin/env python3
"""DS-ROM wavefront verify (model only; read-only on tools/uarch_model.py and committed records).

`run`: cons_v41_rom(S, 8, 36, ...) with the return-storage study's settings (dsrom_return_storage_hbm.py run, 4 stacks)
at 1M and 200K, capturing what the public result drops: the AR and verify-pass critical paths (T1, Tp), the per-stage
issue occupancy (field/hub, AR and verify pass), the per-stage critical-path windows, and the per-die energy categories.
S = 58 (the record's run) and S = 73 (scenario C's stage count).  Writes raw.json.
`compose`: wavefront verify priced on scenario C -> model.json.
"""
import copy, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "results/uarch/dsrom_wavefront_verify_20261003"
CTXS = (1048576, 200000)


def run():
    import uarch_model as u
    cap = json.loads((ROOT / "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json").read_text())
    rows = {r["stages"]: r for r in cap["all_stage_capacity_rows"]}
    saved = copy.deepcopy(u.PRESETS["proposal"])
    rec = []
    o_adj, o_occ, o_win, o_led = u._cons_adjust, u._cons_occupancy, u._cons_windows, u.v41_rom_ledger
    def w(tag, f):
        def g(*a, **k):
            r = f(*a, **k); rec.append((tag, r)); return r
        return g
    u._cons_adjust, u._cons_occupancy, u._cons_windows, u.v41_rom_ledger = (
        w("adj", o_adj), w("occ", o_occ), w("win", o_win), w("led", o_led))
    raw = {}
    try:
        for S in (58, 73):
            for ctx in CTXS:
                rec.clear(); t0 = time.time()
                u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * rows[58]["BF16_pairs_per_die"]   # the S58 die (as the record)
                u.PRESETS["proposal"]["idx_reader_Bpc"] = 4 * 750
                with u._cons_ctx(ctx):
                    p = u.cons_v41_rom(S, 8, 36, bf16="columns", clock_hz=u.PRODUCT_CLOCK_HZ,
                                       field_concurrency=u.FIELD_CONCURRENCY,
                                       added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT),
                                       dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, "w18"), elem_stages=8,
                                       ss_wire=True, serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM,
                                       vmh=u.VMC_FUSED, hub_block=u.PRODUCT_HUB)
                u.PRESETS["proposal"].clear(); u.PRESETS["proposal"].update(copy.deepcopy(saved))
                adj = [r for t, r in rec if t == "adj"]; occ = [r for t, r in rec if t == "occ"]
                win = [r for t, r in rec if t == "win"]; led = [r for t, r in rec if t == "led"][0]
                us = lambda dct: {str(s): {k: round(x * 1e6, 4) for k, x in v.items()} if isinstance(v, dict) else round(v * 1e6, 4)
                                  for s, v in dct.items()}
                raw[f"S{S}/{ctx}"] = dict(
                    S=S, ctx=ctx, ar_tokens_s=p["ar_tokens_s_b1"], mtp_tokens_s=p["mtp_tokens_s_b1"],
                    ar_sat=p["ar_saturated_tokens_s"], mtp_sat=p["mtp_saturated_tokens_s"],
                    busiest=str(p["busiest_stage"]), busiest_us=p["busiest_stage_us"],
                    T1_us=round(adj[0] * 1e6, 3), Tp_us=round(adj[1] * 1e6, 3),
                    occ_ar_us=us(occ[0]), occ_verify_us=us(occ[1]),
                    win_ar_us=us(win[0][0]), win_verify_us=us(win[1][0]),
                    per_die_categories_J=led["per_die_categories_J"], energy=p["energy"],
                    tp=u.V41_TP, dyn_scale=u.PRODUCT_DYN_SCALE, draft_fraction=u.V41_DRAFT_FRACTION,
                    tau=u.V41_TAU, positions=u.V41_POSITIONS, wall_s=round(time.time() - t0, 1))
                print(S, ctx, raw[f"S{S}/{ctx}"]["ar_tokens_s"], raw[f"S{S}/{ctx}"]["T1_us"], raw[f"S{S}/{ctx}"]["Tp_us"], flush=True)
    finally:
        u._cons_adjust, u._cons_occupancy, u._cons_windows, u.v41_rom_ledger = o_adj, o_occ, o_win, o_led
        u.PRESETS["proposal"].clear(); u.PRESETS["proposal"].update(saved)
    import subprocess
    raw["model_git"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    (OUT / "raw.json").write_text(json.dumps(raw, indent=1))


# ------------------------------------------------------------------------------------------------ compose
RS = "results/uarch/dsrom_return_storage_hbm_20261003/model.json"   # ba4dc1a18 scenario C (this branch's base)
DRAFT_OVER_AR = 0.1173        # the scenario C composition's draft (dsrom_return_storage_hbm.py)
TAUS = (3.649, 4.0)
HBM_ACCEL = dict(ar=3015.2, mtp_tau3649=6001.1, mtp_tau4=6579.0,
                 src="a3ed9c36d:results/uarch/hbm_accelerator_study_20261003/ladder.json compare.ds[1]")
# m sweep, isopower history 8bb540cd1 dsrom_isopower_history.md (verify/AR at S58; dies at reticle-full lower..upper area)
M_SWEEP = {1: dict(ver_over_ar=2.35, dies_rel=(1.0, 1.0)), 2: dict(ver_over_ar=1.80, dies_rel=(1.0, 548 / 508)),
           3: dict(ver_over_ar=1.62, dies_rel=(572 / 508, 676 / 508)), 6: dict(ver_over_ar=1.43, dies_rel=(796 / 508, 1044 / 508))}
P = 6
CTXK = ("1048576", "200000")


def compose():
    raw = json.loads((OUT / "raw.json").read_text())
    rs = json.loads((ROOT / RS).read_text())
    C = next(r for r in rs["scenarios"] if r["scenario"] == "C: A + B")
    out = dict(schema="dsrom_wavefront_verify/1", base=dict(record=RS, branch_base="ba4dc1a18", model_git=raw["model_git"]))
    # ---- (1) how the m = 1 verify pass is composed
    q1 = {}
    for k in ("S58/1048576", "S73/1048576", "S73/200000"):
        x = raw[k]
        tot = {s: v["field"] + v["hub"] for s, v in x["occ_ar_us"].items()}
        issue_path = (x["Tp_us"] - x["T1_us"]) / (P - 1)
        q1[k] = dict(T1_us=x["T1_us"], Tp_us=x["Tp_us"], ratio=round(x["Tp_us"] / x["T1_us"], 3),
                     critical_path_issue_us=round(issue_path, 1),
                     latency_us=round(x["T1_us"] - issue_path, 1),
                     max_stage_occupancy_us=round(max(tot.values()), 2), max_stage_occupancy_at=max(tot, key=tot.get),
                     max_stage_window_us=round(max(x["win_ar_us"].values()), 2),
                     max_stage_window_at=max(x["win_ar_us"], key=x["win_ar_us"].get),
                     second_occupancy=sorted(((s, round(v, 2)) for s, v in tot.items()), key=lambda kv: -kv[1])[1])
    out["q1_pass_composition"] = dict(
        rows=q1,
        reading="v41_verify_T / _v41_graph: every node's issue is multiplied by p (lane nodes by ceil(p/m)) and the "
                "graph is re-solved, so each node finishes all 6 positions before its successor starts. Fill, wires, "
                "hops and dependency latency are paid once; the issue of EVERY node on the critical path is paid p "
                "times. Verify = T1 + (p-1) x (critical-path issue). While one stage works on 6 positions, the other "
                "72 stages idle (for this user). It is not p x AR: ~73% of AR is latency, shared already.")
    # ---- (2) wavefront on scenario C
    rows = {}
    for ctx in CTXK:
        ar_us = 1e6 / C["ctx"][ctx]["ar"]
        rec_ver = ar_us * 0 + (4e6 / C["ctx"][ctx]["mtp_tau4"] - DRAFT_OVER_AR * ar_us)
        x = raw[f"S73/{ctx}"]
        tot = {s: v["field"] + v["hub"] for s, v in x["occ_ar_us"].items()}
        tot_v = {s: v["field"] + v["hub"] for s, v in x["occ_verify_us"].items()}
        ii = dict(occupancy=max(tot.values()), window=max(x["win_ar_us"].values()),
                  occupancy_head_doubled=max([v for s, v in tot.items() if s != "head"] + [tot["head"] / 2]))
        td = DRAFT_OVER_AR * ar_us
        r = dict(ar_us=round(ar_us, 2), ar_tok_s=C["ctx"][ctx]["ar"], draft_us=round(td, 2),
                 pass_m1=dict(verify_us=round(rec_ver, 2), ratio=round(rec_ver / ar_us, 3),
                              **{f"mtp_tau{t}": round(t * 1e6 / (rec_ver + td), 1) for t in TAUS}))
        for rule, v in ii.items():
            ver = ar_us + (P - 1) * v
            r[f"wavefront_{rule}"] = dict(ii_us=round(v, 2), verify_us=round(ver, 2), ratio=round(ver / ar_us, 3),
                                         **{f"mtp_tau{t}": round(t * 1e6 / (ver + td), 1) for t in TAUS})
            r[f"wavefront_{rule}"]["vs_hbm_tau3649"] = round(r[f"wavefront_{rule}"]["mtp_tau3.649"] / HBM_ACCEL["mtp_tau3649"], 3)
            r[f"wavefront_{rule}"]["vs_hbm_tau4"] = round(r[f"wavefront_{rule}"]["mtp_tau4.0"] / HBM_ACCEL["mtp_tau4"], 3)
        # saturated: per-stage occupancy per verify step (6 positions, keys re-read per position) + draft on head
        wf_occ = {s: P * v for s, v in tot.items()}
        wf_occ["head"] += x["draft_fraction"] * x["T1_us"]     # the model's own draft placement (cons_v41_rom)
        r["saturated"] = dict(pass_mtp_tok_s=x["mtp_sat"], wavefront_mtp_tok_s=round(3.649e6 / max(wf_occ.values()), 1),
                              pass_busiest_us=round(max(tot_v.values()), 2), wavefront_busiest_us=round(max(wf_occ.values()), 2),
                              busiest=max(wf_occ, key=wf_occ.get))
        # energy: the pass reads index keys once (hbm_if + stack once a pass); the wavefront reads them per position
        import uarch_model as u
        cats = x["per_die_categories_J"]; tp = x["tp"]
        kv_rows = tp * 40 * 640 * u.A.WIN_ROW_B / 4 * u.E_HBM_B
        extra_pass_J = (P - 1) * (tp * (cats["hbm_if"] + cats["stack"]) - kv_rows)
        base_m = rs["scenario_c"] and None
        r["energy"] = dict(extra_mJ_per_pass=round(extra_pass_J * 1e3, 2), extra_mJ_per_emitted_token=round(extra_pass_J * 1e3 / 3.649, 2),
                           basis="(p-1) x TP x (hbm_if + stack) per-die categories, minus the per-position KV rows the "
                                 "pass already charges (MTP_KV_PER_POSITION); i.e. index keys read once per position")
        rows[ctx] = r
    out["q2_wavefront_scenario_c"] = rows
    out["q2_rules"] = dict(
        occupancy="II = the slowest stage's per-position issue occupancy (field + hub), the same rule the model uses for "
                  "multi-user saturation (two tokens may be in one stage on different nodes). Slowest = the LM head "
                  "(8 head dies), 12.37 us; next is the L20-scan stage at 11.62 us (1M) / 4.51 us (200K).",
        window="II = the slowest stage's critical-path window (one position per stage at a time; no intra-stage "
               "overlap): 19.24 us (1M, stage 36) / 15.42 us (200K, head).",
        occupancy_head_doubled="head dies 8 -> 16: II falls only to the next stage (11.62 us at 1M) -- not worth it at 1M.")
    # ---- (3) m sweep on C
    ms = {}
    for ctx in CTXK:
        ar_us = 1e6 / C["ctx"][ctx]["ar"]; td = DRAFT_OVER_AR * ar_us
        ms[ctx] = {f"m{m}": dict(ver_over_ar=v["ver_over_ar"], dies_rel_to_m1=[round(x, 2) for x in v["dies_rel"]],
                                 **{f"mtp_tau{t}": round(t * 1e6 / (v["ver_over_ar"] * ar_us + td), 1) for t in TAUS})
                   for m, v in M_SWEEP.items()}
        ms[ctx]["wavefront_m1_occupancy"] = dict(ver_over_ar=rows[ctx]["wavefront_occupancy"]["ratio"], dies_rel_to_m1=[1.0, 1.0],
                                                 **{f"mtp_tau{t}": rows[ctx]["wavefront_occupancy"][f"mtp_tau{t}"] for t in TAUS})
    out["q3_m_sweep_on_c"] = dict(rows=ms, basis="verify/AR from the S58 m sweep (8bb540cd1) applied to scenario C's AR; "
                                  "added stages for m >= 2 ignored (upper bound for m >= 2).")
    out["hbm_accelerator"] = HBM_ACCEL
    (OUT / "model.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    run() if sys.argv[1] == "run" else compose()
