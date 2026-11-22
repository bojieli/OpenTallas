#!/usr/bin/env python3
"""host_caps.py [--hosts h1,h2,..] [--now ISO] [--conf FILE]   (FLOW-FLEET-R1 11-22, FABLE-FLOW-2200 H2)

Hand-set host admission caps must carry an owner and an expiry.  A cap left behind by a lane that stood down (epyc7
THREAD_CAP_FACTOR=1.0, 11-22 05:1x) refused 31 admits at load 50/96 before anyone noticed.

CONVENTION, in /etc/ot-heavy.conf: the line directly above a cap override is
    #@cap KEY owner=LANE expires=YYYY-MM-DDTHH:MMZ why=free text (what to revert to on expiry)
`expires` is UTC (a trailing Z, or an explicit +hh:mm offset).  A cap is a key of CAP_KEYS set to a value other than
its off value (0).  Rails (memory headroom, disk floors, OOM guards) are not caps and are never flagged.

Verdicts, one line per finding:  CAP-EXPIRED host KEY=val owner expires (age)  |  CAP-UNOWNED host KEY=val (no #@cap line)
| CAP-BADTAG host KEY (tag present, owner or expires missing/unparseable)  |  CAP-OK host KEY=val owner expires (left).
Prints "HOST-CAPS ok" or "HOST-CAPS N flagged: ..." as the last line (the hourly host report appends it).  Read-only.
Exit 0 always (a report, not a gate); --strict exits 1 when anything is flagged.
"""
import argparse, datetime as dt, re, socket, subprocess, sys

CAP_KEYS = {"THREAD_CAP_FACTOR": "0", "LOAD_CAP_FACTOR": "0", "LOAD_GATE_FACTOR": "0"}
HOSTS = ["intel2", "intel1", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10"]
TAG = re.compile(r"^#@cap\s+(\w+)\s*(.*)$")


def parse_time(s):
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else None


def scan(text, now):
    """-> [(verdict, key, value, owner, expires, note)] for the caps of one conf text (pure: tests call it)"""
    out, tag = [], None
    for ln in text.splitlines():
        s = ln.strip()
        m = TAG.match(s)
        if m:
            kv = dict(re.findall(r"(\w+)=(\S+)", m.group(2).split(" why=")[0]))
            tag = (m.group(1), kv.get("owner"), kv.get("expires"))
            continue
        if not s or s.startswith("#") or "=" not in s:
            if not s.startswith("#"):
                tag = None
            continue
        key, val = s.split("=", 1)
        val = val.split("#", 1)[0].strip()
        t, tag = tag, None
        if key not in CAP_KEYS:
            continue
        try:
            off = float(val) == float(CAP_KEYS[key])
        except ValueError:
            off = False
        if off:
            continue
        if not t or t[0] != key:
            out.append(("CAP-UNOWNED", key, val, None, None, "no #@cap line"))
            continue
        exp = parse_time(t[2] or "")
        if not t[1] or exp is None:
            out.append(("CAP-BADTAG", key, val, t[1], t[2], "owner/expires missing or unparseable"))
        elif exp <= now:
            out.append(("CAP-EXPIRED", key, val, t[1], t[2], "expired %.1f h ago" % ((now - exp).total_seconds() / 3600)))
        else:
            out.append(("CAP-OK", key, val, t[1], t[2], "%.1f h left" % ((exp - now).total_seconds() / 3600)))
    return out


def read_conf(host, conf):
    local = host in ("localhost", socket.gethostname().split(".")[0])
    cmd = ["cat", conf] if local else \
          ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ControlPath=none", host, "cat", conf]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout if r.returncode == 0 else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hosts", default=",".join(HOSTS))
    ap.add_argument("--now")
    ap.add_argument("--conf", default="/etc/ot-heavy.conf")
    ap.add_argument("--file", help="scan one local file (label 'file'), no ssh")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    now = parse_time(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    flagged, ok = [], 0
    targets = [("file", a.file)] if a.file else [(h, None) for h in a.hosts.split(",") if h]
    for host, path in targets:
        text = open(path).read() if path else read_conf(host, a.conf)
        if text is None:
            print(f"CAP-UNREAD {host} {a.conf}")
            flagged.append(f"{host}:unread")
            continue
        for v, key, val, owner, exp, note in scan(text, now):
            print(f"{v} {host} {key}={val} owner={owner or '-'} expires={exp or '-'} ({note})")
            if v == "CAP-OK":
                ok += 1
            else:
                flagged.append(f"{host}:{key}={val}:{v[4:]}")
    print(f"HOST-CAPS {len(flagged)} flagged: {' '.join(flagged)}" if flagged else f"HOST-CAPS ok ({ok} owned caps)")
    return 1 if (a.strict and flagged) else 0


if __name__ == "__main__":
    sys.exit(main())
