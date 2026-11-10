#!/usr/bin/python3 -I
"""gate_pass.py: ISOLATION step 4 (KW-FIX-44, COORD 17:3x): GATE PASS per die = the FIRST sealed autopilot job of that
die (any item) that reached sign-off, with 0 isolation refusals and 0 gaps.  It gates only the LEGACY DELETE.

A job counts when, all from the hub's own records:
  - autopilot state.json status ARCHIVED (signed off: signoff + routed LEC EQUIVALENT, archived, versioned) and not
    SIGNED-UNVERSIONED;
  - one of its attempt logs (jobs/<id>/a<n>.log) ran SEALED ("ot-job: SEALED") and ended through the sealed job end
    ("job dir deleted" or "keep=true"), with no "OT-JOB ISOLATION" refusal line;
  - no ISOLATE-GAPS row names its kit (the sealed shims' gap files).
  gate_pass.py [--state S] [--jobs DIR] [--gaps F ...] [--json]     -> per die: GATE PASS <job> <item> <archive>, or open
"""
import argparse
import glob
import json
import os
import sys

DIES = ("s81", "s81_head", "qwen_compute", "qwen_kvsys", "hbm")
HOME = os.path.expanduser("~")
DEF_GAPS = [HOME + "/.local/lib/fleet/kw44-seal-ap/ISOLATE-GAPS-AP.tsv", HOME + "/.local/lib/fleet/kw44-seal-ap/ISOLATE-GAPS-WAVE.tsv",
            HOME + "/.local/lib/fleet/isolate-1/ISOLATE-GAPS.tsv"]


def gap_kits(files):
    out = set()
    for f in files:
        try:
            for ln in open(f, errors="replace"):
                out.update(w for w in ln.split("\t") if w.startswith("/srv/"))
        except OSError:
            pass
    return out


def sealed_end(logs):
    """-> the attempt log that ran sealed and ended through the job end without a refusal, or None"""
    for lf in logs:
        try:
            t = open(lf, errors="replace").read()
        except OSError:
            continue
        if "ot-job: SEALED" in t and ("job dir deleted" in t or "keep=true" in t) and "OT-JOB ISOLATION" not in t \
                and "isolation_refusals" not in t:
            return lf
    return None


def kit_of(j):
    return str(j.get("kit") or "").split(":", 1)[-1]


def gate(state, jobs_dir, gaps):
    jobs = state.get("jobs", state)
    bad = gap_kits(gaps)
    per = {}
    for jid, j in jobs.items():
        if not isinstance(j, dict) or j.get("status") != "ARCHIVED" or j.get("prov_error"):
            continue
        die = j.get("die")
        K = kit_of(j)
        if die not in DIES or not K or any(g == K or g.startswith(K + "/") or K.startswith(g + "/") for g in bad):
            continue
        lf = sealed_end(sorted(glob.glob(os.path.join(jobs_dir, jid, "a*.log"))))
        if not lf:
            continue
        t = os.path.getmtime(lf)
        if die not in per or t < per[die]["t"]:
            per[die] = {"die": die, "job": jid, "type": j.get("type"), "kit": K, "archive": j.get("archive"), "log": lf, "t": t}
    return per


def main(a=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=HOME + "/coord/autopilot/state.json")
    ap.add_argument("--jobs", default=HOME + "/coord/autopilot/jobs")
    ap.add_argument("--gaps", nargs="*", default=DEF_GAPS)
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args(a)
    per = gate(json.load(open(o.state)), o.jobs, o.gaps)
    if o.json:
        print(json.dumps(per, indent=1, sort_keys=True))
        return 0
    for d in DIES:
        g = per.get(d)
        print(f"{d}\tGATE PASS\t{g['job']}\t{g['type']}\t{g['archive']}\t{g['log']}" if g else f"{d}\topen (no sealed job signed off yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
