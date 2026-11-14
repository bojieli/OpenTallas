#!/usr/bin/env python3
"""Re-judge existing routed attempts under R-MINIMAL + R-PERIOD (OWNER 2026-11-13; tools/die_plan/signoff_profile.py).

Sources of routed attempts (all dies except HBM, which is parked):
  - the autopilot state (~/coord/autopilot/state.json): every job's sign-off record, its late-ECO best / iteration
    records and its chain record;
  - a filesystem scan of every fleet host (--scan): every */signoff*/signoff.json under /srv/opentallas-scratch*/claude
    newer than --days (hand builds, ECO dirs, lane re-signs that never went through the autopilot queue).
Each signoff.json is re-read ON ITS HOST (one ssh per host, this file streamed as the reader) and judged by
signoff_profile.judge(): DRC 0, TT setup WNS at 833 ps >= -(P_die - 833) - 42 (P_die 1000 ps by default), internal FF
hold >= 0 (a port-start-only hold miss is the io_hold_parent advisory).  Bind + LATCHECK are kit / die level (a routed
record exists only for a bound kit); the token pass is die level.

  rejudge_minimal.py run --state STATE.json --hosts intel1,intel2,... [--scan] [--days 21] --out DIR
      -> DIR/rejudge.tsv (one row per record), DIR/signed_types.tsv (best signed record per die/type),
         DIR/summary.json (per-die counts, achieved periods, die max period)
  rejudge_minimal.py read PATH...      (host side: compact JSON per record on stdout)
  rejudge_minimal.py scan ROOT DAYS    (host side: signoff.json paths)
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = set()          # hosts read in-process (the hub itself: ssh to self is not set up on intel2)
DIES = ("s81", "s81_head", "qwen_compute", "qwen_kvsys")
ALIAS = {"qc": "qwen_compute", "kv": "qwen_kvsys", "cp1": "s81", "results": "s81_head", "head": "s81_head"}
KEEP_CHECKS = ("drc", "setup_tt", "hold_ff", "antenna", "drv", "clock", "pg", "io_hold_parent", "sdc_lint", "face_guard",
               "unconstrained", "lec_superset", "timing_modes", "macro_libs", "ft_interface")


def compact(rec):
    """the fields signoff_profile.judge() and the report need, small enough to ship back over ssh"""
    ch = {}
    for k in KEEP_CHECKS:
        v = (rec.get("checks") or {}).get(k)
        if isinstance(v, dict):
            ch[k] = {x: v.get(x) for x in ("verdict", "count", "wns_ps", "sdc_wns_ps", "port_only_needs_parent",
                                           "violators") if x in v}
    return dict(verdict=rec.get("verdict"), local_verdict=rec.get("local_verdict"), name=rec.get("name"),
                checks=ch, reasons=(rec.get("reasons") or [])[:12], route=rec.get("route") or {},
                kit=(rec.get("inputs") or {}).get("kit"), base=(rec.get("inputs") or {}).get("base"),
                created=rec.get("created") or rec.get("time") or rec.get("finished"))


def cmd_read(paths):
    for p in paths:
        try:
            rec = json.loads(Path(p).read_text())
            out = compact(rec)
            out["mtime"] = Path(p).stat().st_mtime
        except (OSError, ValueError) as e:
            out = dict(error=f"{type(e).__name__}: {e}"[:200])
        out["path"] = p
        print(json.dumps(out))


def cmd_scan(root, days):
    days = float(days)
    for r in root.split(","):
        if not os.path.isdir(r):
            continue
        p = subprocess.run(["find", r, "-xdev", "-name", "signoff.json", "-path", "*/signoff*", "-mtime", f"-{days:g}",
                            "-not", "-path", "*/hbm/*"], capture_output=True, text=True, timeout=1500)
        for line in p.stdout.splitlines():
            print(line)


# ---- hub side ---------------------------------------------------------------------------------------------------------
def die_of(x):
    d = str(x or "").lower()
    return ALIAS.get(d, d)


PATH_RE = re.compile(r"/kit-wave/(s81_head|s81|qwen_compute|qwen_kvsys|hbm)/[^/]+/items/([^/]+)/attempt_(\d+)/")


def type_of_path(p):
    m = PATH_RE.search(p)
    if m:
        return m.group(1), m.group(2), int(m.group(3))
    m = re.search(r"/(?:kits|gen)/([^/]+)/(?:signoff|eco_)", p)
    return None, (m.group(1) if m else None), None


def jobs_records(state):
    """[(path, host, job)] from the autopilot state"""
    out = []
    for j in (state.get("jobs") or {}).values():
        die = die_of(j.get("die"))
        if die not in DIES:
            continue
        host = j.get("probe") or j.get("host")
        so = j.get("signoff") if isinstance(j.get("signoff"), dict) else {}
        ch = j.get("chain") if isinstance(j.get("chain"), dict) else {}
        eco = ch.get("eco") if isinstance(ch.get("eco"), dict) else {}
        paths = [so.get("path"), ch.get("signoff"), (eco.get("best") or {}).get("signoff")]
        paths += [it.get("signoff") for it in eco.get("iterations") or [] if isinstance(it, dict)]
        for p in dict.fromkeys(x for x in paths if x):
            out.append((p, host, j))
    return out


def ssh_read(host, paths, timeout=1800, chunk=250):
    paths = sorted(set(paths))
    if len(paths) > chunk:
        return [r for i in range(0, len(paths), chunk) for r in ssh_read(host, paths[i:i + chunk], timeout, chunk)]
    if not paths:
        return []
    me = Path(__file__).read_text()
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=20", host,
           "python3 -I - read " + " ".join(sorted(set(paths)))] if host not in LOCAL | {"localhost"} else \
          [sys.executable, "-I", "-", "read"] + sorted(set(paths))
    try:
        p = subprocess.run(cmd, input=me, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return [dict(path=x, error="ssh timeout", host=host) for x in paths]
    rows = []
    for line in p.stdout.splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        r["host"] = host
        rows.append(r)
    got = {r["path"] for r in rows}
    rows += [dict(path=x, host=host, error=f"unreadable host ({p.returncode}: {p.stderr.strip()[-120:]})")
             for x in paths if x not in got]
    return rows


def ssh_scan(host, roots, days):
    me = Path(__file__).read_text()
    try:
        cmd = (["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=20", host,
                f"python3 -I - scan {roots} {days}"] if host not in LOCAL | {"localhost"} else
               [sys.executable, "-I", "-", "scan", roots, str(days)])
        p = subprocess.run(cmd, input=me, capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return []
    return [x for x in p.stdout.splitlines() if x.startswith("/")]


def cmd_run(a):
    sys.path.insert(0, str(HERE))
    import signoff_profile as SP
    from concurrent.futures import ThreadPoolExecutor
    LOCAL.update(h for h in (a.local or "").split(",") if h)
    state = json.loads(Path(a.state).read_text())
    hosts = [h for h in a.hosts.split(",") if h]
    want = collections.defaultdict(set)
    meta = {}
    for p, host, j in jobs_records(state):
        want[host].add(p)
        meta.setdefault((host, p), j)
    if a.scan:
        with ThreadPoolExecutor(len(hosts)) as ex:
            for h, found in zip(hosts, ex.map(lambda h: ssh_scan(h, a.roots, a.days), hosts)):
                want[h].update(found)
    with ThreadPoolExecutor(max(1, len(want))) as ex:
        rows = [r for rs in ex.map(lambda h: ssh_read(h, list(want[h])), list(want)) for r in rs]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = []
    for r in rows:
        j = meta.get((r["host"], r["path"])) or {}
        die, typ, att = type_of_path(r["path"])
        die = die_of(j.get("die")) if j.get("die") else die
        typ = j.get("type") or typ or r.get("name")
        if die not in DIES:
            continue
        if r.get("error"):
            so = j.get("signoff") if isinstance(j.get("signoff"), dict) and j["signoff"].get("path") == r["path"] else None
            if not so:
                res.append(dict(die=die, type=typ, attempt=att, host=r["host"], path=r["path"], job=j.get("id", ""),
                                job_status=j.get("status", ""), verdict="UNREADABLE", reasons=[r["error"]],
                                source="none"))
                continue
            rec, source = dict(so, die=die), "autopilot summary (record unreadable: " + r["error"][:60] + ")"
        else:
            rec, source = dict(r, die=die), "signoff.json"
        jm = SP.judge(rec, die=die)
        res.append(dict(die=die, type=typ, attempt=att, host=r["host"], path=r["path"], job=j.get("id", ""),
                        job_status=j.get("status", ""), verdict=jm["verdict"], legacy=rec.get("verdict"),
                        drc=jm["drc"], tt=jm["tt_wns_ps"], ff=jm["ff_hold_wns_ps"], port_only=jm.get("hold_port_only"),
                        period=jm["achieved_period_ps"], reasons=jm["reasons"], advisories=jm["advisories"][:6],
                        source=source, mtime=r.get("mtime")))
    cols = ("die", "type", "attempt", "verdict", "legacy", "drc", "tt", "ff", "port_only", "period", "job", "job_status",
            "host", "path", "source", "reasons", "advisories")
    with (out / "rejudge.tsv").open("w") as f:
        f.write("\t".join(cols) + "\n")
        for x in sorted(res, key=lambda x: (x["die"], str(x["type"]), str(x["path"]))):
            f.write("\t".join("; ".join(map(str, x.get(c) or [])) if isinstance(x.get(c), list) else str(x.get(c, ""))
                              for c in cols) + "\n")
    best = {}
    for x in res:
        if x["verdict"] != "SIGNED":
            continue
        k = (x["die"], x["type"])
        if k not in best or (x["period"] or 9e9) < (best[k]["period"] or 9e9):
            best[k] = x
    with (out / "signed_types.tsv").open("w") as f:
        f.write("die\ttype\tperiod_ps\ttt_wns\tff_hold\tlegacy_verdict\tjob\tjob_status\thost\tpath\tadvisories\n")
        for k in sorted(best):
            x = best[k]
            f.write(f"{x['die']}\t{x['type']}\t{x['period']}\t{x['tt']}\t{x['ff']}\t{x['legacy']}\t{x['job']}\t"
                    f"{x['job_status']}\t{x['host']}\t{x['path']}\t{'; '.join(x['advisories'])}\n")
    summ = {}
    for d in DIES:
        xs = [x for x in res if x["die"] == d]
        types = {x["type"] for x in xs}
        sig = {k: v for k, v in best.items() if k[0] == d}
        newly = {k for k, v in sig.items() if v["legacy"] not in ("SIGNED",)}
        summ[d] = dict(records=len(xs), unreadable=sum(x["verdict"] == "UNREADABLE" for x in xs), types=len(types),
                       signed_types=len(sig), signed_types_legacy_not_signed=len(newly),
                       die_period_ps=SP.die_period_ps(d),
                       die_max_achieved_period_ps=max([v["period"] for v in sig.values() if v["period"]] or [None],
                                                      key=lambda v: v or 0))
    (out / "summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps(summ, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read")
    r.add_argument("paths", nargs="*")
    s = sub.add_parser("scan")
    s.add_argument("roots")
    s.add_argument("days")
    u = sub.add_parser("run")
    u.add_argument("--state", required=True)
    u.add_argument("--hosts", required=True)
    u.add_argument("--scan", action="store_true")
    u.add_argument("--roots", default="/srv/opentallas-scratch/claude,/srv/opentallas-scratch2/claude,"
                                       "/srv/opentallas-scratch3/claude")
    u.add_argument("--days", default="21")
    u.add_argument("--local", default="", help="hosts to read in-process (the hub this runs on)")
    u.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "read":
        return cmd_read(a.paths)
    if a.cmd == "scan":
        return cmd_scan(a.roots, a.days)
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
