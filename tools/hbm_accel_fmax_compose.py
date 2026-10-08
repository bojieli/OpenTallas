#!/usr/bin/env python3
"""Recompose the DS HBM accelerator 1M AR (position 1,048,575) rate with every domain at 1.2 GHz, from measured
components: the baseline's executed program + SM table (results/rtl/dshbm_baseline_measured_20261004), the SU chain
cycles re-measured at the 1.2 GHz-closing MLAT/ALAT (--su), the attention tile cycles of the 1.2 GHz-closing tile
build (--tile128/--tile640), optional new SM real-op record (--sm, overrides rows of the same shape) and barrier
cycles. The pricing walk is tools/dshbm_baseline_measure.compose_program unchanged; only clocks/cycle tables move.
Model-priced pieces stay flagged (they are the baseline's own unvalidated terms)."""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dshbm_baseline_measure as B  # noqa: E402
import w19_hbm_token_compose as WC  # noqa: E402

BASE = ROOT / "results/rtl/dshbm_baseline_measured_20261004"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--su", default=str(BASE / "su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_v2.json"))
    ap.add_argument("--sm", default=None, help="sm_real_ops record of the 1.2 GHz SM element (default: baseline's)")
    ap.add_argument("--tile128", type=int, default=B.ATT_TILE[128])
    ap.add_argument("--tile640", type=int, default=B.ATT_TILE[640])
    ap.add_argument("--barrier-cycles", type=int, default=B.BARRIER_CYC)
    ap.add_argument("--f-sm", type=float, default=1.2e9)
    ap.add_argument("--f-ser", type=float, default=1.2e9)
    ap.add_argument("--label", default="")
    ap.add_argument("--record", required=True)
    a = ap.parse_args()
    B.ATT_TILE = {128: a.tile128, 640: a.tile640}
    B.BARRIER_CYC = a.barrier_cycles
    B.F_SER = a.f_ser                       # also the quantiser-price factor F_FAST / F_SER inside price_local
    prog = json.loads((BASE / "program.json").read_text())
    sm_recs = [json.loads((ROOT / "results/rtl/w19_sm_real_ops.json").read_text()),
               json.loads((BASE / "sm_real_ops.json").read_text())]
    if a.sm:
        sm_recs.append(json.loads(Path(a.sm).read_text()))
    sm = WC.SMTable(sm_recs, "ar")
    su = B.su_table(json.loads(Path(a.su).read_text()))
    coll = WC.w15_prod(json.loads((ROOT / "results/rtl/w15_hbm_nvls.json").read_text()), "hbm_p48_ss")
    coll["select_cycles"] = 419
    sw = ("tomahawk_ultra_protocol", "board")
    r = B.compose_program(prog=prog, sm=sm, coll=coll, su=su, WC=WC, f_sm=a.f_sm, f_ser=a.f_ser, switch=sw)
    rec = dict(schema="opentallas.hbm_accel.fmax_compose.v1", label=a.label, switch=B.HEADLINE_SWITCH,
               position=1048575, f_sm_hz=a.f_sm, f_ser_hz=a.f_ser, barrier_cycles=a.barrier_cycles,
               attention_tile_cycles=B.ATT_TILE, su_record=a.su, sm_record=a.sm, su_chain_cycles=su,
               tokens_s=r["tokens_s"], total_us=r["total_us"], parts_us=r["parts_us"], flags=r["flags"],
               local_by_fn_us=r["local_by_fn_us"], layers=r["layers"])
    Path(a.record).parent.mkdir(parents=True, exist_ok=True)
    Path(a.record).write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print(a.label, r["tokens_s"], r["total_us"], r["parts_us"])


if __name__ == "__main__":
    main()
