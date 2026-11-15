#!/usr/bin/env python3
"""gp_noconverge.py -- global-placement no-progress report (KW-FIX-44, COORD 11-10 gp-noconverge-scan).

The 2-h hung-job watchdog (watchdog.py) stops a job whose log stops moving.  A non-converging global placement keeps
logging, so it never trips: HBM runs reached 20-40 h and 900k iterations with overflow flat at 0.3-0.5.  This tool reads the
overflow series of live placements (3_3_place_gp.tmp.log exists only while the step runs) and says which ones have stopped
making progress.  REPORT ONLY: it stops nothing and writes nothing but its report.

Rule, either condition:
  CAP       the run has logged at least CAP_ROWS table rows (one row = 10 iterations).
  NO-FLOOR  split the series in blocks of WINDOW rows; a block's floor is its lowest overflow.  STREAK consecutive blocks
            without a lower floor than the block before.

Values come from a replay of every global-place log on the fleet on 11-10 (5 hosts, 568 unique finished runs of >= 100
rows): the longest run that finished had 19,811 rows, and no finished run reached the streak (longest streak seen: 1).
The evidence is thin at the long end, where the rule can act: the streak needs 8,000 rows, and only 2 finished runs got
that far.  The longest of them sat near overflow 0.72 for about 16,000 rows before it converged, and passed because block
floors kept falling by small amounts, so a flat stretch alone does not prove a run will never finish.

A stop by this rule, when enabled, is FLOW/no-converge, not INFRA: the kit is kept and the row is not retried unchanged.

PLACE-NOCONVERGE gate (KW-FIX-44, COORD 11-10, acting): --gate LOG reads one finished 3_3_place_gp.log.  When OpenROAD
stopped global placement at its built-in Nesterov iteration limit (GPL-1010, 5,000 in this image) and the last overflow
row is still above --overflow (0.1, the ORFS target), the run ends at place: exit 3, the verdict line and, with
--marker FILE, the same line in FILE.  gp_noconverge_gate.tcl (PRE_RESIZE_TCL) calls it before resize, so the buffering
and DPL steps never run on a placement that did not converge (HBM kv_line vC: 0.370 at the cap, then +459k buffers and
DPL-0038 at 153%).  A run that reached the cap at or below the overflow limit, or never reached it, passes.

Usage: gp_noconverge.py [--hosts a,b,c] [--out FILE]
       gp_noconverge.py --gate LOG [--overflow 0.1] [--marker FILE]
"""
import argparse, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

WINDOW, STREAK, CAP_ROWS = 2000, 3, 25000
CLASS = "FLOW no-converge"
PLACE_CLASS = "PLACE-NOCONVERGE"
NOCONV_OVERFLOW = 0.1                                          # ORFS global placement target overflow
GPL_CAP = re.compile(r"GPL-1010\]?\s+GPL reached the maximum number of iterations for nesterov\s+(\d+)")
DEFAULT_HOSTS = "intel1,intel2,epyc2,epyc4,epyc7"
HUB = os.environ.get("OT_HUB_NAME", "intel2")                  # the hub cannot ssh to its own name
ROW = re.compile(r"^\s*(\d+) \|\s+([0-9.]+) \|")
ROW_OLD = re.compile(r"Iter:\s*(\d+)\s+overflow:\s*([0-9.]+)", re.I)


def overflows(lines):
    out = []
    for line in lines:
        m = ROW.match(line) or ROW_OLD.search(line)
        if m:
            out.append(float(m.group(2)))
    return out


def judge(series, window=WINDOW, streak=STREAK, cap_rows=CAP_ROWS):
    """-> (verdict, why): verdict is 'STOP' or 'OK'; only full blocks count"""
    if len(series) >= cap_rows:
        return "STOP", f"cap: {len(series)} rows >= {cap_rows}"
    floors = [min(series[i:i + window]) for i in range(0, len(series) - window + 1, window)]
    run = best = 0
    for i in range(1, len(floors)):
        run = run + 1 if floors[i] >= floors[i - 1] else 0
        best = max(best, run)
        if run >= streak:
            return "STOP", f"no lower overflow floor for {run} blocks of {window} rows (fired at row {(i + 1) * window})"
    return "OK", f"{len(floors)} full blocks, longest streak {best} of {streak}"


def gate(text, overflow=NOCONV_OVERFLOW):
    """finished global-place log -> (verdict, why).  Each GPL-1010 closes one Nesterov pass (routability / timing-driven
    runs restart the table); the first pass that stopped at the iteration cap with its last overflow row above
    `overflow` gives 'STOP', the same reading as kit_wave.gpl_cap_noconverge (DIE-HBM-97 classifier).  'OK' otherwise."""
    rows, capped = [], 0
    for line in (text or "").splitlines():
        m = GPL_CAP.search(line)
        if m:
            capped += 1
            if rows and rows[-1] > overflow:
                return "STOP", (f"{PLACE_CLASS}: global placement stopped at the {m.group(1)}-iteration Nesterov cap "
                                f"(GPL-1010, capped pass {capped}) with overflow {rows[-1]:.4f} > {overflow:g} "
                                f"(best {min(rows):.4f}, {len(rows)} rows)")
            rows = []
            continue
        rows += overflows([line])
    if not capped:
        return "OK", "no GPL-1010: placement converged before the Nesterov iteration cap"
    return "OK", f"{capped} capped pass(es), none above overflow {overflow:g}"


def gate_main(log, overflow, marker=None):
    try:
        with open(log, errors="replace") as f:
            text = f.read()
    except OSError as e:
        print(f"{PLACE_CLASS} gate NOT RUN: {e}")
        return 0                                               # no log, no verdict: the flow goes on as before
    verdict, why = gate(text, overflow)
    if verdict == "STOP":
        print(why)
        if marker:
            with open(marker, "a") as f:
                f.write(why + "\n")
        return 3
    print(f"{PLACE_CLASS} gate OK: {why}")
    return 0


HOST_SCRIPT = r"""
import glob, json, os, time
PR = {".git", "__pycache__", "objects", "results", "reports", "macros", "rtl", "physical", "tools", "node_modules", "lec"}
out = []
now = time.time()
for root in sorted(glob.glob("/srv/opentallas-scratch*/claude")):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in PR and not d.startswith("src_")]
        if "3_3_place_gp.tmp.log" in fn:
            p = os.path.join(dp, "3_3_place_gp.tmp.log")
            try:
                age = now - os.path.getmtime(p)
                if age < 3600:
                    with open(p, errors="replace") as f:
                        out.append(dict(path=p, age_s=int(age), lines=[l for l in f if " | " in l or "overflow" in l.lower()]))
            except OSError:
                pass
print(json.dumps(out))
"""


def scan_host(host, timeout=240):
    remote = "cd /; nice -n 19 ionice -c3 python3 -I -"
    cmd = ["sh", "-c", remote] if host == HUB else ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=10", host, remote]
    try:
        r = subprocess.run(cmd, input=HOST_SCRIPT, capture_output=True, text=True, timeout=timeout)
        return host, json.loads(r.stdout), "" if r.returncode == 0 else r.stderr[-200:]
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        return host, [], str(e)[:200]


def report(results):
    """one row per run: the same run is often visible at two paths"""
    seen, rows, errors = set(), [], []
    for host, logs, err in results:
        if err:
            errors.append(f"{host}: {err}")
        for log in logs:
            s = overflows(log["lines"])
            key = (host, log["path"].split("/run/logs/")[-1], len(s) // 10)
            if not s or key in seen:
                continue
            seen.add(key)
            verdict, why = judge(s)
            rows.append(dict(host=host, path=log["path"], rows=len(s), iters=len(s) * 10, best=min(s), last=s[-1], verdict=verdict,
                             why=why, cls=CLASS if verdict == "STOP" else ""))
    return sorted(rows, key=lambda r: (r["verdict"] != "STOP", -r["rows"])), errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hosts", default=DEFAULT_HOSTS)
    ap.add_argument("--out")
    ap.add_argument("--gate", metavar="LOG", help="PLACE-NOCONVERGE verdict on one finished 3_3_place_gp.log")
    ap.add_argument("--overflow", type=float, default=NOCONV_OVERFLOW)
    ap.add_argument("--marker", help="with --gate: append the STOP line to this file")
    a = ap.parse_args(argv)
    if a.gate:
        return gate_main(a.gate, a.overflow, a.marker)
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(scan_host, a.hosts.split(",")))
    rows, errors = report(results)
    text = "".join(f"{r['verdict']:4} {r['host']:7} rows {r['rows']:6} best {r['best']:.4f} last {r['last']:.4f} {r['why']} | {r['cls']} | {r['path']}\n" for r in rows)
    text += "".join(f"ERROR {e}\n" for e in errors)
    text += f"# REPORT ONLY: nothing stopped. {sum(r['verdict'] == 'STOP' for r in rows)} of {len(rows)} live placements would stop.\n"
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
