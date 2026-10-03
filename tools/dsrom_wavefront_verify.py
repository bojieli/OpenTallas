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


if __name__ == "__main__":
    {"run": run}.get(sys.argv[1], lambda: None)() if sys.argv[1] == "run" else __import__(__name__).compose()
