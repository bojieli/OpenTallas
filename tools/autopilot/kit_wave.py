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

    kit_wave.py plan [--config F] [--owners F] [--probe]   dry run: per die gate, picks, skips (prints, launches nothing)
    kit_wave.py status                                      wave state table
    kit_wave.py run-item SPEC.json                          one item pipeline (run by the tick inside a unit)
"""
import argparse
import json
import os
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
               # 21:03 HEAD plan of record (hd_st_str one-block on l45, ROOT-MERGE-AG ab0bf8384)
               "s81_head": {"exact": ("src25p", "src25q2", "src25q3", "l44", "l45", "l46")}}
COORD_ONLY = ("qwen_compute", "hbm")          # OFF until COORD enables them (coord_enable = ruling reference)
GATE_KEYS = ("g0c", "bind", "clock")          # plan event checks that must be PASS (12.4a / 12.17 freeze inputs)
DEFAULTS = {"max_inflight": 40, "max_launch_per_tick": 6, "die_max_inflight": 6, "take_states": ["NEEDS-KIT"],
            "kinds": ["type"], "live_claim_h": 3.0, "place_mem_gb": 48, "place_threads": 8, "geom_mem_gb": 24,
            "gen_mem_gb": 16, "bind_mem_gb": 24, "geom_sample": 5, "place_prefer": [], "hosts": ["intel1", "intel2", "epyc2"],
            "work_root": "/srv/opentallas-scratch2/claude/kit-wave"}
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
    if bad:
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
    return picked, skip


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


# ------------------------------------------------------------------------------------------------ classification
# (class, stage regex or None, text regex, reason).  First match wins; stage-specific rules first.
RULES = [
    ("INFRA", None, r"ot-run: NOT RUN|ot-run: NOT COMPLETED|exit 137\b|Out of memory|oom-kill|OOMKilled|"
                    r"No space left on device|ssh: connect to host|Connection (?:reset|refused|closed)|"
                    r"rsync error|Cannot connect to the Docker daemon|Host key verification failed", "infra"),
    ("RTL", None, r"LEC NOT EQUIVALENT|NOT EQUIVALENT|NON-?EQUIV", "LEC not equivalent"),
    ("INFRA", None, r"^Terminated\b|\nTerminated\b|Killed\s*$", "process terminated (not a design result)"),
    ("PLAN", None, r"ContractError|requires explicit SIGNED", "plan contract metadata missing for this type"),
    ("RTL", None, r"RTL_LINT FAIL|multi(?:ple)?[- ]driv|\bundriven (?:net|wire|signal|port|input|bit)|"
                  r"\"undriven\": [1-9]|syntax error|Unexpected token|"
                  r"is not part of the design|Re-definition of module", "RTL elaboration / lint"),
    ("PLAN", None, r"FACE_GUARD FAIL|face_guard[^\n]*FAIL", "face guard (plan pins / landing)"),
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
    ("FLOW", None, r"SYNTH_MEMORY_MAX_BITS|KIT_PREFLIGHT FAIL|preflight[^\n]*FAIL", "kit recipe / preflight"),
    ("FLOW", None, r"Traceback \(most recent call last\)|KeyError|TypeError|AttributeError|invalid command name|"
                   r"can't read \"|Error: .*\.tcl, \d+", "tool / Tcl error"),
]


def classify(stage, text):
    """-> (class, reason); never guesses INFRA for a design failure"""
    for cls, st_re, tx_re, why in RULES:
        if st_re and not re.search(st_re, stage or ""):
            continue
        m = re.search(tx_re, text or "")
        if m:
            snip = (text or "")[max(0, m.start() - 60):m.end() + 100].replace("\n", " ").strip()
            return cls, f"{why} @{stage}: {snip[:220]}"
    return "FLOW", f"unclassified failure @{stage} (see log)"


# ------------------------------------------------------------------------------------------------ AUTO-GEOM verdict
FILL_ONLY = {"fill", "empty"}


def geom_verdict(line):
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
    return "FAIL", failing, ""


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
            o["next_step"] = f"KIT-WAVE AUTO-GEOM PASS -> enqueued (autopilot route/sign-off) {r.get('kit', '')}"
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
def spec_for(cfg, die, item, hub):
    d = cfg["dies"][die]
    root = f"{opt(cfg, die, 'work_root')}/{die}/{d['event']}"
    return {"die": die, "item": item, "event": d["event"], "plan": d["plan"], "gen_host": d["gen_host"],
            "src": d["src"], "src_sha": d.get("src_sha", ""), "queue_src": d.get("queue_src", ""), "root": root, "work": f"{root}/items/{item}",
            "kit_rtl": d.get("kit_rtl") or {},
            "gen_args": list(d.get("gen_args") or []) + list((d.get("type_args") or {}).get(item) or [])
                        + (["--hard-wrappers", item] if item in (d.get("hard_wrappers") or []) else []),
            # default --contract; an explicit [] (die config) = the plain kit preflight the autopilot submit runs
            "preflight_args": list(["--contract"] if d.get("preflight_args") is None else d["preflight_args"]),
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

    def run(stage, argv, timeout=None):
        res["stage"] = stage
        print(f"KW_STAGE {stage} {now_s()} :: {' '.join(shlex.quote(a) for a in argv)[:600]}", flush=True)
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        txt = (p.stdout or "") + (p.stderr or "")
        (out / f"{stage}.log").write_text(txt)
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
        res.update(stage=stage, verdict="FAIL", tail=txt[-3000:], evidence=evidence or f"{G}:{W}")
        (out / "result.json").write_text(json.dumps(res, indent=1))
        return 1

    q = shlex.quote
    src, plan = sp["src"], sp["plan"]
    gh = [G]
    rc, txt = run("mkdir", remote(f"mkdir -p {q(W)}/logs {q(sp['root'])} && rm -rf {q(W)}/gen {q(W)}/rtl {q(W)}/geom"))
    if rc:
        return fail("mkdir", txt)
    kr = sp["kit_rtl"]
    kit_rtl_arg = ""
    if kr.get("mode") == "bind":
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
    gen = (f"cd {q(src)} && python3 tools/die_plan/gen.py phys {q(plan)} --out {q(W)}/gen --types {q(T)} "
           f"--rtl-root {q(src)} {kit_rtl_arg} {' '.join(q(x) for x in sp['gen_args'])}")
    rc, txt = run("gen", otrun(sp["gen_mem_gb"], 2, W, gen, gh))
    if rc:
        return fail("gen", txt)
    rc, _ = run("gen_kit", remote(f"test -f {q(K)}/config.mk || test -f {q(K)}/freeze.json"))
    if rc:
        return fail("gen", txt + "\nGEN_NO_KIT: gen.py exit 0 but wrote no kit for this type (hard type? see gen --hard-wrappers)")
    pfo = f"preflight.{int(time.time())}.json"            # kit_preflight --out receipts are write-once
    pf = (f"cd {q(src)} && python3 tools/die_plan/kit_preflight.py {q(K)} --plan-dir {q(os.path.dirname(plan))} "
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
        rc, txt = run("sync_hub", ["bash", "-c", f"mkdir -p {q(W)}/gen && rsync -a --delete {SSHE} {G}:{q(W)}/gen/ {q(W)}/gen/"])
        if rc:
            return fail("sync_hub", txt)
    for h in [h for h in sp["hosts"] if h not in (G, hub, "localhost")]:
        cp = (f"ssh -o BatchMode=yes -o ControlPath=none {h} mkdir -p {q(W)}/gen && "
              f"rsync -a --delete {SSHE} {q(W)}/gen/ {h}:{q(W)}/gen/")
        rc, txt = run(f"sync_{h}", ["bash", "-c", cp])
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
    rc, txt = run("place", otrun(m, t, K, f"bash {q(W)}/gen/run_kit.sh {q(K)} place {m} {t}", phosts))
    ran = re.findall(r"(?m)^ot-run: RAN on ([^\s:]+)(?: \(unit [^)\n]+\))?:", txt)
    res["ran_on"] = h = (hub if ran and ran[-1] == "localhost" else ran[-1]) if ran else ""
    if h and h != G and not (on_hub and h == hub):
        if h != hub:
            run("pull", ["bash", "-c", f"rsync -a {SSHE} {h}:{q(W)}/gen/ {q(W)}/gen/"])
        if not on_hub:
            run("push_gen", ["bash", "-c", f"rsync -a {SSHE} {q(W)}/gen/ {G}:{q(W)}/gen/"])
    probe = (f"ls {q(K)}/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1; "
             f"cat {q(K)}/FAIL_* 2>/dev/null | head -5; "
             f"grep -h -i -E 'Number of cells|Chip area' {q(K)}/run/reports/asap7/*/base/synth_stat.txt 2>/dev/null | head -2; "
             f"ls -t {q(K)}/run/logs/asap7/*/base/*.log 2>/dev/null | head -1 | xargs -r tail -30")
    _, ptxt = run("place_probe", remote(probe))
    odb = next((ln for ln in ptxt.splitlines() if ln.endswith("3_place.odb")), "")
    cells = re.search(r"Number of cells:?\s+(\d+)", ptxt)
    res["cells"] = int(cells.group(1)) if cells else None
    if rc or not odb:
        return fail("place", txt[-2000:] + "\n" + ptxt, f"{G}:{K}")
    if res["cells"] and res["cells"] > CELL_CAP:
        return fail("cells", f"{res['cells']} cells", f"{G}:{K}")
    olc = (f"python3 -c \"import json;o=json.load(open('{K}/budget.json'))['outline_um'];print(f'{{o[0]}}x{{o[1]}}')\"")
    _, ol = run("outline", remote(olc))
    ol = ol.strip().splitlines()[-1] if ol.strip() else ""
    chk = {"id": f"kw-{T}".replace("_", "-")[:60], "odb": odb, "image": "openroad/orfs:asap7lock", "mem_gb": sp["geom_mem_gb"],
           "grt": True, "rules_args": ["--all-kits"] + (["--outline", ol] if re.fullmatch(r"[\d.]+x[\d.]+", ol) else [])
           + ["--title", f"{T} KIT-WAVE {sp['event']} 3_place"]}
    gd = f"{W}/geom"
    rc, txt = run("geom_cfg", remote(f"mkdir -p {q(gd)} && cat > {q(gd)}/check.json <<'EOF'\n{json.dumps(chk)}\nEOF"))
    if rc:
        return fail("geom_cfg", txt)
    rc, txt = run("geom", otrun(sp["geom_mem_gb"], 4, W, f"bash {q(src)}/tools/autopilot/geom_check.sh {q(gd)}", gh))
    line = geom_result_line(txt)
    res.update(geom_dir=f"{G}:{gd}", geom_line=line[:600], odb=odb, kit=f"{G}:{K}")
    if not line or line.startswith("AP_AUTO_GEOM_ERROR") or not re.search(r"AUTO-GEOM (PASS|FAIL)\b", line):
        # geom_check.sh exits 1 on a FAIL verdict: only a missing verdict line is a run error
        return fail("geom_run", txt[-3000:], f"{G}:{gd}")
    v, failing, tag = geom_verdict(line)
    if v != "PASS":
        return fail("geom", line, f"{G}:{gd}/auto_geom.json")
    res.update(stage="geom", verdict="PASS", geom_tag=tag, evidence=f"{G}:{gd}/auto_geom.json")
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
    flags = {}
    for t, v in pt.items():
        if not isinstance(v, dict):
            continue
        ck = v.get("clock") or {}
        taps = [tp for tp in ck.get("taps") or [] if isinstance(tp, dict) and tp.get("kind") == "core"]
        signed = bool(taps and v.get("hard_cores") and all("insertion_ff_ps" in tp and
                      str(tp.get("budget_owner", "")).startswith("SIGNED") for tp in taps))
        if v.get("hard"):
            flags[t] = "hard"
        elif ck.get("core_taps") == "internal" and not signed:
            flags[t] = "contract"
    out = {"mtime": st.st_mtime, "plan_sha": hashlib.sha256(raw).hexdigest(), "types": sorted(pt), "flags": flags,
           "cores": sorted(set(blocks) - set(pt)), "blocks": blocks}
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
    args = {"plan": d["plan"]}
    if mode != "raw":
        args.update(block_identity=mode, identity_baseline_plan=d.get("identity_baseline_plan"))
    p = AP.rpy(d["gen_host"], PROBE_PLAN, args, timeout=600)
    if p.get("error"):
        return {"error": p["error"]}
    p["t"] = time.time()
    if mode == "raw":
        st.setdefault("plans", {})[key] = p
    return p


def plan_dies(AP, cfg, st, owners, status, hub, probe=True, log=print):
    """-> list of (die, ok, why, picks, skip) and the launch list [(die, row)] respecting capacity"""
    out, launch = [], []
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
                    d["_identity_holds"] = {}
                    if d.get("block_identity", "raw") != "raw":
                        names, d["_identity_holds"] = BI.reuse_blocks(
                            names, pn["identities"], pn.get("baseline_identities"),
                            st.get("items") or {}, die=die, event=d["event"],
                            receipts=d.get("identity_reuse_receipts"))
            if ok:
                picks, skip = select(owners, cfg, die, st, names)
                n = capacity(cfg, die, st, status, hub, launched_now=len(launch))
                if d.get("max_items_total"):           # canary: lifetime cap of wave items on this event
                    rel = set(d.get("retry") or [])
                    used = sum(1 for r in st["items"].values() if r.get("die") == die and r.get("event") == d["event"]
                               and f"{r.get('item')}@{r.get('attempt')}" not in rel)
                    n = max(0, min(n, int(d["max_items_total"]) - used))
                launch += [(die, r) for r in picks[:n]]
        out.append((die, ok, why, picks, skip))
    return out, launch


def launch(AP, cfg, st, die, r, hub):
    key = item_key(die, cfg["dies"][die]["event"], r["item"], r.get("block_sha"))
    prev = st["items"].get(key) or {}
    attempt = int(prev.get("attempt", 0)) + 1
    jd = Path(AP.AP_DIR) / "kit_wave" / re.sub(r"[^A-Za-z0-9_.-]", "_", key) / f"a{attempt}"
    sp = spec_for(cfg, die, r["item"], hub)
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
                       geom_tag=res.get("geom_tag", ""))
            enqueue_pass(AP, cfg, st, rec, notices)
            continue
        cls, why = classify(res.get("stage", ""), res.get("tail", ""))
        rec.update(status="FAIL", **{"class": cls}, reason=why)
        if cls == "INFRA" and rec["attempt"] < 2:
            rec["status"] = "RETRY-INFRA"                # relaunched once, next tick (selection sees retry_of)
        notices.setdefault(rec["die"], []).append(f"{rec['item']} FAIL {cls} ({why[:160]}) evid {rec['evidence']}")
        AP.log(f"KIT-WAVE FAIL {rec['die']}/{rec['item']} {cls}: {why}")


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
           + (f" {rec['geom_tag']} (owner standing rule 10-30 00:5x: fill/empty only)" if rec.get("geom_tag") else ""))
    cells = rec.get("cells") or 0
    argv = ["python3", str(Path(__file__).resolve().parent / "enqueue.py"), "--die", rec["die"], "--type", rec["item"],
            "--kit", rec["kit"], "--src", src, "--geom", "PASS", "--geom-ref", ref,
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
    for key, rec in st["items"].items():                 # INFRA relaunch once
        # Semantic adoption requires a fresh profile proof. Never launch an
        # old pending retry before plan_dies has had a chance to hold it.
        identity_mode = (cfg.get("dies", {}).get(rec["die"]) or {}).get("block_identity", "raw")
        if rec.get("status") == "RETRY-INFRA" and identity_mode == "raw" and not stop_reason(cfg, rec["die"], ap_dir):
            rec["status"] = "FAIL"
            launch(AP, cfg, st, rec["die"], {"item": rec["item"], "kind": rec.get("kind", "type"),
                                              "parent_item": rec.get("parent_item"), "block_sha": rec.get("block_sha"),
                                              "replicas": rec.get("replicas")}, AP.HUB_NAME)
    owners = parse_owners((Path(ap_dir) / "OWNERS.tsv").read_text() if (Path(ap_dir) / "OWNERS.tsv").exists() else "")
    rc, out, _ = AP.sh([OT_RUN, "--status"], timeout=120)
    status = parse_otrun_status(out if rc == 0 else "")
    _, todo = plan_dies(AP, cfg, st, owners, status, AP.HUB_NAME)
    for die, r in todo:
        rec = launch(AP, cfg, st, die, r, AP.HUB_NAME)
        if rec:
            notices.setdefault(die, []).append(f"{r['item']} LAUNCHED ({rec['unit']})")
    for die, msgs in notices.items():
        lane = (cfg["dies"].get(die) or {}).get("owner_lane", f"{die} owner")
        AP.coord_append("lanes/COORD-REVIEW-QUEUE.md",
                        f"- {now_s()} KIT-WAVE [{die}] -> {lane}: {len(msgs)} event(s): " + "; ".join(msgs)[:1800])
    if not AP.DRY:
        save_state(st, ap_dir)
        write_stages(st, ap_dir)
    return st


STAGES_FILE = "kit_wave_stages.tsv"
STAGE_COLS = ("die", "item", "parent_item", "plan_sha", "block_sha", "event", "stage", "status", "class", "kit",
              "evidence", "updated")


def write_stages(st, ap_dir):
    """OWNER 12.20: one row per wave kit (keyed on plan block sha) for SIGNOFF-SPRINT-1's lanes/SIGNOFF-STAGES.tsv;
    ENQUEUED rows continue in the autopilot queue (route / sign-off / post-route LEC), joined on the kit path"""
    rows = ["\t".join(STAGE_COLS)]
    for r in sorted((st.get("items") or {}).values(), key=lambda r: (r.get("die", ""), r.get("item", ""))):
        v = dict(r, plan_sha=(r.get("plan_sha") or "")[:12], block_sha=(r.get("block_sha") or "")[:12],
                 stage="queue:route" if r.get("status") == "ENQUEUED" else (r.get("stage") or ""),
                 updated=time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("updated") or 0)))
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
