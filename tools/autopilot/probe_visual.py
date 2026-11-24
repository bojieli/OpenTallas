"""probe_visual.py -- PROBE-THROUGH kits feed lanes/VISUAL-QUEUE.tsv (VIS-REOWN, COORD flow review 11-24 08:55).

COORD 08:04 ruling (2) turned past-SLA DRAFT / PRE-PASS rows of lanes/VIS-COVERAGE.tsv into PROBE-THROUGH: lbl_gate admits
their kits, so they place, route and sign off with no review on the way.  This module lists, for every PROBE-THROUGH type,
ONE kit of the type's CURRENT plan that has reached place (a geom dir exists) and is not finished, so
kit_wave.visual_queue_publish adds it to lanes/VISUAL-QUEUE.tsv (same 8 columns; state WAIT-VISUAL-PROBE-PLACE / -GRT,
-FAILED for a failed kit, '@<plan sha12>' appended so the reviewer sees which plan the render is).

CURRENT PLAN (COORD 11-24 10:1x correction: an mtime pick reviewed old N46C/R6V2 kits instead of the C1h probes, 8 good kits
were cancelled): every candidate kit carries a plan identity = sha256[:12] of its plan file (private spec 'plan' on its gen host;
a wave record of the die's current event -> the die plan).  The type's current plan is the plan of its most recently LAUNCHED
kit (spec created / record started), never the newest file mtime.  Only kits of that plan are listed; when none of them has a
render yet the type is not listed (the older-plan render would be reviewed against the wrong form).  Wave records of an older
event than the die's current one are never candidates.
The list is advisory: it never holds, cancels or launches anything (OWNER: probes never wait, review never blocks).
Stdlib only.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) if os.path.dirname(os.path.abspath(__file__)) not in sys.path else None
import lbl_gate as LBL  # noqa: E402

MAX_AGE_S = 48 * 3600
GRT_STAGES = ("grt", "route", "finish", "signoff", "lec", "cts")
DONE_STATUS = ("SIGNED", "FAIL", "CANCELLED")
SHA_CACHE = os.path.expanduser(os.environ.get("OT_PROBE_VISUAL_SHA_CACHE", "~/.local/state/probe_visual/plan_sha.json"))


def probe_types(coord):
    try:
        with open(os.path.join(coord, LBL.REL), encoding="utf-8", errors="replace") as f:
            return LBL.parse(f.read())
    except OSError:
        return []


def is_probe_through(vis, die, item):
    return LBL.lookup(vis, item, die)[0] == "PROBE-THROUGH"


def _row(die, item, family, attempt, state, kit, geom_dir):
    host = kit.partition(":")[0] if ":" in kit else (geom_dir.partition(":")[0] if ":" in geom_dir else "")
    return (die, item, family, str(attempt), state, f"{kit}/run/layout_review" if kit else "",
            f"{geom_dir}/auto_geom.png" if geom_dir else "", host)


def file_sha(path, host=None, timeout=20):
    """sha256[:12] of a plan file: local when readable, else `sha256sum` over ssh on host; None when unreadable"""
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:12]
    except OSError:
        pass
    if not host:
        return None
    try:
        p = subprocess.run(["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host,
                            f"sha256sum {path}"], capture_output=True, text=True, timeout=timeout)
        m = re.match(r"([0-9a-f]{64})\s", p.stdout or "")
        return m.group(1)[:12] if m else None
    except (OSError, subprocess.SubprocessError):
        return None


class ShaCache:
    """plan-file sha per (host, path, spec key); a spec's plan never changes once written, so entries are kept"""
    def __init__(self, path=SHA_CACHE, hasher=file_sha):
        self.path, self.hasher = path, hasher
        try:
            self.d = json.load(open(path))
        except (OSError, ValueError):
            self.d = {}
        self.dirty = False

    def get_many(self, reqs):
        """reqs: {key: (path, host)} -> {key: sha or None}; unknown keys hashed in parallel"""
        todo = {k: v for k, v in reqs.items() if k not in self.d}
        if todo:
            with ThreadPoolExecutor(16) as ex:
                for k, sha in zip(todo, ex.map(lambda pv: self.hasher(*pv), todo.values())):
                    if sha:
                        self.d[k] = sha
                        self.dirty = True
        return {k: self.d.get(k) for k in reqs}

    def save(self):
        if not self.dirty:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = f"{self.path}.{os.getpid()}"
            json.dump(self.d, open(tmp, "w"))
            os.replace(tmp, self.path)
        except OSError:
            pass


def _launched(spec, spec_dir, mtime):
    c = str(((spec.get("private") or {}).get("created")) or "")
    try:
        return time.mktime(time.strptime(c[:16], "%Y-%m-%d %H:%M"))
    except ValueError:
        pass
    m = re.search(r"_(\d{10})$", spec_dir)
    if m:
        try:
            return time.mktime(time.strptime(time.strftime("%Y") + m.group(1), "%Y%m%d%H%M%S"))
        except ValueError:
            pass
    return mtime


def private_candidates(coord, vis, now=None):
    """[(die, item, launched, plan_req, cand)] of private kits of PROBE-THROUGH types newer than MAX_AGE_S"""
    now = time.time() if now is None else now
    out = []
    for sp in glob.glob(os.path.join(coord, "autopilot", "private_specs", "*", "*", "spec.json")):
        d = os.path.dirname(sp)
        try:
            mt = os.path.getmtime(sp)
            if now - mt > MAX_AGE_S:
                continue
            spec = json.load(open(sp))
        except (OSError, ValueError):
            continue
        die, item = str(spec.get("die") or ""), str(spec.get("item") or "")
        if not (die and item) or not is_probe_through(vis, die, item):
            continue
        try:
            res = json.load(open(os.path.join(d, "result.json")))
        except (OSError, ValueError):
            res = {}
        stage, verdict = str(res.get("stage") or "").lower(), str(res.get("verdict") or "").upper()
        state = "WAIT-VISUAL-PROBE-GRT" if stage in GRT_STAGES else "WAIT-VISUAL-PROBE-PLACE"
        if verdict == "FAIL":
            state += "-FAILED"
        cand = dict(attempt=os.path.basename(d), state=state, kit=str(res.get("kit") or ""), geom=str(res.get("geom_dir") or ""),
                    done=verdict == "SIGNED")
        plan = str(spec.get("plan") or "")
        out.append((die, item, _launched(spec, os.path.basename(d), mt), (f"{spec.get('gen_host')}|{plan}|{os.path.basename(d)}", plan, spec.get("gen_host")), cand))
    return out


def wave_candidates(items, vis, kit_location, die_cur):
    """wave records of the die's CURRENT event (die_cur {die: (event, plan, host)}) of PROBE-THROUGH types"""
    out = []
    for rec in (items or {}).values():
        die, item = str(rec.get("die") or ""), str(rec.get("item") or "")
        cur = die_cur.get(die)
        if not die or not cur or str(rec.get("event") or "") != str(cur[0] or "") or not is_probe_through(vis, die, item):
            continue
        done = rec.get("status") in DONE_STATUS or rec.get("q_status") in DONE_STATUS
        state = "WAIT-VISUAL-PROBE-GRT" if rec.get("status") == "ENQUEUED" else "WAIT-VISUAL-PROBE-PLACE"
        cand = dict(attempt=str(int(rec.get("attempt") or 0)), state=state, kit=kit_location(rec) or "", geom=str(rec.get("geom_dir") or ""), done=done)
        out.append((die, item, float(rec.get("started") or rec.get("updated") or 0), (f"die|{die}|{cur[1]}", cur[1], cur[2]), cand))
    return out


def pick(cands, shas):
    """per (die, item): plan of the newest launched kit = current; newest kit of that plan with a render, not finished"""
    by = {}
    for die, item, launched, req, cand in cands:
        by.setdefault((die, item), []).append((launched, shas.get(req[0]) or f"nosha:{req[1]}", cand))
    out = {}
    for k, lst in by.items():
        lst.sort(key=lambda x: x[0], reverse=True)
        cur = lst[0][1]
        for launched, sha, cand in lst:
            if sha == cur and cand["geom"] and not cand["done"]:
                out[k] = (cur, cand)
                break
    return out


def rows_for_queue(coord, items, kit_location, family=lambda die, item: item, listed=(), now=None, die_cur=None, cache=None):
    """probe rows for VISUAL-QUEUE.tsv; listed = {(die, item)} already in the queue (not repeated); die_cur {die: (event, plan, host)}"""
    vis = probe_types(coord)
    if not vis:
        return []
    cands = private_candidates(coord, vis, now=now) + wave_candidates(items, vis, kit_location, die_cur or {})
    cache = cache or ShaCache()
    shas = cache.get_many({req[0]: (req[1], req[2]) for _, _, _, req, _ in cands})
    cache.save()
    out = []
    for (die, item), (sha, c) in pick(cands, shas).items():
        if (die, item) in set(listed):
            continue
        out.append(_row(die, item, family(die, item), c["attempt"], f"{c['state']}@{sha[:12]}", c["kit"], c["geom"]))
    return sorted(out)


def die_current(cfg):
    """kit_wave cfg -> {die: (event, plan path, gen host)}"""
    return {k: (v.get("event"), v.get("plan"), v.get("gen_host")) for k, v in ((cfg or {}).get("dies") or {}).items() if isinstance(v, dict)}


if __name__ == "__main__":                                   # dry list on the hub: python3 -I probe_visual.py [coord]
    c = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/coord")
    try:
        cfg = json.load(open(os.path.join(c, "autopilot", "kit_wave.json")))
    except (OSError, ValueError):
        cfg = {}
    for r in rows_for_queue(c, {}, lambda rec: "", die_cur=die_current(cfg)):
        print("\t".join(r))
