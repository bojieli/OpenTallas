#!/usr/bin/env python3
"""Bench campaign for ot_dsrom_link_rt (reliable package/die link, gap Z5/L1).

Compiles rtl/test/dsrom_sys/tb_dsrom_link_rt.sv under Icarus for every case,
runs them (at most --jobs at a time), lints the RTL with Verilator -Wall, and
writes results/rtl/dsrom_system_rtl_20261003/link_rt_bench.json.

A case passes when its outcome matches its expectation: functional cases must
PASS the scoreboard (exactly-once, in-order, bit-exact, last preserved, no
fault); the throughput cases must also sustain 1 flit/cycle; mutants (negative
controls) must FAIL.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL = "rtl/dsrom_sys/ot_dsrom_link_rt.sv"
CHAN = "rtl/dsrom_sys/ot_dsrom_link_chan.sv"
CRC = "rtl/link/ot_link_crc32.sv"
ORIG = "rtl/rom/ot_rom_pkg_link.sv"
TB = "rtl/test/dsrom_sys/tb_dsrom_link_rt.sv"
SELF = "tools/dsrom_link_rt_campaign.py"
OUT = "results/rtl/dsrom_system_rtl_20261003/link_rt_bench.json"

# name, defines, plusargs, expectation, note
CASES = [
    ("a_ucie_noerr", dict(CH=8), dict(n=20000, gap=20, bpm=0, seed=11), "PASS",
     "UCIe-like CHANNEL_CYCLES=8, no errors, back-pressure sweep 0/30/70%"),
    ("b_board_noerr", dict(CH=156), dict(n=6000, gap=20, bpm=0, seed=12), "PASS",
     "board light-FEC 130 ns at 1.2 GHz (156 cycles), CREDITS=32, no errors"),
    ("c_fwd_err97", dict(CH=8, EFWD=97), dict(n=20000, gap=20, bpm=0, seed=13), "PASS",
     "forward bit flip every 97th frame"),
    ("d_rev_err53", dict(CH=8, EREV=53), dict(n=20000, gap=20, bpm=0, seed=14), "PASS",
     "reverse bit flip every 53rd frame"),
    ("e_both_heavybp", dict(CH=8, EFWD=97, EREV=53), dict(n=12000, gap=10, bpm=1, seed=15), "PASS",
     "both directions injected, heavy back-pressure 70/90%"),
    ("e_board_both", dict(CH=156, EFWD=97, EREV=53), dict(n=4000, gap=20, bpm=0, seed=16), "PASS",
     "both directions injected at board latency"),
    ("f_dyn_1", dict(CH=228, DYN=1), dict(n=4000, gap=20, bpm=0, seed=17, chsel=1), "PASS",
     "DYNAMIC_DELAY=1, CHANNEL_CYCLES=228, channel_cycles=1"),
    ("f_dyn_60", dict(CH=228, DYN=1), dict(n=4000, gap=20, bpm=0, seed=18, chsel=60), "PASS",
     "DYNAMIC_DELAY=1, channel_cycles=60"),
    ("f_dyn_228", dict(CH=228, DYN=1), dict(n=4000, gap=20, bpm=0, seed=19, chsel=228), "PASS",
     "DYNAMIC_DELAY=1, channel_cycles=228"),
    ("g_tput_ucie", dict(CH=8, CRED=32), dict(n=10000, gap=0, bpm=2, seed=20), "PASS_RATE1",
     "throughput: no errors, out_ready=1, CREDITS=32 covers the credit loop at CH=8"),
    ("g_tput_board", dict(CH=156, CRED=512, SEQW=10), dict(n=10000, gap=0, bpm=2, seed=21), "PASS_RATE1",
     "throughput at board latency: CREDITS=512 (SEQW=10) covers the credit loop"),
    ("ref_orig_ucie", dict(CH=8, DUT_ORIG=1), dict(n=2000, gap=0, bpm=2, seed=22), "PASS",
     "reference: original ot_rom_pkg_link, same bench, latency comparison"),
    ("ref_orig_board", dict(CH=156, CRED=512, DUT_ORIG=1), dict(n=2000, gap=0, bpm=2, seed=23), "PASS",
     "reference: original ot_rom_pkg_link at CH=156"),
    ("m_nocrc", dict(CH=8, EFWD=97, OT_DSROM_LINK_MUT_NOCRC=1), dict(n=5000, gap=20, bpm=0, seed=24), "FAIL",
     "mutant: forward CRC check disabled under forward injection"),
    ("m_noreplay", dict(CH=8, EFWD=97, OT_DSROM_LINK_MUT_NOREPLAY=1), dict(n=5000, gap=20, bpm=0, seed=25), "FAIL",
     "mutant: NAK/timeout never rewind under forward injection"),
    ("m_freecredit", dict(CH=8, OT_DSROM_LINK_MUT_FREECREDIT=1), dict(n=5000, gap=20, bpm=0, seed=26), "FAIL",
     "mutant: sends never consume credits (immediate-and-free credit return)"),
    ("h_dead_link", dict(CH=8, EFWD=1), dict(n=500, gap=20, bpm=0, seed=27), "FAIL_FAULT1",
     "negative control of the fault path: every forward frame corrupted; must latch fault 1 (retry exhausted)"),
]

LINT_PARAMS = [
    ["-GFLIT_BYTES=64", "-GCREDITS=32", "-GCHANNEL_CYCLES=8"],
    ["-GFLIT_BYTES=64", "-GCREDITS=32", "-GCHANNEL_CYCLES=228", "-GDYNAMIC_DELAY=1",
     "-GERR_PERIOD_FWD=97", "-GERR_PERIOD_REV=53"],
    ["-GFLIT_BYTES=64", "-GCREDITS=512", "-GSEQW=10", "-GCHANNEL_CYCLES=156"],
]
LINT_WAIVERS = [
    ("WIDTHCONCAT", CRC, "pinned shared CRC module: 32*W-bit mask localparam is intentional (elaboration-time masks)"),
    ("UNUSED", CRC, "pinned shared CRC module: elaboration functions take an unused dummy argument"),
]


def sha(path):
    with open(os.path.join(ROOT, path), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def tool(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[0]
    except Exception as e:  # pragma: no cover
        return "unavailable: %s" % e


def build_key(defs):
    return "_".join("%s%s" % (k, v) for k, v in sorted(defs.items())) or "default"


def compile_case(work, defs, name):
    key = build_key(defs) + "__" + name
    vvp = os.path.join(work, key + ".vvp")
    srcs = [TB, RTL, CHAN, CRC] + ([ORIG] if "DUT_ORIG" in defs else [])
    cmd = ["iverilog", "-g2012", "-o", vvp] + ["-D%s=%s" % (k, v) for k, v in sorted(defs.items())] + \
          [os.path.join(ROOT, s) for s in srcs]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return vvp, cmd, r.returncode, r.stdout + r.stderr


def run_case(work, case):
    name, defs, plus, expect, note = case
    vvp, ccmd, crc, clog = compile_case(work, defs, name)
    rec = dict(case=name, note=note, expect=expect, defines=defs, plusargs=plus,
               compile_cmd=" ".join(os.path.relpath(c, ROOT) if c.startswith(ROOT) else c for c in ccmd))
    if crc != 0:
        rec.update(outcome="COMPILE_ERROR", log=clog[-2000:], ok=False)
        return rec
    rcmd = ["vvp", "-n", vvp] + ["+%s=%s" % (k, v) for k, v in plus.items()] + ["+case=%s" % name]
    t0 = time.time()
    r = subprocess.run(rcmd, capture_output=True, text=True)
    rec["wall_s"] = round(time.time() - t0, 1)
    rec["run_cmd"] = " ".join(["vvp", "-n", os.path.basename(vvp)] + rcmd[3:])
    m = re.search(r"LINKRT_SUMMARY (.*)", r.stdout)
    if not m:
        rec.update(outcome="NO_SUMMARY", log=(r.stdout + r.stderr)[-2000:], ok=False)
        return rec
    rec["summary_line"] = m.group(0)
    fields = {}
    for kv in m.group(1).split():
        k, v = kv.split("=", 1)
        try:
            fields[k] = int(v)
        except ValueError:
            try:
                fields[k] = float(v)
            except ValueError:
                fields[k] = v
    rec["fields"] = fields
    rec["mismatch_lines"] = [l for l in r.stdout.splitlines() if l.startswith("MISMATCH")][:5]
    bench = fields["result"]
    if expect == "PASS":
        ok = bench == "PASS"
    elif expect == "PASS_RATE1":
        ok = bench == "PASS" and fields["rate"] >= 0.9999
    elif expect == "FAIL_FAULT1":
        ok = bench == "FAIL" and fields["fault"] == 1 and fields["fault_code"] == 1
    else:
        ok = bench == "FAIL"
    rec["bench_result"] = bench
    rec["ok"] = ok
    rec["outcome"] = "as_expected" if ok else "UNEXPECTED"
    return rec


def lint(work):
    vlt = os.path.join(work, "waivers.vlt")
    with open(vlt, "w") as f:
        f.write("`verilator_config\n")
        for rule, path, _ in LINT_WAIVERS:
            f.write('lint_off -rule %s -file "*/%s"\n' % (rule, path))
    out = []
    for p in LINT_PARAMS:
        cmd = ["verilator", "--lint-only", "-Wall", "--top-module", "ot_dsrom_link_rt"] + p + \
              [vlt] + [os.path.join(ROOT, s) for s in (RTL, CHAN, CRC)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        out.append(dict(params=p, returncode=r.returncode,
                        warnings=[l for l in (r.stdout + r.stderr).splitlines() if l.startswith("%")][:20],
                        clean=(r.returncode == 0 and "%Warning" not in r.stdout + r.stderr)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", default=None, help="build directory (default: a fresh temp dir)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--output", default=os.path.join(ROOT, OUT))
    ap.add_argument("--only", default=None, help="comma-separated case names")
    a = ap.parse_args()
    work = a.work or tempfile.mkdtemp(prefix="dsrom_link_rt_")
    os.makedirs(work, exist_ok=True)
    cases = [c for c in CASES if not a.only or c[0] in a.only.split(",")]
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        recs = list(ex.map(lambda c: run_case(work, c), cases))
    lint_res = lint(work)
    for r in recs:
        print(r.get("summary_line", "%s %s" % (r["case"], r["outcome"])), "->", r["outcome"])
    flits = sum(r.get("fields", {}).get("rcvd", 0) for r in recs)
    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    func = [r for r in recs if not r["expect"].startswith("FAIL")]
    muts = [r for r in recs if r["expect"].startswith("FAIL")]
    lat = {r["case"]: r["fields"]["lat_first"] for r in recs if "fields" in r}
    rec = dict(
        schema="dsrom_link_rt_bench/1",
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        purpose="Reliable package/die link ot_dsrom_link_rt (gap Z5/L1): drop-in successor of ot_rom_pkg_link "
                "with sequence numbers, CRC-32, go-back-N replay, ACK/NAK and cumulative credit return "
                "across the reverse channel. Default-off: ot_rom_pkg_link stays the default everywhere.",
        verdict="PASS" if all(r["ok"] for r in recs) and all(l["clean"] for l in lint_res) else "FAIL",
        functional_cases_pass=sum(r["ok"] for r in func), functional_cases=len(func),
        mutants_failing_as_required=sum(r["ok"] for r in muts), mutants=len(muts),
        total_flits_delivered=flits,
        first_flit_latency=dict(
            convention="cycles from the input handshake cycle to the first cycle out_valid is high, idle link",
            formula="TX_STAGES + CHANNEL_CYCLES_active + RX_STAGES + 2 (CRC generate and check fold into the "
                    "existing TX/RX stage cycles; +1 receive FIFO write, +1 registered output stage); identical "
                    "to ot_rom_pkg_link measured by the same bench, i.e. zero added error-free latency",
            measured=lat),
        lint=dict(tool=tool(["verilator", "--version"]), waivers=[dict(rule=w[0], file=w[1], why=w[2]) for w in LINT_WAIVERS],
                  runs=lint_res),
        caveats=[
            "ot_dsrom_link_chan is a fixed delay line plus deterministic single-bit flips: no burst errors, "
            "no FEC, no SerDes, no CDC. A single-bit flip is always detected by CRC-32.",
            "Reverse frames are a dedicated per-cycle-capable sideband (ACK/NAK/credit DLLP stand-in) at up to "
            "1 frame/cycle; bandwidth contention with reverse-direction data flits is not modelled.",
            "Full rate needs min(CREDITS, REPLAY) >= the credit loop (about 2*CHANNEL_CYCLES + TX + RX + 8 cycles); "
            "the array bench's CREDITS=32 is credit-bound at board latency exactly as with ot_rom_pkg_link "
            "(whose immediate credit return hid the loop).",
            "REPLAY <= 2^(SEQW-1) is an elaboration check; SEQW=8 supports REPLAY/CREDITS up to 128.",
            "Not yet substituted into tb_hdc_v41x_array.sv; no synthesis/P&R of the link.",
        ],
        sources={p: sha(p) for p in (RTL, CHAN, CRC, ORIG, TB, SELF)},
        source_state=dict(worktree_head=head, note="files were uncommitted at run time; sha256 above binds the "
                                                    "evidence to the exact bytes"),
        tools=dict(iverilog=tool(["iverilog", "-V"]), verilator=tool(["verilator", "--version"]),
                   python=sys.version.split()[0]),
        command=" ".join(["python3", SELF] + sys.argv[1:]),
        wall_s=round(time.time() - t0, 1),
        cases=recs,
    )
    os.makedirs(os.path.dirname(a.output), exist_ok=True)
    with open(a.output, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=False)
        f.write("\n")
    print("verdict=%s flits=%d -> %s" % (rec["verdict"], flits, a.output))
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
