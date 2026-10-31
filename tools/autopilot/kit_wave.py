#!/usr/bin/env python3
"""kit_wave.py -- automatic KIT WAVE stage of the autopilot tick (lane KIT-WAVE-1, OWNER 2026-10-30 00:2x choice (A):
automate kit generation + launch for all dies; die lanes then only handle failures).

It only automates WHO launches kit builds.  No new sign-off check, no plan change, no ECO (owner 12.18a, 12.14):
every stage is an existing tool on the die's plan of record (bind.py kit-rtl, gen.py phys, kit_preflight.py, the kit's
own run_kit.sh place, geom_check.sh AUTO-GEOM) and a PASS goes to the existing queue (enqueue.py) for route -> sign-off
-> post-route LEC.

Per tick (autopilot.py tick calls step() after admit_new; off unless the config enables it):
  1. config = coord/state autopilot/kit_wave.json (COORD toggles a die with one coord commit), stop files on the hub:
     ~/coord/autopilot/kit_wave.stop (all dies) and kit_wave.<die>.stop (one die): nothing NEW is launched, running
     item units finish and are collected.
  2. gating per die (gate()): the die config names the plan of record + its event; the event must be one COORD named
     (KV event28w_c, S81 1dfae74037a or a descendant, HEAD src25p / src25q2) with G0C + strict bind + clock PASS
     recorded in the config.  QC and HBM stay OFF until the config carries coord_enable "<ruling ref>".
  3. selection (select()): OWNERS.tsv rows of the die in the configured states (default NEEDS-KIT) and kinds (default
     type), no live job, no coord line naming the item for live_claim_h (3 h; any lane that touched it keeps it), named
     in the plan of record, never attempted on this event before (a failure is never retried blindly: it stays until
     the event changes or COORD lists the item under the die's "retry").  Order: cores first (they feed parent kits),
     then most replicas.
  4. capacity (capacity()): global in-flight cap (max_inflight, default 40 slots over the allowed hosts), per-die cap,
     max_launch_per_tick, and at least one allowed host whose ot-run admission takes place_mem_gb now.
  5. each picked item runs ONE transient unit `kit_wave.py run-item SPEC` on the hub: (die prep, once per event: strict
     bind) -> kit-rtl -> gen.py phys -> kit_preflight -> copy kit to the allowed hosts -> ot-run run_kit.sh place
     (synth + pre-place LEC + floorplan + place; ot-run picks the least-loaded allowed host) -> AUTO-GEOM (main
     geom_check.sh, 50-it GRT) -> result.json.  Builds always via ot-run (honest --mem, <= 400k cells).
  6. collection: PASS -> enqueue.py (--geom PASS, geom_ref = the AUTO-GEOM record) so the autopilot routes, signs off
     (measured-hold, hold margin 10 from gen) and runs post-route LEC; every 5th PASS also gets a GEOM REQ for the
     independent visual review (owner rule).  FAIL -> classify() into PLAN / FLOW / RTL / INFRA from the stage + log;
     INFRA (never admitted / host lost / OOM) is relaunched ONCE, everything else stops for the die owner.
     One grouped line per die per tick goes to lanes/COORD-REVIEW-QUEUE.md (for the die's owner lane); OWNERS.tsv
     rows of wave items carry owner KIT-WAVE-1, the live unit and the class + evidence (overlay_owners()).

  7. past GEOM (AUTOBUILD-PIPE-1, OWNER 12.23): follow_queue() joins each enqueued kit with its autopilot job (kit
     runner CTS -> route, signoff_chain sign-off + post-route LEC, archive + PROVENANCE flow tag -> credit_designs
     count) and kit_wave_stages.tsv carries stage/status/class TIMING | ROUTING | PLAN | FLOW | INFRA to the count.
     Types whose plan entry names a child view with a lef but no lib wait (WAIT-DEP, no FAIL record) until the plan
     carries the signed child.  AUTO-GEOM items COORD granted (die geom_exceptions + ruling ref) enqueue PASS-COND.
     An ssh drop before a command ran is retried inside the item (sshd bursts); INFRA relaunches up to infra_attempts.

    kit_wave.py plan [--config F] [--owners F] [--probe]   dry run: per die gate, picks, skips (prints, launches nothing)
    kit_wave.py status                                      wave state table
    kit_wave.py run-item SPEC.json                          one item pipeline (run by the tick inside a unit)
"""
import argparse
import json
import os
import random
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import plan_block_identity as BI

HOME = Path.home()
AP_DIR = Path(os.environ.get("AP_DIR", str(HOME / "coord" / "autopilot")))
OT_RUN = os.environ.get("AP_OT_RUN", str(HOME / ".local/bin/ot-run"))
LANE = "KIT-WAVE-1"
CLASSES = ("PLAN", "FLOW", "RTL", "INFRA")
CELL_CAP = 400_000
# COORD-named plan-of-record events (KIT-WAVE-1 brief 10-30): exact names, or a commit and its descendants
GATE_EVENTS = {"qwen_kvsys": {"exact": ("event28w_c",)},
               "s81": {"descends": "1dfae74037a"},
               # q3 = COORD 23:17 fix-only successor of q2; l45 = COORD 10-30 20:14 HEAD plan of record (12.20 one-block
               # event on l44, ROOT-MERGE-AG 3d326042b); l44 = its parent (ROOT-MERGE-AF b2cd2d28d2a); l46 = COORD 10-30
               # 21:03 HEAD plan of record (hd_st_str one-block on l45, ROOT-MERGE-AG ab0bf8384); l47 = COORD 10-31 01:43
               # HEAD plan of record (insertion_ff_ps 380 -> 342 value-only on 21 types, DIE-HEAD-47 c68675660)
               "s81_head": {"exact": ("src25p", "src25q2", "src25q3", "l44", "l45", "l46", "l47")}}
COORD_ONLY = ("qwen_compute", "hbm")          # OFF until COORD enables them (coord_enable = ruling reference)
GATE_KEYS = ("g0c", "bind", "clock")          # plan event checks that must be PASS (12.4a / 12.17 freeze inputs)
DEFAULTS = {"max_inflight": 40, "max_launch_per_tick": 6, "die_max_inflight": 6, "take_states": ["NEEDS-KIT"],
            "kinds": ["type"], "live_claim_h": 3.0, "place_mem_gb": 48, "place_threads": 8, "geom_mem_gb": 24,
            "gen_mem_gb": 16, "bind_mem_gb": 24, "geom_sample": 5, "place_prefer": [], "hosts": ["intel1", "intel2", "epyc2"],
            "work_root": "/srv/opentallas-scratch2/claude/kit-wave", "infra_attempts": 3, "launch_stagger_s": 6}
# AUTOBUILD-PIPE-1 10-30: an ssh transport drop before the command ran (sshd MaxStartups on the gen host when a tick
# launches 16 items at once) is retried inside the item, never charged to the design: up to SSH_RETRIES more tries
SSH_RETRIES = 3
SSH_DROP = re.compile(r"ot-run: NOT RUN|Connection (?:reset|refused|closed)|kex_exchange_identification|"
                      r"SSH probe exit 255|ssh: connect to host")
STATE_FILE = "kit_wave_state.json"


def now_s():
    return time.strftime("%Y-%m-%d %H:%M %Z")


# ------------------------------------------------------------------------------------------------ config + gating
def load_config(text):
    try:
        cfg = json.loads(text) if text and text.strip() else {}
    except ValueError as e:
        return {"error": f"kit_wave.json unreadable: {e}", "dies": {}}
    cfg.setdefault("dies", {})
    return cfg


def opt(cfg, die, key):
    """die value > global value > default"""
    d = (cfg.get("dies") or {}).get(die) or {}
    if key in d:
        return d[key]
    return cfg.get(key, DEFAULTS.get(key))


def stop_reason(cfg, die, ap_dir=None):
    ap_dir = Path(ap_dir or AP_DIR)
    if cfg.get("error"):
        return cfg["error"]
    if (ap_dir / "kit_wave.stop").exists():
        return "global stop file kit_wave.stop"
    if not cfg.get("enabled"):
        return "wave disabled in kit_wave.json"
    if (ap_dir / f"kit_wave.{die}.stop").exists():
        return f"die stop file kit_wave.{die}.stop"
    d = (cfg.get("dies") or {}).get(die)
    if not d:
        return "no die config"
    if d.get("kill"):
        return f"die kill switch: {d['kill']}"
    return None


def gate(cfg, die, descends=None):
    """(ok, why).  descends(sha, base) -> bool (git merge-base --is-ancestor on the hub); None = exact match only"""
    d = (cfg.get("dies") or {}).get(die) or {}
    if not d.get("enabled"):
        return False, "die not enabled"
    if die in COORD_ONLY and not d.get("coord_enable"):
        return False, f"{die} stays OFF until COORD enables it (coord_enable)"
    ev = str(d.get("event") or "")
    rule = GATE_EVENTS.get(die)
    if rule is None and die not in COORD_ONLY:
        return False, f"no plan-of-record rule for {die}"
    if rule:
        if "exact" in rule and ev not in rule["exact"]:
            return False, f"event '{ev}' is not a COORD plan of record ({'/'.join(rule['exact'])})"
        if "descends" in rule:
            base = rule["descends"]
            if not re.fullmatch(r"[0-9a-f]{7,40}", ev):
                return False, f"event '{ev}' is not a commit (needs {base} or newer)"
            if not (ev.startswith(base) or base.startswith(ev)):
                if descends is None or not descends(ev, base):
                    return False, f"event {ev} does not descend from {base}"
    g = d.get("gate") or {}
    bad = [k for k in GATE_KEYS if str(g.get(k, "")).upper() != "PASS"]
    d.pop("_cores_only", None)
    if bad == ["clock"] and d.get("core_kit"):
        # AUTOBUILD-PIPE-2 (COORD 10-30 23:5x, owner 12.22 item 4): a hard core does not depend on the die clock (its
        # boundary is the plan pin table + common core latency), so a core-kit die builds its kind=core items before
        # the die clock PASSes; partition types still wait for it (select() skips them)
        d["_cores_only"] = True
    elif bad:
        return False, f"plan event {ev}: {'/'.join(bad)} not PASS in the config"
    for k in ("plan", "gen_host", "src"):
        if not d.get(k):
            return False, f"config lacks {k}"
    return True, f"plan of record {ev} ({g.get('evidence', 'no evidence ref')})"


# ------------------------------------------------------------------------------------------------ selection
OWN_COLS = ["die", "item", "kind", "state", "owner", "live_job", "last_activity", "next_step", "evidence",
            "default_owner", "replicas", "members"]


def parse_owners(text):
    rows = []
    for line in (text or "").splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("die\t"):
            continue
        f = line.split("\t")
        f += [""] * (len(OWN_COLS) - len(f))
        rows.append(dict(zip(OWN_COLS, f)))
    return rows


def age_min(s):
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)m\s*", s or "")
    return float(m.group(1)) if m else None


def item_key(die, event, item, block=None):
    """OWNER 12.20 (plans hard-frozen): a kit is keyed on its plan block sha, so a new event with the same
    block reuses the record (no regeneration); only a changed block makes a new wave item"""
    return f"{die}|{item}|b{block[:12]}" if block else f"{die}|{event}|{item}"


PLAN_BLOCK = {
    "hard": "plan entry: hard type (gen skips it unless die cfg hard_wrappers names it)",
    "contract": "plan entry fails kit preflight: clock.core_taps internal without SIGNED TT/FF core means (gen ContractError)",
    # AUTOBUILD-PIPE-1 10-30: not launched (gen would fail 'macros have LEF but no timing liberty'); no FAIL record, so
    # the type launches on its own once the plan of record carries the child's signed lib (die owner / core sign-off)
    "noview": "WAIT-DEP: a child hard core / ROM view in the plan has a lef but no lib (child not signed yet)",
}


def plan_entry_block(d, item):
    """plan-entry kit preflight from the plan probe flags; hard_wrappers opt a hard type back in"""
    if item in (d.get("_identity_holds") or {}):
        return "plan block identity held: " + d["_identity_holds"][item]
    f = (d.get("_plan_flags") or {}).get(item)
    if f == "hard" and item in (d.get("hard_wrappers") or []):
        return None
    return PLAN_BLOCK.get(f)


def select(rows, cfg, die, state, plan_types=None):
    """-> (picked rows in launch order, {reason: [items]})"""
    d = cfg["dies"][die]
    ev = d["event"]
    states = set(opt(cfg, die, "take_states"))
    kinds = set(opt(cfg, die, "kinds"))
    claim_m = float(opt(cfg, die, "live_claim_h")) * 60
    retry = set(d.get("retry") or [])                 # "item@attempt": COORD released that failed attempt
    skip = {}
    picked = []
    for r in rows:
        if r["die"] != die:
            continue
        why = None
        blk = lambda t: plan_types.get(t) if isinstance(plan_types, dict) else None
        rec = (state.get("items") or {}).get(item_key(die, ev, r["item"], blk(r["item"])))
        if r["state"] not in states:
            continue
        if r["kind"] not in kinds:
            why = f"kind {r['kind']} not in wave"
        elif d.get("_cores_only") and r["kind"] != "core":
            why = "die clock not PASS: cores only (core_kit, 12.22 item 4)"
        elif rec and rec.get("status") in ("RUNNING", "LAUNCHING"):
            why = "wave item in flight"
        elif rec and rec.get("status") == "ENQUEUED":
            why = "wave kit enqueued"
        elif rec and f"{r['item']}@{rec.get('attempt')}" not in retry:
            why = f"wave {rec.get('status')} {rec.get('class', '')} on this plan block (no blind retry)".replace("  ", " ")
        elif r["live_job"] not in ("", "none"):
            why = "live job (another lane)"
        elif age_min(r["last_activity"]) is not None and age_min(r["last_activity"]) < claim_m \
                and not str(r["owner"]).startswith("KIT-WAVE"):
            # a recent coord line by another lane naming the item is a claim; the wave's own notices never count
            # (any KIT-WAVE-<n> runner lane: the wave's lane name changes with each successor)
            why = f"lane activity < {claim_m / 60:g} h ({r['owner']})"
        elif plan_types is not None and r["item"] not in plan_types:
            # the plan of record may split an item into classes (<item>__cl<hash>): each class is one wave item
            if r["kind"] == "core":                  # AUTOBUILD-PIPE-2: per pin-table views of a core module
                mv = re.fullmatch(r"(.+)_([0-9a-f]{12})", r["item"])
                cls = (sorted(t for t in plan_types if t != r["item"] and core_module(t) == r["item"])
                       or ([f"{mv.group(1)}__v{mv.group(2)}"] if mv and f"{mv.group(1)}__v{mv.group(2)}" in plan_types else []))
            else:
                cls = sorted(t for t in plan_types if t.startswith(r["item"] + "__"))
            its = state.get("items") or {}
            blocked = [c for c in cls if plan_entry_block(d, c)]
            for c in blocked:
                skip.setdefault(plan_entry_block(d, c), []).append(c)
            cls = [c for c in cls if c not in blocked]
            todo = [c for c in cls if not its.get(item_key(die, ev, c, blk(c)))
                    or f"{c}@{its[item_key(die, ev, c, blk(c))].get('attempt')}" in retry]
            if not cls and blocked:
                continue
            if not cls:
                why = "not in plan of record"
            elif not todo:
                why = "all plan classes already in the wave"
            else:
                picked += [dict(r, item=c, parent_item=r["item"], block_sha=blk(c)) for c in todo]
                continue
        if not why:
            why = plan_entry_block(d, r["item"])
        if why:
            skip.setdefault(why, []).append(r["item"])
            continue
        picked.append(dict(r, block_sha=blk(r["item"])) if blk(r["item"]) else r)

    # Optional exact plan-class allowlist: enable safe canaries while other
    # classes await their die-owned hard views.  Never infer parameter variants.
    if d.get("only_items") is not None:
        allowed = set(d["only_items"])
        for r in picked:
            if r["item"] not in allowed:
                skip.setdefault("outside configured only_items", []).append(r["item"])
        picked = [r for r in picked if r["item"] in allowed]

    def rep(r):
        try:
            return int(r["replicas"])
        except ValueError:
            return 0
    picked.sort(key=lambda r: (0 if r["kind"] == "core" else 1, -rep(r), r["item"]))
    picked = pilot_gate(picked, skip, d, die, state)
    return picked, skip


# ------------------------------------------------------------------------------------------------ OWNER 12.27a pilot first
def pilot_key(d, die, item, kind="type"):
    """OWNER 12.27a die x kit class of a wave item: die config pilot_classes [{class, items: [glob ...]}] (COORD override)
    wins, else AUTOBUILD-PIPE-4 kit_class() '<die>|<kind>|<family>'"""
    import fnmatch
    for g in d.get("pilot_classes") or []:
        if isinstance(g, dict) and g.get("class") and any(fnmatch.fnmatchcase(item or "", pt) for pt in g.get("items") or []):
            return str(g["class"])
    return kit_class(die, item, kind)


def pilot_classes_state(d, die, state):
    """-> (signed classes, {class: in-flight count}) over every wave record of the die (all events): a class is proven
    once one of its kits SIGNED OFF through the queue (route + STA + LEC + GEOM) or COORD lists it in pilot_signed"""
    signed = set(d.get("pilot_signed") or [])
    live = {}
    for r in (state.get("items") or {}).values():
        if r.get("die") != die:
            continue
        c = pilot_key(d, die, r.get("item"), r.get("kind") or "type")
        if r.get("q_status") == "SIGNED":
            signed.add(c)
        elif r.get("status") in ("RUNNING", "LAUNCHING") or (
                r.get("status") == "ENQUEUED" and r.get("q_status") not in ("FAIL", "SIGNED")):
            live[c] = live.get(c, 0) + 1
    return signed, live


def pilot_gate(picked, skip, d, die, state):
    """OWNER 12.27a PILOT FIRST (default on): a die x kit class with no signed-off kit has at most pilot_max (default 2,
    the 12.17 parallel variants) kits in flight, counting the ones already running; new launches past that wait.  Classes
    with a signed pilot keep full volume.  In-flight kits are never touched.  pilot_gate false only by COORD ruling."""
    if d.get("pilot_gate") is False:
        return picked
    cap = int(d.get("pilot_max", 2))
    signed, live = pilot_classes_state(d, die, state)
    out = []
    for r in picked:
        c = pilot_key(d, die, r["item"], r.get("kind") or "type")
        if c in signed:
            out.append(r)
        elif live.get(c, 0) < cap:
            live[c] = live.get(c, 0) + 1
            out.append(r)
        else:
            skip.setdefault(f"PILOT-FIRST 12.27a: class {c} unproven, {cap} pilot(s) in flight", []).append(r["item"])
    return out


# ------------------------------------------------------------------------------------------------ capacity
def parse_otrun_status(text):
    """ot-run --status -> {host: {"admit": GB, "run": n, "load": x, "cores": n}}"""
    out = {}
    for part in (text or "").split("|"):
        m = re.search(r"([A-Za-z0-9_.-]+) admits (\d+) GB.*?load (\d+(?:\.\d+)?)/(\d+) run (\d+)", part)
        if m:
            out[m.group(1)] = {"admit": int(m.group(2)), "load": float(m.group(3)), "cores": int(m.group(4)),
                               "run": int(m.group(5))}
    return out


def inflight(state, die=None):
    return sum(1 for r in (state.get("items") or {}).values()
               if r.get("status") in ("RUNNING", "LAUNCHING") and (die is None or r.get("die") == die))


def capacity(cfg, die, state, status, hub="intel2", launched_now=0):
    """number of items this die may launch now"""
    hosts = [("localhost" if h == hub else h) for h in opt(cfg, die, "hosts")]
    mem = int(opt(cfg, die, "place_mem_gb"))
    if not any((status.get(h) or {}).get("admit", 0) >= mem for h in hosts):
        return 0
    n = min(int(cfg.get("max_inflight", DEFAULTS["max_inflight"])) - inflight(state) - launched_now,
            int(opt(cfg, die, "die_max_inflight")) - inflight(state, die),
            int(cfg.get("max_launch_per_tick", DEFAULTS["max_launch_per_tick"])) - launched_now)
    return max(0, n)


# ------------------------------------------------------------------------------------------------ kit class (12.27a)
# OWNER 12.27 (a) PILOT FIRST: one pilot kit per die x kit class reaches sign-off before volume launches of that class.
# Kit class key (AUTOBUILD-PIPE-4 10-31) = '<die>|<kind>|<family>': family = the wave item with its replica/variant
# suffixes dropped (S81 '__t<n>', '__cl<hash>'; HBM '__v<hash>', '__canon_<hash>') and every digit run as '#', so the
# 50+ ot_s81sl_leaf__t<n> types are one class and col_h9_r0_p3 / col_h10_r0_p4 are one class, while differently
# structured cores (hnx_rp3lp3h_n vs _s, sfu split3 pieces) stay apart.
_KC_SUFFIX = re.compile(r"__(?:t\d+|cl[0-9a-f]{6,}|v[0-9a-f]{6,}|canon_[0-9a-f]{6})(?=__|$)")


def kit_class(die, item, kind="type"):
    fam = item or ""
    while True:
        f2 = _KC_SUFFIX.sub("", fam)
        if f2 == fam:
            break
        fam = f2
    fam = re.sub(r"\d+", "#", fam.rstrip("_"))
    return f"{die}|{kind or 'type'}|{fam}"


# ------------------------------------------------------------------------------------------------ classification
# (class, stage regex or None, text regex, reason).  First match wins; stage-specific rules first.
RULES = [
    ("INFRA", None, r"ot-run: NOT RUN|ot-run: NOT COMPLETED|exit 137\b|Out of memory|oom-kill|OOMKilled|"
                    r"No space left on device|rsync error|Cannot connect to the Docker daemon", "infra"),
    # transport only: an ssh drop BEFORE the command ran.  When ot-run reports 'RAN on <host>' the command ran and its
    # own error decides the class (a probe of another host that failed is not the item's failure)
    ("INFRA-SSH", None, r"ssh: connect to host|Connection (?:reset|refused|closed)|kex_exchange_identification|"
                        r"SSH probe exit 255|Host key verification failed", "infra (ssh transport)"),
    ("RTL", None, r"LEC NOT EQUIVALENT|NOT EQUIVALENT|NON-?EQUIV", "LEC not equivalent"),
    ("INFRA", None, r"^Terminated\b|\nTerminated\b|Killed\s*$", "process terminated (not a design result)"),
    ("PLAN", None, r"ContractError|requires explicit SIGNED", "plan contract metadata missing for this type"),
    # AUTOBUILD-PIPE-4 10-31 (OWNER 12.27 d): generation-time lint (tools/die_plan/kit_gen_lint.py), one class per check
    ("RTL", r"^gen_lint$", r"GEN_LINT FAIL rtl_check", "RTL hierarchy / undriven / multi-driven at gen (GEN_LINT)"),
    ("PLAN", r"^gen_lint$", r"GEN_LINT FAIL (?:macro_tcl|pins_vs_plan)",
     "plan at gen: no static macro sites / kit pins differ from the plan (GEN_LINT)"),
    ("FLOW", r"^gen_lint$", r"GEN_LINT FAIL (?:memory_bits|clock_export_form)",
     "kit recipe at gen: memory bits over SYNTH_MEMORY_MAX_BITS / tie clock export form (GEN_LINT)"),
    # AUTOBUILD-PIPE-1 10-30: dependency, not a flow bug -- a child hard core / ROM / PHY of the type has no signed view
    # (lef+lib) in the plan of record yet; the type relaunches on its own when the plan carries the view (new block sha)
    ("PLAN", None, r"macros have LEF but no timing liberty|has no macro view \(lef/lib\)|KeyError: 'u_phy'|"
                   r"per-instance PHY PG domains differ|holds no macro \(a PHY domain", "WAIT-DEP child view (lef/lib) missing in the plan"),
    # fail-closed kit-RTL contracts whose own message names a plan fix (S81 kit_rtl.sh / image_params.py)
    # AUTOBUILD-PIPE-2: core-kit mode (HBM gen_core_kit_hbm): a view the plan names with no harden recipe / an
    # ambiguous pin->port map / several pin tables under one wave item is the plan / core-recipe owner's
    ("PLAN", None, r"NO_RECIPE |MAP_AMBIGUOUS|CORE_VIEW FAIL", "core view has no recipe / unambiguous port map in the plan"),
    ("PLAN", None, r"PLAN_CORE_MACROS ", "macro core has no KNOWN macro rects in the plan core_macros.json"),
    # AUTOBUILD-PIPE-2 (KV kv3_hg_v1 00:1x): a preflight whose ONLY issues are placed macro paths the bound RTL does not
    # have = the plan names the macro by another name than the netlist (plans elsewhere carry u_bound.<path>; hg_v1
    # hard_cores say head0_e0, bind built u_bound.u_head0_e0); gen places the plan name literally, so place fails too
    ("PLAN", r"^preflight$", r"KIT_PREFLIGHT FAIL issues \d+\n(?:[ \t]*- macro_instances: [^\n]*(?:\n|$))+(?![ \t]*- )",
     "plan macro inst is not the bound netlist path (hard_cores/contents inst, e.g. u_bound.<path>)"),
    # AUTOBUILD-PIPE-2 10-31 (HBM ot_hgi_sm_xload_cl2_bfqg, --core-macros auto): a preflight whose ONLY issues are
    # macro_channels = the plan's static macro rects (core_macros.json / partition contents) leave channels under the
    # 10.8-um rule; the generator places them verbatim, so the plan owner moves the rects
    ("PLAN", r"^preflight$", r"KIT_PREFLIGHT FAIL issues \d+\n(?:[ \t]*- macro_channels: [^\n]*(?:\n|$))+(?![ \t]*- )",
     "plan macro rects violate the macro channel rule (macro_channels)"),
    ("PLAN", None, r"constant spare outputs require a plan fix", "plan fix: constant spare outputs (or COORD exception)"),
    ("PLAN", None, r"used outside a child parameter port",
     "plan class instances differ in a logic parameter (class split / image selector needed)"),
    ("RTL", None, r"RTL_LINT FAIL|multi(?:ple)?[- ]driv|\bundriven (?:net|wire|signal|port|input|bit)|"
                  r"\"undriven\": [1-9]|syntax error|Unexpected token|"
                  r"is not part of the design|Re-definition of module", "RTL elaboration / lint"),
    ("PLAN", None, r"FACE_GUARD FAIL|face_guard[^\n]*FAIL|FAIL_PREFLOOR face_guard", "face guard (plan pins / landing)"),
    ("PLAN", None, r"PORT_BIND FAIL|port_bind[^\n]*FAIL", "port bind (plan pins)"),
    ("PLAN", None, r"LEF master \S+ not found|ORD-2013", "macro not declared in the plan type"),
    ("PLAN", None, r"is blocked|fails? closed|no legal site|DPL-0033|DPL-0036|not in plan|unknown (?:partition )?type|"
                   r"outline|utili[sz]ation .* exceeds|PDN-0\d+", "plan geometry / site"),
    ("PLAN", r"^geom$", r"FAIL", "AUTO-GEOM rule FAIL (geometry)"),
    ("FLOW", r"^bind$", r"FileNotFoundError|No such file", "die-prep bind recipe input missing"),
    ("PLAN", r"^bind$", r".", "plan of record not cleanly bound (strict bind)"),
    ("PLAN", r"^cells$", r".", "cell count above the 400k run cap"),
    ("PLAN", None, r"GEN_NO_KIT", "gen wrote no kit (hard / skipped type in the plan)"),
    ("FLOW", r"^kit_rtl$", r"carry different parameters", "generic kit-rtl cannot kit a per-instance parameterised type (die kit recipe needed)"),
    ("FLOW", r"^place$", r"OT_CLAND no legal nonoverlapping row/site in reserved band",
     "clock-landing ring band capacity (pinslot form: plan budgets.cland_pinslot_types, FLOW-12)"),
    # AUTOBUILD-PIPE-4 10-31 (KV core kits qkd_hr_ingest_eng / qkd_hr_core_order): design-side preflight results that
    # fell into the FLOW buckets -- an SRAM core with no static macro sites (rtl_macro_placer only: the plan names no
    # macro rect / hard_children block) and a core whose synthesized faces are not registered (core_preflight
    # shared / feedthrough / unregistered ports = the core cut / face proof, not the kit flow)
    ("PLAN", None, r"no staged MACRO_PLACEMENT_TCL",
     "macro core has no static macro sites (plan core macro rects / hard_children block)"),
    ("PLAN", None, r"CORE_PREFLIGHT FAIL",
     "core faces not registered (CORE_PREFLIGHT shared/feedthrough/unregistered ports): core cut / RTL owner"),
    ("FLOW", None, r"SYNTH_MEMORY_MAX_BITS|KIT_PREFLIGHT FAIL|preflight[^\n]*FAIL", "kit recipe / preflight"),
    ("FLOW", None, r"Traceback \(most recent call last\)|KeyError|TypeError|AttributeError|invalid command name|"
                   r"can't read \"|Error: .*\.tcl, \d+", "tool / Tcl error"),
]


ERROR_LINE = re.compile(r"Traceback \(most recent|^\w*(?:Error|Exception)\b|Error[: ]|ERROR|FAIL|KitError|S81_KIT_RTL|"
                        r"ot-run: NOT (?:RUN|COMPLETED)|Connection (?:reset|refused|closed)|kex_exchange|exit 137\b")


def error_lines(text, n=16):
    """the last n error-looking lines of a whole stage log: classify() reads these first, so a long log whose decisive
    line (a Python exception, FACE_GUARD FAIL) sits before the kept tail is still classified (AUTOBUILD-PIPE-1 10-30:
    13 'unclassified' gen/kit_rtl FAILs had their ValueError > 3000 chars before the end of the log)"""
    out = [ln.strip()[:600] for ln in (text or "").splitlines() if ERROR_LINE.search(ln)]
    return "\n".join(out[-n:])


def classify(stage, text):
    """-> (class, reason); never guesses INFRA for a design failure"""
    ran = re.search(r"ot-run: RAN on \S+", text or "")
    for cls, st_re, tx_re, why in RULES:
        if st_re and not re.search(st_re, stage or ""):
            continue
        if cls == "INFRA-SSH":
            if ran:
                continue
            cls = "INFRA"
        m = re.search(tx_re, text or "")
        if m:
            snip = (text or "")[max(0, m.start() - 60):m.end() + 100].replace("\n", " ").strip()
            return cls, f"{why} @{stage}: {snip[:220]}"
    return "FLOW", f"unclassified failure @{stage} (see log)"


# ------------------------------------------------------------------------------------------------ AUTO-GEOM verdict
FILL_ONLY = {"fill", "empty"}


def geom_verdict(line, waived=None):
    """AP_AUTO_GEOM line (geom_rules.verdict_line) -> (PASS|FAIL, failing rules, tag).
    OWNER standing rule 10-30 00:5x (via COORD): when fill/empty in the plan slot are the ONLY failing AUTO-GEOM items,
    the kit passes with tag FILL-EXCEPTION; with any other failing (or NA) rule -- clock_reach/tap_sinks, r2r, pin_reg,
    grt, slot fit ... -- it is classified as usual."""
    m = re.search(r"AUTO-GEOM (PASS|FAIL)\b", line or "")
    if not m:
        return "FAIL", [], "no verdict"
    failing = sorted(set(re.findall(r"(?:^|\s)([A-Za-z0-9_]+)=(?:FAIL|NA)\(", line)))
    if m.group(1) == "PASS" and not failing:
        return "PASS", [], ""
    if failing and set(failing) <= FILL_ONLY:
        return "PASS", failing, "FILL-EXCEPTION"
    # AUTOBUILD-PIPE-1 10-30: AUTO-GEOM items COORD/owner granted as exceptions for this item (die config
    # geom_exceptions, each with its ruling ref) are PASS-COND, like a reviewer's PASS-COND; NA is never waived
    # AUTOBUILD-PIPE-4 10-31 (COORD 02:43 t46 ruling): a waiver may carry a value bound (geom_exceptions max:
    # {rule: limit}; geom_waivers -> {rule: (ref, limit)}): the rule is waived only while its measured value <= limit
    waived = {r: (v if isinstance(v, (tuple, list)) else (v, None)) for r, v in dict(waived or {}).items()}
    vals = {}
    for r, v in re.findall(r"(?:^|\s)([A-Za-z0-9_]+)=(?:FAIL|NA|ok|PASS)\(([-0-9.eE+]+)\)", line):
        try:
            vals[r] = float(v)
        except ValueError:
            pass
    waived = {r: (ref, lim) for r, (ref, lim) in waived.items()
              if lim is None or (r in vals and vals[r] <= float(lim))}
    na = set(re.findall(r"(?:^|\s)([A-Za-z0-9_]+)=NA\(", line))
    if failing and not na and set(failing) <= FILL_ONLY | set(waived):
        refs = sorted({waived[r][0] + (f" (<= {waived[r][1]:g})" if waived[r][1] is not None else "")
                       for r in failing if r in waived})
        return "PASS-COND", failing, "EXCEPTION " + "; ".join(refs)
    return "FAIL", failing, ""


def geom_waivers(d, item, parent=None):
    """die config geom_exceptions [{rules: [...], items: [glob ...] (default all), ref: 'COORD ruling', max: {rule: limit}
    (optional value bound)}] -> {rule: ref | (ref, limit)}
    for this wave item (its plan class or parent type may match).  Only COORD/owner-granted rules belong there."""
    import fnmatch
    out = {}
    for g in d.get("geom_exceptions") or []:
        if not isinstance(g, dict) or not g.get("ref"):
            continue                                     # an exception without its ruling reference is ignored
        pats = g.get("items") or ["*"]
        if any(fnmatch.fnmatchcase(x, pt) for pt in pats for x in (item, parent) if x):
            lim = g.get("max") or {}
            for r in g.get("rules") or []:
                out.setdefault(str(r), (str(g["ref"]), float(lim[r])) if r in lim else str(g["ref"]))
    return out


# ------------------------------------------------------------------------------------------------ OWNERS overlay
def overlay_owners(orows, state):
    """mark OWNERS rows of wave items (in place): owner KIT-WAVE-1, live unit, next step = status/class/evidence"""
    idx = {}
    for k, r in (state.get("items") or {}).items():
        it = r.get("parent_item") or r["item"]
        prev = idx.get((r["die"], it))
        if not prev or (r.get("updated") or 0) >= (prev.get("updated") or 0):
            idx[(r["die"], it)] = r
    n = 0
    for o in orows:
        r = idx.get((o.get("die"), o.get("item")))
        if not r or o.get("state") in ("SIGNED", "ROUTING", "RETIRED"):
            continue
        st = r.get("status")
        o["owner"] = LANE
        if st in ("RUNNING", "LAUNCHING"):
            o["live_job"] = f"kit-wave unit {r.get('unit', '-')} ({r.get('stage', 'start')})"
            o["next_step"] = "KIT-WAVE in flight: gen -> place -> AUTO-GEOM -> enqueue"
        elif st == "ENQUEUED":
            o["next_step"] = (f"KIT-WAVE AUTO-GEOM PASS -> autopilot {r.get('q_stage', 'queue')} {r.get('q_status', 'QUEUED')} "
                              f"{r.get('q_class', '')}: {(r.get('q_reason') or '')[:120]} {r.get('kit', '')}").replace("  ", " ")
        else:
            o["next_step"] = f"KIT-WAVE {st} {r.get('class', '')}: {r.get('reason', '')[:160]} -> die owner"
        o["evidence"] = r.get("evidence") or o.get("evidence", "")
        n += 1
    return n


# ------------------------------------------------------------------------------------------------ state
def load_state(ap_dir=None):
    p = Path(ap_dir or AP_DIR) / STATE_FILE
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {"items": {}, "prep": {}, "pass_n": 0}


def save_state(st, ap_dir=None):
    p = Path(ap_dir or AP_DIR) / STATE_FILE
    tmp = p.with_suffix(f".{os.getpid()}")
    tmp.write_text(json.dumps(st, indent=1, sort_keys=True))
    os.replace(tmp, p)


# ------------------------------------------------------------------------------------------------ item pipeline
def cland_pinslot_arg(d):
    """die config cland_pinslot: absent/true -> 'all', false -> '' (plan budgets.cland_pinslot_types only), a list ->
    those type / base names"""
    v = d.get("cland_pinslot", True)
    if v is True:
        return "all"
    if isinstance(v, (list, tuple)):
        return ",".join(str(x) for x in v)
    return ""


CORE_VIEW = re.compile(r"^(?P<module>.+)__v(?P<sha>[0-9a-f]{12})$")
CORE_KIT_DEFAULTS = {   # HBM (physical/die_plan/hbm_arch_cores): views inventory + one ORFS kit per (module, pin table)
    "views_cmd": "python3 physical/die_plan/hbm_arch_cores/views_b2r2.py --plan {plan} --out {views}",
    # AUTOBUILD-PIPE-2 10-31 (KIT-WAVE-3 00:46, every d44f kit failed preflight): clock pins as the plan's M5 entry
    # (--clock-pin-entry on) and the plan core_macros.json KNOWN rects as the static macro placement (--core-macros
    # auto); item_args after them override (argparse: last wins)
    "gen_cmd": "python3 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py --views {views} --view {view} --out {out} "
               "--clock-pin-entry on --core-macros auto {args}",
    "runner": "{kit}/run_kit_hbm.sh"}


def core_module(item):
    """wave core item -> plan module: '<module>__v<pins sha12>' names one pin table of a module with several"""
    m = CORE_VIEW.match(item or "")
    return m.group("module") if m else item


def core_kit_cmds(ck, src, plan, root, work, item):
    """-> (views path, views shell cmd or '', gen shell cmd, kit-finder shell cmd); all paths shell-quoted"""
    q = shlex.quote
    c = dict(CORE_KIT_DEFAULTS, **{k: v for k, v in (ck or {}).items() if v})
    views = c.get("views") or f"{root}/core_views.json"
    vcmd = "" if c.get("views") else c["views_cmd"].format(plan=q(plan), views=q(views), src=q(src))
    # the view of this item: '<module>__v<sha12>' -> module@sha12; a bare module must have exactly one pin table
    m = CORE_VIEW.match(item)
    pick = (f"python3 -c \"import json,sys;v=json.load(open(sys.argv[1]));m,s=sys.argv[2],sys.argv[3];"
            f"L=[x['view'] for x in v.get('view_list') or [] if x.get('module')==m and (not s or x['view'].endswith('@'+s))];"
            f"print(L[0]) if len(L)==1 else sys.exit('CORE_VIEW FAIL '+m+'@'+(s or '*')+': '+str(len(L))+' views in the plan views "
            f"(a module with several pin tables is one wave item per table)')\" {q(views)} "
            f"{q(m.group('module') if m else item)} {q(m.group('sha') if m else '')}")
    gen = (f"VIEW=$({pick}) && echo \"KW_CORE_VIEW $VIEW\" && "
           + c["gen_cmd"].format(views=q(views), view='"$VIEW"', out=q(f"{work}/gen"), plan=q(plan), src=q(src),
                                 args=" ".join(q(x) for x in c.get("args") or [])))
    find = f"ls -d {q(work)}/gen/*/freeze.json 2>/dev/null | head -1 | xargs -r dirname"
    return views, vcmd, gen, find, c["runner"]


def spec_for(cfg, die, item, hub, parent=None, kind="type"):
    d = cfg["dies"][die]
    root = f"{opt(cfg, die, 'work_root')}/{die}/{d['event']}"
    return {"die": die, "item": item, "kind": kind, "event": d["event"], "plan": d["plan"], "gen_host": d["gen_host"],
            "src": d["src"], "src_sha": d.get("src_sha", ""), "queue_src": d.get("queue_src", ""), "root": root, "work": f"{root}/items/{item}",
            "kit_rtl": d.get("kit_rtl") or {},
            # AUTOBUILD-PIPE-2: per-die hard-core generator (HBM gen_core_kit_hbm.py); kind=core items use it instead
            # of kit-rtl + gen.py phys.  {views_cmd, gen_cmd, runner, item_args{module: [...]}} (see core_kit_cmds)
            "core_kit": dict(d.get("core_kit") or {}, args=list((d.get("core_kit") or {}).get("args") or [])
                             + list(((d.get("core_kit") or {}).get("item_args") or {}).get(core_module(item)) or []))
                        if d.get("core_kit") else {},
            "gen_args": list(d.get("gen_args") or []) + list((d.get("type_args") or {}).get(item) or [])
                        + (["--hard-wrappers", item] if item in (d.get("hard_wrappers") or []) else []),
            # default --contract; an explicit [] (die config) = the plain kit preflight the autopilot submit runs
            "preflight_args": list(["--contract"] if d.get("preflight_args") is None else d["preflight_args"]),
            "geom_waivers": geom_waivers(d, item, parent),
            # COORD 10-30 23:1x (GEOM-84 ring key order): every wave kit places landing-ring slot flops in pin order
            # (gen phys --cland-pinslot; a kit without ring bands is unchanged).  Die opt-out: cland_pinslot false.
            "cland_pinslot": cland_pinslot_arg(d),
            "hosts": [h for h in opt(cfg, die, "hosts")], "hub": hub, "place_prefer": list(opt(cfg, die, "place_prefer") or []),
            "place_mem_gb": int(opt(cfg, die, "place_mem_gb")), "place_threads": int(opt(cfg, die, "place_threads")),
            "geom_mem_gb": int(opt(cfg, die, "geom_mem_gb")), "gen_mem_gb": int(opt(cfg, die, "gen_mem_gb")),
            "bind_mem_gb": int(opt(cfg, die, "bind_mem_gb")), "ot_run": OT_RUN}


def _ssh(host, hub):
    return [] if host in ("localhost", hub) else ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", host]


def geom_result_line(txt):
    """Ignore PNG/GRT status lines after the actual geometry verdict."""
    return next((ln for ln in reversed(txt.splitlines())
                 if ln.startswith("AP_AUTO_GEOM AUTO-GEOM ") or ln.startswith("AP_AUTO_GEOM_ERROR")), "")


def run_item(spec_path):
    """the per-item pipeline; prints KW_STAGE lines, writes result.json next to SPEC (never raises)"""
    sp = json.loads(Path(spec_path).read_text())
    out = Path(spec_path).parent
    res = {"stage": "start", "verdict": "FAIL", "die": sp["die"], "item": sp["item"], "t0": time.time()}
    G, hub, W, T = sp["gen_host"], sp["hub"], sp["work"], sp["item"]
    K = f"{W}/gen/{T}"                                   # gen.py phys --out W/gen: kit W/gen/T, runner W/gen/run_kit.sh
    logs = []

    def run(stage, argv, timeout=None, idempotent=False):
        """idempotent: the stage may be rerun after any ssh rc 255 (mkdir/probes); every stage is rerun when ot-run
        says NOT RUN or the ssh transport dropped before 'RAN on' (the command never started)"""
        res["stage"] = stage
        print(f"KW_STAGE {stage} {now_s()} :: {' '.join(shlex.quote(a) for a in argv)[:600]}", flush=True)
        txt_all = ""
        for i in range(SSH_RETRIES + 1):
            p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            txt = (p.stdout or "") + (p.stderr or "")
            txt_all += txt
            drop = (p.returncode != 0 and SSH_DROP.search(txt) and not re.search(r"ot-run: RAN on", txt)
                    and (idempotent or argv[:1] == [sp["ot_run"]]))
            if not drop or i == SSH_RETRIES:
                break
            wait = 20 * (i + 1) + random.uniform(0, 20)
            print(f"KW_SSH_RETRY {stage} try {i + 2} in {wait:.0f} s (transport drop before the command ran)", flush=True)
            txt_all += f"\nKW_SSH_RETRY {stage}: transport drop, retry {i + 2}\n"
            time.sleep(wait)
        (out / f"{stage}.log").write_text(txt_all)
        logs.append(stage)
        print(f"KW_STAGE_RC {stage} {p.returncode}", flush=True)
        return p.returncode, txt

    def remote(cmd):                                     # ssh joins argv with spaces: send ONE quoted command
        return _ssh(G, hub) + ["bash -c " + shlex.quote(cmd)] if _ssh(G, hub) else ["bash", "-c", cmd]

    def otrun(mem, thr, d, cmd, hosts):                  # ot-run names the hub itself 'localhost'
        hosts = ["localhost" if h == hub else h for h in hosts]
        return [sp["ot_run"], "--mem", str(mem), "--threads", str(thr), "--dir", d, "--hosts", ",".join(hosts),
                "--", "bash", "-c", cmd]

    def fail(stage, txt, evidence=""):
        res.update(stage=stage, verdict="FAIL", tail=txt[-3000:], errors=error_lines(txt), evidence=evidence or f"{G}:{W}")
        (out / "result.json").write_text(json.dumps(res, indent=1))
        return 1

    q = shlex.quote
    src, plan = sp["src"], sp["plan"]
    gh = [G]
    time.sleep(max(0.0, float(sp.get("start_delay_s") or 0)))   # stagger a tick's burst of items (gen-host sshd)
    rc, txt = run("mkdir", idempotent=True, argv=remote(f"mkdir -p {q(W)}/logs {q(sp['root'])} && rm -rf {q(W)}/gen {q(W)}/rtl {q(W)}/geom"))
    if rc:
        return fail("mkdir", txt)
    kr = sp["kit_rtl"]
    kit_rtl_arg = ""
    core = sp.get("kind") == "core" and bool(sp.get("core_kit"))
    if core:
        # AUTOBUILD-PIPE-2: hard core = the die's own core generator (HBM gen_core_kit_hbm.py) on the plan's views
        # inventory (built once per event under flock, like the die bind); kit = W/gen/<module>_<sha12>
        views, vcmd, gcmd, kfind, runner = core_kit_cmds(sp["core_kit"], src, plan, sp["root"], W, T)
        if vcmd:
            prep = (f"cd {q(src)} && exec 9>{q(sp['root'])}/.views.lock && flock 9 && "
                    f"if [ ! -s {q(views)} ]; then {vcmd} > {q(sp['root'])}/views.log 2>&1 || "
                    f"{{ rm -f {q(views)}; tail -40 {q(sp['root'])}/views.log; exit 3; }}; fi")
            rc, txt = run("views", otrun(8, 2, sp["root"], prep, gh))
            if rc:
                return fail("views", txt, f"{G}:{sp['root']}/views.log")
        rc, txt = run("gen", otrun(sp["gen_mem_gb"], 2, W, f"cd {q(src)} && {gcmd}", gh))
        if rc:
            return fail("gen", txt)
        rc, kt = run("gen_kit", idempotent=True, argv=remote(kfind))
        K = (kt.strip().splitlines() or [""])[-1].strip()
        if rc or not K.startswith(f"{W}/gen/"):
            return fail("gen", txt + "\nGEN_NO_KIT: core generator exit 0 but wrote no kit (freeze.json) under W/gen")
    elif kr.get("mode") == "bind":
        a = kr["asbuilt"]
        if kr.get("bind_out"):
            # the die's strict bind of record: read-only, never rebuilt here; it must report 0 errors
            bind = kr["bind_out"]
            chk = (f"python3 -c \"import json,sys;r=json.load(open('{bind}/bind_report.json'));e=r.get('errors');"
                   f"n=len(e) if isinstance(e,list) else e;print('BIND errors', n);sys.exit(0 if n == 0 else 3)\"")
            rc, txt = run("bind", remote(chk))
            if rc:
                return fail("bind", "bind of record not clean / unreadable (plan not fully bound)\n" + txt, f"{G}:{bind}")
        else:
            bind = f"{sp['root']}/bind"
            # die prep (once per event, shared by every item; flock so concurrent items wait for one bind): the die's
            # strict bind recipe (config prep_cmd, e.g. asbuilt copies + bind --strict) from the wave's own source
            # checkout, so kit-rtl never reads a removed lane worktree; must end with bind_report errors 0
            cmd = (kr.get("prep_cmd") or "python3 tools/die_plan/bind.py bind {plan} --out {bind} --asbuilt {asbuilt} --strict")
            cmd = cmd.format(plan=q(plan), bind=q(bind), asbuilt=q(a), src=q(src))
            ok = (f"python3 -c \"import json,sys;r=json.load(open('{bind}/bind_report.json'));e=r.get('errors');"
                  f"n=len(e) if isinstance(e,list) else e;print('BIND errors', n);sys.exit(0 if n == 0 else 3)\"")
            prep = (f"cd {q(src)} && exec 9>{q(sp['root'])}/.bind.lock && flock 9 && "
                    f"if [ ! -f {q(bind)}/.kw_bind_ok ]; then mkdir -p {q(bind)} && {{ {cmd} ; }} > {q(sp['root'])}/bind.log 2>&1 "
                    f"&& {ok} && touch {q(bind)}/.kw_bind_ok || {{ tail -40 {q(sp['root'])}/bind.log; exit 3; }}; fi")
            rc, txt = run("bind", otrun(sp["bind_mem_gb"], 4, sp["root"], prep, gh))
            if rc:
                return fail("bind", txt, f"{G}:{sp['root']}/bind.log")
        rc, txt = run("kit_rtl", otrun(8, 2, W, f"cd {q(src)} && python3 tools/die_plan/bind.py kit-rtl {q(plan)} --out {q(bind)} "
                                               f"--asbuilt {q(a)} --type {q(T)} --kit {q(W)}/rtl", gh))
        if rc:
            return fail("kit_rtl", txt)
        kit_rtl_arg = f"--kit-rtl {q(T + '=' + W + '/rtl/kit_rtl.f')}"
    elif kr.get("mode") == "script":
        rc, txt = run("kit_rtl", otrun(8, 2, W, f"cd {q(src)} && TYPE={q(T)} OUT={q(W)}/rtl PLAN={q(plan)} bash {q(kr['script'])}", gh))
        if rc:
            return fail("kit_rtl", txt)
        kit_rtl_arg = f"--kit-rtl {q(T + '=' + W + '/rtl/kit_rtl.f')}"
    if not core:
        ps = sp.get("cland_pinslot") or ""
        # a wave source checkout older than gen phys --cland-pinslot keeps the plan-only pinslot (noted in the gen log)
        pin = (f"PS=; if python3 tools/die_plan/gen.py phys --help 2>/dev/null | grep -q -- --cland-pinslot; then "
               f"PS='--cland-pinslot {ps}'; else echo 'KW_NOTE gen.py of this source has no --cland-pinslot (plan list only)'; fi; "
               if ps and re.fullmatch(r"[A-Za-z0-9_,]+", ps) else "PS=; ")
        gen = (f"cd {q(src)} && {pin}python3 tools/die_plan/gen.py phys {q(plan)} --out {q(W)}/gen --types {q(T)} "
               f"--rtl-root {q(src)} {kit_rtl_arg} $PS {' '.join(q(x) for x in sp['gen_args'])}")
        rc, txt = run("gen", otrun(sp["gen_mem_gb"], 2, W, gen, gh))
        if rc:
            return fail("gen", txt)
        rc, _ = run("gen_kit", idempotent=True, argv=remote(f"test -f {q(K)}/config.mk || test -f {q(K)}/freeze.json"))
        if rc:
            return fail("gen", txt + "\nGEN_NO_KIT: gen.py exit 0 but wrote no kit for this type (hard type? see gen --hard-wrappers)")
    pfo = f"preflight.{int(time.time())}.json"            # kit_preflight --out receipts are write-once
    pdir = os.path.dirname(plan)
    pstage = ""
    if os.path.basename(plan) != "die_plan.json":
        # AUTOBUILD-PIPE-2 10-30: kit_contract reads <plan-dir>/die_plan.json; a plan of record named otherwise
        # (KV plan_of_record/plan_c.json) gave 'no plan contents (pass --plan-dir)'.  Stage a plan dir of links: every
        # entry of the plan's own dir (relative pins_file etc. still resolve) + die_plan.json -> the plan file itself
        pdir = f"{W}/plandir"
        pstage = (f"rm -rf {q(pdir)} && mkdir -p {q(pdir)} && for f in {q(os.path.dirname(plan))}/*; do "
                  f"ln -s \"$f\" {q(pdir)}/; done; ln -sfn {q(plan)} {q(pdir)}/die_plan.json && ")
    # AUTOBUILD-PIPE-4 10-31 OWNER 12.27 (d): generation-time lint, before preflight / synth / place (BUILD check, not
    # sign-off): pins vs plan, clock export form, macro tcl, yosys undriven / multi-driven, memory bits vs limit.
    # A wave source older than the lint skips it with a note (the class rule applies from the merge on).
    gl = (f"{pstage}cd {q(src)} && if [ -f tools/die_plan/kit_gen_lint.py ]; then python3 tools/die_plan/kit_gen_lint.py "
          f"{q(K)} --plan-dir {q(pdir)} --mem {int(sp.get('lint_mem_gb') or 8)}; else echo 'KW_NOTE no kit_gen_lint.py in this source'; fi")
    rc, txt = run("gen_lint", otrun(int(sp.get("lint_mem_gb") or 8) + 2, 2, W, gl, gh))
    if rc:
        return fail("gen_lint", txt, f"{G}:{K}/gen_lint.json")
    pstage = ""                                           # the plan dir of links is staged once (above)
    pf = (f"{pstage}cd {q(src)} && python3 tools/die_plan/kit_preflight.py {q(K)} --plan-dir {q(pdir)} "
          f"{' '.join(q(x) for x in sp['preflight_args'])} --out {q(W)}/{pfo}")
    rc, txt = run("preflight", otrun(8, 2, W, pf, gh))
    if rc:
        return fail("preflight", "KIT_PREFLIGHT FAIL\n" + txt, f"{G}:{W}/{pfo}")
    # the kit (a few MB) goes to the same path on every allowed host; ot-run then picks the least-loaded one.
    # Fleet hosts do not resolve each other by name (intel1 -> intel2/epyc2 fails), so the hub (where this unit
    # runs) relays: gen host -> hub -> other hosts, and the placed kit comes back the same way.
    SSHE = "-e 'ssh -o BatchMode=yes -o ControlPath=none'"
    on_hub = G in ("localhost", hub)
    if not on_hub:
        rc, txt = run("sync_hub", idempotent=True, argv=["bash", "-c", f"mkdir -p {q(W)}/gen && rsync -a --delete {SSHE} {G}:{q(W)}/gen/ {q(W)}/gen/"])
        if rc:
            return fail("sync_hub", txt)
    for h in [h for h in sp["hosts"] if h not in (G, hub, "localhost")]:
        cp = (f"ssh -o BatchMode=yes -o ControlPath=none {h} mkdir -p {q(W)}/gen && "
              f"rsync -a --delete {SSHE} {q(W)}/gen/ {h}:{q(W)}/gen/")
        rc, txt = run(f"sync_{h}", ["bash", "-c", cp], idempotent=True)
        if rc:
            return fail(f"sync_{h}", txt)
    m, t = sp["place_mem_gb"], sp["place_threads"]
    phosts = sp["hosts"]
    pref = [h for h in sp.get("place_prefer") or [] if h in phosts]
    if pref:                                             # COORD 10-30 01:2x: PLACE on epyc2 first while it has headroom
        p = subprocess.run([sp["ot_run"], "--status"], capture_output=True, text=True, timeout=120)
        stt = parse_otrun_status(p.stdout if p.returncode == 0 else "")
        ok = [h for h in pref if (stt.get("localhost" if h == hub else h) or {}).get("admit", 0) >= m]
        if ok:
            phosts = ok
    prun = (runner.format(kit=K, work=W) if core else f"{W}/gen/run_kit.sh")
    rc, txt = run("place", otrun(m, t, K, f"bash {q(prun)} {q(K)} place {m} {t}", phosts))
    ran = re.findall(r"(?m)^ot-run: RAN on ([^\s:]+)(?: \(unit [^)\n]+\))?:", txt)
    res["ran_on"] = h = (hub if ran and ran[-1] == "localhost" else ran[-1]) if ran else ""
    if h and h != G and not (on_hub and h == hub):
        rp = rq = 0
        if h != hub:
            rp, _ = run("pull", ["bash", "-c", f"rsync -a {SSHE} {h}:{q(W)}/gen/ {q(W)}/gen/"], idempotent=True)
        if not on_hub:
            rq, _ = run("push_gen", ["bash", "-c", f"rsync -a {SSHE} {q(W)}/gen/ {G}:{q(W)}/gen/"], idempotent=True)
        if rp == 0 and rq == 0:
            # the placed kit now lives on the gen host (the only path records/evidence/enqueue name): drop the
            # PLACE-host and hub relay copies (~2.5 GB per station kit) so scratch floors are not eaten by duplicates
            for x in sorted({h, hub} - {G}):
                run(f"clean_{x}", (["bash", "-c", f"rm -rf {q(W)}/gen"] if x == hub else
                                   ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", x, f"rm -rf {q(W)}/gen"]))
    probe = (f"ls {q(K)}/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1; "
             f"cat {q(K)}/FAIL_* 2>/dev/null | head -5; "
             f"grep -h -i -E 'Number of cells|Chip area' {q(K)}/run/reports/asap7/*/base/synth_stat.txt 2>/dev/null | head -2; "
             f"ls -t {q(K)}/run/logs/asap7/*/base/*.log 2>/dev/null | head -1 | xargs -r tail -30")
    _, ptxt = run("place_probe", remote(probe), idempotent=True)
    odb = next((ln for ln in ptxt.splitlines() if ln.endswith("3_place.odb")), "")
    cells = re.search(r"Number of cells:?\s+(\d+)", ptxt)
    res["cells"] = int(cells.group(1)) if cells else None
    if rc or not odb:
        return fail("place", txt[-2000:] + "\n" + ptxt, f"{G}:{K}")
    if res["cells"] and res["cells"] > CELL_CAP:
        return fail("cells", f"{res['cells']} cells", f"{G}:{K}")
    olc = (f"python3 -c \"import json;o=json.load(open('{K}/budget.json'))['outline_um'];print(f'{{o[0]}}x{{o[1]}}')\"")
    _, ol = run("outline", remote(olc), idempotent=True)
    ol = ol.strip().splitlines()[-1] if ol.strip() else ""
    chk = {"id": f"kw-{T}".replace("_", "-")[:60], "odb": odb, "image": "openroad/orfs:asap7lock", "mem_gb": sp["geom_mem_gb"],
           "grt": True, "rules_args": ["--all-kits"] + (["--outline", ol] if re.fullmatch(r"[\d.]+x[\d.]+", ol) else [])
           + ["--title", f"{T} KIT-WAVE {sp['event']} 3_place"]}
    gd = f"{W}/geom"
    rc, txt = run("geom_cfg", idempotent=True, argv=remote(f"mkdir -p {q(gd)} && cat > {q(gd)}/check.json <<'EOF'\n{json.dumps(chk)}\nEOF"))
    if rc:
        return fail("geom_cfg", txt)
    rc, txt = run("geom", otrun(sp["geom_mem_gb"], 4, W, f"bash {q(src)}/tools/autopilot/geom_check.sh {q(gd)}", gh))
    line = geom_result_line(txt)
    res.update(geom_dir=f"{G}:{gd}", geom_line=line[:600], odb=odb, kit=f"{G}:{K}")
    if not line or line.startswith("AP_AUTO_GEOM_ERROR") or not re.search(r"AUTO-GEOM (PASS|FAIL)\b", line):
        # geom_check.sh exits 1 on a FAIL verdict: only a missing verdict line is a run error
        return fail("geom_run", txt[-3000:], f"{G}:{gd}")
    v, failing, tag = geom_verdict(line, sp.get("geom_waivers"))
    if v not in ("PASS", "PASS-COND"):
        return fail("geom", line, f"{G}:{gd}/auto_geom.json")
    res.update(stage="geom", verdict="PASS", geom=v, geom_tag=tag, evidence=f"{G}:{gd}/auto_geom.json")
    (out / "result.json").write_text(json.dumps(res, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------ tick stage
def _descends(AP):
    def f(sha, base):
        rc, _, _ = AP.sh(["git", "-C", str(AP.REPO), "merge-base", "--is-ancestor", base, sha], timeout=60)
        return rc == 0
    return f


PROBE_PLAN = Path(BI.__file__).read_text().rsplit("\nif __name__", 1)[0] + r'''
import hashlib, json, os, sys
a = json.loads(sys.argv[1]); out = {}
H = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
try:
    st = os.stat(a["plan"]); raw = open(a["plan"], "rb").read(); p = json.loads(raw)
    pt = p.get("partition_types") or {}; bud = p.get("budgets") if isinstance(p.get("budgets"), dict) else {}
    mode = a.get("block_identity", "raw")
    ids = identities(p, a["plan"], mode)
    blocks = {name: value["block_sha"] for name, value in ids.items()}
    baseline = None
    if mode != "raw" and a.get("identity_baseline_plan"):
        baseline_path = a["identity_baseline_plan"]
        baseline = identities(json.loads(Path(baseline_path).read_text()), baseline_path, mode)
    flags, deps = {}, {}
    for t, v in pt.items():
        if not isinstance(v, dict):
            continue
        ck = v.get("clock") or {}
        taps = [tp for tp in ck.get("taps") or [] if isinstance(tp, dict) and tp.get("kind") == "core"]
        signed = bool(taps and v.get("hard_cores") and all("insertion_ff_ps" in tp and
                      str(tp.get("budget_owner", "")).startswith("SIGNED") for tp in taps))
        # gen_phys.type_macros + write_type_kit: a hard core / content with a lef but no lib fails gen at once
        noview = sorted({str(c.get("module") or c.get("inst")) for c in (v.get("hard_cores") or []) + (v.get("contents") or [])
                         if isinstance(c, dict) and c.get("lef") and not c.get("lib")})
        if v.get("hard"):
            flags[t] = "hard"
        elif noview:
            flags[t] = "noview"
            deps[t] = noview
        elif ck.get("core_taps") == "internal" and not signed:
            flags[t] = "contract"
    out = {"mtime": st.st_mtime, "plan_sha": hashlib.sha256(raw).hexdigest(), "types": sorted(pt), "flags": flags,
           "cores": sorted(set(blocks) - set(pt)), "blocks": blocks, "deps": deps}
    if a.get("core_views"):
        # AUTOBUILD-PIPE-2: pin tables per hard-core module (sha256[:12] of the plan pins_file = views_b2r2 view key)
        cv = {}
        for v in pt.values():
            for c in (v.get("hard_cores") or []) if isinstance(v, dict) else []:
                if isinstance(c, dict) and c.get("module") and c.get("pins_file"):
                    f = os.path.join(os.path.dirname(a["plan"]), c["pins_file"])
                    h = hashlib.sha256(open(f, "rb").read()).hexdigest()[:12] if os.path.isfile(f) else "missing"
                    cv.setdefault(c["module"], set()).add(h)
        out["core_views"] = {m: sorted(x) for m, x in cv.items()}
    if mode != "raw":
        out.update(block_identity=mode, identities=ids, baseline_identities=baseline)
except Exception as e:
    out = {"error": f"{type(e).__name__}: {e}"}
print("AP_JSON " + json.dumps(out))
'''


def plan_names(AP, st, d):
    """partition types + hard-core modules of the plan of record (probe on gen_host, cached by plan path + event)"""
    key = f"{d['gen_host']}:{d['plan']}|{d['event']}"
    c = (st.get("plans") or {}).get(key)
    mode = d.get("block_identity", "raw")
    if mode == "raw" and c and c.get("blocks") and time.time() - c.get("t", 0) < 6 * 3600:
        return c
    args = {"plan": d["plan"], "core_views": bool(d.get("core_kit"))}
    if mode != "raw":
        args.update(block_identity=mode, identity_baseline_plan=d.get("identity_baseline_plan"))
    p = AP.rpy(d["gen_host"], PROBE_PLAN, args, timeout=600)
    if p.get("error"):
        return {"error": p["error"]}
    p["t"] = time.time()
    if mode == "raw":
        st.setdefault("plans", {})[key] = p
    return p


def core_view_names(names, core_views):
    """a hard-core module with several plan pin tables is one wave item per table: '<module>__v<sha12>' (select()
    expands an OWNERS row named by the module into these classes); a module with one table keeps its name"""
    if not core_views or not isinstance(names, dict):
        return names
    out = dict(names)
    for m, shas in core_views.items():
        shas = [x for x in shas if re.fullmatch(r"[0-9a-f]{12}", x)]
        if len(shas) > 1 and m in out:
            blk = out.pop(m)
            out.update({f"{m}__v{x}": blk for x in shas})
    return out


def plan_dies(AP, cfg, st, owners, status, hub, probe=True, log=print):
    """-> list of (die, ok, why, picks, skip) and the launch list [(die, row)] respecting capacity"""
    out, launch, per_die = [], [], []
    for die in sorted(set(list(cfg.get("dies") or {}) + list(GATE_EVENTS) + list(COORD_ONLY))):
        stop = stop_reason(cfg, die, AP.AP_DIR if AP else None)
        ok, why = (False, stop) if stop else gate(cfg, die, _descends(AP) if AP else None)
        picks, skip = [], {}
        if ok:
            d = cfg["dies"][die]
            names = None
            if probe and AP:
                pn = plan_names(AP, st, d)
                if pn.get("error"):
                    ok, why = False, f"plan of record unreadable: {pn['error'][:200]}"
                else:
                    names = dict(pn.get("blocks") or {}) or (set(pn.get("types") or []) | set(pn.get("cores") or []))
                    d["_plan_sha"] = pn.get("plan_sha")
                    d["_plan_flags"] = pn.get("flags") or {}
                    d["_plan_deps"] = pn.get("deps") or {}
                    names = core_view_names(names, pn.get("core_views"))
                    d["_identity_holds"] = {}
                    if d.get("block_identity", "raw") != "raw":
                        names, d["_identity_holds"] = BI.reuse_blocks(
                            names, pn["identities"], pn.get("baseline_identities"),
                            st.get("items") or {}, die=die, event=d["event"],
                            receipts=d.get("identity_reuse_receipts"))
            if ok:
                picks, skip = select(owners, cfg, die, st, names)
                n = capacity(cfg, die, st, status, hub)      # per-die share; the global caps apply below
                if d.get("max_items_total"):           # canary: lifetime cap of wave items on this event
                    rel = set(d.get("retry") or [])
                    used = sum(1 for r in st["items"].values() if r.get("die") == die and r.get("event") == d["event"]
                               and f"{r.get('item')}@{r.get('attempt')}" not in rel)
                    n = max(0, min(n, int(d["max_items_total"]) - used))
                per_die.append([(die, r) for r in picks[:n]])
        out.append((die, ok, why, picks, skip))
    # AUTOBUILD-PIPE-2 10-30: round-robin the tick's launches across dies.  Alphabetical fill let S81 (72 queued) take
    # every per-tick slot so HEAD l46 never launched (KIT-WAVE-2 23:17).
    room = max(0, min(int(cfg.get("max_inflight", DEFAULTS["max_inflight"])) - inflight(st),
                      int(cfg.get("max_launch_per_tick", DEFAULTS["max_launch_per_tick"]))))
    i = 0
    while len(launch) < room and any(i < len(q) for q in per_die):
        launch += [q[i] for q in per_die if i < len(q)][:room - len(launch)]
        i += 1
    return out, launch


def launch(AP, cfg, st, die, r, hub, delay_s=0.0):
    key = item_key(die, cfg["dies"][die]["event"], r["item"], r.get("block_sha"))
    prev = st["items"].get(key) or {}
    attempt = int(prev.get("attempt", 0)) + 1
    jd = Path(AP.AP_DIR) / "kit_wave" / re.sub(r"[^A-Za-z0-9_.-]", "_", key) / f"a{attempt}"
    sp = spec_for(cfg, die, r["item"], hub, r.get("parent_item") or prev.get("parent_item"), kind=r.get("kind") or "type")
    sp["start_delay_s"] = round(float(delay_s), 1)
    if attempt > 1:
        # Preserve previous generation/geometry verdicts and run payloads.
        sp["work"] += f"/attempt_{attempt}"
    unit = f"kw-{re.sub(r'[^A-Za-z0-9]', '', die)[:6]}-{re.sub(r'[^A-Za-z0-9]', '', r['item'])[:28]}-{attempt}-{int(time.time()) % 100000}"
    if AP.DRY:
        AP.log(f"KIT-WAVE would launch {die}/{r['item']} unit {unit}: gen {sp['gen_host']}:{sp['work']} plan {sp['plan']}")
        return None
    jd.mkdir(parents=True, exist_ok=True)
    (jd / "spec.json").write_text(json.dumps(sp, indent=1))
    ok = AP.launch_unit(unit, jd / "unit.log", ["python3", str(Path(__file__).resolve()), "run-item", str(jd / "spec.json")])
    rec = {"die": die, "item": r["item"], "parent_item": r.get("parent_item") or prev.get("parent_item"), "kind": r["kind"], "event": sp["event"], "attempt": attempt,
           "block_sha": r.get("block_sha"), "plan_sha": cfg["dies"][die].get("_plan_sha"),
           "unit": unit, "dir": str(jd),
           "status": "RUNNING" if ok else "FAIL", "class": "" if ok else "INFRA", "replicas": r.get("replicas"),
           "reason": "" if ok else "systemd-run failed", "started": time.time(), "updated": time.time()}
    st["items"][key] = rec
    AP.log(f"KIT-WAVE LAUNCH {die}/{r['item']} ({r['kind']}, {r.get('replicas')} replicas) event {sp['event']} unit {unit}")
    return rec


def collect(AP, cfg, st, notices):
    for key, rec in st["items"].items():
        if rec.get("status") != "RUNNING" or AP.unit_active(rec["unit"]):
            if rec.get("status") == "RUNNING":
                try:
                    tail = (Path(rec["dir"]) / "unit.log").read_text().splitlines()
                    stg = [ln.split()[1] for ln in tail if ln.startswith("KW_STAGE ")]
                    rec["stage"] = stg[-1] if stg else "start"
                except OSError:
                    pass
            continue
        jd = Path(rec["dir"])
        try:
            res = json.loads((jd / "result.json").read_text())
        except (OSError, ValueError):
            ut = ""
            try:
                ut = (jd / "unit.log").read_text()
            except OSError:
                pass
            res = {"verdict": "FAIL", "stage": "unit", "tail": ut[-3000:] or "unit ended without result.json"}
        rec["updated"] = time.time()
        rec["stage"] = res.get("stage")
        rec["evidence"] = res.get("evidence", "")
        rec["kit"] = res.get("kit", "")
        if res.get("verdict") == "PASS":
            rec.update(status="PASS", geom=res.get("geom_line", ""), cells=res.get("cells"), geom_dir=res.get("geom_dir"),
                       geom_tag=res.get("geom_tag", ""), geom_verdict=res.get("geom") or "PASS")
            enqueue_pass(AP, cfg, st, rec, notices)
            continue
        cls, why = classify(res.get("stage", ""), (res.get("errors") or "") + "\n" + (res.get("tail") or ""))
        rec.update(status="FAIL", **{"class": cls}, reason=why)
        if cls == "INFRA" and rec["attempt"] < infra_attempts(cfg, rec["die"]):
            rec["status"] = "RETRY-INFRA"                # relaunched next tick (up to infra_attempts in all)
        notices.setdefault(rec["die"], []).append(f"{rec['item']} FAIL {cls} ({why[:160]}) evid {rec['evidence']}")
        AP.log(f"KIT-WAVE FAIL {rec['die']}/{rec['item']} {cls}: {why}")


def infra_attempts(cfg, die):
    """attempts an item may use on INFRA failures (never on a design verdict); AUTOBUILD-PIPE-1 10-30: was 2, but an
    sshd burst on the gen host can drop the same item twice in one wave"""
    try:
        return max(2, int(opt(cfg, die, "infra_attempts")))
    except (TypeError, ValueError):
        return DEFAULTS["infra_attempts"]


def infra_relaunch_due(cfg, rec):
    """an INFRA failure the wave relaunches: RETRY-INFRA, or a FAIL INFRA record left by the old 2-attempt limit"""
    if int(rec.get("attempt") or 0) >= infra_attempts(cfg, rec["die"]):
        return False
    if rec.get("status") == "RETRY-INFRA":
        return True
    return (rec.get("status") == "FAIL" and rec.get("class") == "INFRA"
            and ((cfg.get("dies") or {}).get(rec["die"]) or {}).get("event") == rec.get("event"))


def enqueue_pass(AP, cfg, st, rec, notices):
    d = cfg["dies"][rec["die"]]
    # The result belongs to its immutable launch spec, even if the config
    # changes while PLACE runs. Never relabel an old physical result.
    try:
        pinned = json.loads((Path(rec["dir"]) / "spec.json").read_text())
        src = pinned.get("queue_src") or ("main@" + pinned["src_sha"])
        if not pinned.get("queue_src") and not pinned.get("src_sha"):
            raise ValueError("launch spec has no source identity")
        retry = rec["item"] + "@" + str(rec["attempt"])
        if retry in (d.get("retry") or []) and pinned.get("src_sha") != d.get("src_sha"):
            raise ValueError("old source superseded by explicit FLOW retry")
    except (OSError, ValueError, KeyError) as e:
        rec.update(status="FAIL", **{"class": "FLOW"}, reason=f"enqueue source identity: {e}")
        notices.setdefault(rec["die"], []).append(f"{rec['item']} source HOLD: {e}; original result retained")
        return
    ref = (f"AUTO-GEOM KIT-WAVE {rec['event']} {rec['geom_dir']}/auto_geom.json"
           + (f" {rec['geom_tag']} (owner standing rule 10-30 00:5x: fill/empty only)" if rec.get("geom_tag") == "FILL-EXCEPTION"
              else f" {rec['geom_tag']}" if rec.get("geom_tag") else ""))
    cells = rec.get("cells") or 0
    argv = ["python3", str(Path(__file__).resolve().parent / "enqueue.py"), "--die", rec["die"], "--type", rec["item"],
            "--kit", rec["kit"], "--src", src, "--geom", rec.get("geom_verdict") or "PASS", "--geom-ref", ref,
            "--mem", str(opt(cfg, rec["die"], "place_mem_gb")), "--cells", str(int(cells * 1.3) if cells else 200000),
            "--lane", d.get("lane", LANE)]
    if AP.DRY:
        AP.log("KIT-WAVE would enqueue: " + " ".join(argv))
        return
    rc, out, err = AP.sh(argv, timeout=300)
    if rc:
        rec.update(status="FAIL", **{"class": "FLOW"}, reason=f"enqueue rc {rc}: {(err or out)[-200:]}")
        notices.setdefault(rec["die"], []).append(f"{rec['item']} AUTO-GEOM PASS but enqueue failed rc {rc}")
        return
    rec["status"] = "ENQUEUED"
    st["pass_n"] = int(st.get("pass_n", 0)) + 1
    msg = f"{rec['item']} AUTO-GEOM PASS{' ' + rec['geom_tag'] if rec.get('geom_tag') else ''} -> enqueued ({rec['kit']})"
    if st["pass_n"] % int(cfg.get("geom_sample", DEFAULTS["geom_sample"])) == 1 or int(cfg.get("geom_sample", 5)) == 1:
        AP.coord_append("lanes/GEOM-REVIEW.md",
                        f"- {now_s()} GEOM REQ [KIT-WAVE-1 sample {rec['die']}/{rec['item']}] 3_place {rec['kit']} "
                        f"(event {rec['event']}); AUTO-GEOM PASS {rec['geom_dir']}/auto_geom.{{json,png}}; 1-in-5 "
                        f"independent visual sample (owner rule); route already enqueued -- a FAIL verdict demotes it")
        msg += " + GEOM REQ sample"
    notices.setdefault(rec["die"], []).append(msg)
    AP.log(f"KIT-WAVE ENQUEUE {rec['die']}/{rec['item']} {rec['kit']} geom {rec.get('geom', '')[:120]}")


# ------------------------------------------------------------------------------------------------ past GEOM
# OWNER 12.23 (AUTOBUILD-PIPE-1): after AUTO-GEOM PASS the wave kit is in the autopilot queue, which runs the kit's own
# runner (CTS -> route), signoff_chain.py (sign-off TT setup / FF hold, DRC, antenna, PG, clock + post-route LEC),
# archives a SIGNED view and writes PROVENANCE.json (src commit + flow tag) that release_tree_plan credit_designs
# counts.  follow_queue() reads that job back so kit_wave_stages.tsv carries every wave kit to the count, with the
# class people act on: TIMING / ROUTING (lanes) or PLAN / FLOW / INFRA (die owner / automation).
ROUTING_FAILS = {"drc", "antenna", "grt", "route", "congestion"}
TIMING_FAILS = {"setup_tt", "hold_ff", "drv", "clock", "setup", "hold"}
FLOW_FAILS = {"pg", "sdc_lint", "unconstrained"}


def queue_class(j):
    """autopilot job -> (stage, status, class, reason).  class '' = not a failure (running / waiting / signed)"""
    stt = str(j.get("status") or "")
    if stt.startswith("REVIEW-"):
        stt = "DONE-" + stt[len("REVIEW-"):]
    kind = str(j.get("kind") or "")
    why = str(j.get("reasons") or j.get("hold_why") or "")[:300]
    so = j.get("signoff") if isinstance(j.get("signoff"), dict) else {}
    if stt == "ARCHIVED":
        return "count", "SIGNED", "", f"signed off, archived {j.get('archive', '')} flow {j.get('flow_tag', '')}"
    if stt == "SIGNED":
        return "archive", "RUNNING", "", "signed off; archive + PROVENANCE pending"
    if stt == "SIGNED-UNVERSIONED":
        return "provenance", "FAIL", "FLOW", "signed off but no flow release tag carries its flow: " + str(j.get("prov_error") or "")[:200]
    if stt in ("RUNNING", "") or stt.startswith("WAIT-") or stt in ("ORPHAN", "TRIAL-SIGNED", "WITHDRAWN", "CANCELLED"):
        return ("route" if stt == "RUNNING" else "queue"), (stt or "QUEUED"), "", str((j.get("history") or [[0, 0, ""]])[-1][-1])[:200]
    if stt == "REJECTED":
        return "queue", "FAIL", "FLOW", "queue row rejected: " + str(j.get("error") or why)[:200]
    if stt == "DONE-CRASH":
        return "route", "FAIL", ("INFRA" if kind.startswith("infra") else "FLOW"), f"{kind}: {why}"
    if stt.startswith("DONE-"):
        fails = set(so.get("fails") or [])
        tt, ff = so.get("tt_wns"), so.get("ff_wns")
        drc = so.get("drc") or 0
        stage = "signoff" if so else "route"
        if kind == "pg-unbound" or (fails & FLOW_FAILS):
            return stage, "FAIL", "FLOW", f"{kind}: {why}"
        if kind in ("preflight", "cell-cap", "diagnostic-overrun"):
            return stage, "FAIL", ("FLOW" if kind == "diagnostic-overrun" else "PLAN"), f"{kind}: {why}"
        if kind == "grt-overflow" or (fails & ROUTING_FAILS) or drc:
            return stage, "FAIL", "ROUTING", f"{kind}: drc {drc} {why}".strip()
        if kind in ("post-cts-hold", "hold-structural") or (fails & TIMING_FAILS) or any(
                w is not None and w < 0 for w in (tt, ff)):
            return stage, "FAIL", "TIMING", f"{kind}: TT {tt} FF {ff} ps {why}".strip()
        if kind == "gate":
            return stage, "FAIL", ("TIMING" if re.search(r"hold|setup|slack|wns", why, re.I) else "PLAN"), f"{kind}: {why}"
        if "face_guard" in fails:
            return stage, "FAIL", "PLAN", f"{kind}: {why}"
        return stage, "FAIL", "FLOW", f"{kind or stt}: {why}"
    return "queue", stt, "", why


def follow_queue(st, ap_dir, notices):
    """join ENQUEUED wave items with their autopilot queue job (same kit path); a new terminal queue state is reported
    once to the die owner's grouped notice"""
    try:
        jobs = json.loads((Path(ap_dir) / "state.json").read_text()).get("jobs") or {}
    except (OSError, ValueError):
        return 0
    by_kit = {}
    for j in jobs.values():
        k = j.get("kit")
        if k and (k not in by_kit or float(j.get("updated") or 0) >= float(by_kit[k].get("updated") or 0)):
            by_kit[k] = j
    n = 0
    for rec in (st.get("items") or {}).values():
        if rec.get("status") not in ("ENQUEUED",) or not rec.get("kit"):
            continue
        j = by_kit.get(rec["kit"])
        if not j:
            rec.update(q_stage="queue", q_status="QUEUED", q_class="", q_reason="queue row not yet read by the autopilot")
            continue
        stage, status, cls, why = queue_class(j)
        old = (rec.get("q_status"), rec.get("q_class"))
        rec.update(q_id=j.get("id"), q_stage=stage, q_status=status, q_class=cls, q_reason=why)
        n += 1
        if (status, cls) != old and (status in ("SIGNED", "FAIL")):
            msg = (f"{rec['item']} SIGNED OFF -> count ({why[:120]})" if status == "SIGNED" else
                   f"{rec['item']} {stage} FAIL {cls} ({why[:160]}) job {j.get('id')}")
            notices.setdefault(rec["die"], []).append(msg)
    return n


def step(AP, ap_dir=None):
    """one wave pass; a non-blocking lock keeps two passes (tick + CLI step) from double-launching"""
    import fcntl
    ap_dir = ap_dir or AP.AP_DIR
    lk = open(Path(ap_dir) / "kit_wave.lock", "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        AP.log("KIT-WAVE step skipped: another wave pass holds kit_wave.lock")
        lk.close()
        return None
    try:
        return _step(AP, ap_dir)
    finally:
        lk.close()


def _step(AP, ap_dir):
    cfg = load_config(AP.read_coord("autopilot/kit_wave.json"))
    st = load_state(ap_dir)
    st.setdefault("items", {})
    notices = {}
    collect(AP, cfg, st, notices)
    follow_queue(st, ap_dir, notices)
    stagger = float(cfg.get("launch_stagger_s", DEFAULTS["launch_stagger_s"]))
    nl = 0                                               # items launched this tick: start delay nl * stagger
    for key, rec in list(st["items"].items()):           # INFRA relaunch (up to infra_attempts)
        # Semantic adoption requires a fresh profile proof. Never launch an
        # old pending retry before plan_dies has had a chance to hold it.
        identity_mode = (cfg.get("dies", {}).get(rec["die"]) or {}).get("block_identity", "raw")
        if infra_relaunch_due(cfg, rec) and identity_mode == "raw" and not stop_reason(cfg, rec["die"], ap_dir):
            rec["status"] = "FAIL"
            launch(AP, cfg, st, rec["die"], {"item": rec["item"], "kind": rec.get("kind", "type"),
                                              "parent_item": rec.get("parent_item"), "block_sha": rec.get("block_sha"),
                                              "replicas": rec.get("replicas")}, AP.HUB_NAME, delay_s=nl * stagger)
            nl += 1
    owners = parse_owners((Path(ap_dir) / "OWNERS.tsv").read_text() if (Path(ap_dir) / "OWNERS.tsv").exists() else "")
    rc, out, _ = AP.sh([OT_RUN, "--status"], timeout=120)
    status = parse_otrun_status(out if rc == 0 else "")
    _, todo = plan_dies(AP, cfg, st, owners, status, AP.HUB_NAME)
    for die, r in todo:
        rec = launch(AP, cfg, st, die, r, AP.HUB_NAME, delay_s=nl * stagger)
        nl += 1
        if rec:
            notices.setdefault(die, []).append(f"{r['item']} LAUNCHED ({rec['unit']})")
    for die, msgs in notices.items():
        lane = (cfg["dies"].get(die) or {}).get("owner_lane", f"{die} owner")
        AP.coord_append("lanes/COORD-REVIEW-QUEUE.md",
                        f"- {now_s()} KIT-WAVE [{die}] -> {lane}: {len(msgs)} event(s): " + "; ".join(msgs)[:1800])
    protect_sources(AP, cfg, st, ap_dir)
    if not AP.DRY:
        save_state(st, ap_dir)
        write_stages(st, ap_dir)
    return st


PROTECT_REL = ".local/state/wt-reaper/protect.d/kit_wave.txt"


def source_paths(cfg, st, ap_dir):
    """sorted absolute src / plan / queue_src paths the wave reads: every die config + every RUN item's pinned spec"""
    out = set()
    for d in (cfg.get("dies") or {}).values():
        for k in ("src", "plan", "queue_src"):
            if isinstance(d, dict) and isinstance(d.get(k), str) and d[k].startswith("/"):
                out.add(d[k])
    for rec in (st.get("items") or {}).values():
        if rec.get("status") != "RUN" or not rec.get("dir"):
            continue
        try:
            sp = json.loads((Path(rec["dir"]) / "spec.json").read_text())
        except (OSError, ValueError):
            continue
        for k in ("src", "plan", "queue_src"):
            if isinstance(sp.get(k), str) and sp[k].startswith("/"):
                out.add(sp[k])
    return sorted(out)


def protect_sources(AP, cfg, st, ap_dir):
    """AUTOBUILD-PIPE-2 (COORD 00:1x): the intel1 wt-reaper removed the wave's S81 / HEAD source worktrees.  Publish the
    wave's source paths to <host>:~/<PROTECT_REL> on every wave host (tools/fleet/wt-reaper.py keeps any worktree
    holding a listed path); rewritten only when the list changes or a write failed."""
    paths = source_paths(cfg, st, ap_dir)
    body = "# kit_wave.py protect_sources: worktrees holding these paths are kit-wave sources (wt-reaper keeps them)\n" + \
        "".join(p + "\n" for p in paths)
    hosts = set(cfg.get("hosts") or DEFAULTS["hosts"])
    for d in (cfg.get("dies") or {}).values():
        if isinstance(d, dict):
            hosts |= set(d.get("hosts") or []) | ({d["gen_host"]} if d.get("gen_host") else set())
    done = st.setdefault("protect_written", {})
    for h in sorted(hosts):
        if done.get(h) == body:
            continue
        cmd = _ssh(h, AP.HUB_NAME) + ["bash", "-c", f"'mkdir -p ~/{os.path.dirname(PROTECT_REL)} && "
                                                  f"cat > ~/{PROTECT_REL}.tmp && mv ~/{PROTECT_REL}.tmp ~/{PROTECT_REL}'"]
        if not _ssh(h, AP.HUB_NAME):
            cmd = ["bash", "-c", cmd[-1].strip("'")]
        if AP.DRY:
            continue
        rc, _, err = AP.sh(cmd, timeout=60, input=body)
        if rc == 0:
            done[h] = body
        else:
            AP.log(f"KIT-WAVE protect_sources {h}: write failed rc {rc}: {(err or '').strip()[:160]}")


STAGES_FILE = "kit_wave_stages.tsv"
STAGE_COLS = ("die", "item", "parent_item", "plan_sha", "block_sha", "event", "stage", "status", "class", "kit",
              "evidence", "updated", "reason")


def write_stages(st, ap_dir):
    """OWNER 12.20: one row per wave kit (keyed on plan block sha) for SIGNOFF-SPRINT-1's lanes/SIGNOFF-STAGES.tsv;
    ENQUEUED rows continue in the autopilot queue (route / sign-off / post-route LEC), joined on the kit path"""
    rows = ["\t".join(STAGE_COLS)]
    for r in sorted((st.get("items") or {}).values(), key=lambda r: (r.get("die", ""), r.get("item", ""))):
        v = dict(r, plan_sha=(r.get("plan_sha") or "")[:12], block_sha=(r.get("block_sha") or "")[:12],
                 stage="queue:route" if r.get("status") == "ENQUEUED" else (r.get("stage") or ""),
                 updated=time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("updated") or 0)),
                 reason=(r.get("reason") or "")[:240])
        if r.get("status") == "ENQUEUED" and r.get("q_stage"):
            # past GEOM: the autopilot queue job of this kit (follow_queue); evidence = its job id
            v.update(stage=r["q_stage"], status=r.get("q_status") or "", **{"class": r.get("q_class") or ""},
                     reason=(r.get("q_reason") or "")[:240],
                     evidence=f"autopilot job {r.get('q_id', '')} | {r.get('evidence') or ''}")
        rows.append("\t".join(re.sub(r"\s+", " ", str(v.get(c) or "")) for c in STAGE_COLS))
    tmp = Path(ap_dir) / (STAGES_FILE + ".tmp")
    tmp.write_text("\n".join(rows) + "\n")
    tmp.replace(Path(ap_dir) / STAGES_FILE)


# ------------------------------------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--config")
    p.add_argument("--owners")
    p.add_argument("--probe", action="store_true", help="read the plan of record on gen_host (ssh) to filter items")
    sub.add_parser("status")
    s_ = sub.add_parser("step", help="one wave pass outside the autopilot tick (canary; AP_DIR names its state dir)")
    s_.add_argument("--config", help="kit_wave.json file instead of coord/state autopilot/kit_wave.json")
    s_.add_argument("--owners", help="OWNERS.tsv to select from (default AP_DIR/OWNERS.tsv)")
    s_.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("run-item")
    r.add_argument("spec")
    a = ap.parse_args(argv)
    if a.cmd == "run-item":
        try:
            return run_item(a.spec)
        except Exception as e:                          # a crash of the pipeline itself is FLOW, recorded
            out = Path(a.spec).parent / "result.json"
            out.write_text(json.dumps({"verdict": "FAIL", "stage": "pipeline", "tail": f"Traceback (most recent call "
                                       f"last) {type(e).__name__}: {e}"}))
            raise
    if a.cmd == "status":
        st = load_state()
        for k, rec in sorted(st.get("items", {}).items()):
            print(f"{rec.get('status', ''):<12} {rec.get('class', ''):<6} {k:<60} {rec.get('stage', '')} {rec.get('unit', '')} "
                  f"{(rec.get('reason') or rec.get('evidence') or '')[:120]}")
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import autopilot as AP
    if a.cmd == "step":
        AP.DRY = a.dry_run
        if a.config:
            real = AP.read_coord
            text = Path(a.config).read_text()
            AP.read_coord = lambda rel: text if rel == "autopilot/kit_wave.json" else real(rel)
        if a.owners:
            Path(AP.AP_DIR).mkdir(parents=True, exist_ok=True)
            if Path(a.owners).resolve() != (Path(AP.AP_DIR) / "OWNERS.tsv").resolve():
                (Path(AP.AP_DIR) / "OWNERS.tsv").write_text(Path(a.owners).read_text())
        st = step(AP)
        print(f"{now_s()} kit-wave step: " + ", ".join(f"{k} {v}" for k, v in sorted(
            __import__("collections").Counter(r.get("status") for r in st["items"].values()).items())))
        return 0
    AP.DRY = True
    cfg = load_config(Path(a.config).read_text() if a.config else AP.read_coord("autopilot/kit_wave.json"))
    owners = parse_owners(Path(a.owners or AP_DIR / "OWNERS.tsv").read_text())
    rc, out, _ = AP.sh([OT_RUN, "--status"], timeout=120)
    status = parse_otrun_status(out if rc == 0 else "")
    st = load_state()
    st.setdefault("items", {})
    res, todo = plan_dies(AP, cfg, st, owners, status, AP.HUB_NAME, probe=a.probe)
    print(f"# KIT-WAVE plan {now_s()} (dry run; nothing launched) hosts: " +
          ", ".join(f"{h} admits {v['admit']} GB run {v['run']}" for h, v in status.items()))
    for die, ok, why, picks, skip in res:
        print(f"{die}: {'ON' if ok else 'OFF'} -- {why}")
        if ok:
            print(f"  eligible {len(picks)}: " + " ".join(f"{p['item']}({p['kind']},x{p['replicas']})" for p in picks[:40]))
            for w, its in sorted(skip.items(), key=lambda kv: -len(kv[1])):
                print(f"  skip {len(its)} [{w}]: " + " ".join(its[:12]) + (" ..." if len(its) > 12 else ""))
    print(f"would launch now ({len(todo)}): " + " ".join(f"{d}/{r['item']}" for d, r in todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
