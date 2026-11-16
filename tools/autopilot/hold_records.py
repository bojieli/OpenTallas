#!/usr/bin/env python3
"""hold_records.py: compiled holds for kit_wave (HOLDGEN-1115, COORD r223, FABLE-FLOWCLASS-HOLDS-2030 section 3 C/D/F).

A hold is a RECORD bound to a plan sha with typed, machine-checkable release terms; kit_wave.json's hold_items becomes
generated output (compile_holds() fills it in memory at load, next to apply_hold_release_on).

die.hold_records   list of records, applied in order
  {"id": "...", "plan_sha": "<die plan_sha256 it was written for>", "reason": "text shown as the hold reason",
   "release": ["event_adopt:B6gG3b", "lint_clean:s81"],      # every term must be met; [] = never auto-released
   "items": ["explicit_item", ...], "patterns": ["family__*", ...],     # selector, see below
   "carry": false, "follow_plan": false, "digest": "<input digest at write time, for digest_changed>",
   "migrated": false, "keys": [...]}                         # migrated: the legacy hold_items keys verbatim (no expansion)
die.hold_event_items   {"<plan_sha>": ["item", ...]}         # the per-event item list the patterns expand against
die.planned_events     ["B6gG3b", ...]                        # events declared but not adopted yet (valid event_adopt targets)

Release terms (typed): event_adopt:<event>, lint_clean:<die>, input_staged:<abs path>, kit_snap:<die>, digest_changed.
A NEW record is validated when written (add_record / validate_record): an unknown event or die, a relative path, a free-text term
or a pattern that matches no item of its plan is rejected.  A MIGRATED record keeps its legacy text terms (merge:, lane_ready:,
lane_result:, event_adopt names the code cannot check): they behave exactly as before (never auto-released) and the per-tick audit lists them.

Selector expansion: a pattern expands to the explicit items of hold_event_items[plan_sha] it matches, at compile time.  When the die's
plan sha moved: a follow_plan record is re-expanded against the new plan's item list (and rebound in memory), any other record keeps
holding its old items (no behaviour change at an adopt) and the audit reports it SUPERSEDED.

Audit codes (each should be 0): HELD-BUT-LAUNCHED, TERM-UNREACHABLE, HOLD-SUPERSEDED, HOLD-ZERO-MATCH.
"""
import argparse
import fnmatch
import json
import os
import re
import sys

TYPED = ("event_adopt", "lint_clean", "input_staged", "kit_snap", "digest_changed")
LEGACY_OK = ("merge",)          # still evaluated (ancestor of origin/main); accepted in new records too
GLOB = re.compile(r"[*?\[]")


def plan_id(d):
    return str((d or {}).get("plan_sha256") or (d or {}).get("_plan_sha") or (d or {}).get("plan_sha") or (d or {}).get("event") or "")


def split_term(t):
    kind, _, val = str(t).strip().partition(":")
    return kind.strip(), val.strip()


def known_events(d):
    """lower-case event names the die has or declared: current event, plan file stem, *_prev events, planned_events"""
    out = set()
    d = d or {}
    for v in [d.get("event"), os.path.splitext(os.path.basename(str(d.get("plan") or "")))[0]]:
        if v:
            out.add(str(v).lower())
    for k, v in d.items():
        if k.startswith("event_prev") and isinstance(v, str):
            out.add(v.lower())
    for v in d.get("planned_events") or []:
        out.add(str(v).lower())
    return out


def _event_token_in(name, hay):
    pat = re.compile(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])")
    return any(pat.search(h) for h in hay)


def term_error(term, die, cfg, migrated=False):
    """why a term cannot be written (None = valid).  migrated terms are not validated (they are audited)"""
    if migrated:
        return None
    kind, val = split_term(term)
    d = (cfg.get("dies") or {}).get(die) or {}
    if kind == "event_adopt":
        name = re.sub(r"^event\s+", "", val, flags=re.I).strip().lower()
        if len(name) < 3 or re.search(r"\s", name) or GLOB.search(name):
            return f"{term!r}: event name must be one token of 3+ characters"
        if name not in known_events(d) and not any(_event_token_in(name, [e]) for e in known_events(d)):
            return f"{term!r}: no event {name!r} of die {die} (current, previous or planned_events)"
        return None
    if kind in ("lint_clean", "kit_snap"):
        if val not in (cfg.get("dies") or {}):
            return f"{term!r}: no die {val!r}"
        return None
    if kind == "input_staged":
        if not val.startswith("/"):
            return f"{term!r}: input_staged needs an absolute path"
        return None
    if kind == "digest_changed":
        return None if not val else f"{term!r}: digest_changed takes no value"
    if kind in LEGACY_OK:
        return None if val else f"{term!r}: empty ref"
    return f"{term!r}: not a typed release term ({', '.join(TYPED)})"


def unreachable_why(term, die, cfg):
    """audit: why a release term of a held item can never become true (None = reachable)"""
    kind, val = split_term(term)
    d = (cfg.get("dies") or {}).get(die) or {}
    if kind == "event_adopt":
        name = re.sub(r"^event\s+", "", val, flags=re.I).strip().lower()
        if len(name) < 3 or re.search(r"\s", name):
            return "event name not checkable by the code (under 3 chars or free text)"
        ke = known_events(d)
        if name not in ke and not any(_event_token_in(name, [e]) for e in ke):
            return f"no such event {name!r} (not current, previous or planned)"
        return None
    if kind in ("lint_clean", "kit_snap"):
        return None if val in (cfg.get("dies") or {}) else f"no die {val!r}"
    if kind == "input_staged":
        return None if val.startswith("/") else "relative path"
    if kind == "digest_changed":
        return None
    if kind in LEGACY_OK:
        return None if val else "empty ref"
    return "free-text term: nothing checks it"


class Ctx:
    """evaluation inputs; kit_wave passes its own (is_merged, legacy event_adopt check, input_digest, kit_snap option)"""

    def __init__(self, is_merged=None, event_met=None, digest_fn=None, kit_snap_fn=None, exists_fn=None):
        base, memo = is_merged or (lambda ref: False), {}
        self.is_merged = lambda ref: memo[ref] if ref in memo else memo.setdefault(ref, bool(base(ref)))
        self.event_met = event_met
        self.digest_fn = digest_fn or (lambda cfg, die: "")
        self.kit_snap_fn = kit_snap_fn or (lambda cfg, die: False)
        self.exists_fn = exists_fn or os.path.exists


def term_met(term, rec, die, item, cfg, ctx):
    kind, val = split_term(term)
    d = (cfg.get("dies") or {}).get(die) or {}
    try:
        if kind == "event_adopt":
            if ctx.event_met is not None:
                return bool(ctx.event_met(term, d, ctx.is_merged))
            name = re.sub(r"^event\s+", "", val, flags=re.I).strip().lower()
            if len(name) < 3 or " " in name:
                return False
            hay = [str(d.get("event") or "").lower(), os.path.basename(str(d.get("plan") or "")).lower()]
            return _event_token_in(name, hay)
        if kind == "merge":
            ref = val.split()[0] if val else ""
            return bool(ref) and bool(ctx.is_merged(ref))
        if kind == "lint_clean":
            lc = (cfg.get("dies") or {}).get(val, {}).get("_lint_clean")
            return bool(lc) and (item in lc or "*" in lc)
        if kind == "kit_snap":
            return bool(ctx.kit_snap_fn(cfg, val))
        if kind == "input_staged":
            return bool(val) and bool(ctx.exists_fn(val))
        if kind == "digest_changed":
            base = str(rec.get("digest") or "")
            return bool(base) and ctx.digest_fn(cfg, die) not in ("", base)
    except Exception:
        return False
    return False


def rec_keys(rec, die_items):
    """record -> ordered list of hold keys: migrated = legacy keys verbatim; else items + patterns expanded against die_items"""
    if rec.get("migrated"):
        return list(rec.get("keys") or [])
    out = list(rec.get("items") or [])
    for p in rec.get("patterns") or []:
        for it in die_items:
            if fnmatch.fnmatchcase(it, p) and it not in out:
                out.append(it)
    return out


def validate_record(rec, cfg):
    """-> list of errors for a record about to be written (empty = ok)"""
    errs = []
    die = rec.get("die") or rec.get("_die")
    d = (cfg.get("dies") or {}).get(die)
    if d is None:
        return [f"no die {die!r}"]
    if not rec.get("id"):
        errs.append("record has no id")
    if not rec.get("plan_sha"):
        errs.append("record is not bound to a plan_sha")
    if not rec.get("reason"):
        errs.append("record has no reason")
    if not (rec.get("items") or rec.get("patterns") or rec.get("keys")):
        errs.append("record selects nothing")
    mig = bool(rec.get("migrated"))
    for t in rec.get("release") or []:
        e = term_error(t, die, cfg, migrated=mig)
        if e:
            errs.append(e)
    if not mig:
        items = (d.get("hold_event_items") or {}).get(rec.get("plan_sha")) or []
        for p in rec.get("patterns") or []:
            if not any(fnmatch.fnmatchcase(i, p) for i in items):
                errs.append(f"pattern {p!r} matches no item of the plan item list for {str(rec.get('plan_sha'))[:12]}")
        for i in rec.get("items") or []:
            if items and i not in items:
                errs.append(f"item {i!r} is not in the plan item list for {str(rec.get('plan_sha'))[:12]}")
    return errs


def add_record(cfg, die, rec):
    """write one record into cfg (the caller commits the file).  ValueError when a term / event / lane / pattern does not exist"""
    rec = dict(rec, die=die)
    errs = validate_record(rec, cfg)
    if errs:
        raise ValueError("; ".join(errs))
    rec.pop("die", None)
    cfg["dies"][die].setdefault("hold_records", []).append(rec)
    return rec


def compile_holds(cfg, ctx=None):
    """expand every die's hold_records into cfg dies.<die>.hold_items (appended after any legacy key, never overriding one), dropping
    keys whose release terms are all met.  Fills cfg['_hold_compiled'][die] = {key: record id}, cfg['_hold_rec_info'][die] = [info],
    and extends cfg['_hold_auto_released'] with (die, key, release text).  -> list of auto-released (die, key, release)"""
    ctx = ctx or Ctx()
    released = []
    comp, info = {}, {}
    for die, d in (cfg.get("dies") or {}).items():
        recs = d.get("hold_records")
        if not isinstance(recs, list) or not recs:
            continue
        cur = plan_id(d)
        lists = d.get("hold_event_items") or {}
        if not isinstance(d.get("hold_items"), dict):
            d["hold_items"] = {}
        hold = d["hold_items"]
        for rec in recs:
            sha = str(rec.get("plan_sha") or "")
            stale = bool(sha) and bool(cur) and sha != cur
            use = sha
            rebound = False
            if stale and rec.get("follow_plan") and lists.get(cur) is not None:
                use, stale, rebound = cur, False, True
            keys = rec_keys(rec, lists.get(use) or lists.get(sha) or [])
            rel = [str(t) for t in rec.get("release") or [] if str(t).strip()]
            zero = (not rec.get("migrated")) and bool(rec.get("patterns")) and not keys
            held = 0
            for k in keys:
                if rel and all(term_met(t, rec, die, k, cfg, ctx) for t in rel):
                    released.append((die, k, " + ".join(rel)))
                    continue
                if k not in hold:
                    hold[k] = rec.get("reason", "")
                comp.setdefault(die, {})[k] = rec.get("id")
                held += 1
            info.setdefault(die, []).append({"id": rec.get("id"), "plan_sha": sha, "stale": stale, "rebound": rebound,
                                             "zero": zero, "keys": len(keys), "held": held, "release": rel,
                                             "migrated": bool(rec.get("migrated"))})
    cfg["_hold_compiled"], cfg["_hold_rec_info"] = comp, info
    if released:
        cfg["_hold_auto_released"] = list(cfg.get("_hold_auto_released") or []) + released
    return released


def audit(cfg, launched=()):
    """-> list of findings {code, die, id, term/item, detail, n}; launched = [(die, item)] started this tick.  Groups by (code, die, id, detail)"""
    out = {}

    def add(code, die, rid, detail, item=None, n=1):
        g = out.setdefault((code, die, rid, detail), {"code": code, "die": die, "id": rid, "detail": detail, "items": [], "n": 0})
        if item is not None:
            g["items"].append(item)
            g["n"] = len(g["items"])
        else:
            g["n"] += n

    info = cfg.get("_hold_rec_info") or {}
    recs = {die: {r.get("id"): r for r in (d.get("hold_records") or [])} for die, d in (cfg.get("dies") or {}).items()}
    for die, lst in info.items():
        for inf in lst:
            rid = inf["id"]
            if inf["stale"]:
                add("HOLD-SUPERSEDED", die, rid, f"bound to plan {inf['plan_sha'][:12]}, die plan is {plan_id(cfg['dies'][die])[:12]}")
            if inf["zero"]:
                add("HOLD-ZERO-MATCH", die, rid, "patterns match no item of the plan item list")
            for t in inf["release"]:
                why = unreachable_why(t, die, cfg)
                if why:
                    add("TERM-UNREACHABLE", die, rid, f"{t[:90]}: {why}", n=inf["held"])
    for die, item in launched:
        d = (cfg.get("dies") or {}).get(die) or {}
        for pat in (d.get("hold_items") or {}):
            if fnmatch.fnmatchcase(str(item), pat):
                add("HELD-BUT-LAUNCHED", die, (cfg.get("_hold_compiled") or {}).get(die, {}).get(pat) or "legacy", f"key {pat}", item=item)
                break
    return list(out.values())


def summarize(findings):
    c = {}
    for f in findings:
        c[f["code"]] = c.get(f["code"], 0) + f["n"]
    return c


# ------------------------------------------------------------------------------------------------ migration
def migrate_cfg(cfg):
    """legacy hold_items + hold_release_on -> hold_records, in place, key order kept (consecutive keys with the same reason and
    release become one record).  The legacy dicts are removed (hold_items becomes generated output).  -> {die: n records}"""
    n = {}
    for die, d in (cfg.get("dies") or {}).items():
        hold = d.get("hold_items")
        if not isinstance(hold, dict) or not hold:
            continue
        ro = d.get("hold_release_on") if isinstance(d.get("hold_release_on"), dict) else {}
        pid = plan_id(d)
        recs, last = [], None
        for key, why in hold.items():
            cond = str(ro[key]) if key in ro else ""
            sig = (why, cond)
            if sig != last:
                terms = [t.strip() for t in cond.split(" + ") if t.strip()]
                recs.append({"id": f"{die}-mig-{len(recs) + 1:03d}", "plan_sha": pid, "reason": why, "release": terms,
                             "migrated": True, "keys": [], "carry": True})
                last = sig
            recs[-1]["keys"].append(key)
        d["hold_records"] = recs + [r for r in (d.get("hold_records") or [])]
        d["hold_items"] = {}
        d.pop("hold_release_on", None)
        n[die] = len(recs)
    return n


# ------------------------------------------------------------------------------------------------ cli
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("migrate", help="legacy hold_items -> hold_records (writes --out, never the live file)")
    m.add_argument("--config", required=True)
    m.add_argument("--out", required=True)
    a_ = sub.add_parser("add", help="validate + append one record (json file) to a config copy")
    a_.add_argument("--config", required=True)
    a_.add_argument("--die", required=True)
    a_.add_argument("--record", required=True)
    a_.add_argument("--out", required=True)
    v = sub.add_parser("audit", help="compile + audit a config (no launches known: HELD-BUT-LAUNCHED is per tick in kit_wave)")
    v.add_argument("--config", required=True)
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config))
    cfg.setdefault("dies", {})
    if a.cmd == "migrate":
        print("migrated:", migrate_cfg(cfg))
        json.dump(cfg, open(a.out, "w"), indent=1)
    elif a.cmd == "add":
        try:
            add_record(cfg, a.die, json.load(open(a.record)))
        except ValueError as e:
            print("REJECTED:", e)
            return 2
        json.dump(cfg, open(a.out, "w"), indent=1)
        print("written", a.out)
    else:
        compile_holds(cfg)
        f = audit(cfg)
        print(summarize(f))
        for x in f:
            print(x["code"], x["die"], x["id"], x["detail"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
