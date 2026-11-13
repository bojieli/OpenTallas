#!/usr/bin/env python3
"""run_qual.py REPO OUT [S7FILE] -- HBM-WBQ-QUAL-1 regression driver (Verilator 5.050, lock-step A=old root vs B=ROOT S7 in the real parent).
Builds one simulator per structural variant, runs the clock-ratio / seed / K-stall matrix, then the negative controls, and writes
OUT/results.tsv and OUT/RESULTS.md. Heavy: run under systemd-run -p MemoryMax=48G nice, J parallel sims (default 8)."""
import os, subprocess, sys, re, concurrent.futures as cf, shlex
repo = os.path.abspath(sys.argv[1]); out = os.path.abspath(sys.argv[2])
here = os.path.dirname(os.path.abspath(__file__))
s7 = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else os.path.join(here, "src_s7_greg", "ot_wbq_root_s7_greg.sv")
J = int(os.environ.get("J", "8")); SCALE = float(os.environ.get("SCALE", "1"))
VL = os.environ.get("VERILATOR", os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
os.makedirs(out, exist_ok=True)
D = "rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv"
SRC = [os.path.join(here, f) for f in ("tb_qual.sv", "qual_comp.sv", "qual_s7_g2.sv")] + [s7] + [os.path.join(repo, p) for p in (
    D, "rtl/lib/ot_reset_sync.sv", "rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv",
    "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv",
    "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r0c0_g256/ot_sram_1r1w_128x256_m1_r0c0_g256.v",
    "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x128_m1_r0c0_g128/ot_sram_1r1w_128x128_m1_r0c0_g128.v")]
def gen_rr():
    """V8 candidate (HBM-CORES-C 11-12): kit_g1_rsel52 S7 (RR+RSEL) with ordinal8 shadow + srst copies (RSTCP=8, O8=1), renamed for the bench."""
    t = open(os.environ["V8_S7"]).read()
    t = t.replace("ot_wbq_root_s7_grp", "ot_wbq_rr_s7_grp").replace("ot_wbq_root_s7_g0", "ot_wbq_rr_s7_g0")
    t = t.replace("parameter integer RSTCP=1, parameter integer O8=0)(", "parameter integer RSTCP=1, parameter integer O8=0, parameter integer GREG=0)(")
    t = t.replace("parameter integer RSTCP=8, parameter integer O8=1)(", "parameter integer RSTCP=8, parameter integer O8=1, parameter integer GREG=0)(")
    t = t.replace(".O8(O8)) u_grp", ".O8(O8),.GREG(GREG)) u_grp")
    assert t.count(".RSEL(1)) u_fifo(") == 1
    t = t.replace(".RSEL(1)) u_fifo(", ".RSEL(`OT_WBQ_ROOT_S7_RSEL)) u_fifo(")
    t = "`ifndef OT_WBQ_ROOT_S7_RSEL\n`define OT_WBQ_ROOT_S7_RSEL 0\n`endif\n" + t
    p = os.path.join(out, "gen_rr_s7_greg.sv"); open(p, "w").write(t); return p
def P(**k):
    d = dict(HREG=2, GIN=0, CBREG=1, SSTOPREG=1, GREG=1, MUTCB=0, MUTSTOP=0, CRED=4, DCHK=1)
    d.update(k)
    return d
BUILDS = {
 "tgt": P(), "s7a": P(GREG=0), "base": P(CBREG=0, SSTOPREG=0, GREG=0), "cb": P(SSTOPREG=0, GREG=0), "st": P(CBREG=0, GREG=0),
 "gr": P(CBREG=0, SSTOPREG=0), "tgt_gin": P(GIN=1), "tgt_h0": P(HREG=0),
 "rr": P(GREG=0, RR=1), "rr_rsel": P(GREG=0, RR=1, RSEL=1), "rr_cb": P(GREG=0, RR=1), "tgt_rr": P(RR=1), "tgt_d0": P(DCHK=0), "tgt_d2": P(DCHK=2), "mcb1": P(MUTCB=1), "mcb2": P(MUTCB=2), "mst1": P(MUTSTOP=1), "mst2": P(MUTSTOP=2), "mst3": P(MUTSTOP=3)}
def build(name):
    d = os.path.join(out, "obj_" + name)
    pr = dict(BUILDS[name]); rr = pr.pop("RR", 0); rsel = pr.pop("RSEL", 0)
    g = ["-G%s=%s" % kv for kv in pr.items()]
    extra = []
    if rr:
        g += ["-DQUAL_G1RR", "-DOT_WBQ_ROOT_S7_RPIPE", "-DOT_WBQ_ROOT_S7_RSEL=%d" % rsel]
        extra = [os.path.join(out, "gen_rr_s7_greg.sv"), os.path.join(here, "src_g1_rr", "ot_wbq_root_s7_rr_fifo.sv")]
    cmd = [VL, "--binary", "--timing", "-O1", "-j", "2", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-MULTIDRIVEN", "-Wno-WIDTHCONCAT",
           "--top-module", "tb_qual"] + g + ["-Mdir", d, "-o", "sim"] + SRC + extra
    r = subprocess.run(cmd, capture_output=True, text=True)
    open(d + ".build.log", "w").write(r.stdout + r.stderr)
    return name, r.returncode
RATIOS = [(1000, 1000, 137), (1000, 1000, 500), (1000, 3000, 137), (3000, 1000, 137), (1000, 1370, 300), (1370, 1000, 300), (833, 1024, 200), (1024, 833, 200)]
SUB = [(1000, 1000, 137), (833, 1024, 200), (1000, 3000, 137), (3000, 1000, 137)]
n = lambda x: max(1, int(x * SCALE))
JOBS = []   # (id, build, plusargs, expect)
seed = [100]
def add(build_, tag, rt, mode, ncase, slow=0, quad=0, extra="", expect="PASS", seed_=None):
    seed[0] += 1
    tf, th, ph = rt
    JOBS.append(("%s_%s_%d-%d-%d_s%d_q%d_%d" % (build_, tag, tf, th, ph, slow, quad, seed[0]), build_,
                 "+TF=%d +TH=%d +PH=%d +MODE=%d +NCASE=%d +SLOW=%d +QUAD=%d %s +verilator+seed+%d +verilator+rand+reset+2" % (tf, th, ph, mode, n(ncase), slow, quad, extra, seed[0]), expect))
for rt in RATIOS:                                   # target form, all ratios
    for slow, quad in ((0, 0), (1, 1)):
        add("tgt", "fault", rt, 1, 4000, slow, quad)
    for slow in (0, 1, 2):
        add("tgt", "clean", rt, 0, 300, slow, slow & 1)
for b in ("s7a", "base", "cb", "st", "gr", "tgt_gin", "tgt_h0"):   # variants on four ratios
    for rt in SUB:
        add(b, "fault", rt, 1, 1500, 0, 0)
        add(b, "clean", rt, 0, 300, 0, 0)
for b in ("rr", "tgt_rr"):                                          # g1 RPIPE candidate (kit_g1_vS7_RR_reviewed) on four ratios
    for rt in SUB:
        add(b, "fault", rt, 1, 2000, 0, 0)
        add(b, "clean", rt, 0, 300, 0, 1)
        add(b, "clean", rt, 0, 300, 1, 0)
for b in ("tgt", "s7a", "rr", "tgt_rr"):             # throughput, K always ready (copy-dur old vs new in the QUAL line); CRED fixed 4: parent queue pointers are 2 bits
    for rt in ((1000, 1000, 137), (833, 1024, 200), (1024, 833, 200)):
        add(b, "credit", rt, 0, 60, 2, 0, "+NB=6")
for b in ("mcb1", "mcb2"):                                           # negative controls, must FAIL
    for rt in ((1000, 1000, 137), (833, 1024, 200)):
        add(b, "neg", rt, 0, 100, 0, 0, expect="FAIL")
for b in ("tgt_d0", "tgt_d2"):                                      # rule (a): pre-fix sw (DCHK=0) and the no-check mutant (DCHK=2) must FAIL
    for rt in ((1000, 1000, 137), (833, 1024, 200)):
        add(b, "ruleA", rt, 1, 2400, 0, 0, expect="FAIL")
        add(b, "ruleA", rt, 1, 2400, 1, 1, expect="FAIL")
for b in ("mst1", "mst2", "mst3"):
    for rt in ((1000, 1000, 137), (833, 1024, 200)):
        add(b, "neg", rt, 1, 300, 0, 0, expect="FAIL")
for b in ("rr_rsel",):
    for rt in RATIOS:
        add(b, "fault", rt, 1, 2000, 0, 0)
        add(b, "clean", rt, 0, 300, 0, 1)
        add(b, "clean", rt, 0, 300, 1, 0)
    for rt in ((1000, 1000, 137), (833, 1024, 200), (1024, 833, 200)):
        add(b, "credit", rt, 0, 60, 2, 0, "+NB=6")
ONLY = os.environ.get("ONLY")
if ONLY:
    JOBS[:] = [j for j in JOBS if re.fullmatch(ONLY, j[1])]
    BUILDS = {k: v for k, v in BUILDS.items() if re.fullmatch(ONLY, k)}
def run(job):
    jid, b, args, expect = job
    log = os.path.join(out, jid + ".log")
    r = subprocess.run([os.path.join(out, "obj_" + b, "sim")] + shlex.split(args), capture_output=True, text=True)
    open(log, "w").write(r.stdout + r.stderr)
    return job, r.returncode, r.stdout
if __name__ == "__main__":
    gen_rr()
    with cf.ThreadPoolExecutor(max_workers=max(1, J // 2)) as ex:
        for name, rc in ex.map(build, BUILDS):
            print("build", name, "OK" if rc == 0 else "FAIL", flush=True)
            if rc: sys.exit(2)
    rows = []
    with cf.ThreadPoolExecutor(max_workers=J) as ex:
        for job, rc, so in ex.map(run, JOBS):
            g = lambda pat: (re.findall(pat, so) or [""])[-1]
            verdict = "PASS" if "QUAL PASS" in so else "FAIL"
            ok = "OK" if verdict == job[3] else ("NEG-ESCAPED" if job[3] == "FAIL" else "REGRESSION")
            rows.append((job[0], job[1], job[3], verdict, ok, g(r"QUAL cases (.*)"), g(r"QUAL post-stop root activity: (.*)"), g(r"QUAL bad: (.*)"), g(r"QUAL fault types injected (.*)")))
            print(job[0], verdict, ok, flush=True)
    with open(os.path.join(out, "results.tsv"), "w") as f:
        f.write("job\tbuild\texpect\tgot\tstatus\tcases\tpost_stop\tbad\tinjected\n")
        for r in rows: f.write("\t".join(r) + "\n")
    bad = [r for r in rows if r[4] != "OK"]
    print("TOTAL jobs", len(rows), "not-OK", len(bad))
    sys.exit(1 if bad else 0)
