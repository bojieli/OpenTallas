#!/usr/bin/env python3
"""ELEM-QK 10-24: collect hold-ECO variant verdicts (signoff.json) -> OUT/<head>_<v>.json + table.
    collect_hold.py ROOT OUTDIR [HOST:ROOT ...]   (local ROOT plus remote roots via ssh cat)"""
import json, subprocess, sys
from pathlib import Path

def cat(host, p):
    r = subprocess.run(["cat", p] if host is None else ["ssh", "-n", host, f"cat {p}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def main(root, out, *remotes):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for host, r in [(None, root)] + [tuple(x.split(":", 1)) for x in remotes]:
        for e in [f"e{i}" for i in range(8)]:
            for v in "abc":
                d = f"{r}/{e}/{v}"
                rc = cat(host, f"{d}/rc.txt")
                if rc is None:
                    continue
                row = dict(head=e, variant=v, host=host or "localhost", dir=d, rc=rc.split(), verdict="NOT RUN")
                env = cat(host, f"{d}/variant.env") or ""
                row["recipe"] = " ".join(env.split())
                s = cat(host, f"{d}/signoff/signoff.json")
                if s:
                    j = json.loads(s); c = j.get("checks", {})
                    row.update(verdict=j.get("verdict"), tt_setup_ps=(c.get("setup_tt") or {}).get("wns_ps"),
                               ff_hold_ps=(c.get("hold_ff") or {}).get("wns_ps"),
                               ff_hold_viol=(c.get("hold_ff") or {}).get("violators"),
                               fails={k: x.get("verdict") for k, x in c.items() if x.get("verdict") not in ("PASS", "REPORT", "NOT RUN")})
                    (out / f"{e}_{v}_signoff.json").write_text(s)
                elif "route_finish_rc=0" not in rc:
                    row["verdict"] = "ROUTE FAIL"
                rows.append(row)
    (out / "hold_summary.json").write_text(json.dumps(rows, indent=1) + "\n")
    for x in rows:
        print(x["head"], x["variant"], x["verdict"], x.get("tt_setup_ps"), x.get("ff_hold_ps"), x.get("ff_hold_viol"), x.get("fails"))

if __name__ == "__main__":
    main(*sys.argv[1:])
