#!/usr/bin/env python3
"""HBM-P7-TOK 10-23: substitute the over-cap leaf-split twins (physical/die_plan/hbm/over_cap_split/index.json) into
the r18h5 land-direct slice bundle (TOKg 11:09 vehicle).  Pinned r18h5 RTL is kept byte-exact (the scoped_d4g families
stay as built); each twin is appended to its master's source with the family's scope renames applied to the pinned
modules it instantiates, the twin top renamed to the die master name and the pinned top renamed <master>_pinned.
    subst_split.py --bundle BUNDLE --wt WORKTREE
Substitutions:
  sfu     ot_hgi_sfu_core_split3      <- ot_hgi_sfu_core_split3_sp2 (sfu_sp2/*: store-side pin regs, +3)
  hc      ot_hbm_hc_root_static       <- ot_hbm_hc_root_static_s (tail_unit_s, sinkhorn_s: +7 per HC tail result)
  pgslice ot_hbm_su_static_pgslice_lg <- ot_hbm_su_static_pgslice_lg_s (PIN_REG 1 default, side_s; side MLAT/ALAT kept
          as the r18h5 die passes them: side_s/pgslice_s patched to propagate MLAT/ALAT as the scoped r18h5 side does)
  tkm     ot_hgi_coll_tkm_m_tp192     <- ot_hgi_coll_tkm_m instantiates ot_hgi_coll_tkm_static_p #(PIPE 1) (+2)
  coll    ot_hfd_coll_q3_hard_v8x/q2  <- body u_reduce = ot_hgi_coll_reduce_static_pr (+1 AR reduce publication)
"""
import argparse, json, re
from pathlib import Path

FAM = {
    "sfu": ("ot_hgi_sfu_core_split3", "ot_hgi_sfu_core_split3_sp2",
            sorted(str(p) for p in Path("rtl/hbm_accel/generic/peers/sfu_sp2").glob("*.sv")) if False else None),
    "hc": ("ot_hbm_hc_root_static", "ot_hbm_hc_root_static_s",
           ["rtl/hdc/v41/ot_hdc_sinkhorn_s.sv", "rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_tail_static_s.sv",
            "rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_tail_unit_static_s.sv",
            "rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_root_static_s.sv"]),
    "pgslice": ("ot_hbm_su_static_pgslice_lg", "ot_hbm_su_static_pgslice_lg_s",
                ["rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side_s.sv",
                 "rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pgslice_s.sv",
                 "rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pgslice_lg_s.sv"]),
}


def sub1(t, old, new, what):
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"PATCH_FAIL {what}: {n} matches for {old[:80]!r}")
    return t.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--wt", required=True)
    a = ap.parse_args()
    B, W = Path(a.bundle), Path(a.wt)
    mf = json.loads((B / "master_files.json").read_text())
    FAM["sfu"] = (FAM["sfu"][0], FAM["sfu"][1],
                  sorted(str(p.relative_to(W)) for p in (W / "rtl/hbm_accel/generic/peers/sfu_sp2").glob("*.sv")))
    rec = {}
    for fam, (master, twin, files) in FAM.items():
        sp = f"rtl/hbm_accel/die_glue/scoped_d4g/{fam}.sv"
        S = (B / sp).read_text()
        suf = "__d4g_" + fam
        scoped = set(re.findall(r"\bmodule\s+(\w+)" + re.escape(suf) + r"\b", S))
        S2, n = re.subn(r"\bmodule\s+" + master + r"\b", f"module {master}_pinned", S)
        assert n == 1, (fam, n)
        parts = [S2]
        for f in files:
            t = (W / f).read_text()
            if fam == "pgslice" and f.endswith("ot_hbm_su_static_side_s.sv"):
                t = sub1(t, "module ot_hbm_su_static_side_s #(parameter integer MUT=0, parameter integer SMUT=0)",
                         "module ot_hbm_su_static_side_s #(parameter integer MUT=0, parameter integer SMUT=0, MLAT=3, ALAT=3)",
                         "side_s params")
                t = sub1(t, "    localparam integer MLAT=3, ALAT=3;\n", "", "side_s localparam")
            if fam == "pgslice" and f.endswith("ot_hbm_su_static_pgslice_s.sv"):
                t = sub1(t, "ot_hbm_su_static_side_s #(.SMUT(SMUT)) u_side(",
                         "ot_hbm_su_static_side_s #(.SMUT(SMUT), .MLAT(MLAT), .ALAT(ALAT)) u_side(", "pgslice_s side")
            t = re.sub(r"\b[A-Za-z_]\w*\b", lambda x: x[0] + suf if x[0] in scoped else x[0], t)
            t, n = re.subn(r"\bmodule\s+" + twin + r"\b", f"module {master}", t)
            if f.endswith(twin + ".sv") and n != 1:
                raise SystemExit(f"twin top {twin} not renamed in {f}")
            parts.append(f"// HBM-P7-TOK split twin source: {f} (scope {suf} applied to pinned children)\n" + t + "\n")
        out = f"rtl/hbm_accel/die_glue/scoped_d4g/{fam}_split.sv"
        (B / out).write_text("".join(parts))
        lst = mf[master]
        assert sp in lst, (master, sp)
        mf[master] = [out if x == sp else x for x in lst]
        rec[master] = dict(twin=twin, source=out, twin_files=files)
    # TKM: PIPE 1 twin of ot_hgi_coll_tkm_static inside ot_hgi_coll_tkm_m (the tp192 master's child)
    v5 = "rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_hard_v5.sv"
    t = (B / v5).read_text()
    t = sub1(t, " ot_hgi_coll_tkm_static #(.TP(TP)) u(.clk(clk)", " ot_hgi_coll_tkm_static_p #(.TP(TP),.PIPE(1)) u(.clk(clk)", "tkm")
    v5s = v5.replace(".sv", "_tkmp.sv")
    (B / v5s).write_text(t)
    tkp = "rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static_p.sv"
    (B / tkp).parent.mkdir(parents=True, exist_ok=True)
    (B / tkp).write_text((W / tkp).read_text())
    m = "ot_hgi_coll_tkm_m_tp192"
    mf[m] = [v5s if x == v5 else x for x in mf[m]] + [tkp]
    rec[m] = dict(twin="ot_hgi_coll_tkm_static_p #(PIPE 1)", source=v5s, twin_files=[tkp])
    # COLL: reduce_pr in the shared q2/q3 v8g body
    v8 = "rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_hard_v8g.sv"
    t = (B / v8).read_text()
    t = sub1(t, " ot_hgi_coll_reduce_static u_reduce(", " ot_hgi_coll_reduce_static_pr u_reduce(", "coll reduce")
    v8s = v8.replace(".sv", "_pr.sv")
    (B / v8s).write_text(t)
    rpr = "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_reduce_static_pr.sv"
    (B / rpr).write_text((W / rpr).read_text())
    for m in ("ot_hfd_coll_q3_hard_v8x", "ot_hfd_coll_q2_hard_v8g"):
        if m in mf:
            mf[m] = [v8s if x == v8 else x for x in mf[m]] + [rpr]
            rec[m] = dict(twin="u_reduce = ot_hgi_coll_reduce_static_pr", source=v8s, twin_files=[rpr])
    (B / "master_files.json").write_text(json.dumps(mf, indent=1) + "\n")
    (B / "split_subst.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("SUBST_OK", ", ".join(rec))


if __name__ == "__main__":
    main()
