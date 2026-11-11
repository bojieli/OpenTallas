#!/usr/bin/env python3
"""auto_resign.py -- autopilot stage: re-sign signed runs on the newest flow tag with no agent (FLOW-29, owner 2026-11-04).

Why: during the agent limit 11-04 01:30-03:10 the fleet ran on and 2 real runs signed off, but the count only moved
when an agent came back: sfustore3 signed at 01:48 and counted at 05:34.  A wave run ending WAIT-PARENT is never
archived, and a hand-form dir has no autopilot job at all, so both wait for a lane to re-sign them on a tag.

The autopilot still never alters a design (OWNER 10-25).  This runs tools/die_plan/resign.py on the SAME routed DB and
adds no check, threshold or waiver; resign.py run --auto is stricter than a hand re-sign (chain gates + all_shown).

Per tick (autopilot.py tick calls step() after the kit wave; default ON):
  1. Stop: AP_DIR/auto_resign.stop, or "auto_resign": false in kit_wave.json.  Running units finish and are collected.
  2. Candidates:
       wave      autopilot jobs WAIT-PARENT / SIGNED-UNVERSIONED whose kit is a kit_wave_stages.tsv row with plan_current yes
       registry  rows of coord lanes/AUTO-RESIGN.tsv (hand-form dirs): die name host dir build_commit lane note
                 dir may hold a glob (.../run/i*): the newest record that counts is used, so a lane can register an ECO
                 root before its result exists and walk away.  build_commit '-': read from the kit's own records.
     The counter's own unversioned list is written to auto_resign_suggest.tsv and never run: it holds stale experiments,
     and a type credit has no pin check, so a dir enters only through the wave's current-plan row or a lane's row.
  3. Never launched: a HOLD match (lanes/AUTO-RESIGN-HOLD.tsv: die pattern ruling; an unreadable or empty file stops
     every launch), a design the counter already credits, a COUNT-REVOKED netlist or view, a RETIRED record (a name line
     retires by date, and a re-sign would carry a new date past it, so the ORIGINAL record's date is what is judged).
  4. NO BUILD COMMIT IS INVENTED.  Proof = the job's branch@sha, the row's column, or the kit's PROVENANCE / AUTOPILOT /
     freeze record (resign.kit_build_commit), and the commit must exist on the hub.  Anything else stays for a lane and
     the record says NO-BUILD-COMMIT.  LEC_TOOL.json names the tool's commit, not the build, and is not read.
  5. One ot-run per item on the host holding the DB (--hosts, --no-spill, die priority + crit: a re-sign is the cheapest
     step to a count).  Tag tools are exported on that host at <root>/auto-resign/tools/<tag> with a sha manifest.
  6. Collection: PROVENANCE written -> RECORDED, .keep in kit and re-sign dir (resign.py), the next count credits it.
     No record -> FAILED with the reason; the failed dir stays as evidence (a later attempt gets a new dir).

NO BLIND RETRY.  A failure is keyed by (routed DB sha, sha of the tag's signoff.py + lec.py).  A newer tag re-runs a
failed DB only if those tools changed, since the same bytes on the same DB give the same verdict.  Infra (never
admitted, host lost, out of memory) relaunches once, at 1.5 x memory after OOM, as the autopilot does for kits.  A
retracted tag (gone from origin) makes a RECORDED item a candidate again on the newest tag.

NEAR-MISS ECO (item 2, default on; off: "auto_eco": false or "late_eco": false in kit_wave.json, KIT/late_eco.off).
A registered dir whose newest record does not count enters the existing late-ECO loop (tools/die_plan/eco_loop.py at the
tag) when it is in the owner-approved class: fails only setup_tt / hold_ff / drv / drc / fanout (eco_loop.eligible), each
failing TT / FF gate within the autopilot's NEAR-MISS bound on <= 100 endpoints, DRC < 50, and no hold row.  A wave run needs none of this: its chain already
runs the loop.  One loop per routed form, one iteration (OWNER 11-07 05:3x): no second loop on a loop's output or on a DB a
loop already started from; that stays for a lane, GEOMETRY + REDESIGN.  A PASS goes to the re-sign above on the loop's best
dir; anything else says so in the queue with the best numbers.  No gate moves: the loop's sign-off is the kit's own, and
resign.py --auto runs sign-off + routed LEC again at the tag.

    auto_resign.py status                 state table (hub)
"""
import copy
import fnmatch
import hashlib
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

STATE = "auto_resign_state.json"
LOG_TSV = "auto_resign.tsv"
SUGGEST = "auto_resign_suggest.tsv"
REGISTRY = "lanes/AUTO-RESIGN.tsv"
HOLD = "lanes/AUTO-RESIGN-HOLD.tsv"
REVOKED = "lanes/COUNT-REVOKED.tsv"
RETIRED = "RETIRED_SIGNOFFS.tsv"
QUEUE = "lanes/COORD-REVIEW-QUEUE.md"
LANE = "AUTO-RESIGN"
MEM_GB = 32                   # SS25-27 re-signs ran at --mem 32, LEC container 32g
THREADS = 8
MAX_INFLIGHT = 12
MAX_LAUNCH_PER_TICK = 6
MAX_INFRA = 1
CACHE_MAX_AGE_S = 3 * 3600    # older than this the 'already credited' answer is stale: launch nothing
TAG_TOOL_FILES = ("tools/die_plan/signoff.py", "tools/die_plan/lec.py")
CLOCK_FAMILY_RELS = ("tools/die_plan/clock_family.tcl", "physical/common_flow/clock_family.tcl")
HERE = Path(__file__).resolve().parent
DRIVER = HERE / "die_plan" / "resign.py" if (HERE / "die_plan" / "resign.py").is_file() else HERE.parent / "die_plan" / "resign.py"
WAVE_STATUS = ("WAIT-PARENT", "SIGNED-UNVERSIONED")
ECO_FAILS = {"setup_tt", "hold_ff", "drv", "drc", "fanout"}   # = eco_loop.ECO_FAILS
NEAR_ENDPOINTS = 100                                  # COORD 11-07 05:37, = eco_loop.NEAR_ENDPOINTS
ECO_MEM_GB = 64
ECO_DISK_GB = 40
MAX_ECO_INFLIGHT = 4
RE_KEYS = re.compile(r"^(dp|kr)_(.+)$")


# ------------------------------------------------------------------------------------------------ text inputs (pure)
def parse_rows(text, n):
    """TAB rows of at least n columns; '#' and blank lines are comments"""
    out = []
    for line in (text or "").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) >= n:
            out.append([x.strip() for x in f])
    return out


def parse_holds(text):
    """[(die or '*', pattern, ruling)]; None when the file holds no row: the caller launches nothing (fail closed)"""
    rows = [(r[0], r[1], r[2] if len(r) > 2 else "") for r in parse_rows(text, 2)]
    return rows or None


def parse_registry(text):
    out = []
    for r in parse_rows(text, 4):
        r = r + [""] * (7 - len(r))
        out.append(dict(die=r[0], name=r[1], host=r[2], path=r[3], build_commit="" if r[4] in ("", "-") else r[4],
                        lane=r[5], note=r[6], source="registry"))
    return out


def rec_keys(name, top):
    """= release_tree_plan.rec_keys: the names a record credits"""
    ks = set()
    for v in (top, name):
        if not v:
            continue
        ks.add(v)
        m = RE_KEYS.match(v)
        if m:
            ks.add(m.group(2))
            ks.add(re.sub(r"_(lfp|r\d+|c\d+)$", "", m.group(2)))
    return ks


def hold_hit(holds, die, names):
    for d, pat, why in holds:
        if d not in ("*", die):
            continue
        for n in names:
            if n and fnmatch.fnmatchcase(n, pat):
                return "%s (%s)" % (pat, why) if why else pat
    return ""


def revoked_hit(text, host, kit, netlist_sha):
    """COUNT-REVOKED row die design <sha256:netlist | host:view dir> reason date.  The third column alone names the view;
    the die column uses short names (head, kv) and is not needed for an exact netlist or dir match."""
    for r in parse_rows(text, 3):
        ref = r[2]
        if ref.startswith("sha256:"):
            if netlist_sha and ref[7:] == netlist_sha:
                return ref
        elif ":" in ref:
            h, d = ref.split(":", 1)
            if h == host and kit and (kit == d or kit.startswith(d.rstrip("/") + "/")):
                return ref
    return ""


def date_ts(s):
    """= release_tree_plan._date_ts: local time, date with optional HH:MM"""
    m = re.match(r"^\s*(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}:\d{2}))?", s or "")
    return time.mktime(time.strptime(m.group(1) + " " + (m.group(2) or "00:00"), "%Y-%m-%d %H:%M")) if m else None


def retired_hit(text, die, names, host, path, generated, name=None, top=None, retired_records=()):
    """RETIRED_SIGNOFFS: path line = that record; name line 'name:<die>:<key>' = every record generated before its date.
    The re-sign's own date would pass a name line, so the ORIGINAL record's date is judged here.  A copy of a retired
    record (same name, top, generated; the counter's rule (a)) is retired too."""
    for r in parse_rows(text, 2):
        ref = r[0]
        if ref.startswith("name:"):
            p = ref.split(":", 2)
            if len(p) == 3 and p[1] == die and p[2] in names:
                lim, gen = date_ts(r[1]), date_ts(generated)
                if gen is None or (lim is not None and gen < lim):
                    return ref
        elif ref == "%s:%s" % (host, path):
            return ref
    for x in retired_records or ():
        if isinstance(x, dict) and (x.get("name"), x.get("top"), x.get("generated")) == (name, top, generated) and generated:
            return "copy of " + str(x.get("path"))
    return ""


def cache_plan(cache, die):
    return [e for e in (cache.get("plans") or {}).values() if e.get("die") == die]


def credited(cache, die, names):
    """the counter already credits this design: a signed type of that name, or every design of that core module"""
    for e in cache_plan(cache, die):
        signed = set(e.get("signed_designs") or {})
        for n in names:
            if n in (e.get("signed_types") or {}):
                return "type " + n
            ds = [k for k, g in (e.get("designs") or {}).items() if g.get("module") == n]
            if ds and all(k in signed for k in ds):
                return "design " + n
            if not ds and n in (e.get("signed_cores") or {}):
                return "core " + n
    return ""


def suggestions(cache, handled):
    """counter-listed unversioned records with no autopilot route: printed for a lane, never run"""
    rows = []
    for e in (cache.get("plans") or {}).values():
        for kind in ("unversioned_types", "unversioned_cores"):
            for name, refs in sorted((e.get(kind) or {}).items()):
                if (e.get("die"), name) in handled:
                    continue
                real = [x for x in refs if "/flow-canary/" not in x and "/wt/" not in x]
                if real:
                    rows.append((e.get("die"), name, real[-1].split(" ")[0], len(real)))
    return rows


def wave_kits(tsv_text):
    """{kit path: plan_current} from kit_wave_stages.tsv"""
    lines = (tsv_text or "").splitlines()
    if not lines:
        return {}
    head = lines[0].split("\t")
    try:
        ik, ic = head.index("kit"), head.index("plan_current")
    except ValueError:
        return {}
    out = {}
    for line in lines[1:]:
        f = line.split("\t")
        if len(f) > max(ik, ic) and f[ik]:
            out[f[ik].split(":", 1)[-1]] = f[ic]
    return out


def wave_candidates(jobs, kits, core_module=lambda x: x):
    out = []
    for j in jobs.values():
        if j.get("status") not in WAVE_STATUS:
            continue
        so = j.get("signoff") or {}
        kit = str(j.get("path") or j.get("kit") or "").split(":", 1)[-1]
        if not so.get("path") or kits.get(kit) != "yes":
            continue
        out.append(dict(die=j.get("die"), name=j.get("type"), module=core_module(j.get("type")),
                        host=j.get("probe") or j.get("host"), path=os.path.dirname(os.path.dirname(so["path"])),
                        record=so["path"], src=j.get("src"), lane=j.get("lane") or "", note="wave job %s" % j.get("id"),
                        source="wave", build_commit=""))
    return out


# ARHOST_1111 (KW-FIX-44, COORD 11-11 19:22 hbm/hnx_rp3h_tl): ot-run placed nothing (no host / disk / floor refusal).  Such
# a refusal is INFRA that never ends the row nor spends the infra budget: the row goes PENDING and the next launch is
# placed like any ot-run job (anyhost: no --hosts pin, no --no-spill, --stage of exactly the job's inputs, so a host
# that admits it gets a staged copy and the outputs come back to the DB host).  A failure key recorded for such a
# refusal before this rule is not a verdict and is ignored.
NO_HOST = re.compile(r"no host qualifies|DISK GUARD|ROOT FS \d+% full|disk \d+ GB < \d+|scratch\d? floor|"
                     r"@unit: OSError: \[Errno 28\]", re.I)


def cand_id(c):
    """from the row alone: an item keeps its state when it moves on to a late-ECO result"""
    return hashlib.sha1(("%s|%s|%s|%s" % (c["die"], c["name"], c["host"], c.get("path"))).encode()).hexdigest()[:12]


def tool_key(shas):
    return hashlib.sha256("".join(shas[f] for f in TAG_TOOL_FILES).encode()).hexdigest()[:16]


def judge(c, p, ctx, it):
    """(action, why) for a probed candidate.  action LAUNCH | WAIT | SKIP | LANE (needs a lane, said in the record)"""
    if p.get("error"):
        return "WAIT", "probe: " + str(p["error"])[:200]
    if not p.get("record"):
        return "WAIT", "no record that counts yet"
    rec = rec_keys(p.get("name"), p.get("top"))
    if not rec & {c["name"], c.get("module")}:          # the counter would credit a different design, or nothing
        return "LANE", "record names %s, row names %s" % (sorted(rec), c["name"])
    names = rec | {c["name"], c.get("module")}
    names.discard(None)
    why = hold_hit(ctx["holds"], c["die"], names)
    if why:
        return "SKIP", "HELD " + why
    why = credited(ctx["cache"], c["die"], names)
    if why:
        return "SKIP", "already credited: " + why
    why = revoked_hit(ctx["revoked"], c["host"], p.get("kit"), p.get("netlist_sha"))
    if why:
        return "SKIP", "COUNT-REVOKED " + why
    why = retired_hit(ctx["retired"], c["die"], names, c["host"], p["record"], p.get("generated"), p.get("name"), p.get("top"),
                      ctx["cache"].get("retired_records"))
    if why:
        return "SKIP", "RETIRED " + why
    if not p.get("db_ok"):
        return "LANE", "routed DB, 6_final.v or kit not readable where the record says: %s" % p.get("odb")
    tag = ctx["tag"](c["die"])
    if not tag:
        return "WAIT", "no flow tag covers %s" % c["die"]
    key = "%s|%s" % (p.get("odb_sha"), ctx["tool_key"](tag))
    prev = (it.get("failed") or {}).get(key)
    if prev and NO_HOST.search(prev):                  # ARHOST_1111: a placement refusal is not a verdict
        prev = None
    if prev:
        return "LANE", "FAILED %s; same DB and same signoff.py + lec.py on %s, not retried" % (prev, tag)
    bc = ctx["build_commit"](c, p)
    if not bc:
        return "LANE", "NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane"
    return "LAUNCH", dict(tag=tag, key=key, build_commit=bc)


def judge_eco(c, e, it, holds, near_wns, near_drc):
    """(action, why) for a registered dir with no counting record.  LAUNCH | WAIT | SKIP | LANE"""
    if e.get("error"):
        return "WAIT", "eco probe: " + str(e["error"])[:200]
    if not e.get("record"):
        return "WAIT", "no record that counts yet"
    names = rec_keys(e.get("name"), e.get("top")) | {c["name"]}
    why = hold_hit(holds, c["die"], names)
    if why:
        return "SKIP", "HELD " + why
    fails = set(e.get("fails") or [])
    nums = "TT %s FF %s DRC %s, fails %s" % (e.get("tt"), e.get("ff"), e.get("drc"), ",".join(sorted(fails)))
    if not fails:
        return "WAIT", "no FAIL gate (%s), not an ECO case" % e.get("verdict")
    if fails - ECO_FAILS:
        return "SKIP", "not an ECO class: " + nums
    # port-only hold is not a FAIL; a mixed record scores hold on the core-owned split, the same set eco_loop.near_miss judges (COORD R4)
    timing = [(e.get(k), e.get(k + "_n")) for k, g in (("tt", "setup_tt"), ("ff", "hold_ff")) if g in fails and k != "ff"]
    if "hold_ff" in fails:
        timing.append((e["ff_core"], e["ff_core_n"]) if e.get("ff_core_n") is not None else (e.get("ff"), e.get("ff_n")))
    if any((w is not None and w < near_wns) or (n or 0) > NEAR_ENDPOINTS for w, n in timing) or (e.get("drc") or 0) >= near_drc:
        return "SKIP", "outside the near-miss bound: " + nums
    if e.get("late_eco_off"):
        return "SKIP", "KIT/late_eco.off"
    if not e.get("odb_sha"):
        return "LANE", "routed DB not readable where the record says: %s" % e.get("odb")
    done = it.get("eco_done") or {}
    if e["odb_sha"] in done:
        return "LANE", "late-ECO already ran on this DB: " + nums
    if e.get("loop_bad"):
        return "LANE", "a loop ran here but its record or best record is not readable: %s, %s" % (e["loop_bad"], nums)
    if done or e.get("loop"):
        return "LANE", "one late-stage iteration per routed form, no second loop, GEOMETRY + REDESIGN: " + nums
    return "LAUNCH", nums


def eco_argv(AP, c, e, d, out, mem):
    host = "localhost" if AP.ssh_host(c["host"]) == "localhost" else c["host"]
    return [AP.OT_RUN, "--mem", str(mem), "--threads", str(THREADS), "--hosts", host, "--no-spill", "--disk", str(ECO_DISK_GB),
            "--dir", d, "--priority", "die", "--crit", "--", "python3", "-I", d + "/tools/die_plan/eco_loop.py", "run",
            "--kit", e["kit"], "--signoff", e["record"], "--out", out, "--mem", str(mem), "--cpus", str(THREADS)]


# ------------------------------------------------------------------------------------------------ host probes
PROBE_RECORD = r'''
import glob, hashlib, json, os, shutil, sys
a = json.loads(sys.argv[1]); out = {}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def counts(d):
    v = d.get("verdict")
    if v == "SIGNED": return True
    return (v == "LOCAL_PASS_NEEDS_PARENT" and d.get("local_verdict") == "SIGNED" and
            all(str(r).startswith("io_hold_parent") for r in (d.get("reasons") or [])))
SHA = __import__("re").compile(r"^[0-9a-f]{40}$")
def build_commit(kit):  # = resign.kit_build_commit
    for n in ("PROVENANCE.json", "AUTOPILOT.json", "freeze.json", "kit_provenance.json"):
        try: x = json.load(open(os.path.join(kit, n)))
        except Exception: continue
        if not isinstance(x, dict) or x.get("kind") == "resign": continue
        pv = x.get("provenance")
        for v in (x.get("build_commit"), x.get("src_commit"), pv.get("commit") if isinstance(pv, dict) else None, x.get("source_commit")):
            if isinstance(v, str) and SHA.match(v): return v
    return None
try:
    recs = []
    if a.get("record"):
        recs = [a["record"]]
    else:
        for d in glob.glob(a["path"]):
            recs += [os.path.join(d, "signoff", "signoff.json"), os.path.join(d, "signoff.json")]
    best, bm = None, -1
    for p in recs:
        try:
            m = os.path.getmtime(p); d = json.load(open(p))
        except Exception:
            continue
        if counts(d) and m > bm: best, bm = (p, d), m
    if best:
        p, d = best
        inp = d.get("inputs") or {}
        fg = d.get("face_guard") or {}
        out.update(record=p, verdict=d.get("verdict"), local_verdict=d.get("local_verdict"), name=d.get("name"),
                   top=fg.get("top") if isinstance(fg, dict) else None, generated=d.get("generated"), odb=inp.get("odb"),
                   kit=inp.get("kit"), orfs=inp.get("orfs"), final_v=inp.get("final_v"))
        ok = all(inp.get(k) and os.path.exists(inp[k]) for k in ("odb", "kit", "orfs", "final_v"))
        ok = ok and os.path.realpath(inp["final_v"]).startswith(os.path.realpath(inp["kit"]) + os.sep)
        out["db_ok"] = bool(ok)
        if ok:
            prev = a.get("known") or {}
            st = os.stat(inp["odb"])
            stamp = "%d:%d" % (st.st_size, int(st.st_mtime))
            if prev.get("stamp") == stamp and prev.get("odb_sha"):
                out.update(stamp=stamp, odb_sha=prev["odb_sha"], netlist_sha=prev.get("netlist_sha"))
            else:
                out.update(stamp=stamp, odb_sha=sha(inp["odb"]), netlist_sha=sha(inp["final_v"]))
            out["build_commit"] = build_commit(inp["kit"])
    roots = []
    for r in a.get("roots") or []:
        c = os.path.join(r, "claude")
        if os.path.isdir(c) and os.access(c, os.W_OK) and shutil.disk_usage(c).free > (5 << 30):
            roots.append(r)
    out["root"] = roots[0] if roots else None
except Exception as e:
    out["error"] = "%s: %s" % (type(e).__name__, e)
done()
'''

PROBE_RESULT = r'''
import json, os, sys
a = json.loads(sys.argv[1]); out = {}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
def jl(p):
    try: return json.load(open(p))
    except Exception: return None
o = a["out"]
pv = jl(os.path.join(o, "PROVENANCE.json"))
if isinstance(pv, dict):
    out["prov"] = {k: pv.get(k) for k in ("kind", "flow_tag", "src_commit", "build_commit", "lec_verdict", "routed_db", "verdict_basis")}
so = jl(os.path.join(o, "signoff", "signoff.json"))
if isinstance(so, dict):
    c = so.get("checks") or {}
    out["signoff"] = dict(verdict=so.get("verdict"), local=so.get("local_verdict"), reasons=(so.get("reasons") or [])[:4],
                          tt=(c.get("setup_tt") or {}).get("wns_ps"), ff=(c.get("hold_ff") or {}).get("wns_ps"),
                          drc=(c.get("drc") or {}).get("count"))
le = jl(os.path.join(o, "lec", "lec.json"))
if isinstance(le, dict):
    out["lec"] = dict(verdict=le.get("verdict"), reason=str(le.get("reason") or "")[:200],
                      all_shown=(le.get("superset_vec") or {}).get("all_shown"))
for n in ("signoff.log", "lec.log"):
    try:
        with open(os.path.join(o, n), errors="replace") as f:
            t = f.read()[-20000:]
        if "out of memory" in t.lower() or "Killed" in t:
            out["oom"] = n
    except OSError:
        pass
done()
'''

PROBE_ECO = r'''
import glob, hashlib, json, os, shutil, sys
a = json.loads(sys.argv[1]); out = {}
def done(): print("AP_JSON " + json.dumps(out)); sys.exit(0)
try:
    recs = [a["record"]] if a.get("record") else []
    for d in () if recs else glob.glob(a["path"]):
        recs.append(os.path.join(d, "signoff", "signoff.json"))
    best, bm = None, -1
    for p in recs:
        try:
            m = os.path.getmtime(p); d = json.load(open(p))
        except Exception:
            continue
        if m > bm: best, bm = (p, d), m
    off = False
    if best:
        p, d = best
        kit0, odb0 = (d.get("inputs") or {}).get("kit") or "", (d.get("inputs") or {}).get("odb") or ""
        off = os.path.exists(os.path.join(kit0, "late_eco.off"))
        lj = os.path.join(os.path.dirname(kit0), "eco_loop.json")
        if not os.path.exists(lj):
            prior = []
            for j in glob.glob(os.path.join(kit0, "eco_*", "eco_loop.json")):
                try:
                    if json.load(open(j)).get("base_routed_db") == odb0: prior.append(j)
                except Exception:
                    out["loop_bad"] = j
            lj = max(prior, key=os.path.getmtime) if prior else None
        if lj:
            try:
                L = json.load(open(lj)); b = L.get("best") or {}; k = L.get("kit") or ""
                out["loop"] = dict(file=lj, verdict=L.get("verdict"), base=L.get("base_metrics"), best=b.get("metrics"))
                off = off or os.path.exists(os.path.join(k, "late_eco.off"))
                if b.get("signoff") != p:
                    p, d = b["signoff"], json.load(open(b["signoff"]))
            except Exception as ex:
                out["loop_bad"] = "%s (%s)" % (lj, ex)
        c, inp, fg = d.get("checks") or {}, d.get("inputs") or {}, d.get("face_guard") or {}
        out.update(record=p, verdict=d.get("verdict"), name=d.get("name"), top=fg.get("top") if isinstance(fg, dict) else None,
                   fails=sorted(k for k, v in c.items() if isinstance(v, dict) and v.get("verdict") == "FAIL"),
                   tt=(c.get("setup_tt") or {}).get("wns_ps"), ff=(c.get("hold_ff") or {}).get("wns_ps"),
                   tt_n=(c.get("setup_tt") or {}).get("violators"), ff_n=(c.get("hold_ff") or {}).get("violators"),
                   drc=(c.get("drc") or {}).get("count"), odb=inp.get("odb"), kit=inp.get("kit"))
        # KW-FIX-36 11-08 (COORD R4): the FF census split eco_loop.core_hold reads, so a mixed record is judged on the same endpoints
        try:
            s = json.load(open(os.path.join(os.path.dirname(p), "ff", "corner.json"))).get("std_min_start") or {}
            if s.get("err") == 0 and s.get("trunc") == 0:
                if s.get("core_n") is not None and s.get("core_wns") is not None:
                    out.update(ff_core=s["core_wns"], ff_core_n=s["core_n"])
                elif s.get("nonport_n") is not None and s.get("nonport_wns") is not None:
                    n = s["nonport_n"] if not s.get("oport") else min(s["nonport_n"], (s.get("other") or 0) + (s.get("reg") or 0))
                    out.update(ff_core=s["nonport_wns"], ff_core_n=n)
        except Exception:
            pass
        kit, odb = inp.get("kit") or "", inp.get("odb") or ""
        out["late_eco_off"] = off or os.path.exists(os.path.join(kit, "late_eco.off"))
        if os.path.isfile(odb) and os.path.isdir(kit):
            h = hashlib.sha256()
            with open(odb, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
            out["odb_sha"] = h.hexdigest()
    need = a.get("free_gb", 40) << 30
    roots = [r for r in a.get("roots") or [] if os.path.isdir(os.path.join(r, "claude")) and shutil.disk_usage(r).free > need]
    out["root"] = roots[0] if roots else None
except Exception as e:
    out["error"] = "%s: %s" % (type(e).__name__, e)
done()
'''

PROBE_ECO_RESULT = r'''
import json, os, sys
a = json.loads(sys.argv[1]); out = {}
try:
    r = json.load(open(os.path.join(a["out"], "eco_loop.json")))
    b = r.get("best") or {}
    out.update(verdict=r.get("verdict"), reason=str(r.get("reason") or "")[:200], best_dir=b.get("dir"), best_signoff=b.get("signoff"),
               metrics={k: (b.get("metrics") or {}).get(k) for k in ("tt", "ff", "drv", "drc")})
except FileNotFoundError:
    out["verdict"] = None
except Exception as e:
    out["error"] = "%s: %s" % (type(e).__name__, e)
print("AP_JSON " + json.dumps(out))
'''

ROOTS = ("/srv/opentallas-scratch3", "/srv/opentallas-scratch2", "/srv/opentallas-scratch", "/home/ubuntu/scratch-root")


# ------------------------------------------------------------------------------------------------ hub side
def load_state(ap_dir):
    try:
        return json.loads((Path(ap_dir) / STATE).read_text())
    except (OSError, ValueError):
        return {"items": {}}


def save_state(ap_dir, st):
    p = Path(ap_dir) / STATE
    t = p.with_suffix(".tmp")
    t.write_text(json.dumps(st, indent=1, sort_keys=True))
    os.replace(t, p)


def stop_reason(ap_dir):
    if (Path(ap_dir) / "auto_resign.stop").exists():
        return "stop file auto_resign.stop"
    try:
        if json.loads((Path(ap_dir) / "kit_wave.json").read_text()).get("auto_resign", True) is False:
            return '"auto_resign": false in kit_wave.json'
    except (OSError, ValueError):
        pass
    return ""


def hub_git(AP, *args, timeout=120):
    return AP.sh(["git", "-C", str(AP.REPO)] + list(args), timeout=timeout)


def known_commit(AP, sha, branch=None):
    """full sha when the hub has this commit (fetched from the branch when named), else ''"""
    if not sha or not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        return ""
    q = lambda: hub_git(AP, "rev-parse", "-q", "--verify", sha + "^{commit}")
    rc, out, _ = q()
    if (rc or not out.strip()) and branch:
        hub_git(AP, "fetch", "-q", "origin", branch, timeout=300)
        rc, out, _ = q()
    return out.strip().split()[0] if rc == 0 and out.strip() else ""


def tag_shas(AP, tag):
    """manifest files: sha256 of every tag file resign.py checks; {} when the tag lacks a tool"""
    out = {}
    if hub_git(AP, "rev-parse", "-q", "--verify", tag + "^{commit}")[0]:   # flow_tags reads origin; the hub may not hold it yet
        hub_git(AP, "fetch", "-q", "origin", "refs/tags/%s:refs/tags/%s" % (tag, tag), timeout=300)
    for rel in TAG_TOOL_FILES + CLOCK_FAMILY_RELS:
        rc, txt, _ = bin_show(AP, tag, rel)
        if rc == 0:
            out[rel] = hashlib.sha256(txt).hexdigest()
    return out if all(f in out for f in TAG_TOOL_FILES) else {}


def bin_show(AP, tag, rel):
    import subprocess
    p = subprocess.run(["git", "-C", str(AP.REPO), "show", "%s:%s" % (tag, rel)], capture_output=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


def stage_tools(AP, host, root, tag, shas):
    """export the tag's tools on the host + a sha manifest + the recording driver.  Tools are tag bytes (resign.py checks
    them); the driver is main's, since a tag older than this stage has none with --auto."""
    d = "%s/claude/auto-resign/tools/%s" % (root, tag)
    h = AP.ssh_host(host)
    # a READY export is never rewritten: a running sign-off may be reading it
    if AP.sh(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", h, "test -f %s/READY" % shlex.quote(d)], timeout=60)[0] == 0:
        return d, ""
    rels = ["tools/die_plan"] + [r for r in CLOCK_FAMILY_RELS if r in shas and not r.startswith("tools/die_plan")]
    cmd = ("git -C %s archive %s -- %s | ssh -o BatchMode=yes -o ControlPath=none %s %s"
           % (shlex.quote(str(AP.REPO)), shlex.quote(tag), " ".join(shlex.quote(r) for r in rels), shlex.quote(h),
              shlex.quote("mkdir -p %s && tar -C %s -xf - && touch %s/.extracted" % (d, d, d))))
    rc, _, err = AP.sh(["bash", "-c", "set -o pipefail; " + cmd], timeout=600)
    if rc:
        return None, "tools export to %s: %s" % (host, err.strip()[-200:])
    commit = hub_git(AP, "rev-parse", tag + "^{commit}")[1].strip()
    man = dict(schema="opentallas.resign_tag_manifest.v1", tag=tag, commit=commit, files=shas)
    payload = json.dumps(man, indent=1) + "\n"
    drv = DRIVER.read_text()
    for name, text in (("tag_manifest.json", payload), ("resign_driver.py", drv)):
        rc, _, err = AP.sh(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", h, "cat > %s/%s" % (shlex.quote(d), name)],
                           timeout=120, input=text)
        if rc:
            return None, "%s to %s: %s" % (name, host, err.strip()[-200:])
    rc, _, err = AP.sh(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", h, "touch %s/READY" % shlex.quote(d)], timeout=60)
    return (d, "") if rc == 0 else (None, "READY on %s: %s" % (host, err.strip()[-200:]))


# KW-FIX-32 11-07 (COORD 21:4x (3), DIE-KV-91: no dd-kv tools under auto-resign/tools when a lane re-signed by hand):
# every die's newest flow tag is exported on every fleet host when it lands, not only when the first wave re-sign of
# that die launches there.  Same export (stage_tools: tag bytes + sha manifest + driver, READY marker), same root rule
# as a launch (first scratch root with a claude dir and PRESTAGE_FREE_GB free).  ~19 MB per tag and host.
PRESTAGE_DIES = ("qwen_compute", "s81", "s81_head", "qwen_kvsys", "hbm")
PRESTAGE_FREE_GB = 5
PRESTAGE_MAX_PER_TICK = int(os.environ.get("OT_AR_PRESTAGE_MAX", "8"))     # exports per pass; the rest go next pass
HOST_LINE_RE = re.compile(r"(?:^|[|]|ot-run status:)\s*([A-Za-z0-9_.-]+) (?:admits|REFUSED)\b", re.M)

PROBE_ROOT = r'''
import json, os, shutil, sys
a = json.loads(sys.argv[1]); need = a.get("free_gb", 5) << 30
roots = [r for r in a.get("roots") or [] if os.path.isdir(os.path.join(r, "claude")) and shutil.disk_usage(r).free > need]
print("AP_JSON " + json.dumps(dict(root=roots[0] if roots else None)))
'''


def fleet_hosts(AP):
    """host names ot-run --status lists (admitting or refused: a refused host can still hold a routed DB)"""
    rc, out, _ = AP.sh([AP.OT_RUN, "--status"], timeout=120)
    return sorted(set(HOST_LINE_RE.findall(out))) if rc == 0 else []


def prestage(AP, st, ctx, hosts=None):
    """export each die's newest tag on every host once; -> [(host, tag, dir or error)].  Off: OT_AR_PRESTAGE=0."""
    if AP.DRY or os.environ.get("OT_AR_PRESTAGE", "1") == "0":
        return []
    done, out, budget = st.setdefault("prestaged", {}), [], PRESTAGE_MAX_PER_TICK
    hosts = fleet_hosts(AP) if hosts is None else hosts
    for die in PRESTAGE_DIES:
        tag = ctx["tag"](die)
        if not tag:
            continue
        ctx["tool_key"](tag)
        shas = ctx["shas"].get(tag) or {}
        if not shas:
            continue
        for host in hosts:
            key = "%s|%s" % (host, tag)
            if key in done or budget <= 0:
                continue
            r = AP.rpy(host, PROBE_ROOT, dict(roots=ROOTS, free_gb=PRESTAGE_FREE_GB), timeout=120)
            if not r.get("root"):
                out.append((host, tag, "no scratch root: %s" % (r.get("error") or "none with %d GB free" % PRESTAGE_FREE_GB)))
                continue
            budget -= 1
            d, err = stage_tools(AP, host, r["root"], tag, shas)
            if d:
                done[key] = d
            out.append((host, tag, d or err))
    for host, tag, what in out:
        AP.log("AUTO-RESIGN PRESTAGE %s %s: %s" % (host, tag, what))
    return out


def out_dir(root, c, tag, odb_sha, attempt):
    s = "%s/claude/auto-resign/%s/%s__%s__%s" % (root, c["die"], c["name"], tag, odb_sha[:8])
    return s if attempt <= 1 else "%s_a%d" % (s, attempt)


def job_argv(AP, c, p, d, out, tag, bc, mem, anyhost=False):
    # --dir is the tools dir, not the kit: ot-run ignores a --dir under a lane root marked .ot-run-spill-copy (ECO kits on a
    # spill copy, e.g. die-hbm-63 on epyc2), so a pinned job on the kit would wait for ever on a DB that is really there.
    host = "localhost" if AP.ssh_host(c["host"]) == "localhost" else c["host"]   # ot-run names the hub localhost
    note = "%s; %s" % (c.get("lane") or c.get("source"), c.get("note") or "")
    if anyhost:                                        # ARHOST_1111: placed like any ot-run job, inputs staged
        stage = [d, p["kit"], p["orfs"], out] + ([p["odb"]] if not str(p["odb"]).startswith(str(p["orfs"]).rstrip("/") + "/") else [])
        place = ["--stage", ",".join(stage)]
    else:
        place = ["--hosts", host, "--no-spill"]
    return [AP.OT_RUN, "--mem", str(mem), "--threads", str(THREADS)] + place + ["--disk", "2",
            "--dir", d, "--priority", "die", "--crit", "--", "python3", "-I", d + "/resign_driver.py", "run",
            "--auto", "--kit", p["kit"], "--run-dir", p["orfs"], "--routed-db", p["odb"], "--tag", tag,
            "--repo", d + "/tag_manifest.json", "--tools", d + "/tools/die_plan", "--out", out, "--build-commit", bc,
            "--lane", LANE, "--note", note[:300], "--lec-mem", "%dg" % mem]


def classify(client, res, tag):
    """(status, why): RECORDED | INFRA | INFRA_OOM | FAILED"""
    pv = res.get("prov") or {}
    if pv.get("kind") == "resign" and pv.get("flow_tag") == tag and pv.get("lec_verdict") == "EQUIVALENT":
        return "RECORDED", ""
    if client.get("cancelled"):
        return "FAILED", "cancelled: " + client["cancelled"][:160]
    if client.get("not_run"):
        return "INFRA", client.get("msg", "ot-run NOT RUN")
    if client.get("not_completed"):
        return "INFRA", client.get("msg", "ot-run NOT COMPLETED")
    if res.get("oom") or client.get("exit") in (137, 143):
        return "INFRA_OOM", "out of memory in %s" % (res.get("oom") or "client exit %s" % client.get("exit"))
    so, le = res.get("signoff") or {}, res.get("lec") or {}
    if not so:
        return "FAILED", "no sign-off record, client exit %s" % client.get("exit")
    if so.get("verdict") != "SIGNED" and not (so.get("verdict") == "LOCAL_PASS_NEEDS_PARENT" and so.get("local") == "SIGNED"):
        return "FAILED", "re-sign %s TT %s FF %s: %s" % (so.get("verdict"), so.get("tt"), so.get("ff"), "; ".join(so.get("reasons") or [])[:160])
    if le.get("verdict") != "EQUIVALENT":
        return "FAILED", "LEC %s %s" % (le.get("verdict"), le.get("reason") or "")
    return "FAILED", "no PROVENANCE: resign.py refused (all_shown %s or gates); read the client log" % le.get("all_shown")


ACTIVE = ("RUNNING", "ECO")


def guarded(AP, it, notices, fn, *args):
    """KW-FIX-7's launch_safe, per row (ROOT-MERGE-30 07:05): one row's error logs and the pass goes on.  The row stays as it
    was and is taken again next pass, unless it had already started a unit: that stays on record, or the unit would be lost
    and the same attempt dir used again."""
    keep, n = copy.deepcopy(it), len(notices)
    try:
        fn(*args)
    except Exception as e:
        started = it.get("status") in ACTIVE and keep.get("status") not in ACTIVE
        if not started:
            it.clear()
            it.update(keep)
            del notices[n:]
        try:
            AP.log("AUTO-RESIGN ROW-SKIP %s/%s: %s: %s (pass continues, %s)" % (it.get("die"), it.get("name"), type(e).__name__, str(e)[:300],
                                                                              "unit started, kept on record" if started else "row unchanged, next pass"))
        except Exception:
            pass


def poll(AP, st, notices, ap_dir):
    for cid, it in st["items"].items():
        if it.get("status") == "RUNNING":
            guarded(AP, it, notices, poll_row, AP, cid, it, notices)


def poll_row(AP, cid, it, notices):
    if AP.unit_active(it["unit"]):
        return
    try:
        client = AP.parse_client_log(Path(it["log"]).read_text(errors="replace"))
    except OSError:
        client = {}
    res = AP.rpy(it["host"], PROBE_RESULT, {"out": it["out"]}, timeout=120)
    if res.get("error"):
        AP.log("AUTO-RESIGN %s: result probe failed, next tick: %s" % (it["name"], res["error"][:200]))
        return
    status, why = classify(client, res, it["tag"])
    it["finished"] = time.time()
    if status == "RECORDED":
        it.update(status="RECORDED", why="")
        so, le = res.get("signoff") or {}, res.get("lec") or {}
        msg = "%s/%s RECORDED %s TT %s FF %s LEC %s, %s:%s" % (it["die"], it["name"], it["tag"], so.get("tt"), so.get("ff"),
                                                             le.get("verdict"), it["host"], it["out"])
    elif status == "INFRA" and NO_HOST.search(why):   # ARHOST_1111: placement refusal, retried next tick on any host
        it.update(status="PENDING", anyhost=True,
                  why="NO-HOST %s; next tick placed like any ot-run job (staged inputs), infra budget unchanged" % why[:200])
        AP.log("AUTO-RESIGN %s/%s: %s" % (it["die"], it["name"], it["why"]))
        return
    elif status in ("INFRA", "INFRA_OOM") and it.get("infra", 0) < MAX_INFRA:
        it["infra"] = it.get("infra", 0) + 1
        if status == "INFRA_OOM":
            it["mem"] = min(512, int(it.get("mem", MEM_GB) * 1.5 + 0.999))
        it.update(status="PENDING", why="%s; relaunch %d of %d, --mem %s" % (why[:200], it["infra"], MAX_INFRA, it.get("mem", MEM_GB)))
        AP.log("AUTO-RESIGN %s/%s: %s" % (it["die"], it["name"], it["why"]))
        return
    else:
        it.update(status="FAILED", why=why[:400])
        it.setdefault("failed", {})[it["key"]] = why[:200]
        msg = "%s/%s FAILED on %s: %s. DB and tools unchanged means no retry; dir kept, %s:%s" % (it["die"], it["name"], it["tag"], why[:300], it["host"], it["out"])
    AP.log("AUTO-RESIGN " + msg)
    notices.append(msg)
    AP.tsv_append(LOG_TSV, "%s-%s" % (cid, int(it["finished"])), [it["die"], it["name"], it["host"], it["tag"], it["status"], it["out"], it.get("build_commit", ""), it.get("why", "")])


def poll_eco(AP, st, notices):
    for cid, it in st["items"].items():
        if it.get("status") == "ECO":
            guarded(AP, it, notices, poll_eco_row, AP, cid, it, notices)


def poll_eco_row(AP, cid, it, notices):
    if AP.unit_active(it["eco_unit"]):
        return
    try:
        client = AP.parse_client_log(Path(it["eco_log"]).read_text(errors="replace"))
    except OSError:
        client = {}
    r = AP.rpy(it["host"], PROBE_ECO_RESULT, {"out": it["eco_out"]}, timeout=120)
    if r.get("error"):
        AP.log("AUTO-ECO %s: result probe failed, next tick: %s" % (it["name"], r["error"][:200]))
        return
    v = r.get("verdict")
    # KW-FIX-24 11-06: ABORTED = an ECO step stopped from outside (docker stop / kill, no OOM line): infra, relaunched
    # once at the same --mem like a never-run loop, never a design verdict
    if (v in ("ECO_OOM", "ABORTED") or v is None) and it.get("eco_infra", 0) < MAX_INFRA and (v in ("ECO_OOM", "ABORTED") or client.get("not_run") or client.get("not_completed")):
        it["eco_infra"] = it.get("eco_infra", 0) + 1
        if v == "ECO_OOM":
            it["eco_mem"] = int(it.get("eco_mem", ECO_MEM_GB) * 1.5 + 0.999)
        it.update(status="WAIT", why="late-ECO infra (%s); relaunch at --mem %s" % (v or "not run", it.get("eco_mem", ECO_MEM_GB)))
        it.setdefault("eco_done", {}).pop(it.get("eco_key"), None)
        AP.log("AUTO-ECO %s/%s: %s" % (it["die"], it["name"], it["why"]))
        return
    m = r.get("metrics") or {}
    nums = "TT %s FF %s DRV %s DRC %s" % (m.get("tt"), m.get("ff"), m.get("drv"), m.get("drc"))
    if v == "PASS" and r.get("best_signoff"):
        it.update(status="WAIT", why="late-ECO PASS, re-sign next", eco_record=r["best_signoff"])
        msg = "%s/%s late-ECO PASS %s, %s:%s; re-sign follows" % (it["die"], it["name"], nums, it["host"], r.get("best_dir"))
    elif r.get("best_signoff"):                  # the next tick's judge_eco sends it to a lane: no second loop
        it.update(status="WAIT", why="late-ECO %s, best %s, %s" % (v, nums, r.get("reason") or "client exit %s" % client.get("exit")), eco_next=r["best_signoff"])
        msg = "%s/%s %s; dir %s:%s" % (it["die"], it["name"], it["why"], it["host"], it["eco_out"])
    else:
        it.update(status="LANE", why="late-ECO %s, no best record, %s" % (v or "no result", r.get("reason") or "client exit %s" % client.get("exit")))
        msg = "%s/%s %s; dir %s:%s" % (it["die"], it["name"], it["why"], it["host"], it["eco_out"])
    AP.log("AUTO-ECO " + msg)
    notices.append(msg)
    AP.tsv_append(LOG_TSV, "eco-%s-%s" % (cid, int(time.time())), [it["die"], it["name"], it["host"], "", "ECO-" + str(v), it["eco_out"], "", it.get("why", "")])


def eco_stop(AP, ap_dir):
    try:
        cfg = json.loads((Path(ap_dir) / "kit_wave.json").read_text())
    except (OSError, ValueError):
        return False
    return cfg.get("auto_eco", True) is False or cfg.get("late_eco", True) is False


def try_eco(AP, c, ctx, it, cid, ap_dir, eco_running, notices):
    """-> True when a late-ECO loop was launched"""
    e = AP.rpy(c["host"], PROBE_ECO, dict(path=c["path"], record=it.get("eco_next"), roots=ROOTS, free_gb=ECO_DISK_GB), timeout=300)
    action, why = judge_eco(c, e, it, ctx["holds"], getattr(AP, "NEAR_WNS_PS", -30.0), getattr(AP, "NEAR_DRC_MAX", 50))
    if action == "LANE" and e.get("odb_sha") in (it.get("eco_done") or {}):
        return False                                 # this DB's loop already reported its result once
    if action != "LAUNCH":
        new = "%s %s" % (action, why)
        if it.get("why") != new:
            it["why"] = new
            if action == "LANE":
                notices.append("%s/%s needs a lane: %s" % (c["die"], c["name"], why[:300]))
        it["status"] = action
        return False
    if eco_running >= MAX_ECO_INFLIGHT or AP.DRY or eco_stop(AP, ap_dir):
        it.update(status="WAIT", why="near miss, ECO not launched this tick (%s)" % why)
        return False
    if not e.get("root"):
        it.update(status="WAIT", why="near miss, no scratch root with %d GB free on %s" % (ECO_DISK_GB, c["host"]))
        return False
    tag = ctx["tag"](c["die"])
    ctx["tool_key"](tag) if tag else None
    shas = ctx["shas"].get(tag) or {}
    if not shas:
        it.update(status="WAIT", why="no tag tools for %s" % c["die"])
        return False
    d, err = stage_tools(AP, c["host"], e["root"], tag, shas)
    if not d:
        it.update(status="WAIT", why=err)
        return False
    n = it.get("eco_attempt", 0) + 1
    out = "%s/claude/auto-resign/eco/%s/%s__%s%s" % (e["root"], c["die"], c["name"], e["odb_sha"][:8], "" if n == 1 else "_a%d" % n)
    mem = it.get("eco_mem", ECO_MEM_GB)
    unit = "ae-%s-a%d" % (cid, n)
    logf = Path(ap_dir) / "auto_resign_jobs" / (unit + ".log")
    if not AP.launch_unit(unit, logf, eco_argv(AP, c, e, d, out, mem)):
        it.update(status="WAIT", why="systemd-run failed")
        return False
    it.update(status="ECO", why=why, eco_unit=unit, eco_log=str(logf), eco_out=out, eco_key=e["odb_sha"], eco_attempt=n, eco_mem=mem, eco_tag=tag)
    it.setdefault("eco_done", {})[e["odb_sha"]] = tag
    msg = "%s/%s near miss enters late-ECO on %s: %s" % (c["die"], c["name"], tag, why)
    AP.log("AUTO-ECO LAUNCH " + msg)
    notices.append(msg)
    return True


def build_commit_of(AP):
    def f(c, p):
        if c.get("source") == "wave" and "@" in str(c.get("src")):
            branch, sha = c["src"].rsplit("@", 1)
            got = known_commit(AP, sha, re.sub(r"^origin/", "", branch))
            if got:
                return got
        for v in (c.get("build_commit"), p.get("build_commit")):
            got = known_commit(AP, v)
            if got:
                return got
        return ""
    return f


def read_ctx(AP, ap_dir):
    """the inputs every launch rests on; (ctx, '') or (None, why nothing may launch)"""
    holds = parse_holds(AP.read_coord(HOLD))
    if holds is None:
        return None, "the hold list is unreadable or empty"
    try:
        cache = json.loads(Path(AP.RELEASE_CACHE).read_text())
    except (OSError, ValueError) as e:
        return None, "release cache unreadable: %s" % e
    age = time.time() - float(cache.get("generated") or 0)
    if age > CACHE_MAX_AGE_S:
        return None, "release cache %d min old" % (age / 60)
    memo = {}

    def key(tag):
        if tag not in memo:
            memo[tag] = tag_shas(AP, tag)
        return tool_key(memo[tag]) if memo[tag] else "NO-TOOLS"
    return dict(holds=holds, cache=cache, revoked=AP.read_coord(REVOKED), retired=AP.read_coord(RETIRED),
                tag=lambda die: next(iter(AP.flow_tags(die)), None), tool_key=key, shas=memo,
                build_commit=build_commit_of(AP)), ""


def _step(AP, ap_dir):
    st = load_state(ap_dir)
    notices = []
    try:
        poll(AP, st, notices, ap_dir)
        poll_eco(AP, st, notices)
        stop = stop_reason(ap_dir)
        if stop:
            st["blocked"] = stop
        else:
            ctx, why = read_ctx(AP, ap_dir)
            if ctx is None:
                if st.get("blocked") != why:
                    AP.log("AUTO-RESIGN no launches: " + why)
                st["blocked"] = why
            else:
                st.pop("blocked", None)
                advance(AP, st, ctx, ap_dir, notices)
                try:
                    prestage(AP, st, ctx)
                except Exception as e:                   # tool export is a convenience; it never stops the pass
                    AP.log("AUTO-RESIGN PRESTAGE skipped: %s: %s" % (type(e).__name__, e))
    finally:                                         # a raise outside the rows still keeps what this pass started and collected
        save_state(ap_dir, st)
        if notices and not AP.DRY:
            AP.coord_append(QUEUE, "- %s AUTO-RESIGN [AUTOPILOT -> COORD, die owners] %s" % (AP.now_s(), " | ".join(notices)))


def candidates(AP, ap_dir):
    try:
        kits = wave_kits((Path(ap_dir) / "kit_wave_stages.tsv").read_text())
    except OSError:
        kits = {}
    cm = getattr(AP.KW, "core_module", lambda x: x) if hasattr(AP, "KW") else (lambda x: x)
    return wave_candidates(AP.load_state().get("jobs") or {}, kits, cm) + parse_registry(AP.read_coord(REGISTRY))


def advance(AP, st, ctx, ap_dir, notices):
    items = st["items"]
    handled = set()
    room = dict(running=sum(1 for it in items.values() if it.get("status") == "RUNNING"),
                eco=sum(1 for it in items.values() if it.get("status") == "ECO"), launched=0)
    for c in candidates(AP, ap_dir):
        handled.add((c["die"], c["name"]))
        cid = cand_id(c)
        it = items.setdefault(cid, dict(die=c["die"], name=c["name"], host=c["host"], path=c["path"], source=c["source"], status="NEW"))
        if it["status"] in ACTIVE:
            continue
        guarded(AP, it, notices, advance_row, AP, c, cid, it, ctx, ap_dir, notices, room)
        if it["status"] in ACTIVE:                   # on disk before the next row, whatever happens to this process
            room["eco" if it["status"] == "ECO" else "running"] += 1
            room["launched"] += it["status"] == "RUNNING"
            save_state(ap_dir, st)
    write_suggest(AP, ap_dir, ctx["cache"], handled)


def advance_row(AP, c, cid, it, ctx, ap_dir, notices, room):
    if it.get("eco_record"):                         # the late-ECO best dir is what gets re-signed
        c = dict(c, record=it["eco_record"])
    if it["status"] == "RECORDED":
        if it.get("tag") in [t for t in ctx_tags(AP, c["die"])]:
            return
        it["why"] = "tag %s no longer on origin" % it.get("tag")
    if room["running"] >= MAX_INFLIGHT or room["launched"] >= MAX_LAUNCH_PER_TICK:
        return
    p = AP.rpy(c["host"], PROBE_RECORD, dict(path=c["path"], record=c.get("record"), roots=ROOTS,
                                             known=dict(stamp=it.get("stamp"), odb_sha=it.get("odb_sha"), netlist_sha=it.get("netlist_sha"))), timeout=300)
    action, why = judge(c, p, ctx, it)
    if action == "WAIT" and why == "no record that counts yet" and c["source"] == "registry" and not p.get("error"):
        try_eco(AP, c, ctx, it, cid, ap_dir, room["eco"], notices)
        return
    it.update({k: p[k] for k in ("stamp", "odb_sha", "netlist_sha") if p.get(k)})
    if action != "LAUNCH":
        new = "%s %s" % (action, why)
        if it.get("why") != new:
            it["why"] = new
            if action == "LANE":                       # one line per change: the record says why a lane is needed
                notices.append("%s/%s needs a lane: %s" % (c["die"], c["name"], why[:300]))
        it["status"] = {"SKIP": "SKIP", "LANE": "LANE", "WAIT": "WAIT"}[action]
        return
    if not p.get("root"):
        it.update(status="WAIT", why="no scratch root with 5 GB free on %s" % c["host"])
        return
    launch(AP, c, p, ctx, it, why, cid, ap_dir)


def ctx_tags(AP, die):
    return AP.flow_tags(die)


def launch(AP, c, p, ctx, it, plan, cid, ap_dir):
    tag, bc = plan["tag"], plan["build_commit"]
    ctx["tool_key"](tag)
    shas = ctx["shas"].get(tag) or {}
    if not shas:
        it.update(status="WAIT", why="%s: signoff.py + lec.py not readable on the hub" % tag)
        return False
    if AP.DRY:
        AP.log("would AUTO-RESIGN %s/%s on %s, build %s" % (c["die"], c["name"], tag, bc[:12]))
        return False
    d, err = stage_tools(AP, c["host"], p["root"], tag, shas)
    if not d:
        it.update(status="WAIT", why=err)
        return False
    n = it.get("attempt", 0) + 1
    out = out_dir(p["root"], c, tag, p["odb_sha"], n)
    mem = it.get("mem", MEM_GB)
    unit = "ar-%s-a%d" % (cid, n)
    logf = Path(ap_dir) / "auto_resign_jobs" / (unit + ".log")
    anyhost = bool(it.get("anyhost"))
    if anyhost:                                        # ARHOST_1111: the output dir exists so ot-run can stage it
        h = AP.ssh_host(c["host"])
        if AP.sh(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", h, "mkdir -p %s" % shlex.quote(out)], timeout=60)[0]:
            it.update(status="WAIT", why="ARHOST: mkdir %s on %s failed" % (out, c["host"]))
            return False
    argv = job_argv(AP, c, p, d, out, tag, bc, mem, anyhost=anyhost)
    rec = dict(status="RUNNING", why="", attempt=n, unit=unit, log=str(logf), out=out, tag=tag, key=plan["key"], build_commit=bc,
               mem=mem, started=time.time(), kit=p["kit"], routed_db=p["odb"], anyhost=anyhost)     # read first: nothing may raise once the unit runs
    if not AP.launch_unit(unit, logf, argv):
        it.update(status="WAIT", why="systemd-run failed")
        return False
    it.update(rec)
    AP.log("AUTO-RESIGN LAUNCH %s/%s %s:%s tag %s build %s --mem %s" % (c["die"], c["name"], c["host"], p["kit"], tag, bc[:12], mem))
    return True


def write_suggest(AP, ap_dir, cache, handled):
    rows = suggestions(cache, handled)
    text = "# counter-listed unversioned records with no autopilot route; a lane may register one in %s\n# die\tname\tnewest record\tcopies\n" % REGISTRY
    text += "".join("\t".join(str(x) for x in r) + "\n" for r in rows)
    if not AP.DRY:
        (Path(ap_dir) / SUGGEST).write_text(text)


def step(AP, ap_dir=None):
    """one pass; a non-blocking lock keeps a manual pass from double-launching with the tick"""
    import fcntl
    ap_dir = ap_dir or AP.AP_DIR
    lk = open(Path(ap_dir) / "auto_resign.lock", "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lk.close()
        return None
    try:
        return _step(AP, ap_dir)
    finally:
        lk.close()


if __name__ == "__main__":
    st = load_state(os.environ.get("AP_DIR", str(Path.home() / "coord" / "autopilot")))
    for it in sorted(st["items"].values(), key=lambda x: (x["die"], x["name"])):
        print("\t".join(str(x) for x in (it["die"], it["name"], it["status"], it.get("host"), it.get("tag", ""), it.get("why", "")[:120])))
    if st.get("blocked"):
        print("BLOCKED:", st["blocked"], file=sys.stderr)
