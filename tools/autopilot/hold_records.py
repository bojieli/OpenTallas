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
import time

TYPED = ("event_adopt", "lint_clean", "input_staged", "kit_snap", "digest_changed", "proof", "census_lt", "tree_ready", "tree_has", "tree_has_sha", "result", "gen_pilot")
LEGACY_OK = ("merge",)          # still evaluated (ancestor of origin/main); accepted in new records too
GLOB = re.compile(r"[*?\[]")
PROOF_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
CENSUS = re.compile(r"^(\d+)(k?)$", re.I)


def split_result(val):
    """'FABLE-FIX-S81-SVC:svc-ready' -> ('FABLE-FIX-S81-SVC', 'svc-ready')"""
    lane, _, tag = str(val).partition(":")
    return lane.strip(), tag.strip()


def split_tree(val):
    """'qwen_compute:/abs/tree' -> ('qwen_compute', '/abs/tree')"""
    die, _, path = str(val).partition(":")
    return die.strip(), path.strip()


def tree_marker_rel(die):
    """the builder's switch file, in the coord tree: lanes/handoff/tree_switch_<die>.json"""
    return f"lanes/handoff/tree_switch_{die}.json"


def census_limit(val):
    """'400k' -> 400000, '400000' -> 400000, else None"""
    m = CENSUS.match(str(val).strip())
    return int(m.group(1)) * (1000 if m.group(2) else 1) if m else None


def plan_id(d):
    return str((d or {}).get("plan_sha256") or (d or {}).get("_plan_sha") or (d or {}).get("plan_sha") or (d or {}).get("event") or "")


def split_pilot(val):
    """'qwen_kvsys:13f758a4fe34' -> ('qwen_kvsys', '13f758a4fe34')  (die : first 12 hex of the tree manifest sha)"""
    die, _, sha = str(val).partition(":")
    return die.strip(), sha.strip().lower()


PILOT_SHA = re.compile(r"^[0-9a-f]{12}$")


def split_term(t):
    kind, _, val = str(t).strip().partition(":")
    return kind.strip(), val.strip()


def adopted_events(d):
    """Current adopted identities only; declarations and previous events never release a hold."""
    d = d or {}
    return {str(v).lower() for v in (d.get("event"), d.get("plan_event"),
            os.path.splitext(os.path.basename(str(d.get("plan") or "")))[0]) if v}


def lineage_events(d):
    """WAVE-FLOW-R2 11-17 (COORD r631): the die's recorded event lineage = the events the current event was composed from (dies.<die>.event_lineage, written by the
    atomic apply when the event changes, or set explicitly), e.g. QC N1B: S4q6d, L2, M"""
    d = d or {}
    v = d.get("event_lineage")
    return {str(x).lower() for x in (v if isinstance(v, (list, tuple)) else [v] if v else []) if x}


def released_events(d):
    """the events an `event_adopt:<X>` term is met by: the current adopted identities AND every ancestor in the recorded lineage (a hold waiting for an event the die
    already builds on is released; a descendant or a sibling that is not in the lineage is not)"""
    return adopted_events(d) | lineage_events(d)


def known_events(d):
    """Event names current or declared: adopted identities, *_prev events, planned_events."""
    d = d or {}
    out = adopted_events(d) | lineage_events(d)
    for k, v in d.items():
        if k.startswith("event_prev") and isinstance(v, str):
            out.add(v.lower())
    for v in d.get("planned_events") or []:
        out.add(str(v).lower())
    return out


def event_re(name):
    """event token pattern: the whole token, or with one trailing '*' the tokens that start with the name (B6gG3* = B6gG3, B6gG3b)"""
    glob = name.endswith("*")
    base = name[:-1] if glob else name
    return re.compile(r"(?<![a-z0-9])" + re.escape(base) + (r"[a-z0-9]*" if glob else "") + r"(?![a-z0-9])")


def event_name_ok(name):
    """3+ characters (before a single trailing '*'), no spaces, no other glob character"""
    base = name[:-1] if name.endswith("*") else name
    return len(base) >= 3 and not re.search(r"\s", name) and not GLOB.search(base)


def _event_token_in(name, hay):
    return any(event_re(name).search(h) for h in hay)



# ---------------------------------------------------------------- dead-term guard (HOLD-FLOW-R 11-16, FABLE-FLOW-2000)
# Dead release terms were the biggest loss of 11-16: a hold waiting for an event / lane / proof that nothing would ever produce.
# (a) a record is refused unless every term resolves to a planned or adopted plan event, a LIVE lane (agent_ids / OWNERS /
#     active in the queue) by EXACT name, or a known system check;  (b) term_alerts() names any held term with no producer for 12 h.
POST_HEAD = re.compile(r"^\s*-?\s*(\d{4}-\d\d-\d\d)\s+(\d\d:\d\d)\s+\S+\s+[A-Za-z]{2,5}\s+\[([A-Za-z0-9_.-]+)\s*->")
LANE_ACTIVE_H = 6            # WAVE-PILOT-FIX 11-17: a lane is live when it posted within 6 h (a registry row alone proves nothing: dead lanes keep theirs)
HOLD_TTL_H = 6               # a hold record whose owner lane is silent for HOLD_TTL_H hours (and was not renewed) expires
OWNER_SINCE = re.compile(r"(\d{4}-\d\d-\d\d)[ T](\d\d:\d\d)")
SYSTEM_CHECKS = ("lint_clean", "kit_snap", "digest_changed", "input_staged", "tree_ready", "tree_has", "tree_has_sha", "gen_pilot", "census_lt", "merge")


def lane_activity(lines):
    """{lane: epoch of its latest post} from queue lines '- 2026-11-16 07:18 PST RESULT [LANE -> ...'"""
    out = {}
    for ln in lines or []:
        m = POST_HEAD.match(ln)
        if not m:
            continue
        try:
            ts = time.mktime(time.strptime(m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M"))
        except ValueError:
            continue
        if ts > out.get(m.group(3), 0):
            out[m.group(3)] = ts
    return out


def registry_lanes(agent_ids_text, owners_text):
    """lane names of lanes/agent_ids.tsv (column 1) and autopilot OWNERS.tsv (owner and default_owner columns)"""
    names = set()
    for ln in (agent_ids_text or "").splitlines():
        if ln.strip() and not ln.startswith("#"):
            names.add(ln.split("\t")[0].strip())
    cols = None
    for ln in (owners_text or "").splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        f = ln.split("\t")
        if f[0] == "die":
            cols = [i for i, c in enumerate(f) if c in ("owner", "default_owner")]
            continue
        for i in cols or []:
            if i < len(f) and f[i].strip() not in ("", "-"):
                names.add(f[i].strip())
    return names


def lane_known(cfg, lane, now=None):
    """-> (ok, why).  Exact name only (a lane named in a different case is not the lane).  cfg['_registry_lanes'] absent = lanes are not
    checkable here (old callers, tests): ok.  Live = in the registry, or posted within LANE_ACTIVE_H hours."""
    reg = cfg.get("_registry_lanes")
    if reg is None:
        return True, ""
    act = cfg.get("_lane_activity") or {}
    now = now or float(cfg.get("_now") or time.time())
    if lane in (cfg.get("_live_lanes") or ()) or now - act.get(lane, 0) <= LANE_ACTIVE_H * 3600:
        return True, ""
    same = sorted({n for n in set(reg) | set(act) if n.lower() == lane.lower()})
    if same:
        return False, f"lane {lane!r} is not a live lane by exact name (did you mean {same[0]!r}?)"
    return False, f"lane {lane!r} has no post in {LANE_ACTIVE_H} h (and is not a listed live lane): nothing will produce this term; name the live successor lane"


def event_variants(name, d):
    """known events of the die that differ from NAME only by suffix (s4q9l2 vs s4q9l2d): an exact-name term fires for one of them only"""
    base = name[:-1] if name.endswith("*") else name
    if name.endswith("*"):
        return []
    return sorted(e for e in known_events(d) if e != base and e.startswith(base) and re.fullmatch(r"[a-z0-9]*", e[len(base):]))


def term_error(term, die, cfg, migrated=False):
    """why a term cannot be written (None = valid).  migrated terms are not validated (they are audited)"""
    if migrated:
        return None
    kind, val = split_term(term)
    d = (cfg.get("dies") or {}).get(die) or {}
    if kind == "event_adopt":
        name = re.sub(r"^event\s+", "", val, flags=re.I).strip().lower()
        if not event_name_ok(name):
            return f"{term!r}: event name must be one token of 3+ characters (one trailing * = prefix)"
        if not any(_event_token_in(name, [e]) for e in known_events(d)):
            var = event_variants(name, d)
            hint = f"; known variants {var}: use the exact name or '{name}*' for a prefix" if var else ""
            return f"{term!r}: no event {name!r} of die {die} (current, previous or planned_events){hint}"
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
    if kind == "tree_ready":
        td, tp = split_tree(val)
        if td != die:
            return f"{term!r}: tree_ready names die {td!r} but the record is die {die!r}"
        if not tp.startswith("/") or tp.endswith("/") or ".." in tp.split("/"):
            return f"{term!r}: tree_ready needs <die>:<absolute tree path without trailing slash>"
        return None
    if kind == "tree_has":
        return None if re.fullmatch(r"r\d{3,4}", val) else f"{term!r}: tree_has needs a ruling id rNNN (true only when the die's current tree tools contain it)"
    if kind == "tree_has_sha":
        return None if re.fullmatch(r"[0-9a-f]{7,40}", val) else f"{term!r}: tree_has_sha needs a commit sha (7-40 hex)"
    if kind == "gen_pilot":
        pd, ps = split_pilot(val)
        if pd != die or not PILOT_SHA.match(ps):
            return f"{term!r}: gen_pilot needs <this die>:<12 hex of the tree manifest sha>"
        return None
    if kind == "result":
        lane, tag = split_result(val)
        if not (PROOF_NAME.match(lane) and PROOF_NAME.match(tag)):
            return f"{term!r}: result needs <lane>:<tag> (one token each); released by a RESULT line of that lane with '<tag> PASS'"
        ok, why = lane_known(cfg, lane)
        return None if ok else f"{term!r}: {why}"
    if kind == "proof":
        return None if PROOF_NAME.match(val) else f"{term!r}: proof needs one name token (a RESULT PASS post naming it)"
    if kind == "census_lt":
        return None if census_limit(val) else f"{term!r}: census_lt needs a cell count such as 400k"
    if kind in LEGACY_OK:
        return None if val else f"{term!r}: empty ref"
    return f"{term!r}: not a typed release term ({', '.join(TYPED)})"


def unreachable_why(term, die, cfg):
    """audit: why a release term of a held item can never become true (None = reachable)"""
    kind, val = split_term(term)
    d = (cfg.get("dies") or {}).get(die) or {}
    if kind == "event_adopt":
        name = re.sub(r"^event\s+", "", val, flags=re.I).strip().lower()
        if not event_name_ok(name):
            return "event name not checkable by the code (under 3 chars or free text)"
        ke = known_events(d)
        if not any(_event_token_in(name, [e]) for e in ke):
            return f"no such event {name!r} (not current, previous or planned)"
        return None
    if kind in ("lint_clean", "kit_snap"):
        return None if val in (cfg.get("dies") or {}) else f"no die {val!r}"
    if kind == "input_staged":
        return None if val.startswith("/") else "relative path"
    if kind == "digest_changed":
        return None
    if kind == "tree_ready":
        td, tp = split_tree(val)
        return None if td == die and tp.startswith("/") else "tree_ready die or path malformed"
    if kind == "tree_has":
        return None if re.fullmatch(r"r\d{3,4}", val) else "tree_has needs rNNN"
    if kind == "tree_has_sha":
        return None if re.fullmatch(r"[0-9a-f]{7,40}", val) else "tree_has_sha needs a commit sha"
    if kind == "gen_pilot":
        pd, ps = split_pilot(val)
        return None if pd == die and PILOT_SHA.match(ps) else "gen_pilot die or manifest sha malformed"
    if kind == "result":
        lane, tag = split_result(val)
        return None if PROOF_NAME.match(lane) and PROOF_NAME.match(tag) else "result lane or tag malformed"
    if kind == "proof":
        return None if PROOF_NAME.match(val) else "proof name not one token"
    if kind == "census_lt":
        return None if census_limit(val) else "census_lt value is not a cell count"
    if kind in LEGACY_OK:
        return None if val else "empty ref"
    return "free-text term: nothing checks it"


class Ctx:
    """evaluation inputs; kit_wave passes its own (is_merged, legacy event_adopt check, input_digest, kit_snap option)"""

    def __init__(self, is_merged=None, event_met=None, digest_fn=None, kit_snap_fn=None, exists_fn=None, proof_fn=None, cells_fn=None, tree_fn=None, marker_fn=None, lint_fn=None, result_fn=None, pilot_fn=None, release_pilot_fn=None, release_pilot_failed_fn=None, tree_has_fn=None):
        base, memo = is_merged or (lambda ref: False), {}
        self.is_merged = lambda ref: memo[ref] if ref in memo else memo.setdefault(ref, bool(base(ref)))
        self.event_met = event_met
        self.digest_fn = digest_fn or (lambda cfg, die: "")
        self.kit_snap_fn = kit_snap_fn or (lambda cfg, die: False)
        self.exists_fn = exists_fn or os.path.exists
        self.proof_fn = proof_fn or (lambda name: False)          # name -> a RESULT PASS line names this proof
        self.result_fn = result_fn or (lambda lane, tag: False)    # (lane, tag) -> a RESULT line of that lane says '<tag> PASS'
        self.lint_fn = lint_fn                                      # (die, item-or-pattern) -> True when no sdc_lint failure is known; None = old _lint_clean list
        self.release_pilot_fn = release_pilot_fn or (lambda die, item, t0: False)    # (die, pilot item, release time) -> the pilot's attempt since then passed GEN
        self.release_pilot_failed_fn = release_pilot_failed_fn    # (die, pilot item, release time) -> the pilot's attempt since then FAILed INFRA / FLOW / per-instance; None = not known
        self.pilot_fn = pilot_fn or (lambda die, sha12: False)    # (die, tree manifest sha[:12]) -> one GEN pilot from that tree passed GEN + preflight
        self.tree_fn = tree_fn or (lambda die, path: False)       # (die, tree) -> marker + smoke + replication on all gen hosts
        self.tree_has_fn = tree_has_fn or (lambda die, token: False)   # (die, rNNN | sha) -> the die's CURRENT tree tools contain that ruling / commit (FABLE-FLOW-1700 item 2)
        self.marker_fn = marker_fn or (lambda die: None)          # die -> parsed lanes/handoff/tree_switch_<die>.json or None
        self.cells_fn = cells_fn or (lambda die, item: None)      # (die, item) -> measured cell count or None (unknown = held)


def term_met(term, rec, die, item, cfg, ctx):
    kind, val = split_term(term)
    d = (cfg.get("dies") or {}).get(die) or {}
    try:
        if kind == "event_adopt":
            if ctx.event_met is not None:
                return bool(ctx.event_met(term, d, ctx.is_merged))
            name = re.sub(r"^event\s+", "", val, flags=re.I).strip().lower()
            if not event_name_ok(name):
                return False
            return _event_token_in(name, released_events(d))
        if kind == "merge":
            ref = val.split()[0] if val else ""
            return bool(ref) and bool(ctx.is_merged(ref))
        if kind == "lint_clean":
            if ctx.lint_fn is not None:
                return bool(ctx.lint_fn(val, item))
            lc = (cfg.get("dies") or {}).get(val, {}).get("_lint_clean")
            return bool(lc) and (item in lc or "*" in lc)
        if kind == "kit_snap":
            return bool(ctx.kit_snap_fn(cfg, val))
        if kind == "input_staged":
            return bool(val) and bool(ctx.exists_fn(val))
        if kind == "tree_ready":
            td, tp = split_tree(val)
            return td == die and bool(ctx.tree_fn(td, tp))
        if kind in ("tree_has", "tree_has_sha"):
            return bool(val) and bool(ctx.tree_has_fn(die, val))
        if kind == "gen_pilot":
            pd, ps = split_pilot(val)
            return pd == die and bool(ctx.pilot_fn(pd, ps))
        if kind == "result":
            lane, tag = split_result(val)
            return bool(ctx.result_fn(lane, tag))
        if kind == "proof":
            return bool(ctx.proof_fn(val))
        if kind == "census_lt":
            n, lim = ctx.cells_fn(die, item), census_limit(val)
            return n is not None and lim is not None and int(n) < lim
        if kind == "digest_changed":
            base = str(rec.get("digest") or "")
            return bool(base) and ctx.digest_fn(cfg, die) not in ("", base)
    except Exception:
        return False
    return False


def proof_exclusions(rec, d):
    """items named as the proof of a proof:<name> term of this record: die.proof_items = {name: [item, ...]}.  A proof:<name> record
    must never hold them (the proof's own routing is what releases the hold)"""
    out = set()
    for t in rec.get("release") or []:
        kind, val = split_term(t)
        if kind == "result":
            val, kind = split_result(val)[1], "proof"          # result:<lane>:<tag> names its proof items by <tag>
        if kind == "proof":
            out.update(str(i) for i in ((d or {}).get("proof_items") or {}).get(val) or [])
        if kind == "gen_pilot":                                  # the pilot item itself is never held by the pilot record
            out.update(str(i) for i in rec.get("pilot_items") or [])
    return out


def carve_keys(keys, excl, names):
    """-> (keys without the proof items, [pattern keys that still cover a proof item because no item list is known])"""
    out, stuck = [], []
    for k in keys:
        if k in excl:
            continue
        if GLOB.search(k) and any(fnmatch.fnmatchcase(i, k) for i in excl):
            if names:
                out.extend(n for n in names if fnmatch.fnmatchcase(n, k) and n not in excl and n not in out)
            else:
                out.append(k)
                stuck.append(k)
            continue
        out.append(k)
    return out, stuck


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
    if rec.get("switch_only"):
        if rec.get("items") or rec.get("patterns") or rec.get("keys"):
            errs.append("a switch_only record holds nothing: no items / patterns / keys")
        if not any(split_term(t)[0] == "tree_ready" for t in rec.get("release") or []):
            errs.append("a switch_only record needs a tree_ready release term")
    elif not (rec.get("items") or rec.get("patterns") or rec.get("keys")):
        errs.append("record selects nothing")
    mig = bool(rec.get("migrated"))
    if not mig and not rec.get("switch_only") and not rec.get("auto_pilot"):
        # WAVE-PILOT-FIX 11-17 (OWNER 06:1x): a hold names its SHARED structural cause and an owner lane that is alive; it expires
        # after HOLD_TTL_H hours of owner silence unless renewed.  Infra / flow / per-instance causes never hold (rules 1-2).
        if not str(rec.get("cause") or "").strip():
            errs.append("a hold needs 'cause': the measured SHARED structural cause (not an infra / flow / per-instance failure)")
        own = str(rec.get("owner") or "").strip()
        if not own:
            errs.append("a hold needs 'owner': the live lane that will lift or renew it (expires after %g h of silence)" % HOLD_TTL_H)
        else:
            ok, why = lane_known(cfg, own)
            if not ok:
                errs.append(f"owner {own!r}: {why}")
    ex = proof_exclusions(rec, d)
    for k in list(rec.get("items") or []) + list(rec.get("keys") or []):
        if k in ex:
            errs.append(f"{k!r} is named as the proof of this record's proof: term: a proof record never holds its own proof items")
    for t in rec.get("release") or []:
        e = term_error(t, die, cfg, migrated=mig)
        if e:
            errs.append(e)
    if not mig and not rec.get("switch_only"):
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


RELEASE_PILOT_MIN = 3        # a release of MORE than this many items launches ONE pilot first (FABLE-FLOW-2200)


RELEASE_PILOTS = 3           # WAVE-PILOT-FIX 11-17: three pilots launch in parallel; the first that passes GEN releases the rest


def release_pilot_picks(cfg, die, d, ready, n=RELEASE_PILOTS):
    """up to N items of READY (explicit names only) that launch first: die.pilot_item when among them, then the smallest known cell counts"""
    names = sorted(k for k in ready if not GLOB.search(str(k)))
    cells = cfg.get("_item_cells") or {}
    names.sort(key=lambda k: (k != d.get("pilot_item"), cells.get((die, k)) if cells.get((die, k)) is not None else 10 ** 12, k))
    return names[:max(1, int(n))]


def release_pilot_pick(cfg, die, d, ready):
    """the one item of READY (explicit names only) that launches first: die.pilot_item when it is among them, else the one with the
    fewest known cells, else the first by name.  '' = none usable (glob keys only): the gate fails open"""
    names = sorted(k for k in ready if not GLOB.search(str(k)))
    if not names:
        return ""
    if d.get("pilot_item") in names:
        return str(d["pilot_item"])
    cells = cfg.get("_item_cells") or {}
    return sorted(names, key=lambda k: (cells.get((die, k)) if cells.get((die, k)) is not None else 10 ** 12, k))[0]


def _latest_row(cfg, die, item):
    best = None
    for r in cfg.get("_item_rows") or []:
        if r.get("die") == die and r.get("item") == item and (best is None or int(r.get("attempt") or 0) >= int(best.get("attempt") or 0)):
            best = r
    return best


def _row_failed(r):
    return bool(r) and (r.get("status") == "FAIL" or (r.get("status") == "ENQUEUED" and r.get("q_status") == "FAIL"))


def held_elsewhere(d, rec_id, item):
    """True when another record of the die names ITEM explicitly (items / keys) or by a pattern: the pilot would not launch"""
    for r in d.get("hold_records") or []:
        if r.get("id") == rec_id or r.get("auto_pilot"):
            continue
        names = list(r.get("items") or []) + list(r.get("keys") or [])
        if item in names or any(fnmatch.fnmatchcase(item, p) for p in list(r.get("patterns") or []) + [n for n in names if GLOB.search(str(n))]):
            if r.get("release"):
                return True
    return False


def pilot_launchable(cfg, die, d, item, rec_id=""):
    """WAVE-PILOT-FIX 11-17 (FABLE-FLOW-1100 / owner r556: no family hold): a pilot is launchable when no other record holds it and its
    latest attempt has not FAILed (a FAIL row is refused a blind relaunch: the family would wait on it forever)"""
    if not item or held_elsewhere(d, rec_id, item):
        return False
    return not _row_failed(_latest_row(cfg, die, item))


def pilot_deadlock(cfg, die, d, rec):
    """PILOT-DEADLOCK: '' when the auto-pilot record may stand, else why it is released: it names a stale tree (not the die's current
    src manifest), or every one of its pilot items is held by another record or has a FAILed latest attempt (fail open)"""
    if not rec.get("auto_pilot"):
        return ""
    cur = str(d.get("src_manifest_hash") or "")[:12].lower()
    for t in rec.get("release") or []:
        kind, val = split_term(str(t))
        if kind == "gen_pilot":
            sha = split_pilot(val)[1]
            if cur and PILOT_SHA.match(cur) and sha != cur:
                return f"PILOT-DEADLOCK: pilot record names tree {sha}, the die is on {cur}"
    items = list(rec.get("pilot_items") or [])
    if items and not any(pilot_launchable(cfg, die, d, i, rec.get("id")) for i in items):
        why = []
        for i in items:
            why.append(f"{i}: " + ("held by another record" if held_elsewhere(d, rec.get("id"), i) else "latest attempt FAILed"))
        return "PILOT-DEADLOCK: no launchable pilot (" + "; ".join(why) + ")"
    return ""


def unreachable_event_expiry(rec, die, cfg):
    """WAVE-PILOT-FIX 11-17 (COORD FABLE-FLOW-2200 F): at an adopt the hold whose event_adopt term names an event that is neither the die's current,
    a previous nor a planned one can never be met (S81 went from 0 to 74 held at the 21:08 tree switch).  '' = the term is reachable"""
    for t in rec.get("release") or []:
        if split_term(str(t))[0] != "event_adopt":
            continue
        why = unreachable_why(str(t), die, cfg)
        if why and why.startswith("no such event"):
            return f"UNREACHABLE: {t}: {why}; dropped at adopt (re-key the hold to a real event to keep it)"
    return ""


def rec_owner(rec):
    """the lane that owns a hold record: its 'owner' field, else the lane of its first result: term, else '' (a legacy record with no owner never expires)"""
    if rec.get("owner"):
        return str(rec["owner"]).strip()
    for t in rec.get("release") or []:
        kind, val = split_term(str(t))
        if kind == "result":
            return split_result(val)[0]
    return ""


def rec_renewed(rec):
    """epoch of the last renewal: rec['renewed_at'] (epoch, or 'YYYY-MM-DD HH:MM'), else the timestamp in rec['owner_since'], else 0"""
    best = 0.0
    for key in ("renewed_at", "owner_since"):
        v = rec.get(key)
        if isinstance(v, (int, float)):
            best = max(best, float(v))
        elif v:
            m = OWNER_SINCE.search(str(v))
            if m:
                try:
                    best = max(best, time.mktime(time.strptime(m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M")))
                except ValueError:
                    pass
    return best


def record_expired(rec, cfg, now=None, hours=None):
    """WAVE-PILOT-FIX 11-17 (OWNER 06:1x): '' when the hold stands, else why it expired.  A record with an owner lane expires when that lane
    has posted nothing for HOLD_TTL_H hours and the record was not renewed in that time (renewed_at / owner_since).  Fails safe: no
    owner, or no readable lane activity this tick (a blind queue read), never expires."""
    if rec.get("no_expiry") is True:
        return ""
    owner = rec_owner(rec)
    act = cfg.get("_lane_activity")
    if not owner or not act:
        return ""
    now = now or float(cfg.get("_now") or time.time())
    ttl = float(hours or HOLD_TTL_H) * 3600
    last = max(float(act.get(owner, 0) or 0), rec_renewed(rec))
    if now - last <= ttl:
        return ""
    since = "no post seen" if not last else f"last post/renewal {(now - last) / 3600:.1f} h ago"
    return f"EXPIRED: owner lane {owner} silent > {HOLD_TTL_H:g} h ({since}); renew with owner/renewed_at"


def key_in_names(key, names):
    key = str(key)
    return key == "*" or any(n == key or n.startswith(key + "__") or (GLOB.search(key) and fnmatch.fnmatchcase(n, key)) for n in names)


def zero_vs_plan(rec, names):
    """COORD 11-17: a record none of whose keys / items / patterns matches an item of the CURRENT plan (names = the plan's item names; [] = unknown, never zero)"""
    raw = [str(x) for f in ("keys", "items", "patterns") for x in rec.get(f) or []]
    return bool(names) and bool(raw) and not any(key_in_names(k, names) for k in raw)


def compile_holds(cfg, ctx=None):
    """expand every die's hold_records into cfg dies.<die>.hold_items (appended after any legacy key, never overriding one), dropping
    keys whose release terms are all met.  Fills cfg['_hold_compiled'][die] = {key: record id}, cfg['_hold_rec_info'][die] = [info],
    and extends cfg['_hold_auto_released'] with (die, key, release text).  -> list of auto-released (die, key, release)"""
    ctx = ctx or Ctx()
    released = []
    comp, info = {}, {}
    for die, ks in (cfg.get("_hold_added") or {}).items():          # recompile: drop what an earlier pass added
        for name, k in ks:
            h = ((cfg.get("dies") or {}).get(die) or {}).get(name)
            if isinstance(h, dict):
                h.pop(k, None)
    cfg["_hold_added"] = added = {}
    cfg["_pilot_deadlock"] = []
    if cfg.get("_hold_auto_released"):
        cfg["_hold_auto_released"] = [r for r in cfg["_hold_auto_released"] if r[0] not in (cfg.get("_hold_rec_dies") or ())]
    rec_dies = set()
    stuck_all = []
    for die, d in (cfg.get("dies") or {}).items():
        recs = d.get("hold_records")
        if not isinstance(recs, list) or not recs:
            continue
        cur = plan_id(d)
        lists = d.get("hold_event_items") or {}
        for name in ("hold_items", "route_hold_items"):
            if not isinstance(d.get(name), dict):
                d[name] = {}
        rec_dies.add(die)
        owned = set()
        for rec in recs:                                   # a record is the authority for its keys: a copy of them written into the
            owned.update(rec_keys(rec, lists.get(str(rec.get("plan_sha") or "")) or lists.get(cur) or []))   # file's hold_items (a dumped
        for name in ("hold_items", "route_hold_items"):    # config) would outlive a release; drop it, the record re-adds what is held
            for k in [k for k in d[name] if k in owned and (name == "hold_items" or any(r.get("route") and k in (r.get("keys") or []) for r in recs))]:
                del d[name][k]
        for rec in recs:
            sha = str(rec.get("plan_sha") or "")
            stale = bool(sha) and bool(cur) and sha != cur
            use = sha
            rebound = False
            if stale and rec.get("follow_plan") and lists.get(cur) is not None:
                use, stale, rebound = cur, False, True
            keys = rec_keys(rec, lists.get(use) or lists.get(sha) or [])
            excl = proof_exclusions(rec, d)
            if excl:
                keys, stuck = carve_keys(keys, excl, (cfg.get("_item_names") or {}).get(die) or [])
                for k in stuck:
                    stuck_all.append((die, rec.get("id"), k))
            rel = [str(t) for t in rec.get("release") or [] if str(t).strip()]
            zero = (not rec.get("migrated")) and bool(rec.get("patterns")) and not keys
            zero_plan = zero_vs_plan(rec, (cfg.get("_plan_item_names") or {}).get(die) or [])
            zero = zero or zero_plan
            held = 0
            tname = "route_hold_items" if rec.get("route") else "hold_items"       # route: true = a ROUTE-HOLD (place/CTS/GRT still run)
            hold = d[tname]
            # RELEASE PILOT (FABLE-FLOW-2200): when a record would release more than RELEASE_PILOT_MIN items at once, ONE pilot item
            # launches first and the rest stay held until it passes GEN (the pilot rule the tree switch uses).  S81 11-16: a hold on 34
            # types released, all 34 launched on an unfixed tree, 33 failed kit_rtl in 11 minutes.  State per record in
            # cfg['_release_pilot'] (kit_wave persists it): {pilot, t, passed}.  Fails open: glob-only keys, no state store.
            exp = record_expired(rec, cfg) if rel is not None else ""
            dl = pilot_deadlock(cfg, die, d, rec) or (unreachable_event_expiry(rec, die, cfg) if not rec.get("keep_unreachable") else "")
            if dl:
                exp = dl
                cfg.setdefault("_pilot_deadlock", []).append((die, rec.get("id"), dl))
            ready = [k for k in keys if exp or (rel and all(term_met(t, rec, die, k, cfg, ctx) for t in rel))]
            gate = {}
            store = cfg.get("_release_pilot")
            sid = f"{die}|{rec.get('id')}"
            if store is not None and (rel or exp) and rec.get("pilot_release") is not False and not rec.get("auto_pilot"):
                st_ = store.get(sid)
                if st_ is None:
                    launched = set((cfg.get("_item_active") or {}).get(die) or [])      # live attempts only: a FAIL / CANCELLED row is not a launch
                    if len(ready) > RELEASE_PILOT_MIN and not (launched & set(ready)):
                        pks = release_pilot_picks(cfg, die, d, ready)
                        if pks:
                            st_ = store[sid] = {"pilot": pks[0], "pilots": pks, "t": float(cfg.get("_now") or time.time()), "passed": False, "n": len(ready)}
                    elif len(ready) > RELEASE_PILOT_MIN:       # some of them already launched: this release happened before the gate existed
                        store[sid] = {"pilot": "", "t": 0.0, "passed": True, "n": len(ready)}
                if st_ is not None and not st_.get("passed"):
                    pl = list(st_.get("pilots") or [st_["pilot"]])
                    if any(ctx.release_pilot_fn(die, p, st_["t"]) for p in pl):
                        st_["passed"] = True                            # the first pilot that passes GEN releases the family
                    elif ctx.release_pilot_failed_fn is not None and all(ctx.release_pilot_failed_fn(die, p, st_["t"]) for p in pl):
                        st_["passed"] = True                            # every pilot failed INFRA / FLOW / per-instance: that never holds a family
                        st_["note"] = "pilots failed per-instance or infra: released (WAVE-PILOT-FIX rules 1-2)"
                    elif any(p in ready for p in pl):
                        gate = {"pilot": st_["pilot"], "pilots": [p for p in pl if p in ready], "n": len(ready)}
            for k in keys:
                if exp or (rel and all(term_met(t, rec, die, k, cfg, ctx) for t in rel)):
                    if not gate or k in gate["pilots"]:
                        released.append((die, k, (exp or " + ".join(rel)) + (" (release pilot)" if gate else "")))
                        continue
                    # held until the pilot passes GEN
                    if k not in hold:
                        hold[k] = f"RELEASE PILOT: {', '.join(gate['pilots'])} launch first (3 in parallel), {gate['n'] - len(gate['pilots'])} more held until one passes GEN. " + str(rec.get("reason", ""))
                        added.setdefault(die, []).append((tname, k))
                    comp.setdefault(die, {})[k] = rec.get("id")
                    held += 1
                    continue
                if k not in hold:
                    hold[k] = rec.get("reason", "")
                    added.setdefault(die, []).append((tname, k))
                comp.setdefault(die, {})[k] = rec.get("id")
                held += 1
            info.setdefault(die, []).append({"id": rec.get("id"), "plan_sha": sha, "stale": stale, "rebound": rebound,
                                             "zero": zero, "zero_plan": zero_plan, "keys": len(keys), "held": held, "release": rel, "expired": exp,
                                             "migrated": bool(rec.get("migrated"))})
    cr = {}
    for die_, d_ in (cfg.get("dies") or {}).items():          # LATENCY-R: keys of records with cancel_running: true (their running builds are stopped, not protected)
        for rec_ in (d_.get("hold_records") or []) if isinstance(d_, dict) else []:
            if rec_.get("cancel_running"):
                cr.setdefault(die_, []).extend(rec_keys(rec_, (d_.get("hold_event_items") or {}).get(str(rec_.get("plan_sha") or "")) or (d_.get("hold_event_items") or {}).get(plan_id(d_)) or []))
    cfg["_hold_cancel_running"] = cr
    cfg["_hold_compiled"], cfg["_hold_rec_info"], cfg["_hold_rec_dies"] = comp, info, rec_dies
    cfg["_hold_proof_stuck"] = stuck_all
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
                add("HOLD-ZERO-MATCH", die, rid, "no key matches an item of the current plan" if inf.get("zero_plan") else "patterns match no item of the plan item list")
            for t in inf["release"]:
                why = unreachable_why(t, die, cfg)
                if why:
                    add("TERM-UNREACHABLE", die, rid, f"{t[:90]}: {why}", n=inf["held"])
                k_, v_ = split_term(t)
                if k_ == "event_adopt":
                    nm_ = re.sub(r"^event\s+", "", v_, flags=re.I).strip().lower()
                    var_ = event_variants(nm_, (cfg.get("dies") or {}).get(die) or {}) if event_name_ok(nm_) else []
                    if var_:
                        add("TERM-VARIANT", die, rid, f"{t[:90]}: exact name; the die also knows {var_} (a suffix variant does NOT fire it; "
                                                      f"use '{nm_}*' if either is meant)", n=inf["held"])
                elif k_ == "result":
                    ok_, why_ = lane_known(cfg, split_result(v_)[0])
                    if not ok_:
                        add("TERM-UNREACHABLE", die, rid, f"{t[:90]}: {why_}", n=inf["held"])
    for die, d in (cfg.get("dies") or {}).items():          # legacy prose keys: a hold_items key with no record has no machine release
        owned = {k for r in d.get("hold_records") or [] for k in (r.get("keys") or []) + (r.get("items") or [])}
        loose = [k for k in (d.get("hold_items") or {}) if k not in owned and k not in (cfg.get("_hold_added") or {}).get(die, [])]
        loose = [k for k in loose if k not in {x for n, x in (cfg.get("_hold_added") or {}).get(die, []) if n == "hold_items"}]
        if loose and die != "hbm":
            add("LEGACY-HOLD", die, "-", f"{len(loose)} hold_items key(s) with no record / typed release: {','.join(loose[:4])}", n=len(loose))
    for die, rid, why in cfg.get("_pilot_deadlock") or []:
        add("PILOT-DEADLOCK", die, rid, why[:200])                                   # released by compile_holds the same pass
    for die, rid, k in cfg.get("_hold_proof_stuck") or []:
        add("PROOF-HELD", die, rid, f"pattern {k!r} still covers a proof item (no item list to carve it)")
    for die, item in launched:
        d = (cfg.get("dies") or {}).get(die) or {}
        for pat in (d.get("hold_items") or {}):
            if fnmatch.fnmatchcase(str(item), pat):
                add("HELD-BUT-LAUNCHED", die, (cfg.get("_hold_compiled") or {}).get(die, {}).get(pat) or "legacy", f"key {pat}", item=item)
                break
    return list(out.values())


def producer_why(term, die, cfg, now, hours=12.0):
    """None when the term has a producer, else why not.  Producers: a planned / current / previous plan event; a lane that is in the
    registry or posted within HOURS; a queue line within HOURS naming a proof; system checks always."""
    kind, val = split_term(term)
    d = (cfg.get("dies") or {}).get(die) or {}
    if kind in SYSTEM_CHECKS:
        return None
    if kind == "event_adopt":
        name = re.sub(r"^event\s+", "", val, flags=re.I).strip().lower()
        if event_name_ok(name) and any(_event_token_in(name, [e]) for e in known_events(d)):
            return None
        return f"no plan event {name!r} is planned or adopted"
    if kind == "result":
        lane = split_result(val)[0]
        reg, act = cfg.get("_registry_lanes"), cfg.get("_lane_activity") or {}
        if reg is None:
            return None
        if lane in (cfg.get("_live_lanes") or ()) or now - act.get(lane, 0) <= hours * 3600:
            return None
        return f"lane {lane!r} has not posted in {hours:g} h (a registry row is not a producer)"
    if kind == "proof":
        recent = [ln for ln in cfg.get("_queue_recent") or [] if val in ln]
        return None if recent or cfg.get("_queue_recent") is None else f"no queue post names proof {val!r} in {hours:g} h"
    return None


def term_alerts(cfg, seen, now=None, hours=12.0, is_met=None):
    """(b) wave alert lines for held release terms with no producer for HOURS.  seen = persistent {key: first epoch without producer},
    updated in place (a producer, or a met term, resets it).  -> [{die,id,term,why,since_h,n}]"""
    now = now or time.time()
    out, live = [], set()
    recs = {die: {r.get("id"): r for r in (d.get("hold_records") or [])} for die, d in (cfg.get("dies") or {}).items()}
    for die, lst in (cfg.get("_hold_rec_info") or {}).items():
        for inf in lst:
            if not inf.get("held"):
                continue
            for t in inf["release"]:
                key = f"{die}|{inf['id']}|{t}"
                try:
                    met = bool(is_met(t, die, recs.get(die, {}).get(inf["id"]) or {})) if is_met else False
                except Exception:
                    met = False
                why = None if met else producer_why(t, die, cfg, now, hours)
                if not why:
                    seen.pop(key, None)
                    continue
                live.add(key)
                first = seen.setdefault(key, now)
                if now - first >= hours * 3600:
                    out.append(dict(die=die, id=inf["id"], term=t, why=why, since_h=round((now - first) / 3600, 1), n=inf["held"]))
    for k in [k for k in seen if k not in live]:
        seen.pop(k, None)
    return out


def summarize(findings):
    c = {}
    for f in findings:
        c[f["code"]] = c.get(f["code"], 0) + f["n"]
    return c


# ------------------------------------------------------------------------------------------------ migration
def migrate_cfg(cfg, only=None):
    """legacy hold_items + hold_release_on -> hold_records, in place, key order kept (consecutive keys with the same reason and
    release become one record).  The legacy dicts are removed (hold_items becomes generated output).  -> {die: n records}"""
    n = {}
    for die, d in (cfg.get("dies") or {}).items():
        if only and die not in only:
            continue
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


def _deep_set(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_set(dst[k], v)
        else:
            dst[k] = v


def apply_tree_switches(cfg, ctx):
    """a tree_ready term whose tree is ready switches the die in memory: dies.<die>.src = tree, src_manifest_hash, die_gen_env merged,
    plus the marker's `config` (die keys, dicts merged, e.g. kit_rtl.bind_out / tools_sha).  The switch does not wait for the
    record's other terms: the tree is what the owner asked for.  -> [(die, tree, [changed keys])] for the trees that changed anything"""
    out = []
    for die, d in (cfg.get("dies") or {}).items():
        for rec in d.get("hold_records") or []:
            for t in rec.get("release") or []:
                kind, val = split_term(t)
                if kind != "tree_ready":
                    continue
                td, tp = split_tree(val)
                if td != die or not ctx.tree_fn(td, tp):
                    continue
                m = ctx.marker_fn(die) or {}
                ch = []
                _switched = d.get("src") != tp
                if d.get("src") != tp:
                    old_src = d.get("src")
                    if old_src:                      # FLEET-OPS-R: the replaced tree is queued for guarded retirement (retire_superseded.py)
                        sup = d.setdefault("superseded_trees", [])
                        if old_src not in sup:
                            sup.append(old_src)
                    d["src"] = tp
                    ch.append("src")
                if m.get("manifest_hash") and d.get("src_manifest_hash") != m["manifest_hash"]:
                    d["src_manifest_hash"] = m["manifest_hash"]
                    ch.append("src_manifest_hash")
                # A marker can repoint plan via explicit config below. Carry
                # its declared digest with that adoption, never calculate a new
                # declaration from arbitrary plan bytes. Explicit config wins.
                if m.get("plan_sha256") and "plan_sha256" not in (m.get("config") or {}):
                    if d.get("plan_sha256") != m["plan_sha256"]:
                        d["plan_sha256"] = m["plan_sha256"]
                        ch.append("plan_sha256")
                for k, v in (m.get("die_gen_env") or {}).items():
                    env = d.setdefault("die_gen_env", {})
                    if env.get(k) != v:
                        env[k] = v
                        ch.append(f"die_gen_env.{k}")
                # The tree base is source identity; tools_sha can legitimately
                # name a different tooling revision. Apply defaults before the
                # marker explicit config, so composed identities stay explicit.
                main_sha = str(m.get("_validated_main_sha") or "")
                if re.fullmatch(r"[0-9a-f]{40}", main_sha):
                    for k, v in (("src_sha", main_sha), ("queue_src", "main@" + main_sha)):
                        if k not in (m.get("config") or {}) and d.get(k) != v:
                            d[k] = v
                            ch.append(k)
                for k, v in (m.get("config") or {}).items():
                    before = json.dumps(d.get(k), sort_keys=True, default=str)
                    if isinstance(v, dict) and isinstance(d.get(k), dict):
                        _deep_set(d[k], v)
                    else:
                        d[k] = v
                    if json.dumps(d.get(k), sort_keys=True, default=str) != before:
                        ch.append(k)
                if _switched and add_pilot_hold(cfg, die, d, m):
                    ch.append("pilot_hold")
                if ch:
                    out.append((die, tp, ch))
    return out


def pilot_item_for(cfg, die, d):
    """the one item that is allowed to GEN first: die.pilot_item (COORD choice), else the smallest known item name of the die"""
    if d.get("pilot_item"):
        return str(d["pilot_item"])
    names = sorted((cfg.get("_item_names") or {}).get(die) or [])
    if names:
        return names[0]
    items = (d.get("hold_event_items") or {}).get(plan_id(d)) or []
    return sorted(items)[0] if items else ""


def add_pilot_hold(cfg, die, d, marker):
    """PILOT wave mode (FLEET-OPS-R, COORD r393): after a tree switch the die is held (hold_items['*']) except ONE pilot item; the hold is
    released when `gen_pilot:<die>:<manifest sha[:12]>` is met = one GEN pilot built from the new tree passed GEN + preflight.  Fails OPEN:
    no resolvable pilot item (or pilot_after_switch: false) adds no hold, so the die can never deadlock.  Superseded auto-pilots are retired only after a valid replacement is resolved;
    manual/physical holds are preserved. -> True when a record was added or a superseded auto-pilot retired"""
    if d.get("pilot_after_switch") is False or cfg.get("pilot_after_switch") is False:
        return False
    sha = str(d.get("src_manifest_hash") or (marker or {}).get("manifest_hash") or "")[:12].lower()
    item = pilot_item_for(cfg, die, d)
    if item and not pilot_launchable(cfg, die, d, item, f"pilot-{die}-{sha}"):
        names = sorted((cfg.get("_item_names") or {}).get(die) or [])
        item = next((n for n in names if pilot_launchable(cfg, die, d, n, f"pilot-{die}-{sha}")), "")   # a launchable pilot, else fail open
    if not PILOT_SHA.match(sha) or not item:
        return False
    rid = f"pilot-{die}-{sha}"
    recs = d.setdefault("hold_records", [])
    current = next((r for r in recs if r.get("id") == rid), None)
    if current is not None and not current.get("auto_pilot"):
        return False                              # a manual record with this id is never replaced
    # A tree's pilot is meaningful only for that tree.  Keeping the old
    # follow_plan auto-pilot would hold every other item forever after the
    # current pilot passed.  Only retire after validating the new identity
    # and pilot above; ordinary/physical holds are preserved verbatim.
    keep = [r for r in recs if not r.get("auto_pilot") or r.get("id") == rid]
    changed = len(keep) != len(recs)
    if current is None:
        keep.append({"id": rid, "plan_sha": plan_id(d), "reason": f"PILOT after tree switch: one GEN pilot ({item}) from tree {sha} must pass GEN + preflight first",
                     "release": [f"gen_pilot:{die}:{sha}"], "items": ["*"], "pilot_items": [item], "follow_plan": True, "auto_pilot": True})
        changed = True
    if changed:
        d["hold_records"] = keep
    return changed


def convert_keys(cfg, keymap):
    """per-key retyping: keymap = {die: {hold key: [typed terms] | None}}.  None = release (the key is dropped).  A key's migrated
    record is split so the key sits in a record of its own release terms (keys with equal terms share one new record).  Every term is
    validated (ValueError).  A key not in any migrated record is an error.  -> (retyped, dropped)"""
    ret = drop = 0
    for die, km in (keymap or {}).items():
        d = (cfg.get("dies") or {}).get(die)
        if d is None:
            raise ValueError(f"keymap: no die {die!r}")
        recs = d.get("hold_records") or []
        where = {k: r for r in recs if r.get("migrated") for k in r.get("keys") or []}
        groups = {}
        for k, terms in km.items():
            if k not in where:
                raise ValueError(f"keymap {die}: {k!r} is not a migrated hold key")
            for t in terms or []:
                e = term_error(t, die, cfg)
                if e:
                    raise ValueError(f"{die}/{k}: {e}")
            where[k]["keys"].remove(k)
            if terms is None:
                drop += 1
                continue
            g = groups.setdefault((where[k]["id"], tuple(terms)), [])
            g.append(k)
            ret += 1
        for n, ((rid, terms), ks) in enumerate(groups.items(), 1):
            src = next(r for r in recs if r["id"] == rid)
            recs.append({"id": f"{rid}-k{n}", "plan_sha": src["plan_sha"], "reason": src["reason"], "release": list(terms),
                         "migrated": True, "keys": ks, "carry": True})
        d["hold_records"] = [r for r in recs if r.get("keys") or r.get("items") or r.get("patterns") or r.get("switch_only")]
    return ret, drop


def convert_cfg(cfg, termmap, planned=None, only=None):
    """r238: declare planned_events ({die: [event, ...]}) and retype migrated records.  termmap = {legacy release text (terms joined
    ' + '): [typed terms]}; a record whose release text is mapped gets the typed terms (each validated with term_error, ValueError on a
    bad one), the others keep their legacy text.  -> (converted keys, [(die, record id, release text, n keys)] unmapped)"""
    for die, evs in (planned or {}).items():
        d = (cfg.get("dies") or {}).get(die)
        if d is None:
            raise ValueError(f"planned_events: no die {die!r}")
        d["planned_events"] = sorted(set(d.get("planned_events") or []) | set(evs))
    done, left = 0, []
    for die, d in (cfg.get("dies") or {}).items():
        if only and die not in only:
            continue
        for rec in d.get("hold_records") or []:
            txt = " + ".join(rec.get("release") or [])
            if txt in termmap:
                new = list(termmap[txt])
                for t in new:
                    e = term_error(t, die, cfg)
                    if e:
                        raise ValueError(f"{die}/{rec.get('id')}: {e}")
                rec["release"] = new
                done += len(rec.get("keys") or rec.get("items") or [])
            elif any(unreachable_why(t, die, cfg) for t in rec.get("release") or []) or not rec.get("release"):
                left.append((die, rec.get("id"), txt, len(rec.get("keys") or rec.get("items") or [])))
    return done, left


# ------------------------------------------------------------------------------------------------ cli
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("migrate", help="legacy hold_items -> hold_records (writes --out, never the live file)")
    m.add_argument("--config", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--die", action="append", help="migrate only this die (repeatable)")
    a_ = sub.add_parser("add", help="validate + append one record (json file) to a config copy")
    a_.add_argument("--config", required=True)
    a_.add_argument("--die", required=True)
    a_.add_argument("--record", required=True)
    a_.add_argument("--out", required=True)
    cv = sub.add_parser("convert", help="declare planned_events + retype migrated release terms (json: {planned:{die:[ev]}, terms:{legacy:[typed]}})")
    cv.add_argument("--config", required=True)
    cv.add_argument("--map", required=True)
    cv.add_argument("--out", required=True)
    cv.add_argument("--die", action="append", help="convert only this die (repeatable)")
    v = sub.add_parser("audit", help="compile + audit a config (no launches known: HELD-BUT-LAUNCHED is per tick in kit_wave)")
    v.add_argument("--config", required=True)
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config))
    cfg.setdefault("dies", {})
    if a.cmd == "migrate":
        print("migrated:", migrate_cfg(cfg, a.die))
        json.dump(cfg, open(a.out, "w"), indent=1)
    elif a.cmd == "convert":
        m = json.load(open(a.map))
        try:
            done, left = convert_cfg(cfg, m.get("terms") or {}, m.get("planned") or {}, a.die)
            kr, kd = convert_keys(cfg, m.get("keys") or {})
            print(f"per-key: retyped {kr}, released {kd}")
        except ValueError as e:
            print("REJECTED:", e)
            return 2
        json.dump(cfg, open(a.out, "w"), indent=1)
        print(f"retyped {done} keys; unmapped {sum(x[3] for x in left)} keys in {len(left)} records")
        for x in left:
            print("UNMAPPED", *x)
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
