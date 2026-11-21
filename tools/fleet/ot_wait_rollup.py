#!/usr/bin/env python3
"""ot_wait_rollup.py -- FLOW-OPS-1300 (FABLE-FLOW-1240 g / FABLE-FLOW-1000 fix 9): fold the per-host ot-wait ledgers (~/.local/state/ot-wait/waits.tsv,
appended by every ot-wait exit, b6934d7751) into ONE hub table lanes/WAITS.tsv, so lane waits can be measured on the hub.

  python3 -I ot_wait_rollup.py [--coord ~/coord] [--days 7] [--dry-run] HOST ...     (hub cron, intel2; the hub itself = localhost)

Columns: the ledger's own (time host lane mode targets rc waited_s timeout ended).  Rows are deduplicated by their full text, kept for --days, sorted by time.
A host that cannot be read keeps its rows already in WAITS.tsv (one bad ssh never drops history).  Writes only on a change, through bin/coord-commit.sh."""
import argparse, os, subprocess, sys, time

HEADER = "time\thost\tlane\tmode\ttargets\trc\twaited_s\ttimeout\tended"
LEDGER = "~/.local/state/ot-wait/waits.tsv"


def parse(text):
    """-> [row text] of a ledger / WAITS.tsv (header and blank lines dropped)"""
    return [l.rstrip("\n") for l in (text or "").splitlines() if l.strip() and not l.startswith("time\t") and l.count("\t") >= 5]


def merge(existing, per_host, now=None, days=7):
    """existing WAITS.tsv rows + {host: rows or None (unreadable)} -> sorted, deduplicated rows inside the window.  Pure."""
    now = time.time() if now is None else now
    cut = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now - days * 86400))
    rows = set(existing)
    for _h, rs in per_host.items():
        if rs is not None:
            rows.update(rs)
    return sorted(r for r in rows if r.split("\t", 1)[0] >= cut)


def read_host(h, timeout=60):
    """the host's ledger rows, [] when it has none, None when the host cannot be read"""
    try:
        if h in ("localhost", "hub"):
            p = os.path.expanduser(LEDGER)
            return parse(open(p).read()) if os.path.exists(p) else []
        r = subprocess.run(["timeout", str(timeout), "ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", h,
                            f"f={LEDGER}; [ -f $f ] && cat $f || echo NO-LEDGER"], capture_output=True, text=True, timeout=timeout + 15)
        if r.returncode != 0:
            return None
        return [] if r.stdout.strip() == "NO-LEDGER" else parse(r.stdout)
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("hosts", nargs="+")
    ap.add_argument("--coord", default=os.path.expanduser("~/coord"))
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    out = os.path.join(a.coord, "lanes", "WAITS.tsv")
    try:
        old_text = open(out).read()
    except OSError:
        old_text = ""
    per = {h: read_host(h) for h in a.hosts}
    rows = merge(parse(old_text), per, days=a.days)
    text = HEADER + "\n" + "".join(r + "\n" for r in rows)
    bad = sorted(h for h, v in per.items() if v is None)
    print(time.strftime("%F %T"), f"ot_wait_rollup: {len(rows)} rows from {len(per) - len(bad)} hosts" + (f"; unreadable {','.join(bad)}" if bad else ""))
    if text == old_text or a.dry_run:
        return 0
    tmp = out + f".{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, out)
    r = subprocess.run(["bash", os.path.join(a.coord, "bin/coord-commit.sh"), "WAITS rollup (ot_wait_rollup.py)", "lanes/WAITS.tsv"], capture_output=True, text=True, timeout=600)
    print((r.stdout or r.stderr).strip().splitlines()[-1:] or ["coord-commit: no output"])
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
