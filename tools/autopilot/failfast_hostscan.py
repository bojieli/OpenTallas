#!/usr/bin/env python3
"""failfast_hostscan.py -- host side of failfast_scan.py (FAILFAST-1): READ-ONLY.  Lists the OpenROAD route/CTS jobs of this
host, finds each one's kit (the /work mount of its container), and judges its log with the same functions the kit wrapper
uses (physical/common_flow/failfast_rules.py).  Opens files for reading only; sends no signal; writes nothing.
Sent over ssh as a payload (rules module first, as the `failfast_rules` module); prints one JSON document.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

import failfast_rules as R

WAVE_RX = re.compile(r"/kit-wave/([^/\s]+)/([^/\s]+)/items/([^/\s]+)(?:/attempt_(\d+))?(?=[/\s]|$)")
STAGE_OF = (("global_route.tcl", "GRT"), ("detail_route.tcl", "DRT"), ("cts.tcl", "CTS"))


def sh(cmd, timeout=60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def openroad_jobs():
    """[{pid, etimes, stage, cid}] of openroad processes running a watched stage script"""
    out = []
    for ln in sh(["ps", "-eo", "pid,etimes,args"]).splitlines()[1:]:
        f = ln.split(None, 2)
        if len(f) < 3 or not f[0].isdigit() or "/bin/openroad" not in f[2].split(" ", 1)[0]:
            continue
        st = next((s for k, s in STAGE_OF if k in f[2]), None)
        if not st:
            continue
        cid = None
        try:
            m = re.search(r"docker-([0-9a-f]{64})\.scope", open("/proc/%s/cgroup" % f[0]).read())
            cid = m[1] if m else None
        except OSError:
            pass
        out.append({"pid": int(f[0]), "etimes": int(f[1]), "stage": st, "cid": cid})
    return out


def containers(cids):
    """{cid: {name, work, started}} from one docker inspect"""
    ids = sorted({c for c in cids if c})
    if not ids:
        return {}
    try:
        info = json.loads(sh(["docker", "inspect"] + ids, 120) or "[]")
    except ValueError:
        return {}
    res = {}
    for c in info:
        work = next((m.get("Source") for m in c.get("Mounts", []) if m.get("Destination") == "/work"), None)
        st = c.get("State", {}).get("StartedAt", "")
        try:
            started = time.mktime(time.strptime(st[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        except ValueError:
            started = 0
        res[c["Id"]] = {"name": c.get("Name", "").lstrip("/"), "work": work, "started": started}
    return res


def item_key(work, name):
    """(key, plan_sha, wave?) of a job: the kit-wave (die, event, item), else the container name without its pid"""
    m = WAVE_RX.search(work or "")
    nm = re.sub(r"^dpkit-", "", name or "")
    nm = re.sub(r"-\d+(-lec)?$", "", nm)
    sha = re.search(r"__(?:cl|pv|physical_v)([0-9a-f]{6,})", nm)
    if m:
        return "wave:%s/%s/%s" % (m[1], m[2], m[3]), (sha[1] if sha else ""), True, int(m[4] or 1)
    return "name:" + nm, (sha[1] if sha else ""), False, 0


def judge_ro(job, cont, now):
    work = cont["work"]
    cfgt = ""
    try:
        cfgt = open(os.path.join(work, "config.mk"), errors="replace").read()
    except OSError:
        pass
    c = R.config_values({}, cfgt)
    lg, rp = R._dirs(work)
    row = {"stage": job["stage"], "kit": work, "log": None, "verdicts": []}
    if not lg:
        return row
    t0 = (cont["started"] or now - job["etimes"]) - 60
    logs = {os.path.basename(p): p for p in R._fresh(glob.glob(os.path.join(lg, "*.log")), t0)}
    cts = [p for n, p in logs.items() if n.startswith("4_1_cts")]
    grt = [p for n, p in logs.items() if n.startswith("5_1_grt")]
    drt = [p for n, p in logs.items() if n.startswith("5_2_route")]
    caps, stall, stage = 0, None, "cts"
    for p in sorted(cts + grt):
        s = R.scan_lines(R._read_lines(p))
        caps += s["caps"]
        if s["caps"] and p in grt:
            stage = "grt"
        if s["stall"] and not stall:
            stall, stage = s["stall"], "cts" if p in cts else "grt"
    row["hold_caps"], row["hold_stall"] = caps, stall
    d = R.hold_decide(caps, stall, c, cfgt)
    if d:
        row["verdicts"].append({"rule": "HOLD_STRUCTURAL", "evidence": R.hold_line(d, stage, stamp=False)
                                + (" [LATE: the build is already in detailed route]" if job["stage"] == "DRT" else ""),
                                "log": sorted(cts + grt)[-1], "late": job["stage"] == "DRT"})
    for p in sorted(drt):
        s = R.scan_lines(R._read_lines(p))
        row["drt_iters"] = len(s["drt"])
        row["drt_tail"] = [v for _l, v in s["drt"][-4:]]
        row["log"] = p
        d = R.drt_decide(s["drt"], c)
        if d:
            row["verdicts"].append({"rule": "DRT_NO_PROGRESS", "evidence": R.drt_line(d, stamp=False), "log": p})
    tmp = [p for p in grt if os.path.basename(p).startswith("5_1_grt.tmp")] or grt
    if tmp:                                  # GRT: statistics only; no GRT rule exists (deleted 11-14, OWNER)
        p = sorted(tmp)[-1]
        row["log"] = p
        s = R.scan_lines(R._read_lines(p))
        cum, cur, prev_len, rounds = R.iteration_state(s["iters"])
        row.update(grt_iters=cum, grt_cur="%d/%d" % (cur, s["iters"][-1][1]) if s["iters"] else "-", grt_rounds=rounds + (1 if cur else 0),
                   grt_ndr=s["ndr"], grt_in_route=bool(s["iters"]) and not s["final"])
    return row


def main():
    now = time.time()
    jobs = openroad_jobs()
    conts = containers([j["cid"] for j in jobs])
    rows = []
    for j in jobs:
        cont = conts.get(j["cid"])
        if not cont or not cont["work"]:
            rows.append({"pid": j["pid"], "stage": j["stage"], "etimes": j["etimes"], "note": "no docker /work mount"})
            continue
        key, sha, wave, att = item_key(cont["work"], cont["name"])
        try:
            r = judge_ro(j, cont, now)
        except Exception as e:                         # never let one kit hide the others
            r = {"stage": j["stage"], "kit": cont["work"], "verdicts": [], "error": repr(e)[:200]}
        r.update(pid=j["pid"], etimes=j["etimes"], name=cont["name"], key=key, plan_sha=sha, wave=wave, attempt=att,
                 age_h=round((now - cont["started"]) / 3600.0, 1) if cont["started"] else None)
        rows.append(r)
    print(json.dumps({"host": os.uname().nodename, "time": now, "rows": rows}))


if __name__ == "__main__":
    main()
