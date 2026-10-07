#!/usr/bin/env python3
"""HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): the stream unit's exact benches on the c12 build.

The c12 build is the f12 build (MLAT 6 multipliers, f12 adders) with the routed failing classes fixed:
  rtl/hdc/ot_hdc_fastfp_lat_c12.sv        ALAT 6 -> ot_hdc_fp32_add_f12_l6x (DS ROM kit six-stage adder)
  rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv  registered memory-read ports, operand registers (OPR), kit divider (DDIV),
                                            lane 0's side registers (SIDEX)
  rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv  side pipe input / output / fault registers (SIDEX), fsqrt_c12 (FSQ)
  rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv       softplus with the kit divider and fsqrt_c12
  rtl/hdc/v41/ot_hdc_fsqrt_c12.sv           keep-prefix digit recurrence, precomputed finish (same depth)
  rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv   reducer registers (RPAD, RSL, RTAP)
  rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv       the controller with the matching depths
A thin driver over tools/rtl_hdc_v41x_vec_campaign.py (the unit's spec / random / vehicle campaign against the
golden reference) and tools/dshbm_baseline_measure.py (su-run: the DS HBM SU chains); both unchanged.  This file
swaps the source lists, sets the campaign's depth model to the c12 depths and EXITS NONZERO on any mismatch.

    python3 tools/hbm_su_c12.py campaign --quick --no-1024 --scratch W --out R.json          (bit-level units)
    python3 tools/hbm_su_c12.py su-run --out O --work W --bcast 7 --ret 8 --n 1024 --m 256 --fp dpi_beh \\
        --cases su_cases_v2_ildr.pkl                                                        (the composition's cycles)
    python3 tools/hbm_su_c12.py su-run ... --n 64 --m 16 --fp rtl ...                       (bit-level, N 64)
Common options (before the subcommand's own): --mlat 6 --alat 6 --opr 1 --ddiv 21 --sidex 3 --fsq 1
--rpad R --rsl S --rtap T --rslice W --gsh G --kimm K --denr D --dring R (defaults: the c12 build; gsh / kimm: CLAUDE HBM-ABSTRACTS
hub lane margin, default off).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

C12_UNITS = ["rtl/hdc/ot_hdc_fastfp_lat_c12.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/v41x/ot_dsrom_su_add6.sv",
             "rtl/hdc/v41x/ot_dsrom_su_f12.sv", "rtl/hdc/v41/ot_hdc_fsqrt_c12.sv"]
C12_UNITS_DPI = ["rtl/hdc/ot_hdc_fastfp_lat_c12.sv", "rtl/test/sim_hdc_fp32_f12_dpi_tops.sv",
                 "rtl/test/sim_dsrom_su_add6_dpi.sv", "rtl/hdc/v41x/ot_dsrom_su_f12.sv", "rtl/hdc/v41/ot_hdc_fsqrt_c12.sv"]
SWAP = {"rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv": ["rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv"],
        "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv": ["rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv"],
        "rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv": ["rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv"],
        "rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv": ["rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv"],
        "rtl/hdc/v41x/ot_hdc_v41x_vec.sv": ["rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv"]}
P = dict(mlat=6, alat=6, opr=1, ddiv=21, sidex=4, fsq=1, capr=1, rpad=1, rsl=2, rtap=1, rout=1, rslice=64, ctl12=1, gsh=0, kimm=0, denr=0, dring=0)


def take_params(argv):
    for k in list(P):
        f = f"--{k}"
        if f in argv:
            i = argv.index(f)
            P[k] = int(argv[i + 1])
            del argv[i:i + 2]
    # the campaign's / su-run's own --mlat / --alat must agree
    for k in ("mlat", "alat"):
        argv += [f"--{k}", str(P[k])]
    return argv


def set_c12(VC):
    """The campaign's depth model at the c12 depths (the formulas of ot_hdc_v41x_vec_c12.sv)."""
    I = VC.I
    m, a = P["mlat"], P["alat"]
    assert 3 <= a <= m <= 8, (m, a)
    VC.MLAT, VC.ALAT = m, a
    VC.D_FETCH, VC.D_FETCH_G = 4 + P["capr"], 6 + P["opr"] + P["capr"] + P["gsh"]
    VC.D_PRE = 1 + P["opr"]                  # the M1 operand register sits between PRE and M1
    VC.D_DIV = P["ddiv"]
    VC.D_OUT = 1 + P["opr"]                  # the E1 operand register (a constant stage on every element)
    VC.D_M1 = VC.D_STAGE = m
    VC.D_AD = a + P["opr"]
    VC.D_RSTEP = a
    VC.D_RED = 2 + m + 7 * a + P["rpad"] + P["rsl"] + P["rtap"] + P["rout"]
    d_exp = 7 * m + 8 * a + 4
    d_sig0 = d_exp + a + P["ddiv"]
    d_sig = d_sig0 + P["denr"]           # lane sigmoid / SiLU (DENR); the side pipe's gate keeps d_sig0
    sx = P["sidex"]
    VC.SFU_DEPTH = {I.SFU_NONE: 0, I.SFU_EXP: d_exp, I.SFU_SIGM: d_sig, I.SFU_SILU: d_sig,
                    I.SFU_RSQRT: 1 + 9 * m + 3 * a + sx, I.SFU_SQRT: 31 + sx,
                    I.SFU_SPSQRT: d_exp + 11 * m + 10 * a + 31 + P["ddiv"] + sx, I.SFU_EGATE: 1 + 31 + 1 + d_sig0 + sx}


def vflags():
    g = dict(OPR=P["opr"], DDIV=P["ddiv"], SIDEX=P["sidex"], FSQ=P["fsq"], CAPR=P["capr"], RPAD=P["rpad"], RSL=P["rsl"], ROUT=P["rout"], CTL12=P["ctl12"],
             RTAP=P["rtap"], RSLICE=P["rslice"], GSH=P["gsh"], KIMM=P["kimm"], DENR=P["denr"], DRING=P["dring"])
    return " ".join(f"-G{k}={v}" for k, v in g.items())


def apply(VC, dpi=False):
    units = C12_UNITS_DPI if dpi else C12_UNITS
    sw = dict(SWAP)
    sw["rtl/hdc/ot_hdc_fastfp_lat.sv"] = units
    for lst in (VC.RTL, VC.LIB):
        out = []
        for p in lst:
            r = str(Path(p).relative_to(ROOT))
            out += [ROOT / x for x in sw[r]] if r in sw else [p]
        lst[:] = out
    for p in VC.RTL + VC.LIB:
        assert p.is_file(), p
    VC.TB = ROOT / "rtl/test/tb_hdc_v41x_vec_c12.sv"
    VC.TB_SFU = ROOT / "rtl/test/tb_hdc_v41x_vec_sfu_c12.sv"
    os.environ["OT_VFLAGS"] = (os.environ.get("OT_VFLAGS", "") + " " + vflags()).strip()
    VC.set_mlat = lambda mlat, alat=3: set_c12(VC)
    set_c12(VC)
    print("c12 params", P, "OT_VFLAGS", os.environ["OT_VFLAGS"], flush=True)


def all_pass(rec):
    bad = []
    if "sfu_equivalence" in rec and not rec["sfu_equivalence"].get("pass_"):
        bad.append("sfu_equivalence")
    for k, rows in (rec.get("random") or {}).items():
        bad += [f"random {k} #{i}" for i, r in enumerate(rows) if not r.get("pass_")]
    for i, r in enumerate((rec.get("vehicle") or {}).get("batches", [])):
        if not r.get("pass_"):
            bad.append(f"vehicle #{i}")
    for k in ("perf_N64_M16", "perf_N1024_M256"):
        if k in rec:
            s = json.dumps(rec[k])
            if '"pass_": false' in s:
                bad.append(k)
    return bad


def cmd_compose(argv):
    """DS 1M AR / MTP with the c12 SU chain records in place of the m6a5 ones (same cases, same levers): the matched
    reference's rows corrected+wg+su12 and matched (+ fused SU chains), SU lanes at 1.2 GHz; every other term from
    the committed records (tools/dshbm_hbm_opt_compose.setup).  --c12-v2 / --c12-p6: the c12 su-run records."""
    import argparse
    import dshbm_hbm_opt_compose as OC
    import dshbm_chain_levers as CL
    import dshbm_baseline_measure as DM
    import dshbm_matched_reference as M
    import dshbm_1m_allmeasured as A
    ap = argparse.ArgumentParser()
    ap.add_argument("--c12-v2", type=Path, required=True)
    ap.add_argument("--c12-p6", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    S = OC.setup()
    ar0, mm0, _, _ = OC.gate_rows(S)
    s1 = CL.best_of([("dr", json.loads(a.c12_v2.read_text()))])
    s6 = CL.best_of([("dr", json.loads(a.c12_p6.read_text()))])
    assert all(DM.su_exact(c) for c in s1["chains"] + s6["chains"]), "c12 SU records not exact"
    c12 = (CL.su_table_overlap(s1), CL.su_table_overlap(s6))
    T12 = dict(A.TARGET, su=1.2e9, du_ser=M.F_SER)
    use = ("coll", "local", "hbm", "mixes")
    rows = {}
    for name, pair in (("m6a5", S["su12"]), ("c12", c12)):
        for fz_name, fz in (("corrected+wg+su12", None), ("matched", S["fused"])):
            t, _ = M.walk(S["prog"], S["smseq"], pair[0], S["coll"], S["local"], S["hbm"], P=1, clk=T12, use=use, wg=True,
                          fused=fz)
            mm, _ = M.mtp(S["prog"], S["smseq"], pair[1], S["coll"], S["local"], S["hbm"], T12, use, True, fz)
            rows[f"{fz_name}:{name}"] = dict(AR_us=round(t, 3), AR_tok_s=round(1e6 / t, 1), MTP_step_us=mm["step_us"],
                                             MTP_tok_s=mm["mtp_tok_s"])
    eff = {}
    for fz_name in ("corrected+wg+su12", "matched"):
        b, c = rows[f"{fz_name}:m6a5"], rows[f"{fz_name}:c12"]
        eff[fz_name] = dict(AR_us_delta=round(c["AR_us"] - b["AR_us"], 3),
                            AR_rate_pct=round(100 * (b["AR_us"] / c["AR_us"] - 1), 3),
                            MTP_step_us_delta=round(c["MTP_step_us"] - b["MTP_step_us"], 3),
                            MTP_rate_pct=round(100 * (c["MTP_tok_s"] / b["MTP_tok_s"] - 1), 3))
    chains = {c["chain"]: c.get("first_emit_to_last_write") for c in s1["chains"]}
    rec = dict(schema="opentallas.dshbm.su_c12_compose.v1", context=1048576, position=1048575,
               gate_reproduced=dict(AR_us=ar0, MTP_step_us=mm0["step_us"]), su_records=dict(
                   c12_v2=OC.rel(a.c12_v2), c12_v2_sha256=OC.sha(a.c12_v2), c12_p6=OC.rel(a.c12_p6),
                   c12_p6_sha256=OC.sha(a.c12_p6)), c12_params=dict(P), rows=rows, effect_c12_vs_m6a5=eff,
               c12_chain_spans_P1=chains)
    a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print(json.dumps(dict(rows=rows, effect=eff), indent=1))
    return 0


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "compose":
        return cmd_compose(argv[1:])
    cmd, argv = argv[0], take_params(argv[1:])
    import rtl_hdc_v41x_vec_campaign as VC
    if cmd == "campaign":
        apply(VC)
        out = Path(argv[argv.index("--out") + 1])
        sys.argv = [str(ROOT / "tools/rtl_hdc_v41x_vec_campaign.py")] + argv
        VC.main()
        rec = json.loads(out.read_text())
        rec["c12_params"] = dict(P)
        rec["c12_tool"] = "tools/hbm_su_c12.py"
        bad = all_pass(rec)
        rec["c12_all_pass"] = not bad
        rec["c12_failures"] = bad
        out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
        print("C12 CAMPAIGN", "PASS" if not bad else f"FAIL {bad}", flush=True)
        return 1 if bad else 0
    if cmd == "su-run":
        fp = argv[argv.index("--fp") + 1] if "--fp" in argv else "rtl"
        apply(VC, dpi=fp != "rtl")
        import runpy
        sys.argv = [str(ROOT / "tools/dshbm_baseline_measure.py"), "su-run"] + argv
        try:
            runpy.run_path(str(ROOT / "tools/dshbm_baseline_measure.py"), run_name="__main__")
        except SystemExit as e:
            rc = int(e.code or 0)
            print("C12 SU-RUN", "PASS" if rc == 0 else "FAIL", flush=True)
            return rc
        return 1
    print("unknown subcommand", cmd)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
