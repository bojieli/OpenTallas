#!/usr/bin/env python3
"""tools/geom/auto_geom.py -- standalone AUTO-GEOM run on one placed checkpoint (GEOM-AUTO-2, OWNER 2026-10-27).

OWNER 10-27: AUTO GEOM PASS for ALL core kits on measured checks; 1 in 5 PASS kits get a visual review (deterministic
hash sample); every FAIL gets a visual review.  The autopilot runs the same check as its gate before route
(tools/autopilot/auto_geom.py, AP_AUTO_GEOM_ALL=1); this CLI is for lanes and reviewers outside the queue.

    auto_geom.py HOST ODB OUTDIR [--id ID] [--outline WxH] [--mem GB] [--no-grt] [--title T]

Copies tools/autopilot/{geom_check.sh, geom_dump.tcl, geom_grt.tcl, geom_rules.py, geom_png.py} to HOST:OUTDIR/tools
and runs geom_check.sh there (docker, ODB mounted read-only; dump + >= 50-iteration GRT probe in parallel).  Output on
HOST: OUTDIR/auto_geom.json, auto_geom.png, geom.tsv, grt.log.  Prints the verdict and the GEOM REQ line to post
(tag FAIL or SAMPLE; no line for an unsampled PASS).  Checks: geom_rules.py docstring + GEOM-AUTO-2 section.
"""
import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

AP = Path(__file__).resolve().parent.parent / "autopilot"
TOOLS = ["geom_check.sh", "geom_dump.tcl", "geom_grt.tcl", "geom_rules.py", "geom_png.py"]
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none"]


def sampled(rid, mod=5):
    """same deterministic 1-in-5 hash as tools/autopilot/auto_geom.sampled"""
    return int(hashlib.sha1(f"auto-geom|{rid}".encode()).hexdigest(), 16) % mod == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("host")
    ap.add_argument("odb")
    ap.add_argument("outdir")
    ap.add_argument("--id", help="row / kit id for the sample hash (default: sha1 of the ODB path)")
    ap.add_argument("--outline", help="parent slot WxH; default = the checkpoint's own die area (slot check skipped)")
    ap.add_argument("--mem", type=int, default=24)
    ap.add_argument("--no-grt", action="store_true")
    ap.add_argument("--title", default="")
    a = ap.parse_args(argv)
    rid = a.id or hashlib.sha1(a.odb.encode()).hexdigest()[:12]
    out = a.outdir.rstrip("/")
    subprocess.run(SSH + [a.host, f"mkdir -p {shlex.quote(out)}/tools"], check=True)
    subprocess.run(["scp", "-q", "-o", "ControlPath=none"] + [str(AP / t) for t in TOOLS] + [f"{a.host}:{out}/tools/"],
                   check=True)
    ra = ["--all-kits"] + (["--outline", a.outline] if a.outline else []) + (["--title", a.title] if a.title else [])
    meta = dict(id=rid, odb=a.odb, mem_gb=a.mem, grt=not a.no_grt, rules_args=ra)
    if not a.outline:     # no slot given: compare with the checkpoint's own outline (reported as such)
        meta["rules_args"] = ra + ["--outline-self"]
    subprocess.run(SSH + [a.host, f"cat > {shlex.quote(out)}/check.json"], input=json.dumps(meta).encode(), check=True)
    p = subprocess.run(SSH + [a.host, "bash", f"{out}/tools/geom_check.sh", out], capture_output=True, text=True)
    print(p.stdout.strip()[-4000:])
    line = next((l[len("AP_AUTO_GEOM "):] for l in p.stdout.splitlines() if l.startswith("AP_AUTO_GEOM AUTO-GEOM")), "")
    if not line:
        print(f"no verdict (rc {p.returncode}): {p.stderr.strip()[-600:]}", file=sys.stderr)
        return 2
    verdict = "PASS" if line.startswith("AUTO-GEOM PASS") else "FAIL"
    tag = "FAIL" if verdict == "FAIL" else "SAMPLE" if sampled(rid) else ""
    if tag:
        print(f"\n{time.strftime('%Y-%m-%d %H:%M %Z')} GEOM REQ [AUTO-GEOM {rid}] {tag} {line[:900]} | checkpoint "
              f"{a.host}:{a.odb} rules {a.host}:{out}/auto_geom.json image {a.host}:{out}/auto_geom.png | visual review "
              f"requested ({'rule FAIL' if tag == 'FAIL' else '1-in-5 audit sample'})")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
