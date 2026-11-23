#!/usr/bin/env python3
"""SVC-BCAST-STAGE lock-step proof (rc16, 11-23): the svc engine (ot_s81_svc_attn_s, dsdv_svc_att configuration, S81
H8 head-core tile with --hcore) built as built and with -DOT_SVC_BCAST (TREP 1: per-tile kept copies of the tile load /
issue controls + per-tile reset relays) must produce every score / P.V beat and accept every job / q / kv / p word on the
SAME cycle with the same data (shift 0, strict lock-step), with the bank-set checker clean.  Negative control
-DOT_SVC_BCAST -DOT_SVC_TREP_MUT (tile 0's issue valid one edge late) must break the data.  Reuses the vectors, harness,
run and compare of svc_srx_lockstep.py (same directory).
Usage: svc_bcast_lockstep.py --root <repo> --work <dir> [--srx N] [--hcore] [--rt2-calendar]
"""
import argparse, json, os, shlex, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parent))
import svc_srx_lockstep as L   # noqa: E402


def build(a, variant, nkv, np_):
    defs = {"ref": [], "bcast": ["+define+OT_SVC_BCAST"], "mut": ["+define+OT_SVC_BCAST", "+define+OT_SVC_TREP_MUT"]}[variant]
    tag = f"bcast_{variant}_srx{a.srx}" + ("_hc" if a.hcore else "") + ("_t" if a.srxt else "") + (f"_ns{a.nstage}" if a.nstage != 2 else "")
    if (a.work / f"build_{tag}.rc").is_file() and (a.work / f"build_{tag}.rc").read_text().strip() == "0":
        return tag
    prm = dict(L.P, NSTAGE=a.nstage, SRX=a.srx, SRXMUT=0, NJOBMAX=len(L.TS), NKV=nkv, NP=np_, NSC=1, NPV=1, MAXCYC=400000)
    if a.srx and a.srxt:
        prm["SRXT"] = f"1024'h{a.srxt}"
    r = "/work/root"
    ys = ["rtl/hdc/v41x", "rtl/hdc", "rtl/dsrom_sys/s81_svc", "rtl/dsrom_sys/s81_dv"]
    files = ["rtl/hdc/v41x/ot_hdc_v41x_kreg.sv", "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv",
             "rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
             "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv"]
    if a.hcore:
        files += ["rtl/hdc/v41x/ot_s81c_attn_hcore.sv", "rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv", "rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv",
                  "rtl/hdc/v41x/ot_dsrom_su_add6.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/v41x/ot_dsrom_su_f12.sv",
                  "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv"]
    files += ["rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv", "rtl/dsrom_sys/s81_dv/ot_s81_svc_merge_h4.sv",
              "rtl/dsrom_sys/s81_svc/ot_s81_svc_band.sv"]
    cmd = ["verilator", "--cc", "--exe", "--build", "-j", "16", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "-Wno-MULTIDRIVEN", "--top-module", "tb_hdc_v41x_attn", "--prefix", "Vtb", "-Mdir",
           f"/work/out/obj_{tag}", "+define+OT_ATTN_SETCHECK", "+define+SRX_DUT_S81", "+define+OT_SVC_MERGE_H4", *defs,
           *(["+define+OT_ATTN_HCORE", "+define+OT_S81C_HCORE_CTLA", "+define+OT_S81C_HCORE_RST_TIMED", "+define+OT_SVC_H8",
              "+define+OT_SVC_H8_REUSE_RT2"] if a.hcore else []),
           *(["+define+OT_SVC_NATIVE_RT2_CALENDAR"] if a.rt2_calendar else []),
           *[x for y in ys for x in ("-y", f"{r}/{y}")],
           *[f"-G{k}={v}" for k, v in prm.items()], *[f"{r}/{f}" for f in files],
           f"{r}/rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_srx_attn.sv", f"{r}/rtl/test/hdc_v41_harness.cpp",
           "--x-assign", "fast", "--x-initial", "fast", "--output-split", "20000", "-fno-inline", "-MAKEFLAGS", "OPT_FAST=-O1"]
    dk = ["docker", "run", "--rm", "--memory", "32g", "--cpus", "16", "-u", f"{os.getuid()}:{os.getgid()}",
          "-v", f"{a.root}:/work/root:ro", "-v", f"{a.work}:/work/out", "-e", "HOME=/work/out", "-e", "CCACHE_DISABLE=1",
          "--entrypoint", "bash", a.image, "-c",
          " ".join(shlex.quote(x) for x in cmd) + f" > /work/out/build_{tag}.log 2>&1; echo $? > /work/out/build_{tag}.rc"]
    subprocess.run(dk, check=False)
    rc = (a.work / f"build_{tag}.rc").read_text().strip()
    if rc != "0":
        sys.exit(f"build {tag} failed rc={rc}; see {a.work}/build_{tag}.log")
    return tag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--srx", type=int, default=0)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--srxt", default="", help="SRXT relay-tree table (hex, 256 digits max) for SRX > 0")
    ap.add_argument("--nstage", type=int, default=2)
    ap.add_argument("--hcore", action="store_true")
    ap.add_argument("--rt2-calendar", action="store_true")
    ap.add_argument("--image", default="verilator/verilator:v5.032")
    a = ap.parse_args()
    a.analyze_only = False
    a.work = a.work.resolve(); a.work.mkdir(parents=True, exist_ok=True)
    nkv, np_ = L.vectors(a.work / "vec", a.seed)
    with ThreadPoolExecutor(3) as ex:
        tags = list(ex.map(lambda v: build(a, v, nkv, np_), ["ref", "bcast", "mut"]))
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(lambda t: L.run(a, t), tags))
    (ref, rs), (dut, ds), (mut, ms) = res
    c = L.compare(ref, dut, 0, 0)
    cm = L.compare(ref, mut, 0, 0)
    setchk = ds.get("V41XSETCHK", {}).get("errors")
    lock = all(v["ok"] for v in c.values()) and setchk in ("0", None)
    caught = not all(v["data_equal"] for v in cm.values())
    rec = dict(tool="svc_bcast_lockstep.py", srx=a.srx, hcore=a.hcore, rt2_calendar=a.rt2_calendar, seed=a.seed,
               T=L.TS, ref=dict(tag=tags[0], summary=rs, beats_sc=len(ref["BSC"]), beats_pv=len(ref["BPV"])),
               bcast=dict(tag=tags[1], summary=ds, strict_lockstep=lock, setcheck_errors=setchk, compare=c),
               mut=dict(tag=tags[2], summary=ms, caught=caught, compare=cm))
    rec["status"] = "PASS" if (lock and caught and len(ref["BPV"]) > 0 and len(ref["BSC"]) > 0) else "FAIL"
    (a.work / f"bcast_lockstep_srx{a.srx}{'_hc' if a.hcore else ''}.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("SVC_BCAST_LOCKSTEP", rec["status"], "strict_lockstep", lock, "mutant_caught", caught,
          "sc/pv beats", len(ref["BSC"]), len(ref["BPV"]), "setchk", setchk)
    sys.exit(0 if rec["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
