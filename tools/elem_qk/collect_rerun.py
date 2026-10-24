#!/usr/bin/env python3
"""ELEM-QK 10-24: collect re-run verdicts (route status + signoff.json) from the run hosts into
results/elem_qk_1024/rerun/<kit>/ (signoff.json, route_rc) and a summary table results/elem_qk_1024/rerun_summary.json.
    collect_rerun.py HOSTS_TXT LIST_TXT OUTDIR"""
import json
import subprocess
import sys
from pathlib import Path


def fetch(h, path):
    cmd = ["cat", path] if h == "localhost" else ["ssh", "-n", h, f"cat {path}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main(hosts_txt, list_txt, out):
    out = Path(out)
    mods = {l.split()[2]: (l.split()[0], l.split()[1], l.split()[4]) for l in open(list_txt) if l.strip()}
    loc = {}
    for l in open(hosts_txt):
        f = l.split()
        if len(f) >= 3 and f[2].startswith("/"):
            loc[f[0]] = (f[1], f[2])
    loc.setdefault("qkd_hp_or2", ("epyc3", "/srv/opentallas-scratch/claude/elem-qk/rerun/qkd_hp_or2"))
    rows = []
    for kit, (die, mod, sha) in mods.items():
        h, d = loc[kit]
        rc = fetch(h, f"{d}/cl/route_rc") or ""
        so = fetch(h, f"{d}/signoff/signoff.json")
        kd = out / "rerun" / kit
        kd.mkdir(parents=True, exist_ok=True)
        (kd / "route_rc").write_text(rc)
        row = dict(die=die, module=mod, kit=kit, source_commit=sha, host=h, run_dir=d,
                   route_ok="route_ok=1" in rc, verdict="NOT RUN")
        if so:
            (kd / "signoff.json").write_text(so)
            s = json.loads(so)
            c = s.get("checks", {})
            g = lambda k, f="slack_ps": (c.get(k) or {}).get(f)
            row.update(verdict=s.get("verdict"), reasons=s.get("reasons"),
                       tt_setup_ps=g("setup_tt"), ff_hold_ps=g("hold_ff"),
                       checks={k: (v or {}).get("verdict") for k, v in c.items()})
        elif rc:
            row["verdict"] = "ROUTE FAIL" if "route_ok=0" in rc else "NOT RUN"
        rows.append(row)
    (out / "rerun_summary.json").write_text(json.dumps(rows, indent=1) + "\n")
    for r in rows:
        print(r["kit"], r["verdict"], r.get("tt_setup_ps"), r.get("ff_hold_ps"),
              {k: v for k, v in (r.get("checks") or {}).items() if v not in ("PASS", None)})


if __name__ == "__main__":
    main(*sys.argv[1:])
