#!/usr/bin/env python3
"""hbm-fmax-su (2026-10-04): the DS HBM serial unit's chain benches at the 1.2 GHz depths.

A thin driver over tools/dshbm_baseline_measure.py (su-run / su-equiv, unchanged): with --f12 the RTL source list
takes the 1.2 GHz file swaps (rtl/hdc/ot_hdc_fastfp_lat_f12.sv + rtl/hdc/ot_hdc_fp32_f12.sv in place of
rtl/hdc/ot_hdc_fastfp_lat.sv; every --swap OLD=NEW likewise), so `--fp rtl` runs the bit-level units that close
0.833 ns.  The DPI runs (--fp dpi / dpi_beh) are latency-only stand-ins: their cycles depend on MLAT / ALAT /
BCAST / RET alone, so they are the same for either source list.

    python3 tools/su_fmax_measure.py su-run --out O --work W --bcast 7 --ret 8 --mlat 5 --alat 4 --n 1024 --m 256 \
        --fp dpi_beh --cases su_cases_v2.pkl
    python3 tools/su_fmax_measure.py su-run --f12 ... --n 64 --m 16 --fp rtl --cases su_cases_v2.pkl
    python3 tools/su_fmax_measure.py su-equiv --out O --su RTL.json,DPI.json --record EQ.json
    python3 tools/su_fmax_measure.py local --su BASE.json@0.9e9 --su NEW.json@1.2e9 [--record R.json]
        the local (serial-unit) term of the measured DS HBM baseline token (dshbm_baseline_measure.compose_program on
        results/rtl/dshbm_baseline_measured_20261004 program / SM tables, TU-protocol board switch, SM at 1.2 GHz)
        with each SU record priced at its serial clock (the model-priced quantiser / top-6 nodes scale with it)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

F12_SWAP = {"rtl/hdc/ot_hdc_fastfp_lat.sv": ["rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_f12.sv"],
            "rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv": ["rtl/hdc/v41x/ot_hdc_v41x_vec_lane_f12.sv"],
            "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv": ["rtl/hdc/v41x/ot_hdc_v41x_sfu_f12.sv"]}
# the DPI benches: the f12 unit tops as latency stand-ins (rtl/test/sim_hdc_fp32_f12_dpi_tops.sv)
F12_SWAP_DPI = {"rtl/hdc/ot_hdc_fastfp_lat.sv": ["rtl/hdc/ot_hdc_fastfp_lat_f12.sv",
                                                 "rtl/test/sim_hdc_fp32_f12_dpi_tops.sv"],
                "rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv": ["rtl/hdc/v41x/ot_hdc_v41x_vec_lane_f12.sv"],
                "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv": ["rtl/hdc/v41x/ot_hdc_v41x_sfu_f12.sv"]}


def set_mlat_f12(mlat, alat=3, VC=None):
    """rtl_hdc_v41x_vec_campaign.set_mlat's depths without its 3..5 / 3..4 range assert (the 1.2 GHz build runs MLAT 6 /
    ALAT 5 on the f12 lane, whose own range check is ALAT 3..7 <= MLAT); the same formulas, unchanged."""
    if VC is None:
        import rtl_hdc_v41x_vec_campaign as VC
    I = VC.I
    assert 3 <= alat <= mlat <= 8, (mlat, alat)
    VC.MLAT, VC.ALAT = mlat, alat
    VC.D_M1 = VC.D_STAGE = mlat
    VC.D_AD = alat
    VC.D_RSTEP = alat
    VC.D_RED = 2 + mlat + 7 * alat
    d_exp = 7 * mlat + 8 * alat + 4
    d_sig = d_exp + alat + 19
    VC.SFU_DEPTH = {I.SFU_NONE: 0, I.SFU_EXP: d_exp, I.SFU_SIGM: d_sig, I.SFU_SILU: d_sig,
                    I.SFU_RSQRT: 1 + 9 * mlat + 3 * alat, I.SFU_SQRT: 31,
                    I.SFU_SPSQRT: d_exp + 11 * mlat + 10 * alat + 50, I.SFU_EGATE: 1 + 31 + 1 + d_sig}


def apply_swaps(swaps):
    import rtl_hdc_v41x_vec_campaign as VC
    for lst in (VC.RTL, VC.LIB):
        out = []
        for p in lst:
            r = str(Path(p).relative_to(ROOT))
            out += [ROOT / x for x in swaps[r]] if r in swaps else [p]
        lst[:] = out
    for new in [x for v in swaps.values() for x in v]:
        assert (ROOT / new).is_file(), new


def cmd_local(argv):
    import argparse
    import json
    import dshbm_baseline_measure as DM
    import w19_hbm_token_compose as WC
    ap = argparse.ArgumentParser()
    ap.add_argument("--su", action="append", required=True, help="SU record @ serial clock in Hz")
    ap.add_argument("--base", default=str(ROOT / "results/rtl/dshbm_baseline_measured_20261004"))
    ap.add_argument("--record", default=None)
    a = ap.parse_args(argv)
    base = Path(a.base)
    prog = json.loads((base / "program.json").read_text())
    sm = WC.SMTable([json.loads((ROOT / "results/rtl/w19_sm_real_ops.json").read_text()),
                     json.loads((base / "sm_real_ops.json").read_text())], "ar")
    coll = WC.w15_prod(json.loads((ROOT / "results/rtl/w15_hbm_nvls.json").read_text()), "hbm_p48_ss")
    coll["select_cycles"] = 419
    rows = []
    for spec in a.su:
        path, f, *P = spec.split("@")          # path@clock[@positions]: P > 1 prices the MTP verify pass
        f = float(f)
        P = int(P[0]) if P else 1
        rec = json.loads(Path(path).read_text())
        su = DM.su_table(rec)
        f_old = DM.F_SER
        DM.F_SER = f                       # price_local scales the model-priced quantiser / top-6 by F_FAST / F_SER
        try:
            r = DM.compose_program(prog, sm, coll, su, WC, f_sm=DM.F_FAST, f_ser=f,
                                   switch=("tomahawk_ultra_protocol", "board"), P=P)
        finally:
            DM.F_SER = f_old
        rows.append(dict(positions=P, su=path, su_sha256=DM.sha(Path(path)), config=rec["config"], serial_clock_hz=f,
                         su_chain_cycles=su, local_us=r["parts_us"]["local"], parts_us=r["parts_us"],
                         tokens_s=r["tokens_s"], local_by_fn_us=r["local_by_fn_us"], flags=r["flags"]))
        print(f"{Path(path).name}  P{P} @{f / 1e9:.2f} GHz  local {r['parts_us']['local']:.2f} us  token {r['tokens_s']} tok/s "
              f"parts {r['parts_us']}")
    if a.record:
        Path(a.record).write_text(json.dumps(dict(schema="opentallas.rtl.su_fmax_local_term.v1", rows=rows),
                                             indent=1, default=float) + "\n")
    return 0


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "local":
        raise SystemExit(cmd_local(argv[1:]))
    swaps = {}
    if argv and argv[0] == "campaign-kr":
        # the fusion build's campaign (tools/rtl_hdc_v41x_vec_kr_campaign.py) on the 1.2 GHz sources
        import rtl_hdc_v41x_vec_kr_campaign as KC
        sw = {"rtl/hdc/ot_hdc_fastfp_lat.sv": F12_SWAP["rtl/hdc/ot_hdc_fastfp_lat.sv"],
              "rtl/hdc/v41x/ot_hdc_v41x_vec_lane_kr.sv": ["rtl/hdc/v41x/ot_hdc_v41x_vec_lane_kr_f12.sv"],
              "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv": ["rtl/hdc/v41x/ot_hdc_v41x_sfu_f12.sv"]}
        for lst in (KC.RTL, KC.LIB):
            lst[:] = [ROOT / x for p in lst for x in (sw.get(str(Path(p).relative_to(ROOT)), [str(Path(p).relative_to(ROOT))]))]
        KC.set_mlat = lambda m, a=3: set_mlat_f12(m, a, KC)
        KC.TB_SFU = ROOT / "rtl/test/tb_hdc_v41x_vec_sfu_f12.sv"
        print("source swaps:", sw, flush=True)
        sys.argv = [str(ROOT / "tools/rtl_hdc_v41x_vec_kr_campaign.py")] + argv[1:]
        raise SystemExit(KC.main())
    if "--f12" in argv:
        argv.remove("--f12")
        fp = argv[argv.index("--fp") + 1] if "--fp" in argv else "rtl"
        swaps.update(F12_SWAP if fp == "rtl" else F12_SWAP_DPI)
        import rtl_hdc_v41x_vec_campaign as VC
        VC.set_mlat = set_mlat_f12
    while "--swap" in argv:
        i = argv.index("--swap")
        old, new = argv[i + 1].split("=", 1)
        swaps.setdefault(old, []).extend(new.split(","))
        del argv[i:i + 2]
    if swaps:
        apply_swaps(swaps)
        print("source swaps:", {k: v for k, v in swaps.items()}, flush=True)
    import runpy
    if argv and argv[0] == "campaign":
        # the unit's own spec / op-type campaign (tools/rtl_hdc_v41x_vec_campaign.py, the ROM designs' bench) on the
        # swapped sources: python3 tools/su_fmax_measure.py campaign --f12 --mlat 6 --alat 5 [--quick] --out R.json
        import rtl_hdc_v41x_vec_campaign as VC
        VC.TB_SFU = ROOT / "rtl/test/tb_hdc_v41x_vec_sfu_f12.sv"
        sys.argv = [str(ROOT / "tools/rtl_hdc_v41x_vec_campaign.py")] + argv[1:]
        raise SystemExit(VC.main())
    sys.argv = [str(ROOT / "tools/dshbm_baseline_measure.py")] + argv
    runpy.run_path(str(ROOT / "tools/dshbm_baseline_measure.py"), run_name="__main__")


if __name__ == "__main__":
    main()
