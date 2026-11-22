#!/usr/bin/env python3
"""BIND-DOOM-1122 (FABLE-FLOW-0350 B1): a die bind that started before a pre-check landed keeps running without it.  Two QC binds
died 2.6 h and 3.3 h in on one coll_core tap name that plan_gate_pre TAPNAME (landed later) refuses in seconds.

Every tick the autopilot calls step(): it posts the findings of the last sweep and, when a sweep is due, starts one detached
(`python3 -I bind_doom.py sweep`).  A sweep lists every live `tools/die_plan/bind.py bind|elab` process on the fleet, and on that
host runs plan_gate_pre of the host's rt/current (the newest pre-checks) against the bind's own plan, tree (the process cwd) and
--asbuilt, with only the classes a bind dies of late: TAPNAME, EMITNAME and RESETPUB (COORD: QC V3 n3/cr/b2r reset edge mismatch).  A bind is re-checked when it is new (launch), when
rt/current changed (a new pre-check landed) and at least every RECHECK_S (hourly).

A FAIL posts one `BIND-DOOMED <host>:<pid> <rule>` NEEDS-ACTION to the owning lane (the scratch dir of the bind tree / out) and
writes the plan into autopilot/DOOMED-PLANS.tsv (sha256 + path + rule) so a lane composing on that plan can see it is known bad.
TAPNAME-UNCHECKED (the density base could not be solved in the bind's own tree) is logged, never posted as doomed.  Nothing
is cancelled: the owning lane decides.  Never raises into the tick."""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SWEEP_S = 600                 # a new bind is checked within ~10 min of its start
RECHECK_S = 3600              # every live bind at least hourly
CHECK_TIMEOUT_S = 900
RUN_STALE_S = 3 * 3600
STATE = "bind_doom.json"
RUNFILE = "bind_doom.run"
DOOMED_TSV = "DOOMED-PLANS.tsv"
POSTED = "bind_doom_posted.json"   # written by the tick only (a detached sweep never races the posted marks)
ONLY = ("TAPNAME", "EMITNAME", "RESETPUB")
DOOM_RE = re.compile(r"^FAIL (TAPNAME|TAPNAME-RETAP|EMITNAME|RESETPUB)[ :]")
LANE_RE = re.compile(r"^/srv/opentallas-scratch\d*/claude/([^/]+)/")
RT_DEFAULT = "/srv/opentallas-scratch2/claude/rt/current"

# runs on each host (python3 -I - <json args>): live binds + the pre-check of each one not in "skip"
REMOTE = r'''
import json, os, subprocess, sys, time, hashlib
a = json.loads(sys.argv[1])
rt = os.path.realpath(a["rt"])
pgp = os.path.join(rt, "tools", "die_plan", "plan_gate_pre.py")
classes = a["classes"]
out = {"rt": rt, "has_pgp": os.path.isfile(pgp), "binds": []}
try:
    up = float(open("/proc/uptime").read().split()[0]); hz = os.sysconf("SC_CLK_TCK")
except Exception:
    up, hz = 0.0, 100
for p in os.listdir("/proc"):
    if not p.isdigit():
        continue
    try:
        argv = open(f"/proc/{p}/cmdline", "rb").read().decode(errors="replace").split("\0")
    except OSError:
        continue
    i = next((k for k, x in enumerate(argv) if x.endswith("tools/die_plan/bind.py")), None)
    if i is None or len(argv) < i + 3 or argv[i + 1] not in ("bind", "elab"):
        continue
    try:
        cwd = os.readlink(f"/proc/{p}/cwd")
        start = int(open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()[19])
    except (OSError, ValueError, IndexError):
        continue
    rest = argv[i + 2:]
    plan = rest[0]
    opt = {}
    for k, x in enumerate(rest[:-1]):
        if x in ("--asbuilt", "--out"):
            opt[x[2:]] = rest[k + 1]
    ab = lambda f: f if not f or os.path.isabs(f) else os.path.join(cwd, f)
    plan_abs = ab(plan)
    try:
        sha = hashlib.sha256(open(plan_abs, "rb").read()).hexdigest()
    except OSError:
        continue
    b = {"pid": int(p), "start": start, "key": f"{p}@{start}", "age_s": round(up - start / hz), "sub": argv[i + 1], "cwd": cwd,
         "plan": plan_abs, "plan_sha": sha, "asbuilt": ab(opt.get("asbuilt")), "out": ab(opt.get("out")), "findings": None}
    if b["key"] + "|" + sha + "|" + rt not in a["skip"] and out["has_pgp"]:
        cmd = [sys.executable, "-I", "-B", pgp, "check", "--tree", cwd, "--plan", plan_abs, "--quiet"]
        if b["asbuilt"]:
            cmd += ["--asbuilt", b["asbuilt"]]
        for c in a["all_classes"]:
            if c not in classes:
                cmd += ["--skip", c]
        try:
            r = subprocess.run(["nice", "-n", "10", "timeout", str(a["timeout"])] + cmd, cwd=cwd, capture_output=True, text=True)
            lines = (r.stdout + r.stderr).splitlines()
            b["rc"] = r.returncode
            b["findings"] = [x for x in lines if x.startswith("FAIL ")][:20]
            b["verdict"] = next((x for x in lines if x.startswith("PLAN-GATE-PRE ")), "")[:300]
            if not b["verdict"]:
                b["error"] = "\n".join(lines[-3:])[:400]
        except OSError as e:
            b["error"] = str(e)[:300]
    out["binds"].append(b)
print(json.dumps(out))
'''

ALL_CLASSES = ("SCHEMA", "INPUT", "TOOLS", "ROWS", "GEOM", "KITFIT", "FIXEDCYC", "ROWSINK", "MODULES", "TOOLSTALE", "LANDREMAP", "ABSPATH",
               "ISTCYC", "DEADIN", "TAPNAME", "R8STALE", "RELAYSINK", "EMITNAME", "RESETPUB")


def lane_of(b, lanes=()):
    """owning lane of a bind: the claude/<dir> scratch folder of its tree or out dir, upper-cased (matched to a registry lane when one fits)"""
    for p in (b.get("cwd"), b.get("out"), b.get("plan")):
        m = LANE_RE.match(str(p or "") + "/")
        if m:
            name = m.group(1).upper()
            for ln in lanes:
                if ln.upper() == name:
                    return ln
            return name
    return ""


def doomed(b):
    """-> [finding] that kill this bind late (TAPNAME / TAPNAME-RETAP / EMITNAME FAIL lines); UNCHECKED is not doom"""
    return [x for x in (b.get("findings") or []) if DOOM_RE.match(x)]


def ssh(host, hub):
    return [] if host in ("localhost", hub) else ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=20", host]


def probe_host(host, hub, skip, rt=RT_DEFAULT, timeout=CHECK_TIMEOUT_S, run=subprocess.run):
    """one host: -> parsed REMOTE output, or {'error': ...}"""
    arg = json.dumps({"rt": rt, "classes": list(ONLY), "all_classes": list(ALL_CLASSES), "skip": sorted(skip), "timeout": timeout})
    cmd = ssh(host, hub)
    if cmd:                                       # remote: the code goes as one quoted argument
        import shlex
        cmd = cmd + ["cd / && python3 -I -c " + shlex.quote(REMOTE) + " " + shlex.quote(arg)]
    else:
        cmd = ["python3", "-I", "-c", REMOTE, arg]
    try:
        r = run(cmd, capture_output=True, text=True, timeout=RUN_STALE_S - 600, cwd="/")
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {"error": (r.stderr or "")[-300:]}
    except (subprocess.TimeoutExpired, ValueError, IndexError, OSError) as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


def merge(state, host, res, now):
    """fold one host's probe into state['binds'] (key host|pid@start); binds gone from the host are dropped"""
    binds = state.setdefault("binds", {})
    if res.get("error"):
        state.setdefault("errors", {})[host] = res["error"]
        return
    state.setdefault("errors", {}).pop(host, None)
    live = set()
    for b in res.get("binds") or []:
        k = f"{host}|{b['key']}"
        live.add(k)
        old = binds.get(k) or {}
        b["host"] = host
        if b.get("findings") is None:             # skipped (already checked on this rt + plan): keep the last result
            for f in ("findings", "verdict", "rc", "checked_t", "rt"):
                if f in old:
                    b[f] = old[f]
        else:
            b["checked_t"], b["rt"] = now, res.get("rt")
        binds[k] = b
    for k in [k for k in binds if k.startswith(host + "|") and k not in live]:
        del binds[k]


def skip_set(state, host, now):
    """bind keys whose check is current: same plan sha and rt, checked < RECHECK_S ago"""
    out = set()
    for k, b in (state.get("binds") or {}).items():
        if b.get("host") == host and b.get("checked_t") and now - float(b["checked_t"]) < RECHECK_S:
            out.add(f"{b['key']}|{b.get('plan_sha')}|{b.get('rt')}")
    return out


def sweep(ap_dir, hosts, hub, rt=RT_DEFAULT, probe=probe_host, now=None):
    ap_dir = Path(ap_dir)
    p = ap_dir / STATE
    try:
        state = json.loads(p.read_text())
    except (OSError, ValueError):
        state = {}
    from concurrent.futures import ThreadPoolExecutor
    now = now or time.time()
    with ThreadPoolExecutor(max_workers=max(1, len(hosts))) as ex:
        res = dict(zip(hosts, ex.map(lambda h: probe(h, hub, skip_set(state, h, now), rt), hosts)))
    for h, r in res.items():
        merge(state, h, r, now)
    state["swept_t"] = now
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    os.replace(tmp, p)
    return state


def posts(state, posted, lanes=()):
    """-> [(bind key, lane, line text)] for doomed binds not yet posted for this plan sha; marks them in posted {key: plan sha}"""
    out = []
    for k in [k for k in posted if k not in (state.get("binds") or {})]:
        del posted[k]
    for k, b in sorted((state.get("binds") or {}).items()):
        d = doomed(b)
        if not d or posted.get(k) == b.get("plan_sha"):
            continue
        lane = lane_of(b, lanes)
        rules = sorted({x.split()[1] for x in d})
        txt = (f"BIND-DOOMED {b['host']}:{b['pid']} {'+'.join(rules)} ({b.get('sub')} {round(float(b.get('age_s') or 0) / 3600, 1)} h in, plan "
               f"{b.get('plan')} sha {str(b.get('plan_sha'))[:12]}, tree {b.get('cwd')}): plan_gate_pre of rt {Path(str(b.get('rt') or '')).name} "
               f"refuses this plan, so the bind will die at the same check: " + " | ".join(x[:300] for x in d[:3])
               + f" -- cancel it and fix the plan; DOOMED-PLANS.tsv marks this plan sha so no lane composes on it")
        posted[k] = b.get("plan_sha")
        out.append((k, lane, txt))
    return out


def doomed_rows(state, old_text=""):
    """DOOMED-PLANS.tsv text: one row per (plan sha, rule), kept across sweeps"""
    head = "plan_sha256\tplan\trule\thost_pid\tfirst_seen\n"
    rows = {}
    for ln in (old_text or "").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) >= 5:
            rows[(f[0], f[2])] = ln
    for b in (state.get("binds") or {}).values():
        for x in doomed(b):
            r = x.split()[1]
            rows.setdefault((b["plan_sha"], r), "\t".join([b["plan_sha"], b["plan"], r, f"{b['host']}:{b['pid']}",
                                                           time.strftime("%Y-%m-%d %H:%M")]))
    return head + "".join(v + "\n" for _, v in sorted(rows.items()))


def due(state, now, rt_now=None):
    """a sweep is due SWEEP_S after the last one, or at once when rt/current moved (a new pre-check landed)"""
    if not state.get("swept_t") or now - float(state["swept_t"]) >= SWEEP_S:
        return True
    return bool(rt_now and state.get("rt_seen") and state["rt_seen"] != rt_now)


def step(AP):
    """autopilot tick: post the last sweep's findings; start a detached sweep when due.  Never raises."""
    try:
        ap_dir = Path(AP.AP_DIR)
        p = ap_dir / STATE
        try:
            state = json.loads(p.read_text())
        except (OSError, ValueError):
            state = {}
        try:
            lanes = [ln.split("\t")[0] for ln in AP.read_coord("lanes/agent_ids.tsv").splitlines() if ln.strip()]
        except Exception:
            lanes = []
        pp = ap_dir / POSTED
        try:
            posted = json.loads(pp.read_text())
        except (OSError, ValueError):
            posted = {}
        new = posts(state, posted, lanes)
        for _k, lane, txt in new:
            AP.coord_append("lanes/COORD-REVIEW-QUEUE.md",
                            f"- {time.strftime('%Y-%m-%d %H:%M %Z')} NEEDS-ACTION [AUTOPILOT -> {lane or 'COORD'}, COORD] {txt}"[:2000])
            AP.log(f"BIND-DOOM {txt[:300]}")
        if new:
            tsv = ap_dir / DOOMED_TSV
            tsv.write_text(doomed_rows(state, tsv.read_text() if tsv.exists() else ""))
        n_unc = sum(1 for b in (state.get("binds") or {}).values() if any("UNCHECKED" in x for x in b.get("findings") or []))
        now = time.time()
        rt_now = os.path.realpath(os.environ.get("OT_RT_CURRENT") or RT_DEFAULT)
        if due(state, now, rt_now) and not AP.DRY:
            run = ap_dir / RUNFILE
            if not (run.exists() and now - run.stat().st_mtime < RUN_STALE_S):
                run.write_text(str(os.getpid()))
                hosts = [h for h in os.environ.get("OT_FLEET_HOSTS", "intel2,intel1,epyc2,epyc7,epyc8,epyc9,epyc10").split(",") if h]
                subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve()), "sweep", str(ap_dir), ",".join(hosts), str(AP.HUB_NAME)],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                AP.log(f"BIND-DOOM sweep started ({len(hosts)} hosts, rt {Path(rt_now).name}; {len(state.get('binds') or {})} bind(s) known, "
                       f"{sum(1 for b in (state.get('binds') or {}).values() if doomed(b))} doomed, {n_unc} unchecked)")
        if new or posted:
            pp.write_text(json.dumps(posted))
    except Exception as e:
        AP.log(f"BIND-DOOM skipped: {type(e).__name__}: {e}")


def main(argv):
    if len(argv) >= 4 and argv[0] == "sweep":
        ap_dir, hosts, hub = argv[1], [h for h in argv[2].split(",") if h], argv[3]
        try:
            st = sweep(ap_dir, hosts, hub)
            st["rt_seen"] = os.path.realpath(os.environ.get("OT_RT_CURRENT") or RT_DEFAULT)
            Path(ap_dir, STATE).write_text(json.dumps(st, indent=1))
        finally:
            try:
                Path(ap_dir, RUNFILE).unlink()
            except OSError:
                pass
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
