"""launch_gate.py -- KNOWN-PROBLEM launch gate + POST-PLACEMENT gate (COMPOSE-FAST 11-25; OWNER 04:4x, 04:5x, 05:0x, 05:1x via COORD).

Where it acts.  A wave kit always runs to AUTO-GEOM (placed) first; the ROUTE submission (kit_wave.enqueue_pass) is the full launch.  So the
gate decides there, per row, every tick (ROUTE-HELD rows are re-judged by retry_enqueue, so a fix, a pilot sign-off or idle capacity releases
them without a relaunch).  A private `run-item` kit asks at start: a PROBE decision turns its goal route / finish / auto into place.
Live kits are never cancelled: an ENQUEUED row is never touched.

Decision per (die, type) -> FULL | PILOT | PROBE (+ reason)
  flags     every open problem listed for the type:
              VIS     lanes/VIS-CAUSES.tsv row (die, type); PROVEN when basis starts MEASURED, else advisory (STOPPED, CENSUS-ONLY)
              SMELL   lanes/SMELL.tsv row (die, type); PROVEN
              FP      lanes/FP-<DIE>.tsv (written by the die's FP-CONVERGE lane; latest row per (type, class)); a row FAILs when its
                      status starts FAIL; PROVEN when its proven column is yes/1/true/proven, or the class is an established PRE class
                      (PRE:<CLASS> or a plan_gate_pre class name: PRE findings from established rules), else advisory.  A type with no
                      PASS row of class VISUAL / status FLOORPLAN-CLEAN gets the advisory flag FP:NOT-CLEAN (never blocks).
              RULES   lanes/LAUNCH-GATE-RULES.tsv: a rule whose status is PROVEN blocks whatever its source; the wave rewrites the
                      advisory rows' measured hit rates hourly (rule_stats / promote: PROVEN when >= MIN_FLAGGED flagged and unflagged types,
                      flagged fail rate >= 0.5 and >= 2x the unflagged rate).  New / unproven rules never block (guardrail 1).
              HAND    HAND_PLACE_ONLY (FLOW-0730 F9): CORE-TAP-OWNER, MISAIM, SMELL:GRT, STREET, REACH are PROVEN-HAND: PROBE (place only), never a pilot.
            A row whose cells say FIXED / RESOLVED / CLOSED is not a flag.
  FULL      no proven flag, and the family is a single type or its pilot SIGNED (family release, guardrail 4)
  PILOT     the first full kit of a family: every replicated family runs ONE full pilot (guardrail 4), and a family with proven flags
            still gets ONE full pilot per flag signature (guardrail 3: hold / DRC / LEC surface early); recorded in st['kpg_pilots']
  PROBE     proven flags and the family already has its pilot for this signature, or a replicated family whose pilot is not signed:
            stays placed (ROUTE-HELD "KPG-PROBE: ...")
  idle fill PROBE rows with NO proven flag (family-wait members) route anyway on idle capacity (per host: load < IDLE_RATIO x cores,
            ot-run status), fewest advisory flags first, at most the idle core share / IDLE_KIT_CORES kits per tick (guardrail 2)

POST-PLACEMENT (pp_*): before a FULL / PILOT row routes, its placed kit is read once (auto_visual_review remote read + auto_geom rule
FAILs): setup estimate worse than PP_SETUP_PS (-150), a density pile (auto_geom FAIL on a density / demand / pile rule) or a congestion
hot spot (GRT overflow > 0 or a congestion rule FAIL) -> ROUTE-HELD "PP-REVIEW: ..." and a row in lanes/PP-FLAGS.tsv for the die's FP-CONVERGE
lane to start its next plan iteration; released by an FP-<DIE>.tsv row class POSTPLACE status PASS / RELEASE for the type.  No data = no hold.
Report-only until PP_ENFORCE_AFTER (then enforcing); kit_wave.json launch_gate.pp = off | report | enforce overrides.  The known-problem
gate enforces now (launch_gate.kpg = off | report | enforce, default enforce).
Stdlib only."""
import fnmatch
import json
import os
import re
import subprocess
import time

REFRESH_S = 300
VIS_REL = "lanes/VIS-CAUSES.tsv"
SMELL_REL = "lanes/SMELL.tsv"
RULES_REL = "lanes/LAUNCH-GATE-RULES.tsv"
PP_REL = "lanes/PP-FLAGS.tsv"
DIE_TAG = {"s81": "S81", "s81_head": "HEAD", "head": "HEAD", "qwen_kvsys": "KV", "qwen_compute": "QC", "hbm": "HBM"}
# established plan_gate_pre classes (its CLASSES minus ADVISORY and the tool / input classes): PRE findings from established rules
PRE_CLASSES = ("GEOM", "KITFIT", "KITFIT-OVERLAP", "FIXEDCYC", "ROWSINK", "MODULES", "LANDREMAP", "ISTCYC", "DEADIN", "TAPNAME", "R8STALE", "RELAYSINK",
               "EMITNAME", "RESETPUB", "MACROGHOST", "SEATMATCH", "SITEGRID", "DEPTH", "RSTREACH", "DERIVEDNAME", "ENTRYFOOT", "ISTPRICE", "RSTPIN",
               "RSTNAMES", "STNXREF", "COMPOSEDROP", "FTSITE", "R8BOUND", "HALOCORNER", "MONLEG", "CABIND")
SMELL_NOT = ("CHECKPOINT", "RENDER", "")                  # SMELL.tsv rows that only record a render checkpoint are not smells
FP_META = ("type", "family", "die", "note", "notes", "iter", "kit", "fails", "scope", "owner", "ts", "time", "updated", "detail", "proven",
           "kit_max_tap_sinks", "measured_le_1000", "lane_latency(g0/fic)")
CLEARED = re.compile(r"\b(FIXED|RESOLVED|CLOSED)\b", re.I)
TRUE = ("yes", "y", "1", "true", "proven")
MIN_FLAGGED = 4
# FLOW-0730 F9 (COORD ruling 11-25): five rules measured to separate failing from passing types (CORE-TAP-OWNER 87/87, MISAIM 25/25, SMELL:GRT 15/15,
# STREET 7/7, REACH 95/102 vs 63/95) are PROVEN by hand: a type any of them flags gets PLACE PROBES ONLY (no pilot, no full route kit) until the flag
# clears.  Applied in code so the hourly rule-table rewrite cannot demote them; the table rows are written PROVEN-HAND.  Everything else stays advisory.
HAND_PLACE_ONLY = frozenset({"FP:CORE-TAP-OWNER", "FP:MISAIM", "SMELL:GRT", "FP:STREET", "FP:REACH"})
IDLE_RATIO = 0.8
IDLE_KIT_CORES = 32
PP_SETUP_PS = -150.0
PP_ENFORCE_AFTER = 1795612800          # 2026-11-25 05:20 PST: one report-only hour after the design post (04:1x)
PP_DENSITY = re.compile(r"density|demand|pile|util", re.I)
PP_CONGEST = re.compile(r"grt|congest|overflow", re.I)
_MEM = {}


# ---------------------------------------------------------------- tables
def parse_tsv(text):
    """-> list of {lowercased header: cell} (comment lines skipped; first non-comment line is the header)"""
    head, out = None, []
    for ln in (text or "").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        f = [c.strip() for c in ln.split("\t")]
        if head is None:
            head = [h.lower() for h in f]
            continue
        out.append({h: (f[i] if i < len(f) else "") for i, h in enumerate(head)} | {"_cells": f})
    return out


def _col(row, *names):
    for n in names:
        if row.get(n):
            return row[n]
    return ""


def _read(rel, reader=None, hub=None):
    if reader:
        try:
            return reader(rel)
        except Exception:                      # noqa: BLE001
            return None
    for base in (os.environ.get("OT_COORD_DIR"), os.path.expanduser("~/coord")):
        if base and os.path.isfile(os.path.join(base, rel)):
            try:
                return open(os.path.join(base, rel), encoding="utf-8", errors="replace").read()
            except OSError:
                pass
    if hub:
        try:
            p = subprocess.run(["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", hub,
                                f"cat ~/coord/{rel} 2>/dev/null"], capture_output=True, text=True, timeout=60)
            return p.stdout if p.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    return None


def tables(die, reader=None, hub=None, now=None):
    """-> {vis, smell, fp, rules} parsed rows for DIE (cached REFRESH_S; an unreadable table is [])"""
    now = time.time() if now is None else now
    out = {}
    for k, rel in (("vis", VIS_REL), ("smell", SMELL_REL), ("fp", f"lanes/FP-{DIE_TAG.get(die, die.upper())}.tsv"), ("rules", RULES_REL)):
        c = _MEM.get(rel)
        if c and now - c[0] < REFRESH_S:
            out[k] = c[1]
            continue
        rows = parse_tsv(_read(rel, reader, hub) or "")
        _MEM[rel] = (now, rows)
        out[k] = rows
    return out


def reset_cache():
    _MEM.clear()


# ---------------------------------------------------------------- flags
def _names(item):
    n = [item] + ([item[3:]] if item.startswith("ot_") else [])
    return n + [re.split(r"__(?:cl|pv|r8)[0-9a-f]{6,}", x, maxsplit=1)[0] for x in n]


def _die_ok(row, die):
    d = _col(row, "die")
    return not d or d.lower() == die.lower() or d.upper() == DIE_TAG.get(die, "")


def _base(n):
    n = str(n or "").strip().rstrip("/").rsplit("/", 1)[-1]
    n = n[3:] if n.startswith("ot_") else n
    return re.split(r"__(?:cl|pv|r8)[0-9a-f]{6,}", n, maxsplit=1)[0]


def _type_ok(row, item):
    """the row's type (or its kit dir name) names ITEM: exact, without ot_, or the same variant base"""
    t = _col(row, "type", "item")
    cands = [x for x in (t, _col(row, "kit")) if x]
    names = _names(item)
    return any(c in names or _base(c) == _base(item) for c in cands)


def _cleared(row):
    return any(CLEARED.search(c) for c in row.get("_cells", [])[2:])


def flags(die, item, T):
    """-> [dict(rule, source, proven, detail)] for one type; rules from the rule table override 'proven'"""
    fl = []
    for r in T.get("vis") or []:
        if _die_ok(r, die) and _type_ok(r, item) and not _cleared(r):
            basis = _col(r, "basis").upper()
            fl.append(dict(rule="VIS:" + (_col(r, "cause") or "?"), source="VIS-CAUSES", proven=basis.startswith("MEASURED"),
                           detail=f"{_col(r, 'kit')} {basis[:20]}"))
    for r in T.get("smell") or []:
        trig = (_col(r, "smell", "trigger", "class", "rule", "cause") or "").upper()
        if trig in SMELL_NOT or not _die_ok(r, die) or not _type_ok(r, item) or _cleared(r):
            continue
        fl.append(dict(rule="SMELL:" + trig, source="SMELL", proven=True, detail=(_col(r, "value", "detail", "note") or "")[:80]))
    clean = False
    for cls, st, proven_cell, r, long_ in fp_rows(die, item, T):
        if (cls in ("VISUAL", "FLOORPLAN-CLEAN") and st.startswith(("PASS", "CLEAN", "FLOORPLAN-CLEAN"))) or st == "FLOORPLAN-CLEAN" \
                or (cls in ("CLEAN", "STATUS") and st in ("YES", "CLEAN", "FLOORPLAN-CLEAN")):
            clean = True
        if not st.startswith("FAIL") or CLEARED.search(st) or (long_ and _cleared(r)):
            continue
        pre = cls.startswith("PRE:") or cls in PRE_CLASSES
        fl.append(dict(rule=cls if cls.startswith("PRE:") else ("PRE:" + cls if pre else "FP:" + cls), source="FP",
                       proven=pre or proven_cell in TRUE, detail=st[:80]))
    if not clean:
        fl.append(dict(rule="FP:NOT-CLEAN", source="FP", proven=False, detail="no VISUAL PASS / CLEAN row"))
    status = {_col(r, "rule"): _col(r, "status").upper() for r in T.get("rules") or []}
    for f in fl:
        s = status.get(f["rule"]) or ""
        if s.startswith("PROVEN"):
            f["proven"] = True
        elif s.startswith("ADVISORY") and f["source"] == "FP" and not f["rule"].startswith("PRE:"):
            f["proven"] = False                       # an FP class marked proven by hand but measured as not predictive
        if f["rule"] in HAND_PLACE_ONLY:
            f["proven"] = True
            f["hand"] = True                          # FLOW-0730 F9: place probes only
    return fl


def fp_rows(die, item, T):
    """FP-<DIE>.tsv rows of ITEM as (CLASS, STATUS, proven cell, row), latest per class.  Two layouts: long (type, class, status[, proven]) and
    wide (type + one column per class, a cell 'FAIL ...' / 'pass' / 'WARN ...'; the FP-CONVERGE tables of 11-25).  A visual* column is VISUAL."""
    last = {}
    for r in T.get("fp") or []:
        if not _die_ok(r, die) or not _type_ok(r, item):
            continue
        if _col(r, "class", "rule", "check") and _col(r, "status", "verdict"):
            last[_col(r, "class", "rule", "check").upper()] = (_col(r, "status", "verdict").upper(), _col(r, "proven").lower(), r, True)
            continue
        for h, v in r.items():
            if h.startswith("_") or h in FP_META or not v:
                continue
            cls = "VISUAL" if h.startswith("visual") else h.upper()
            last[cls] = (v.strip().upper(), "", r, False)
    return [(c,) + v for c, v in last.items()]


# ---------------------------------------------------------------- decision
def sig(fl):
    return ",".join(sorted(f["rule"] for f in fl if f["proven"])) or "-"


def decide(die, item, fl, family, members, pilots, pilot_state, event=""):
    """-> (mode, reason, pilot_key or '').  members: distinct types seen in the family; pilots: st['kpg_pilots'];
    pilot_state(item) -> 'SIGNED' | 'LIVE' | 'FAILED' | ''"""
    proven = [f for f in fl if f["proven"]]
    hand = sorted(f["rule"] for f in proven if f.get("hand"))
    if hand:                                          # FLOW-0730 F9: no pilot, no full kit while a hand-proven rule flags the type
        return "PROBE", f"hand-proven rule(s) {','.join(hand)} (FLOW-0730 F9): place-only probe until the flag clears", ""
    replicated = len(set(members) | {item}) > 1
    s = sig(fl)
    fam_key = f"{die}|{family}|{event}|family"
    blk_key = f"{die}|{family}|{event}|{s}"
    if replicated:
        p = pilots.get(fam_key)
        if not p:                                         # a member already signed / routing is the family's pilot
            seen = {m: pilot_state(m) for m in sorted(set(members) - {item})}
            p = next(({"item": m} for st_ in ("SIGNED", "LIVE") for m, v in seen.items() if v == st_), None)
        if not p:
            return "PILOT", f"family {family} pilot ({len(set(members) | {item})} members)" + (f"; proven flags {s}" if proven else ""), fam_key
        if p["item"] == item and not (proven and pilot_state(item) == "FAILED"):
            return "PILOT", f"family {family} pilot (recorded)", ""
        if p["item"] == item:
            return "PROBE", f"family {family} pilot failed with known problems {s}: place-only probe until a fix changes them", ""
        pst = pilot_state(p["item"])
        if pst != "SIGNED":
            return "PROBE", f"family {family} pilot {p['item']} is {pst or 'pending'}: members route after it signs (family release)", ""
    if not proven:
        return "FULL", "no proven flag" + (" (family pilot SIGNED)" if replicated else ""), ""
    p = pilots.get(blk_key)
    if not p:
        return "PILOT", f"one full pilot for known problems {s} (family {family})", blk_key
    if p["item"] == item and pilot_state(item) in ("LIVE", ""):
        return "PILOT", f"known-problem pilot (recorded) {s}", ""
    return "PROBE", f"known problems {s}: place-only probe (pilot {p['item']} {pilot_state(p['item']) or 'pending'})", ""


def idle_slots(status, ratio=IDLE_RATIO, kit_cores=IDLE_KIT_CORES):
    """free kit slots on hosts under RATIO x cores (ot-run status rows {cores, load}), summed per host: one idle host counts even
    while the rest of the fleet is loaded (COORD 04:2x: epyc2 57/128 while epyc12 178/96); 0 when unknown"""
    n = 0
    for v in (status or {}).values():
        if isinstance(v, dict) and int(v.get("cores") or 0) > 0:
            n += int(max(0.0, ratio * int(v["cores"]) - float(v.get("load") or 0)) // kit_cores)
    return n


def idle_pick(cands, n):
    """cands [(key, n_proven, n_advisory)] -> keys allowed to route on idle capacity: no proven flag, fewest advisory flags first"""
    ok = sorted((c for c in cands if c[1] == 0), key=lambda c: (c[2], c[0]))
    return [c[0] for c in ok[:max(0, n)]]


# ---------------------------------------------------------------- rule table
def outcome(rec):
    """'FAIL' | 'PASS' | '' for a wave record"""
    q = str(rec.get("q_status") or "").upper()
    if q in ("SIGNED", "SIGNED-LINKED"):
        return "PASS"
    if q == "FAIL" or str(rec.get("class") or "").upper() in ("PLAN", "ROUTING", "TIMING", "RTL", "STRUCTURAL", "DESIGN"):
        return "FAIL"
    return ""


def rule_stats(types):
    """types: {(die, type): (outcome, [rules])} -> {rule: [flagged_n, flagged_fail, unflagged_n, unflagged_fail]}"""
    rules = sorted({r for _, rs in types.values() for r in rs})
    out = {}
    judged = {k: v for k, v in types.items() if v[0]}
    for r in rules:
        fn = ff = un = uf = 0
        for o, rs in judged.values():
            if r in rs:
                fn += 1
                ff += o == "FAIL"
            else:
                un += 1
                uf += o == "FAIL"
        out[r] = [fn, ff, un, uf]
    return out


def promote(s):
    fn, ff, un, uf = s
    if fn < MIN_FLAGGED or un < MIN_FLAGGED:              # no contrast: a rule that flags (nearly) every type predicts nothing
        return "ADVISORY"
    fr, ur = ff / fn, uf / un
    return "PROVEN" if fr >= 0.5 and fr >= 2 * ur else "ADVISORY"


def rules_tsv(stats, keep=None, now=None):
    """the LAUNCH-GATE-RULES.tsv text; KEEP: {rule: status} set by hand (a 'PROVEN-HAND' / 'ADVISORY-HAND' status is never rewritten)"""
    ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(now))
    lines = ["# LAUNCH-GATE-RULES.tsv: advisory launch-gate rules and their measured hit rate (kit_wave, hourly). status PROVEN blocks a full launch;",
             "# promotion: >= %d flagged and unflagged types, flagged fail rate >= 0.5 and >= 2x unflagged.  A *-HAND status is kept as written." % MIN_FLAGGED,
             "rule\tstatus\tflagged_n\tflagged_fail\tunflagged_n\tunflagged_fail\tupdated"]
    for r, s in sorted(stats.items()):
        k = (keep or {}).get(r, "")
        st = k if k.endswith("-HAND") else ("PROVEN-HAND" if r in HAND_PLACE_ONLY else promote(s))
        lines.append("\t".join([r, st] + [str(x) for x in s] + [ts]))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- post-placement
PP_EXTRA = r'''
try:
    j = json.load(open(os.path.join(X, "geom", "auto_geom.json")))
    out["geom_fail"] = [[r.get("rule"), r.get("value")] for r in j.get("rules", []) if str(r.get("status")).upper() == "FAIL"][:20]
except Exception:
    out["geom_fail"] = None
'''


def pp_remote_script():
    import auto_visual_review as AVR
    return AVR.REMOTE_SCRIPT.replace("print(json.dumps(out))", PP_EXTRA + "print(json.dumps(out))")


def pp_info(kit_loc, timeout=120):
    host, _, path = kit_loc.partition(":")
    if not host or not path.startswith("/"):
        return None
    try:
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ControlPath=none", host, "python3", "-I", "-", path],
                           input=pp_remote_script(), capture_output=True, text=True, timeout=timeout)
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        return None


def pp_decide(info, setup_ps=PP_SETUP_PS):
    """-> [flag text] (empty = continue).  None / unreadable parts never flag."""
    if not info:
        return []
    import auto_visual_review as AVR
    out = []
    rep = AVR.parse_report(info.get("rpt")) if info.get("rpt") else {}
    setup = rep.get("path_slack") if rep.get("path_slack") is not None else rep.get("wns")
    if setup is not None and setup < setup_ps:
        out.append(f"setup {setup:.0f} ps < {setup_ps:.0f}")
    for rule, val in info.get("geom_fail") or []:
        if PP_DENSITY.search(str(rule)):
            out.append(f"density pile {rule}={val}")
        elif PP_CONGEST.search(str(rule)):
            out.append(f"congestion {rule}={val}")
    try:
        if info.get("grt") not in (None, "") and float(str(info["grt"]).split()[0]) > 0 and not any("congestion" in o for o in out):
            out.append(f"congestion GRT overflow {info['grt']}")
    except ValueError:
        pass
    return out


def pp_released(die, item, T, since):
    """an FP row class POSTPLACE status PASS / RELEASE for the type written after the flag (ts column epoch or 'YYYY-MM-DD HH:MM')"""
    for r in T.get("fp") or []:
        if not (_die_ok(r, die) and _type_ok(r, item)):
            continue
        long_ = _col(r, "class", "rule", "check").upper() == "POSTPLACE" and _col(r, "status", "verdict").upper() in ("PASS", "RELEASE")
        if long_ or str(r.get("postplace") or "").upper().startswith(("PASS", "RELEASE")):
            ts = _col(r, "ts", "time", "updated")
            try:
                t = float(ts) if re.fullmatch(r"\d+(\.\d+)?", ts) else time.mktime(time.strptime(ts[:16], "%Y-%m-%d %H:%M"))
            except ValueError:
                t = since
            if t >= since - 60:
                return True
    return False


def mode(cfg, key, now=None):
    """'off' | 'report' | 'enforce' for 'kpg' (default enforce) / 'pp' (report until PP_ENFORCE_AFTER)"""
    v = str(((cfg or {}).get("launch_gate") or {}).get(key) or "").lower()
    if v in ("off", "report", "enforce"):
        return v
    if key == "pp":
        return "enforce" if (time.time() if now is None else now) >= PP_ENFORCE_AFTER else "report"
    return "enforce"


def private_goal(die, item, goal, hub=None, reader=None, log=print):
    """run-item (private kit): a route / finish / auto goal on a type with proven flags -> 'place' (OT_KPG_FULL=1 keeps it: an explicit
    lane pilot).  Never raises; unreadable tables keep the goal."""
    try:
        g = str(goal or "auto").lower()
        if g not in ("route", "finish", "auto") or os.environ.get("OT_KPG_FULL") == "1":
            return goal
        fl = flags(die, item, tables(die, reader=reader, hub=hub))
        pr = [f["rule"] for f in fl if f["proven"]]
        if not pr:
            return goal
        log(f"KPG-PROBE {die}/{item}: known problems {','.join(pr)}: goal {g} -> place (OT_KPG_FULL=1 runs it full as the lane's pilot)")
        return "place"
    except Exception as e:                       # noqa: BLE001
        log(f"KPG check error {die}/{item}: {type(e).__name__}: {e} (goal kept)")
        return goal


def match_any(item, pats):
    return any(fnmatch.fnmatchcase(item, p) for p in pats or ())
