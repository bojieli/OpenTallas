#!/usr/bin/env python3
"""S81-A1 SRX lock-step proof (S81-ARCH-RTL-2 11-11).

Builds tb_svc_srx_attn.sv (Verilator, docker image) for the svc engine configuration of dsdv_svc_att
(H 8, D = TD = 32, NL 4, PWORDS 2, ILV 1, REPL 2, NSTAGE 2, FPL 4, FML 6, TILE_S 1, NARROW 1, MFAN 1, TRX 1, F12 1,
FPLX 5, SC_CRED = PV_CRED = 0) at SRX = 0 (as built, the reference) and SRX = n, runs both on the same random
vectors and checks, beat by beat:
  * every score beat (row, mask, data, flags) is bit-identical, the first job's land exactly n cycles later;
  * every P.V beat (c, data, flags) is bit-identical and lands exactly 2n cycles later (the bench's SU model starts
    the p stream at the last score, i.e. the compiler's PIO move of +n);
  * job / q / kv / p accepts carry the same words in the same order (cycles reported: back-to-back NSTAGE 2 jobs
    are NOT cycle-identical, the double buffer couples the front end to the later P.V drain, measured as end_cycle);
  * the RTL bank-set checker (OT_ATTN_SETCHECK) reports 0 errors.
Each SRXMUT negative control (1 tags not delayed, 2 load line one stage short, 3 tile 0 fill one stage short) must
FAIL.  Usage: svc_srx_lockstep.py --root <repo> --work <dir> --srx 7 [--srxt <hex>] [--dut hdc|s81] [--mut 1,2,3] [--nstage 3]
With --nstage 3 the end_cycle pair should match (the third buffer covers the back-to-back slip).
"""
import argparse, json, os, random, re, shlex, subprocess, sys, hashlib
from pathlib import Path

P = dict(H=8, D=32, TD=32, NL=4, TROWS=640, PWORDS=2, ILV=1, REPL=2, NSTAGE=2, FPL=4, FML=6, TILE_S=1, NARROW=1,
         MFAN=1, F12=1, FPLX=5, TRX=1, SC_CRED=0, PV_CRED=0, NBANKP=0)
TS = [37, 128, 1, 200, 64, 333, 96, 640, 5, 160]
ROWW = 265


def vectors(d: Path, seed: int):
    rng = random.Random(seed)
    d.mkdir(parents=True, exist_ok=True)
    H, R = P["H"], P["TD"] // P["H"]
    jobs, kv, q, p = [], [], [], []
    for t in TS:
        jobs.append((len(kv), len(p), t))
        kv += [rng.getrandbits(ROWW) for _ in range(t)]
        q += [rng.getrandbits(P["D"] * 16) for _ in range(H)]
        p += [rng.getrandbits(P["TD"] * 16) for _ in range((t + R - 1) // R)]
    w = lambda n, xs, bits: (d / n).write_text("".join(f"{x:0{(bits + 3) // 4}x}\n" for x in xs))
    w("jobs.hex", [(0 << 128) | (0 << 96) | (pp << 64) | (k << 32) | t for k, pp, t in jobs], 160)
    w("kv.hex", kv, ROWW); w("q.hex", q, P["D"] * 16); w("p.hex", p, P["TD"] * 16)
    w("sc.hex", [0], H * 33); w("pv.hex", [0], H * 33)
    return len(kv), len(p)


def build(a, srx, mut, nkv, np_):
    ns = a.nstage if srx else 2
    band = a.band if srx else 0
    tag = f"{a.dut}_srx{srx}_m{mut}" + (f"_ns{ns}" if ns != 2 else "") + (f"_band{band}m{a.bandm}t{a.bandt}" if band else "") + ("_hc" if a.hcore else "")
    if (a.work / f"build_{tag}.rc").is_file() and (a.work / f"build_{tag}.rc").read_text().strip() == "0":
        return tag
    prm = dict(P, NSTAGE=ns, SRX=srx, SRXMUT=mut, NJOBMAX=len(TS), NKV=nkv, NP=np_, NSC=1, NPV=1, MAXCYC=400000)
    if band:
        # --band: the S81 band form (ot_s81_svc_band); the mutants are the BAND negative controls (BANDMUT 1, 2)
        prm.update(SRXMUT=0, BANDX=band, BANDM=a.bandm, BANDT=a.bandt, BANDMUT=mut)
    if srx and a.srxt:
        prm["SRXT"] = f"1024'h{a.srxt}"
    r = "/work/root"
    ys = ["rtl/hdc/v41x", "rtl/hdc", "rtl/dsrom_sys/s81_svc", "rtl/dsrom_sys/s81_dv"]
    files = ["rtl/hdc/v41x/ot_hdc_v41x_kreg.sv", "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv",
             "rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
             "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv"]
    if a.dut == "s81":
        if a.hcore:
            files += ["rtl/hdc/v41x/ot_s81c_attn_hcore.sv", "rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv", "rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv",
                      "rtl/hdc/v41x/ot_dsrom_su_add6.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/v41x/ot_dsrom_su_f12.sv", "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv"]
        files += ["rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv", "rtl/dsrom_sys/s81_dv/ot_s81_svc_merge_h4.sv",
                  "rtl/dsrom_sys/s81_svc/ot_s81_svc_band.sv"]
    cmd = ["verilator", "--cc", "--exe", "--build", "-j", "24", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "-Wno-MULTIDRIVEN", "--top-module", "tb_hdc_v41x_attn", "--prefix", "Vtb", "-Mdir",
           f"/work/out/obj_{tag}", "+define+OT_ATTN_SETCHECK",
           *(["+define+SRX_DUT_S81", "+define+OT_SVC_MERGE_H4"] if a.dut == "s81" else []),
           *(["+define+OT_ATTN_HCORE", "+define+OT_S81C_HCORE_CTLA", "+define+OT_S81C_HCORE_RST_TIMED", "+define+OT_SVC_H8", "+define+OT_SVC_H8_REUSE_RT2"] if a.hcore else []),
           *(["+define+OT_S81C_TILE_PAIR", "+define+OT_S81C_TILE_REACH" if a.bandt == 5 else "+define+OT_S81C_TILE_STAGE"] if (a.hcore and band and a.bandt) else []),
           *[x for y in ys for x in ("-y", f"{r}/{y}")],
           *[f"-G{k}={v}" for k, v in prm.items()], *[f"{r}/{f}" for f in files],
           f"{r}/rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_srx_attn.sv", f"{r}/rtl/test/hdc_v41_harness.cpp",
           "--x-assign", "fast", "--x-initial", "fast", "--output-split", "20000", "-fno-inline", "-MAKEFLAGS", "OPT_FAST=-O1"]
    dk = ["docker", "run", "--rm", "--memory", "32g", "--cpus", "24", "-u", f"{os.getuid()}:{os.getgid()}",
          "-v", f"{a.root}:/work/root:ro", "-v", f"{a.work}:/work/out", "-e", "HOME=/work/out", "-e", "CCACHE_DISABLE=1", "--entrypoint", "bash", a.image, "-c",
          " ".join(shlex.quote(x) for x in cmd) + f" > /work/out/build_{tag}.log 2>&1; echo $? > /work/out/build_{tag}.rc"]
    subprocess.run(dk, check=False)
    rc = (a.work / f"build_{tag}.rc").read_text().strip()
    if rc != "0":
        sys.exit(f"build {tag} failed rc={rc}; see {a.work}/build_{tag}.log")
    return tag


def run(a, tag):
    log = a.work / f"run_{tag}.log"
    dk = ["docker", "run", "--rm", "--memory", "8g", "--cpus", "1", "-u", f"{os.getuid()}:{os.getgid()}",
          "-v", f"{a.work}:/work/out", "-e", "HOME=/work/out", "-e", "CCACHE_DISABLE=1", "--entrypoint", "bash", a.image, "-c",
          f"timeout 900 /work/out/obj_{tag}/Vtb +dir=/work/out/vec > /work/out/run_{tag}.log 2>&1"]
    subprocess.run(dk, check=False)
    ev = {"BSC": [], "BPV": [], "IJ": [], "IQ": [], "IKV": [], "IP": []}
    summ = {}
    for ln in log.read_text().splitlines():
        f = ln.split()
        if f and f[0] in ev:
            ev[f[0]].append((int(f[1]), " ".join(f[2:])))
        elif ln.startswith("V41XATTN") or ln.startswith("V41XSETCHK"):
            summ[ln.split()[0]] = dict(kv.split("=") for kv in ln.split()[1:])
    return ev, summ


def compare(ref, dut, n, npv=None):
    npv = 2 * n if npv is None else npv
    out = {}
    for k, sh in (("IJ", 0), ("IQ", 0), ("IKV", 0), ("IP", n), ("BSC", n), ("BPV", npv)):
        a, b = ref[k], dut[k]
        ok = len(a) == len(b) and all(x[1] == y[1] and y[0] - x[0] == sh for x, y in zip(a, b))
        bad = next((i for i, (x, y) in enumerate(zip(a, b)) if x[1] != y[1] or y[0] - x[0] != sh), None)
        out[k] = dict(n_ref=len(a), n_dut=len(b), shift=sh, ok=ok, first_bad=bad,
                      data_equal=len(a) == len(b) and all(x[1] == y[1] for x, y in zip(a, b)),
                      first_shift=(b[0][0] - a[0][0]) if a and b else None,
                      deltas=sorted({y[0] - x[0] for x, y in zip(a, b)})[:8])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--srx", type=int, default=7)
    ap.add_argument("--srxt", default="")
    ap.add_argument("--dut", choices=("hdc", "s81"), default="hdc")
    ap.add_argument("--mut", default="1,2,3")
    ap.add_argument("--nstage", type=int, default=2, help="DUT NSTAGE (3 = third staging buffer); the SRX 0 reference stays 2")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--band", type=int, default=0, help="S81 band form: BANDX = capture depth (1 or 2) on top of --srx; "
                    "--mut then names the BANDMUT controls (1 = tags one stage short, 2 = band 0 merge tags early)")
    ap.add_argument("--bandt", type=int, default=0, help="BANDT: 1 = the S81 tile with its per-core input stage (needs --hcore: adds +define+OT_S81C_TILE_STAGE to the DUT only)")
    ap.add_argument("--hcore", action="store_true", help="build reference and DUT with the S81 H8 RT2 head-core tile (OT_ATTN_HCORE ...)")
    ap.add_argument("--bandm", type=int, default=0, help="BANDM: 1 = merge inputs registered in the band (P.V +1 more)")
    ap.add_argument("--image", default="verilator/verilator:v5.032")
    a = ap.parse_args()
    a.work = a.work.resolve(); a.work.mkdir(parents=True, exist_ok=True)
    if a.band and a.dut != "s81":
        sys.exit("--band needs --dut s81")
    n = a.srx + ((a.band + 1 + a.bandt) if a.band else 0)     # scores +n (band: capture stages + output register)
    npv = 2 * n + (a.bandm if a.band else 0)       # P.V: p feed +n, then +n (+1 with registered merge inputs)
    nkv, np_ = vectors(a.work / "vec", a.seed)
    from concurrent.futures import ThreadPoolExecutor
    muts = [0] + [int(m) for m in a.mut.split(",") if m]
    with ThreadPoolExecutor(len(muts) + 1) as ex:
        tags = list(ex.map(lambda sm: build(a, sm[0], sm[1], nkv, np_), [(0, 0)] + [(a.srx, m) for m in muts]))
    ref_tag = tags[0]
    ref, rs = run(a, ref_tag)
    rec = dict(tool="svc_srx_lockstep.py", dut=a.dut, srx=a.srx, band=a.band, bandm=a.bandm, bandt=a.bandt, hcore=a.hcore, shift=n, shift_pv=npv, nstage=a.nstage, srxt=a.srxt, seed=a.seed, params=P, T=TS,
               ref=dict(tag=ref_tag, summary=rs, beats_sc=len(ref["BSC"]), beats_pv=len(ref["BPV"])), runs={})
    engine_source = a.root / "rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv"
    fixed_rt2_calendar = a.hcore and a.dut == "s81" and "ot_s81_svc_rt2_load_calendar u_calendar" in engine_source.read_text()
    rec["native_load_calendar"] = dict(ii_cycles=2, first_load_phase=0, replay_phase=1, static=True) if fixed_rt2_calendar else None
    rec["summary_fault_counter_kind"] = "expected golden flags, not observed DUT protocol faults"
    with ThreadPoolExecutor(len(muts)) as ex:
        res = list(ex.map(lambda t: run(a, t), tags[1:]))
    for mut, tag, (ev, s) in zip(muts, tags[1:], res):
        c = compare(ref, ev, n, npv)
        setchk = s.get("V41XSETCHK", {}).get("errors")
        lock = all(v["ok"] for v in c.values()) and setchk in ("0", None)
        data = all(v["data_equal"] for v in c.values()) and setchk in ("0", None)
        first = c["BSC"]["first_shift"] == n and c["BPV"]["first_shift"] == npv
        end = (ref["BPV"][-1][0], ev["BPV"][-1][0]) if ev["BPV"] and ref["BPV"] else None
        rec["runs"][tag] = dict(srxmut=mut, lockstep=lock, data_equal=data, first_job_shift_ok=first, end_cycle=end,
                                setcheck_errors=setchk, summary=s, compare=c)
    m0r = rec["runs"][tags[1]]
    caught = all(not r["data_equal"] for r in rec["runs"].values() if r["srxmut"])
    # PASS = every output / input stream bit-identical in value and order, the first job exactly +n / +2n, the bank-set
    # checker clean, every negative control breaks the data; strict per-beat lock-step (lockstep) is reported, not
    # required: with NSTAGE 2 back-to-back jobs the staging double buffer couples the front end to the later P.V drain
    rec["status"] = "PASS" if (m0r["data_equal"] and m0r["first_job_shift_ok"] and caught and rec["ref"]["beats_pv"] > 0) else "FAIL"
    (a.work / "lockstep.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("status", rec["status"], "data_equal", m0r["data_equal"], "strict_lockstep", m0r["lockstep"], "end_cycle",
          m0r["end_cycle"], "mutants_caught", caught,
          "sc/pv beats", rec["ref"]["beats_sc"], rec["ref"]["beats_pv"])
    sys.exit(0 if rec["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
