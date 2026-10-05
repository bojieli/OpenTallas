#!/usr/bin/env python3
"""RD sweep of the W1 credit return node (046bf5026) against the RD64 reference, directed RTL (Icarus).

Sources are read from the pinned W1 commit with `git show` and hashed; nothing in rtl/ is modified.
This is a directed node-chain measurement, NOT the L0/L20 program gate."""
import argparse, hashlib, itertools, json, re, subprocess, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W1 = "046bf5026d36cc4f31813db26045360da618e51f"
SOURCES = ["rtl/v41rom/ot_v41_ret.sv", "rtl/v41rom/ot_v41_ret_credit.sv", "rtl/v41die/ot_v41_retn_w17w10.sv",
           "rtl/v41die/ot_v41_retn_credit.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_delay.sv"]
BENCH = "rtl/test/tb_dsrom_credit_rd_sweep.sv"
# (MODE, ROUND, PER, SKEW): saturated fixture; program-shaped 8-row rounds at the 40-cycle chain floor
# with sibling skews; back-to-back 8-row rounds (PER=8, saturated round stream) with skews.
CASES = [(0, 8, 40, 0)] + [(1, 8, 40, s) for s in (0, 1, 2, 3, 5, 8, 12, 20)] + [(1, 8, 8, s) for s in (0, 1, 2, 3)]
RDS = (4, 8, 16, 32)


def run(out: Path):
    out.mkdir(parents=True, exist_ok=False)
    src = out / "src"
    pins = {}
    for p in SOURCES:
        b = subprocess.check_output(["git", "show", f"{W1}:{p}"], cwd=ROOT)
        (src / p).parent.mkdir(parents=True, exist_ok=True)
        (src / p).write_bytes(b)
        pins[f"{W1}:{p}"] = hashlib.sha256(b).hexdigest()
    pins[BENCH] = hashlib.sha256((ROOT / BENCH).read_bytes()).hexdigest()
    rows, t0 = [], time.monotonic()
    for rd, (mode, rnd, per, skew) in itertools.product(RDS, CASES):
        exe = out / f"rd{rd}_m{mode}_r{rnd}_p{per}_s{skew}"
        cmd = ["iverilog", "-g2012", "-s", "tb_dsrom_credit_rd_sweep", "-o", str(exe),
               *(f"-Ptb_dsrom_credit_rd_sweep.{k}={v}" for k, v in
                 dict(RD=rd, MODE=mode, ROUND=rnd, PER=per, SKEW=skew).items()),
               *[str(src / p) for p in SOURCES], str(ROOT / BENCH)]
        c = subprocess.run(cmd, capture_output=True, text=True)
        if c.returncode:
            rows.append(dict(RD=rd, MODE=mode, PER=per, SKEW=skew, status="FAIL_COMPILE", log=c.stderr[-2000:]))
            continue
        r = subprocess.run(["vvp", "-n", str(exe)], capture_output=True, text=True)
        res = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
        row = dict(RD=rd, MODE=mode, ROUND=rnd, PER=per, SKEW=skew,
                   status=("PASS_EXACT" if "reference_fault=0" in res[-1] else "PASS_CREDIT_NO_FAULT_REFERENCE_OVERFLOWED") if (r.returncode == 0 and res and "FATAL" not in r.stdout) else "FAIL",
                   log_tail=None if res else (r.stdout + r.stderr)[-1500:])
        if res:
            f = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", res[-1])}
            row.update(f)
            row["completion_ratio"] = f["credit_last"] / f["reference_last"]
            row["rate_loss"] = 1 - f["reference_last"] / f["credit_last"]
        exe.unlink(missing_ok=True)
        rows.append(row)
    rec = dict(schema="dsrom.credit_rd_sweep.v1", label="MEASURED_DIRECTED_RTL_NOT_PROGRAM_GATE",
               simulator="Icarus " + subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0],
               w1_commit=W1, source_sha256=pins, cases=rows, wall_s=round(time.monotonic() - t0, 1),
               scope="two-level node chain, independent side backpressure; per-row count and {tag,data} sum equal to "
                     "the RD64 reference (exact); not the L0/L20 program occupancy join")
    (out / "result.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    rec = run(ap.parse_args().out)
    for c in rec["cases"]:
        print({k: c.get(k) for k in ("RD", "MODE", "PER", "SKEW", "status", "credit_last", "reference_last",
                                     "rate_loss", "reference_fault", "row_delay_max", "peak_a", "peak_b", "parent_peak_a", "stalls")})
