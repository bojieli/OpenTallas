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
     (measured-hold, hold margin 0 from gen since OWNER 11-02) and runs post-route LEC; every 5th PASS also gets a GEOM REQ for the
     independent visual review (owner rule).  FAIL -> classify() into PLAN / FLOW / RTL / INFRA from the stage + log;
     INFRA (never admitted / host lost / OOM) is relaunched ONCE, everything else stops for the die owner.
     One grouped line per die per tick goes to lanes/COORD-REVIEW-QUEUE.md (for the die's owner lane); OWNERS.tsv
     rows of wave items carry owner KIT-WAVE-1, the live unit and the class + evidence (overlay_owners()).

     Optional per-die route_hold_items maps item glob patterns to nonempty reasons, e.g.
     {"cbf_q01*": "native reset redesign pending"}. It holds only a completed geometry PASS before enqueue,
     retains the kit/review, and resumes enqueue on a later tick when removed. Default empty; admitted jobs
     are never cancelled. Existing hold_items still gates new builds independently.

  7. past GEOM (AUTOBUILD-PIPE-1, OWNER 12.23): follow_queue() joins each enqueued kit with its autopilot job (kit
     runner CTS -> route, signoff_chain sign-off + post-route LEC, archive + PROVENANCE flow tag -> credit_designs
     count) and kit_wave_stages.tsv carries stage/status/class TIMING | ROUTING | PLAN | FLOW | INFRA to the count.
     Types whose plan entry names a child view with a lef but no lib wait (WAIT-DEP, no FAIL record) until the plan
     carries the signed child.  AUTO-GEOM items COORD granted (die geom_exceptions + ruling ref) enqueue PASS-COND.
     An ssh drop before a command ran is retried inside the item (sshd bursts); INFRA relaunches up to infra_attempts.
  8. PROVISIONAL-VIEW launch (KW-PROV-1, COORD 11-03 17:50 (C); die option prov_view, default ON every die): a WAIT-DEP
     type (child hard core planned / lef-without-lib) launches now on a provisional abstract of each such child
     (prov_view.py: the child's latest routed DRC-clean LEF + lib, else a plan-contract blackbox LEF + budget lib), via
     an overlay plan that binds only those children of that type.  The kit carries provisional_views.json, so the
     autopilot holds its sign-off as WAIT-PARENT (provisional.tsv, never archived or counted); when the plan of record
     binds the signed child view, prov_resign_due() runs an STA-only re-sign on the final libs (same routed DB).

    kit_wave.py plan [--config F] [--owners F] [--probe]   dry run: per die gate, picks, skips (prints, launches nothing)
    kit_wave.py status                                      wave state table
    kit_wave.py run-item SPEC.json                          one item pipeline (run by the tick inside a unit)
"""
import argparse
import hashlib
import fnmatch
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
import kit_resume as KR
import wave_jobs as WJ

# A main merge can happen during a long tick. Never release a merged fix with
# older in-memory launch logic; the next ordinary tick imports the new package.
def scheduler_code_id():
    h = hashlib.sha256()
    for name in ("kit_wave.py", "autopilot.py", "source_follow.py", "kit_resume.py"):
        p = Path(__file__).with_name(name)
        h.update(name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


IMPORTED_SCHEDULER_CODE = scheduler_code_id()


def scheduler_current(AP):
    """True when the scheduler files on disk are the code this process imported.  Stale code never creates an attempt
    (launch() refuses); KW-FIX-4 11-03 (COORD 07:1x class fix): instead of deferring to the next tick, _step re-runs the
    pass on the current code in the SAME tick (reload_step).  Merges every ~20 min had deferred 10 ticks on 11-03."""
    return scheduler_code_id() == IMPORTED_SCHEDULER_CODE or os.environ.get("KW_RELOADED") == "1"


def reload_step(AP, ap_dir):
    """run this pass in a fresh process on the CURRENT scheduler code; the caller holds kit_wave.lock (KW_LOCK_HELD)
    and has saved its state.  -> the state the reload pass wrote."""
    ap_dir = ap_dir or AP.AP_DIR
    env = dict(os.environ, KW_RELOADED="1", KW_LOCK_HELD="1", AP_DIR=str(ap_dir))
    cmd = [sys.executable, str(Path(__file__).resolve()), "step"] + (["--dry-run"] if getattr(AP, "DRY", False) is True else [])
    AP.log("KIT-WAVE scheduler files changed: re-running this pass on the current code (same tick, no deferral)")
    try:
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=int(os.environ.get("KW_RELOAD_S", "3000")))
        if p.returncode:
            AP.log(f"KIT-WAVE failed: reload pass rc {p.returncode}: {(p.stderr or p.stdout)[-300:]}")
    except subprocess.TimeoutExpired:
        AP.log("KIT-WAVE failed: reload pass timed out")
    return load_state(ap_dir)


HOME = Path.home()
AP_DIR = Path(os.environ.get("AP_DIR", str(HOME / "coord" / "autopilot")))
OT_RUN = os.environ.get("AP_OT_RUN", str(HOME / ".local/bin/ot-run"))
LANE = "KIT-WAVE-1"
# STRUCTURAL (DIE-HBM-97 11-10, COORD): a design verdict the flow reached early (gpl-noconverge); held like FLOW/PLAN
CLASSES = ("PLAN", "FLOW", "RTL", "INFRA", "STRUCTURAL")
CELL_CAP = 400_000       # default kit run cap; a kit's own native_cell_count.json limit (--native-cell-cap) overrides it
CELL_CAP_MAX = 517_000   # COORD 11-04 06:00 (2): 400k advisory up to the largest closed run; above stays stopped
PLACE_POLL_S = float(os.environ.get("KW_PLACE_POLL_S", "60"))
# run on the gen host by place_receipt(): argv K, service start time (epoch s)
PLACE_RECEIPT = r"""
import glob, json, os, sys
k, t0 = sys.argv[1], float(sys.argv[2])
if any(os.path.exists(os.path.join(k, f)) for f in ("lec_async.stop", "FAIL_PREFLOOR", "FAIL_POSTCTS")):
    sys.exit(0)
for f in sorted(glob.glob(os.path.join(k, "physical_completion", "*.json"))):
    try:
        r = json.load(open(f)); cp = r.get("checkpoint") or {}; c = os.path.join(k, cp["path"]); st = os.stat(c)
    except (OSError, ValueError, KeyError, TypeError):
        continue
    if (r.get("schema") != "opentallas.physical_completion.v1" or r.get("goal") != "place" or r.get("rc") != 0
            or float(r.get("started") or 0) < t0 - 120 or st.st_size != cp.get("size") or st.st_size <= 0
            or st.st_mtime_ns != cp.get("mtime_ns") or not os.path.realpath(c).startswith(os.path.realpath(k) + os.sep)):
        continue
    print("KW_PLACE_RECEIPT " + json.dumps(dict(path=f, run_id=r.get("run_id"), checkpoint=cp, host=r.get("host"),
          proof_owner=r.get("proof_owner"), proof_id=r.get("proof_id"), proof_pending=r.get("proof_pending"))))
"""
# COORD-named plan-of-record events (KIT-WAVE-1 brief 10-30): exact names, or a commit and its descendants
GATE_EVENTS = {"qwen_kvsys": {"exact": ("event28w_c",)},
               "s81": {"descends": "1dfae74037a"},
               # q3 = COORD 23:17 fix-only successor of q2; l45 = COORD 10-30 20:14 HEAD plan of record (12.20 one-block
               # event on l44, ROOT-MERGE-AG 3d326042b); l44 = its parent (ROOT-MERGE-AF b2cd2d28d2a); l46 = COORD 10-30
               # 21:03 HEAD plan of record (hd_st_str one-block on l45, ROOT-MERGE-AG ab0bf8384); l47 = COORD 10-31 01:43
               # HEAD plan of record (insertion_ff_ps 380 -> 342 value-only on 21 types, DIE-HEAD-47 c68675660); l47k = COORD 10-31
               # 04:0x/04:4x (K re-plan strap ties + sidecar, merged 98d42235330), l47t = l47k + hd_st_turn local reset copy (after merge); l48w = COORD 10-31 16:2x/16:4x HEAD plan of record
               # (WFALL 4 types + per-type tap windows + seam_ps 90, merged 29e4be44f); l48x = l48w + one-pin raw-export fixes
               # (COORD 10-31 18:0x (4), DIE-HEAD-52; gate only after its READY is approved); l48y = COORD 11-01 01:0x
               # HEAD plan of record (dh52-tile2 1d77f1bb566 hd_tile; wave switches only after that merge); l48z = l48x +
               # one-block geom fixes in 4 types (COORD 11-01 09:2x plan event, APPROVED 14:0x, merged 854277ebaaf);
               # l48h0 = DIE-HEAD-55 prepared_l48h0 on src claude/dh55-headsrc-1102@69e06c8b9 (COORD 11-03 00:2x (a) APPROVED)
               # l48h1 = DIE-HEAD-56 prep_v3 (plan 8e8ce514127b: l48h0 + hd_ctl_e/hd_ctl_n/hd_host_n cland republish), DIE-HEAD-56 RULING 11-03 04:5x
               # l48rf = DH58-RFPLAN RE-FORM plan event on l48h1 (head_rf_plan_delta.py 9bb4620c625, plan a09cd3ac1180), COORD 11-03 09:0x/09:20
               # l48tb = DH58-TURNB FREG-1 on l48rf (hd_turn_a/hd_turn_b face register + strap K, plan f9623a82a239,
               # claude/dh58-turnb-1103@67cc18d2e8e merged main 4b09653bef8, COORD 16:00 approved)
               # l48ub = DIE-HEAD-62 l48ua + plan-carried lec_hints on hd_host, hd_mesh only (plan 3e4c1adfbb4e, sidecar same)
               # l48uc = DIE-HEAD-65 l48ub + DIE-HEAD-38 landing staging knobs on hd_mesh, hd_host only (head_cland_stage_delta.py, plan 2255e92faccc, sidecar same)
               # l48ud = DIE-HEAD-66 l48uc + landing stage/copy sites off the macros on hd_host, hd_mesh (xy only, plan d8d8a0cac25e, sidecar same)
               # l48ue = DIE-HEAD-68 l48ud + measured per-port tap window (clock.tap_window.per_port_ps) on 9 open types (SDC only, plan 9a2186d89486, sidecar same)
               # l48uf = DIE-HEAD-70 l48ue + hd_tile u_core long-hop params ROW_IN_REG/TEN_HOP/FLT_XHOP 1, BST 3 (head_tile_hop_delta.py, plan 69ce0830f6e4, sidecar same)
               # l48ug = DIE-HEAD-70 l48uf + hd_tile u_core TEN_HOP 2, KEY_HOP 1 (tile4 CTS: ten hop -187, kl_gt -279; 0 cycles; plan 2a0980eb4a82, sidecar same)
               # l48uh = DIE-HEAD-71 l48ug + hd_tile relay_sites only: u_x direct lanes follow BST 3 (head_tile_hop_delta.py --xrelay; tile5 line[899] -126.5; 0 cycles; plan 8a47a824b3c4, sidecar same)
               # l48ui = DIE-HEAD-75 l48uh + hd_serdes pad_clock pma_rck data_inputs pma_rx capture same_edge, eye_hold_extra_ps 175 (SDC only, head_serdes_same_edge_delta.py, plan a2c18c19e08c, sidecar same; COORD 11-06 10:01/10:2x)
               # l48uj = DIE-HEAD-77 l48ui + hd_spn/hd_spn_end partition blocks of the Codex station_closeout plan 1b9d (clock/reset/internal stations only) + 8 hd_spn fstart_face_* landing_local_resets (head_spn_fstart_delta.py, plan 3b0e9771f47b, sidecar same, 0 cycles; COORD 11-06 21:2x (1))
               # l48rc = DH58-RF2 CONSERVATIVE re-form on l48rf (plan 8327f303db76: clock.plain_seam_split rx_in 480/580 +
               # hd_ctl_n reset.local_taps_um; ctl_e/ctl_n/host_n/spn_eshim_tx), OWNER directive via DIE-HEAD-58 11-03 19:3x
               "s81_head": {"exact": ("src25p", "src25q2", "src25q3", "l44", "l45", "l46", "l47", "l47k", "l47t",
                                      "l48w", "l48x", "l48y", "l48z", "l48h0", "l48h1", "l48rf", "l48tb", "l48rc", "l48tc", "l48sd", "l48se", "l48sf", "l48sg", "l48ua", "l48ub", "l48uc", "l48ud", "l48ue", "l48uf", "l48ug", "l48uh", "l48ui", "l48uj")}}
COORD_ONLY = ("qwen_compute", "hbm")          # OFF until COORD enables them (coord_enable = ruling reference)
GATE_KEYS = ("g0c", "bind", "clock")          # plan event checks that must be PASS (12.4a / 12.17 freeze inputs)
# SAFE-STATION-1 11-03 (OWNER TWO-STRIKES): wire-only station types take the relay-bay form (tools/die_plan/relay_bay.py)
# right after gen: a registered relay at every <=300-um hop, extra cycles declared, per-hop table >= +10% of the period
# or FAIL_PREBUILD before route.  Class default ON; a die opts out with "relay_bay_re": "".
RELAY_BAY_RE = {"s81": r"^slice_station__", "qwen_compute": r"^sl[ew]_(?:stm|fw|fe)_v\d"}
DEFAULTS = {"max_inflight": 40, "max_launch_per_tick": 6, "die_max_inflight": 6, "take_states": ["NEEDS-KIT"],
            "kinds": ["type"], "live_claim_h": 3.0, "place_mem_gb": 48, "place_threads": 8, "geom_mem_gb": 24, "geom_grt_wall_s": 1800,
            "gen_mem_gb": 16, "bind_mem_gb": 24, "lint_mem_gb": 8, "geom_sample": 5, "place_prefer": [], "hosts": ["intel1", "intel2", "epyc2", "epyc4"],
            "work_root": "/srv/opentallas-scratch2/claude/kit-wave", "infra_attempts": 3, "launch_stagger_s": 6,
            # KW-RESUME-1 (OWNER 11-01 19:5x / COORD 20:0x default-on): a relaunch reuses the previous attempt's ORFS
            # steps up to the first step whose input fingerprint changed (kit_resume.py); die/global false opts out
            "stage_resume": True,
            # KW-FIX-17 (COORD 11-05 16:4x): a sign-off FAIL with the LEAFSLEW signature relaunches once with the
            # clk_leaf_repeat post-CTS hook; die/global "leafslew_auto": false opts out
            "leafslew_auto": True,
            # KW-FIX-33 (COORD 11-07 22:53, OWNER 11-07 HBM type builds allowed): a die-wide census label in OWNERS.tsv
            # (HBM-PLAN owns every HBM type row with a fresh last_activity) is not a lane claim on a type row; a specific
            # per-item owner still claims.  Die/global "generic_owner_labels" overrides; [] restores the old behaviour.
            "generic_owner_labels": ["HBM-PLAN"]}
# AUTOBUILD-PIPE-1 10-30: an ssh transport drop before the command ran (sshd MaxStartups on the gen host when a tick
# launches 16 items at once) is retried inside the item, never charged to the design: up to SSH_RETRIES more tries
SSH_RETRIES = 3
SSH_DROP = re.compile(r"ot-run: NOT RUN|Connection (?:reset|refused|closed)|kex_exchange_identification|"
                      r"SSH probe exit 255|ssh: connect to host|Could not resolve hostname")
NO_HOST = re.compile(r"no host qualifies|@unit: OSError: \[Errno 28\]")              # ot-run placed nothing: fleet disk or memory, not the design
NO_HOST_RETRY_S = 900
STATE_FILE = "kit_wave_state.json"
LOAD_CAP_FACTOR = 1.5                                    # = ot-heavy LOAD_CAP_FACTOR (read here, set there)


def place_retry_sh(inner, log):
    """KW-FIX-17 11-05 (QC sle_stm_v1 a6 INFRA 15:12): the async PLACE service ran its ot-run client ONCE, so a gen-host
    sshd drop during ot-run's probe ('NOT RUN: no host qualifies (... epyc4: SSH probe exit 255 ...)') failed the
    attempt as INFRA; run() already retries such a drop.  Same rule here: a try whose own output says 'ot-run: NOT RUN'
    and has no 'ot-run: RAN on' (the command never started) is rerun up to SSH_RETRIES more times; rc in $rc."""
    lq = shlex.quote(log)
    return (f"for i in $(seq 0 {SSH_RETRIES}); do echo KW_PLACE_TRY $i; {inner}; rc=$?; [ $rc -eq 0 ] && break; "
            f"t=$(sed -n \"/^KW_PLACE_TRY $i\\$/,\\$p\" {lq}); "
            f"printf '%s' \"$t\" | grep -q 'ot-run: RAN on' && break; "
            f"printf '%s' \"$t\" | grep -q 'ot-run: NOT RUN' || break; [ $i -lt {SSH_RETRIES} ] || break; "
            f"echo \"KW_SSH_RETRY place try $((i+2)) (ot-run NOT RUN before the command ran)\"; "
            f"sleep $((20*(i+1)+RANDOM%20)); done")


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


def place_mem_gb(cfg, die, item):
    """PLACE memory (GB) of one item: the first fnmatch pattern of place_mem_gb_by_item (die > global, in insertion
    order) that matches the item, else the die's place_mem_gb.  QC-TYPES-6 11-08: the hc tap-pair kits need >= 96 GB
    for their kit LEC (rc137 OOM at 32 and 48 GB) without raising every kit's budget."""
    for pat, gb in (opt(cfg, die, "place_mem_gb_by_item") or {}).items():
        if fnmatch.fnmatchcase(str(item), pat):
            return int(gb)
    return int(opt(cfg, die, "place_mem_gb"))


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
        # KW-FIX-45 11-11: the accepted event labels come from the die config too (die option gate_events_extra), so a
        # cut label such as hcut1111 does not need a code change; without the option the code list decides as before.
        if "exact" in rule and ev not in rule["exact"] and ev not in (d.get("gate_events_extra") or ()):
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
    if bad == ["clock"] and d.get("types_before_die_clock"):
        # KW-FIX-32 11-07 (OWNER 17:4x "allow type builds for all dies, including HBM"): die option
        # types_before_die_clock true -> a die whose ONLY non-PASS plan gate is the die clock builds every kind (types
        # too), not just cores; g0c/bind must still PASS.  Default off = the 12.22 item 4 cores-only behaviour below.
        pass
    elif bad == ["clock"] and d.get("core_kit"):
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
    "contract": "plan entry fails kit preflight: clock.core_taps internal with parent_budget core taps (gen ContractError)",
    # AUTOBUILD-PIPE-1 10-30: not launched (gen would fail 'macros have LEF but no timing liberty'); no FAIL record, so
    # the type launches on its own once the plan of record carries the child's signed lib (die owner / core sign-off)
    "noview": "WAIT-DEP: a child hard core / ROM view in the plan has a lef but no lib (child not signed yet)",
    # DIE-KV-62/types 11-02 (class A, KV 21 rows 'macro not declared in the plan type' ORD-2013): a hard_cores[] entry
    # with no lef is a PLANNED core whose view the plan does not bind yet.  gen_phys.type_macros skips it, so kit-rtl
    # inlines the child's soft RTL (kv3_pv_pair -> its ot_sram_1r1w_32x128_m1 leaves; HR cores -> their SRAMs) and the
    # flat kit stops at synth_odb ORD-2013 (macros the type does not place) or runs far over the 400k cell cap.  Not a
    # failure: the type waits (PENDING-DEP) until the plan binds the child's signed lef/lib.  Die opt-out:
    # kit_wave.json dies.<die>.planned_core_flat true (old behaviour: build the type flat with the child inlined).
    "planned": "WAIT-DEP: a child hard core has no view bound in the plan (PLANNED core, no lef/lib): the type kit would "
               "inline the child RTL; waits for the plan to bind the signed child view",
}


def prov_on(d):
    """KW-PROV-1 (COORD 11-03 17:50 (C)): die option prov_view, default ON on every die; false = the old WAIT-DEP wait"""
    return (d or {}).get("prov_view", True) is not False


def prov_item(d, item):
    """True when this item launches on PROVISIONAL child views (planned / noview flag and prov_view on)"""
    f = (d.get("_plan_flags") or {}).get(item)
    return prov_on(d) and (f == "noview" or (f == "planned" and not d.get("planned_core_flat")))


def kit_rtl_mode(d):
    """the die's kit-RTL mode (bind / script): the type kit takes the bound partition RTL; None = plan wrapper"""
    kr = d.get("kit_rtl") if isinstance(d.get("kit_rtl"), dict) else {}
    return kr.get("mode") if kr.get("mode") in ("bind", "script") else None


NEEDS_BIND = ("NEEDS-BIND: plan type has buses with no leaf binding and the die has no kit_rtl (bound partition RTL); "
              "gen would fail 'bus ... is not bound to any leaf port'")


def plan_entry_block(d, item, kind=None):
    """plan-entry kit preflight from the plan probe flags; hard_wrappers opt a hard type back in"""
    if item in (d.get("_identity_holds") or {}):
        return "plan block identity held: " + d["_identity_holds"][item]
    f = (d.get("_plan_flags") or {}).get(item)
    # DIE-HBM-89-TGEN 11-07 (HBM q_b000/q_b001 + __physical_v1 FAIL @gen 19:0x): a type kit without kit_rtl is the
    # plan wrapper, which binds a bus only via buses[].leaf / contents[].bind.  A type with unbound buses fails gen
    # with certainty, so it is not launched (no FAIL row, no gen slot) until the die config gives it bound RTL
    # (kit_rtl mode bind/script).  Die opt-out: unbound_launch true (old behaviour).  kind=core items (core_kit) and
    # hard types never go through the plan wrapper.
    ub = (d.get("_plan_unbound") or {}).get(item)
    if ub and kind != "core" and f != "hard" and not kit_rtl_mode(d) and not d.get("unbound_launch"):
        return f"{NEEDS_BIND} ({len(ub)} bus(es), e.g. {','.join(ub[:3])})"
    if f == "hard" and item in (d.get("hard_wrappers") or []):
        return None
    if f == "planned" and d.get("planned_core_flat"):
        return None
    if prov_item(d, item):
        return None                 # KW-PROV-1: builds on provisional child views (never counted until re-signed)
    if PLAN_BLOCK.get(f):
        return PLAN_BLOCK[f]
    li = (d.get("_lint") or {}).get(item)
    # OWNER 11-03 07:0x: the gen-time lint is an ADVISORY report; it never blocks a launch.  The only blocking case,
    # a missing planned core view, is the probe's planned/noview flag above (WAIT-DEP).  die prelint_block true opts
    # a die back into blocking on lint hits (default off).
    if li and d.get("prelint", True) is not False and d.get("prelint_block"):
        return lint_reason(li)
    return None


# ------------------------------------------------------------------------------------------------ KW-FIX-4 gen-time lint
# OWNER 11-03 (COORD 06:11 RE-FORM template, GEN rules): before any kit launches, a lint fails the type on
#   cells   estimated flat std cells > 150k (plan probe; die prelint_cells_max overrides);
#   memory  a memory over SYNTH_MEMORY_MAX_BITS that is not a macro (the type's GEN_LINT memory_bits verdict on this
#           same plan block; a block change, or a retry row whose fix is named in retry_fix, clears it);
#   view    a planned hard core without a signed view (probe flags planned / noview: these already wait as WAIT-DEP);
#   strap   leaked strap ports (strap_* type ports not declared id_straps/count_straps, duplicate declared names, or the
#           type's gen verdict 'undeclared top-level ID' / 'straps: duplicate names' on this same block).
# OWNER 11-03 07:0x: ADVISORY. A hit is reported as one LINT row (stage prelint, status LINT-ADVISORY) in
# kit_wave_stages.tsv and in the skip-free launch path; it never blocks a launch except a missing planned core view
# (planned/noview flags = WAIT-DEP).  dies.<die>.prelint false: no report; dies.<die>.prelint_block true: block.
PRELINT_HISTORY = (
    ("memory", re.compile(r"memory_bits|SYNTH_MEMORY_MAX_BITS"),
     "memory over SYNTH_MEMORY_MAX_BITS is not a macro (GEN_LINT memory_bits on this block): make it a generated memory macro"),
    ("strap", re.compile(r"undeclared top-level ID|straps: duplicate names"),
     "leaked / duplicate strap ports (gen verdict on this block): declare them in the plan (parent_id_straps)"),
)


COUNT_CACHE = Path.home() / ".local/state/fleet-viz/release_tree_plan_cache.json"
_COUNT_SIGNED = {}


def count_signed_modules(d, die):
    """KW-FIX-35-V 11-08 (COORD: the prelint and the count drifted): the child modules the RELEASE COUNT has signed
    for this die -- the same record source the count uses (release_tree_plan cache: plans[*].signed_cores, matched by
    module name like the counter).  None when the cache is unreadable (no claim either way).  Die option count_cache
    overrides the path."""
    path = Path(d.get("count_cache") or COUNT_CACHE)
    try:
        mt = path.stat().st_mtime
    except OSError:
        return None
    hit = _COUNT_SIGNED.get(str(path))
    if not hit or hit[0] != mt:
        try:
            c = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        by = {}
        for k, p in (c.get("plans") or {}).items():
            if not isinstance(p, dict):
                continue
            dn = p.get("die") or str(k).split("/", 1)[0]
            for m, recs in (p.get("signed_cores") or {}).items():
                if recs:                     # the count lists only signed records per module
                    by.setdefault(dn, set()).add(m)
        hit = _COUNT_SIGNED[str(path)] = (mt, by)
    return hit[1].get(die, set())


def has_counted_view(d, m):
    """a prov_view_sources candidate of m (die config or the auto-views overlay) is the counted signed view"""
    v = (d.get("prov_view_sources") or {}).get(m)
    return any(prov_counted(c) for c in (v if isinstance(v, list) else [v] if v else []) if isinstance(c, dict))


def count_noview(d, counted):
    """KW-FIX-35-CV 11-08: sorted child modules that prelint reports SIGNED IN COUNT BUT NO WAVE VIEW (children of the
    WAIT types -- same flag rule as prelint -- signed in the count with no counted view in prov_view_sources)"""
    if not counted:
        return []
    out = set()
    for t, f in (d.get("_plan_flags") or {}).items():
        if f in ("planned", "noview") and not (f == "planned" and d.get("planned_core_flat")):
            out |= {m for m in (d.get("_plan_deps") or {}).get(t, []) if m in counted and not has_counted_view(d, m)}
    return sorted(out)


# KW-FIX-35-CV 11-08 (DIE-HBM-92 10:2x: types built on PROVISIONAL child views although every child was signed in the
# count; counted_child_views.py was manual, and its --apply wrote the hub's kit_wave.json, which the tick does not read).
# The tick now runs the export itself, at most hourly per die and only for the SIGNED IN COUNT BUT NO WAVE VIEW
# modules, in a detached unit; the unit publishes the complete counted views to this hub sidecar, and every tick merges
# the sidecar into dies.<die>.prov_view_sources at read time (candidates first; the committed config is never written).
# Die/global option auto_child_views false turns both the export and the overlay off.
AUTO_VIEWS_FILE = "prov_view_sources_auto.json"
AUTO_VIEWS_PERIOD_S = 3600


# KW-FIX-44 11-10 (COORD): src_sha does not name a wave source once files are overlaid in place (LEF overrides, flow tools,
# RTL: 6-16 files per die on 11-10), so unchanged_fail saw "no input change" for a row whose input had changed.  The spec
# now carries a content hash of the parts of the source a kit reads; a real overlay changes it, a re-copy does not.
SRC_OVERLAY_SCOPE = ("tools", "rtl", "physical/die_plan", "physical/common_flow")
SRC_OVERLAY_SCRIPT = r"""
import hashlib, os, sys
H = hashlib.sha256()
for r in %r:
    for dp, dn, fn in os.walk(r):
        dn[:] = sorted(d for d in dn if d not in (".git", "__pycache__"))
        for f in sorted(fn):
            p = os.path.join(dp, f)
            if f.endswith(".pyc") or ".bak" in f or os.path.islink(p) or os.stat(p).st_size > 16 << 20:
                continue
            H.update(p.encode() + b"\0")
            with open(p, "rb") as x:
                H.update(hashlib.sha1(x.read()).digest())
print(H.hexdigest())
""" % (SRC_OVERLAY_SCOPE,)


def src_overlay_hash(src, host, hub, timeout=90):
    """content hash of the source scope on its gen host; '' when it cannot be read (the hold then compares as before)"""
    remote = _ssh(host, hub)
    try:
        if remote:
            r = subprocess.run(remote + [f"cd {shlex.quote(src)} && python3 -I -c {shlex.quote(SRC_OVERLAY_SCRIPT)}"],
                               capture_output=True, text=True, timeout=timeout)
        else:
            r = subprocess.run(["python3", "-I", "-c", SRC_OVERLAY_SCRIPT], cwd=src, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    out = r.stdout.strip()
    return out if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{64}", out) else ""


def merge_src_overlay(cfg, hub, log=None):
    """set each enabled die's in-memory _src_overlay, once per pass"""
    for die, d in (cfg.get("dies") or {}).items():
        if isinstance(d, dict) and d.get("enabled") and d.get("src") and d.get("gen_host"):
            d["_src_overlay"] = src_overlay_hash(d["src"], d["gen_host"], hub)
            if log and not d["_src_overlay"]:
                log(f"KIT-WAVE src_overlay: {die} unreadable on {d['gen_host']}; hold compares without it")


def merge_auto_views(cfg, ap_dir, log=None):
    """overlay the sidecar's counted views FIRST into each die's prov_view_sources (in memory) -> {die: [modules]}"""
    p = Path(ap_dir or AP_DIR) / AUTO_VIEWS_FILE
    try:
        side = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for die, ent in ((side or {}).get("dies") or {}).items():
        d = (cfg.get("dies") or {}).get(die)
        if not isinstance(d, dict) or opt(cfg, die, "auto_child_views") is False:
            continue
        pvs = dict(d.get("prov_view_sources") or {})
        for m, cands in sorted(((ent or {}).get("modules") or {}).items()):
            new = [dict(c, counted=True) for c in cands or [] if isinstance(c, dict) and c.get("host") and c.get("dir")]
            if not new:
                continue
            old = pvs.get(m) or []
            old = old if isinstance(old, list) else [old]
            dirs = {c["dir"] for c in new}
            rest = [c for c in old if not (isinstance(c, dict) and c.get("dir") in dirs)]
            # DIE-HBM-97 11-09: a config entry with a detailed abstract is a proven fix for this module; a sidecar view
            # without detail must not shadow it (ot_wbq_root_g1 and others kept their DRT-0073 LEF that way).
            first = [] if any(c.get("detailed_lef") for c in new) else [
                c for c in rest if isinstance(c, dict) and c.get("detailed_lef")]
            pvs[m] = first + new + [c for c in rest if not any(c is f for f in first)]
            out.setdefault(die, []).append(m)
        if die in out:
            d["prov_view_sources"] = pvs
            d["_auto_views"] = out[die]
    if out and log:
        log("KIT-WAVE AUTO-VIEWS overlay: " + " ".join(f"{k}={len(v)}" for k, v in sorted(out.items())))
    return out


def auto_views_step(AP, cfg, st, ap_dir, now=None):
    """launch counted_child_views.py --export --publish for each die whose plan probe has SIGNED IN COUNT BUT NO WAVE
    VIEW children; at most once per AUTO_VIEWS_PERIOD_S per die and never while the die's previous unit is active.
    -> {die: unit}"""
    now = time.time() if now is None else now
    ap_dir = Path(ap_dir or AP_DIR)
    runs = st.setdefault("auto_views", {})
    tool = Path(__file__).resolve().with_name("counted_child_views.py")
    out = {}
    for die, d in sorted((cfg.get("dies") or {}).items()):
        if not isinstance(d, dict) or "_plan_flags" not in d or opt(cfg, die, "auto_child_views") is False:
            continue
        nv = count_noview(d, count_signed_modules(d, die))
        if not nv:
            continue
        last = runs.get(die) or {}
        if now - float(last.get("t") or 0) < float(opt(cfg, die, "auto_views_period_s") or AUTO_VIEWS_PERIOD_S):
            continue
        if last.get("unit") and hasattr(AP, "unit_active") and AP.unit_active(last["unit"]):
            continue
        unit = f"kw-av-{re.sub(r'[^A-Za-z0-9]', '', die)[:16]}-{int(now) % 100000}"
        jd = ap_dir / "auto_views" / die
        dc = {k: d.get(k) for k in ("gen_host", "plan", "event")}
        argv = ["python3", "-I", str(tool), "--die", die, "--export", "--manifest", str(jd / "manifest.json"),
                "--config", str(jd / "config.json"), "--state", str(ap_dir / STATE_FILE),
                "--counter", str(Path(d.get("count_cache") or COUNT_CACHE)), "--publish", str(ap_dir / AUTO_VIEWS_FILE),
                "--only", *nv]
        if getattr(AP, "DRY", False):
            AP.log(f"KIT-WAVE would AUTO-VIEWS {die}: export {len(nv)} counted children ({' '.join(nv[:6])})")
            continue
        jd.mkdir(parents=True, exist_ok=True)
        (jd / "config.json").write_text(json.dumps({"dies": {die: dc}}, indent=1))
        ok = AP.launch_unit(unit, jd / "unit.log", argv)
        runs[die] = {"t": now, "unit": unit if ok else None, "modules": nv, "ok": bool(ok)}
        AP.log(f"KIT-WAVE AUTO-VIEWS {die}: {'launched ' + unit if ok else 'launch FAILED'} for {len(nv)} counted "
               f"children without a wave view ({' '.join(nv[:6])}{' ...' if len(nv) > 6 else ''})")
        if ok:
            out[die] = unit
    return out


def count_view_note(d, deps, counted):
    """'' or '; count: ...' -- per child: signed in the count AND a counted signed view in prov_view_sources (the kit
    is built on it and is FINAL), signed in the count but NO wave view (export it: counted_child_views.py), unsigned"""
    if counted is None or not deps:
        return ""
    has = lambda m: has_counted_view(d, m)
    sv = [m for m in deps if m in counted and has(m)]
    nv = [m for m in deps if m in counted and not has(m)]
    un = [m for m in deps if m not in counted]
    parts = ([f"signed+view {len(sv)}"] if sv else []) + (
        [f"SIGNED IN COUNT BUT NO WAVE VIEW {len(nv)} ({','.join(nv[:4])})"] if nv else []) + (
        [f"unsigned {len(un)} ({','.join(un[:4])})"] if un else [])
    return "; count: " + ", ".join(parts)


def lint_reason(issues):
    kinds = sorted({str(i).split(":", 1)[0] for i in issues})
    return f"LINT {'+'.join(kinds)}: gen-time lint before launch (no build), see kit_wave_stages.tsv LINT rows"


def prelint(d, die, names, state):
    """-> {item: [issue, ...]} for the current plan of record: probe (plan-static) issues + verdict history on the SAME
    plan block (key) that no named fix released.  names: {type: block_sha} (or a set)."""
    out = {t: list(v) for t, v in (d.get("_plan_lint") or {}).items()}
    counted = count_signed_modules(d, die)
    for t, f in (d.get("_plan_flags") or {}).items():
        if f in ("planned", "noview") and not (f == "planned" and d.get("planned_core_flat")):
            deps = (d.get('_plan_deps') or {}).get(t, [])
            out.setdefault(t, []).append(f"view: planned hard core without a signed view: "
                                         f"{','.join(deps[:4])} "
                                         + ("(launches on PROVISIONAL child views, KW-PROV-1)" if prov_on(d)
                                            else "(waits, WAIT-DEP)") + count_view_note(d, deps, counted))
    fixed = set((d.get("retry_fix") or {}).keys()) if isinstance(d.get("retry_fix"), dict) else set()
    items = (state or {}).get("items") or {}
    blocks = names if isinstance(names, dict) else {}
    for t in (names or ()):
        rec = items.get(item_key(die, d.get("event"), t, blocks.get(t)))
        if not rec or rec.get("status") not in ("FAIL", "CANCELLED") or f"{t}@{rec.get('attempt')}" in fixed:
            continue
        txt = f"{rec.get('reason') or ''}\n{rec.get('errors') or ''}"
        for kind, rx, msg in PRELINT_HISTORY:
            if rx.search(txt):
                out.setdefault(t, []).append(f"{kind}: {msg} (attempt {rec.get('attempt')})")
    return {t: v for t, v in out.items() if v and (not names or t in names)}


def record_lint(st, cfg, die, lint):
    """replace the die's LINT rows (st['lint']) with this tick's verdict"""
    d = cfg["dies"][die]
    L = st.setdefault("lint", {})
    for k in [k for k, v in L.items() if v.get("die") == die]:
        del L[k]
    if d.get("prelint", True) is False:
        return
    blocks = d.get("_lint_blocks") or {}
    for t, issues in lint.items():
        L[f"{die}|{t}"] = dict(die=die, item=t, event=d.get("event"), plan_sha=d.get("_plan_sha"),
                               block_sha=blocks.get(t) if isinstance(blocks, dict) else None,
                               issues=issues, evidence=d.get("plan", ""), updated=time.time())


def _own_wave_unit(r):
    """DIE-QC-63/KITS 11-02: overlay_owners writes the wave's OWN in-flight unit into the parent OWNERS row
    (owner KIT-WAVE-*, live_job 'kit-wave unit ...', newest record of ANY class of that parent).  That is not
    another lane's claim: per-class records already gate in-flight classes ('wave item in flight' / 'all plan
    classes already in the wave').  Treating it as one blocked every sibling class and every released retry of
    the parent while one sibling ran (QC 11-02: 18 parents; GPL-0305 retries x3, slw_stm_v1__cle34a73c3 never
    launched)."""
    if not str(r.get("owner", "")).startswith("KIT-WAVE"):
        return False
    lj = str(r.get("live_job", ""))
    if lj.startswith("kit-wave unit"):
        return True
    # KW-FIX-12 11-05: the queue form 'ap-<id>-a<n> <id>' on a KIT-WAVE row is the wave's own routed kit of one sibling
    # class; it blocked released retries of the other classes (QC 11-05: 26 parents, sle_su_l1).
    # KW-FIX-35-P 11-08: ownership.py lists EVERY live job of the parent, '; '-joined, with ' (+N)' for jobs not shown
    # ('ap-X-a1 X; ap-Y-a1 Y (+2)').  Only the first entry was read, so two of the wave's own route jobs looked like
    # another lane's claim and held sle_stm_v2 / slw_su_l0 classes on 11-08.  Each listed entry must be the wave's own
    # (ap- queue job, or an ot-run job dir of this item / its classes); one foreign entry keeps the claim.
    lj = re.sub(r"\s*\(\+\d+\)\s*$", "", lj)
    parts = [x.strip() for x in lj.split("; ") if x.strip()]
    return bool(parts) and all(_own_wave_entry(x, r["item"]) for x in parts)


def _own_wave_entry(lj, item):
    """one live_job entry of a KIT-WAVE OWNERS row: the wave's own queue job or its own place/geom job of item"""
    if re.fullmatch(r"ap-[0-9a-f]+-a\d+ [0-9a-f]+", lj):
        return True
    # ownership.py form 'ot-run pid N <last 70 chars of the job dir>': the wave's own place/geom job of this item or
    # one of its classes (wave kit dirs end .../items/<class>/[attempt_n/]gen/<class>)
    if not lj.startswith("ot-run pid"):
        return False
    segs = re.split(r"[/\s]+", lj.split(None, 3)[-1]) if len(lj.split(None, 3)) == 4 else []
    return ("gen" in segs or "items" in segs) and any(x == item or x.startswith(item + "_") for x in segs)


def blocked_parents(d):
    """SCHED-1 11-07 (OWNER closure first): {child module: plan types still waiting for its view}, from the plan probe's
    _plan_deps / _prov_deps.  The rows that unlock the most blocked parents launch first."""
    n = {}
    for deps in (d.get("_prov_deps") or d.get("_plan_deps") or {}).values():
        for m in set(deps):
            n[m] = n.get(m, 0) + 1
    return n


WAVE_SRC_CHECK_DIR = "/srv/opentallas-scratch2/claude/wave-ops-1/srccheck"


def wave_src_flag(cfg, die):
    """WAVE-OPS-1 11-10 (COORD URGENT (a)): the FLAGS line for a die whose wave src differs from its declared commit +
    approved overlays, read from WAVE-OPS-1's last check (srccheck/<die>.json on the hub); '' when clean, absent, for
    another src, or unreadable.  ADVISORY (OWNER 11-03 targets, not gates)."""
    d = (cfg.get("dies") or {}).get(die) or {}
    try:
        r = json.loads((Path(cfg.get("wave_src_check_dir") or WAVE_SRC_CHECK_DIR) / f"{die}.json").read_text())
    except (OSError, ValueError):
        return ""
    if not isinstance(r, dict) or r.get("src") != d.get("src") or not r.get("mismatch"):
        return ""
    return (f"FLAGS WAVE-SRC-DRIFT {die}: src {r.get('src')} on {r.get('host')} differs from declared "
            f"{str(r.get('declared') or '?')[:12]} + approved overlays in {r['mismatch']} file(s) "
            f"(stale old git copies {r.get('stale', 0)}, not in git {r.get('undeclared', 0)}; checked {r.get('at', '?')}; "
            f"ADVISORY, WAVE-OPS-1 wave_src_check)")


NO_ROW_SOURCE = "NO-ROW-SOURCE: only_items item with no OWNERS row and no plan_core_items/allowlist row (never launches)"


def no_row_source(rows, d, die, plan_types):
    """WAVE-OPS-1 11-10 (OWNER item A): only_items names the wave can never pick because nothing makes a row for them.
    A row comes from OWNERS.tsv (the item, its class parent '<k>__...', or its core module for '<m>__v<sha12>'), from
    plan_items_from_allowlist (a type in the plan of record) or from plan_core_items (a core in the plan of record).
    18 HBM cores were allowed in only_items but had no OWNERS row and no plan_core_items entry, so they silently never
    launched.  -> sorted list of those items; [] when the plan is unknown (no probe) or there is no allowlist."""
    if plan_types is None or d.get("only_items") is None:
        return []
    known = {r["item"] for r in rows if r["die"] == die}
    cores = set(d.get("plan_core_items") or [])
    out = []
    for item in d.get("only_items") or []:
        if item in known or core_module(item) in known or any(item.startswith(k + "__") for k in known):
            continue
        if item in plan_types and (d.get("plan_items_from_allowlist") or item in cores):
            continue
        out.append(item)
    return sorted(set(out))


def select(rows, cfg, die, state, plan_types=None):
    """-> (picked rows in launch order, {reason: [items]})"""
    d = cfg["dies"][die]
    ev = d["event"]
    states = set(opt(cfg, die, "take_states"))
    kinds = set(opt(cfg, die, "kinds"))
    claim_m = float(opt(cfg, die, "live_claim_h")) * 60
    generic = set(opt(cfg, die, "generic_owner_labels") or [])
    retry = set(d.get("retry") or [])                 # "item@attempt": COORD released that failed attempt
    skip = {}
    picked = []
    orphans = no_row_source(rows, d, die, plan_types)
    if orphans:
        skip[NO_ROW_SOURCE] = orphans                   # plan_dies() logs it loudly every tick
    if (d.get("plan_items_from_allowlist") or d.get("plan_core_items")) and plan_types is not None:
        # Adopted plans may split types before the ownership census catches up.
        # Explicit die-owned allowlists select those real plan types; retain every
        # existing ownership/live-job claim and the normal retry/geometry gates.
        rows = list(rows)
        known = {r["item"] for r in rows if r["die"] == die}
        for item in (d.get("only_items") or []) if d.get("plan_items_from_allowlist") else []:
            # Existing parent rows already expand into these plan classes,
            # including their live-job claims; do not synthesize a second owner.
            if item in known or item not in plan_types or any(item.startswith(k + "__") for k in known):
                continue
            rows.append(dict(die=die, item=item, kind="type", state="NEEDS-KIT",
                             owner="KIT-WAVE", live_job="none", last_activity="",
                             next_step="adopted plan allowlist", evidence=d.get("plan", ""),
                             default_owner=d.get("owner_lane", ""), replicas="1", members=""))
        # A plan-of-record hard core the ownership census cannot see yet (OWNERS reads the older HBM plan): a kind=core
        # row for the names the die lists, and only those.
        for item in d.get("plan_core_items") or []:
            if item in known or item not in plan_types:
                continue
            rows.append(dict(die=die, item=item, kind="core", state="NEEDS-KIT",
                             owner="KIT-WAVE", live_job="none", last_activity="",
                             next_step="adopted plan core allowlist", evidence=d.get("plan", ""),
                             default_owner=d.get("owner_lane", ""), replicas="1", members=item))
    for r in rows:
        if r["die"] != die:
            continue
        why = None
        # Die owners may park a measured failing class while its structural fix
        # is built. Explicit holds only affect new picks; active jobs are intact.
        import fnmatch
        held = next((why for pat, why in (d.get("hold_items") or {}).items()
                     if fnmatch.fnmatchcase(r["item"], pat)), None)
        if held:
            skip.setdefault("die-owned hold: " + held, []).append(r["item"])
            continue
        blk = lambda t: plan_types.get(t) if isinstance(plan_types, dict) else None
        if counted_now(cfg, state, die, r["item"], blk(r["item"])):
            skip.setdefault("counted by the sign-off counter", []).append(r["item"])
            continue
        rec = (state.get("items") or {}).get(item_key(die, ev, r["item"], blk(r["item"])))
        only_retry = False
        if r["state"] not in states:
            # KW-RELAUNCH-1 11-05: the parent row of a class-split item carries the state of the wave's OWN running class
            # (ROUTING / QUEUED ...).  That hid every released retry of its sibling classes (S81 slice_station t29 / t40 /
            # t6: retry @6 / @8 / @9 set, never launched).  Such a parent still expands, but only into released retries.
            if not (str(r.get("owner", "")).startswith("KIT-WAVE") and _own_wave_unit(r)
                    and plan_types is not None and r["item"] not in plan_types
                    and any(x.split("@", 1)[0].startswith(r["item"] + "__") for x in retry)):
                continue
            only_retry = True
        if r["kind"] not in kinds:
            why = f"kind {r['kind']} not in wave"
        elif d.get("_cores_only") and r["kind"] != "core":
            why = "die clock not PASS: cores only (core_kit, 12.22 item 4)"
        elif rec and rec.get("status") in ("RUNNING", "LAUNCHING", "ROUTE-HELD"):
            why = "wave item in flight"
        elif prov_predecessor(d, die, state, r["item"], rec):
            why = ("PROV-RESIGN: the PROVISIONAL kit of this type re-signs (STA only, no re-route) on the signed child "
                   "views (KW-PROV-1)")
        elif rec and rec.get("status") == "ENQUEUED" and not (
                rec.get("q_status") == "FAIL" and f"{r['item']}@{rec.get('attempt')}" in retry):
            # KIT-TRIAGE-1 11-01: a kit that FAILED in the autopilot queue (route / sign-off) stays ENQUEUED in the
            # wave; once a class fix lands, COORD (retry) or a merged kit_wave_pending.tsv row releases that attempt
            # and the wave builds a fresh kit (attempt + 1) on the current source -- the batch relaunch path
            why = "wave kit enqueued" + (" (queue FAIL; relaunch = retry item@attempt)" if rec.get("q_status") == "FAIL" else "")
        elif rec and rec.get("status") == "CANCELLED" and rec.get("volume") and (
                rec["volume"] in pilot_classes_state(d, die, state)[0]
                or pilot_fail_times(d, die, state, d.get("src_sha") or "").get(rec["volume"], 0.0) <= float(rec.get("started") or 0)):
            pass        # queued volume cancelled by a failed pilot: class now proven, or no class FAIL stands any more
        elif rec and is_wait_dep(rec) and not rec.get("provisional") and prov_item(d, r["item"]):
            pass        # KW-PROV-1: a gen-time WAIT-DEP stop (child view missing) relaunches on provisional child views
        elif rec and f"{r['item']}@{rec.get('attempt')}" not in retry:
            why = f"wave {rec.get('status')} {rec.get('class', '')} on this plan block (no blind retry)".replace("  ", " ")
        elif rec and cfg.get("hold_unchanged") and unchanged_fail(cfg, state, die, r["item"], rec, r.get("parent_item"), r.get("kind")):
            why = HOLD_UNCHANGED
        elif r["live_job"] not in ("", "none") and not _own_wave_unit(r):
            why = "live job (another lane)"
        elif age_min(r["last_activity"]) is not None and age_min(r["last_activity"]) < claim_m \
                and not str(r["owner"]).startswith("KIT-WAVE") \
                and not (r["kind"] == "type" and r["owner"] in generic):
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
            blocked = [c for c in cls if plan_entry_block(d, c, r.get("kind"))]
            for c in blocked:
                skip.setdefault(plan_entry_block(d, c, r.get("kind")), []).append(c)
            for c in cls:                    # DIE-QC-63/KITS 11-02: hold_items naming a class hold that class
                hc = next((w for pat, w in (d.get("hold_items") or {}).items() if fnmatch.fnmatchcase(c, pat)), None)
                if hc and c not in blocked:
                    skip.setdefault("die-owned hold: " + hc, []).append(c)
                    blocked.append(c)
            for c in cls:
                if c not in blocked and counted_now(cfg, state, die, c, blk(c)):
                    skip.setdefault("counted by the sign-off counter", []).append(c)
                    blocked.append(c)
            cls = [c for c in cls if c not in blocked]
            # KW-FIX-8 11-04: a class in flight is never picked again.  Without this a retry row naming the live attempt
            # relaunched a RUNNING class (QC 11:30: 12 classes launched twice in one pass, a2 then a3)
            cls_live = lambda c: (its.get(item_key(die, ev, c, blk(c))) or {}).get("status") in ("RUNNING", "LAUNCHING")
            released = lambda c: f"{c}@{(its.get(item_key(die, ev, c, blk(c))) or {}).get('attempt')}" in retry
            todo = [c for c in cls if not cls_live(c) and (not only_retry or released(c))
                    and (not its.get(item_key(die, ev, c, blk(c)))
                    or f"{c}@{its[item_key(die, ev, c, blk(c))].get('attempt')}" in retry
                    or (is_wait_dep(its[item_key(die, ev, c, blk(c))]) and not its[item_key(die, ev, c, blk(c))].get("provisional")
                        and prov_item(d, c)))]
            if cfg.get("hold_unchanged"):
                same = [c for c in todo if unchanged_fail(cfg, state, die, c, its.get(item_key(die, ev, c, blk(c))), r["item"], r.get("kind"))]
                if same:
                    skip.setdefault(HOLD_UNCHANGED, []).extend(same)
                    todo = [c for c in todo if c not in same]
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
            why = plan_entry_block(d, r["item"], r.get("kind"))
        if why:
            skip.setdefault(why, []).append(r["item"])
            continue
        picked.append(dict(r, block_sha=blk(r["item"])) if blk(r["item"]) else r)

    # An allowlist class may also be expanded from its OWNERS parent. Both
    # rows name one producer, not parallel forms; retain its first eligible row.
    unique, seen = [], set()
    for row in picked:
        key = item_key(die, ev, row["item"], row.get("block_sha"))
        if key in seen:
            skip.setdefault("same plan item already selected this tick", []).append(row["item"])
            continue
        seen.add(key)
        unique.append(row)
    picked = unique

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
    unlocks = blocked_parents(d)
    picked.sort(key=lambda r: (-unlocks.get(core_module(r["item"]), 0), 0 if r["kind"] == "core" else 1, -rep(r), r["item"]))
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
        elif r.get("status") in ("RUNNING", "LAUNCHING") or r.get("enqueue_pending") or (
                r.get("status") == "ENQUEUED" and r.get("q_status") not in ("FAIL", "SIGNED")):
            live[c] = live.get(c, 0) + 1
    return signed, live


def pilot_queue_mode(d, cfg=None):
    """OWNER 11-01 / COORD 05:3x (1): pilot_mode 'queue' (die or global) = unproven-class volume is queued behind its
    pilots instead of held out of the queue; anything else = the 12.27a hold"""
    return str(d.get("pilot_mode") or (cfg or {}).get("pilot_mode") or "") == "queue"


def pilot_gate(picked, skip, d, die, state):
    """OWNER 12.27a PILOT FIRST (default on): a die x kit class with no signed-off kit has at most pilot_max (default 2,
    the 12.17 parallel variants) kits in flight, counting the ones already running; new launches past that wait.  Classes
    with a signed pilot keep full volume.  In-flight kits are never touched.  pilot_gate false only by COORD ruling."""
    if d.get("pilot_gate") is False:
        return picked
    cap = int(d.get("pilot_max", 2))
    signed, live = pilot_classes_state(d, die, state)
    out, volume = [], []
    for r in picked:
        c = pilot_key(d, die, r["item"], r.get("kind") or "type")
        if c in signed:
            out.append(r)
        elif live.get(c, 0) < cap:
            live[c] = live.get(c, 0) + 1
            out.append(r)
        elif pilot_queue_mode(d):
            # OWNER 11-01 (COORD 05:3x (1)): volume of an unproven class is queued too, BEHIND every pilot of the tick
            # (launched last; ot-run waiters); cancel_class_volume() stops it while queued if a pilot of its class fails
            volume.append(dict(r, volume=c))
        else:
            skip.setdefault(f"PILOT-FIRST 12.27a: class {c} unproven, {cap} pilot(s) in flight", []).append(r["item"])
    out += volume
    return out


# ------------------------------------------------------------------------------------------------ capacity
def parse_otrun_status(text):
    """ot-run --status -> {host: {"admit": GB, "run": n, "load": x, "cores": n}}"""
    out = {}
    for part in (text or "").split("|"):
        # KIT-WAVE-10 10-31: a negative admission ("admits -29 GB") and fields between load and run ("waiters 1:200 GB")
        # must not drop the host (intel1 with a waiter vanished from the status, so the wave launched nothing there)
        m = re.search(r"([A-Za-z0-9_.-]+) admits (-?\d+) GB.*?load (\d+(?:\.\d+)?)/(\d+)\b.*?\brun (\d+)", part)
        if m:
            out[m.group(1)] = {"admit": int(m.group(2)), "load": float(m.group(3)), "cores": int(m.group(4)),
                               "run": int(m.group(5))}
            # KW-FIX-4 11-03 (COORD 12:1x FLEET): the queued demand 'waiters N:G GB' -> wait_n / wait_gb
            w = re.search(r"\bwaiters (\d+):(\d+) GB", part)
            if w:
                out[m.group(1)].update(wait_n=int(w.group(1)), wait_gb=int(w.group(2)))
            # KW-FIX-24 11-06 (COORD 16:2x): the scratch disk's free GB ('scratch 44 GB') -> scratch_gb (gen_disk_low)
            sc = re.search(r"\bscratch (\d+) GB", part)
            if sc:
                out[m.group(1)]["scratch_gb"] = int(sc.group(1))
    return out


def inflight(state, die=None):
    return sum(1 for r in (state.get("items") or {}).values()
               if r.get("status") in ("RUNNING", "LAUNCHING") and (die is None or r.get("die") == die))


def capacity(cfg, die, state, status, hub="intel2", launched_now=0):
    """number of items this die may launch now"""
    hosts = [("localhost" if h == hub else h) for h in opt(cfg, die, "hosts")]
    mem = int(opt(cfg, die, "place_mem_gb"))
    # OWNER 11-01 (COORD 05:3x): queue_fill keeps the ot-run queue full (waiters > 0 on every host): launch whether or
    # not a host admits the place request now; the item waits in ot-run (memory admission) instead of in the planner
    if not cfg.get("queue_fill") and not any((status.get(h) or {}).get("admit", 0) >= mem for h in hosts):
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
# DIE-HBM-97 11-10 (COORD ruling, gplcap-classifier): this OpenROAD build caps each Nesterov pass at 5,000 iterations.
# At the cap it prints [WARNING GPL-1010], writes the placement anyway and the flow goes on: kv_line vC stopped at row
# 4,990 with overflow 0.370, repair_design then inserted 459k buffers and DPL-0038 failed at 153% utilisation.
# Converging peers end under 1,000 iterations at overflow <= 0.1 (q_b100pv1 957, q_b011 468, q_b012 441, q_spu1 463).
# A capped pass at overflow <= 0.1 is not this class.  Routability / timing-driven runs restart the Nesterov table
# many times (vB 225,900 iterations): each GPL-1010 closes one pass, and the first capped pass above the limit decides.
GPL_CAP_OVERFLOW = 0.1
GPL_CAP_MARK = "GPL-1010"
GPL_ROW = re.compile(r"^\s*(\d+) \|\s+([0-9.]+) \|")                       # 'Iteration | Overflow | HPWL ...' table
GPL_ROW_OLD = re.compile(r"Iter:\s*(\d+)\s+overflow:\s*([0-9.]+)", re.I)   # older [NesterovSolve] form
GPL_PROBE_PREFIX = "KW_GPL "                                                  # probe lines (after_place / PROBE_CLASSIFY)


def gpl_cap_noconverge(text, limit=GPL_CAP_OVERFLOW):
    """a 3_3_place_gp log (or the probe's KW_GPL lines: the last table row before each GPL-1010 and the warning) ->
    'GPL-1010 ... iteration N overflow X > 0.1 ...' for the first Nesterov pass that stopped at the iteration cap with
    overflow above limit, else None.  A pass whose last row is <= limit, or a log without GPL-1010, gives None."""
    last, capped = None, 0
    for ln in (text or "").splitlines():
        if ln.startswith(GPL_PROBE_PREFIX):
            ln = ln[len(GPL_PROBE_PREFIX):]
        if GPL_CAP_MARK in ln:
            capped += 1
            if last is not None and last[1] > limit:
                return (f"{GPL_CAP_MARK} Nesterov pass cap hit at iteration {last[0]} with overflow {last[1]:.3f} > "
                        f"{limit:g} (capped pass {capped}): placement did not converge; resizer/DPL would run on it")
            last = None
            continue
        m = GPL_ROW.search(ln) or GPL_ROW_OLD.search(ln)
        if m:
            last = (int(m.group(1)), float(m.group(2)))
    return None


# probe shell (gen host): the last table row before each GPL-1010 of the kit's global-place logs, prefixed KW_GPL
GPL_PROBE_AWK = (r"""awk '/GPL-1010/{print "KW_GPL " l; print "KW_GPL " $0; l=""; next} """
                 r"""/^ *[0-9]+ \| +[0-9.]+ \|/ || /Iter: *[0-9]+ +overflow:/{l=$0}'""")


# (class, stage regex or None, text regex, reason).  First match wins; stage-specific rules first.
RULES = [
    # DIE-HBM-97 11-10 (COORD): before INFRA and the PLAN geometry rules.  The capped unconverged placement is the cause;
    # the DPL-0038 / utilisation / OOM / watchdog lines after it are its consequence, so it wins whatever surrounds it.
    ("STRUCTURAL", r"^place$", lambda s: gpl_cap_noconverge(s),
     "gpl-noconverge: global placement stopped at the per-pass Nesterov iteration cap unconverged"),
    # KIT-TRIAGE-1 11-01: gen raises when a plan landing band has no rect / placement FAIL (S81 svc_* on e8cbe5f6c70;
    # DIE-S81-47 event2 2026e1e1561 adds the bands) -> a plan event, not a flow error
    ("PLAN", None, r"landing band absent", "plan landing band absent (plan event: band rect / placement)"),
    # KW-FIX-7 11-04: before INFRA. S81 serdes__t3/t4/t12-16 stopped on the cap with ot-run client text beside it, read as
    # INFRA and relaunched at the same cap.  The cap line is a verdict on the kit whatever surrounds it.
    ("PLAN", r"^place$", r"OT_NATIVE_CELL_CAP.*above \d+ run cap", "actual native standard-cell count above the kit run cap"),
    # KW-FIX-8 11-04: same class.  serdes__t13 a6: MPL-0034 at 08:46, make stopped, a parallel LEC then idled until the
    # watchdog stop 12:53, so the unit ended 143, read as INFRA and relaunched at the same macro position.
    ("PLAN", r"^place$", r"\[ERROR MPL-0034\]", "plan macro position outside the core"),
    # NETNONE_1111 (KW-FIX-44, COORD 11-11): ot-heavy containers run with --network none by default; a job that really
    # needs the network fails on name resolution / connect: INFRA, and its class goes into /etc/ot-heavy-network-allow
    ("INFRA", None, r"Temporary failure in name resolution|Could not resolve host|Name or service not known|"
                    r"Network is unreachable|getaddrinfo failed|Failed to establish a new connection",
     "infra (NETNONE: network refused in a --network none container; allowlist the class in /etc/ot-heavy-network-allow)"),
    # RC125_1111 (KW-FIX-44, COORD 11-11 via KW-FIX-43): docker rc 125 at gen / gen_lint is the daemon refusing or failing
    # to create the container (leaked veth device units, udevd / logind under load), never a design result
    ("INFRA", r"^gen(?:_lint)?$", r"docker: Error response from daemon|Error response from daemon: failed to create|"
                                  r"\brc[ =]+125\b|\bexit(?: status| code)? 125\b|returned non-zero exit status 125\b",
     "infra (docker rc 125: container not created)"),
    ("INFRA", None, r"ot-run: NOT RUN|ot-run: NOT COMPLETED|exit 1(?:37|43)\b|Out of memory|oom-kill|OOMKilled|"
                    r"No space left on device|rsync error|Cannot connect to the Docker daemon|"
                    r"yosys elaboration failed rc[ =]+1(?:25|37)\b|"
                    # S81-OTHERFAIL-1 11-07: host earlyoom SIGTERMs yosys (epyc2 16:01/16:09 PST, mem 3%): the synth make
                    # reports 'Error 241' (256-15), selrange 'yosys exit -15', rtl_lint/selrange the KILLED marker
                    # KW-FIX-43 11-09: make Error 247 = 256-9, a SIGKILL (q_su20 cgroup kill was labelled PLAN off [INFO PDN-0001])
                    r"\] Error 24[17]\b|yosys exit -15\b|FAIL_PREFLOOR \w+ KILLED \(yosys signal", "infra"),
    # transport only: an ssh drop BEFORE the command ran.  When ot-run reports 'RAN on <host>' the command ran and its
    # own error decides the class (a probe of another host that failed is not the item's failure)
    ("INFRA-SSH", None, r"ssh: connect to host|Connection (?:reset|refused|closed)|kex_exchange_identification|"
                        r"SSH probe exit 255|Host key verification failed|Could not resolve hostname", "infra (ssh transport)"),
    ("RTL", None, r"LEC NOT EQUIVALENT|NOT EQUIVALENT|NON-?EQUIV", "LEC not equivalent"),
    ("INFRA", None, r"^Terminated\b|\nTerminated\b|Killed\s*$", "process terminated (not a design result)"),
    ("PLAN", None, r"ContractError|requires explicit SIGNED", "plan contract metadata missing for this type"),
    # AUTOBUILD-PIPE-4 10-31 (OWNER 12.27 d): generation-time lint (tools/die_plan/kit_gen_lint.py), one class per check
    ("RTL", r"^gen_lint$", r"GEN_LINT FAIL rtl_check", "RTL hierarchy / undriven / multi-driven at gen (GEN_LINT)"),
    ("PLAN", r"^gen_lint$", r"GEN_LINT FAIL (?:macro_tcl|pins_vs_plan)",
     "plan at gen: no static macro sites / kit pins differ from the plan (GEN_LINT)"),
    ("FLOW", r"^gen_lint$", r"GEN_LINT FAIL (?:memory_bits|clock_export_form)",
     "kit recipe at gen: memory bits over SYNTH_MEMORY_MAX_BITS / tie clock export form (GEN_LINT)"),
    ("FLOW", r"^gen_lint$", r"GEN_LINT FAIL src_skew",
     "kit source older than the queue lint (GEN_LINT src_skew): bump the wave src to the hub commit and re-GEN"),
    # KW-PROV-1 11-03: no routed abstract passed the plan-pin check and the plan has no contract for a child
    ("PLAN", r"^prov_", r"PROVISIONAL view FAIL|PROV_FAIL", "PROVISIONAL child view: no routed abstract / plan contract"),
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
    # KIT-TRIAGE-1/G26 11-01 (HBM ot_hgi_sfu_split3_lane_core__idpin @place): the preflight's yosys 'check -assert'
    # (undriven wires) reported only as 'FAIL_PREFLOOR rtl_lint' fell through to 'unclassified'
    ("RTL", None, r"is used but has no driver|Found \d+ problems in 'check -assert'|FAIL_PREFLOOR rtl_lint",
     "RTL lint at preflight (undriven / check -assert)"),
    # SAFE-STATION-1 11-03: a relay-bay hop below +10% of the period = the station plan (bays / lane length), not the flow
    ("PLAN", None, r"FAIL_PREBUILD relay_bay", "relay-bay pre-build hop table below +10% (station lane plan)"),
    ("PLAN", None, r"FACE_GUARD FAIL|face_guard[^\n]*FAIL|FAIL_PREFLOOR face_guard", "face guard (plan pins / landing)"),
    ("PLAN", None, r"PORT_BIND FAIL|port_bind[^\n]*FAIL|FAIL_PREFLOOR port_bind", "port bind (plan pins)"),
    ("PLAN", None, r"LEF master \S+ not found|ORD-2013", "macro not declared in the plan type"),
    ("PLAN", None, r"is blocked|fails? closed|no legal site|DPL-0033|DPL-0036|not in plan|unknown (?:partition )?type|"
                   r"outline|utili[sz]ation .* exceeds|\[ERROR PDN-0\d+|Error:[^\n]*PDN-0\d+", "plan geometry / site"),
    ("PLAN", r"^geom$", r"FAIL", "AUTO-GEOM rule FAIL (geometry)"),
    ("PLAN", r"^kit_topology$", r"KIT_TOPOLOGY_(?:BIND_STALE|CONTEXT|REGENERATE|SOURCE)",
     "native source stage/reset realization differs: regenerate the canonical bind/kit"),
    ("FLOW", r"^kit_topology$", r"No such file|can.t open file|ImportError|ModuleNotFoundError",
     "captured source cohort lacks canonical topology preparation capability/input"),
    ("FLOW", r"^bind$", r"FileNotFoundError|No such file", "die-prep bind recipe input missing"),
    ("PLAN", r"^bind$", r".", "plan of record not cleanly bound (strict bind)"),
    ("PLAN", r"^cells$", r".", "cell count above the kit run cap"),
    ("PLAN", None, r"GEN_NO_KIT", "gen wrote no kit (hard / skipped type in the plan)"),
    # DIE-HBM-89-TGEN 11-07 (HBM q_b000/q_b001 @gen 'unclassified'): the plan-wrapper gen found a plan bus with no
    # buses[].leaf / contents[].bind; the plan of record binds leaves only in the die bind (kit_rtl), not in the plan
    ("PLAN", r"^gen$", r"is not bound to any leaf port",
     "plan type has unbound buses and the kit took the plan wrapper: the die needs kit_rtl (bound partition RTL)"),
    # KIT-TRIAGE-1/G26 11-01 (QC cbf_q00/cbf_q11/cbn_q11): instances that differ ONLY in ID parameters (tile_id ...) are
    # one kit once the plan declares those leaf ports parent_id_straps (OWNER 10-25 option B: strap_* pins tied at the
    # parent, bind.py emit_type promotes them); any other parameter difference is the LOGIC value-set case below
    ("PLAN", r"^kit_rtl$", lambda s: id_only_param_diff(s),
     "per-instance ID parameters differ: plan declares parent_id_straps on those leaf ports (OWNER 10-25 B), rebind"),
    # DIE-QC-97 11-09 (QC sle_st_b_v1 / slw_st_b_v2 / slw_st_b_v1__cl6357f1cc: regenerated HI_PAD latency pads 30/29,
    # 29/28 per slice): instances that differ in a LOGIC parameter are different hardware, so no kit recipe can take one
    # value set for all of them.  The plan fix by construction: tools/die_plan/param_class_split.py splits the type into
    # one plan type per value set (T__pv<hash>, + clock-landing sidecar), rebind; generic kit-rtl then kits each.
    ("PLAN", r"^kit_rtl$", r"carry different parameters",
     "per-instance LOGIC parameters differ: split the plan type per value set (tools/die_plan/param_class_split.py), rebind"),
    # KIT-TRIAGE-1/G26 11-01 (9 S81 slice_station kit_rtl 'unclassified'): the strict bind of record names absolute HDL
    # sources in a lane worktree that was pruned / moved on; the kit_rtl script must point at the current bind
    ("FLOW", None, r"preferred HDL source missing",
     "kit-RTL bind of record names HDL sources that are gone (pruned bind worktree): point kit_rtl at the current strict bind"),
    # KIT-TRIAGE-1/G26 11-01 (HEAD hd_turn_a): the prepared HEAD cohort's published wrapper no longer matches what the
    # current gen emits for the type (e.g. HEAD-RINGHOLD-1 WFALL on a landing cascade): the die owner re-prepares
    ("PLAN", None, r"differs from published source cohort|published wrapper changed|prepared plan changed",
     "HEAD prepared cohort stale vs current gen (re-prepare / republish the type wrapper)"),
    ("FLOW", r"^place$", r"OT_CLAND no legal nonoverlapping row/site in reserved band",
     "clock-landing band too small or blocked (band plan, or tool: this kit already reads its pinslot setting from spec cland_pinslot)"),
    # AUTOBUILD-PIPE-4 10-31 (KV core kits qkd_hr_ingest_eng / qkd_hr_core_order): design-side preflight results that
    # fell into the FLOW buckets -- an SRAM core with no static macro sites (rtl_macro_placer only: the plan names no
    # macro rect / hard_children block) and a core whose synthesized faces are not registered (core_preflight
    # shared / feedthrough / unregistered ports = the core cut / face proof, not the kit flow)
    ("PLAN", None, r"no staged MACRO_PLACEMENT_TCL",
     "macro core has no static macro sites (plan core macro rects / hard_children block)"),
    ("PLAN", None, r"CORE_PREFLIGHT FAIL",
     "core faces not registered (CORE_PREFLIGHT shared/feedthrough/unregistered ports): core cut / RTL owner"),
    # KW-FIX-8 11-04 (S81 14 dsdv_slice_*_C rows 'unclassified', COORD 17:2x): yosys Tcl exec of native_bb stops on a signed
    # child's *_bb.v parameter default it cannot read, or on an override that differs from it (STA-0171): view/plan side, not flow
    ("PLAN", None, r"OT_SIGNED_PARAM_SERIALIZE ERROR",
     "signed child parameter override not provable against its *_bb.v header default (view or plan owner)"),
    ("FLOW", None, r"SYNTH_MEMORY_MAX_BITS|KIT_PREFLIGHT FAIL|preflight[^\n]*FAIL", "kit recipe / preflight"),
    # KIT-TRIAGE-1/G26 11-01 (KV qkd_hr_core_peer gen): a tool input path that does not exist (a cached views file /
    # recipe naming a removed lane worktree) is the flow's, and is named as such instead of a generic traceback
    ("FLOW", None, r"FileNotFoundError|No such file or directory", "tool input file missing (stale path / pruned worktree)"),
    ("FLOW", None, r"Traceback \(most recent call last\)|KeyError|TypeError|AttributeError|invalid command name|"
                   r"can't read \"|Error: .*\.tcl, \d+", "tool / Tcl error"),
]


ERROR_LINE = re.compile(r"Traceback \(most recent|^\w*(?:Error|Exception)\b|Error[: ]|ERROR|FAIL|KitError|S81_KIT_RTL|"
                        r"ot-run: NOT (?:RUN|COMPLETED)|Connection (?:reset|refused|closed)|kex_exchange|exit 137\b")


def preflight_advisory(text):
    """kit_preflight --out receipt text -> {check: {verdict, n, errors[:5]}} for every contract advisory that is not
    PASS/NA (OWNER 11-03 targets, not gates: a report, never a stop); {'unread': why} when the receipt is unreadable.
    A plan-less run ('no plan contents (pass --plan-dir)') is kept as it is: the wave always passes --plan-dir."""
    s = text or ""
    try:                                                 # the receipt is the one JSON object in the text (ssh chatter around)
        rec = json.loads(s[s.index("{"):s.rindex("}") + 1])
    except ValueError as e:
        return {"unread": f"receipt not JSON: {e}"[:200]}
    if not isinstance(rec, dict):
        return {"unread": "receipt is not an object"}
    out = {}
    for name, row in sorted((rec.get("contract_advisory") or {}).items()):
        if row.get("verdict") in ("PASS", "NA"):
            continue
        errs = row.get("errors") or []
        out[name] = {"verdict": row.get("verdict"), "n": int(row.get("n_errors") or len(errs)),
                     "errors": [str(e)[:300] for e in errs[:5]]}
    return out


def advisory_line(adv):
    """one summary line of preflight_advisory(): 'macro_pin_grid 6 (macro X ...); macro_channels 2 (...)' or ''"""
    if not adv:
        return ""
    if "unread" in adv:
        return "receipt unread: " + adv["unread"][:120]
    return "; ".join(f"{k} {v['n']} ({(v['errors'] or [''])[0][:140]})" for k, v in adv.items())[:600]


def error_lines(text, n=16):
    """the last n error-looking lines of a whole stage log: classify() reads these first, so a long log whose decisive
    line (a Python exception, FACE_GUARD FAIL) sits before the kept tail is still classified (AUTOBUILD-PIPE-1 10-30:
    13 'unclassified' gen/kit_rtl FAILs had their ValueError > 3000 chars before the end of the log)"""
    out = [ln.strip()[:600] for ln in (text or "").splitlines() if ERROR_LINE.search(ln)]
    return "\n".join(out[-n:])


# ot-run / ot-heavy admission and progress chatter: never the item's error (KIT-TRIAGE-1/G26 11-01: reasons read
# 'd on key-cardinal as oth-ubuntu-302855-... after 1 s Traceback ...' and hid the exception).  'RAN on ... exit N',
# 'NOT RUN', 'NOT COMPLETED' and 'SSH probe exit 255' stay: the INFRA rules read them.
ADMISSION = re.compile(r"^\s*(?:ot-run: (?:\S+\s+admits\b|-> |waiting\b|queued\b|wait\b)|"
                       r"ot-heavy: (?:admitted|request|waiting|queued|charged|wait)\b|KW_SSH_RETRY\b|"
                       # OWNER 11-03: an advisory check is never the item's error (KW6-CLASS 11-04: "pins_canonical check
                       # could not run: ModuleNotFoundError" hid a place failure on 3 rows)
                       r"KIT_PREFLIGHT ADVISORY\b|"
                       # KW-FIX-8 11-04: the kill of the pre-route LEC beside a stopped flow; its exit 137 read as INFRA and
                       # relaunched 9 KV rows on the same PDN-0006 / OT_CLAND error.  The flow's own error decides.
                       # KW-FIX-24 11-06: a pre-route LEC killed by a signal (docker stop / OOM) is no verdict either
                       r"LEC_ASYNC \S+ \S+ aborted (?:with its flow|by signal)\b)")
EXC_LINE = re.compile(r"^\s*(?:[A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt)(?::|$)|bind: ERROR|ERROR\b|Error:|"
                      r"[A-Z][A-Z0-9_]+ FAIL\b|FAIL_PREFLOOR\b)")
ID_PARAM = re.compile(r"(?:_id|_tid|sidx|map_lane_j)$")


def strip_admission(text):
    """the log without ot-run/ot-heavy admission/progress lines (classification + reasons read this)"""
    return "\n".join(ln for ln in (text or "").splitlines() if not ADMISSION.search(ln))


# KW43-77 11-10: a try that was NOT RUN (admission refused: 'ot-heavy: NOT RUN ...', 'ot-run: NOT RUN on epyc2: ot-heavy
# exit 75') and then retried, with the retry reporting 'ot-run: RAN on', is a superseded try, not the verdict.
# kv3_pv_v12 a25 / kv3_pv_v1 a10 failed FLOW (OT_CLAND) at 04:15/04:53; the 05:30 auto-rejudge re-read the whole
# place.log, met the earlier try's NOT RUN line before the CLAND rule and rewrote both rows to INFRA.
SUPERSEDED_TRY = re.compile(r"^\s*(?:ot-run|ot-heavy): NOT RUN\b")
RAN_LINE = re.compile(r"ot-run: RAN on \S+")


def drop_superseded_tries(text):
    """the text without NOT RUN lines that a later 'ot-run: RAN on' line supersedes (the retry ran: its result decides)"""
    lines = (text or "").splitlines()
    last = max((i for i, ln in enumerate(lines) if RAN_LINE.search(ln)), default=-1)
    return "\n".join(ln for i, ln in enumerate(lines) if i > last or not SUPERSEDED_TRY.search(ln))


def decisive_line(text):
    """the line that decides a failed stage: the last exception / ERROR / <CHECK> FAIL line of the (admission-free)
    log, else the last error-looking line, else the last non-empty line"""
    lines = [ln.strip() for ln in strip_admission(text).splitlines() if ln.strip()]
    exc = [ln for ln in lines if EXC_LINE.search(ln) and not ln.startswith(("Traceback", "File "))]
    if exc:
        return exc[-1]
    err = [ln for ln in lines if ERROR_LINE.search(ln) and not ln.startswith(("Traceback", "File ", "ot-run: RAN on"))]
    if err:
        return err[-1]
    rest = [ln for ln in lines if not ln.startswith("ot-run: RAN on")]
    return (rest or lines or [""])[-1]


def id_only_param_diff(text):
    """'instances of X carry different parameters [sets]' whose sets differ ONLY in ID parameters (tile_id, sidx, ...):
    -> the differing names joined, else None"""
    m = re.search(r"carry different parameters (\[.*?\])(?::|\s*$)", text or "", re.M | re.S)
    if not m:
        return None
    sets = [dict(re.findall(r"\.(\w+)\(([^()]*)\)", x)) for x in re.findall(r"#\((.*?)\)[\"']", m.group(1))]
    if len(sets) < 2:
        return None
    names = sorted({k for st in sets for k in st if len({st2.get(k) for st2 in sets}) > 1})
    if not names or not all(ID_PARAM.search(k) for k in names):
        return None
    return " ".join(names)


def _matched_line(s, m):
    a = s.rfind("\n", 0, m.start()) + 1
    b = s.find("\n", m.start())
    line = s[a:b if b >= 0 else len(s)].strip()
    if b >= 0 and m.end() > b + 1:                    # a multi-line rule: keep the matched block on one line
        line += " | " + s[b + 1:m.end()].strip().replace("\n", " | ")
    return line


def classify(stage, text):
    """-> (class, reason); never guesses INFRA for a design failure.  The rules read the error lines of the log first,
    then the whole log, both without ot-run admission chatter; the reason quotes the decisive error line (the matched
    line, or the exception line when the match is a bare Traceback / frame)"""
    raw = text or ""
    ran = re.search(r"ot-run: RAN on \S+", raw)
    clean = drop_superseded_tries(strip_admission(raw))
    views = (error_lines(clean), clean)
    for cls, st_re, tx_re, why in RULES:
        if st_re and not re.search(st_re, stage or ""):
            continue
        if cls == "INFRA-SSH":
            if ran:
                continue
            cls = "INFRA"
        for s in views:
            if callable(tx_re):
                hit = tx_re(s)
                if hit:
                    return cls, f"{why} @{stage}: {hit}"[:400]
                continue
            m = re.search(tx_re, s)
            if m:
                line = _matched_line(s, m)
                if not line or re.match(r"(?:Traceback|File |ot-run: RAN on)", line):
                    line = decisive_line(clean) or line
                return cls, f"{why} @{stage}: {line[:300]}"
    dl = decisive_line(clean)
    return "FLOW", f"unclassified failure @{stage} (see log)" + (f": {dl[:300]}" if dl else "")


# ------------------------------------------------------------------------------------------------ AUTO-GEOM verdict
FILL_ONLY = {"fill", "empty"}
# KIT-TRIAGE-1/G7 11-01 (CLASS FIX, default-on, every die): standing GEOM exceptions applied without per-item config.
# Each is a plan-given item (the slot outline / pin faces are the plan's), granted by intent (OWNER 12.28b fewer rules,
# closure first).  NA is never waived; every other failing rule (clock_reach, clock_tap_sinks, r2r, pin_reg, pin_unreg,
# grt, col_v ...) still gates.  {rule: (ruling ref, condition)}; condition 'outline_ok' = only while the measured outline
# equals the plan slot (outline=ok in the same line), i.e. the shape is provably the plan's.
STANDING_GEOM_EXCEPTIONS = {
    "partial_face": ("COORD RULING 2026-10-30 22:24 (a) + 11-01 00:07 (io_ft, 12.28b): partial_face = the plan's pin "
                     "form (pin_density still gates)", None),
    "aspect": ("COORD RULING 2026-10-31 03:35 (GEOM-87, by intent) + OWNER 12.28b: aspect of the plan slot outline "
               "(only with outline=ok)", "outline_ok"),
    # GEOM-111 class E 11-02: channel_h/channel_v/col_v are placement-density ESTIMATES; when the same record's measured
    # GRT converged with 0 overflow the measurement supersedes the estimate (route decides).  Any GRT overflow, a missing
    # GRT, or NA keeps them gating.
    "channel_h": ("GEOM-111 class E 11-02 (GEOM-110 18:24, GEOM-96 d44f bdring precedent, OWNER 12.28b): estimate-only congestion superseded by the same record's measured GRT at 0 overflow -- route decides (only with grt=ok(0))", "grt_zero"),
    "channel_v": ("GEOM-111 class E 11-02 (GEOM-110 18:24, GEOM-96 d44f bdring precedent, OWNER 12.28b): estimate-only congestion superseded by the same record's measured GRT at 0 overflow -- route decides (only with grt=ok(0))", "grt_zero"),
    "col_v": ("GEOM-111 class E 11-02 (GEOM-110 18:24, GEOM-96 d44f bdring precedent, OWNER 12.28b): estimate-only congestion superseded by the same record's measured GRT at 0 overflow -- route decides (only with grt=ok(0))", "grt_zero"),
}


def geom_verdict(line, waived=None, standing=True):
    """AP_AUTO_GEOM line (geom_rules.verdict_line) -> (PASS|PASS-COND|FAIL, failing rules, tag).
    OWNER standing rule 10-30 00:5x (via COORD): when fill/empty in the plan slot are the ONLY failing AUTO-GEOM items,
    the kit passes with tag FILL-EXCEPTION; with any other failing (or NA) rule -- clock_reach/tap_sinks, r2r, pin_reg,
    grt, slot fit ... -- it is classified as usual.
    KIT-TRIAGE-1/G7 11-01: the standing COORD exceptions STANDING_GEOM_EXCEPTIONS (partial_face; aspect with
    outline=ok) apply on every die without per-item config -> PASS-COND tagged 'GEOM-EXCEPTION <rules>: <refs>'."""
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
    outline_ok = re.search(r"(?:^|\s)outline=(?:ok|PASS)\(", line) is not None
    grt_zero = re.search(r"(?:^|\s)grt=(?:ok|PASS)\(0(?:\.0+)?\)", line) is not None
    for r, (ref, cond) in (STANDING_GEOM_EXCEPTIONS.items() if standing else ()):
        if r not in waived and (cond is None or (cond == "outline_ok" and outline_ok)
                                  or (cond == "grt_zero" and grt_zero)):
            waived[r] = (ref, None)
    na = set(re.findall(r"(?:^|\s)([A-Za-z0-9_]+)=NA\(", line))
    if failing and not na and set(failing) <= FILL_ONLY | set(waived):
        exc = [r for r in failing if r in waived]
        refs = []
        for r in exc:
            ref = waived[r][0] + (f" (<= {waived[r][1]:g})" if waived[r][1] is not None else "")
            if ref not in refs:
                refs.append(ref)
        fills = [r for r in failing if r in FILL_ONLY]
        return "PASS-COND", failing, ("GEOM-EXCEPTION " + ",".join(fills + exc) + ": " + "; ".join(
            refs + (["fill/empty = owner standing rule 10-30 00:45"] if fills else [])))
    return "FAIL", failing, ""


GEOM_ADVISORY_REF = "OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory)"


def geom_gate(line, waived=None, advisory=True):
    """KW-FIX-4 11-03: the wave's AUTO-GEOM gate.  geom_verdict() still judges the line; with advisory on (default,
    die opt geom_advisory false = the old hard gate) a FAIL with a verdict line passes as PASS-COND tagged
    'GEOM-ADVISORY <rules>' so the kit goes on to sign-off, which is the only blocking gate.  A missing verdict line
    stays FAIL (geom did not run)."""
    v, failing, tag = geom_verdict(line, waived)
    if v == "FAIL" and advisory and re.search(r"AUTO-GEOM (PASS|FAIL)\b", line or ""):
        na = sorted(set(re.findall(r"(?:^|\s)([A-Za-z0-9_]+)=NA\(", line)) - set(failing))
        return "PASS-COND", failing, ("GEOM-ADVISORY " + ",".join(failing + [f"{r}(NA)" for r in na]) + ": "
                                      + GEOM_ADVISORY_REF)
    return v, failing, tag


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
    # KIT-TRIAGE-1/G26 11-01 (KV qkd_hr_core_peer FileNotFoundError): the per-event views cache is keyed on the wave
    # src + plan, so a src bump never reuses views whose core json paths point into an older (pruned) src worktree
    views = c.get("views") or f"{root}/core_views.{hashlib.sha1(f'{src}|{plan}'.encode()).hexdigest()[:10]}.json"
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


ENV_KEY_RE, ENV_VAL_RE = re.compile(r"OT_[A-Z0-9_]+"), re.compile(r"[A-Za-z0-9_.,:=+-]*")


def topology_env_prefix(sp):
    """Forward the one opt-in native-topology selector, never arbitrary gen env."""
    env = sp.get("gen_env") or {}
    value = env.get("OT_NATIVE_RESET_SCOPE")
    capture = env.get("OT_NATIVE_PRODUCER_CONTEXT")
    if value is None:
        if capture is not None:
            raise ValueError("producer context needs OT_NATIVE_RESET_SCOPE=selected")
        return ""
    if value != "selected":
        raise ValueError("OT_NATIVE_RESET_SCOPE must be selected when provided")
    prefix = "OT_NATIVE_RESET_SCOPE=selected "
    if capture is not None:
        if not isinstance(capture, str) or not capture.startswith("/") or "\x00" in capture:
            raise ValueError("producer context must be an absolute file path")
        prefix += "OT_NATIVE_PRODUCER_CONTEXT=" + shlex.quote(capture) + " "
    return prefix


def item_env(d, item):
    """die item_env[item] -> {OT_*: value} (validated: OT_ names, shell-safe values; anything else raises)"""
    env = dict((d.get("item_env") or {}).get(item) or {})
    for k, v in env.items():
        capture_path = (k == "OT_NATIVE_PRODUCER_CONTEXT" and isinstance(v, str)
                        and re.fullmatch(r"/[A-Za-z0-9_./-]+", v))
        # OT_MACRO_MOVES names hard-core instances such as u_vp.g_ln[14].u_l: [ ] are the only extra characters, the value is
        # shell-quoted at its one consumer (export in run_item)
        moves = k == "OT_MACRO_MOVES" and bool(ENV_VAL_RE.fullmatch(str(v).replace("[", "").replace("]", "")))
        if not ENV_KEY_RE.fullmatch(str(k)) or not (ENV_VAL_RE.fullmatch(str(v)) or capture_path or moves):
            raise ValueError(f"item_env {item}: {k}={v!r} (OT_* names, safe values; producer context may be an absolute path)")
    if "OT_NATIVE_PRODUCER_CONTEXT" in env and env.get("OT_NATIVE_RESET_SCOPE") != "selected":
        raise ValueError("producer context needs OT_NATIVE_RESET_SCOPE=selected")
    return {str(k): str(v) for k, v in sorted(env.items())}


def capture_ot_run(cfg):
    """Resolve an explicit frontend only when capturing a new immutable spec."""
    chosen = cfg.get("ot_run")
    if chosen is None:
        return OT_RUN
    if not isinstance(chosen, str) or not Path(chosen).is_absolute():
        raise ValueError("kit-wave ot_run override must be an absolute executable path")
    if not Path(chosen).is_file() or not os.access(chosen, os.X_OK):
        raise ValueError("kit-wave ot_run override is not an existing executable: " + chosen)
    return chosen


def overlay_sha(path):
    """sha256 of a type-overlay file when readable here ('' otherwise), so a changed overlay is a changed input"""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def spec_for(cfg, die, item, hub, parent=None, kind="type"):
    d = cfg["dies"][die]
    root = f"{opt(cfg, die, 'work_root')}/{die}/{d['event']}"
    # KW-FIX-38 11-08 (COORD: HBM plan_final3 for 11 types only): die option item_inputs {item: {plan, kit_rtl: {...}}} builds
    # that item from its own plan and bind; row identity (block_sha, retry keys, counting) stays on the die plan
    item_in = (d.get("item_inputs") or {}).get(item) or {}
    # KW-FIX-45 11-11 (COORD: HBM opsb_group private src copy): item_inputs may also name src / src_sha / queue_src, so one
    # item builds from its own source tree (cp -al copy plus real copies of the approved files); the die src stays shared.
    item_kr = dict(d.get("kit_rtl") or {}, **(item_in.get("kit_rtl") or {})) if item_in.get("kit_rtl") else (d.get("kit_rtl") or {})
    return {"die": die, "item": item, "kind": kind, "event": d["event"], "plan": item_in.get("plan") or d["plan"],
            "gen_host": pick_gen_host(cfg, die, take=place_mem_gb(cfg, die, item),
                                      threads=int(opt(cfg, die, "place_threads")), item=item),
            "src": item_in.get("src") or d["src"], "src_sha": item_in.get("src_sha") or d.get("src_sha", ""), "src_base": d.get("src_base", ""), "src_overlay": d.get("_src_overlay", ""), "queue_src": item_in.get("queue_src") or d.get("queue_src", ""), "root": root, "work": f"{root}/items/{item}",
            "kit_rtl": item_kr,
            # KIT-OVERLAY-1: item_inputs {item: {type_overlay: <path>}} = positions-only intra-type overlay (type_overlay.py) on
            # the die plan of record; gen phys --type-overlay + the overlaid plan for station preparation.  Absent = unchanged.
            **({"type_overlay": str(item_in["type_overlay"]), "type_overlay_sha": overlay_sha(item_in["type_overlay"])}
               if item_in.get("type_overlay") else {}),
            # next captured cohort; old worker specs stay unchanged.  Die option canonical_topology_prepare false:
            # the die kit RTL is regenerated by gen.py phys from the same prepared plan (HEAD head_wave_kit_rtl
            # export: no bind.py manifest, no bind_out/bound_module), so no separate native bind can go stale.
            "canonical_topology_prepare": d.get("canonical_topology_prepare", True) is not False,
            # AUTOBUILD-PIPE-2: per-die hard-core generator (HBM gen_core_kit_hbm.py); kind=core items use it instead
            # of kit-rtl + gen.py phys.  {views_cmd, gen_cmd, runner, item_args{module: [...]}} (see core_kit_cmds)
            "core_kit": dict(d.get("core_kit") or {}, args=list((d.get("core_kit") or {}).get("args") or [])
                             + list(((d.get("core_kit") or {}).get("item_args") or {}).get(core_module(item)) or []))
                        if d.get("core_kit") else {},
            # die option item_env {item: {OT_*: value}}: generation environment of that item's gen.py phys
            # OT_NATIVE_RESET_SCOPE alone is also forwarded to canonical topology preparation.
            # (e.g. OT_IO_HOLD=sender_min, a die-owner input-hold contract ruling on one type; plan clock.io_hold wins)
            # KW-FIX-30 11-07 (COORD 15:01 (b)): die option flow_tag -> OT_FLOW_TAG in the gen env (gen.py phys writes K/flow_tag,
            # run_kit.sh passes it to the GRT clock gate); an item_env OT_FLOW_TAG wins.  Unset = as before.
            "gen_env": ({"OT_FLOW_TAG": str(d["flow_tag"])} if d.get("flow_tag") else {}) | item_env(d, item),
            "gen_args": list(d.get("gen_args") or []) + list((d.get("type_args") or {}).get(item) or [])
                        + (["--hard-wrappers", item] if item in (d.get("hard_wrappers") or []) else []),
            # default --contract; an explicit [] (die config) = the plain kit preflight the autopilot submit runs
            "preflight_args": list(["--contract"] if d.get("preflight_args") is None else d["preflight_args"]),
            "geom_waivers": geom_waivers(d, item, parent),
            # COORD 10-30 23:1x (GEOM-84 ring key order): every wave kit places landing-ring slot flops in pin order
            # (gen phys --cland-pinslot; a kit without ring bands is unchanged).  Die opt-out: cland_pinslot false.
            "cland_pinslot": cland_pinslot_arg(d),
            "hosts": [h for h in opt(cfg, die, "hosts")], "hub": hub, "place_prefer": list(opt(cfg, die, "place_prefer") or []),
            "place_mem_gb": place_mem_gb(cfg, die, item), "place_threads": int(opt(cfg, die, "place_threads")),
            "geom_mem_gb": int(opt(cfg, die, "geom_mem_gb")), "geom_grt_wall_s": int(opt(cfg, die, "geom_grt_wall_s")), "gen_mem_gb": int(opt(cfg, die, "gen_mem_gb")),
            # A measured large elaboration can override its own lint container
            # and matching ot-run admission without raising every kit's budget.
            "lint_mem_gb": int((d.get("lint_mem_gb_by_item") or {}).get(item, opt(cfg, die, "lint_mem_gb"))),
            "geom_advisory": opt(cfg, die, "geom_advisory") is not False,
            "place_spill": bool(opt(cfg, die, "place_spill") if opt(cfg, die, "place_spill") is not None else True),
            "relay_bay_re": (d["relay_bay_re"] if "relay_bay_re" in d else RELAY_BAY_RE.get(die, "")) if kind == "type" else "",
            "prov_first_re": (d.get("prov_first_re") or "") if kind == "type" else "",
            "bind_mem_gb": int(opt(cfg, die, "bind_mem_gb")), "ot_run": capture_ot_run(cfg),
            "crit": near_count_hit(cfg.get("_near_count") or set(), die, item, parent, core_module(item))} \
        | ({"kit_store": True} if kit_store_on(cfg, die, item) else {}) \
        | ({"cell_check": True} if d.get("cell_check") and kind == "type" else {})  # PLAN-GEN-RULES-1 rule C (advisory)


# ------------------------------------------------------------------------------------------------ KW-PROV-1 provisional views
PROV_MAX_CANDS = 3


def prov_job_module(j, mods):
    """module of `mods` an autopilot job built: its type, or a core view item '<module>__v<sha12>'"""
    t = str(j.get("type") or "")
    if t in mods:
        return t
    m = CORE_VIEW.match(t)
    return m.group("module") if m and m.group("module") in mods else None


def prov_counted(c):
    """KW-FIX-35-V 11-08: a prov_view_sources candidate that is the COUNTED signed view of the child (exported by
    counted_child_views.py / export_view.py from the counter's own sign-off record: job 'COUNTED <module> ...', or an
    explicit counted: true).  prov_view.py make still checks pins / libs and the export gates.json before it marks the
    child FINAL."""
    return bool(c.get("counted")) or str(c.get("job") or "").startswith("COUNTED ")


def prov_sources(jobs, die, modules, d=None, hub="intel2"):
    """{module: [candidate]} routed DRC-clean abstracts of each child module, best first: die option
    prov_view_sources {module: [{host, dir[, base]}]} (die owner pick: dir holds <m>_tt.lib, <m>_ff.lib, <m>.lef) first, then autopilot queue jobs of the die whose
    newest sign-off record has DRC 0 (routed; timing may still fail -- the abstract is provisional), newest first.
    candidate = {host, dir (sign-off dir holding <m>_tt.lib/_ff.lib/<m>.lef), base (routed results dir), job, ...}.
    Optional candidate fields detailed_lef, detailed_receipt and detail_bloat_factor stage an already exported
    precise abstract plus its hash/pin splice receipt; paths may be relative to dir. No hidden export or P&R.
    The files are checked against the plan pins on the gen host (prov_view.py make); a candidate that fails falls
    through to the next, then to the plan-contract abstract."""
    mods = set(modules)
    out = {m: [] for m in modules}
    for m, lst in ((d or {}).get("prov_view_sources") or {}).items():
        if m in mods:
            for c in lst if isinstance(lst, list) else [lst]:
                out[m].append(dict(c, job=c.get("job") or "die-config prov_view_sources"))
    cands = []
    for j in (jobs or {}).values():
        if j.get("die") != die or not isinstance(j.get("signoff"), dict):
            continue
        m = prov_job_module(j, mods)
        so = j["signoff"]
        if not m or not so.get("path") or so.get("drc") is None or int(so.get("drc") or 0) != 0:
            continue
        kit = str(j.get("kit") or "")
        host = j.get("ran_on") or (kit.split(":", 1)[0] if ":" in kit else j.get("host")) or hub
        cands.append((m, float(j.get("finished") or j.get("updated") or 0), dict(
            host=hub if host == "localhost" else host, dir=os.path.dirname(so["path"]), base=so.get("base") or "",
            job=j.get("id"), status=j.get("status"), drc=0, tt_wns=so.get("tt_wns"), ff_wns=so.get("ff_wns"),
            signoff=so["path"])))
    for m, _t, c in sorted(cands, key=lambda x: -x[1]):
        if len(out[m]) < PROV_MAX_CANDS:
            out[m].append(c)
    return out


def prov_predecessor(d, die, state, item, cur=None):
    """key of a live PROVISIONAL record of die/item whose type entry is unchanged apart from its children's lef/lib
    (prov_key): the plan now binds the signed child view -> new block sha, but the kit is re-signed, not rebuilt.
    A re-sign that failed (RE-ROUTE / FAIL) or a queue FAIL releases the normal rebuild."""
    pk = (d.get("_prov_keys") or {}).get(item)
    if not pk or not prov_on(d):
        return None
    for key, rec in (state.get("items") or {}).items():
        if rec is cur or rec.get("die") != die or rec.get("item") != item or not rec.get("provisional") or rec.get("arm"):
            continue
        rs = (rec.get("prov_resign") or {}).get("status")
        if (rec.get("prov_key") == pk and rec.get("status") in ("RUNNING", "LAUNCHING", "PASS", "ENQUEUED")
                and rec.get("q_status") != "FAIL" and rs not in ("FAIL", "RE-ROUTE")):
            return key
    return None


def prov_spec(AP, d, die, item, hub):
    """launch spec part of a PROVISIONAL item: {modules: [...], cands: {module: [candidate]}}"""
    mods = list((d.get("_prov_deps") or {}).get(item) or (d.get("_plan_deps") or {}).get(item) or [])
    try:
        jobs = json.loads((Path(AP.AP_DIR) / "state.json").read_text()).get("jobs") or {}
    except (OSError, ValueError):
        jobs = {}
    return {"modules": mods, "cands": prov_sources(jobs, die, mods, d, hub)}


def prov_missing_cands(spec):
    """KW-FIX-45 11-11: child modules of a PROVISIONAL launch spec with no routed candidate view ({modules, cands});
    die option prov_require_cands true turns a launch with such a child into a wait (it would fail PLAN at prov_views)"""
    cands = (spec or {}).get("cands") or {}
    return [m for m in (spec or {}).get("modules") or [] if not cands.get(m)]


def prov_tb_last(txt):
    """the exception line closing the last Python traceback in txt ('' when there is none)"""
    ls = (txt or "").splitlines()
    i = max((k for k, ln in enumerate(ls) if ln.startswith("Traceback (most recent call last)")), default=-1)
    if i < 0:
        return ""
    tail = [ln for ln in ls[i + 1:] if ln.strip() and not ln.startswith((" ", "\t", "PROV_JSON "))]
    return tail[-1].strip()[:300] if tail else ""


def prov_stage(sp, run, remote, fail, out, rtl=""):
    """run_item stage: stage prov_view.py + routed candidate files on the gen host, build the provisional views and the
    overlay plan -> (overlay plan path, {module: source}) or (None, fail rc)"""
    q = shlex.quote
    G, hub, W, T = sp["gen_host"], sp["hub"], sp["work"], sp["item"]
    pv = sp["prov_views"]
    P = f"{W}/prov"
    on_hub = G in ("localhost", hub)
    rc, txt = run("prov_dir", remote(f"rm -rf {q(P)} && mkdir -p {q(P)}/routed"), idempotent=True)
    if rc:
        return None, fail("prov_views", txt)
    tool = Path(__file__).resolve().with_name("prov_view.py")
    SSH = "ssh -o BatchMode=yes -o ControlPath=none"
    rc, txt = run("prov_tool", ["rsync", "-a", "-e", SSH, str(tool), (P + "/") if on_hub else f"{G}:{P}/"],
                  idempotent=True)
    if rc:
        return None, fail("prov_views", txt)
    # routed candidates: candidate host -> hub relay (W/prov_relay on the hub) -> gen host W/prov/routed/<m>/c<i>/
    relay = Path(f"{W}/prov_relay")
    fetched = 0
    for m, cands in sorted((pv.get("cands") or {}).items()):
        for i, c in enumerate(cands):
            dst = relay / m / f"c{i}"
            dst.mkdir(parents=True, exist_ok=True)
            counted = prov_counted(c)
            files = [f"{c['dir']}/{m}_tt.lib", f"{c['dir']}/{m}_ff.lib", f"{c['dir']}/{m}.lef"] + (
                [f"{c['base']}/{m}.lef"] if c.get("base") else []) + (
                [f"{c['dir']}/gates.json", f"{c['dir']}/provenance.json",
                 f"{c['dir']}/landing_evidence"] if counted else [])   # KW-FIX-40 (QC-TYPES-10 11-08 class N): hard_landing reads it beside the LEF
            for f in files:
                if (dst / os.path.basename(f)).exists():
                    continue
                srcf = f if c["host"] in ("localhost", hub) else f"{c['host']}:{f}"
                subprocess.run(["rsync", "-a", "-e", SSH, srcf, str(dst) + "/"], capture_output=True, timeout=900)
            # Explicit already-exported precise abstract; no hidden OpenROAD work in the provisional stage.
            # Fixed staging names avoid a detailed source named <module>.lef overwriting the captured base.
            staged = dict(c)
            if counted:
                staged["counted"] = True     # KW-FIX-35-V: prov_view.py make takes it as the FINAL signed view
            for key, name in (("detailed_lef", "detail_view.lef"), ("detailed_receipt", "detail_receipt.json")):
                if isinstance(c.get(key), str) and c[key]:
                    f = c[key] if os.path.isabs(c[key]) else os.path.join(c["dir"], c[key])
                    srcf = f if c["host"] in ("localhost", hub) else f"{c['host']}:{f}"
                    subprocess.run(["rsync", "-a", "-e", SSH, srcf, str(dst / name)],
                                   capture_output=True, timeout=900)
                    staged["source_" + key] = c[key]
                    staged[key] = name
            (dst / "meta.json").write_text(json.dumps(staged))
            fetched += 1
    if fetched:
        rc, txt = run("prov_relay", ["rsync", "-a", "-e", SSH, str(relay) + "/",
                                     (P + "/routed/") if on_hub else f"{G}:{P}/routed/"], idempotent=True)
        if rc:
            return None, fail("prov_views", txt)
    rc, txt = run("prov_views", remote(f"python3 -I {q(P)}/prov_view.py make --plan {q(sp['plan'])} --type {q(T)} "
                                       f"--out {q(P)} --src {q(sp['src'])} --routed {q(P)}/routed"
                                       + (f" --rtl {q(rtl)}" if rtl else "")))
    js = next((json.loads(ln[9:]) for ln in reversed(txt.splitlines()) if ln.startswith("PROV_JSON ")), None)
    if rc or not js or not js.get("ok"):
        # WAVE-OPS-1 11-10 (COORD, HBM-CORES-B): a prov_view crash says what crashed (last traceback line)
        tb = prov_tb_last(txt)
        return None, fail("prov_views", (f"PROVISIONAL view FAIL (KW-PROV-1): prov_view.py crashed on {T}: {tb}\n"
                                         if tb else "PROVISIONAL view FAIL (KW-PROV-1): no provisional abstract for a "
                                         f"child of {T}\n") + txt, f"{G}:{P}")
    out["provisional"] = js.get("children") or {}
    out["prov_status"] = js.get("status") or "PROVISIONAL"
    return js["overlay_plan"], 0


def prov_census(AP, cfg, st):
    """{die: {types, routed, contract, children, children_routed}}: the current plan's WAIT-DEP types (noview / planned
    children) that launch on provisional views; routed = every child has a routed DRC-clean candidate (the plan-pin
    check runs at launch, a rejected candidate falls back to the contract abstract)"""
    try:
        jobs = json.loads((Path(AP.AP_DIR) / "state.json").read_text()).get("jobs") or {}
    except (OSError, ValueError):
        jobs = {}
    out = {}
    for die, d in sorted((cfg.get("dies") or {}).items()):
        if not isinstance(d, dict) or not d.get("plan"):
            continue
        try:
            pn = plan_names(AP, st, d)
        except Exception as e:                           # one unreadable plan never hides the other dies
            out[die] = {"error": f"probe {type(e).__name__} "}
            continue
        if pn.get("error"):
            out[die] = {"error": f"probe {pn['error'][:80]} "}
            continue
        d["_plan_flags"] = pn.get("flags") or {}
        pdeps = pn.get("prov_deps") or {}
        types = sorted(t for t in d["_plan_flags"] if prov_item(d, t))
        mods = sorted({m for t in types for m in pdeps.get(t) or []})
        srcs = prov_sources(jobs, die, mods, d, AP.HUB_NAME)
        routed = [t for t in types if pdeps.get(t) and all(srcs.get(m) for m in pdeps[t])]
        part = [t for t in types if t not in routed and any(srcs.get(m) for m in pdeps.get(t) or [])]
        out[die] = {"types": len(types), "routed": len(routed), "contract": len(types) - len(routed), "mixed": len(part),
                    "children": len(mods), "children_routed": sum(1 for m in mods if srcs.get(m)),
                    "routed_types": routed, "contract_children": [m for m in mods if not srcs.get(m)]}
    return out


def prov_abs(plan_dir, f):
    return f if not f or os.path.isabs(f) else os.path.normpath(os.path.join(plan_dir, f))


def prov_resign_due(cfg, st, jobs):
    """[(key, rec, {module: {lef, tt, ff}}, kit host)] PROVISIONAL kits whose children the plan of record now binds
    (signed lef + lib), whose queue job routed + signed off locally (WAIT-PARENT on the provisional marker) and whose
    type entry is otherwise unchanged (prov_key) -> STA-only re-sign on the final libs (KW-PROV-1)"""
    out = []
    for key, rec in (st.get("items") or {}).items():
        if not rec.get("provisional") or (rec.get("prov_resign") or {}).get("status"):
            continue
        if rec.get("status") != "ENQUEUED" or rec.get("q_status") != "WAIT-PARENT":
            continue
        d = (cfg.get("dies") or {}).get(rec.get("die")) or {}
        bound = d.get("_prov_bound") or {}
        if not prov_on(d) or not all(m in bound for m in rec["provisional"]):
            continue
        if rec.get("prov_key") and (d.get("_prov_keys") or {}).get(rec["item"]) not in (None, rec["prov_key"]):
            continue                                     # the type itself changed: the normal rebuild owns it
        pdir = d.get("_plan_dir") or os.path.dirname(str(d.get("plan") or ""))
        ch = {}
        for m in rec["provisional"]:
            tt = prov_abs(pdir, bound[m]["lib"])
            ff = re.sub(r"_tt(\.lib(?:\.gz)?)$", r"_ff\1", tt)
            ch[m] = {"lef": prov_abs(pdir, bound[m]["lef"]), "tt": tt, "ff": ff}
        j = (jobs or {}).get(rec.get("q_id")) or {}
        g, _, kp = str(rec.get("kit") or "").partition(":")
        host = j.get("ran_on") or g
        out.append((key, rec, ch, host, kp))
    return out


def prov_resign_step(AP, cfg, st, notices, ap_dir, hub):
    """tick: launch due re-signs (one systemd unit each: kit_wave.py prov-resign SPEC) and collect finished ones"""
    try:
        jobs = json.loads((Path(ap_dir) / "state.json").read_text()).get("jobs") or {}
    except (OSError, ValueError):
        jobs = {}
    for key, rec in (st.get("items") or {}).items():
        pr = rec.get("prov_resign") or {}
        if pr.get("status") != "RUNNING" or AP.unit_active(pr.get("unit", "")):
            continue
        try:
            r = json.loads((Path(pr["dir"]) / "result.json").read_text())
        except (OSError, ValueError, KeyError):
            r = {"status": "FAIL", "tail": "prov-resign unit ended without result.json"}
        pr.update(status=r.get("status") or "FAIL", tail=str(r.get("tail") or "")[-600:], updated=time.time())
        notices.setdefault(rec["die"], []).append(
            f"{rec['item']} PROVISIONAL re-sign {pr['status']} (KW-PROV-1; "
            + ("autopilot re-probes the new sign-off" if pr["status"] == "PASS" else
               "RE-ROUTE: signed child abstract differs, normal rebuild released" if pr["status"] == "RE-ROUTE" else
               "STA re-sign FAIL: late-ECO / stage-resume loop") + f") {pr.get('dir')}")
        AP.log(f"KIT-WAVE PROV-RESIGN {rec['die']}/{rec['item']} {pr['status']}")
    for key, rec, ch, host, kp in prov_resign_due(cfg, st, jobs):
        d = cfg["dies"][rec["die"]]
        gh = d.get("gen_host") or hub
        jd = Path(rec["dir"]).parent / f"resign{int(time.time())}"
        sp = {"key": key, "die": rec["die"], "item": rec["item"], "plan_host": gh, "kit_host": host, "kit": kp,
              "children": ch, "hub": hub, "ot_run": capture_ot_run(cfg), "image": d.get("prov_resign_image") or ""}
        unit = f"kw-prs-{re.sub(r'[^A-Za-z0-9]', '', rec['item'])[:28]}-{int(time.time()) % 100000}"
        if AP.DRY:
            AP.log(f"KIT-WAVE would PROV-RESIGN {rec['die']}/{rec['item']} kit {host}:{kp}")
            continue
        jd.mkdir(parents=True, exist_ok=True)
        (jd / "spec.json").write_text(json.dumps(sp, indent=1))
        ok = AP.launch_unit(unit, jd / "unit.log", ["python3", str(Path(__file__).resolve()), "prov-resign",
                                                     str(jd / "spec.json")])
        rec["prov_resign"] = {"status": "RUNNING" if ok else "FAIL", "unit": unit, "dir": str(jd), "started": time.time()}
        notices.setdefault(rec["die"], []).append(f"{rec['item']} PROVISIONAL children signed -> STA-only re-sign "
                                                  f"({unit}, KW-PROV-1)")


def prov_resign_run(spec_path):
    """worker: relay the signed child views (plan host) to the kit host, run prov_view.py resign there under ot-run"""
    sp = json.loads(Path(spec_path).read_text())
    jd = Path(spec_path).parent
    hub, H, K = sp["hub"], sp["kit_host"], sp["kit"]
    SSH = "ssh -o BatchMode=yes -o ControlPath=none"
    q = shlex.quote
    res = {"status": "FAIL", "t0": time.time()}

    def at(host, path):
        return path if host in ("localhost", hub) else f"{host}:{path}"

    def done(status, tail):
        res.update(status=status, tail=tail[-3000:], t1=time.time())
        (jd / "result.json").write_text(json.dumps(res, indent=1))
        return 0 if status == "PASS" else 1

    D = f"{K}/prov_final"
    log = []
    rem = (lambda c: ["bash", "-c", c]) if H in ("localhost", hub) else (lambda c: _ssh(H, hub) + ["bash -c " + q(c)])
    p = subprocess.run(rem(f"mkdir -p {q(D)}"), capture_output=True, text=True, timeout=300)
    if p.returncode:
        return done("FAIL", p.stdout + p.stderr)
    args = []
    for m, f in sorted(sp["children"].items()):
        loc = jd / "views" / m
        loc.mkdir(parents=True, exist_ok=True)
        for k in ("lef", "tt", "ff"):
            p = subprocess.run(["rsync", "-a", "-e", SSH, at(sp["plan_host"], f[k]), str(loc) + "/"],
                               capture_output=True, text=True, timeout=900)
            if p.returncode:
                return done("FAIL", f"relay {m} {k} {f[k]}: " + p.stderr)
        args.append(f"--child {q(m + '=' + ','.join(D + '/' + m + '/' + os.path.basename(f[k]) for k in ('lef', 'tt', 'ff')))}")
    tool = Path(__file__).resolve().with_name("prov_view.py")
    for src, dst in ((str(jd / "views") + "/", D + "/"), (str(tool), D + "/")):
        p = subprocess.run(["rsync", "-a", "-e", SSH, src, at(H, dst)], capture_output=True, text=True, timeout=900)
        if p.returncode:
            return done("FAIL", "relay to kit host: " + p.stderr)
    cmd = (f"python3 -I {q(D)}/prov_view.py resign --kit {q(K)} " + " ".join(args)
           + (f" --image {q(sp['image'])}" if sp.get("image") else ""))
    argv = [sp["ot_run"], "--mem", "16", "--threads", "4", "--dir", K, "--hosts",
            "localhost" if H == hub else H, "--", "bash", "-c", cmd]
    p = subprocess.run(argv, capture_output=True, text=True)
    txt = (p.stdout or "") + (p.stderr or "")
    log.append(txt)
    if "PROV_RESIGN REROUTE" in txt:
        return done("RE-ROUTE", txt)
    return done("PASS" if p.returncode == 0 else "FAIL", txt)


GEN_DISK_MIN_GB = 60      # KW-FIX-24 11-06 (COORD 16:2x): cfg gen_disk_min_gb; 0 turns it off


def gen_disk_low(v, floor=None):
    """KW-FIX-24 11-06 (COORD 16:2x: epyc6 scratch2 44 GB, ot-run REFUSED): an ot-run status row whose scratch disk
    has < gen_disk_min_gb free -- no new or restaged attempt goes there while another gen host has room"""
    floor = GEN_DISK_MIN_GB if floor is None else floor
    return bool(v) and floor > 0 and v.get("scratch_gb") is not None and int(v["scratch_gb"]) < floor


def host_score(v, disk_low=None):
    """ot-run --status row -> preference (higher first): free admits MINUS the GB already waiting there (KW-FIX-4 11-03,
    COORD 12:1x FLEET: raw admits sent every burst to epyc4 while 131 waiters / 1359 GB queued there and intel1 had 0),
    a positive score discounted 4x on a host already >= 0.9 x cores.  A host under the gen disk floor (gen_disk_low)
    ranks below every host with room (KW-FIX-24)."""
    if not v:
        return -1e9
    if (gen_disk_low(v) if disk_low is None else disk_low):
        return -1e8 + int(v.get("scratch_gb") or 0)
    busy = float(v.get("load", 0)) >= 0.9 * max(1, int(v.get("cores") or 1))
    s = float(v.get("admit", 0)) - float(v.get("wait_gb", 0))
    return s * 0.25 if (busy and s > 0) else s


def gen_hosts(cfg, die, item=None):
    """KW-FIX-4 11-03 (COORD epyc4 fill): die option gen_hosts = hosts that hold the die's src/plan/kit_rtl inputs at
    the SAME paths; a new attempt generates, stages and (async) PLACEs on the one with the most free ot-run admits, so
    a fresh host fills instead of every kit pinning to the one configured gen host.  Default: [gen_host] (unchanged).
    KW-FIX-35-RD 11-08: with item, a host that lacks one of that item's own inputs (item_env / type_args paths,
    cfg _item_incomplete) is left out while another host stays."""
    d = cfg["dies"][die]
    hs = [h for h in (d.get("gen_hosts") or []) if h]
    hs = hs if d.get("gen_host") in hs else [d["gen_host"]] + hs
    # KW-FIX-4 11-03 (COORD 14:2x INFRA class 2): a host whose die lane root carries an ot-run SPILL marker treats
    # every --dir under it as a stale copy (ot-run probe NODIR -> "NOT RUN: no host qualifies"), although the wave's
    # mkdir made the attempt dir there: such a host is no gen host for the die.  KW-FIX-8 11-04: this holds for the
    # configured gen_host too while another host stays (QC 11:09, KV 06:12 lost a batch on it); with none left the list
    # keeps the configured host and work_root_problem() turns the die's launches off with the reason
    marked = cfg.get("_spill_marked") or {}
    lane = lane_root(opt(cfg, die, "work_root"))
    bad = cfg.get("_src_incomplete") or {}
    # KW-FIX-30 11-07 (COORD 13:21): a host whose disk under the die's work_root is under the gen floor
    # (workroot_low) is no gen host for the die while another host stays; with none left the list is as before and
    # load_hold() holds the die's new rows
    low = cfg.get("_workroot_low") or {}
    imiss = cfg.get("_item_incomplete") or {}
    if item:
        hs = [h for h in hs if item not in (imiss.get(h) or {}).get(die, {})
              and core_module(item) not in (imiss.get(h) or {}).get(die, {})] or hs   # WAVE-OPS-1: core_kit.item_args
    return ([h for h in hs if lane not in marked.get(h, ()) and die not in bad.get(h, {}) and die not in low.get(h, {})]
            or [h for h in hs if lane not in marked.get(h, ()) and die not in bad.get(h, {})]
            or [h for h in hs if lane not in marked.get(h, ())] or [d["gen_host"]])


# KW-FIX-24 11-06 (COORD 19:2x (5) stale-source class): a gen host whose copy of a die's src tree or plan dir is
# incomplete (a prune removed 46k files of kw21/src_c926f on intel1 -> kit_rtl "can't open tools/die_plan/bind.py";
# d44v35 cut to 3 files -> views FileNotFoundError; the KV plan dir cut to 2 files on the hub) is no gen host for
# that die.  Per tick, one ssh per gen host counts the files of each input tree (src to SRC_PROBE_DEPTH, the plan dir
# whole) and tests the required files; a host whose count is below SRC_MIN_FRAC of the best copy on any host, or
# that lacks a required file, is dropped from the die's gen_hosts (logged SRC-INCOMPLETE).  An unreachable host is
# unknown, never dropped.  Die or global option src_probe: false turns it off.
SRC_PROBE_DEPTH = 3
SRC_MIN_FRAC = 0.99
SRC_REQUIRED = ("tools/die_plan/bind.py",)


def src_inputs(cfg, die):
    """([input tree dirs], [required files]) of a die: its src (to SRC_PROBE_DEPTH) and plan dir, the plan file and
    the src tools every kit_rtl / bind step runs"""
    d = cfg["dies"][die]
    src, plan = str(d.get("src") or ""), str(d.get("plan") or "")
    trees = [t for t in (src, os.path.dirname(plan)) if t]
    files = ([plan] if plan else []) + [os.path.join(src, r) for r in SRC_REQUIRED if src]
    # the kit-RTL inputs: asbuilt / script, and every HDL source the strict bind of record names (bind_out/bind.f,
    # read on the hub; KV 19:16 kit_rtl "preferred HDL source missing" = bind sources in a pruned src copy)
    kr = d.get("kit_rtl") if isinstance(d.get("kit_rtl"), dict) else {}
    files += [str(kr[k]) for k in ("asbuilt", "script") if str(kr.get(k) or "").startswith("/")]
    if str(kr.get("bind_out") or "").startswith("/"):
        try:
            with open(os.path.join(str(kr["bind_out"]), "bind.f")) as f:
                files += [ln.strip() for ln in f if ln.strip().startswith("/") and " " not in ln.strip()]
        except OSError:
            pass
    return trees, files


# KW-FIX-35-RD 11-08 (COORD 09:4x RESTAGE-DEPS): 23 S81 rows restaged / generated on epyc6 failed kit_rtl with
# FileNotFoundError die-s81-70/kvov/bind/bind_report.json.  The kit_rtl script (kw35/t45ov wrapper) exports
# S81_BIND_OUT=die-s81-70/kvov/bind, a symlink tree into codex-wave-bind-1106/s81_emitted_v2 + s81_ready_v3, absent on
# epyc6; the probe tested only the script file itself.  The same day 18 HBM rows failed on epyc6 because the bind_x2
# bind.f (read on the hub, where bind_x2 does not exist) named composed_rtl files only on epyc4.  DEEP inputs are
# therefore checked ON EACH GEN HOST: every absolute path in kit_rtl (script, asbuilt, bind_out, ...), gen_args and the
# /srv paths a kit_rtl .sh script names (one level), each resolved there (test -e follows links), a directory also
# for broken symlinks below it (find -L, under a lane sub-dir only) and for every absolute source its bind.f names.  item_env / type_args paths
# are the item's own inputs: a host missing one is no gen host for that item (cfg _item_incomplete).
DEEP_LINK_DEPTH = 4
ABS_RE = re.compile(r"(?:^|(?<=[\s=,:]))(/[A-Za-z0-9_.+-][^\s\"',;:=()$]*)")


def abs_paths(v):
    """absolute paths in a config value (str / list / dict values), e.g. --clock-landing /x.json, OT_X=/y"""
    out = []
    if isinstance(v, str):
        out += [m.rstrip(".") for m in ABS_RE.findall(v) if len(m) > 1]
    elif isinstance(v, dict):
        for x in v.values():
            out += abs_paths(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            out += abs_paths(x)
    return out


def deep_inputs(cfg, die):
    """the die's absolute kit_rtl / gen_args inputs, checked on each gen host (see _deep_probe_cmd)"""
    d = cfg["dies"][die]
    kr = d.get("kit_rtl") if isinstance(d.get("kit_rtl"), dict) else {}
    ps = abs_paths({k: v for k, v in kr.items() if not str(k).startswith("note")}) + abs_paths(d.get("gen_args") or [])
    ck = d.get("core_kit") if isinstance(d.get("core_kit"), dict) else {}
    ps += abs_paths(ck.get("args") or [])            # WAVE-OPS-1 11-10: die-wide core kit args (every core reads them)
    return list(dict.fromkeys(ps))


def item_inputs(cfg, die):
    """{item: [absolute paths]} named by the die's item_env, type_args and item_inputs ({plan, kit_rtl{...}}) for that
    item.  KW-FIX-44 11-10 (COORD, t42 bind10_ctap): item_inputs was not probed, so an item's own kit_rtl script (and the
    bind dir it names) could be absent on a gen host the probe passed"""
    d = cfg["dies"][die]
    out = {}
    for key in ("item_env", "type_args", "item_inputs"):
        for item, v in ((d.get(key) or {}) if isinstance(d.get(key), dict) else {}).items():
            if isinstance(v, dict):
                v = {k: x for k, x in v.items() if not str(k).startswith("note")}
            ps = abs_paths(v)
            # WAVE-OPS-1 11-10 (COORD, HBM-CORES-B q_hub_ne/epyc8): the plan's dir too (its pins_file / views are
            # relative to it); the deep probe samples one pins_file of each probed plan json (ckp)
            pl = v.get("plan") if key == "item_inputs" and isinstance(v, dict) else None
            if isinstance(pl, str) and pl.startswith("/") and pl.endswith((".json", ".json.gz")):
                ps.append(os.path.dirname(pl))
            if ps:
                out.setdefault(item, [])
                out[item] += [p for p in ps if p not in out[item]]
    # WAVE-OPS-1 11-10 (COORD, HBM-CORES-B svgr_top/epyc4 p6_relay/core_clock_regions.json): per-core kit args
    # (core_kit.item_args {core module: [...]}, e.g. --clock-regions <json>) are that core's own inputs too
    ck = d.get("core_kit") if isinstance(d.get("core_kit"), dict) else {}
    for mod, v in ((ck.get("item_args") or {}) if isinstance(ck.get("item_args"), dict) else {}).items():
        ps = abs_paths(v)
        if ps:
            out.setdefault(mod, [])
            out[mod] += [p for p in ps if p not in out[mod]]
    return out


# KW-FIX-44 11-10 (COORD, KV kv3_pv batch 'preferred HDL source missing'): an as-built json (kit_rtl asbuilt, or one a
# kit_rtl script names) points the bind at a source tree by 'base' + relative files / prefer / netlist / rtl_roots; on
# epyc8 kw32/src_27db6 was a 15-file stub, so the bind failed on 45 files the probe never looked at.  Each listed path
# is tested on the host (python3 there; first 3 missing reported as D lines).
_ASBUILT_PY = """import json, os, sys
p, lab = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(p))
except Exception:
    sys.exit(0)
b = d.get("base") if isinstance(d, dict) else None
n = 0
if isinstance(b, str) and b.startswith("/"):
    for k in ("files", "prefer", "netlist", "rtl_roots"):
        v = d.get(k)
        for r in (v if isinstance(v, list) else []):
            if isinstance(r, str) and r:
                q = r if r.startswith("/") else os.path.join(b, r)
                if not os.path.exists(q):
                    print("D", lab, q)
                    n += 1
                    if n >= 3:
                        sys.exit(0)
"""


def _deep_probe_cmd(paths):
    """shell: per path 'M <p>' (absent) or 'D <p> <what>' (a broken link below it, a missing bind.f source, or a path a
    .sh script names that fails the same test); silent when whole.  KW-FIX-44 11-10: 'N <p> <what>' = a path named by
    a .sh / .json file the script names (its inputs: S81_ASBUILT json, a sourced .sh) that is absent here; counted
    by src_incomplete only where another probed host has it (old provenance paths absent everywhere are not inputs)"""
    q = shlex.quote
    fn = ("ck() { p=$1; if [ ! -e \"$p\" ]; then echo \"M $p\"; return; fi; "
          # a link / bind.f scan only below a lane's sub-dir (never a lane root or claude/ itself: size and noise)
          "case \"$p\" in /srv/*/claude/*/*/*) ;; *) return;; esac; "
          "if [ -d \"$p\" ]; then "
          f"b=$(find -L \"$p\" -maxdepth {DEEP_LINK_DEPTH} -type l -print 2>/dev/null | head -1); "
          "[ -n \"$b\" ] && echo \"D $p $b\"; "
          "if [ -f \"$p/bind.f\" ]; then grep '^/' \"$p/bind.f\" | while read -r s; do [ -e \"$s\" ] || echo \"D $p $s\"; "
          "done | head -3; fi; fi; }; "
          f"ckj() {{ [ -f \"$1\" ] && python3 -I -c {shlex.quote(_ASBUILT_PY)} \"$1\" \"$2\" 2>/dev/null; }}; "
          # WAVE-OPS-1 11-10: a plan json's first pins_file (relative = to the plan dir) must exist ('D <plan> <pins>')
          "ckp() { [ -f \"$1\" ] || return; f=$(grep -o -m1 '\"pins_file\": *\"[^\"]*\"' \"$1\" 2>/dev/null | head -1 "
          "| sed 's/.*: *\"//; s/\"$//'); [ -n \"$f\" ] || return; case \"$f\" in /*) g=$f;; *) g=$(dirname \"$1\")/$f;; "
          "esac; [ -e \"$g\" ] || echo \"D $1 $g\"; }; "
          "ckd() { ck \"$1\"; case \"$1\" in *.json) ckp \"$1\";; esac; case \"$1\" in *.json) ckj \"$1\" \"$1\";; esac; case \"$1\" in *.sh) [ -f \"$1\" ] && "
          "for s in $(grep -o '/srv/opentallas-scratch[^[:space:]\"'\"'\"';)$]*' \"$1\" | sort -u); do "
          "ck \"$s\" | sed \"s#^M \\(.*\\)#D $1 \\1#; s#^D [^ ]* \\(.*\\)#D $1 \\1#\"; "
          "case \"$s\" in *.sh|*.json) [ -f \"$s\" ] && [ $(stat -c %s \"$s\") -lt 5000000 ] && "
          "for t in $(grep -o '/srv/opentallas-scratch[^[:space:]\"'\"'\"';),$]*' \"$s\" | sort -u); do "
          "[ -e \"$t\" ] || echo \"N $1 $t\"; done;; esac; "
          "case \"$s\" in *.json) ckj \"$s\" \"$1\";; esac; done;; esac; }")
    return "; ".join([fn] + [f"ckd {q(p)}" for p in paths] + ["true"])


def _src_probe_cmd(trees, files):
    q = shlex.quote
    parts = []
    for t in trees:
        parts.append(f"echo T {q(t)} $(find {q(t.rstrip('/') + '/')} -maxdepth {SRC_PROBE_DEPTH} -type f 2>/dev/null "
                     "| wc -l)")
    parts += [f"test -e {q(f)} || echo M {q(f)}" for f in files]
    return "; ".join(parts + ["true"])


def src_incomplete(AP, cfg, run=None):
    """{host: {die: why}} for the gen hosts whose input copies are incomplete (see SRC_MIN_FRAC); run(host, cmd) ->
    (rc, out) defaults to ssh (the hub runs the probe locally)"""
    if cfg.get("src_probe") is False:
        return {}
    hub = cfg.get("_hub") or getattr(AP, "HUB_NAME", "") or ""
    if run is None:
        def run(h, cmd):
            if h in (hub, "localhost"):
                rc, o, _ = AP.sh(["bash", "-c", cmd], timeout=120)
            else:
                rc, o, _ = AP.sh(["ssh", "-n", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", "-o",
                                  "ControlPath=none", h, cmd], timeout=120)
            return rc, o
    need = {}
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or d.get("src_probe") is False:
            continue
        for h in list(d.get("gen_hosts") or []) + [d.get("gen_host")]:
            if h:
                need.setdefault(h, set()).add(die)
    counts, missing, deep, nmiss, probed = {}, {}, {}, {}, {}
    for h, ds in sorted(need.items()):
        trees = sorted({t for die in ds for t in src_inputs(cfg, die)[0]})
        files = sorted({f for die in ds for f in src_inputs(cfg, die)[1]})
        dps = sorted({p for die in ds for p in deep_inputs(cfg, die)}
                     | {p for die in ds for ps in item_inputs(cfg, die).values() for p in ps})
        try:
            rc, o = run(h, _src_probe_cmd(trees, files) + ("; " + _deep_probe_cmd(dps) if dps else ""))
        except Exception:
            continue
        if rc != 0:
            continue                                   # unreachable / failed probe = unknown, never dropped
        counts[h], missing[h], deep[h], nmiss[h], probed[h] = {}, set(), {}, {}, set(dps)
        for ln in (o or "").splitlines():
            f = ln.split()
            if len(f) == 3 and f[0] == "T" and f[2].isdigit():
                counts[h][f[1]] = int(f[2])
            elif len(f) == 2 and f[0] == "M":
                missing[h].add(f[1])
            elif len(f) == 3 and f[0] == "D":
                deep[h].setdefault(f[1], f[2])
            elif len(f) == 3 and f[0] == "N":
                nmiss[h].setdefault(f[1], set()).add(f[2])
    # a second-level name counts only where another probed host has both the script and that path (KW-FIX-44 11-10)
    for h in nmiss:
        for p, subs in nmiss[h].items():
            for sub in sorted(subs):
                if p not in deep[h] and any(p in probed[g] and p not in missing[g] and sub not in nmiss[g].get(p, ())
                                            for g in counts if g != h):
                    deep[h].setdefault(p, sub)
    best = {}
    for h, c in counts.items():
        for t, n in c.items():
            best[t] = max(best.get(t, 0), n)
    out, items = {}, {}
    for h in counts:
        for die in sorted(need[h]):
            trees, files = src_inputs(cfg, die)
            why = [f"{t} {counts[h].get(t, 0)}/{best.get(t, 0)} files" for t in trees
                   if best.get(t, 0) and counts[h].get(t, 0) < SRC_MIN_FRAC * best[t]]
            why += [f"{f} missing" for f in files if f in missing[h]]
            why += [f"{p} missing" if p in missing[h] else f"{p}: {deep[h][p]} missing"
                    for p in deep_inputs(cfg, die) if p in missing[h] or p in deep[h]]
            if why:
                out.setdefault(h, {})[die] = "; ".join(why)
            for item, ps in item_inputs(cfg, die).items():
                iw = [f"{p} missing" if p in missing[h] else f"{p}: {deep[h][p]} missing"
                      for p in ps if p in missing[h] or p in deep[h]]
                if iw:
                    items.setdefault(h, {}).setdefault(die, {})[item] = "; ".join(iw)
    if isinstance(cfg, dict):
        cfg["_item_incomplete"] = items
    return out


def workroot_low(AP, cfg, run=None):
    """KW-FIX-30 11-07 (COORD 13:21): {host: {die: free GB}} for the gen hosts where the disk that really holds the
    die's work_root has less than gen_disk_min_gb free.  GEN-DISK-LOW reads ot-run's scratch disk (scratch2), but the
    S81/QC lane root /srv/opentallas-scratch3/claude/kw26-wave-1106 is the ROOT disk on most hosts (epyc6 root 94 GB
    gave gens while scratch2 looked fine).  One ssh per host: df of the lane root, or of its nearest existing parent.
    An unreachable host or unreadable df is unknown, never low.  Global or die option workroot_probe: false = off."""
    floor = int(cfg.get("gen_disk_min_gb", GEN_DISK_MIN_GB))
    # KW-FIX-35 11-08 (COORD 08:4x; OWNER 11-05 all disks are scratch, 11-06 root floor 150): a lane on the ROOT fs
    # ('/') must keep root_floor_gb free beyond the gen room: low there below root_floor_gb + root_gen_room_gb
    rfloor = int(cfg.get("root_floor_gb", 150)) + int(cfg.get("root_gen_room_gb", 40))
    free_map = cfg.setdefault("_workroot_free", {}) if isinstance(cfg, dict) else {}
    free_map.clear()
    alt_map = cfg.setdefault("_workroot_alt", {}) if isinstance(cfg, dict) else {}
    alt_map.clear()
    lim_map = cfg.setdefault("_workroot_lim", {}) if isinstance(cfg, dict) else {}
    lim_map.clear()
    cfg.pop("_alt_spent", None)
    alt_on = cfg.get("workroot_alt") is not False
    alt_lim = floor + int(cfg.get("gen_need_gb", GEN_NEED_GB))
    if cfg.get("workroot_probe") is False or floor <= 0:
        return {}
    hub = cfg.get("_hub") or getattr(AP, "HUB_NAME", "") or ""
    if run is None:
        def run(h, cmd):
            if h in (hub, "localhost"):
                rc, o, _ = AP.sh(["bash", "-c", cmd], timeout=120)
            else:
                rc, o, _ = AP.sh(["ssh", "-n", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", "-o",
                                  "ControlPath=none", h, cmd], timeout=120)
            return rc, o
    need = {}
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or d.get("enabled") is False or d.get("workroot_probe") is False:
            continue
        lane = lane_root(opt(cfg, die, "work_root"))
        if not lane.startswith("/"):
            continue
        for h in list(d.get("gen_hosts") or []) + [d.get("gen_host")]:
            if h:
                need.setdefault(h, {}).setdefault(lane, set()).add(die)
    q = shlex.quote
    out = {}
    for h, lanes in sorted(need.items()):
        cmd = "; ".join(f"d={q(l)}; while [ ! -e \"$d\" ] && [ \"$d\" != / ]; do d=$(dirname \"$d\"); done; "
                        f"echo W {q(l)} $(df -BG --output=avail \"$d/\" 2>/dev/null | tail -1 | tr -dc 0-9) "
                        f"$(df --output=target \"$d/\" 2>/dev/null | tail -1 | tr -d \" \") "
                        # KW-FIX-38 11-08: scratch3 is a separate mount of the root fs on the fleet, so df's target is
                        # never '/': compare devices as ot-run does; and measure scratch2 for the alternative below
                        f"$(stat -Lc %d \"$d/\" 2>/dev/null) $(stat -Lc %d / 2>/dev/null) "
                        f"$(df -BG --output=avail {SCRATCH2_ROOT}/ 2>/dev/null | tail -1 | tr -dc 0-9) "
                        f"$(stat -Lc %d {SCRATCH2_ROOT}/ 2>/dev/null)"
                        for l in sorted(lanes))
        try:
            rc, o = run(h, cmd + "; true")
        except Exception:
            continue
        if rc != 0:
            continue
        for ln in (o or "").splitlines():
            f = ln.split()
            if len(f) >= 3 and f[0] == "W" and f[2].isdigit() and f[1] in lanes:
                on_root = len(f) >= 4 and (f[3] == "/" or (len(f) >= 6 and f[4] == f[5]))
                lim = rfloor if on_root else floor
                hard = int(cfg.get("root_floor_gb", 150)) if on_root else GEN_SCRATCH_HARD_FLOOR_GB
                gb = int(f[2])
                # KW-FIX-38 11-08 (COORD: 52 rows at kit_rtl behind a root floor): the lane sits on the root fs with no
                # room but this host's scratch2 is another disk with room: the attempt starts there (work_alt in
                # run_item: attempt dir = symlink to the scratch2 path); option workroot_alt false turns it off
                alt = ""
                if on_root and gb < lim and alt_on and len(f) >= 8 and f[6].isdigit() and f[7] != f[5] \
                        and int(f[6]) >= alt_lim and f[1].startswith(SCRATCH3_ROOT + "/"):
                    alt, gb, hard = SCRATCH2_ROOT + f[1][len(SCRATCH3_ROOT):], int(f[6]), GEN_SCRATCH_HARD_FLOOR_GB
                # KW-FIX-44 11-10 (COORD): a lane SPELLED under scratch2 whose real path is on the root fs (epyc2:
                # kw43-wave-1109 is a symlink onto scratch3 = root) has no same-path twin on scratch2; its new attempts
                # start in <lane><workroot_alt_suffix> (default "-s2"), a real scratch2 dir; work_alt_cmd links them in
                elif on_root and gb < lim and alt_on and len(f) >= 8 and f[6].isdigit() and f[7] != f[5] \
                        and int(f[6]) >= alt_lim and f[1].startswith(SCRATCH2_ROOT + "/"):
                    alt = f[1].rstrip("/") + str(cfg.get("workroot_alt_suffix") or "-s2")
                    gb, hard = int(f[6]), GEN_SCRATCH_HARD_FLOOR_GB
                for die in lanes[f[1]]:
                    free_map.setdefault(h, {})[die] = gb
                    cfg.setdefault("_workroot_hard", {}).setdefault(h, {})[die] = hard
                    if alt:
                        alt_map.setdefault(h, {})[die] = alt
                    elif gb < lim:
                        out.setdefault(h, {})[die] = gb
                        lim_map.setdefault(h, {})[die] = lim
    return out


SCRATCH2_ROOT, SCRATCH3_ROOT = "/srv/opentallas-scratch2", "/srv/opentallas-scratch3"
SPILL_MARK = ".ot-run-spill-copy"                  # ot-run SPILL copy marker (ot-run v14 mark_ancestors)
LANE_RE = re.compile(r"^(/srv/opentallas-scratch[^/]*/claude/[^/]+)(/|$)")


def lane_root(path):
    """ot-run lane root of a scratch path (/srv/opentallas-scratch*/claude/<lane>), else the path itself"""
    m = LANE_RE.match(os.path.normpath(str(path or "")))
    return m.group(1) if m else os.path.normpath(str(path or ""))


def spill_marked(AP, cfg):
    """{host: {lane roots carrying the ot-run SPILL marker}} for every non-hub gen host of an enabled die (one ssh
    per host; an unreachable host is left out = unknown, never marked)"""
    hub, roots = cfg.get("_hub") or "", {}
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict):
            continue
        for h in list(d.get("gen_hosts") or []) + [d.get("gen_host")]:
            if h and h not in (hub, "localhost"):
                roots.setdefault(h, set()).add(lane_root(opt(cfg, die, "work_root")))
    out = {}
    for h, rs in sorted(roots.items()):
        cmd = "; ".join(f"test -e {shlex.quote(r + '/' + SPILL_MARK)} && echo {shlex.quote(r)}" for r in sorted(rs)) + "; true"
        rc, o, _ = AP.sh(["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", "-o", "ControlPath=none", h, cmd],
                         timeout=60)
        if rc == 0:
            out[h] = {x for x in o.split() if x in rs}
    return out


def work_root_problem(cfg, die, hub_isdir=os.path.isdir):
    """KW-FIX-8 11-04 (COORD 11:4x): why no kit of this die can run under its work_root, read before any launch, else
    None.  Two lost batches: every gen host carries the SPILL marker on the lane root (ot-run: NOT RUN: no host
    qualifies; KV 06:12, QC 11:09), or the scratch mount is not on the hub (sync_hub mkdir: Permission denied; KV 07:00).
    An unreachable host is unknown, never a problem."""
    d = cfg["dies"][die]
    root = str(opt(cfg, die, "work_root") or "")
    lane = lane_root(root)
    m = re.match(r"^(/srv/[^/]+)/", root)
    if m and not hub_isdir(m.group(1)):
        return f"work_root {root}: {m.group(1)} is not on the hub, sync_hub cannot mkdir there; set work_root"
    marked = cfg.get("_spill_marked") or {}
    hs = [h for h in list(d.get("gen_hosts") or []) + [d.get("gen_host")] if h]
    bad = cfg.get("_src_incomplete") or {}
    if hs and all(die in bad.get(h, {}) for h in hs):
        return ("src/plan inputs incomplete on every gen host (KW-FIX-24 SRC-INCOMPLETE): "
                + "; ".join(f"{h}: {bad[h][die]}" for h in sorted(set(hs))) + "; sync the copies or set gen_hosts")
    if hs and all(lane in marked.get(h, ()) for h in hs):
        return (f"work_root lane {lane} carries {SPILL_MARK} on {' '.join(sorted(set(hs)))}: ot-run would say no host "
                "qualifies for every kit; set work_root to an unmarked lane on the hub and these hosts")
    return None


def over_load_cap(v):
    """the ot-heavy rule (LOADCAP_1101): a non-crit job waits while int(load1) >= int(LOAD_CAP_FACTOR x nproc)"""
    n = int((v or {}).get("cores") or 0)
    return n > 0 and int(float(v.get("load", 0))) >= int(LOAD_CAP_FACTOR * n)


def host_room(v, disk_low=None):
    """a status row that can take a new build now: under its load cap and over the gen disk floor (disk_low: the
    die-aware answer of die_disk_low, else ot-run's scratch2 figure)"""
    return bool(v) and not over_load_cap(v) and not (gen_disk_low(v) if disk_low is None else disk_low)


def die_disk_low(cfg, die, h, v):
    """KW-FIX-35 11-08 (COORD 08:4x epyc6 wave room): is host h under the gen disk floor FOR THIS DIE?  When the
    work_root probe measured the disk that really holds the die's lane on h (cfg _workroot_free), that measure decides:
    S81/QC kw26 lanes live on the epyc6 ROOT disk (218 GB) while ot-run's 'scratch' figure is its scratch2 (60 GB), and
    the global figure kept epyc6 out of every die's gen pick at load 22/128.  Unmeasured -> gen_disk_low(v) as before."""
    free = (cfg.get("_workroot_free") or {}).get(h) or {}
    if die in free:
        return die in ((cfg.get("_workroot_low") or {}).get(h) or {})
    return gen_disk_low(v)


def die_score(cfg, die, h, v):
    """host_score with the die-aware disk floor (die_disk_low)"""
    return host_score(v, disk_low=die_disk_low(cfg, die, h, v) if v else None)


# KW-FIX-36 11-08 (COORD 17:3x): gen_disk_min_gb is a preference.  When no gen host of a die clears it the die would stop
# although some host can still take a kit, so the fallback picks the host with the most free disk on the die's lane that
# clears the REAL floor (root_floor_gb for a lane on a root fs, ot-run's scratch floor otherwise) plus the gen need,
# at most gen_fallback_per_tick gens per host per tick.  Option gen_disk_fallback false turns it off.
GEN_SCRATCH_HARD_FLOOR_GB = 50      # ot-run refuses a scratch disk below this
GEN_NEED_GB = 20                    # gen + place of one kit: 1-3 GB measured on 8 HBM attempts, with margin
GEN_ALT_CHARGE_GB = 6               # KW-FIX-38: booked per kit on a scratch2 alternative within one tick (1-6 GB through place)
GEN_FALLBACK_PER_TICK = 2


def gen_fallback_host(cfg, die, hs):
    """the host for a gen when no host of hs clears the preference (see above), or None"""
    if cfg.get("gen_disk_fallback") is False:
        return None
    stt, hub = cfg.get("_otrun_status") or {}, cfg.get("_hub") or ""
    need, cap = int(cfg.get("gen_need_gb", GEN_NEED_GB)), int(cfg.get("gen_fallback_per_tick", GEN_FALLBACK_PER_TICK))
    taken, free, hard = cfg.get("_gen_fallback_taken") or {}, cfg.get("_workroot_free") or {}, cfg.get("_workroot_hard") or {}
    best = None
    for h in hs:
        v = stt.get("localhost" if h == hub else h)
        if not v or over_load_cap(v) or taken.get(h, 0) >= cap:
            continue
        f, floor = (free.get(h) or {}).get(die), (hard.get(h) or {}).get(die, GEN_SCRATCH_HARD_FLOOR_GB)
        f = ((cfg.get("_workroot_low") or {}).get(h) or {}).get(die) if f is None else f
        f = int(v["scratch_gb"]) if f is None and v.get("scratch_gb") is not None else f
        if f is not None and int(f) >= floor + need and (best is None or int(f) > best[0]):
            best = (int(f), h)
    return best[1] if best else None


def load_hold(cfg, die, *names):
    """SCHED-1 11-07 (OWNER closure first): no gen host of the die has room -> the reason a new row stays pending in the
    wave instead of queueing behind a host's load cap; "" = launch.  It holds no started job and no NEAR-COUNT row (those
    launch --crit, which bypasses the cap).  No status = unchanged.  cfg load_hold false turns it off."""
    stt, hub = cfg.get("_otrun_status") or {}, cfg.get("_hub") or ""
    if cfg.get("load_hold") is False or not stt or near_count_hit(cfg.get("_near_count") or set(), die, *names):
        return ""
    low = cfg.get("_workroot_low") or {}
    rows = [(h, stt.get("localhost" if h == hub else h)) for h in gen_hosts(cfg, die)]
    if any(host_room(v, die_disk_low(cfg, die, h, v)) and die not in low.get(h, {}) for h, v in rows):
        return ""
    if gen_fallback_host(cfg, die, [h for h, _ in rows]):
        return ""
    return "LOAD-HOLD no gen host with room: " + " ".join(
        f"{h} {'absent' if not v else 'load %d/%d' % (v.get('load', 0), v.get('cores', 0))}"
        + (f" work_root {low[h][die]} GB" if die in low.get(h, {}) else "") for h, v in rows)


def pick_gen_host(cfg, die, take=0, threads=0, item=None):
    """the gen host for a new attempt (see gen_hosts); with no cached ot-run status the configured gen_host.  take =
    GB charged to the picked host's cached admits so one tick's burst spreads once that host's headroom is used.
    SCHED-1 11-07: only hosts with room (host_room) while one exists, the least loaded one whose admits minus queue fit
    take, else the best host_score; threads = load charged to the pick, so one tick's burst stops at the cap."""
    hs, stt, hub = gen_hosts(cfg, die, item), cfg.get("_otrun_status") or {}, cfg.get("_hub") or ""
    if not stt:
        d = cfg["dies"][die]
        return d["gen_host"] if (d["gen_host"] in hs or not hs) else hs[0]      # KW-FIX-35-RD: item inputs
    key = lambda h: stt.get("localhost" if h == hub else h)
    if cfg.get("load_hold") is not False and hs and not any(
            host_room(key(h), die_disk_low(cfg, die, h, key(h))) and die not in (cfg.get("_workroot_low") or {}).get(h, {}) for h in hs):
        fb = gen_fallback_host(cfg, die, hs)                      # KW-FIX-36: no host clears the preference
        if fb:
            t = cfg.setdefault("_gen_fallback_taken", {})
            t[fb] = t.get(fb, 0) + 1
            return fb
    if len(hs) < 2:
        best = hs[0] if hs else cfg["dies"][die]["gen_host"]      # KW-FIX-30: the one host gen_hosts left
    else:
        on = cfg.get("load_hold") is not False
        low = cfg.get("_workroot_low") or {}
        room = [h for h in hs if host_room(key(h), die_disk_low(cfg, die, h, key(h))) and die not in low.get(h, {})] if on else []
        sc = lambda h: die_score(cfg, die, h, key(h))
        fits = [h for h in room if sc(h) >= max(take, 1)]
        frac = lambda h: round(float(key(h).get("load", 0)) / max(1, int(key(h).get("cores") or 1)), 1)
        best = (min(fits, key=lambda h: (frac(h), -sc(h), hs.index(h))) if fits
                else max(room or hs, key=lambda h: (sc(h), -hs.index(h))))
    if key(best) is not None and len(hs) >= 2 and take:
        charge(key(best), take)
    alt_charge(cfg, best)
    if key(best) is not None and threads:
        key(best)["load"] = float(key(best).get("load", 0)) + threads
    return best


def alt_charge(cfg, h):
    """KW-FIX-38 11-08: one new attempt booked on host h's scratch2 alternative (gen_need_gb); below room it is off for
    the rest of the tick, so one tick cannot send more kits to the alternative disk than it holds"""
    alt = (cfg.get("_workroot_alt") or {}).get(h) or {}
    if not alt:
        return
    need, free = int(cfg.get("gen_alt_charge_gb", GEN_ALT_CHARGE_GB)), cfg.setdefault("_workroot_free", {}).get(h) or {}
    lim = int(cfg.get("gen_disk_min_gb", GEN_DISK_MIN_GB)) + need              # entry needed +gen_need_gb; the burst may use it down to one kit above the floor
    for die in list(alt):
        free[die] = int(free.get(die, lim)) - need
        if free[die] < lim:
            del alt[die]
            cfg.setdefault("_workroot_low", {}).setdefault(h, {})[die] = free[die]
            cfg.setdefault("_alt_spent", {}).setdefault(h, set()).add(die)


def charge(v, gb):
    """book gb of new demand on a cached ot-run status row: it admits now if it fits, else it waits there"""
    if int(v.get("admit", 0)) >= gb:
        v["admit"] = int(v.get("admit", 0)) - gb
    else:
        v["wait_n"], v["wait_gb"] = int(v.get("wait_n", 0)) + 1, int(v.get("wait_gb", 0)) + gb


def wsize(v, mem):
    """GB one queued waiter books on a status row: its mean waiter size (most waiters are 10 GB gen/lint stages
    waiting for short slots, not 48 GB PLACE), else the die's place_mem_gb"""
    v = v or {}
    return max(1, round(int(v.get("wait_gb", 0)) / int(v["wait_n"]))) if int(v.get("wait_n", 0)) > 0 else mem


def uncharge(v, gb):
    """a waiter moved off a host: its queued GB leaves the cached status row"""
    if int(v.get("wait_n", 0)) > 0:
        v["wait_n"], v["wait_gb"] = int(v["wait_n"]) - 1, max(0, int(v.get("wait_gb", 0)) - gb)


COUNTER_CACHE = Path.home() / ".local/state/fleet-viz/release_tree_plan_cache.json"


def load_counter_signed(cfg):
    """{die: names} the sign-off counter counts now (tools/release_tree_plan.py cache), read at the start of a tick.  An
    unreadable cache means nothing is known to be counted: the wave then behaves as before."""
    got = {}
    try:
        plans = json.loads(Path(cfg.get("counter_cache") or COUNTER_CACHE).read_text()).get("plans") or {}
        for ent in plans.values():
            got.setdefault(ent.get("die"), set()).update(ent.get("signed_types") or {}, ent.get("signed_designs") or {})
    except (OSError, ValueError, AttributeError):
        got = {}
    cfg["_counter_signed"] = got
    return got


def counted_now(cfg, st, die, item, block=None):
    """KW-FIX-27 11-07 (COORD, hd_st_n4 rebuilt after its ECO sign-off): the wave does not rebuild a design the counter
    counts unless the plan changed it.  The plan block seen when the row is first found counted is kept in the state; another
    block later = the plan changed the design.  Die list rebuild_counted names a deliberate rebuild."""
    if item not in (cfg.get("_counter_signed") or {}).get(die, ()):
        return False
    if item in ((cfg.get("dies") or {}).get(die) or {}).get("rebuild_counted", ()):
        return False
    if not block:
        return True
    return st.setdefault("counted_blocks", {}).setdefault(f"{die}|{item}", block) == block


# OWNER 11-07 05:1x "never use more place and route retries" (KW-FIX-27): a design FAIL relaunches only when the row's
# inputs changed.  Not inputs: where and how large it runs (host, memory, paths), and resume data.  src_sha is the whole
# source tree, so a new source counts as a change for every row of the die.
# src_base (KW-FIX-44 11-10, COORD): the commit a wave source tree actually started from; src_sha names the commit its
# switch inputs came from, and the tree was never at it.  A record of provenance, so not an input.
INPUT_SKIP = {"src_base", "die", "item", "kind", "event", "gen_host", "work", "root", "hosts", "hub", "place_prefer", "place_mem_gb",
              "place_threads", "geom_mem_gb", "geom_grt_wall_s", "gen_mem_gb", "lint_mem_gb", "bind_mem_gb", "ot_run", "crit",
              "start_delay_s", "resume_from", "future_lec", "src", "plan", "queue_src", "region_guide_geom", "leafslew_form",
              "prov_views", "geom_advisory", "place_spill", "hold_items", "route_hold_items"}


def input_hash(sp, prov_key=None):
    src = str(sp.get("src") or "")

    def clean(v):
        if isinstance(v, dict):
            return {k: c for k, c in ((k, clean(x)) for k, x in v.items() if k != "note") if c not in (None, "", {}, [])}
        if isinstance(v, (list, tuple)):
            return [clean(x) for x in v]
        return v.replace(src, "<SRC>") if isinstance(v, str) and src else v
    # OT_FLOW_TAG selects the released sign-off tools/child context, not design inputs. Normalize
    # both stored and candidate specs; changing only this metadata must never release a failed row.
    compared = dict(sp)
    if isinstance(compared.get("gen_env"), dict):
        compared["gen_env"] = {k: v for k, v in compared["gen_env"].items() if k != "OT_FLOW_TAG"}
    body = {k: c for k, c in ((k, clean(v)) for k, v in compared.items() if k not in INPUT_SKIP) if c not in (None, "", {}, [])}
    form = sp.get("leafslew_form")
    if form:
        body["leafslew"] = clean(form.get("env") or {})
    if prov_key:
        body["prov_key"] = prov_key
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def unchanged_fail(cfg, st, die, item, rec, parent=None, kind="type"):
    """True: a design FAIL whose relaunch would build the same inputs.  INFRA and unreadable records are never held.
    COORD 11-07 05:24: after a TIMING or ROUTING FAIL a new source alone is no change: the retry entry's retry_fix text must
    name a redesign (REDESIGN: changed RTL, pin cycles, macros, outline or clock).  Other spec differences do not count:
    on 11-07 flow flags and paths differed on 144 of 147 such rows, none of them a redesign."""
    if not rec or not (rec.get("status") == "FAIL" or (rec.get("status") == "ENQUEUED" and rec.get("q_status") == "FAIL")):
        return False
    cls = str((rec.get("q_class") if rec.get("q_status") == "FAIL" else "") or rec.get("class") or "")
    if cls == "INFRA":
        return False
    if cls in ("TIMING", "ROUTING"):
        rf = ((cfg.get("dies") or {}).get(die) or {}).get("retry_fix")
        return "REDESIGN:" not in str((rf.get(f"{item}@{rec.get('attempt')}") if isinstance(rf, dict) else "") or "")
    try:
        old = json.loads((Path(rec["dir"]) / "spec.json").read_text())
        cand = spec_for(dict(cfg, _otrun_status={}), die, item, cfg.get("_hub") or "", parent or rec.get("parent_item"),
                        kind=kind or rec.get("kind") or "type")
        attempt = int(rec.get("attempt") or 0) + 1
        key, form = leafslew_launch(cfg, st, die, item, rec, attempt)
        if key:                                       # released by the LEAFSLEW signature: the form changes
            return False
        if form:
            cand["leafslew_form"] = form
        d = cfg["dies"][die]
        # Compared only when both sides have it: a kit built before the field existed, or a host that could not be read,
        # must neither release the row nor hold it on a value that was never measured.
        if not (old.get("src_overlay") and cand.get("src_overlay")):
            old.pop("src_overlay", None); cand.pop("src_overlay", None)
        return input_hash(old, rec.get("prov_key")) == input_hash(cand, (d.get("_prov_keys") or {}).get(item) or rec.get("prov_key"))
    except (OSError, ValueError, KeyError, TypeError):
        return False


HOLD_UNCHANGED = "no input change since this FAIL: redesign list, no P&R retry (OWNER 11-07)"
REDESIGN_FILE = "kit_wave_redesign.tsv"


def redesign_rows(cfg, st):
    """current-plan design FAIL rows of the wave's state whose relaunch would build the same inputs; released = a retry entry
    names the attempt, so without the hold it would relaunch"""
    out = []
    for key, rec in sorted((st.get("items") or {}).items()):
        die = rec.get("die")
        d = (cfg.get("dies") or {}).get(die)
        if not d or rec.get("arm") or rec.get("event") != d.get("event") or not unchanged_fail(cfg, st, die, rec.get("item"), rec):
            continue
        ia = f"{rec.get('item')}@{rec.get('attempt')}"
        q = rec.get("q_status") == "FAIL"
        out.append(dict(die=die, item=rec.get("item"), attempt=rec.get("attempt"),
                        cls=(rec.get("q_class") if q else "") or rec.get("class") or "",
                        stage=(rec.get("q_stage") if q else "") or rec.get("stage") or "",
                        released="yes" if ia in (d.get("retry") or []) else "no",
                        reason=re.sub(r"\s+", " ", str((rec.get("q_reason") if q else "") or rec.get("reason") or ""))[:200], key=key))
    return out


def write_redesign(cfg, st, ap_dir):
    rows = redesign_rows(cfg, st)
    cols = ["die", "item", "attempt", "cls", "stage", "released", "reason"]
    (Path(ap_dir) / REDESIGN_FILE).write_text("\n".join(["\t".join(cols)] + ["\t".join(str(x[c]) for c in cols) for x in rows]) + "\n")
    return rows


def restage_waiters(AP, cfg, st, notices):
    """KW-FIX-4 11-03 (COORD: not-yet-started waiters may be restaged): a RUNNING attempt of a die with gen_hosts whose
    current ot-run stage still WAITS for admission (volume_started False) on a gen host other than the best one is
    stopped (unit + detached PLACE client, exact unit names) and marked RETRY-INFRA: the INFRA relaunch path starts it
    again this tick on the best host.  Also an async PLACE client started PINNED (--hosts G, before place_spill) that
    still waits: relaunched it can SPILL.  At most restage_max_per_tick (60); die restage_waiters false opts out.
    COORD 12:1x FLEET class fix: (1) 'best' = the most admits MINUS queued waiter GB (host_score); a waiter moves when
    the best host's score beats its own host's by >= place_mem_gb -- no load hold (owner: NO LOAD HOLD), so 131
    waiters on epyc4 move to an intel1 with 0; (2) a never-admitted wait is an infra move, not an attempt: it moves
    even when the infra retry budget is used, and the move itself is not charged (infra_base + 1)."""
    stt, hub = cfg.get("_otrun_status") or {}, cfg.get("_hub") or ""
    cap, n = int(cfg.get("restage_max_per_tick", 60)), 0
    row = lambda h: stt.get("localhost" if h == hub else h)
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or d.get("restage_waiters") is False:
            continue
        multi = len(gen_hosts(cfg, die)) >= 2 and bool(stt)
        spill = opt(cfg, die, "place_spill") is not False
        mem = int(opt(cfg, die, "place_mem_gb"))
        for r in (st.get("items") or {}).values():
            if n >= cap:
                return n
            if r.get("die") != die or r.get("status") != "RUNNING" or not r.get("unit") or r.get("arm"):
                continue
            # only an attempt the INFRA path WILL relaunch this tick (raw block identity, die not stopped)
            if (d.get("block_identity", "raw") != "raw") or stop_reason(cfg, die, cfg.get("_ap_dir")):
                continue
            try:
                g = json.loads((Path(r["dir"]) / "spec.json").read_text()).get("gen_host")
            except (OSError, ValueError, KeyError):
                continue
            try:
                svc0 = json.loads((Path(r["dir"]) / "place_service.json").read_text())
            except (OSError, ValueError):
                svc0 = {}
            why, best, v = "", g, {}
            # KW-FIX-24 20:3x RESTAGE ping-pong class: a host move needs the waiter to have waited restage_min_wait_s
            # (default 1800) since its launch; a fresh waiter moved every tick (epyc5 <-> epyc2, 24 moves/h, the gen
            # stage redone each time) never reaches admission
            # KW-FIX-27 11-07: the wait doubles with each move of the row (at most x8), so a row is not restarted every 30 min
            young = (time.time() - float(r.get("started") or 0)
                     < float(cfg.get("restage_min_wait_s", 1800)) * 2 ** min(3, int(r.get("restage_n") or 0)))
            # KW-FIX-28 11-07: a spillable async PLACE client is already host-mobile: ot-run re-places it every 120 s and spills it
            # to any host that admits.  Stopping it only redoes kit_rtl and gen on the target (181 of 267 moves on 11-07, none of
            # which could help admission).  A move is for a waiter pinned to its gen host: an earlier stage, or a pinned client.
            # KW-FIX-40 11-08 (COORD 23:06): a kit under a path only the root disk of the other hosts has (scratch3) cannot spill past
            # their root floors, so restage_place_waiters makes such waiters movable from mkdir like an earlier stage.
            mobile = (spill and svc0.get("launch") == "launched" and "--hosts" not in (svc0.get("argv") or [])
                      and not cfg.get("restage_place_waiters"))
            if multi and not young and not mobile:
                best = pick_gen_host(cfg, die, item=r.get("item"))       # KW-FIX-35-RD: a target with its inputs
                v = row(best) or {}
                if best != g and (host_room(v, die_disk_low(cfg, die, best, v) if v else None)
                                  or cfg.get("load_hold") is False) and (
                        die_score(cfg, die, best, v) - die_score(cfg, die, g, row(g)) >= wsize(row(g), mem)):
                    why = f"{g} -> {best}"
            # an async PLACE client started pinned (--hosts G, before place_spill) can never move: relaunch it spillable
            if not why and spill and svc0.get("launch") == "launched" and "--hosts" in (svc0.get("argv") or []):
                why, best = f"pinned async PLACE waiter on {g} -> spillable PLACE", g
            if counted_now(cfg, st, die, r.get("item"), r.get("block_sha")):
                why, best = "counted by the sign-off counter", g      # the INFRA path below ends it instead of relaunching
            if not why or volume_started(r):
                continue
            # KW-FIX-35-H 11-08: a host move never stops an attempt whose PLACE already ran or was admitted (only the
            # counted end above may); it waits on its host instead of being relaunched from mkdir
            if not why.startswith("counted") and heavy_progress(r):
                continue
            if not AP.DRY:
                AP.sh(["systemctl", "--user", "stop", r["unit"]], timeout=180)
                try:
                    svc = json.loads((Path(r["dir"]) / "place_service.json").read_text())
                    AP.sh(["systemctl", "--user", "stop", svc["unit"]], timeout=180)
                except (OSError, ValueError, KeyError):
                    pass
            gb = wsize(row(g), mem)
            if v:
                charge(v, gb)
                # KW-FIX-28: the moved row's load counts now, so one tick's moves stop at the target's cap (host_room above)
                if best != g:
                    v["load"] = float(v.get("load", 0)) + int(opt(cfg, die, "place_threads"))
            if row(g):
                uncharge(row(g), gb)
            # the move is not an attempt: keep the infra budget where it was (and give a spent one its move)
            # (+1: the relaunch's attempt number +1 is not charged; a spent budget is lifted to exactly one relaunch)
            r["infra_base"] = int(r.get("infra_base") or 0) + max(1, infra_used(r) - infra_attempts(cfg, die) + 1)
            r.update(status="RETRY-INFRA", **{"class": "INFRA"}, updated=time.time(),
                     reason=f"restaged: unstarted ot-run waiter ({why}) (KW-FIX-4)")
            # KW-FIX-27 11-07: the move binds.  spec_for reselects a host at launch, so a logged move could return to g
            r["restage_host"] = best
            r["restage_n"] = int(r.get("restage_n") or 0) + 1
            notices.setdefault(die, []).append(f"{r['item']} unstarted waiter RESTAGED ({why})")
            AP.log(f"KIT-WAVE RESTAGE {die}/{r['item']} unit {r['unit']} ({why})")
            n += 1
    return n


OT_TAG_RE = re.compile(r"--tag (otrun-(\S+)-(\d+)-\d+)\s")


def orphan_waiters(ps_text, node, live_pids, roots=("/kit-wave/",)):
    """remote `ps -eo pid=,ppid=,args=` -> {tag: [pids]} of ot-heavy WAITERS whose hub ot-run client (pid in the tag,
    tag made on hub `node`) is gone and that never started (no ot-heavy-exit / systemd-run child), limited to kit-wave
    item dirs (roots).  The bash -c wrapper carrying the same tag is listed too (ot-run's own cancel = pkill by tag)."""
    rows = []
    for ln in (ps_text or "").splitlines():
        p = ln.split(None, 2)
        if len(p) == 3 and p[0].isdigit() and p[1].isdigit():
            rows.append((int(p[0]), int(p[1]), p[2]))
    kids = {}
    for pid, ppid, a in rows:
        kids.setdefault(ppid, []).append(a)
    tags, started = {}, set()
    for pid, ppid, a in rows:
        m = OT_TAG_RE.search(a + " ")
        if not m or m.group(2) != node or int(m.group(3)) in live_pids or not any(r in a for r in roots):
            continue
        tags.setdefault(m.group(1), []).append(pid)
        if "ot-heavy --mem" in a and any(("ot-heavy-exit" in k or "systemd-run" in k) for k in kids.get(pid, [])):
            started.add(m.group(1))
    return {t: sorted(v) for t, v in tags.items() if t not in started}


def local_otrun_pids():
    out = set()
    for p in os.listdir("/proc"):
        if p.isdigit():
            try:
                if b"ot-run" in Path(f"/proc/{p}/cmdline").read_bytes():
                    out.add(int(p))
            except OSError:
                pass
    return out


def reap_orphan_waiters(AP, cfg):
    """KW-FIX-4 11-03 (COORD 12:1x FLEET): a stopped kit-wave unit's ot-run client cancels its remote waiter with one
    `ssh host pkill --tag` from its signal handler; under a 70-unit stop burst (11:26) those ssh calls were lost and
    35 waiters stayed queued on epyc4 with no client (20 of them for attempt dirs already deleted): they inflate the
    host's waiter count and would start with nobody listening.  Each tick, per remote gen/place host, one ssh lists the
    ot-heavy waiters tagged by THIS hub whose client pid is dead and which never started (kit-wave dirs only) and
    TERMs exactly those pids.  cfg reap_orphan_waiters false opts out."""
    if cfg.get("reap_orphan_waiters") is False:
        return 0
    hub, node = AP.HUB_NAME, os.uname().nodename
    hosts = set()
    for die, d in (cfg.get("dies") or {}).items():
        if isinstance(d, dict):
            hosts |= set(gen_hosts(cfg, die)) | set(d.get("hosts") or [])
    n = 0
    for h in sorted(x for x in hosts if x and x not in ("localhost", hub)):
        live = local_otrun_pids()
        rc, out, _ = AP.sh(_ssh(h, hub) + ["ps -eo pid=,ppid=,args="], timeout=60)
        if rc != 0:
            continue
        orph = orphan_waiters(out, node, live | local_otrun_pids())
        pids = sorted(p for v in orph.values() for p in v)
        if not pids or AP.DRY:
            n += len(orph)
            continue
        AP.sh(_ssh(h, hub) + ["kill -TERM " + " ".join(map(str, pids)) + " 2>/dev/null; true"], timeout=60)
        AP.log(f"KIT-WAVE REAP {h}: {len(orph)} orphan waiter(s) (hub client gone, never started): "
               + " ".join(sorted(orph))[:600])
        n += len(orph)
    return n


def near_count_hit(near, die, *names):
    """(die or '*', name) listed in lanes/NEAR-COUNT.tsv for the item, its parent type or its core module"""
    return any((d, n) in near for n in names if n for d in (die, "*"))


def target_hosts(hosts, hub, allow_hub=False):
    """KW-FIX-45 11-12 (COORD: intel2 is a capped build host again for place/route, never gen): the ot-run --hosts list of a
    heavy stage.  Default: the hub and 'localhost' (ot-run's name for the hub) are dropped.  allow_hub (place stage only): the
    hub stays, spelled 'localhost' once, last; the host's own cap (ot-run HOST_RESERVE, scratch floor) bounds the load."""
    names = (hub, "localhost")
    if not allow_hub:
        return [h for h in hosts if h not in names]
    out = [h for h in hosts if h not in names]
    return out + (["localhost"] if any(h in names for h in hosts) else [])


def hub_names(sp):
    """KW-FIX-45 11-12 (COORD ruling 4, TAP-SITE-1: a place job ran on the hub): the hub and 'localhost' (ot-run's name for it)"""
    return sorted({"localhost", str(sp.get("hub") or "")} - {""})


def crit_args(sp):
    """ot-run admission flags of a NEAR-COUNT item (empty otherwise)"""
    return ["--priority", "die", "--crit"] if sp.get("crit") else []


def heavy_args(sp):
    """KW-FIX-45 11-12: ot-run flags of every heavy kit-wave stage: never the hub (--exclude-hosts) + crit_args"""
    # 11-12: opt-in.  ot-run-lane-declare and ot-run-sealed (in front of ot-run on the hub) reject --exclude-hosts: usage text, NOT RUN
    # (28 QC kit_rtl attempts 11-11 23:25-23:46).  Default off; the host lists and otrun()/place_async refusals keep the hub out.
    return (["--exclude-hosts", ",".join(hub_names(sp))] if sp.get("ot_run_exclude_hosts") else []) + crit_args(sp)


def _ssh(host, hub):
    return [] if host in ("localhost", hub) else ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", host]


SEALED_COPY_BACK = re.compile(r"(?m)^ot-run-sealed: copy-back (\S+) -> (\S+) rc 0\b")


def copy_back_host(txt, default):
    """KW-FIX-46 11-11 (COORD 05:3x, ot_hbm_sm_i8w_front a8): a sealed place run copies its kit back to the host its inputs were
    fetched from ('ot-run-sealed: copy-back intel2 -> epyc7 rc 0'), which is not always the spec's gen host.  The place probe
    and everything after it must look where the sealed run record says the kit is.  Last successful copy-back wins; no record
    (an unsealed run) = the gen host, as before."""
    got = SEALED_COPY_BACK.findall(txt or "")
    return got[-1][1] if got else default


def remote_argv(host, hub, cmd):
    """ssh joins argv with spaces: send ONE quoted command (host None/local = run here)"""
    s = _ssh(host, hub)
    return s + ["bash -c " + shlex.quote(cmd)] if s else ["bash", "-c", cmd]


def geom_result_line(txt):
    """Ignore PNG/GRT status lines after the actual geometry verdict."""
    return next((ln for ln in reversed(txt.splitlines())
                 if ln.startswith("AP_AUTO_GEOM AUTO-GEOM ") or ln.startswith("AP_AUTO_GEOM_ERROR")), "")


def src_skew_check(sp, kit):
    """AUTOBUILD-PIPE-5 10-31 (COORD 04:0x, KIT-WAVE-5 03:47): kit src older than the queue lint.  When the launch spec's
    src_sha has a different copy of the queue's admission lint files than this (hub) checkout, run the hub's own
    sdc_lint on the kit (the hub copy of it, after sync) -- the exact admission verdict, so no false fail; other
    differing lint files are reported (KW_SRC_SKEW), not judged.  -> [errors] ([] = ok / not applicable)."""
    hub_repo = Path(__file__).resolve().parents[2]
    try:
        sys.path.insert(0, str(hub_repo / "tools" / "die_plan"))
        import kit_gen_lint as KGL
    except Exception as e:                      # an old hub without the lint: say so, never block on it
        print(f"KW_NOTE src_skew not checked: {e}", flush=True)
        return []
    _errs, info = KGL.src_skew(sp.get("src_sha", ""), hub_repo)
    print(f"KW_SRC_SKEW {json.dumps(info)}", flush=True)
    if "tools/die_plan/sdc_lint.py" not in (info.get("differ") or []) or not (Path(kit) / "sdc_lint.json").is_file():
        return []
    p = subprocess.run([sys.executable, "-I", str(hub_repo / "tools/die_plan/sdc_lint.py"), str(kit)],
                       capture_output=True, text=True, timeout=600)
    if p.returncode == 0:
        return []
    bad = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.startswith("SDC_LINT ERROR")] or [(p.stdout + p.stderr)[-400:]]
    return [f"kit src {info.get('src')} older than the queue lint {info.get('queue')}: the queue's sdc_lint fails this "
            f"kit ({len(bad)} errors) -> bump the wave src to >= {info.get('queue')} and re-GEN"] + bad[:20]


def outline_cmd(K):
    """shell command printing the kit outline 'WxH' (um). GEOM-91 (OWNER 12.28b): core kits (HBM) carry the plan
    outline in freeze.json, not budget.json; a missing outline made AUTO-GEOM outline=NA = FAIL on every core kit,
    so budget.json outline_um is read first and freeze.json outline_um is the fallback."""
    return (f"python3 -c \"import json,os\nfor f in ('budget.json','freeze.json'):\n p=os.path.join('{K}',f)\n"
            f" o=json.load(open(p)).get('outline_um') if os.path.isfile(p) else None\n"
            f" if o:\n  print(f'{{o[0]}}x{{o[1]}}');break\"")


def region_guide_geom(prev, gen_host):
    """FLOW-23 (COORD 11-02 23:0x, GEOM-111 class D): the previous attempt's AUTO-GEOM dir when it FAILED at the geom
    stage on the gen host (its geom.tsv is read in place), else None.  region_guide.py plan itself writes a spec only
    when that AUTO-GEOM r2r rule FAILED (class D), so every other relaunch gets no guide (kit unchanged).
    QC-FAIL-22 11-10 (COORD): no guide after an INFRA or watchdog relaunch, nor when that AUTO-GEOM passed.  The INFRA
    relaunch path marks the record FAIL before launch while its stage is still geom, so a row that had passed geom
    (advisory-only rule fails count as pass: the row reached the queue, q_id / q_status set) and then hung or was
    stopped got guides on its retry (cbn_q11 a12, slw_fw_v1 a16: GPL-0307 on guides)."""
    ev = str(prev.get("evidence") or "")
    if prev.get("status") != "FAIL" or prev.get("stage") != "geom" or not ev.endswith("/auto_geom.json") or ":" not in ev:
        return None
    if str(prev.get("class") or "") == "INFRA" or prev.get("q_id") or prev.get("q_status") \
            or "watchdog" in str(prev.get("reason") or "").lower():
        return None
    host, path = ev.split(":", 1)
    return path.rsplit("/", 1)[0] if host == gen_host and path.startswith("/") else None


def region_guide_cmd(sp, core):
    """-> (shell prefix that sets RG, ' $RG'): region_guide.py plan on the previous AUTO-GEOM; RG = the generator flag
    (core: --region-guide SPEC; type: --region-guide TYPE=SPEC) only when a class-D spec was written.  A source
    without region_guide.py, a missing geom.tsv or a planner error leaves RG empty (kit unchanged, KW_NOTE)."""
    q = shlex.quote
    gd = sp.get("region_guide_geom")
    if not gd:
        return "RG=; ", ""
    out = f"{sp['work']}/region_guide.json"
    flag = f"--region-guide {out}" if core else f"--region-guide {sp['item']}={out}"
    return (f"RG=; rm -f {q(out)}; if [ -f tools/die_plan/region_guide.py ] && [ -f {q(gd + '/geom.tsv')} ]; then "
            f"python3 tools/die_plan/region_guide.py plan --geom-dir {q(gd)} --out {q(out)} "
            f"|| echo 'KW_NOTE region_guide plan failed: kit without region guide'; "
            f"if [ -s {q(out)} ]; then RG={q(flag)}; fi; "
            f"else echo 'KW_NOTE no region_guide.py in this source or no previous geom.tsv: kit without region guide'; fi; "
            f"echo \"KW_REGION_GUIDE ${{RG:-none}}\"; "), " $RG"


def work_alt_cmd(work, alt_lane):
    """KW-FIX-38 11-08: shell that makes a FRESH attempt dir a symlink to the same path on the host's scratch2 (the form of
    KW-FIX-37's 19:46 re-link, realpath-safe for autoclean).  An existing link or any content other than an empty logs/
    keeps the dir as it is; the attempt then runs on the lane where it stands."""
    q = shlex.quote
    alt = alt_lane.rstrip("/") + "/" + os.path.normpath(work)[len(lane_root(work)):].lstrip("/")
    return (f"W={q(work)}; A={q(alt)}; "
            'if [ -L "$W" ]; then echo "KW_WORK_ALT kept existing link $W"; '
            # KW-FIX-39 11-08: when a parent of W is itself a link to scratch2 (attempt 1's W was the item dir), W and A are the
            # same path: rmdir W + ln -s A W made a self-link (q_sm0/q_sm3/q_b003 a2: 'mkdir: Already exists')
            'elif [ "$(readlink -m "$W")" = "$(readlink -m "$A")" ]; then echo "KW_WORK_ALT already on the alternative lane $W"; '
            'elif [ -d "$W" ] && [ -n "$(find "$W" -mindepth 1 -not -path "$W/logs" -print -quit 2>/dev/null)" ]; then '
            'echo "KW_WORK_ALT kept non-empty dir $W"; '
            'else mkdir -p "$A" "$(dirname "$W")" && { rmdir "$W/logs" 2>/dev/null; rmdir "$W" 2>/dev/null; true; } && '
            'if [ -e "$W" ]; then echo "KW_WORK_ALT kept dir $W"; else ln -s "$A" "$W" && echo "KW_WORK_ALT $W -> $A"; fi; '
            'fi; true')


FUTURE_LEC_FILES = ("lec.py", "TOOL.json", "kit_resume.py", "run_kit_template.sh", "future_kit_lec.py")


def future_lec_snapshot(snapshot, commit=None):
    """write the future-LEC tool snapshot (lec.py, kit_resume.py, the gen_phys RUN_KIT template, future_kit_lec.py and
    TOOL.json) into SNAPSHOT -> meta.  commit None: the scheduler checkout's HEAD, whose working lec.py / kit_resume.py
    must equal the committed bytes (a new attempt, as before).  commit set: the bytes of that commit (KW-FIX-44 11-10:
    run_item re-staging a spec's pinned snapshot)."""
    import ast, hashlib
    snapshot = Path(snapshot)
    snapshot.mkdir(parents=True, exist_ok=True)   # an attempt whose launch failed before its unit started is taken again
    repo = Path(__file__).resolve().parents[1] / "die_plan"
    show = lambda c, f, text=False: subprocess.run(["git", "-C", str(repo), "show", f"{c}:{f}"], check=True,
                                                   capture_output=True, text=text).stdout
    if commit is None:
        source = repo / "lec.py"
        payload = source.read_bytes()
        commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True).stdout.strip()
        if payload != show(commit, "tools/die_plan/lec.py"):
            raise ValueError("future LEC scheduler file differs from committed main tool")
        resume_helper = Path(KR.__file__).read_bytes()
        if resume_helper != show(commit, "tools/autopilot/kit_resume.py"):
            raise ValueError("resume helper differs from pinned scheduler commit")
    else:
        payload = show(commit, "tools/die_plan/lec.py")
        resume_helper = show(commit, "tools/autopilot/kit_resume.py")
    tree = ast.parse(show(commit, "tools/die_plan/gen_phys.py", text=True))
    template = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "RUN_KIT" for t in n.targets))
    (snapshot / "kit_resume.py").write_bytes(resume_helper)
    (snapshot / "run_kit_template.sh").write_text(template)
    meta = dict(commit=commit, sha256=hashlib.sha256(payload).hexdigest(),
        runner_template_sha256=hashlib.sha256(template.encode()).hexdigest(),
        resume_helper_sha256=hashlib.sha256(resume_helper).hexdigest())
    (snapshot / "lec.py").write_bytes(payload)
    (snapshot / "TOOL.json").write_text(json.dumps(meta) + "\n")
    (snapshot / "future_kit_lec.py").write_bytes(Path(__file__).with_name("future_kit_lec.py").read_bytes())
    return meta


def future_lec_for(cfg, die, snapshot):
    """the future-LEC snapshot of a new attempt.  KW-FIX-43 11-10 (COORD class fix, false LEC NOT EQUIVALENT on the
    3c6f29fb pin; q_b100__physical_v1 a13 proves EQUIVALENT 101,250/101,250 with main >= f502d8a): option
    future_lec_commit (die > global) pins lec.py / kit_resume.py / the RUN_KIT template to that reviewed commit of the
    scheduler repo; unset = the scheduler checkout HEAD, as before."""
    return future_lec_snapshot(snapshot, commit=opt(cfg, die, "future_lec_commit") or None)


def ensure_future_lec(out, meta):
    """KW-FIX-44 11-10 (COORD, LEC-SNAP class: TYPE-SAFE-5 p4, st_b_v2 a2, sfw_proof a6 failed lec_tools_copy rsync rc 23
    after their queue wait because the spec named a snapshot that was never staged next to it).  Before any stage: a
    complete snapshot whose TOOL.json is the spec's meta is used as is; otherwise it is staged here from the spec's
    commit and kept only when every sha equals the spec's.  -> '' (ready) or the reason to fail now."""
    import shutil, tempfile
    out = Path(out)
    snap = out / "future_lec"
    want = {k: meta.get(k) for k in ("commit", "sha256", "runner_template_sha256", "resume_helper_sha256")}
    try:
        have = json.loads((snap / "TOOL.json").read_text())
    except (OSError, ValueError):
        have = None
    if have is not None and {k: have.get(k) for k in want} == want and all((snap / f).is_file() for f in FUTURE_LEC_FILES):
        return ""
    if not want["commit"]:
        return f"spec future_lec names no commit; cannot stage {snap}"
    tmp = Path(tempfile.mkdtemp(prefix=".future_lec-", dir=str(out)))
    try:
        got = future_lec_snapshot(tmp, commit=want["commit"])
    except (subprocess.CalledProcessError, ValueError, StopIteration, OSError, SyntaxError) as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return f"future_lec snapshot {snap} missing/incomplete and commit {want['commit']} cannot be read here: {str(e)[:200]}"
    bad = [k for k in want if got.get(k) != want[k]]
    if bad:
        shutil.rmtree(tmp, ignore_errors=True)
        return (f"future_lec snapshot {snap} missing/incomplete; re-staged from {want['commit']} but "
                + ", ".join(f"{k} {str(got.get(k))[:12]} != spec {str(want[k])[:12]}" for k in bad))
    if snap.exists():
        snap.rename(out / f".future_lec.incomplete-{int(time.time())}")    # kept for diagnosis, never deleted here
    tmp.rename(snap)
    print(f"KW_FUTURE_LEC staged {snap} from {want['commit'][:12]} (sha {want['sha256'][:12]})", flush=True)
    return ""


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
            # stderr streams to <stage>.live.log so the tick can see whether ot-run already started the command
            # ('ot-heavy: admitted on') or it still waits in the memory queue (cancel_class_volume)
            live = out / f"{stage}.live.log"
            with open(live, "w") as ef:
                p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=ef, text=True, timeout=timeout)
            txt = (p.stdout or "") + (getattr(p, "stderr", None) or "") + live.read_text(errors="replace")
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

    def otrun(mem, thr, d, cmd, hosts, allow_hub=False):  # ot-run names the hub itself 'localhost'
        hosts = target_hosts(hosts, hub, allow_hub)       # KW-FIX-45 11-12: only the place stage may target the hub (capped by ot-run), never gen
        if not hosts:
            raise RuntimeError("heavy stage refused: every target host is the hub (KW-FIX-45 hub guard)")
        return [sp["ot_run"], "--mem", str(mem), "--threads", str(thr), "--dir", d, "--hosts", ",".join(hosts)] \
            + heavy_args(sp) + ["--", "bash", "-c", cmd]

    def fail(stage, txt, evidence=""):
        res.update(stage=stage, verdict="FAIL", tail=txt[-3000:], errors=error_lines(txt), evidence=evidence or f"{G}:{W}")
        (out / "result.json").write_text(json.dumps(res, indent=1))
        return 1

    def after_place(K, rc, txt):
        """probe the placed kit on the gen host, AUTO-GEOM it, write result.json (sync PLACE, and an async PLACE
        released by its fresh physical_completion receipt while the original proof owner keeps running)"""
        kh = copy_back_host(txt, G)      # the host that holds the kit (sealed copy-back record)
        rem = lambda cmd: remote_argv(kh, hub, cmd)
        if kh != G:
            print(f"KW_KIT_HOST {T}: sealed copy-back put the kit on {kh}, not the gen host {G}", flush=True)

        probe = (f"ls {q(K)}/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1; "
                 f"cat {q(K)}/FAIL_* 2>/dev/null | head -5; "
                 f"if [ -f {q(K)}/native_cell_count.json ]; then sed 's/^/NATIVE_CELL_COUNT /' {q(K)}/native_cell_count.json; fi; "
                 f"grep -h -i -E 'Number of cells|Chip area' {q(K)}/run/reports/asap7/*/base/synth_stat.txt 2>/dev/null | head -2; "
                 # DIE-HBM-97 11-10: GPL-1010 cap lines for classify() (gpl-noconverge); the stage tail does not reach them
                 f"for f in {q(K)}/run/logs/asap7/*/base/3_3_place_gp*.log; do [ -f \"$f\" ] && {GPL_PROBE_AWK} \"$f\"; "
                 f"done 2>/dev/null | tail -40; "
                 f"ls -t {q(K)}/run/logs/asap7/*/base/*.log 2>/dev/null | head -1 | xargs -r tail -30")
        _, ptxt = run("place_probe", rem(probe), idempotent=True)
        odb = next((ln for ln in ptxt.splitlines() if ln.endswith("3_place.odb")), "")
        cells = re.search(r"Number of cells:?\s+(\d+)", ptxt)
        res["cells"] = int(cells.group(1)) if cells else None
        native = re.search(r"(?m)^NATIVE_CELL_COUNT (\{[^\n]+\})$", ptxt)
        if native:
            count = json.loads(native.group(1))
            if count.get("schema") == "opentallas.native_cell_count.v1" and type(count.get("stdcells")) is int:
                res["cells"] = count["stdcells"]
                res["cells_basis"] = "actual synthesized top standard cells, excluding block macros"
                if type(count.get("limit")) is int:
                    res["cells_limit"] = min(count["limit"], CELL_CAP_MAX)
        if sp.get("cell_check") and res["cells"]:
            cc_cmd = (f"cd / && python3 -I {q(src)}/tools/die_plan/cell_check.py --plan {q(sp['plan'])} --type {q(T)} "
                      f"--cells {int(res['cells'])} --stat \"$(ls {q(K)}/run/reports/asap7/*/base/synth_stat.txt | head -1)\"")
            _, cct = run("cell_check", rem(cc_cmd), idempotent=True)
            m = re.search(r"(?m)^CELL_CHECK (\{.*\})$", cct)
            if m:
                try:
                    res["cell_check"] = json.loads(m.group(1))
                except ValueError:
                    pass
        if rc or not odb:
            return fail("place", txt[-2000:] + "\n" + ptxt, f"{kh}:{K}")
        if res["cells"] and res["cells"] > res.get("cells_limit", CELL_CAP):
            return fail("cells", f"{res['cells']} cells", f"{kh}:{K}")
        olc = outline_cmd(K)
        _, ol = run("outline", rem(olc), idempotent=True)
        ol = ol.strip().splitlines()[-1] if ol.strip() else ""
        chk = {"id": f"kw-{T}".replace("_", "-")[:60], "odb": odb, "image": "openroad/orfs:asap7lock", "mem_gb": sp["geom_mem_gb"],
               "grt": True, "grt_wall_s": int(sp.get("geom_grt_wall_s", 1800)), "rules_args": ["--all-kits"] + (["--outline", ol] if re.fullmatch(r"[\d.]+x[\d.]+", ol) else [])
               + ["--title", f"{T} KIT-WAVE {sp['event']} 3_place"]}
        gd = f"{W}/geom"
        rc, txt = run("geom_cfg", idempotent=True, argv=rem(f"mkdir -p {q(gd)} && cat > {q(gd)}/check.json <<'EOF'\n{json.dumps(chk)}\nEOF"))
        if rc:
            return fail("geom_cfg", txt)
        rc, txt = run("geom", otrun(sp["geom_mem_gb"], 4, W, f"bash {q(src)}/tools/autopilot/geom_check.sh {q(gd)}", [kh]))
        line = geom_result_line(txt)
        res.update(geom_dir=f"{kh}:{gd}", geom_line=line[:600], odb=odb, kit=f"{kh}:{K}")
        if not line or line.startswith("AP_AUTO_GEOM_ERROR") or not re.search(r"AUTO-GEOM (PASS|FAIL)\b", line):
            # geom_check.sh exits 1 on a FAIL verdict: only a missing verdict line is a run error
            return fail("geom_run", txt[-3000:], f"{kh}:{gd}")
        v, failing, tag = geom_gate(line, sp.get("geom_waivers"), sp.get("geom_advisory", True))
        if v not in ("PASS", "PASS-COND"):
            return fail("geom", line, f"{kh}:{gd}/auto_geom.json")
        res.update(stage="geom", verdict="PASS", geom=v, geom_tag=tag, evidence=f"{kh}:{gd}/auto_geom.json")
        (out / "result.json").write_text(json.dumps(res, indent=1))
        return 0

    svc_file = out / "place_service.json"

    def save_svc(svc):
        tmp = svc_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(svc, indent=1) + "\n")
        tmp.replace(svc_file)

    def place_receipt(K, svc):
        """a fresh PLACE physical_completion receipt of this attempt's kit on the gen host (lec_async.sh phase_done):
        rc 0, started after the service, 3_place checkpoint still the exact recorded file, no LEC stop / FAIL mark"""
        cmd = f"python3 - {q(K)} {float(svc['started'])} <<'KWPY'\n{PLACE_RECEIPT}\nKWPY"
        try:
            p = subprocess.run(remote(cmd), capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return None
        got = [ln[len("KW_PLACE_RECEIPT "):] for ln in (p.stdout or "").splitlines() if ln.startswith("KW_PLACE_RECEIPT ")]
        return json.loads(got[-1]) if p.returncode == 0 and got else None

    def place_wait(svc):
        """FLOW-21 11-01 (COORD 08:2x, CODEX async/PLACE handoff): the PLACE client runs in its own systemd unit, so the
        worker returns on the fresh PLACE receipt while the admitted proof owner (async pre-route LEC) runs on.  A
        terminal client rc wins; a client lost before its rc is a FAIL that never launches a duplicate proof."""
        res["stage"] = "place"
        print(f"KW_STAGE place {now_s()} :: service {svc['unit']} {' '.join(shlex.quote(a) for a in svc['argv'])[:500]}",
              flush=True)
        logs.append("place")
        logf = Path(svc["log"])
        while True:
            act = subprocess.run(["systemctl", "--user", "is-active", svc["unit"]], capture_output=True, text=True,
                                 timeout=60)
            txt = logf.read_text(errors="replace") if logf.exists() else ""
            rcs = re.findall(r"(?m)^KW_PLACE_RC=(-?\d+)\s*$", txt)
            if rcs:
                (out / "place.log").write_text(txt)
                print(f"KW_STAGE_RC place {rcs[-1]} (client ended)", flush=True)
                return int(rcs[-1]), txt, None
            if (act.stdout or "").strip() not in ("active", "activating", "reloading"):
                txt += ("\nKW_PLACE_LOST: the PLACE service unit ended without a terminal rc; its kit and any proof "
                        "owner are kept, no duplicate PLACE/proof is launched\n")
                (out / "place.log").write_text(txt)
                return 1, txt, None
            r = place_receipt(svc["kit"], svc)
            if r:
                svc["receipt"] = r
                save_svc(svc)
                (out / "place.log").write_text(txt + f"\nKW_PLACE_RECEIPT {json.dumps(r)}\n")
                print(f"KW_STAGE_RC place 0 (physical receipt {r.get('path')}; proof owner {r.get('proof_owner')} "
                      f"{'pending' if r.get('proof_pending') else 'done'})", flush=True)
                return 0, txt, r
            time.sleep(PLACE_POLL_S)

    def place_async(K, prun, m, t):
        """launch (once per attempt: the descriptor is saved before systemd-run) and wait"""
        if svc_file.exists():
            return place_wait(json.loads(svc_file.read_text()))
        if G in ("localhost", hub):                  # KW-FIX-45 11-12 hub guard: the kit's gen host is the hub
            msg = f"KW_PLACE_REFUSED: heavy stage place refuses to run on the hub ({G}); pick a fleet gen host (KW-FIX-45 hub guard)"
            (out / "place.log").write_text(msg + "\n")
            return 1, msg, None
        cmd = f"bash {shlex.quote(prun)} {shlex.quote(K)} place {m} {t}"
        if sp.get("place_spill", True):
            # KW-FIX-4 11-03 (ONBOARD-1 ask, COORD approved): no --hosts pin (a pin disables ot-run SPILL / LOAD SPILL /
            # RE-PLACE); --stage = the kit dir + its runner, so a waiter the gen host cannot admit (or that would
            # overload it) is copied to a host that admits it NOW (epyc4), runs there and copies every written file
            # back before the client exits.  SPILL-PROOF-1 11-04: OT_RUN_SPILL_HANDOFF (ot-run spill_handoff, below) hands
            # the physical result to G at phase_done while the proof owner stays admitted on the spill host; the proof's
            # own files follow at client end and G:K is the one physical /work, so route runs there.  Without a hand-off
            # the receipt appears on G at the client's end (KW_PLACE_RC wins).  Die option place_spill false = the old pin.
            argv = ([sp["ot_run"], "--mem", str(m), "--threads", str(t), "--dir", K, "--stage", K, "--stage", prun]
                    + heavy_args(sp) + ["--", "bash", "-c", cmd])
        else:
            argv = otrun(m, t, K, cmd, [G])
        unit = "kwp-" + hashlib.sha256(str(out.resolve()).encode()).hexdigest()[:20]
        svc = {"schema": "opentallas.kw_place_service.v1", "unit": unit, "argv": argv, "kit": K, "host": G,
               "started": time.time(), "log": str(out / "place.live.log"), "launch": "prepared"}
        save_svc(svc)
        inner = " ".join(shlex.quote(a) for a in argv)
        cmd = ["systemd-run", "--user", "--quiet", "--collect", f"--unit={unit}",
               f"--setenv=PATH={HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin", f"--setenv=HOME={HOME}",
               "--setenv=OT_RUN_SPILL_HANDOFF=place", "--property=TimeoutStopSec=120", "/bin/bash", "-c",
               f"exec >> {shlex.quote(svc['log'])} 2>&1; echo KW_PLACE_START $(date +%s) {unit}; "
               + place_retry_sh(inner, svc["log"]) + "; echo KW_PLACE_RC=$rc"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        svc["launch"] = "launched" if p.returncode == 0 else "failed"
        save_svc(svc)
        if p.returncode:
            svc_file.replace(out / "place_service.failed.json")      # never started: a retry may launch it
            return 1, f"Connection closed: systemd-run of the PLACE service failed rc {p.returncode}: {p.stderr[-300:]}", None
        return place_wait(svc)

    q = shlex.quote
    src, plan = sp["src"], sp["plan"]
    gh = [G]
    if sp.get("future_lec"):                             # KW-FIX-44 11-10: before any queue wait, not at lec_tools_copy
        why = ensure_future_lec(out, sp["future_lec"])
        if why:
            return fail("lec_tools_preflight", "KW_FUTURE_LEC FAIL " + why)
    time.sleep(max(0.0, float(sp.get("start_delay_s") or 0)))   # stagger a tick's burst of items (gen-host sshd)
    if svc_file.exists():
        # a restarted worker of this attempt: the saved PLACE service owns W/gen (and maybe a live proof);
        # never regenerate, delete or relaunch it -- resume waiting on the same client / receipt
        svc = json.loads(svc_file.read_text())
        rc, txt, _ = place_wait(svc)
        res["ran_on"] = G
        try:
            return after_place(svc["kit"], rc, txt)
        finally:
            run("resume_release", remote(kr_cmd(f"release {q(svc['kit'])}")), idempotent=True)
    if sp.get("work_alt_lane"):                          # KW-FIX-38: fresh attempt on the host's scratch2 (best effort)
        run("work_alt", idempotent=True, argv=remote(work_alt_cmd(W, sp["work_alt_lane"])))
    rc, txt = run("mkdir", idempotent=True, argv=remote(f"mkdir -p {q(W)}/logs {q(sp['root'])} && rm -rf {q(W)}/gen {q(W)}/rtl {q(W)}/geom"))
    if rc:
        return fail("mkdir", txt)
    plan0 = plan                                          # the die's plan of record (shared die bind prep, kit RTL)
    kr = sp["kit_rtl"]
    kit_rtl_arg = ""
    core = sp.get("kind") == "core" and bool(sp.get("core_kit"))
    ks_on = bool(sp.get("kit_store")) and kit_store_applies(sp)
    if ks_on:
        # KIT-INPUT-STORE-1: every input this kit reads -> W/kit_inputs (hardlinks from the per-host dedupe store); the
        # rest of the pipeline sees only kit-local paths, so a pruned lane worktree can no longer break a relaunch
        mp, why = kit_store_stage(sp, run, remote, res, W, plan)
        if mp is None:
            return fail("kit_store", why)
        plan = plan0 = ks_map(plan, mp)
        kr = ks_map(kr, mp)
        if sp.get("type_overlay"):
            sp["type_overlay"] = ks_map(sp["type_overlay"], mp)
        sp["plan"], sp["kit_rtl"] = plan, kr
        sp["gen_args"] = ks_map(list(sp.get("gen_args") or []), mp)
        sp["gen_env"] = ks_map(dict(sp.get("gen_env") or {}), mp)
    # DIE-KV-69 11-04: die option prov_first_re names types whose planned children have no source under the manifest
    # roots (KV PCC / PCF, results/kv_host_regen_1/rtl_rf3).  bind kit-rtl finds such a child only through the view an
    # overlay plan row binds, so these types build the overlay first and run kit-rtl on it.  Every other type keeps
    # kit RTL -> overlay.
    prov_first = bool(sp.get("prov_views") and not core and sp.get("prov_first_re")
                      and re.search(sp["prov_first_re"], T))
    if prov_first:
        plan, prc = prov_stage(sp, run, remote, fail, res)
        if plan is None:
            return prc
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
        rgp, rga = region_guide_cmd(sp, True)
        rc, txt = run("gen", otrun(sp["gen_mem_gb"], 2, W, f"cd {q(src)} && {rgp}{gcmd}{rga}", gh))
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
            cmd = cmd.format(plan=q(plan0), bind=q(bind), asbuilt=q(a), src=q(src))
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
        if ks_on:
            rc, txt = run("kit_store_fl", remote(ks_cmd(f"localize-filelist {q(W)}/rtl/kit_rtl.f --kit-root {q(W)} "
                                                        f"--kit-inputs {q(W)}/kit_inputs")), idempotent=True)
            if rc:
                return fail("kit_store", txt)
            res["kit_store_fl"] = (txt.strip().splitlines() or [""])[-1][:400]
        kit_rtl_arg = f"--kit-rtl {q(T + '=' + W + '/rtl/kit_rtl.f')}"
    elif kr.get("mode") == "script":
        rc, txt = run("kit_rtl", otrun(8, 2, W, f"cd {q(src)} && TYPE={q(T)} OUT={q(W)}/rtl PLAN={q(plan)} bash {q(kr['script'])}", gh))
        if rc:
            return fail("kit_rtl", txt)
        if ks_on:
            rc, txt = run("kit_store_fl", remote(ks_cmd(f"localize-filelist {q(W)}/rtl/kit_rtl.f --kit-root {q(W)} "
                                                        f"--kit-inputs {q(W)}/kit_inputs")), idempotent=True)
            if rc:
                return fail("kit_store", txt)
            res["kit_store_fl"] = (txt.strip().splitlines() or [""])[-1][:400]
        kit_rtl_arg = f"--kit-rtl {q(T + '=' + W + '/rtl/kit_rtl.f')}"
    if sp.get("prov_views") and not core and not prov_first:
        # KW-PROV-1: build against PROVISIONAL child views (latest routed DRC-clean abstract, else the plan-contract
        # abstract) through an overlay plan; the kit is marked PROVISIONAL and never counted until the STA-only re-sign.
        # After kit RTL (bind kit-rtl reads no child view): the kit RTL is the first source of child port directions
        plan, prc = prov_stage(sp, run, remote, fail, res, rtl=f"{W}/rtl" if kit_rtl_arg else "")
        if plan is None:
            return prc
    plan_ov = plan                       # plan the station preparation reads (istations.tcl sites follow the overlay)
    ov_arg = ""
    if sp.get("type_overlay") and not core:
        # KIT-OVERLAY-1: fail closed on a source without the flag; the overlaid plan (type-scoped validation, EQ projection)
        # feeds prepare-stations so the FIRM station sites match the placement; gen phys applies the same overlay itself.
        ovp = q(sp["type_overlay"])
        rc, txt = run("type_overlay", otrun(8, 2, W, f"cd {q(src)} && python3 tools/die_plan/gen.py phys --help 2>/dev/null | grep -q -- --type-overlay "
                                                     f"&& python3 -I tools/die_plan/type_overlay.py apply {q(plan)} {ovp} --out {q(W)}/plan_overlaid.json "
                                                     f"|| {{ echo 'KW_TYPE_OVERLAY source has no --type-overlay or the overlay is rejected'; exit 1; }}", gh))
        if rc:
            return fail("type_overlay", txt)
        plan_ov = f"{W}/plan_overlaid.json"
        ov_arg = f" --type-overlay {ovp}"
    if not core and kit_rtl_arg and sp.get("canonical_topology_prepare"):
        # One canonical implementation for both bind and script callers, after
        # the actual typed overlay and before any physical generation.
        helper = f"{src}/tools/die_plan/kit_topology.py"
        context_args = f" --asbuilt {q(kr['asbuilt'])}" if kr.get("asbuilt") else ""
        prep = (f"cd {q(src)} && {topology_env_prefix(sp)}python3 -I {q(helper)} prepare-stations {q(plan_ov)} {q(T)} {q(W)}/rtl "
                f"--native-plan {q(plan0)}{context_args}")
        rc, txt = run("kit_topology", otrun(8, 2, W, prep, gh))
        if rc:
            return fail("kit_topology", txt)
    if not core:
        ps = sp.get("cland_pinslot") or ""
        # a wave source checkout older than gen phys --cland-pinslot keeps the plan-only pinslot (noted in the gen log)
        pin = (f"PS=; if python3 tools/die_plan/gen.py phys --help 2>/dev/null | grep -q -- --cland-pinslot; then "
               f"PS='--cland-pinslot {ps}'; else echo 'KW_NOTE gen.py of this source has no --cland-pinslot (plan list only)'; fi; "
               if ps and re.fullmatch(r"[A-Za-z0-9_,]+", ps) else "PS=; ")
        rgp, rga = region_guide_cmd(sp, False)
        genv = "".join(f"export {k}={q(v)}; " for k, v in sorted((sp.get("gen_env") or {}).items()))
        gen = (f"cd {q(src)} && {genv}{pin}{rgp}python3 tools/die_plan/gen.py phys {q(plan)} --out {q(W)}/gen --types {q(T)} "
               f"--rtl-root {q(src)} {kit_rtl_arg} $PS {' '.join(q(x) for x in sp['gen_args'])}{rga}{ov_arg}")
        rc, txt = run("gen", otrun(sp["gen_mem_gb"], 2, W, gen, gh))
        if rc:
            return fail("gen", txt)
        rc, _ = run("gen_kit", idempotent=True, argv=remote(f"test -f {q(K)}/config.mk || test -f {q(K)}/freeze.json"))
        if rc:
            return fail("gen", txt + "\nGEN_NO_KIT: gen.py exit 0 but wrote no kit for this type (hard type? see gen --hard-wrappers)")
    if sp.get("prov_views"):
        # KW-PROV-1 marker: the kit carries provisional_views.json (autopilot classify turns its SIGNED into
        # LOCAL_PASS_NEEDS_PARENT = WAIT-PARENT until every child view is FINAL) and W/gen/PROVENANCE.json says
        # PROVISIONAL, so release_tree_plan never counts it as a versioned sign-off
        # KW-FIX-35-V: a marker FINAL (every child = its counted signed view) is a normal kit: no PROVISIONAL provenance
        final = q("import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get('status') == 'FINAL' else 1)")
        pv = (f"cp {q(W)}/prov/provisional_views.json {q(K)}/provisional_views.json && "
              f"{{ python3 -I -c {final} {q(K)}/provisional_views.json || python3 -c "
              + q("import json,sys;json.dump({'schema':'opentallas.provisional_view.v1','verdict':'PROVISIONAL',"
                  "'note':'KW-PROV-1: built on provisional child views; STA-only re-sign on the signed child libs owed'},"
                  "open(sys.argv[1],'w'))") + f" {q(W)}/gen/PROVENANCE.json; }}")
        rc, txt = run("prov_mark", remote(pv), idempotent=True)
        if rc:
            return fail("prov_views", txt)
    # SAFE-STATION-1 11-03: relay-bay station form on wire-only station kits (class default, see RELAY_BAY_RE).  The tool
    # and its computed hop rows come from the scheduler checkout (the wave src is pinned and may predate them), staged
    # into W/relay_bay; it rewrites K in place (extra relays, plan bays, repeater pitch, declared_cycles.json) or fails
    # closed with FAIL_PREBUILD relay_bay before any gate / build.  Before resume_inputs, so a resume fingerprints it.
    rbre = sp.get("relay_bay_re") or ""
    if not core and rbre and re.search(rbre, T):
        rbd = Path(__file__).resolve().parents[1] / "die_plan"
        staged = f"{W}/relay_bay"
        rc, txt = run("relay_bay_dir", remote(f"mkdir -p {q(staged)}"), idempotent=True)
        if rc:
            return fail("relay_bay", txt)
        dest = staged + "/" if G in ("localhost", hub) else f"{G}:{staged}/"
        rc, txt = run("relay_bay_copy", ["rsync", "-a", "-e", "ssh -o BatchMode=yes -o ControlPath=none",
            str(rbd / "relay_bay.py"), str(rbd / "relay_bay_hop_rows.json"), str(rbd / "grt_maxwire.tcl"), dest], idempotent=True)
        if rc:
            return fail("relay_bay", txt)
        rc, txt = run("relay_bay", remote(f"python3 -I {q(staged)}/relay_bay.py {q(K)} --rows {q(staged)}/relay_bay_hop_rows.json"))
        if rc:
            return fail("relay_bay", txt, f"{G}:{K}/relay_bay_table.tsv")
        res["relay_bay"] = (txt.strip().splitlines() or [""])[-1][:300]
    # KW-FIX-17 LEAFSLEW form (COORD 11-05 16:4x): stage physical/common_flow/clk_leaf_repeat.tcl from the scheduler
    # checkout into K (a kit's own copy is kept) and chain it ahead of the kit's POST_CTS_TCL in config.mk; before
    # resume_inputs, so a stage resume restarts at CTS (POST_CTS_TCL / OT_CLR_NEXT_TCL are cts-stage inputs)
    lsf = sp.get("leafslew_form")
    if lsf:
        src_tcl = Path(__file__).resolve().parents[2] / "physical" / "common_flow" / LEAFSLEW_TCL
        dest = K + "/" if G in ("localhost", hub) else f"{G}:{K}/"
        rc, txt = run("leafslew_copy", ["rsync", "-a", "--ignore-existing", "-e", "ssh -o BatchMode=yes -o ControlPath=none",
                                        str(src_tcl), dest], idempotent=True)
        if rc:
            return fail("leafslew", txt)
        rc, txt = run("leafslew", remote(leafslew_patch_cmd(K, lsf)), idempotent=True)
        if rc:
            return fail("leafslew", "KW_LEAFSLEW patch failed (no config.mk / hook not staged)\n" + txt, f"{G}:{K}/config.mk")
        res["leafslew_form"] = (re.findall(r"KW_LEAFSLEW [^\n]*", txt) or ["KW_LEAFSLEW"])[-1][:200]
    # New-attempt tool update only, before any physical/proof work or resume copy.
    # The generator source stays pinned; record the independent scheduler LEC snapshot.
    lt = sp.get("future_lec")
    if lt:
        staged = f"{W}/future_lec"
        rc, txt = run("lec_tools_dir", remote(f"mkdir -p {q(staged)}"), idempotent=True)
        if rc:
            return fail("lec_tools", txt)
        dest = staged + "/" if G in ("localhost", hub) else f"{G}:{staged}/"
        rc, txt = run("lec_tools_copy", ["rsync", "-a", "-e", "ssh -o BatchMode=yes -o ControlPath=none",
            str(out / "future_lec") + "/", dest], idempotent=True)
        if rc:
            return fail("lec_tools", txt)
        rc, txt = run("lec_tools", remote(f"python3 {q(staged)}/future_kit_lec.py {q(K)} "
            f"{q(staged)}/lec.py {q(staged)}/TOOL.json "
            f"{q(runner.format(kit=K, work=W) if core else W + '/gen/run_kit.sh')} {q(staged)}/run_kit_template.sh"))
        if rc:
            return fail("lec_tools", txt)
        res["future_lec"] = lt
    # KW-RESUME-1: record the kit's gen-time inputs (K/.kw_inputs.json) before any gate writes into K; a later
    # relaunch fingerprints against this record.  Advisory: a failure only means the next relaunch uses the mtime rule.
    run("resume_inputs", remote(kr_cmd(f"inputs {q(K)}")), idempotent=True)
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
    # KW-FIX-44 11-10 (DIE-KV-97): the contract advisories of this --plan-dir run (macro_pin_grid, macro_channels ...)
    # were only in the receipt and one log line; they go into result.json and the row.  Advisory: never stops the kit.
    _, rtxt = run("preflight_adv", remote(f"cat {q(W)}/{pfo}"), idempotent=True)
    res["preflight_advisory"] = preflight_advisory(rtxt)
    # the kit (a few MB) goes to the same path on every allowed host; ot-run then picks the least-loaded one.
    # Fleet hosts do not resolve each other by name (intel1 -> intel2/epyc2 fails), so the hub (where this unit
    # runs) relays: gen host -> hub -> other hosts, and the placed kit comes back the same way.
    SSHE = "-e 'ssh -o BatchMode=yes -o ControlPath=none'"
    on_hub = G in ("localhost", hub)
    if not on_hub:
        rc, txt = run("sync_hub", idempotent=True, argv=["bash", "-c", f"mkdir -p {q(W)}/gen && rsync -a --delete {SSHE} {G}:{q(W)}/gen/ {q(W)}/gen/"])
        if rc:
            return fail("sync_hub", txt)
    # AUTOBUILD-PIPE-5 10-31: the queue's own sdc_lint on the hub copy of the kit when the wave src's lint differs
    sk = src_skew_check(sp, K)
    if sk:
        return fail("gen_lint", "GEN_LINT FAIL src_skew\n" + "\n".join(sk), f"{G}:{K}")
    def place_and_geom(K, rs):
        """PLACE (async service or ot-run) + after_place; rs = the stage-resume start step or ''"""
        # FLOW-21 11-01 (COORD 08:2x): kits whose runner hands the pre-route LEC to lec_async.sh (phase receipts) PLACE
        # as a detached service on the gen host itself: that kit dir is the one authoritative copy (proof owner, GEOM,
        # enqueue and the route all use G:K), so it is never relayed, pulled or cleaned while its proof runs.
        asy = False
        if sp.get("place_async", True) and G in sp["hosts"] + ["localhost", hub]:
            _, at = run("place_mode", idempotent=True, argv=remote(
                f"test -f {q(K)}/lec_async.sh && grep -q phase_done {q(K)}/lec_async.sh && test -f {q(K)}/lec.py "
                f"&& echo KW_ASYNC_OK || echo KW_ASYNC_NO"))
            asy = "KW_ASYNC_OK" in at
        res["place_async"] = asy
        if asy:
            if not on_hub:
                run("clean_hub", ["bash", "-c", f"rm -rf {q(W)}/gen"])   # pre-place relay copy (lint only)
            m, t = sp["place_mem_gb"], sp["place_threads"]
            prun = (runner.format(kit=K, work=W) if core else f"{W}/gen/run_kit.sh")
            rc, txt, rcpt = place_async(K, prun, m, t)
            res["ran_on"] = G
            if rcpt:
                res["place_receipt"] = rcpt
            return after_place(K, *resume_verify(rs, rc, txt))
        # a resumed kit's run/ holds hardlinks into the previous attempt on G: it PLACEs on G only (a relay would copy GBs)
        for h in ([] if rs else [h for h in sp["hosts"] if h not in (G, hub, "localhost")]):
            cp = (f"ssh -o BatchMode=yes -o ControlPath=none {h} mkdir -p {q(W)}/gen && "
                  f"rsync -a --delete {SSHE} {q(W)}/gen/ {h}:{q(W)}/gen/")
            rc, txt = run(f"sync_{h}", ["bash", "-c", cp], idempotent=True)
            if rc:
                return fail(f"sync_{h}", txt)
        m, t = sp["place_mem_gb"], sp["place_threads"]
        phosts = [G] if rs else sp["hosts"]
        pref = [h for h in sp.get("place_prefer") or [] if h in phosts]
        if pref and not rs:                                             # COORD 10-30 01:2x: PLACE on epyc2 first while it has headroom
            p = subprocess.run([sp["ot_run"], "--status"], capture_output=True, text=True, timeout=120)
            stt = parse_otrun_status(p.stdout if p.returncode == 0 else "")
            ok = [h for h in pref if (stt.get("localhost" if h == hub else h) or {}).get("admit", 0) >= m]
            if ok:
                phosts = ok
        prun = (runner.format(kit=K, work=W) if core else f"{W}/gen/run_kit.sh")
        rc, txt = run("place", otrun(m, t, K, f"bash {q(prun)} {q(K)} place {m} {t}", phosts, allow_hub=True))
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
        return after_place(K, *resume_verify(rs, rc, txt))

    def resume_verify(rs, rc, txt):
        """KW-RESUME-1: after a resumed PLACE every hardlinked source file must be unchanged (no write through a link)"""
        if not rs:
            return rc, txt
        vrc, vt = run("resume_verify", remote(kr_cmd(f"verify {q(K)}")), idempotent=True)
        if vrc:
            return (rc or 1), txt + "\nKW_RESUME_VERIFY FAIL: a reused (hardlinked) checkpoint file changed\n" + vt[-1500:]
        return rc, txt

    prun0 = (runner.format(kit=K, work=W) if core else f"{W}/gen/run_kit.sh")
    rs = resume_prepare(sp, K, prun0, run, remote, res)
    if rs == "nochange":
        (out / "result.json").write_text(json.dumps(res, indent=1))
        return 1
    try:
        return place_and_geom(K, rs)
    finally:
        if rs:
            run("resume_release", remote(kr_cmd(f"release {q(K)}")), idempotent=True)


# ------------------------------------------------------------------------------------------------ KIT-INPUT-STORE-1
# COORD 11-10 (+ amendment): kit-wave kits read plan / bind / kit_rtl recipe / asbuilt / sidecars from lane worktrees
# that cleanup deletes (KV kv3_pv x6, S81 leaf t42, HEAD hd_ctl, 100 S81 types on a stale bind8).  Option kit_store
# (die > global, default off; off = spec.json and every command byte-identical): the gen host hardlinks every input file
# the kit reads into W/kit_inputs from its per-fs dedupe store (tools/autopilot/kit_store.py), recipes (bind.f, *.sh)
# rewritten to the kit-local paths, json byte-identical; the kit is self-contained and the store is never a run-time
# path.  The wave src checkout itself is not copied (rebuildable from src_sha; recorded in the manifest).
KS_PATH = Path(__file__).resolve().parent / "kit_store.py"


def ks_cmd(args):
    """shell command running kit_store.py <args> on a gen host (source on stdin, like kr_cmd)"""
    return f"python3 - {args} <<'KWKS_EOF'\n{KS_PATH.read_text()}\nKWKS_EOF"


def kit_store_on(cfg, die, item):
    """option kit_store (die > global): true = every item; a list = the items matching one of its fnmatch patterns
    (pilot); absent / false = off"""
    v = opt(cfg, die, "kit_store")
    if isinstance(v, list):
        return any(fnmatch.fnmatch(item, str(x)) for x in v)
    return v is True


def kit_store_applies(sp):
    """hard cores (core_kit) and the event-shared prep bind (kit_rtl bind without bind_out) keep their own paths"""
    kr = sp.get("kit_rtl") or {}
    if sp.get("kind") == "core" and sp.get("core_kit"):
        return False
    return not (kr.get("mode") == "bind" and not kr.get("bind_out"))


def ks_inputs(sp, plan):
    """the input list of one kit: plan (+ its dir's own files and r8/), kit_rtl asbuilt (+ dir files) / bind_out /
    script, prep_cmd paths, gen_args and gen_env paths; recipes are scanned for further inputs on the gen host"""
    kr = sp.get("kit_rtl") or {}
    ins = [{"role": "plan", "path": plan, "kind": "file", "required": True, "siblings": ["r8"]}]
    if str(kr.get("asbuilt") or "").startswith("/"):
        ins.append({"role": "asbuilt", "path": kr["asbuilt"], "kind": "file", "required": True, "siblings": []})
    if str(kr.get("bind_out") or "").startswith("/"):
        ins.append({"role": "bind_out", "path": kr["bind_out"], "kind": "dir", "required": True})
    if str(kr.get("script") or "").startswith("/"):
        ins.append({"role": "kit_rtl_script", "path": kr["script"], "kind": "file", "required": True})
    if str(sp.get("type_overlay") or "").startswith("/"):
        ins.append({"role": "type_overlay", "path": sp["type_overlay"], "kind": "file", "required": True})
    for role, v in (("prep_cmd", kr.get("prep_cmd") or ""), ("gen_args", sp.get("gen_args") or []),
                    ("gen_env", sp.get("gen_env") or {})):
        for p in abs_paths(v):
            if p.startswith("/srv/"):
                ins.append({"role": role, "path": p, "required": False})
    return ins


def ks_map(v, mp):
    """config value with every input path (whole path or a path prefix ending at a separator) -> its kit-local path"""
    if not mp:
        return v
    if isinstance(v, str):
        keys = sorted(mp, key=len, reverse=True)
        return re.sub("(" + "|".join(re.escape(k) for k in keys) + r")(?=[/\s\"',;:=()$`<>|&]|$)",
                      lambda m: mp[m.group(1)], v)
    if isinstance(v, list):
        return [ks_map(x, mp) for x in v]
    if isinstance(v, dict):
        return {k: (x if str(k).startswith("note") else ks_map(x, mp)) for k, x in v.items()}
    return v


def kit_store_stage(sp, run, remote, res, W, plan):
    """-> ({orig: kit-local}, '') or (None, why).  Manifest W/kit_inputs/MANIFEST.json (+ store manifests/ for the
    14-day retention rule) records each file's sha and the rebuild recipe (src_sha, queue_src, plan, kit_rtl)."""
    import base64
    q = shlex.quote
    kr = {k: v for k, v in (sp.get("kit_rtl") or {}).items() if not str(k).startswith("note")}
    spec = {"inputs": ks_inputs(sp, plan),
            "rebuild": {"src": sp.get("src"), "src_sha": sp.get("src_sha"), "queue_src": sp.get("queue_src"),
                        "plan": plan, "kit_rtl": kr, "gen_args": sp.get("gen_args"), "event": sp.get("event")},
            "meta": {"die": sp.get("die"), "item": sp.get("item"), "attempt": os.path.basename(W), "work": W}}
    b64 = base64.b64encode(json.dumps(spec).encode()).decode()
    rc, txt = run("kit_store", remote(ks_cmd(f"snapshot --spec-b64 {q(b64)} --kit-inputs {q(W)}/kit_inputs")),
                  idempotent=True)
    got = [ln[len("KW_KIT_STORE "):] for ln in txt.splitlines() if ln.startswith("KW_KIT_STORE ")]
    if rc or not got:
        return None, "KIT-STORE snapshot failed (rc %s)\n%s" % (rc, txt[-3000:])
    doc = json.loads(got[-1])
    res["kit_store"] = {k: doc.get(k) for k in ("n_files", "bytes_copied", "blobs_new", "restored", "store")} \
        | {"absent": len(doc.get("absent") or [])}
    return doc["map"], ""


def kr_cmd(args):
    """shell command running kit_resume.py <args> on a host that has no repo checkout (source on stdin)"""
    return f"python3 - {args} <<'KWRS_EOF'\n{Path(KR.__file__).read_text()}\nKWRS_EOF"


def resume_prepare(sp, K, prun, run, remote, res):
    """KW-RESUME-1: fingerprint the new kit (always: res['stage_fp']); on a relaunch decide the resume step against the
    previous attempt's checkpoint and link it into K/run.  -> '' (full build), a step name (resumed from it) or
    'nochange' (res carries the FAIL).  Every error / doubt -> full build."""
    q = shlex.quote
    G, hub = sp["gen_host"], sp["hub"]
    rc, txt = run("resume_fp", remote(kr_cmd(f"manifest {q(K)} --runner {q(prun)} --no-checkpoint")), idempotent=True)
    new = _kr_json(txt, "KW_RESUME_MANIFEST")
    if new and not new.get("error"):
        res["stage_fp"] = new.get("fingerprints")
    rf = sp.get("resume_from")
    if not rf:
        return ""
    info = {"decision": "full", "source_attempt": rf.get("attempt"), "why": ""}
    res["resume"] = info
    if not new or new.get("error"):
        info["why"] = f"new kit manifest failed: {(new or {}).get('error') or txt[-300:]}"
        return ""
    best = None
    for h, path in rf.get("candidates") or []:
        cut = f" --cutoff {float(rf['gen_end'])}" if rf.get("gen_end") else ""
        cmd = kr_cmd(f"manifest {q(path)} --runner {q(os.path.join(os.path.dirname(path), 'run_kit.sh'))}{cut}")
        argv = _ssh(h, hub) + ["bash -c " + q(cmd)] if _ssh(h, hub) else ["bash", "-c", cmd]
        _, t = run(f"resume_old_{h}", argv, idempotent=True)
        m = _kr_json(t, "KW_RESUME_MANIFEST")
        if not m or m.get("error"):
            continue
        m["_host"] = h
        up = (m.get("checkpoint") or {}).get("upto")
        rank = KR.IDX[up] if up else -1
        if best is None or rank > best[0]:
            best = (rank, m)
    if best is None:
        info["why"] = "no readable checkpoint of the previous attempt (pruned / host unreachable)"
        return ""
    old = best[1]
    dec = KR.decide(new, old, allow_nochange=bool(rf.get("allow_nochange")))
    info.update(decision=dec["decision"], why=dec["why"], changed=dec["changed"][:40], n_changed=len(dec["changed"]),
                source_host=old["_host"], source_kit=old["kit"], start=dec.get("start"), reuse=dec.get("reuse"),
                fingerprints=dec.get("fingerprints"))
    if dec["decision"] == "nochange":
        res.update(stage="resume_nochange", verdict="FAIL", **{"class": rf.get("class") or "FLOW"},
                   reason=f"relaunch refused: {dec['why']} (attempt {rf.get('attempt')}; class {rf.get('class')})",
                   tail=dec["why"], errors=dec["why"], evidence=f"{old['_host']}:{old['kit']}")
        return "nochange"
    if dec["decision"] != "resume":
        return ""
    srch, srck = old["_host"], old["kit"]
    meta = {"host": srch, "kit": srck, "attempt": rf.get("attempt"), "attempt_dir": rf.get("attempt_dir"),
            "checkpoint": old.get("checkpoint"), "same_host": srch == G, "relay": None}
    src = srck
    if srch != G:
        # fleet hosts do not reach each other: relay ONLY the reused files (no 30 GB copy) source -> hub -> gen host
        files = [rel for rel, _ in KR.link_plan(old["checkpoint"], dec["start"], old.get("run_files") or {})]
        if not files:
            info.update(decision="full", why="relay: no files to reuse")
            return ""
        stage_dir = f"{sp['work']}/resume_src"
        SSHE = "-e 'ssh -o BatchMode=yes -o ControlPath=none'"
        hub_dir = stage_dir if G in ("localhost", hub) else f"{sp['work']}/resume_relay"
        lst = "\n".join(files)
        get = (f"mkdir -p {q(hub_dir)} && printf '%s\\n' {q(lst)} | rsync -a --files-from=- {SSHE} "
               f"{srch}:{q(srck)}/ {q(hub_dir)}/" if srch not in ("localhost", hub) else
               f"mkdir -p {q(hub_dir)} && printf '%s\\n' {q(lst)} | rsync -a --files-from=- {q(srck)}/ {q(hub_dir)}/")
        rc, t = run("resume_relay", ["bash", "-c", get], idempotent=True)
        if rc == 0 and hub_dir != stage_dir:
            rc, t = run("resume_push", ["bash", "-c", f"rsync -a {SSHE} {q(hub_dir)}/ {G}:{q(stage_dir)}/ && rm -rf {q(hub_dir)}"],
                        idempotent=True)
        if rc:
            info.update(decision="full", why=f"relay of the reused files failed rc {rc}: {t[-200:]}")
            return ""
        src, meta["relay"] = stage_dir, f"{srch}:{srck} -> {G}:{stage_dir} ({len(files)} files)"
    doc = json.dumps({"decision": dec, "source": meta})
    cmd = (f"python3 -c \"import sys;open(sys.argv[1],'w').write(sys.stdin.read())\" {q(sp['work'])}/resume_decision.json "
           f"<<'KWRD_EOF'\n{doc}\nKWRD_EOF\n" + kr_cmd(f"apply {q(K)} --src {q(src)} --decision {q(sp['work'])}/resume_decision.json"))
    if src != srck:
        cmd += f"\nrc=$?; rm -rf {q(src)}; exit $rc"
    rc, t = run("resume_apply", remote(cmd), idempotent=False)
    ap = _kr_json(t, "KW_RESUME_APPLIED")
    if rc or not ap:
        info.update(decision="full", why=f"apply failed: {(_kr_json(t, 'KW_RESUME_APPLY_FAIL') or {}).get('error') or t[-300:]}")
        return ""
    info.update(applied={k: ap.get(k) for k in ("n_link", "n_copy", "bytes_link", "bytes_copy", "keep_created")})
    print(f"KW_RESUME {sp['item']} start {dec['start']} reuse {','.join(dec['reuse'])} from {srch}:{srck} "
          f"({dec['why']})", flush=True)
    return dec["start"]


def _kr_json(txt, tag):
    got = [ln[len(tag) + 1:] for ln in (txt or "").splitlines() if ln.startswith(tag + " ")]
    try:
        return json.loads(got[-1]) if got else None
    except ValueError:
        return None



# ------------------------------------------------------------------------------------------------ tick stage
def _descends(AP):
    def f(sha, base):
        rc, _, _ = AP.sh(["git", "-C", str(AP.REPO), "merge-base", "--is-ancestor", base, sha], timeout=60)
        return rc == 0
    return f


PROBE_V = 5   # DIE-KV-62/types 11-02: bump when the probe output changes (a cached older probe is re-run); 3 = KW-FIX-4 lint
#              4 = KW-PROV-1 prov_deps (every planned + noview child of a type) + bound (signed lef/lib per module)
#              5 = DIE-HBM-89-TGEN unbound (plan buses with no leaf binding: the plan-wrapper gen cannot bind them)
PROBE_PLAN = Path(BI.__file__).read_text().rsplit("\nif __name__", 1)[0] + f"\nPROBE_V = {PROBE_V}\n" + r'''
import hashlib, json, os, re, sys
a = json.loads(sys.argv[1]); out = {}
H = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
try:
    st = os.stat(a["plan"]); raw = open(a["plan"], "rb").read(); p = json.loads(raw)
    pt = p.get("partition_types") or {}; bud = p.get("budgets") if isinstance(p.get("budgets"), dict) else {}
    mode = a.get("block_identity", "raw")
    # die option block_ignore (KW-FIX-6 11-04): plan-model metadata that moves no geometry, pin or net stays out of the
    # block hash, so pinning a frozen plan to the models it was solved with does not supersede its live and signed kits
    for dotted in a.get("block_ignore") or []:
        sec, key = dotted.split(".", 1)
        for v in pt.values():
            if isinstance(v, dict) and isinstance(v.get(sec), dict):
                v[sec].pop(key, None)
                if not v[sec]:
                    del v[sec]
    ids = identities(p, a["plan"], mode)
    blocks = {name: value["block_sha"] for name, value in ids.items()}
    baseline = None
    if mode != "raw" and a.get("identity_baseline_plan"):
        baseline_path = a["identity_baseline_plan"]
        baseline = identities(json.loads(Path(baseline_path).read_text()), baseline_path, mode)
    flags, deps, lint, pdeps, bound, pkeys, unbound = {}, {}, {}, {}, {}, {}, {}
    cmax = int(a.get("cells_max") or 150000)
    for t, v in pt.items():
        if not isinstance(v, dict):
            continue
        # KW-FIX-4 11-03 (OWNER gen-time lint): plan-static checks, no build.  cells: plan type.cells, else the sum of
        # contents[].cells when every content carries one; a type with hard_cores[] is skipped (its estimate may
        # include the cores, which the type kit does not build flat)
        li = []
        nc = v.get("cells")
        if not isinstance(nc, (int, float)) or isinstance(nc, bool):
            cc = [c.get("cells") for c in (v.get("contents") or []) if isinstance(c, dict)]
            nc = sum(cc) if cc and all(isinstance(x, (int, float)) for x in cc) else None
        if nc is not None and nc > cmax and not v.get("hard_cores") and not v.get("hard"):
            li.append(f"cells: est {int(nc)} flat std cells > {cmax} (plan estimate): re-form into hard cores / a smaller slot")
        decl = [r.get("name") for r in (v.get("id_straps") or []) + (v.get("count_straps") or []) if isinstance(r, dict)]
        dup = sorted({n for n in decl if decl.count(n) > 1})
        if dup:
            li.append("strap: duplicate declared strap names " + ",".join(map(str, dup[:4])))
        leak = sorted({str(b.get("name")) for b in (v.get("buses") or []) if isinstance(b, dict)
                       and re.match(r"strap_", str(b.get("name") or "")) and b.get("name") not in decl})
        if leak:
            li.append("strap: leaked strap ports on the type boundary, not declared id_straps/count_straps: " + ",".join(leak[:4]))
        if li:
            lint[t] = li
        ck = v.get("clock") or {}
        taps = [tp for tp in ck.get("taps") or [] if isinstance(tp, dict) and tp.get("kind") == "core"]
        signed = bool(taps and v.get("hard_cores") and all("insertion_ff_ps" in tp and
                      str(tp.get("budget_owner", "")).startswith("SIGNED") for tp in taps))
        # gen_phys.type_macros + write_type_kit: a hard core / content with a lef but no lib fails gen at once
        noview = sorted({str(c.get("module") or c.get("inst")) for c in (v.get("hard_cores") or []) + (v.get("contents") or [])
                         if isinstance(c, dict) and c.get("lef") and not c.get("lib")})
        # DIE-KV-62/types 11-02: hard_cores[] without a lef = PLANNED core (view not bound in the plan yet)
        planned = sorted({str(c.get("module") or c.get("inst")) for c in (v.get("hard_cores") or [])
                          if isinstance(c, dict) and not c.get("lef")})
        # KW-PROV-1: every child that waits for a view (both kinds) + the lef/lib the plan binds per module (the signed
        # view a provisional kit is re-signed on)
        if noview or planned:
            pdeps[t] = sorted(set(noview) | set(planned))
        if v.get("hard_cores") or v.get("contents"):
            # prov_key: the type entry without its children's lef/lib -- equal before and after a child view is bound,
            # so a provisional kit is re-signed (STA only) rather than rebuilt when only the child view changed
            w = json.loads(json.dumps(v, default=str))
            for c in (w.get("hard_cores") or []) + (w.get("contents") or []):
                if isinstance(c, dict):
                    c.pop("lef", None); c.pop("lib", None)
            pkeys[t] = H(w)[:16]
        for c in (v.get("hard_cores") or []) + (v.get("contents") or []):
            if isinstance(c, dict) and c.get("lef") and c.get("lib"):
                bound.setdefault(str(c.get("module") or c.get("inst")), {"lef": c["lef"], "lib": c["lib"]})
        # DIE-HBM-89-TGEN 11-07: the plan-wrapper gen (gen_rtl.write_rtl, no --kit-rtl) binds a bus only through
        # buses[].leaf or a contents[].bind "bus:<name>"; any other bus is 'not bound to any leaf port' at gen.  A die
        # whose plan carries no leaf bindings (HBM d44v: 0 of 81 types) needs kit_rtl (the bound partition RTL)
        if not v.get("hard"):
            bb = {k for c in (v.get("contents") or []) if isinstance(c, dict)
                  for k in (c.get("bind") or {}).values() if isinstance(k, str)}
            ub = [str(b.get("name")) for b in (v.get("buses") or []) if isinstance(b, dict)
                  and not b.get("leaf") and f"bus:{b.get('name')}" not in bb]
            if ub:
                unbound[t] = ub
        if v.get("hard"):
            flags[t] = "hard"
        elif noview:
            flags[t] = "noview"
            deps[t] = noview
        elif planned:
            flags[t] = "planned"
            deps[t] = planned
        elif ck.get("core_taps") == "internal" and not signed and any(
                str(tp.get("budget_owner", "")).startswith("parent_budget") for tp in taps):
            # DIE-KV-60/taps 11-01: = gen_phys.internal_core_taps_estimate (unsigned internal taps -> estimate form)
            flags[t] = "contract"
    out = {"mtime": st.st_mtime, "plan_sha": hashlib.sha256(raw).hexdigest(), "types": sorted(pt), "flags": flags,
           "cores": sorted(set(blocks) - set(pt)), "blocks": blocks, "deps": deps, "lint": lint, "probe_v": PROBE_V,
           "prov_deps": pdeps, "prov_keys": pkeys, "bound": bound, "plan_dir": os.path.dirname(os.path.abspath(a["plan"])),
           "unbound": unbound}
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
    if mode == "raw" and c and c.get("blocks") and c.get("probe_v") == PROBE_V and time.time() - c.get("t", 0) < 6 * 3600:
        return c
    args = {"plan": d["plan"], "core_views": bool(d.get("core_kit")), "cells_max": d.get("prelint_cells_max"),
            "block_ignore": d.get("block_ignore")}
    if mode != "raw":
        args.update(block_identity=mode, identity_baseline_plan=d.get("identity_baseline_plan"))
    p = AP.rpy(d["gen_host"], PROBE_PLAN, args, timeout=600)
    if p.get("error"):
        return {"error": p["error"]}
    p["t"] = time.time()
    if mode == "raw":
        st.setdefault("plans", {})[key] = p
    return p


def ensure_plan_view(AP, st, d):
    """The INFRA relaunch loop runs before plan_dies, on a fresh config: a launch there saw no _plan_flags, so a type
    with planned child cores got no provisional views and its kit tried the child bodies (11-04, 16 QC cb rows + the
    su_c pilot).  Read the plan first, cached like plan_dies.  False when the plan cannot be read."""
    if d is None:
        return False
    if "_plan_flags" in d:
        return True
    pn = plan_names(AP, st, d)
    if pn.get("error"):
        return False
    d["_plan_sha"] = pn.get("plan_sha")
    d["_plan_flags"] = pn.get("flags") or {}
    d["_plan_unbound"] = pn.get("unbound") or {}
    d["_plan_deps"] = pn.get("deps") or {}
    d["_prov_deps"] = pn.get("prov_deps") or {}
    d["_prov_keys"] = pn.get("prov_keys") or {}
    d["_prov_bound"] = pn.get("bound") or {}
    d["_plan_dir"] = pn.get("plan_dir") or ""
    return True


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
        if ok and AP and probe:
            if "_spill_marked" not in cfg:              # the dry plan does not pass the tick's probe
                try:
                    cfg["_spill_marked"] = spill_marked(AP, cfg)
                except Exception as e:                  # a diagnostic probe never stops the plan
                    log(f"KIT-WAVE spill-mark probe skipped: {e}")
            if "_src_incomplete" not in cfg:
                try:
                    cfg["_src_incomplete"] = src_incomplete(AP, cfg)
                except Exception as e:                  # a diagnostic probe never stops the plan
                    log(f"KIT-WAVE src probe skipped: {e}")
            bad = work_root_problem(cfg, die)
            if bad:
                ok, why = False, bad
                AP.log(f"KIT-WAVE WORK-ROOT {die}: {bad}")
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
                    d["_plan_unbound"] = pn.get("unbound") or {}
                    d["_plan_deps"] = pn.get("deps") or {}
                    d["_plan_lint"] = pn.get("lint") or {}
                    d["_prov_deps"] = pn.get("prov_deps") or {}
                    d["_prov_keys"] = pn.get("prov_keys") or {}
                    d["_prov_bound"] = pn.get("bound") or {}
                    d["_plan_dir"] = pn.get("plan_dir") or ""
                    names = core_view_names(names, pn.get("core_views"))
                    d["_identity_holds"] = {}
                    if d.get("block_identity", "raw") != "raw":
                        names, d["_identity_holds"] = BI.reuse_blocks(
                            names, pn["identities"], pn.get("baseline_identities"),
                            st.get("items") or {}, die=die, event=d["event"],
                            receipts=d.get("identity_reuse_receipts"))
                    # KW-FIX-4 11-03 OWNER gen-time lint: LINT rows before any launch (plan_entry_block refuses them)
                    d["_lint_blocks"] = names if isinstance(names, dict) else {}
                    d["_lint"] = prelint(d, die, names, st)
                    record_lint(st, cfg, die, d["_lint"])
            if ok:
                picks, skip = select(owners, cfg, die, st, names)
                if skip.get(NO_ROW_SOURCE):                  # WAVE-OPS-1 11-10: never silent (18 HBM cores had no row)
                    its = skip[NO_ROW_SOURCE]
                    (AP.log if AP else log)(f"KIT-WAVE NO-ROW-SOURCE {die}: {len(its)} only_items item(s) have no row "
                                            f"source (no OWNERS row, not in plan_core_items / allowlisted plan types) "
                                            f"and can never launch: " + " ".join(its[:40]) + (" ..." if len(its) > 40 else ""))
                if picks:                                    # WAVE-OPS-1 11-10 (a): advisory, never blocks
                    fl = wave_src_flag(cfg, die)
                    if fl:
                        (AP.log if AP else log)(fl)
                n = capacity(cfg, die, st, status, hub)      # per-die share; the global caps apply below
                if d.get("max_items_total"):           # canary: lifetime cap of wave items on this event
                    rel = set(d.get("retry") or [])
                    used = sum(1 for r in st["items"].values() if r.get("die") == die and r.get("event") == d["event"]
                               and f"{r.get('item')}@{r.get('attempt')}" not in rel)
                    n = max(0, min(n, int(d["max_items_total"]) - used))
                go = [r for r in picks if not load_hold(cfg, die, r["item"], r.get("parent_item"), core_module(r["item"]))]
                if len(go) < len(picks):
                    skip.setdefault(load_hold(cfg, die), []).extend(r["item"] for r in picks if r not in go)
                per_die.append([(die, r) for r in go[:n]])
        out.append((die, ok, why, picks, skip))
    # AUTOBUILD-PIPE-2 10-30: round-robin the tick's launches across dies.  Alphabetical fill let S81 (72 queued) take
    # every per-tick slot so HEAD l46 never launched (KIT-WAVE-2 23:17).
    if per_die:                                          # KW-FIX-43: no die is always first or last (rotate_dies)
        k = int(st.get("pass_n") or 0) % len(per_die)
        per_die = per_die[k:] + per_die[:k]
    room = max(0, min(int(cfg.get("max_inflight", DEFAULTS["max_inflight"])) - inflight(st),
                      int(cfg.get("max_launch_per_tick", DEFAULTS["max_launch_per_tick"]))))
    # queued volume (pilot_mode queue) goes after every die's pilots and other picks, so it queues behind them
    lists = ([[x for x in q if not x[1].get("volume")] for q in per_die]
             + [[x for x in q if x[1].get("volume")] for q in per_die])
    for part in (lists[:len(per_die)], lists[len(per_die):]):
        i = 0
        while len(launch) < room and any(i < len(q) for q in part):
            launch += [q[i] for q in part if i < len(q)][:room - len(launch)]
            i += 1
    return out, launch


def _refused_class(attempt_dir):
    """class a relaunch refusal carried over from the attempt it compared with (state rows hold FLOW for those)"""
    try:
        r = json.loads((Path(attempt_dir) / "result.json").read_text())
    except (OSError, ValueError):
        return ""
    return r.get("class") if isinstance(r, dict) and r.get("stage") == "resume_nochange" else ""


def resume_source(AP, prev):
    """KW-RESUME-1: where the previous attempt's checkpoint lives.  Candidates: the attempt's kit on its gen host and,
    for a kit the autopilot routed on another host (ot-run spill), that host's copy of the same path, which holds the
    CTS / GRT outputs.  gen_end = the attempt's gen.log mtime: kit files not newer are the attempt's gen-time inputs
    (kits from before .kw_inputs.json)."""
    jd = Path(prev["dir"])
    out = {"attempt": prev.get("attempt"), "attempt_dir": str(jd), "candidates": [],
           "class": prev.get("q_class") or prev.get("class") or "",
           "allow_nochange": prev.get("class") == "INFRA" or prev.get("status") == "RETRY-INFRA"
                             # stopped, not failed: a queued volume released or a cancelled attempt has no failure a
                             # same-input run would repeat (KW6-CLASS 11-04, S81 slice_station__t23/t44)
                             or prev.get("status") == "CANCELLED" or prev.get("class") == "VOLUME"
                             or _refused_class(jd) == "VOLUME"}
    try:
        out["gen_end"] = (jd / "gen.log").stat().st_mtime
    except OSError:
        out["gen_end"] = None
    try:
        osp = json.loads((jd / "spec.json").read_text())
    except (OSError, ValueError):
        osp = {}
    kit = prev.get("kit") or ""
    if not kit:
        try:
            kit = json.loads((jd / "result.json").read_text()).get("kit") or ""
        except (OSError, ValueError):
            kit = ""
    if not kit and osp.get("work") and osp.get("gen_host") and (prev.get("kind") or "type") != "core":
        kit = f"{osp['gen_host']}:{osp['work']}/gen/{prev['item']}"
    if ":" in kit:
        h, path = kit.split(":", 1)
        out["candidates"].append([h, path])
        try:
            j = (json.loads((Path(AP.AP_DIR) / "state.json").read_text()).get("jobs") or {}).get(prev.get("q_id") or "") or {}
            ro = j.get("ran_on")
            if ro and ro != h and j.get("path") == path:
                out["candidates"].append([ro, path])
        except (OSError, ValueError, AttributeError):
            pass
    return out


def bind_restage(cfg, die, prev, sp):
    """the attempt after a RESTAGE runs on the host the move chose, while that host still holds the die's gen inputs"""
    moved = prev.pop("restage_host", None)
    if moved and moved in gen_hosts(cfg, die, sp.get("item")):
        sp["gen_host"] = moved


def launch_safe(AP, cfg, st, die, r, hub, delay_s=0.0):
    """KW-FIX-7 11-04: one row's launch error never ends the pass.  06:28 a merge changed kit_resume.py under a reload pass:
    launch raised, the pass died before save_state, and 5 units already launched were in no state record (a next pass would
    relaunch the same attempt dirs).  The row stays as it was and is taken again on a later pass."""
    try:
        return launch(AP, cfg, st, die, r, hub, delay_s=delay_s)
    except Exception as e:
        AP.log(f"KIT-WAVE LAUNCH-SKIP {die}/{r.get('item')}: {type(e).__name__}: {e} (pass continues; retried next pass)")
        return None


def launch(AP, cfg, st, die, r, hub, delay_s=0.0):
    if not scheduler_current(AP):
        return None
    arm = r.get("arm") if isinstance(r.get("arm"), dict) else None      # KW-FIX-44 GRTARM_1111
    key = arm["key"] if arm else item_key(die, cfg["dies"][die]["event"], r["item"], r.get("block_sha"))
    prev = st["items"].get(key) or {}
    # A stale/repeated launch list must never replace a live producer claim.
    if prev.get("status") in ("RUNNING", "LAUNCHING", "ROUTE-HELD"):
        AP.log(f"KIT-WAVE LAUNCH-KEEP {die}/{r['item']}: active producer {prev.get('unit', '')}")
        return None
    # The attempt dir is per item and event, not per plan block: number across every block's records, or a new block's
    # attempt N lands in an older block's attempt_N, whose results make "make place" a no-op (t14@4, t17@5, COORD 11-04).
    event = cfg["dies"][die]["event"]
    attempt = max([int(prev.get("attempt", 0))] + [int(v.get("attempt", 0)) for v in st["items"].values()
                                                  if v.get("die") == die and v.get("event") == event
                                                  and v.get("item") == r["item"]]) + 1
    jd = Path(AP.AP_DIR) / "kit_wave" / re.sub(r"[^A-Za-z0-9_.-]", "_", key) / f"a{attempt}"
    sp = spec_for(cfg, die, r["item"], hub, r.get("parent_item") or prev.get("parent_item"), kind=r.get("kind") or "type")
    sp["start_delay_s"] = round(float(delay_s), 1)
    if arm:                                        # KW-FIX-44 GRTARM_1111: the halving-off arm of this row
        if arm.get("gen_host"):
            sp["gen_host"] = arm["gen_host"]
            sp["place_prefer"] = [arm["gen_host"]] + [h for h in sp.get("place_prefer") or [] if h != arm["gen_host"]]
            sp["hosts"] = [arm["gen_host"]] + [h for h in sp.get("hosts") or [] if h != arm["gen_host"]]
        why = grt_arm_pin(st, arm, sp)             # KW-FIX-46: the arm builds from its sibling's src, plan and bind
        if why:
            AP.log(f"KIT-WAVE GRT-ARM LAUNCH-SKIP {die}/{r['item']}: {why}")
            return None
        sp["gen_env"] = dict(sp.get("gen_env") or {}, OT_GRT_TRANSITION_MODE=arm["mode"])
        sp["grt_arm"] = dict(sp.get("grt_arm") or {}, of=arm["of"], mode=arm["mode"])
        why = grt_arm_src_check(AP, cfg, sp)
        if why:
            AP.log(f"KIT-WAVE GRT-ARM LAUNCH-SKIP {die}/{r['item']}: {why}")
            return None
    bind_restage(cfg, die, prev, sp)
    alt = ((cfg.get("_workroot_alt") or {}).get(sp["gen_host"]) or {}).get(die)
    if alt:                                        # KW-FIX-38: this host starts the attempt on its scratch2
        sp["work_alt_lane"] = alt
    elif die in (cfg.get("_alt_spent") or {}).get(sp["gen_host"], ()):
        # the plan for this tick was made before the charges: the disk this host had room on is used up, the attempt would
        # wait at kit_rtl behind the root floor; it stays pending for a later tick instead (no attempt number consumed)
        AP.log(f"KIT-WAVE LAUNCH-DEFER {die}/{r['item']}: scratch2 room on {sp['gen_host']} used up this tick")
        return None
    d = cfg["dies"][die]
    if (r.get("kind") or "type") == "type" and prov_item(d, r["item"]):
        # KW-PROV-1 (COORD 17:50 (C)): a type whose child views are unsigned launches on PROVISIONAL child views
        sp["prov_views"] = prov_spec(AP, d, die, r["item"], hub)
        miss = prov_missing_cands(sp["prov_views"]) if opt(cfg, die, "prov_require_cands") is True else []
        if miss:           # KW-FIX-45 11-11 (COORD, hbm q_su01 PLAN): wait for the child cores, no attempt consumed
            AP.log(f"KIT-WAVE WAIT-CHILD {die}/{r['item']}: no routed PROVISIONAL source yet for child core(s) {' '.join(miss)} (prov_require_cands)")
            return None
    if attempt > 1:
        # Preserve previous generation/geometry verdicts and run payloads.
        sp["work"] += f"/attempt_{attempt}"
        if opt(cfg, die, "stage_resume") is not False and prev.get("dir"):
            sp["resume_from"] = resume_source(AP, prev)
        # FLOW-23 class D: a relaunch after an AUTO-GEOM FAIL plans soft region guides from that result (written only
        # when its r2r rule failed); die opt-out: region_guide false
        if opt(cfg, die, "region_guide") is not False:
            rgg = region_guide_geom(prev, sp["gen_host"])
            if rgg:
                sp["region_guide_geom"] = rgg
    # KW-FIX-17: an attempt released by the LEAFSLEW signature (or following a hooked one) builds with clk_leaf_repeat
    ls_key, ls_form = leafslew_launch(cfg, {} if arm else st, die, r["item"],
                                      (prev or st["items"].get(arm["of"]) or {}) if arm else prev, attempt) \
        if attempt > 1 or leafslew_item_env(cfg, die, r["item"]) is not None else (None, None)
    if ls_form:
        sp["leafslew_form"] = ls_form
    unit = f"kw-{re.sub(r'[^A-Za-z0-9]', '', die)[:6]}-{re.sub(r'[^A-Za-z0-9]', '', r['item'])[:28]}-{attempt}-{int(time.time()) % 100000}"
    if AP.DRY:
        AP.log(f"KIT-WAVE would launch {die}/{r['item']} unit {unit}: gen {sp['gen_host']}:{sp['work']} plan {sp['plan']}")
        return None
    jd.mkdir(parents=True, exist_ok=True)
    # Snapshot current approved tool bytes into this new attempt, never another lane's kit.
    if opt(cfg, die, "future_lec") is not False:
        sp["future_lec"] = future_lec_for(cfg, die, jd / "future_lec")
    (jd / "spec.json").write_text(json.dumps(sp, indent=1))
    ok = AP.launch_unit(unit, jd / "unit.log", ["python3", str(Path(__file__).resolve()), "run-item", str(jd / "spec.json")])
    rec = {"die": die, "item": r["item"], "parent_item": r.get("parent_item") or prev.get("parent_item"), "kind": r["kind"], "event": sp["event"], "attempt": attempt,
           "block_sha": r.get("block_sha"), "plan_sha": cfg["dies"][die].get("_plan_sha"),
           "unit": unit, "dir": str(jd), "volume": r.get("volume") or "",
           "status": "RUNNING" if ok else "FAIL", "class": "" if ok else "INFRA", "replicas": r.get("replicas"),
           "reason": "" if ok else "systemd-run failed", "started": time.time(), "updated": time.time(),
           # INFRA budget counts INFRA attempts since the last design verdict (KIT-TRIAGE-1 11-01): an item that had
           # design FAILs before must still get its infra_attempts after a class fix relaunch
           "infra_base": (int(prev.get("infra_base") or 0) if prev.get("class") == "INFRA"
                          else int(prev.get("attempt") or 0))}
    if arm:
        rec["arm"] = {k: arm.get(k) for k in ("of", "key", "mode", "gen_host")}
    if sp.get("prov_views"):
        rec["provisional"] = {m: "pending" for m in sp["prov_views"]["modules"]}
        rec["prov_key"] = (d.get("_prov_keys") or {}).get(r["item"])
    if ls_form and ok:
        rec["leafslew_form"] = ls_form
        if ls_key:
            st["leafslew"][ls_key]["hooked_attempt"] = attempt
    if prev.get("restage_n") and prev.get("class") == "INFRA":      # a design verdict in between starts the count again
        rec["restage_n"] = prev["restage_n"]
    st["items"][key] = rec
    AP.log(f"KIT-WAVE LAUNCH {die}/{r['item']} ({r['kind']}, {r.get('replicas')} replicas) event {sp['event']} unit {unit}")
    return rec


# ------------------------------------------------------------------------------------------------ GRT halving-off arm
# KW-FIX-44 GRTARM_1111 (COORD 01:0x 11-11; OWNER 11-11: "yes, I agree to rolling out the halving. If detailed routing
# failed, stop it."): die option grt_halving_arm {items: [...], mode: off|edge|edge_outline, gen_host: <host>,
# stop: <reason>} launches ONE extra attempt per listed current-plan row, alongside its normal path.  The arm has its own
# state key (<row key>|grtarm-<mode>), its own attempt number and dir, and the gen env OT_GRT_TRANSITION_MODE=<mode>:
# gen_phys writes K/grt_transition_mode and run_kit.sh runs the ORFS main run ONLY on the pinned patched router image
# (asap7lock-grtoff); LEC and sign-off STA stay stock, receipt K/grt_transition.json.  An arm launches only from a die src
# whose gen_phys.py has that writer (checked on the gen host).  Same item identity: the first of the two to sign off
# (SIGNED / WAIT-PARENT) counts, the other is stopped by its exact units, marked CANCELLED SUPERSEDED and its run data
# reclaimed (logs, reports, json kept).  STOP RULE: an arm that ends FAIL after the wave (DRT DRC>0, DRT not converged, any
# route/sign-off verdict) is final and never relaunched; only an INFRA failure before any verdict uses the infra budget.
# Class stop: top-level grt_halving_arm_stop, die option stop, or AP_DIR/grt_halving_arm.stop launches no new arm and
# stops every live arm (CANCELLED ARM-STOP).  No option anywhere = no arm and the tick is unchanged.
GRT_ARM_MODES = ("off", "edge", "edge_outline")
GRT_ARM_STOP_FILE = "grt_halving_arm.stop"
GRT_ARM_GEN_MARK = "def write_grt_transition_mode"
GRT_ARM_SIGNED = ("SIGNED", "WAIT-PARENT")
GRT_ARM_RECLAIM = ("*.odb", "*.def", "*.gds", "*.gds.gz", "*.spef", "*.oas")
GRT_ARM_MAX_PER_TICK = 6


def grt_arm_key(base_key, mode):
    return f"{base_key}|grtarm-{mode}"


def grt_arm_opt(cfg, die):
    """the die's validated grt_halving_arm option, or None"""
    o = ((cfg.get("dies") or {}).get(die) or {}).get("grt_halving_arm")
    if not o:
        return None
    if not isinstance(o, dict) or str(o.get("mode", "off")) not in GRT_ARM_MODES or not isinstance(o.get("items") or [], list):
        raise ValueError(f"grt_halving_arm {die}: {{items: [...], mode: {'|'.join(GRT_ARM_MODES)}}}")
    gh = o.get("gen_host")
    if gh is not None and not re.fullmatch(r"[A-Za-z0-9_.-]+", str(gh)):
        raise ValueError(f"grt_halving_arm {die}: gen_host {gh!r}")
    return dict(o, mode=str(o.get("mode", "off")), items=[str(x) for x in (o.get("items") or [])])


def grt_arm_stop(cfg, die, ap_dir):
    """class stop reason, '' = none (an unreadable stop file stops: fail-closed)"""
    if cfg.get("grt_halving_arm_stop"):
        return str(cfg["grt_halving_arm_stop"])[:200]
    o = ((cfg.get("dies") or {}).get(die) or {}).get("grt_halving_arm")
    if isinstance(o, dict) and o.get("stop"):
        return str(o["stop"])[:200]
    p = Path(ap_dir or ".") / GRT_ARM_STOP_FILE
    try:
        return (p.read_text().strip()[:200] or GRT_ARM_STOP_FILE) if p.exists() else ""
    except OSError:
        return GRT_ARM_STOP_FILE + " unreadable"


def grt_arm_signed(rec):
    return rec.get("status") == "ENQUEUED" and rec.get("q_status") in GRT_ARM_SIGNED


def grt_arm_live(rec):
    """an attempt that is still on its way to a verdict (the one the arbitration stops)"""
    s = rec.get("status")
    if s in ("RUNNING", "LAUNCHING", "PASS", "ROUTE-HELD", "RETRY-INFRA"):
        return True
    q = str(rec.get("q_status") or "")
    return s == "ENQUEUED" and q not in GRT_ARM_SIGNED and (q in ("", "QUEUED", "RUNNING") or q.startswith("WAIT-"))


# KW-FIX-46 KIT_TOPOLOGY_BIND_STALE (QC sle_hc1__cl22c1ff36 arm @31, 11-11 02:52): spec_for() builds the arm from the die's
# CURRENT config (plan, src, bind, asbuilt, clock-landing sidecar), which KW-FIX-43's rebinds had moved on from the sibling's
# attempt; the A/B arm then ran a bind that does not belong to its src (kit_topology: "regenerate the canonical native bind").
# The arm differs from its sibling only by the gen env OT_GRT_TRANSITION_MODE, so everything the kit reads is the sibling's.
GRT_ARM_PIN = ("plan", "src", "src_sha", "src_base", "src_overlay", "queue_src", "kit_rtl", "canonical_topology_prepare",
               "core_kit", "gen_args", "preflight_args", "cland_pinslot", "relay_bay_re", "prov_first_re", "cell_check")
GRT_ARM_PIN_REQUIRED = ("src", "plan")


def grt_arm_sibling_spec(st, arm):
    """the spec.json of the newest attempt of the arm's sibling (the normal path of the row), or (None, why)"""
    base = (st.get("items") or {}).get(arm.get("of"))
    if not base or not base.get("dir"):
        return None, f"sibling {arm.get('of')} has no attempt dir"
    try:
        return json.loads((Path(base["dir"]) / "spec.json").read_text()), ""
    except (OSError, ValueError) as e:
        return None, f"sibling spec {base.get('dir')}/spec.json unreadable ({type(e).__name__})"


def grt_arm_pin(st, arm, sp):
    """overwrite sp's source inputs (GRT_ARM_PIN) with the sibling attempt's, in place; the sibling's gen env is kept and the
    arm's mode is added by the caller.  Returns '' or the reason the arm must not launch (fail closed: no sibling spec, or a
    sibling spec without src/plan, launches nothing rather than an arm on a different src or bind)."""
    sib, why = grt_arm_sibling_spec(st, arm)
    if sib is None:
        return why
    miss = [k for k in GRT_ARM_PIN_REQUIRED if not sib.get(k)]
    if miss:
        return f"sibling spec lacks {','.join(miss)}: cannot pin the arm to the sibling's inputs"
    for k in GRT_ARM_PIN:
        if k in sib:
            sp[k] = sib[k]
        else:
            sp.pop(k, None)
    sp["gen_env"] = dict(sib.get("gen_env") or {})
    kr = sib.get("kit_rtl") if isinstance(sib.get("kit_rtl"), dict) else {}
    sp["grt_arm"] = {"pinned_from": {"attempt": (st["items"].get(arm.get("of")) or {}).get("attempt"), "src": sib.get("src"),
                                     "plan": sib.get("plan"), "bind_out": kr.get("bind_out"), "asbuilt": kr.get("asbuilt")}}
    return ""


def grt_arm_src_check(AP, cfg, sp):
    """'' when the arm's gen host has a die src whose gen_phys.py writes K/grt_transition_mode, else why not (cached per tick)"""
    h, src = sp.get("gen_host") or "", str(sp.get("src") or "")
    cache = cfg.setdefault("_grt_arm_src", {})
    if (h, src) not in cache:
        f = shlex.quote(src.rstrip("/") + "/tools/die_plan/gen_phys.py")
        cmd = f"grep -q {shlex.quote(GRT_ARM_GEN_MARK)} {f} && echo KW_GRTARM_SRC_OK || echo KW_GRTARM_SRC_NO"
        remote = _ssh(h, getattr(AP, "HUB_NAME", "localhost"))
        try:
            rc, out, _ = AP.sh(remote + ["bash -c " + shlex.quote(cmd)] if remote else ["bash", "-c", cmd], timeout=60)
        except Exception as e:                       # noqa: a probe error launches nothing
            rc, out = 1, f"probe error {type(e).__name__}"
        cache[(h, src)] = "" if "KW_GRTARM_SRC_OK" in (out or "") else \
            f"{h}:{src} gen_phys.py has no {GRT_ARM_GEN_MARK} (GRT-PATCH-1 runner not in this src; rc {rc})"
    return cache[(h, src)]


def grt_arm_withdraw(AP, cfg, rec, why):
    """append-only queue withdrawal of an ENQUEUED kit whose job has not started (enqueue.py --mode withdraw)"""
    d = (cfg.get("dies") or {}).get(rec["die"]) or {}
    try:
        pinned = json.loads((Path(rec["dir"]) / "spec.json").read_text())
        src = enqueue_src(AP, pinned, d)
    except (OSError, ValueError, KeyError) as e:
        return f"withdraw not sent: {e}"
    argv = ["python3", str(Path(__file__).resolve().parent / "enqueue.py"), "--die", rec["die"], "--type", rec["item"],
            "--kit", rec["kit"], "--src", src, "--geom", rec.get("geom_verdict") or "PASS",
            "--geom-ref", re.sub(r"\s+", " ", why)[:200], "--mem", str(place_mem_gb(cfg, rec["die"], rec["item"])),
            "--cells", "200000", "--lane", d.get("lane", LANE), "--mode", "withdraw"]
    rc, out, err = AP.sh(argv, timeout=300)
    return "withdrawn" if rc == 0 else f"withdraw rc {rc}: {(err or out)[-160:]}"


def grt_arm_reclaim(AP, rec, hosts):
    """delete the run data (GRT_ARM_RECLAIM) of a stopped attempt under its OWN dir .../items/<item>/attempt_<n> on each host
    that may hold it.  Fail-closed: a dir that is not this record's attempt_<n> (attempt 1's dir holds the later attempts), or
    one with any signoff.json under it, is left as it is and the reason is returned."""
    try:
        w = str(json.loads((Path(rec["dir"]) / "spec.json").read_text()).get("work") or "")
    except (OSError, ValueError, KeyError, TypeError):
        return "not reclaimed: spec.json unreadable"
    want = f"/items/{rec.get('item')}/attempt_{rec.get('attempt')}"
    if not w.startswith("/") or not w.endswith(want) or "/../" in w + "/" or int(rec.get("attempt") or 0) < 2:
        return f"not reclaimed: {w or '?'} is not this attempt's own dir"
    names = " -o ".join(f"-name {shlex.quote(g)}" for g in GRT_ARM_RECLAIM)
    cmd = (f"W=$(readlink -f {shlex.quote(w)}) || exit 0; [ -d \"$W\" ] || {{ echo KW_RECLAIM_SKIP absent; exit 0; }}; "
           f"case \"$W\" in *{shlex.quote(want)}) ;; *) echo KW_RECLAIM_SKIP resolves elsewhere; exit 0;; esac; "
           f"if find \"$W\" -name signoff.json -print -quit | grep -q .; then echo KW_RECLAIM_SKIP signoff.json; exit 0; fi; "
           f"b=$(du -sm \"$W\" | cut -f1); find \"$W\" -xdev -type f \\( {names} \\) -delete; "
           f"echo KW_RECLAIM $b $(du -sm \"$W\" | cut -f1)")
    out = []
    hub = getattr(AP, "HUB_NAME", "localhost")
    for h in [h for h in dict.fromkeys(hosts) if h]:
        remote = _ssh(h, hub)
        try:
            rc, o, _ = AP.sh(remote + ["bash -c " + shlex.quote(cmd)] if remote else ["bash", "-c", cmd], timeout=240)
        except Exception as e:                       # noqa: reclaim never stops the tick
            rc, o = 1, type(e).__name__
        m = re.search(r"KW_RECLAIM (\d+) (\d+)", o or "")
        k = re.search(r"KW_RECLAIM_SKIP ([^\n]+)", o or "")
        out.append(f"{h}: {m.group(1)}->{m.group(2)} MB" if m else f"{h}: skip {k.group(1)}" if k else f"{h}: rc {rc}")
    return "; ".join(out) or "no host"


def grt_arm_cancel(AP, cfg, rec, why, cls, jobs, notices):
    """stop one attempt by its exact units (wave unit + PLACE client, or its running route job; an unstarted queue row is
    withdrawn), stop its containers on the fleet, mark it CANCELLED <cls> and reclaim its run data"""
    units, withdraw, s = [], False, rec.get("status")
    j = (jobs or {}).get(rec.get("q_id")) or {}
    if s in ("RUNNING", "LAUNCHING"):
        units.append(rec.get("unit"))
        try:
            units.append(json.loads((Path(rec["dir"]) / "place_service.json").read_text())["unit"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
    elif s == "ENQUEUED":
        if j.get("status") == "RUNNING" and j.get("unit"):
            units.append(j["unit"])
        elif rec.get("kit"):
            withdraw = True
    if AP.DRY:
        AP.log(f"KIT-WAVE GRT-ARM would cancel {rec['die']}/{rec['item']}@{rec.get('attempt')} units {units}: {why}")
        return
    for u in units:
        if u:
            AP.sh(["systemctl", "--user", "stop", u], timeout=180)
    wd = grt_arm_withdraw(AP, cfg, rec, why) if withdraw else ""
    root = attempt_root(rec)
    stopped = ""
    if root and (units or s == "ENQUEUED"):
        res = WJ.stop_on_fleet(AP.sh, AP.HUB_NAME, [root])
        stopped = " ".join(WJ.stopped_names(res))[:300]
    try:
        gh = json.loads((Path(rec["dir"]) / "spec.json").read_text()).get("gen_host")
    except (OSError, ValueError, KeyError, TypeError):
        gh = None
    rec.update(status="CANCELLED", **{"class": cls}, updated=time.time(), reason=why[:300])
    rec["reclaim"] = grt_arm_reclaim(AP, rec, [gh, str(rec.get("kit") or "").partition(":")[0], j.get("ran_on")])
    notices.setdefault(rec["die"], []).append(f"{rec['item']}@{rec.get('attempt')} {cls}: {why[:200]}")
    AP.log(f"KIT-WAVE GRT-ARM CANCEL {rec['die']}/{rec['item']}@{rec.get('attempt')} units {units} {wd} "
           f"containers [{stopped or 'none'}] reclaim [{rec['reclaim']}]: {why}")


GRT_ARM_REPIN_FILE = "grt_halving_arm.repin"


def grt_arm_repin_due(ap_dir, rec):
    """AP_DIR/grt_halving_arm.repin: lines 'item<TAB>max_attempt'; an arm of that item at attempt <= max_attempt that is not
    yet flagged is cancelled (if live) and flagged repin, which lets grt_arm_launches launch it again from the pinned
    launcher (the new record carries no flag, and has a higher attempt, so it is not taken again)"""
    if (rec.get("arm") or {}).get("repin"):
        return False
    try:
        lines = (Path(ap_dir or ".") / GRT_ARM_REPIN_FILE).read_text().splitlines()
    except OSError:
        return False
    for ln in lines:
        f = ln.split("\t")
        if len(f) >= 2 and f[0] == rec.get("item") and f[1].strip().isdigit() and int(rec.get("attempt") or 0) <= int(f[1]):
            return True
    return False


def grt_arm_step(AP, cfg, st, notices, ap_dir):
    """arbitration + stop rule + class stop for every arm record (after collect/follow_queue, before any relaunch)"""
    items = st.get("items") or {}
    arms = [(k, r) for k, r in items.items() if isinstance(r.get("arm"), dict)]
    if not arms:
        return 0
    try:
        jobs = json.loads((Path(ap_dir) / "state.json").read_text()).get("jobs") or {}
    except (OSError, ValueError):
        jobs = {}
    n = 0
    for k, a in arms:
        die, mode = a.get("die"), a["arm"].get("mode")
        base = items.get(a["arm"].get("of")) or {}
        if grt_arm_repin_due(ap_dir, a):              # KW-FIX-46 (COORD 04:5x (e)): arm built from inputs unlike its sibling's
            if grt_arm_live(a):
                grt_arm_cancel(AP, cfg, a, f"GRT-ARM[{mode}] re-pin: its src/plan/bind differ from the sibling's; "
                                           "relaunched from the pinned launcher", "ARM-REPIN", jobs, notices)
                n += 1
            a["arm"]["repin"] = True
            a["arm"].pop("final", None)
            AP.log(f"KIT-WAVE GRT-ARM REPIN {die}/{a['item']}@{a.get('attempt')}")
            continue
        if a.get("status") == "RETRY-INFRA" and a.get("q_status") == "FAIL":
            a["status"] = "FAIL"                          # never: a route verdict is final (stop rule)
        if a.get("status") == "ENQUEUED" and a.get("q_status") == "FAIL" and not a["arm"].get("final"):
            a["arm"]["final"] = f"FAIL {a.get('q_class') or ''}: {str(a.get('q_reason') or '')[:160]}"
            notices.setdefault(die, []).append(
                f"{a['item']}@{a.get('attempt')} GRT-ARM[{mode}] FAIL, final (stop rule, no retry): {a['arm']['final']}")
            AP.log(f"KIT-WAVE GRT-ARM FINAL {die}/{a['item']}@{a.get('attempt')}: {a['arm']['final']}")
        stop = grt_arm_stop(cfg, die, ap_dir)
        if stop and grt_arm_live(a):
            grt_arm_cancel(AP, cfg, a, f"GRT-ARM[{mode}] class stop: {stop}", "ARM-STOP", jobs, notices)
            n += 1
            continue
        if grt_arm_signed(a) and base and base is not a and grt_arm_live(base):
            grt_arm_cancel(AP, cfg, base, f"GRT-ARM arbitration: the {mode} arm {a['item']}@{a.get('attempt')} signed off "
                                          f"first (job {a.get('q_id')}); this normal-path attempt is superseded",
                           "SUPERSEDED", jobs, notices)
            n += 1
        elif grt_arm_signed(base) and grt_arm_live(a):
            grt_arm_cancel(AP, cfg, a, f"GRT-ARM arbitration: the normal path {base.get('item')}@{base.get('attempt')} "
                                       f"signed off first (job {base.get('q_id')}); this {mode} arm is superseded",
                           "SUPERSEDED", jobs, notices)
            n += 1
        elif grt_arm_live(a) and counted_now(cfg, st, die, a.get("item"), a.get("block_sha")):
            grt_arm_cancel(AP, cfg, a, f"GRT-ARM[{mode}]: counted by the sign-off counter", "SUPERSEDED", jobs, notices)
            n += 1
    return n


def grt_arm_launches(AP, cfg, st, notices, ap_dir, nl=0, stagger=0.0):
    """launch the arms of every die option grt_halving_arm (once per row key and mode; never after a final FAIL)"""
    cur, n = None, 0
    cap = int(cfg.get("grt_arm_max_per_tick", GRT_ARM_MAX_PER_TICK))
    for die in sorted(cfg.get("dies") or {}):
        d = cfg["dies"][die]
        try:
            o = grt_arm_opt(cfg, die) if isinstance(d, dict) else None
        except ValueError as e:
            AP.log(f"KIT-WAVE GRT-ARM option refused: {e}")
            continue
        if not o or not o["items"] or grt_arm_stop(cfg, die, ap_dir) or stop_reason(cfg, die, ap_dir):
            continue
        cur = current_blocks(cfg, st) if cur is None else cur
        blocks = cur.get(die)
        if not blocks:
            continue                                      # no cached plan probe: nothing is judged current
        for item in o["items"]:
            if n >= cap:
                return n
            if item not in blocks:
                AP.log(f"KIT-WAVE GRT-ARM {die}/{item}: not an item of the current plan; no arm")
                continue
            base = item_key(die, d["event"], item, blocks[item])
            ak = grt_arm_key(base, o["mode"])
            brec = (st.get("items") or {}).get(base)
            if (ak in st["items"] and not (st["items"][ak].get("arm") or {}).get("repin")) or not brec or grt_arm_signed(brec) or counted_now(cfg, st, die, item, blocks[item]):
                continue
            if any(fnmatch.fnmatchcase(item, pat) for pat in (d.get("hold_items") or {})):
                continue                                  # an operator hold holds the arm too
            if d.get("only_items") is not None and item not in d["only_items"]:
                continue                                  # KW-FIX-45 11-11: a paused / restricted die (only_items) launches no arm
                                                          # either (QC only_items=[] still got 6 arm relaunches at 08:42)
            if load_hold(cfg, die, item, brec.get("parent_item"), core_module(item)):
                continue
            r = {"item": item, "kind": brec.get("kind") or "type", "parent_item": brec.get("parent_item"),
                 "block_sha": blocks[item], "replicas": brec.get("replicas"),
                 "arm": {"of": base, "key": ak, "mode": o["mode"], "gen_host": o.get("gen_host")}}
            rec = launch_safe(AP, cfg, st, die, r, AP.HUB_NAME, delay_s=(nl + n) * stagger)
            if rec:
                n += 1
                notices.setdefault(die, []).append(f"{item} GRT-ARM[{o['mode']}] LAUNCHED ({rec['unit']}, beside "
                                                   f"{brec.get('item')}@{brec.get('attempt')} {brec.get('status')})")
    return n


def stage_disk_wait(live_log):
    """KW-FIX-38 11-08: the stage client's KW12_DISK_WAIT line while it is the last line of the stage log (the wrapper
    sits behind a disk floor and nothing started), else ''"""
    try:
        with open(live_log, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 800))
            lines = [x for x in f.read().decode("utf-8", "replace").splitlines() if x.strip()]
    except OSError:
        return ""
    return lines[-1][:200] if lines and "KW12_DISK_WAIT" in lines[-1] else ""


# KW-FIX-46 REAP-DEAD (COORD 11-11, KW-FIX-45 finding: S81 rows RUNNING / RETRY-INFRA with no live process on any host).
# collect() already turns a RUNNING row whose systemd unit is gone into FAIL/RETRY-INFRA; what it never handles is
#   R1  a RUNNING / LAUNCHING row whose unit is gone and that stayed RUNNING for more than N minutes (collect did not
#       reach it: pass cut short, unit renamed, result unreadable): unit, PLACE client and fleet containers under its
#       attempt root are stopped by exact name, and the row becomes FAIL INFRA (the infra budget decides the retry);
#   R2  a RUNNING row whose unit is active but silent for N minutes while no process, container or ot-run command on any
#       fleet host names its attempt root (a zombie holding one of the die's slots): same stop and terminal state as R1;
#   R3  a RETRY-INFRA row that infra_relaunch_due() can never take again because its infra budget is spent (it was set
#       while the budget was open): it stays RETRY-INFRA for ever, counted as in flight.  It becomes a terminal FAIL INFRA.
# A silent row that is still named on the fleet (an ot-run waiter, a container) is only reported (SILENT).
# Never touched: held rows (hold_items), arms handled by their own rules, rows whose unit is active.
REAP_DEAD_MIN = 180
LIVE_PROBE = r'''
import json, os, subprocess, sys
roots = [r.rstrip('/') for r in json.loads(sys.argv[1])]
me = str(os.getpid())
hit = {}
for pid in filter(str.isdigit, os.listdir('/proc')):
    if pid == me:
        continue
    try:
        cl = open('/proc/%s/cmdline' % pid, 'rb').read().decode('utf-8', 'replace').replace('\0', ' ')
        cwd = os.readlink('/proc/%s/cwd' % pid)
    except OSError:
        continue
    if 'LIVE_PROBE' in cl or 'python3 -I -' in cl:
        continue
    for r in roots:
        if (r + '/') in cl or cl.rstrip().endswith(r) or cwd == r or cwd.startswith(r + '/'):
            hit.setdefault(r, []).append(pid)
ids = subprocess.run(['docker', 'ps', '-q', '--no-trunc'], capture_output=True, text=True, timeout=60).stdout.split()
if ids:
    for c in json.loads(subprocess.run(['docker', 'inspect'] + ids, capture_output=True, text=True, timeout=120).stdout or '[]'):
        for m in c.get('Mounts', []):
            for r in roots:
                if m.get('Type') == 'bind' and (m['Source'] == r or m['Source'].startswith(r + '/')):
                    hit.setdefault(r, []).append('docker:' + c['Name'].lstrip('/'))
print(json.dumps(hit))
'''


def live_on_fleet(AP, roots, hosts=None):
    """{root: [pid | docker:name]} found on ANY fleet host (process cmdline/cwd or container bind mount naming the root);
    None when a host could not be read (then nothing is reaped for silence)"""
    roots = sorted({r for r in roots if r})
    if not roots:
        return {}
    args = json.dumps(roots)
    hub = AP.HUB_NAME
    out = {}
    for h in (hosts or WJ.FLEET):
        cmd = ["python3", "-I", "-", args] if h in ("localhost", hub, os.uname().nodename) else \
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ControlPath=none", h, "python3", "-I", "-", shlex.quote(args)]
        try:
            rc, o, e = AP.sh(cmd, timeout=240, input=LIVE_PROBE)
            if rc == 255 and "Could not resolve hostname" in (e or ""):      # this host's own fleet alias: run it here
                rc, o, e = AP.sh(["python3", "-I", "-", args], timeout=240, input=LIVE_PROBE)
            if rc != 0 or not (o or "").strip():
                return None
            for r, v in json.loads(o.strip().splitlines()[-1]).items():
                out.setdefault(r, []).extend(f"{h}:{x}" for x in v)
        except Exception:                                    # noqa: an unreadable host reaps nothing
            return None
    return out


def reap_dead_scan(AP, cfg, st, now=None, minutes=None):
    """-> [(key, kind, why)] (read-only)"""
    now = now or time.time()
    minutes = REAP_DEAD_MIN if minutes is None else minutes
    out, silent = [], []
    for key, rec in sorted((st.get("items") or {}).items()):
        s = rec.get("status")
        age_m = (now - max(float(rec.get("updated") or 0), float(rec.get("started") or 0))) / 60.0
        if s in ("RUNNING", "LAUNCHING"):
            unit = rec.get("unit") or ""
            if unit and AP.unit_active(unit):
                try:
                    newest = max((f.stat().st_mtime for f in Path(rec["dir"]).glob("*.log")), default=0)
                except OSError:
                    newest = 0
                if newest and (now - newest) / 60.0 > minutes:
                    silent.append((key, rec, (now - newest) / 60.0))
                continue
            if age_m <= minutes:
                continue
            if (Path(rec.get("dir") or "/nonexistent") / "result.json").exists():
                continue                                  # collect reads it next tick
            out.append((key, "R1", f"unit {unit or '-'} gone, row RUNNING for {age_m:.0f} min without a terminal record"))
        elif s == "RETRY-INFRA":
            if infra_used(rec) >= infra_attempts(cfg, rec["die"]):
                out.append((key, "R3", f"RETRY-INFRA with the infra budget spent ({infra_used(rec)} of "
                                       f"{infra_attempts(cfg, rec['die'])}): never relaunched, {age_m / 60:.1f} h"))
    if silent:                                           # R2: an active unit with no output AND nothing alive on the fleet
        roots = {key: attempt_root(rec) for key, rec, _ in silent}
        hosts = list(WJ.FLEET)
        for d_ in (cfg.get("dies") or {}).values():
            for h in (d_.get("hosts") or cfg.get("hosts") or DEFAULTS["hosts"]) if isinstance(d_, dict) else []:
                h = AP.HUB_NAME if h == "localhost" else h
                if h not in hosts:
                    hosts.append(h)
        live = live_on_fleet(AP, list(roots.values()), hosts)
        for key, rec, m in silent:
            if live is None:
                out.append((key, "SILENT", f"unit active, no output for {m:.0f} min; fleet probe unreadable (reported only)"))
            elif live.get(roots[key]):
                out.append((key, "SILENT", f"unit active, no output for {m:.0f} min; alive: {','.join(live[roots[key]][:3])} (reported only)"))
            elif not roots[key]:
                out.append((key, "SILENT", f"unit active, no output for {m:.0f} min; no attempt root (reported only)"))
            else:
                out.append((key, "R2", f"unit active but no output for {m:.0f} min and no process, container or ot-run command "
                                       f"names {roots[key]} on any fleet host"))
    return out


def reap_dead(AP, cfg, st, notices, now=None):
    """apply reap_dead_scan under the wave lock (called from _step); die/global option reap_dead_min 0 = off"""
    minutes = float(cfg.get("reap_dead_min", REAP_DEAD_MIN))
    if minutes <= 0:
        return 0
    roots, n = [], 0
    for key, kind, why in reap_dead_scan(AP, cfg, st, now, minutes):
        if kind == "SILENT":
            AP.log(f"KIT-WAVE REAP-DEAD SILENT {key}: {why}")
            continue
        rec = st["items"][key]
        if AP.DRY:
            AP.log(f"KIT-WAVE REAP-DEAD would reap {key} {kind}: {why}")
            continue
        if kind in ("R1", "R2"):
            units = [rec.get("unit")]
            try:
                units.append(json.loads((Path(rec["dir"]) / "place_service.json").read_text())["unit"])
            except (OSError, ValueError, KeyError, TypeError):
                pass
            for u in units:
                if u:
                    AP.sh(["systemctl", "--user", "stop", u], timeout=180)
            r = attempt_root(rec)
            if r:
                roots.append(r)
        rec.update(status="FAIL", **{"class": "INFRA"}, updated=time.time(),
                   reason=f"REAP-DEAD {kind}: {why}"[:300])
        notices.setdefault(rec["die"], []).append(f"{rec['item']}@{rec.get('attempt')} REAP-DEAD {kind}: {why[:160]}")
        AP.log(f"KIT-WAVE REAP-DEAD {rec['die']}/{rec['item']}@{rec.get('attempt')} {kind}: {why}")
        n += 1
    if roots:
        res = WJ.stop_on_fleet(AP.sh, AP.HUB_NAME, roots)
        AP.log(f"KIT-WAVE REAP-DEAD remote stop: {' '.join(WJ.stopped_names(res))[:400] or 'none running'}")
    return n


def collect(AP, cfg, st, notices):
    for key, rec in st["items"].items():
        if rec.get("status") != "RUNNING" or AP.unit_active(rec["unit"]):
            if rec.get("status") == "RUNNING":
                try:
                    tail = (Path(rec["dir"]) / "unit.log").read_text().splitlines()
                    stg = [ln.split()[1] for ln in tail if ln.startswith("KW_STAGE ")]
                    rec["stage"] = stg[-1] if stg else "start"
                    rec["disk_wait"] = stage_disk_wait(Path(rec["dir"]) / f"{rec['stage']}.live.log")
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
        cell_check_note(AP, st, rec, res, notices)
        if "preflight_advisory" in res:                  # KW-FIX-44 11-10: the kit's contract advisories, per attempt
            rec["preflight_advisory"] = res["preflight_advisory"]
            line = advisory_line(res["preflight_advisory"])
            if line:
                notices.setdefault(rec["die"], []).append(f"{rec['item']} PREFLIGHT-ADVISORY {line}")
        if res.get("provisional"):                      # KW-PROV-1: {child module: routed <job> | contract}
            # KW-FIX-35-V: a child built on its counted signed view ('signed') is final, not owed a re-sign
            rec["provisional"] = {m: (v.get("source") if isinstance(v, dict) else v)
                                  for m, v in res["provisional"].items()
                                  if (v.get("source") if isinstance(v, dict) else v) != "signed"}
            rec["prov_signed"] = sorted(m for m, v in res["provisional"].items()
                                        if (v.get("source") if isinstance(v, dict) else v) == "signed")
        if res.get("verdict") == "PASS":
            for k in ("resume", "stage_fp"):
                if res.get(k):
                    rec[k] = res[k]
            rec.update(status="PASS", geom=res.get("geom_line", ""), cells=res.get("cells"), geom_dir=res.get("geom_dir"),
                       geom_tag=res.get("geom_tag", ""), geom_verdict=res.get("geom") or "PASS")
            enqueue_pass(AP, cfg, st, rec, notices)
            continue
        for k in ("resume", "stage_fp"):
            if res.get(k):
                rec[k] = res[k]
        cls, why = classify(res.get("stage", ""), (res.get("errors") or "") + "\n" + (res.get("tail") or ""))
        if res.get("class"):                             # KW-RESUME-1 'nochange': the previous attempt's class stands
            cls, why = res["class"], (res.get("reason") or why)
        rec.update(status="FAIL", **{"class": cls}, reason=why)
        if cls == "INFRA" and NO_HOST.search(why):       # KW-FIX-37: a host shortage spends no infra attempt, the row waits
            rec["infra_base"] = int(rec.get("infra_base") or 0) + 1
            rec["no_host_at"] = time.time()
            rec["status"] = "RETRY-INFRA"
        if cls == "INFRA" and infra_used(rec) < infra_attempts(cfg, rec["die"]):
            rec["status"] = "RETRY-INFRA"                # relaunched next tick (up to infra_attempts in all)
        notices.setdefault(rec["die"], []).append(f"{rec['item']} FAIL {cls} ({why[:160]}) evid {rec['evidence']}")
        AP.log(f"KIT-WAVE FAIL {rec['die']}/{rec['item']} {cls}: {why}")


CELL_FLAGS_REL = "lanes/FLAGS-CELLCHECK.tsv"


def cell_check_note(AP, st, rec, res, notices):
    """PLAN-GEN-RULES-1 rule C (OWNER 11-10, advisory, never a verdict): the first flagged cell check of an item in a
    die event becomes one PLAN-CHANGE notice for the die owner (the grouped KIT-WAVE queue line) and one FLAGS-shaped row
    in lanes/FLAGS-CELLCHECK.tsv.  Later attempts of the same item/event post nothing (first synthesis only)."""
    cc = res.get("cell_check")
    if not isinstance(cc, dict) or not cc.get("flags"):
        return
    seen = st.setdefault("cell_check_posted", {})
    key = f"{rec.get('die')}/{rec.get('event', '')}/{rec.get('item')}"
    if key in seen:
        return
    seen[key] = time.time()
    notices.setdefault(rec["die"], []).append(f"{rec['item']} PLAN-CHANGE (rule C) {'; '.join(cc['flags'])}: "
                                              f"{(cc.get('plan_change') or '')[:300]}")
    AP.coord_append(CELL_FLAGS_REL, "\t".join(str(x) for x in (
        now_s(), "-", rec.get("die"), rec.get("event", ""), "-", cc.get("type"), "yes", "cells", "A", "-",
        cc.get("density"), round(max((cc["density"] / cc["density_flag"]) if cc.get("density") else 0.0,
                                     (cc["ratio"] / cc["ratio_flag"]) if cc.get("ratio") else 0.0), 3),
        "; ".join(cc["flags"]), cc.get("plan_change") or "-", "-", "-")))


def infra_attempts(cfg, die):
    """attempts an item may use on INFRA failures (never on a design verdict); AUTOBUILD-PIPE-1 10-30: was 2, but an
    sshd burst on the gen host can drop the same item twice in one wave"""
    try:
        return max(2, int(opt(cfg, die, "infra_attempts")))
    except (TypeError, ValueError):
        return DEFAULTS["infra_attempts"]


def infra_used(rec):
    """attempts spent since the last design verdict (records before infra_base existed: all attempts)"""
    return int(rec.get("attempt") or 0) - int(rec.get("infra_base") or 0)


def rotate_dies(rows, die_of, pass_n):
    """KW-FIX-43 11-09 (COORD: S81 always last): the order of one pass's launches, the dies rotated by pass number.  Rows
    were taken in sorted die order, and with one gen host each tick filled its load cap before reaching s81 (0 S81 launches
    18:58-19:50, 50 rows waiting).  Stable within a die; pass 0 = sorted order."""
    dies = sorted({die_of(x) for x in rows})
    if len(dies) < 2:
        return list(rows)
    k = int(pass_n or 0) % len(dies)
    rank = {d: (i - k) % len(dies) for i, d in enumerate(dies)}
    return sorted(rows, key=lambda x: rank[die_of(x)])


def infra_relaunch_due(cfg, rec):
    """an INFRA failure the wave relaunches: RETRY-INFRA, or a FAIL INFRA record left by the old 2-attempt limit"""
    if infra_used(rec) >= infra_attempts(cfg, rec["die"]):
        return False
    # KW-FIX-10 11-05: a held item stays held here too.  serdes__t4 a1, stopped and held 11-04 23:37, came back as a2 at
    # 23:44 through this path, which is not plan_dies and never read hold_items.
    import fnmatch
    if any(fnmatch.fnmatchcase(rec.get("item", ""), pat)
           for pat in (((cfg.get("dies") or {}).get(rec["die"]) or {}).get("hold_items") or {})):
        return False
    if rec.get("status") == "RETRY-INFRA":
        # KW-FIX-37 11-08 (COORD 18:49, iq_C t1 'no host qualifies'): such a row retries, paced so a full fleet is not
        # hit with a new attempt on every tick
        return time.time() - float(rec.get("no_host_at") or 0) >= NO_HOST_RETRY_S
    return (rec.get("status") == "FAIL" and rec.get("class") == "INFRA"
            and ((cfg.get("dies") or {}).get(rec["die"]) or {}).get("event") == rec.get("event"))


def route_hold_reason(cfg, rec):
    """An optional die-owned hold on new ROUTE submissions, never on an admitted unit."""
    d = (cfg.get("dies") or {}).get(rec["die"]) or {}
    return next((str(why) for pat, why in (d.get("route_hold_items") or {}).items()
                 if why and fnmatch.fnmatchcase(rec["item"], pat)), None)


# KW-FIX-36 11-08 (e): a kit generated from a composed source pins queue_src "a@s1+b@s2" (with or without spaces), which
# the queue refuses ("src must be branch@sha": hbm q_spb1, q_su01, q_su11__physical_v1, vsN2, sfu_programme_store_r10,
# kv3_io_cor).  The queue row needs ONE commit that is really the source, so a composition resolves to one only when
# that is provable; it is never guessed:
#   - die option queue_src_exact {composed queue_src: "branch@sha"}: the operator's published composition commit, or
#   - the spec's src_sha, when every part is an ancestor of it or changes only tools/autopilot/ (operational tools run
#     from the live autopilot checkout, not kit content; e.g. the providx fix on top of the HBM integration commit).
# Anything else stays a FLOW failure naming the part that is not in the commit.
FREE_SRC_RE = re.compile(r"^([A-Za-z0-9_./-]+)\s+([0-9a-f]{7,40})(?:\s|$)")
SINGLE_SRC_RE = re.compile(r"^[A-Za-z0-9_./-]+@[0-9a-f]{7,40}$")      # autopilot.SRC_RE
COMPOSED_SRC_TOOL_PREFIX = "tools/autopilot/"
SRC_REFUSED = "enqueue rc 1: enqueue: REFUSED: src must be branch@sha"


def enqueue_src(AP, pinned, d):
    """the queue row's branch@sha for this launch spec (see above); ValueError when the source has no single commit"""
    qs = str(pinned.get("queue_src") or "").strip()
    if not qs:
        return "main@" + pinned["src_sha"]
    if SINGLE_SRC_RE.match(qs):
        return qs
    m = FREE_SRC_RE.match(qs)         # KW-FIX-45 11-11: free-text label 'main 730345725942 (QC 12:00 event ...)' (a GRT-ARM pins its sibling's) -> main@730345725942
    if m and "+" not in qs:
        return f"{m.group(1)}@{m.group(2)}"
    if "+" not in qs:               # not a composition: the queue's own check judges it
        return qs
    exact = (d.get("queue_src_exact") or {}).get(qs)
    if exact:
        if not SINGLE_SRC_RE.match(str(exact)):
            raise ValueError(f"queue_src_exact for {qs!r} is not branch@sha: {exact!r}")
        return str(exact)
    parts = [p for p in re.split(r"\s*\+\s*", qs) if p]
    if len(parts) < 2 or not all(SINGLE_SRC_RE.match(p) for p in parts):
        raise ValueError(f"queue_src {qs!r} is not a composition a@sha+b@sha")
    sha = str(pinned.get("src_sha") or "")
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        raise ValueError(f"composed queue_src {qs!r} has no src_sha to resolve to")
    git = lambda *a: AP.sh(["git", "-C", str(AP.REPO), *a], timeout=120)
    if git("rev-parse", "-q", "--verify", sha + "^{commit}")[0]:
        raise ValueError(f"composed queue_src: src_sha {sha} is not a commit on the hub")
    for p in parts:
        psha = p.rsplit("@", 1)[1]
        if sha.startswith(psha) or psha.startswith(sha) or not git("merge-base", "--is-ancestor", psha, sha)[0]:
            continue
        rc, base, _ = git("merge-base", sha, psha)
        rc2, files, _ = git("diff", "--name-only", base.strip(), psha) if not rc and base.strip() else (1, "", "")
        names = files.split()
        if rc2 or not names or not all(n.startswith(COMPOSED_SRC_TOOL_PREFIX) for n in names):
            raise ValueError(f"composed queue_src: part {p} is not in src_sha {sha[:12]} and changes kit content; "
                             f"publish a composition commit and set die option queue_src_exact")
    label = next((p.rsplit("@", 1)[0] for p in parts if sha.startswith(p.rsplit("@", 1)[1])), "")
    if not label:
        rc, refs, _ = git("for-each-ref", "--contains", sha, "--count=1", "--format=%(refname:lstrip=3)", "refs/remotes/origin")
        label = refs.strip() if not rc and refs.strip() and refs.strip() != "HEAD" else parts[0].rsplit("@", 1)[0]
    return f"{label}@{sha}"


def enqueue_pass(AP, cfg, st, rec, notices):
    # An already submitted row is immutable here, even if a hold is added later.
    if rec.get("status") == "ENQUEUED":
        return
    why = route_hold_reason(cfg, rec)
    if why:
        if rec.get("status") != "ROUTE-HELD" or rec.get("route_hold") != why:
            notices.setdefault(rec["die"], []).append(f"{rec['item']} AUTO-GEOM PASS, ROUTE held: {why}")
            AP.log(f"KIT-WAVE ROUTE-HOLD {rec['die']}/{rec['item']}: {why}")
        rec.update(status="ROUTE-HELD", route_hold=why, reason=f"ROUTE hold: {why}", updated=time.time())
        return
    if rec.pop("route_hold", None):
        rec.update(status="PASS", reason="", updated=time.time())
    d = cfg["dies"][rec["die"]]
    # The result belongs to its immutable launch spec, even if the config
    # changes while PLACE runs. Never relabel an old physical result.
    try:
        pinned = json.loads((Path(rec["dir"]) / "spec.json").read_text())
        if not pinned.get("queue_src") and not pinned.get("src_sha"):
            raise ValueError("launch spec has no source identity")
        src = enqueue_src(AP, pinned, d)
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
            "--mem", str(place_mem_gb(cfg, rec["die"], rec["item"])), "--cells", str(min(int(cells * 1.3), CELL_CAP_MAX) if cells else 200000),
            "--lane", d.get("lane", LANE)]
    if AP.DRY:
        AP.log("KIT-WAVE would enqueue: " + " ".join(argv))
        return
    if cfg.get("_enqueue_down"):                         # the coord remote failed earlier this tick: do not repeat the backoff
        rc, out, err = 1, "", "enqueue: NOT SUBMITTED: " + cfg["_enqueue_down"]
    else:
        rc, out, err = AP.sh(argv, timeout=300)
    if rc and (rc == 124 or "NOT SUBMITTED" in f"{err}{out}"):
        # KW6-CODE 11-04: the row did not reach coord/state (a transport error, not a verdict on the kit). The kit
        # stays PASS and retry_enqueue() sends it on a later tick; publish is idempotent, so a lost reply cannot
        # duplicate the row.
        why = (err or out)[-200:]
        cfg["_enqueue_down"] = why
        if not rec.get("enqueue_pending"):
            notices.setdefault(rec["die"], []).append(f"{rec['item']} AUTO-GEOM PASS, enqueue not submitted; retried next tick ({why[:120]})")
        rec.update(status="PASS", enqueue_pending=int(rec.get("enqueue_pending") or 0) + 1, **{"class": ""},
                   reason=f"enqueue pending, rc {rc}: {why}", updated=time.time())
        AP.log(f"KIT-WAVE ENQUEUE-PENDING {rec['die']}/{rec['item']}@{rec.get('attempt')} try {rec['enqueue_pending']}: {why}")
        return
    if rc:
        rec.pop("enqueue_pending", None)
        rec.update(status="FAIL", **{"class": "FLOW"}, reason=f"enqueue rc {rc}: {(err or out)[-200:]}")
        notices.setdefault(rec["die"], []).append(f"{rec['item']} AUTO-GEOM PASS but enqueue failed rc {rc}")
        return
    if rec.pop("enqueue_pending", None):
        rec.update(reason="", updated=time.time())
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


def retry_enqueue(AP, cfg, st, notices):
    """send the kits enqueue_pass() kept PASS on a transport failure. Only records it marked: old FAIL FLOW rows whose
    reason reads NOT SUBMITTED stay with the operator (some hold kits older than a class fix). A die stop or a
    hold_items match waits; a block that left the current plan is closed, not sent. ROUTE-HELD records resume
    here without regenerating, replacing or repeating the completed geometry review."""
    import fnmatch
    n = 0
    for rec in (st.get("items") or {}).values():
        # KW-FIX-36 (e): the queue's grammar refusal was a tool bug, not a verdict on the kit: resend it through
        # enqueue_src.  A composition with no single commit then fails with its own reason and is not resent.
        if rec.get("kit") and rec.get("status") == "FAIL" and str(rec.get("reason") or "").startswith(SRC_REFUSED):
            rec.update(status="PASS", enqueue_pending=1, **{"class": ""}, updated=time.time())
        if not rec.get("kit") or not (rec.get("status") == "ROUTE-HELD" or
                (rec.get("status") == "PASS" and rec.get("enqueue_pending"))):
            continue
        d = (cfg.get("dies") or {}).get(rec.get("die"))
        if not isinstance(d, dict) or stop_reason(cfg, rec["die"], cfg.get("_ap_dir") or AP.AP_DIR):
            continue
        if any(fnmatch.fnmatchcase(rec["item"], pat) for pat in (d.get("hold_items") or {})):
            continue
        if _plan_current(cfg, st, rec) is False:
            rec.pop("enqueue_pending", None)
            rec.update(status="CANCELLED", **{"class": "SUPERSEDED"}, updated=time.time(),
                       reason="enqueue pending on a superseded plan block (plan_current=no); not sent")
            notices.setdefault(rec["die"], []).append(f"{rec['item']}@{rec.get('attempt')} SUPERSEDED: pending enqueue not sent")
            continue
        enqueue_pass(AP, cfg, st, rec, notices)
        n += 1
    return n


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
        # S81-OTHERFAIL-1 11-07: autopilot keeps the reject reason only in history (c1x_C t6/t7 showed an empty
        # reason): fall back to the last history entry; a kit that carries an LEC FAIL_PREFLOOR is an RTL verdict
        last = str((j.get("history") or [[0, 0, ""]])[-1][-1] or "")
        msg = str(j.get("error") or why or last)[:200]
        return "queue", "FAIL", ("RTL" if re.search(r"LEC NOT EQUIVALENT|KEEP FAIL", msg) else "FLOW"), \
            "queue row rejected: " + msg
    if stt == "DONE-CRASH":
        return "route", "FAIL", ("INFRA" if kind.startswith("infra") else "FLOW"), f"{kind}: {why}"
    if stt.startswith("DONE-"):
        eco = (j.get("chain") or {}).get("eco") if isinstance(j.get("chain"), dict) else None
        if isinstance(eco, dict) and eco.get("verdict") in ("EXHAUSTED", "ERROR") and "late-ECO" not in why:
            # KW-ECO-1: the class table names a route/sign-off FAIL the late-stage ECO loop could not repair
            why = (str(eco.get("summary") or "late-ECO exhausted")[:160] + " | " + why)[:300]
        fails = set(so.get("fails") or [])
        tt, ff = so.get("tt_wns"), so.get("ff_wns")
        drc = so.get("drc") or 0
        stage = "signoff" if so else "route"
        if kind == "pg-unbound" or (fails & FLOW_FAILS):
            return stage, "FAIL", "FLOW", f"{kind}: {why}"
        if kind == "preflight" and re.search(r"KILLED \(yosys signal", why):
            return stage, "FAIL", "INFRA", f"{kind}: {why}"          # S81-OTHERFAIL-1: host OOM kill, not a verdict
        if kind in ("preflight", "cell-cap", "diagnostic-overrun"):
            return stage, "FAIL", ("FLOW" if kind == "diagnostic-overrun" else "PLAN"), f"{kind}: {why}"
        if kind == "grt-overflow" or (fails & ROUTING_FAILS) or drc:
            return stage, "FAIL", "ROUTING", f"{kind}: drc {drc} {why}".strip()
        if kind in ("post-cts-hold", "hold-structural", "grt-timecap") or (fails & TIMING_FAILS) or any(
                w is not None and w < 0 for w in (tt, ff)):
            # KIT-TRIAGE-1/G5: pre-route stops have no sign-off record -> no 'TT None FF None'; the gate line is in why
            wns = f"TT {tt} FF {ff} ps " if (tt is not None or ff is not None) else ""
            return stage, "FAIL", "TIMING", f"{kind}: {wns}{why}".strip()
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
        cls, why = leafslew_plan_route(rec, status, cls, why)
        old = (rec.get("q_status"), rec.get("q_class"))
        rec.update(q_id=j.get("id"), q_stage=stage, q_status=status, q_class=cls, q_reason=why)
        if status == "CANCELLED":
            # KW-FIX-45 11-11 (COORD option (a), orphaned q_b003__physical_v1 pilot): a queue job that was cancelled (ot-run
            # --cancel / cancel-dir, a stopped route) is a stopped attempt, not a failure and not a superseded block: the
            # wave row becomes CANCELLED (class QUEUE-CANCELLED) so a retry entry item@attempt relaunches it (select()
            # relaunches a CANCELLED row only when its retry entry names the attempt; resume_source allows a re-gen of a
            # CANCELLED attempt)
            rec.update(status="CANCELLED", **{"class": "QUEUE-CANCELLED"}, updated=time.time(),
                       reason=f"queue job {j.get('id')} cancelled: {str(why)[:160]}")
            notices.setdefault(rec["die"], []).append(f"{rec['item']} queue job {j.get('id')} CANCELLED -> row CANCELLED "
                                                      f"(retry {rec['item']}@{rec.get('attempt')} relaunches)")
            n += 1
            continue
        so = j.get("signoff") if isinstance(j.get("signoff"), dict) else {}
        if status == "FAIL" and so.get("path"):
            # KW-FIX-17: where the routed sign-off of this attempt lives (leafslew_step reads its TT sta.log)
            kh = str(j.get("kit") or "").split(":", 1)[0] if ":" in str(j.get("kit") or "") else ""
            rec.update(q_signoff=so["path"], q_hosts=[h for h in dict.fromkeys([j.get("ran_on"), kh, j.get("host")]) if h])
        n += 1
        if (status, cls) != old:
            rec["q_updated"] = time.time()
        if (status, cls) != old and (status in ("SIGNED", "FAIL")):
            msg = (f"{rec['item']} SIGNED OFF -> count ({why[:120]})" if status == "SIGNED" else
                   f"{rec['item']} {stage} FAIL {cls} ({why[:160]}) job {j.get('id')}")
            notices.setdefault(rec["die"], []).append(msg)
    return n


ADMITTED = "ot-heavy: admitted on"            # ot-run echoes the host's admission line (OT_RUN_START stripped)
PILOT_FAIL_CLASSES = ("PLAN", "RTL", "FLOW", "TIMING", "ROUTING")


def is_wait_dep(r):
    """KW-FIX-1 11-02 (COORD 19:2x): a FAIL record whose class reason is WAIT-DEP (a child hard core / ROM view of
    the type has a lef but no lib yet) is a dependency wait, not a failure: kit_wave_stages.tsv shows it PENDING-DEP
    and it never stops its class volume (pilot gate).  The type relaunches on its own once the plan carries the signed
    child view (new block sha = new item key); the child cores already launch first (select() sorts cores first)."""
    return r.get("status") == "FAIL" and str(r.get("reason") or "").startswith("WAIT-DEP")


def rec_src_sha(rec):
    """the src_sha an attempt was generated from (its spec.json), '' when unknown"""
    try:
        return json.loads((Path(rec["dir"]) / "spec.json").read_text()).get("src_sha") or ""
    except (OSError, ValueError, KeyError, TypeError):
        return ""


def pilot_fail_times(d, die, state, src_sha=""):
    """-> {class: latest pilot FAIL time} over the die's non-volume records.  KIT-WAVE-14 11-01: an AUTO-GEOM FAIL
    (stage 'geom') is a per-block geometry verdict -- GEOM review often releases it PASS-COND (fill/empty standing
    exceptions) and it says nothing about the other blocks of the class -- so it never stops the class volume
    (slice_station__t26 geom FAIL cancelled 12 queued S81 stations at 10:16)."""
    fail_t = {}
    for r in (state.get("items") or {}).values():
        if r.get("die") != die or r.get("volume") or r.get("arm"):
            continue
        c = pilot_key(d, die, r.get("item"), r.get("kind") or "type")
        t = None
        if (r.get("status") == "FAIL" and r.get("class") in PILOT_FAIL_CLASSES and r.get("stage") != "geom"
                and not is_wait_dep(r)):
            t = float(r.get("updated") or 0)
        elif r.get("status") == "ENQUEUED" and r.get("q_status") == "FAIL":
            t = float(r.get("q_updated") or r.get("updated") or 0)
        # KW-FIX-4 11-03 (I2 RESET-CORE batch: old-src col_h9 attempts failing OT_RESET_CORE at 17:21 cancelled the
        # class-fix volume just launched on the fixed src): with src_sha given, only a pilot FAIL generated from that
        # same source counts -- a failure on a superseded source says nothing about volume on the current one
        if t is not None and t > fail_t.get(c, 0.0) and src_sha and rec_src_sha(r) not in ("", src_sha):
            t = None
        if t is not None:
            fail_t[c] = max(fail_t.get(c, 0.0), t)
    return fail_t


def volume_started(rec):
    """True when the item's current ot-run stage was admitted on its host (the command runs; never cancelled)"""
    try:
        lives = sorted(Path(rec["dir"]).glob("*.live.log"), key=lambda f: f.stat().st_mtime)
        return bool(lives) and ADMITTED in lives[-1].read_text(errors="replace")
    except OSError:
        return True                                     # unreadable -> treat as running (never cancel blind)


KEEP_STAGES = ("place",)        # KW-FIX-35-H 11-08: an attempt past one of these keeps its host (restage / volume cancel)


def heavy_progress(rec):
    """KW-FIX-35-H 11-08: the first P&R stage of KEEP_STAGES this attempt finished (unit.log KW_STAGE_RC <s> 0) or that
    was admitted on its host (its live log says ADMITTED), else ''.  volume_started only reads the CURRENT stage, so
    restage_waiters stopped attempts whose PLACE had already run (HEAD hd_lep0N a13 11-07 05:08: place RC 0 after
    1.5 h, geom in a disk wait) and the relaunch started again from mkdir; HEAD hd_host/hd_lep0N/hd_serdes were
    restaged 30 times 11-06/07.  Such an attempt waits where it is; unreadable logs count as progress (never stop blind)."""
    try:
        d = Path(rec["dir"])
        log = (d / "unit.log").read_text(errors="replace") if (d / "unit.log").exists() else ""
        for s in KEEP_STAGES:
            if re.search(rf"^KW_STAGE_RC {re.escape(s)} 0\b", log, re.M):
                return s
            lv = d / f"{s}.live.log"
            if lv.exists() and ADMITTED in lv.read_text(errors="replace"):
                return s
    except (OSError, KeyError, TypeError):
        return "unreadable"
    return ""


def cancel_class_volume(AP, cfg, st, notices):
    """OWNER 11-01 (COORD 05:3x (1)): when a pilot of an unproven die x kit class fails on a design/flow class after
    volume of that class was queued, stop that volume while it still WAITS (its current ot-run stage not admitted);
    started volume runs on.  Cancelled volume relaunches by itself once the class has a signed-off kit."""
    items = st.get("items") or {}
    n = 0
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or not pilot_queue_mode(d, cfg):
            continue
        signed, _ = pilot_classes_state(d, die, st)
        fail_t = pilot_fail_times(d, die, st, d.get("src_sha") or "")
        for r in items.values():
            c = r.get("volume")
            if r.get("die") != die or r.get("status") != "RUNNING" or not c or c in signed:
                continue
            if fail_t.get(c, 0.0) <= float(r.get("started") or 0) or volume_started(r) or heavy_progress(r):
                continue
            if not AP.DRY:
                AP.sh(["systemctl", "--user", "stop", r["unit"]], timeout=180)
                try:                                     # its detached PLACE client still waits for admission too
                    svc = json.loads((Path(r["dir"]) / "place_service.json").read_text())
                    AP.sh(["systemctl", "--user", "stop", svc["unit"]], timeout=180)
                except (OSError, ValueError, KeyError):
                    pass
            r.update(status="CANCELLED", **{"class": "VOLUME"}, updated=time.time(),
                     reason=f"queued volume of {c} cancelled: a pilot of the class failed (OWNER 11-01); relaunches when "
                            f"the class signs off")
            notices.setdefault(die, []).append(f"{r['item']} queued volume CANCELLED (pilot of {c} failed)")
            AP.log(f"KIT-WAVE CANCEL-VOLUME {die}/{r['item']} unit {r['unit']} class {c}")
            n += 1
    return n


def attempt_root(r):
    """the attempt's dir on its host (spec.json work), else its kit path; '' when neither is known"""
    try:
        return json.loads((Path(r["dir"]) / "spec.json").read_text())["work"]
    except (OSError, ValueError, KeyError, TypeError):
        return (r.get("kit") or "").partition(":")[2]


def cancel_superseded(AP, cfg, st, notices, ap_dir=None):
    """COORD 11-01 18:3x (KV kv3_io_ft pre-fix kits ran GRT 22.5 h after a newer fix superseded them): an attempt
    whose plan block is no longer in the die's current plan of record (plan_current=no) can never count, so it is
    stopped at the next tick -- a RUNNING/LAUNCHING wave unit (and its detached place client) and the autopilot
    route job of an ENQUEUED kit -- and marked CANCELLED class SUPERSEDED.  The current block is a different key
    and launches on its own.  Only dies with a cached current-plan probe are judged; die option cancel_superseded
    false opts out; at most supersede_max_per_tick stops per tick (a mass stop is logged, not hidden).  The containers of a
    stopped attempt are stopped on every fleet host too (WATCHDOG-1 11-03); watchdog.py is the net for a host missed here.
    KW-FIX-35-K 11-08 (KV kv3_phy@7 in geom and kv3_phy_v1@4 in place were stopped 08:22 by a plan switch while both
    items were in hold_items "in flight, do not re-pick"): an active row is KEPT, never stopped, when (a) its item matches
    the die's hold_items -- an operator hold means the row's owner decides, the wave neither re-picks nor cancels it -- or
    (b) its own plan block is unchanged (the record's block_sha equals the item's block in the current plan, so only the
    event label or another item moved).  Each keep is logged once per row and reason (KIT-WAVE SUPERSEDED-KEEP)."""
    cur = current_keys(cfg, st)
    cur_blocks = current_blocks(cfg, st)
    jobs = {}
    if ap_dir:
        try:
            jobs = json.loads((Path(ap_dir) / "state.json").read_text()).get("jobs") or {}
        except (OSError, ValueError):
            jobs = {}
    cap = int(cfg.get("supersede_max_per_tick", DEFAULTS.get("supersede_max_per_tick", 20)))
    n = 0
    roots = []
    for key, r in (st.get("items") or {}).items():
        die = r.get("die")
        d = (cfg.get("dies") or {}).get(die)
        if die not in cur or ((r.get("arm") or {}).get("of") or key) in cur[die] or not isinstance(d, dict) \
                or d.get("cancel_superseded") is False:
            continue
        if r.get("status") in ("RUNNING", "LAUNCHING", "ENQUEUED"):
            item = r.get("item") or ""
            held = next((str(w) for pat, w in (d.get("hold_items") or {}).items() if fnmatch.fnmatchcase(item, pat)), None)
            same = bool(r.get("block_sha")) and cur_blocks.get(die, {}).get(item) == r.get("block_sha")
            if held is not None or same:
                why = (f"hold_items: {held[:160]}" if held is not None else
                       f"own plan block {str(r.get('block_sha'))[:12]} unchanged in the current plan")
                if r.get("supersede_kept") != why:
                    r["supersede_kept"] = why
                    AP.log(f"KIT-WAVE SUPERSEDED-KEEP {die}/{item}@{r.get('attempt')} {r.get('status')}: {why}")
                continue
        units = []
        if r.get("status") in ("RUNNING", "LAUNCHING"):
            units.append(r.get("unit"))
            try:
                units.append(json.loads((Path(r["dir"]) / "place_service.json").read_text())["unit"])
            except (OSError, ValueError, KeyError, TypeError):
                pass
            what = f"wave {r.get('stage') or r.get('status')}"
        elif r.get("status") == "ENQUEUED" and r.get("q_id"):
            j = jobs.get(r["q_id"]) or {}
            if j.get("status") != "RUNNING" or not j.get("unit"):
                continue
            units.append(j["unit"])
            what = f"queue job {r['q_id']}"
        else:
            continue
        if n >= cap:
            AP.log(f"KIT-WAVE SUPERSEDED cap {cap} reached; {die}/{r.get('item')} waits for the next tick")
            break
        if not AP.DRY:
            for u in units:
                if u:
                    AP.sh(["systemctl", "--user", "stop", u], timeout=180)
            roots.append(attempt_root(r))
        r.update(status="CANCELLED", **{"class": "SUPERSEDED"}, updated=time.time(),
                 reason=f"{what} on a superseded plan block (plan_current=no) stopped; the current block "
                        f"relaunches on its own key (COORD 11-01 18:3x)")
        notices.setdefault(die, []).append(f"{r.get('item')}@{r.get('attempt')} SUPERSEDED: {what} stopped")
        AP.log(f"KIT-WAVE CANCEL-SUPERSEDED {die}/{r.get('item')}@{r.get('attempt')} {what} units {units}")
        n += 1
    if roots:
        # the units above are hub clients; ot-run leaves a started command running on its host (HUNG-1103)
        res = WJ.stop_on_fleet(AP.sh, AP.HUB_NAME, roots)
        AP.log(f"KIT-WAVE CANCEL-SUPERSEDED remote stop: {' '.join(WJ.stopped_names(res))[:600] or 'none running'}"
               + "".join(f"; {h} not checked: {v['error']}" for h, v in res.items() if v.get("error")))
    return n


def step(AP, ap_dir=None):
    """one wave pass; a non-blocking lock keeps two passes (tick + CLI step) from double-launching"""
    import fcntl
    ap_dir = ap_dir or AP.AP_DIR
    if os.environ.get("KW_LOCK_HELD") == "1":           # reload_step child: the parent pass holds kit_wave.lock
        return _step(AP, ap_dir)
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
    if not scheduler_current(AP):
        return reload_step(AP, ap_dir)
    cfg = load_config(AP.read_coord("autopilot/kit_wave.json"))
    merge_auto_views(cfg, ap_dir, AP.log)                # KW-FIX-35-CV: counted child views overlay (hub sidecar)
    merge_src_overlay(cfg, AP.HUB_NAME, AP.log)          # KW-FIX-44: spec field for in-place source overlays
    # NEAR-COUNT (COORD 11-01 KIT-WAVE-16 (6)): items in lanes/NEAR-COUNT.tsv launch with --priority die --crit
    cfg["_near_count"] = AP.parse_near_count(AP.read_coord(AP.NEAR_COUNT_FILE)) if hasattr(AP, "parse_near_count") else set()
    st = load_state(ap_dir)
    import source_follow
    source_follow.step(AP, cfg, st)
    st.setdefault("items", {})
    notices = {}
    prune_stale_retries(cfg, st, notices, AP.log)
    collect(AP, cfg, st, notices)
    try:                                                 # KW-FIX-46 REAP-DEAD: under the wave lock, right after collect
        reap_dead(AP, cfg, st, notices)
    except Exception as e:                              # a sweep never stops the tick
        AP.log(f"KIT-WAVE REAP-DEAD skipped: {type(e).__name__}: {e}")
    retry_enqueue(AP, cfg, st, notices)
    follow_queue(st, ap_dir, notices)
    auto_rejudge(AP, cfg, st, notices)
    try:
        release_pending(cfg, st, parse_pending(AP.read_coord(PENDING_FILE)), _merged(AP, cfg), notices)
    except Exception as e:                               # a missing/unreadable pending file never blocks the wave
        AP.log(f"KIT-WAVE pending retries skipped: {type(e).__name__}: {e}")
    try:                                                 # KW-FIX-17: LEAFSLEW signature -> auto class retry
        leafslew_step(AP, cfg, st, notices, AP.HUB_NAME)
    except Exception as e:                               # a sign-off log read never blocks the wave
        AP.log(f"KIT-WAVE LEAFSLEW step skipped: {type(e).__name__}: {e}")
    prune_stale_retries(cfg, st, notices, AP.log)          # KW-FIX-23: pending / LEAFSLEW entries too
    cancel_class_volume(AP, cfg, st, notices)
    cancel_superseded(AP, cfg, st, notices, ap_dir)
    try:                                        # KW-FIX-44 GRTARM_1111: arm arbitration / stop rule / class stop
        grt_arm_step(AP, cfg, st, notices, ap_dir)
    except Exception as e:                      # an arm problem never stops the wave
        AP.log(f"KIT-WAVE GRT-ARM step skipped: {type(e).__name__}: {e}")
    try:                                        # SUBSTEP-1 (COORD 11-05 10:53): sub-step ODBs of terminal attempts
        import substep_prune
        substep_prune.tick(AP, cfg, st, ap_dir, lambda h: _ssh(h, AP.HUB_NAME),
                           AP.read_coord)
    except Exception as e:                      # disk hygiene never stops the tick
        AP.log(f"KIT-WAVE SUBSTEP-1 skipped: {type(e).__name__}: {e}")
    rc, out, _ = AP.sh([OT_RUN, "--status"], timeout=120)
    status = parse_otrun_status(out if rc == 0 else "")
    cfg["_otrun_status"], cfg["_hub"], cfg["_ap_dir"] = {h: dict(v) for h, v in status.items()}, AP.HUB_NAME, ap_dir
    global GEN_DISK_MIN_GB
    GEN_DISK_MIN_GB = int(cfg.get("gen_disk_min_gb", 60))
    low = sorted(h for h, v in status.items() if gen_disk_low(v))
    if low:
        txt = " ".join("%s=%s" % (h, status[h]["scratch_gb"]) for h in low)
        AP.log(f"KIT-WAVE GEN-DISK-LOW {txt} GB < {GEN_DISK_MIN_GB}: new/restaged attempts go to gen hosts with room "
               "(KW-FIX-24)")
    try:                                        # KW-FIX-30: the disk under each die's work_root
        cfg["_workroot_low"] = workroot_low(AP, cfg)
        for h, ds in sorted(cfg["_workroot_low"].items()):
            # KW-FIX-44 11-10 (COORD): each die's own limit (a root-fs lane needs root_floor_gb + root_gen_room_gb,
            # 150 + 40); the line used to print gen_disk_min_gb for all ('hbm=143 ... GB < 70')
            lims = (cfg.get("_workroot_lim") or {}).get(h, {})
            AP.log(f"KIT-WAVE GEN-DISK-LOW work_root {h}: " + " ".join(
                       f"{d}={g}<{lims.get(d, GEN_DISK_MIN_GB)}" for d, g in sorted(ds.items()))
                   + " GB free<needed (root-fs lane: root_floor_gb + root_gen_room_gb; scratch lane: gen_disk_min_gb;"
                   " not a gen host for those dies while another has room; KW-FIX-30)")
    except Exception as e:                      # a diagnostic probe never stops the tick
        AP.log(f"KIT-WAVE work_root disk probe skipped: {e}")
    if cfg.get("_workroot_alt"):
        AP.log("KIT-WAVE WORKROOT-ALT root-fs lane full, scratch2 has room: " + "; ".join(
            f"{h}: {' '.join(sorted(a))}" for h, a in sorted(cfg["_workroot_alt"].items()) if a))
    try:
        cfg["_spill_marked"] = spill_marked(AP, cfg)
        for h, rs in cfg["_spill_marked"].items():
            if rs:
                AP.log(f"KIT-WAVE SPILL-MARKED {h}: {' '.join(sorted(rs))} (ot-run treats dirs there as stale copies; "
                       "not a gen host for those dies)")
    except Exception as e:                      # a diagnostic probe never stops the tick
        AP.log(f"KIT-WAVE spill-mark probe skipped: {e}")
    try:                                        # KW-FIX-24 stale-source class
        cfg["_src_incomplete"] = src_incomplete(AP, cfg)
        for h, ds in sorted(cfg["_src_incomplete"].items()):
            for die, why in sorted(ds.items()):
                AP.log(f"KIT-WAVE SRC-INCOMPLETE {h} {die}: {why} (not a gen host for the die until its copy is whole)")
    except Exception as e:                      # a diagnostic probe never stops the tick
        AP.log(f"KIT-WAVE src probe skipped: {e}")
    load_counter_signed(cfg)
    restage_waiters(AP, cfg, st, notices)
    try:
        reap_orphan_waiters(AP, cfg)
    except Exception as e:                      # a diagnostic sweep never stops the tick
        AP.log(f"KIT-WAVE REAP skipped: {e}")
    stagger = float(cfg.get("launch_stagger_s", DEFAULTS["launch_stagger_s"]))
    nl = 0                                               # items launched this tick: start delay nl * stagger
    if not scheduler_current(AP):                        # code changed during collect: launch on the current code now
        if not AP.DRY:
            save_state(st, ap_dir)
            write_stages(st, ap_dir, cfg)
        return reload_step(AP, ap_dir)
    held = {}                                            # SCHED-1: rows left pending this tick, per die
    for key, rec in rotate_dies(list(st["items"].items()), lambda kv: kv[1]["die"], st.get("pass_n")):  # INFRA relaunch (up to infra_attempts)
        # Semantic adoption requires a fresh profile proof. Never launch an
        # old pending retry before plan_dies has had a chance to hold it.
        identity_mode = (cfg.get("dies", {}).get(rec["die"]) or {}).get("block_identity", "raw")
        if infra_relaunch_due(cfg, rec) and counted_now(cfg, st, rec["die"], rec["item"], rec.get("block_sha")):
            rec.update(status="CANCELLED", **{"class": "COUNTED"}, updated=time.time(),
                       reason="counted by the sign-off counter, not relaunched (KW-FIX-27)")
            AP.log(f"KIT-WAVE COUNTED {rec['die']}/{rec['item']}: not relaunched")
            continue
        if infra_relaunch_due(cfg, rec) and identity_mode == "raw" and not stop_reason(cfg, rec["die"], ap_dir):
            if load_hold(cfg, rec["die"], rec["item"], rec.get("parent_item"), core_module(rec["item"])):
                held[rec["die"]] = held.get(rec["die"], 0) + 1
                continue                                 # stays RETRY-INFRA, next tick
            if not ensure_plan_view(AP, st, cfg["dies"].get(rec["die"])):
                continue                                 # plan unreadable: stays RETRY-INFRA, next tick
            rec["status"] = "FAIL"
            launch_safe(AP, cfg, st, rec["die"], {"item": rec["item"], "kind": rec.get("kind", "type"),
                                              "parent_item": rec.get("parent_item"), "block_sha": rec.get("block_sha"),
                                              "replicas": rec.get("replicas"), "arm": rec.get("arm")},
                        AP.HUB_NAME, delay_s=nl * stagger)
            nl += 1
    if nl and not AP.DRY:                                # launched units are on record before anything else can raise
        save_state(st, ap_dir)
    owners = parse_owners((Path(ap_dir) / "OWNERS.tsv").read_text() if (Path(ap_dir) / "OWNERS.tsv").exists() else "")
    res, todo = plan_dies(AP, cfg, st, owners, status, AP.HUB_NAME)
    try:                                                 # KW-FIX-35-CV: export counted child views (hourly per die)
        auto_views_step(AP, cfg, st, ap_dir)
    except Exception as e:                               # an export launch never stops the wave
        AP.log(f"KIT-WAVE AUTO-VIEWS skipped: {type(e).__name__}: {e}")
    if cfg.get("hold_unchanged"):
        try:
            write_redesign(cfg, st, ap_dir)
        except Exception as e:                  # a report never stops the tick
            AP.log(f"KIT-WAVE redesign list skipped: {e}")
    for die, ok, why, picks, skip in res:
        n = sum(len(its) for w, its in skip.items() if w.startswith("LOAD-HOLD"))
        if n:
            held[die] = held.get(die, 0) + n
    for die, r in todo:
        if load_hold(cfg, die, r["item"], r.get("parent_item"), core_module(r["item"])):  # this tick's launches filled the hosts
            held[die] = held.get(die, 0) + 1
            continue
        rec = launch_safe(AP, cfg, st, die, r, AP.HUB_NAME, delay_s=nl * stagger)
        nl += 1
        if rec:
            notices.setdefault(die, []).append(f"{r['item']} LAUNCHED ({rec['unit']})")
    try:                                                 # KW-FIX-44 GRTARM_1111: halving-off arms
        nl += grt_arm_launches(AP, cfg, st, notices, ap_dir, nl, stagger)
    except Exception as e:                               # an arm problem never stops the wave
        AP.log(f"KIT-WAVE GRT-ARM launches skipped: {type(e).__name__}: {e}")
    if nl and not AP.DRY:
        save_state(st, ap_dir)
    if cfg.get("_gen_fallback_taken"):
        AP.log("KIT-WAVE GEN-DISK-FALLBACK no gen host over gen_disk_min_gb; gens on the most free host above the real floor: "
               + " ".join(f"{h}={n}" for h, n in sorted(cfg["_gen_fallback_taken"].items())))
    try:
        prov_resign_step(AP, cfg, st, notices, ap_dir, AP.HUB_NAME)
    except Exception as e:                               # a re-sign problem never stops the wave
        AP.log(f"KIT-WAVE PROV-RESIGN step skipped: {type(e).__name__}: {e}")
    for die, msgs in notices.items():
        lane = (cfg["dies"].get(die) or {}).get("owner_lane", f"{die} owner")
        AP.coord_append("lanes/COORD-REVIEW-QUEUE.md",
                        f"- {now_s()} KIT-WAVE [{die}] -> {lane}: {len(msgs)} event(s): " + "; ".join(msgs)[:1800])
    protect_sources(AP, cfg, st, ap_dir)
    if not AP.DRY:
        save_state(st, ap_dir)
        write_stages(st, ap_dir, cfg)
    return st


PROTECT_REL = ".local/state/wt-reaper/protect.d/kit_wave.txt"


_ABS_PATH_RE = re.compile(r"(?<![\w.~$/])/(?:srv|home|data|mnt)/[^\s'\"<>|;,:()\[\]{}=\\`*?$]+")


def _config_paths(v, key=""):
    """FLOW-19: every absolute path inside a die config value (kit_rtl script / asbuilt / prep_cmd / core_kit args ...),
    skipping free-text *note* fields; the wt-reaper follows these through scripts and bind manifests to the source
    worktrees they read (the S81 kit-RTL script -> die-s81-41/sbind -> wt/die-s81-41-bind chain, reaped 10-31 09:42)"""
    out = set()
    if "note" in key.lower():
        return out
    if isinstance(v, dict):
        for k, x in v.items():
            out |= _config_paths(x, str(k))
    elif isinstance(v, list):
        for x in v:
            out |= _config_paths(x, key)
    elif isinstance(v, str):
        out |= {m.rstrip("/.") for m in _ABS_PATH_RE.findall(v)}
    return out


def source_paths(cfg, st, ap_dir):
    """sorted absolute paths the wave reads: die configs + active/held kits and their pinned source specs,
    plus (FLOW-19) every other absolute path of a die config (kit_rtl script, asbuilt, prep_cmd, core_kit args)"""
    out = set()
    for d in (cfg.get("dies") or {}).values():
        for k in ("src", "plan", "queue_src"):
            if isinstance(d, dict) and isinstance(d.get(k), str) and d[k].startswith("/"):
                out.add(d[k])
        if isinstance(d, dict):
            out |= _config_paths(d)
    for rec in (st.get("items") or {}).values():
        active = (rec.get("status") in ("RUN", "RUNNING", "ROUTE-HELD") or
                  (rec.get("status") == "PASS" and rec.get("enqueue_pending")) or
                  (rec.get("status") == "ENQUEUED" and rec.get("q_status") not in ("SIGNED", "FAIL")))
        if not active or not rec.get("dir"):
            continue
        # A held/released kit and its pinned source survive config/source advancement.
        if isinstance(rec.get("kit"), str):
            kp = rec["kit"].split(":", 1)[-1]
            if kp.startswith("/"):
                out.add(kp)
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
              "evidence", "updated", "plan_current", "reason")


def current_blocks(cfg, st):
    """KW-FIX-35-K 11-08: {die: {item: block sha}} of the current plan of record (the cached probe and names that
    current_keys reads); a die without a cached probe is absent."""
    out = {}
    for die, d in ((cfg or {}).get("dies") or {}).items():
        if not isinstance(d, dict) or not d.get("plan") or not d.get("event"):
            continue
        p = (st.get("plans") or {}).get(f"{d.get('gen_host')}:{d['plan']}|{d['event']}")
        if p and p.get("blocks"):
            out[die] = dict(core_view_names(dict(p["blocks"]), p.get("core_views")))
    return out


def current_keys(cfg, st):
    """KIT-TRIAGE-1 11-01: item keys of the CURRENT plan of record per die (the keys select() would look up), from the
    cached plan probe (plan_names, raw block identity).  -> {die: set(keys)}; a die without a cached probe is absent
    (its rows stay plan_current '' = unknown).  419 FAIL rows on 11-01 04:0x were only ~142 on current blocks: the
    rest were superseded blocks/events that can never relaunch as such and were read as open failures."""
    out = {}
    for die, d in ((cfg or {}).get("dies") or {}).items():
        if not isinstance(d, dict) or not d.get("plan") or not d.get("event"):
            continue
        p = (st.get("plans") or {}).get(f"{d.get('gen_host')}:{d['plan']}|{d['event']}")
        if not p or not p.get("blocks"):
            continue
        names = core_view_names(dict(p["blocks"]), p.get("core_views"))
        out[die] = {item_key(die, d["event"], t, b) for t, b in names.items()}
    return out


def write_stages(st, ap_dir, cfg=None):
    """OWNER 12.20: one row per wave kit (keyed on plan block sha) for SIGNOFF-SPRINT-1's lanes/SIGNOFF-STAGES.tsv;
    ENQUEUED rows continue in the autopilot queue (route / sign-off / post-route LEC), joined on the kit path.
    plan_current (KIT-TRIAGE-1 11-01; reason stays the last column): yes = the row's key is an item of the die's current plan of record, no = a
    superseded block/event (history only: count burn-down on 'yes' rows; its FAIL reads status/class SUPERSEDED), '' = no
    cached plan probe for the die."""
    cur = current_keys(cfg, st)
    rows = ["\t".join(STAGE_COLS)]
    for r in sorted((st.get("items") or {}).values(), key=lambda r: (r.get("die", ""), r.get("item", ""))):
        v = dict(r, plan_sha=(r.get("plan_sha") or "")[:12], block_sha=(r.get("block_sha") or "")[:12],
                 plan_current=("" if r.get("die") not in cur else "yes" if item_key(
                     r.get("die"), r.get("event"), r.get("item"), r.get("block_sha")) in cur[r.get("die")] else "no"),
                 stage="queue:route" if r.get("status") == "ENQUEUED" else (r.get("stage") or ""),
                 updated=time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("updated") or 0)),
                 reason=(r.get("reason") or "")[:240])
        if is_wait_dep(r):
            v["status"] = "PENDING-DEP"
        if r.get("status") == "RUNNING" and r.get("disk_wait"):      # KW-FIX-38: admitted to nothing yet; behind a disk floor
            v["status"], v["reason"] = "WAIT-DISK", str(r["disk_wait"])[:240]
        if r.get("status") == "ENQUEUED" and r.get("q_stage"):
            # past GEOM: the autopilot queue job of this kit (follow_queue); evidence = its job id
            v.update(stage=r["q_stage"], status=r.get("q_status") or "", **{"class": r.get("q_class") or ""},
                     reason=(r.get("q_reason") or "")[:240],
                     evidence=f"autopilot job {r.get('q_id', '')} | {r.get('evidence') or ''}")
        if v["plan_current"] == "no" and v.get("status") == "FAIL":
            # KW-FIX-4/HBMRS 11-03 (DIE-HBM-61, COORD 17:1x): a FAIL on a superseded plan block can never relaunch
            # or count as such (its current block is another key), so the class burn-down skips it: SUPERSEDED here,
            # the wave record itself (attempts, two-strike history) is unchanged
            v.update(status="SUPERSEDED", **{"class": "SUPERSEDED"},
                     reason=f"superseded plan block (plan_current=no), was FAIL {v.get('class') or ''}: {v.get('reason') or ''}"[:240])
        if v.get("status") in ("FAIL", "SUPERSEDED", "PENDING-DEP") and r.get("item") in set(
                (((cfg or {}).get("dies") or {}).get(r.get("die")) or {}).get("counted_items") or []):
            # KW-RELAUNCH-1 11-05 (COORD 19:4x): die option counted_items = items already signed off and counted on
            # another path (lane build, OWNERS SIGNED); their old wave FAIL row reads SIGNED / COUNTED, not open work
            v.update(status="SIGNED", **{"class": "COUNTED"},
                     reason=f"counted elsewhere (counted_items), was {v.get('status')} {v.get('class') or ''}: {v.get('reason') or ''}"[:240])
        if isinstance(r.get("arm"), dict):               # KW-FIX-44 GRTARM_1111: the halving-off arm of the row
            v["reason"] = (f"GRT-ARM[{r['arm'].get('mode')}] " + str(v.get("reason") or ""))[:240]
        if r.get("provisional"):
            # KW-PROV-1: built on PROVISIONAL child views (never counted until the STA-only re-sign on the signed libs)
            pv = ",".join(f"{m}:{str(src).split()[0] if src else '?'}" for m, src in sorted(r["provisional"].items()))
            rs = (r.get("prov_resign") or {}).get("status")
            v["reason"] = (f"PROVISIONAL[{pv}]" + (f" resign:{rs}" if rs else "") + " " + str(v.get("reason") or ""))[:240]
        rows.append("\t".join(re.sub(r"\s+", " ", str(v.get(c) or "")) for c in STAGE_COLS))
    # KW-FIX-4 11-03: gen-time lint verdicts of the current plans (never launched, no build cost)
    for r in sorted((st.get("lint") or {}).values(), key=lambda r: (r.get("die", ""), r.get("item", ""))):
        v = dict(r, plan_sha=(r.get("plan_sha") or "")[:12], block_sha=(r.get("block_sha") or "")[:12], stage="prelint",
                 status="LINT-ADVISORY", plan_current="yes", **{"class": "LINT"},
                 updated=time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("updated") or 0)),
                 reason="; ".join(r.get("issues") or [])[:240])
        rows.append("\t".join(re.sub(r"\s+", " ", str(v.get(c) or "")) for c in STAGE_COLS))
    tmp = Path(ap_dir) / (STAGES_FILE + ".tmp")
    tmp.write_text("\n".join(rows) + "\n")
    tmp.replace(Path(ap_dir) / STAGES_FILE)


# ------------------------------------------------------------------------------------------------ reclassify
RESULT_ONLY_STAGES = ("geom", "cells", "geom_cfg", "geom_run", "unit", "pipeline")   # reason = the result line itself


def stored_fail_text(rec):
    """the text collect() classified (result.json errors + tail) + the whole stored stage log, so FAILs recorded
    before a rule existed (or before result.json carried 'errors') are re-read from the evidence the wave kept"""
    d = Path(rec.get("dir") or "")
    try:
        res = json.loads((d / "result.json").read_text())
    except (OSError, ValueError):
        res = {}
    stage = res.get("stage") or rec.get("stage") or ""
    if rec.get("stage") and res.get("stage") and res["stage"] != rec["stage"]:
        return rec["stage"], ""                       # the record's verdict came from elsewhere (recovery result)
    log = ""
    if stage not in RESULT_ONLY_STAGES:
        try:
            log = (d / f"{stage}.log").read_text(errors="replace")
        except OSError:
            log = ""
    text = (res.get("errors") or error_lines(log)) + "\n" + (res.get("tail") or "")
    return stage, text + ("\n" + log if log else "")


def reclassify(st, write=False, log=print):
    """recompute class/reason of every FAIL record from its stored logs with the current RULES; -> [(key, old, new)]
    (dry run unless write; status / attempt / stage never change)"""
    out = []
    for key, rec in sorted((st.get("items") or {}).items()):
        if rec.get("status") != "FAIL":
            continue
        stage, text = stored_fail_text(rec)
        if not text.strip():
            continue
        cls, why = classify(stage, text)
        old = (rec.get("class") or "", rec.get("reason") or "")
        if (cls, why) == old:
            continue
        out.append((key, old, (cls, why)))
        if write:
            rec.update(**{"class": cls}, reason=why, reclassified=now_s())
    return out


def _why(reason):
    """reason -> its rule text (before ' @<stage>')"""
    return re.split(r" @\w+", reason or "", maxsplit=1)[0][:90]


BIND_ADVISORY_RE = re.compile(r"S81_BIND_OUT=(\S+)")


def bind_out_of(kr, script_text=""):
    """The bind directory a wave's kit_rtl reads: kit_rtl.bind_out, or S81_BIND_OUT named in its script; else None."""
    kr = kr or {}
    if kr.get("bind_out"):
        return kr["bind_out"]
    m = BIND_ADVISORY_RE.search(script_text or "")
    return m.group(1) if m else None


def bind_advisory_cmd(src, plan, bind):
    """Shell for the gen host: the plan-dir files that differ between the bind's commit and src HEAD (read only)."""
    rel = f"$(realpath --relative-to={shlex.quote(src)} {shlex.quote(str(Path(plan).parent))})"
    py = "import json,sys; print(json.load(open(sys.argv[1]))['provenance']['commit'])"
    return (f"c=$(python3 -I -c {shlex.quote(py)} {shlex.quote(bind)}/provenance_bind.json) || {{ echo NOPROV; exit 0; }}; "
            f"git -C {shlex.quote(src)} cat-file -e $c^{{commit}} 2>/dev/null || {{ echo NOCOMMIT $c; exit 0; }}; "
            f"echo COMMIT $c; git -C {shlex.quote(src)} diff --name-only $c HEAD -- \"{rel}\" | grep -E '\\.json$' | head -8")


def bind_advisory_line(die, bind, src, out):
    """One advisory line (never a block) when a wave's bind_out is older than a plan or sidecar change in its src."""
    ls = [x.strip() for x in (out or "").splitlines() if x.strip()]
    if not ls or ls[0].startswith("NOPROV"):
        return f"  BIND-ADVISORY {die}: no provenance_bind.json in {bind}: not compared"
    if ls[0].startswith("NOCOMMIT"):
        return f"  BIND-ADVISORY {die}: bind commit {ls[0].split()[-1][:11]} of {bind} is not in {src}: not compared"
    if len(ls) > 1:
        return f"  BIND-ADVISORY {die}: bind_out {bind} ({ls[0].split()[-1][:11]}) is older than src {src} for: " + " ".join(ls[1:])
    return None


def bind_advisories(AP, cfg, res):
    """COORD 11-04: dry run prints a mismatch when src moved a plan or sidecar and bind_out did not move. No block."""
    out = []
    for die, ok, *_ in res:
        d = cfg["dies"].get(die) or {}
        kr, src, plan, gh = d.get("kit_rtl") or {}, d.get("src"), d.get("plan"), d.get("gen_host")
        if not (ok and src and plan and gh and kr):
            continue
        txt = ""
        if kr.get("script"):
            _, txt, _ = AP.sh(["ssh", "-o", "ControlPath=none", gh, "cat " + shlex.quote(kr["script"])], timeout=30)
        bind = bind_out_of(kr, txt)
        if not bind:
            continue
        _, o, _ = AP.sh(["ssh", "-o", "ControlPath=none", gh, bind_advisory_cmd(src, plan, bind)], timeout=60)
        line = bind_advisory_line(die, bind, src, o)
        if line:
            out.append(line)
    return out


def cmd_reclassify(a):
    import collections
    import fcntl
    ap_dir = Path(a.ap_dir or AP_DIR)
    lk = None
    if a.write:
        lk = open(ap_dir / "kit_wave.lock", "w")
        for _ in range(120):                          # wait for a running wave pass (never write under it)
            try:
                fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                time.sleep(5)
        else:
            print("reclassify: kit_wave.lock held for 10 min; nothing written")
            return 2
    try:
        st = load_state(ap_dir)
        ch = reclassify(st, write=a.write)
        hist = collections.Counter((o[0], _why(o[1]), n[0], _why(n[1])) for _k, o, n in ch)
        for k, o, n in ch:
            if not a.quiet:
                print(f"{k}\n    {o[0] or '-'}: {o[1][:200]}\n -> {n[0]}: {n[1][:300]}")
        print(f"# reclassify {now_s()} {'WRITE' if a.write else 'dry run'}: {len(ch)} of "
              f"{sum(1 for r in st.get('items', {}).values() if r.get('status') == 'FAIL')} FAIL records change")
        for (oc, ow, nc, nw), n in hist.most_common():
            print(f"{n:5d}  {oc or '-'}: {ow}  ->  {nc}: {nw}")
        if a.write and ch:
            save_state(st, ap_dir)
            write_stages(st, ap_dir)
        return 0
    finally:
        if lk:
            lk.close()


# ------------------------------------------------------------------------------------------------ re-judge GEOM
# KIT-TRIAGE-1/G7 11-01: FAIL@geom records were judged by the geom_verdict() of their day; the standing exceptions
# (STANDING_GEOM_EXCEPTIONS) and the core-kit outline fallback (GEOM-91, 952e12fdd77) came later.  rejudge-geom re-reads
# each stored auto_geom.json line (read-only), re-judges it with today's geom_verdict + die waivers and lists what now
# passes; --write releases the CURRENT-plan passes in one batch through enqueue_pass() (the path a fresh PASS takes).
PROBE_GEOM = r"""
import json, os, sys
a = json.loads(sys.argv[1]); out = {}
for k, ev, kit in a["items"]:
    r = {}
    try:
        d = json.load(open(ev))
        r["line"] = d.get("line", "")
        mt = d.get("metrics") or {}
        r["stage"] = mt.get("stage"); r["clk_fixed"] = mt.get("clock_islands_fixed")
    except Exception as e:
        r["error"] = f"{type(e).__name__}: {e}"
    r["kit_ok"] = bool(kit) and os.path.isdir(kit)
    for f in ("budget.json", "freeze.json"):
        p = os.path.join(kit or "", f)
        try:
            o = json.load(open(p)).get("outline_um") if os.path.isfile(p) else None
        except Exception:
            o = None
        if o:
            r["outline"] = [float(o[0]), float(o[1])]; r["outline_src"] = f
            break
    out[k] = r
print("AP_JSON " + json.dumps(out))
"""
OUTLINE_TOL = 0.01                                     # = geom_rules.OUTLINE_TOL


def outline_fill_in(line, outline, src="kit"):
    """an old line with outline=NA (kit outline not passed, GEOM-91) -> the outline rule geom_rules would have written
    with --outline (== slot within OUTLINE_TOL); unchanged when the line has no NA outline or no kit outline is known"""
    m = re.search(r"(?:^|\s)outline=NA\(([\d.]+)x([\d.]+)\)", line or "")
    if not m or not outline:
        return line, ""
    ok = abs(float(m.group(1)) - outline[0]) <= OUTLINE_TOL and abs(float(m.group(2)) - outline[1]) <= OUTLINE_TOL
    tok = m.group(0).replace("outline=NA(", "outline=ok(" if ok else "outline=FAIL(")
    return _relabel(line.replace(m.group(0), tok, 1)), f"outline {'ok' if ok else 'FAIL'} vs {src} {outline[0]:g}x{outline[1]:g}"


def prects_clock_info(line):
    """a 3_place clock_reach FAIL -> info (COORD 11-01 04:4x, = geom_rules: with 0 pre-placed clock cells the 3_place
    reach is port-to-farthest-flop only; the 4_cts gate is clock_leaf_reach).  rejudge_rows applies it only when the
    stored metrics say stage 'placed' and clock_islands_fixed == 0; 'whatif' keeps the unconditional reading"""
    if "3_place" not in (line or ""):
        return line
    return _relabel(re.sub(r"(^|\s)clock_reach=FAIL\(", r"\1clock_reach=info(", line))


def _relabel(line):
    """head 'AUTO-GEOM FAIL' -> PASS when an edited line has no FAIL / NA rule left (geom_rules verdict semantics)"""
    if re.search(r"(?:^|\s)[A-Za-z0-9_]+=(?:FAIL|NA)\(", line):
        return line
    return line.replace("AUTO-GEOM FAIL", "AUTO-GEOM PASS", 1)


def _plan_current(cfg, st, rec):
    """True / False = the record's key is / is not an item of its die's current plan of record (cached plan probe);
    None = no cached probe"""
    d = (cfg.get("dies") or {}).get(rec.get("die")) or {}
    p = (st.get("plans") or {}).get(f"{d.get('gen_host')}:{d.get('plan')}|{d.get('event')}")
    if not p or not p.get("blocks"):
        return None
    names = core_view_names(dict(p["blocks"]), p.get("core_views"))
    keys = {item_key(rec["die"], d["event"], t, b) for t, b in names.items()}
    return item_key(rec["die"], rec.get("event"), rec["item"], rec.get("block_sha")) in keys


def rejudge_rows(cfg, st, probe):
    """FAIL@geom (class PLAN) records -> rows {key, die, ia, current, old, new, failing, tag, note, kit_ok, whatif}.
    probe(host, [(key, auto_geom.json path, kit path)]) -> {key: {line, kit_ok, outline, outline_src | error}}"""
    recs = {k: r for k, r in (st.get("items") or {}).items()
            if r.get("status") == "FAIL" and r.get("stage") == "geom" and r.get("class") == "PLAN"}
    by_host = {}
    for k, r in recs.items():
        h, _, ev = (r.get("evidence") or "").partition(":")
        kit = (r.get("kit") or "").partition(":")[2]
        by_host.setdefault(h, []).append((k, ev, kit))
    got = {}
    for h, items in sorted(by_host.items()):
        p = probe(h, items) or {}
        if set(p) == {"error"}:                          # the whole host probe failed: say so on each row
            p = {k: {"error": f"{h}: {p['error']}"} for k, _, _ in items}
        got.update(p)
    rows = []
    for k, r in sorted(recs.items(), key=lambda kv: (kv[1].get("die", ""), kv[1].get("item", ""))):
        g = got.get(k) or {"error": "no probe result"}
        line = g.get("line") or ""
        row = dict(key=k, die=r["die"], ia=f"{r['item']}@{r.get('attempt')}", current=_plan_current(cfg, st, r),
                   kit_ok=bool(g.get("kit_ok")), error=g.get("error", ""), line=line)
        if not re.search(r"AUTO-GEOM (PASS|FAIL)\b", line):
            row.update(old="FAIL", new="FAIL", failing=[], tag="", note="no stored verdict line", whatif="FAIL")
            rows.append(row)
            continue
        w = geom_waivers((cfg.get("dies") or {}).get(r["die"]) or {}, r["item"], r.get("parent_item"))
        old = geom_verdict(line, w, standing=False)[0]   # today's die waivers, no standing class / outline fill-in
        line2, note = outline_fill_in(line, g.get("outline"), g.get("outline_src", "kit"))
        if g.get("stage") == "placed" and g.get("clk_fixed") == 0 and "clock_reach=FAIL(" in line2:
            line2 = prects_clock_info(line2)
            note = (note + "; " if note else "") + "clock_reach INFO (3_place, 0 fixed clock cells; COORD 11-01 04:4x)"
        adv = opt(cfg, r["die"], "geom_advisory") is not False
        v, failing, tag = geom_gate(line2, w, adv)
        row.update(old=old, new=v, failing=failing, tag=tag, note=note, line=line2,
                   whatif=geom_gate(prects_clock_info(line2), w, adv)[0])
        rows.append(row)
    return rows


def rejudge_geom(AP, cfg, st, ap_dir, write=False, include_old=False):
    """print the re-judge table; --write: release every CURRENT-plan record that now passes (kit present) through
    enqueue_pass() under kit_wave.lock, post one KIT-WAVE notice per die and save state + stages"""
    probe = lambda h, items: AP.rpy(h, PROBE_GEOM, {"items": items}, timeout=600)
    rows = rejudge_rows(cfg, st, probe)
    rel = [x for x in rows if x["new"] in ("PASS", "PASS-COND") and x["kit_ok"] and (x["current"] or include_old)]
    print(f"# KIT-WAVE rejudge-geom {now_s()}: {len(rows)} FAIL@geom PLAN records; now PASS/PASS-COND "
          f"{sum(x['new'] != 'FAIL' for x in rows)} (current plan {sum(x['new'] != 'FAIL' and bool(x['current']) for x in rows)}); "
          f"release set {len(rel)}; what-if pre-CTS clock_reach INFO: +{sum(x['whatif'] != 'FAIL' and x['new'] == 'FAIL' for x in rows)}")
    print("die\titem@attempt\tcurrent\tkit\told\tnew\twhatif\tfailing\ttag/note")
    for x in rows:
        print("\t".join([x["die"], x["ia"], {True: "yes", False: "no", None: "?"}[x["current"]],
                         "ok" if x["kit_ok"] else "MISSING", x["old"], x["new"], x["whatif"], ",".join(x["failing"]),
                         (x["tag"] + (" | " + x["note"] if x["note"] else "") + (" | " + x["error"] if x["error"] else ""))[:300]]))
    if not write:
        return rows
    import fcntl
    lk = open(Path(ap_dir) / "kit_wave.lock", "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("rejudge-geom --write: kit_wave.lock held by a wave pass; nothing written (rerun after the tick)")
        lk.close()
        return rows
    try:
        st = load_state(ap_dir)                          # fresh copy under the lock
        notices = {}
        rejudge_release(AP, cfg, st, rel, notices)
        for die, msgs in notices.items():
            lane = (cfg["dies"].get(die) or {}).get("owner_lane", f"{die} owner")
            AP.coord_append("lanes/COORD-REVIEW-QUEUE.md",
                            f"- {now_s()} KIT-WAVE [{die}] -> {lane}: rejudge-geom {len(msgs)} event(s): "
                            + "; ".join(msgs)[:1800])
        if not AP.DRY:
            save_state(st, ap_dir)
            write_stages(st, ap_dir, cfg)
    finally:
        lk.close()
    return rows


def rejudge_release(AP, cfg, st, rel, notices, log=print):
    """release the re-judged passes (rows of rejudge_rows) through enqueue_pass(); caller holds kit_wave.lock"""
    if True:
        for x in rel:
            rec = st["items"].get(x["key"])
            if not rec or rec.get("status") != "FAIL" or rec.get("stage") != "geom":
                continue                                 # changed since the dry read
            try:
                res = json.loads((Path(rec["dir"]) / "result.json").read_text())
            except (OSError, ValueError):
                res = {}
            rec.update(status="PASS", geom=x["line"][:600], cells=res.get("cells"),
                       geom_dir=res.get("geom_dir") or rec["evidence"].rsplit("/", 1)[0], geom_verdict=x["new"],
                       geom_tag=(x["tag"] + (f" [rejudge-geom {x['note']}]" if x["note"] else "")).strip(),
                       **{"class": ""}, reason=f"rejudge-geom {now_s()}: {x['new']} {x['tag']}"[:240],
                       updated=time.time())
            enqueue_pass(AP, cfg, st, rec, notices)
            log(f"released {x['die']}/{x['ia']}: {rec['status']} {rec.get('reason', '')[:160]}")


# ------------------------------------------------------------------------------------------------ queue-full (OWNER 11-01)
# OWNER 11-01 (COORD 05:3x): keep the queue full without a live agent.  Two tick-time mechanisms:
#  (1) auto_rejudge: when the wave code (kit_wave.py + geom_rules.py) changes on the hub, the next tick re-reads every
#      stored FAIL with the current RULES (reclassify) and re-judges every FAIL@geom with today's geom rules, releasing
#      the current-plan passes -- the one-time 'reclassify --write' / 'rejudge-geom --write' runs happen at merge.
#  (2) pending retries: lanes queue "item@attempt" retries that a fix unlocks in coord autopilot/kit_wave_pending.tsv
#      (sha, scope, die, item@attempt, lane, note); a row joins the die's retry set once its fix sha is merged
#      (scope hub: ancestor of the hub origin/main; scope src: ancestor of the die's src_sha).
PENDING_FILE = "autopilot/kit_wave_pending.tsv"
AUTO_REJUDGE_FILES = ("kit_wave.py", "geom_rules.py")


def wave_code_id():
    h = hashlib.sha1()
    for f in AUTO_REJUDGE_FILES:
        try:
            h.update((Path(__file__).resolve().parent / f).read_bytes())
        except OSError:
            h.update(f.encode())
    return h.hexdigest()[:12]


def auto_rejudge(AP, cfg, st, notices, log=None):
    """once per wave-code version: reclassify stored FAILs + re-judge FAIL@geom and release current-plan passes"""
    log = log or AP.log
    cid = wave_code_id()
    if st.get("auto_rejudge_code") == cid:
        return None
    try:
        ch = reclassify(st, write=True, log=lambda *_: None)
        probe = lambda h, items: AP.rpy(h, PROBE_GEOM, {"items": items}, timeout=600)
        rows = rejudge_rows(cfg, st, probe)
        rel = [x for x in rows if x["new"] in ("PASS", "PASS-COND") and x["kit_ok"] and x["current"]]
        rejudge_release(AP, cfg, st, rel, notices, log=log)
    except Exception as e:                               # never block the wave on it; retried next tick
        log(f"KIT-WAVE auto-rejudge {cid} failed: {type(e).__name__}: {e}")
        return None
    st["auto_rejudge_code"] = cid
    log(f"KIT-WAVE auto-rejudge {cid}: reclassified {len(ch)}, geom re-judged {len(rows)}, released {len(rel)}")
    return len(ch), len(rows), len(rel)


# ------------------------------------------------------------------------------------------------ KW-FIX-23 RETRY-EPOCH
# COORD 11-06 11:4x (KW-FIX-23): a die's retry list holds plain "item@N" strings with no source or time, so an old
# entry fired again whenever a NEW attempt reached N (S81 ot_s81sl_leaf__t50: stale @2..@5 entries from 11-03/04
# relaunched a4/a5/a6 every tick).  Rule: a retry entry releases attempt N only when attempt N was launched BEFORE the
# entry was first seen by the scheduler (st["retry_seen"]); an entry that names an attempt launched later is stale and
# is dropped from this tick's in-memory retry set (kit_wave.json is never written).  Entries added in-tick (pending
# rows, LEAFSLEW) and COORD releases of an already failed / running attempt keep working unchanged.
# KW-FIX-33 (COORD 11-07 22:53): the first-seen key carries the die's event ("<die>|<event>|<item>@<N>"; retry_seen_key).
# Without it a COORD release of item@N on a NEW event inherited the first-seen time of the same string on an older event,
# and the new event's attempt N (launched after that) dropped it as stale (S81 ot_s81sl_leaf__t12@2/@3, 11-07 21:56).
# One-time migration: a legacy "<die>|<item>@<N>" time moves to the CURRENT event's key (and the legacy key is removed),
# so the rollout re-arms nothing; a later event change starts its entries fresh.  retry_stale_logged uses the same keys.
def retry_seen_key(die, event, ia):
    return f"{die}|{event}|{ia}" if event else f"{die}|{ia}"


def _retry_key_migrate(tab, die, event, ia):
    """-> the event key of die/ia in tab (retry_seen / retry_stale_logged), moving a legacy key's value onto it once"""
    k = retry_seen_key(die, event, ia)
    legacy = f"{die}|{ia}"
    if k != legacy and k not in tab and legacy in tab:
        tab[k] = tab.pop(legacy)
    return k


def prune_stale_retries(cfg, st, notices=None, log=None, now=None):
    # KW-FIX-23 14:0x hot-fix: epoch seconds on both sides (now_s() is a display string; 13:57 TypeError)
    now = time.time() if now is None else float(now)
    seen = st.setdefault("retry_seen", {})
    latest = {}
    for rec in (st.get("items") or {}).values():
        k = (rec.get("die"), rec.get("item"), str(rec.get("attempt")))
        try:
            t = float(rec.get("started") or 0)
        except (TypeError, ValueError):
            continue
        latest[k] = max(latest.get(k, 0.0), t)
    dropped = {}
    # KW-FIX-45 11-11 (su_l0 @2 and the HBM pilot stayed stale after remove + re-add): a retry entry that is ABSENT from the
    # config at this pass loses its first-seen record, so re-adding it later is a fresh release (the documented re-arm).
    # Limited to dies that still carry a retry list, so an empty/unsynced list of a die never wipes anything.
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or not d.get("retry"):
            continue
        ev = d.get("event") or ""
        present = {retry_seen_key(die, ev, ia) for ia in d["retry"]}
        pre = f"{die}|{ev}|" if ev else f"{die}|"
        for tab in (seen, st.setdefault("retry_stale_logged", {})):
            for k in [k for k in tab if k.startswith(pre) and k not in present]:
                del tab[k]
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or not d.get("retry"):
            continue
        keep = []
        ev = d.get("event") or ""
        for ia in d["retry"]:
            sk = _retry_key_migrate(seen, die, ev, ia)
            try:
                first = float(seen.setdefault(sk, now))
            except (TypeError, ValueError):
                first = seen[sk] = now      # unparsable (old string) -> first seen now
            item, _, n = str(ia).rpartition("@")
            started = latest.get((die, item, n), 0.0)
            if started and started > first:
                dropped.setdefault(die, []).append(ia)
                continue
            keep.append(ia)
        d["retry"] = keep
    logged = st.setdefault("retry_stale_logged", {})
    for die, xs in dropped.items():
        ev = ((cfg.get("dies") or {}).get(die) or {}).get("event") or ""
        new = [x for x in xs if _retry_key_migrate(logged, die, ev, x) not in logged]
        for x in new:
            logged[retry_seen_key(die, ev, x)] = now
        if new and log:
            log(f"KIT-WAVE retry stale {die}: {len(new)} entries name an attempt launched after the entry "
                f"(KW-FIX-23 retry epoch; not released): {' '.join(new[:12])}")
    return dropped


def parse_pending(text):
    out = []
    for ln in (text or "").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) < 4 or not re.fullmatch(r"[0-9a-f]{7,40}", f[0].strip()) or f[1].strip() not in ("hub", "src") \
                or not re.fullmatch(r"[^@\s]+@\d+", f[3].strip()):
            continue
        out.append(dict(sha=f[0].strip(), scope=f[1].strip(), die=f[2].strip(), retry=f[3].strip(),
                        lane=(f[4].strip() if len(f) > 4 else ""), note=(f[5].strip() if len(f) > 5 else "")))
    return out


def release_pending(cfg, st, rows, merged, notices):
    """merged(sha, scope, die) -> bool.  Adds each merged row's item@attempt to the die's in-memory retry set
    (kit_wave.json is never written); a first release posts one notice per die."""
    seen = st.setdefault("pending_released", {})
    for r in rows:
        d = (cfg.get("dies") or {}).get(r["die"])
        if not d:
            continue
        k = f"{r['sha']}|{r['scope']}|{r['die']}|{r['retry']}"
        if k not in seen:
            if not merged(r["sha"], r["scope"], r["die"]):
                continue
            seen[k] = now_s()
            notices.setdefault(r["die"], []).append(f"{r['retry']} retry released (fix {r['sha']} merged, {r['lane']})")
        rt = d.setdefault("retry", [])
        if r["retry"] not in rt:
            rt.append(r["retry"])


# ------------------------------------------------------------------------------------------------ KW-FIX-17 LEAFSLEW
# COORD 11-05 16:4x (KW-FIX-17): HBM-CTS-LEAFSLEW is a default-on class fix.  Signature: the routed TT sign-off sta.log
# lists max_slew violations on clock-tree cell pins (clkbuf_*/A, ot_dtap*_iso/A, CTS inverters / delay buffers, ...) or
# register clock pins -- 320-563 ps on ~8 HBM + 3-4 S81 failing designs, 0 of 110 signed runs.  Such a queue FAIL
# releases its item@attempt once per item and source sha (in-memory retry + retry_fix, like kit_wave_pending.tsv),
# and the next attempt's kit carries physical/common_flow/clk_leaf_repeat.tcl as POST_CTS_TCL (the kit's own
# POST_CTS_TCL hook still runs after it via OT_CLR_NEXT_TCL).  An attempt built with the hook never auto-releases.
LEAFSLEW_NOTE = "LEAFSLEW class (KW-FIX-17, COORD 16:4x): clk_leaf_repeat post-CTS hook"
LEAFSLEW_TCL = "clk_leaf_repeat.tcl"
LEAFSLEW_CLK_INST = re.compile(r"^(clkbuf|clkload|clkleafrep|clkinv|delaybuf|cts|ot_dtap|.*_tb\d+_d\d+)", re.I)
LEAFSLEW_CLK_PINS = ("CLK", "CK")
LEAFSLEW_TRIES = 3                                         # unreadable sign-off log: give up (no trigger) after this
LEAF_OPTOUT_RE = r"^[[:space:]]*(override[[:space:]]+)?(export[[:space:]]+)?OT_CLK_LEAF_REPEAT[[:space:]]*[:?]?=[[:space:]]*0[[:space:]]*(#.*)?$"
LEAFSLEW_READS_PER_TICK = 24                               # newest queue FAILs first; the rest are read next tick


def leafslew_parse(text):
    """sta.log text (or its grep of 'Pin .. Limit' headers + VIOLATED rows) -> {pins, worst_ps, worst_pin}: max_slew
    VIOLATED rows on clock-tree cell pins or register clock pins.  Rows under a max capacitance / fanout table never
    count (their header names no Slew)."""
    inslew = False
    pins, worst, wpin = 0, 0.0, ""
    for ln in (text or "").splitlines():
        s = ln.strip()
        if s.startswith("Pin") and "Limit" in s:
            inslew = "Slew" in s
            continue
        if not inslew or "VIOLATED" not in s:
            continue
        m = re.match(r"^(\S+)\s+([\d.]+)\s+([\d.]+)\s+(-[\d.]+)\s+\(VIOLATED\)", s)
        if not m:
            continue
        pin = m.group(1)
        inst, _, pn = pin.rpartition("/")
        leaf = re.split(r"(?<!\\)[/.]", inst)[-1] if inst else ""
        if pn in LEAFSLEW_CLK_PINS or (leaf and LEAFSLEW_CLK_INST.match(leaf)):
            pins += 1
            if float(m.group(3)) > worst:
                worst, wpin = float(m.group(3)), pin
    return {"pins": pins, "worst_ps": round(worst, 2), "worst_pin": wpin}


def leafslew_read(AP, rec, hub):
    """-> signature dict, or None when no host could read the TT sta.log (fail-soft: never a trigger)"""
    tt = os.path.join(os.path.dirname(rec["q_signoff"]), "tt", "sta.log")
    # KW-FIX-25 (COORD 22:1x (5)): a kit whose plan owns the clock tree sets OT_CLK_LEAF_REPEAT=0, so the hook would do nothing
    cm = os.path.join(os.path.dirname(os.path.dirname(rec["q_signoff"])), "config.mk")
    cmd = (f"if test -r {shlex.quote(tt)}; then grep -E '^Pin .*Limit|VIOLATED' {shlex.quote(tt)} | head -n 200000; "
           f"grep -Eqs {shlex.quote(LEAF_OPTOUT_RE)} {shlex.quote(cm)} && echo KW_LEAF_OPTOUT; "
           f"echo KW_LEAFSLEW_READ; else echo KW_LEAFSLEW_NOLOG; fi")
    for h in rec.get("q_hosts") or [hub]:
        h = hub if h == "localhost" else h
        argv = _ssh(h, hub) + ["bash -c " + shlex.quote(cmd)] if _ssh(h, hub) else ["bash", "-c", cmd]
        try:
            rc, out, _ = AP.sh(argv, timeout=60)
        except Exception:
            continue
        if rc == 0 and "KW_LEAFSLEW_READ" in (out or ""):
            return dict(leafslew_parse(out), log=f"{h}:{tt}", leaf_optout="KW_LEAF_OPTOUT" in out)
    return None


def leafslew_plan_route(rec, status, cls, why):
    """KW-FIX-25: -> (class, reason) of a queue row; a slew FAIL on a plan-owned clock tree stays a PLAN fail on every re-read"""
    if status == "FAIL" and (rec.get("leafslew") or {}).get("route") == "PLAN":
        return "PLAN", "plan fix: clock slew on a plan-owned tree, no LEAFSLEW retry: " + str(why or "")
    return cls, why


def leafslew_step(AP, cfg, st, notices, hub=None):
    """judge each new queue FAIL once for the LEAFSLEW signature; keep released attempts in the die's in-memory retry
    set until the hooked attempt launches (launch() reads st['leafslew'])"""
    hub = hub or getattr(AP, "HUB_NAME", "localhost")
    ls = st.setdefault("leafslew", {})
    todo = [rec for rec in (st.get("items") or {}).values()
            if rec.get("status") == "ENQUEUED" and rec.get("q_status") == "FAIL" and rec.get("q_signoff")
            and "leafslew" not in rec and rec.get("die") in (cfg.get("dies") or {}) and not rec.get("arm")
            and opt(cfg, rec.get("die"), "leafslew_auto") is not False]
    todo.sort(key=lambda r: -float(r.get("q_updated") or r.get("updated") or 0))
    for rec in todo[:LEAFSLEW_READS_PER_TICK]:
        die = rec["die"]
        sig = leafslew_read(AP, rec, hub)
        if sig is None:
            rec["leafslew_tries"] = int(rec.get("leafslew_tries") or 0) + 1
            if rec["leafslew_tries"] >= LEAFSLEW_TRIES:
                rec["leafslew"] = {"pins": 0, "error": "TT sta.log unreadable"}
            continue
        rec["leafslew"] = sig
        if not sig["pins"] or rec.get("leafslew_form"):
            continue                                     # no signature, or the hooked attempt itself failed: no loop
        if sig.get("leaf_optout"):                       # KW-FIX-25: no retry, the plan owns this tree: goes to a plan fix
            sig["route"] = "PLAN"
            rec["q_class"], rec["q_reason"] = leafslew_plan_route(rec, "FAIL", rec.get("q_class"), rec.get("q_reason"))
            notices.setdefault(die, []).append(
                f"{rec['item']}@{rec.get('attempt')} clock slew on a plan-owned tree ({sig['pins']} clock pins over max_slew, worst "
                f"{sig['worst_ps']:.0f} ps {sig['worst_pin']}), OT_CLK_LEAF_REPEAT=0: no LEAFSLEW retry, PLAN FIX needed (KW-FIX-25)")
            if hasattr(AP, "log"):
                AP.log(f"KIT-WAVE LEAFSLEW plan-owned {die}/{rec['item']}@{rec.get('attempt')}: no retry, plan fix: {sig}")
            continue
        src = rec_src_sha(rec)
        k = f"{die}|{rec['item']}|{src}"
        if k in ls:
            continue
        ls[k] = dict(die=die, item=rec["item"], src_sha=src, attempt=rec.get("attempt"), pins=sig["pins"],
                     worst_ps=sig["worst_ps"], worst_pin=sig["worst_pin"], log=sig.get("log", ""),
                     q_id=rec.get("q_id"), released=now_s(), hooked_attempt=None)
        notices.setdefault(die, []).append(
            f"{rec['item']}@{rec.get('attempt')} LEAFSLEW signature ({sig['pins']} clock pins over max_slew, worst "
            f"{sig['worst_ps']:.0f} ps {sig['worst_pin']}) -> auto retry with the clk_leaf_repeat hook (KW-FIX-17)")
        if hasattr(AP, "log"):
            AP.log(f"KIT-WAVE LEAFSLEW {die}/{rec['item']}@{rec.get('attempt')}: {sig}")
    for e in ls.values():
        d = (cfg.get("dies") or {}).get(e.get("die"))
        if not isinstance(d, dict) or e.get("hooked_attempt") or opt(cfg, e["die"], "leafslew_auto") is False:
            continue
        ia = f"{e['item']}@{e['attempt']}"
        rt = d.setdefault("retry", [])
        if ia not in rt:
            rt.append(ia)
        if d.get("retry_fix") is None:
            d["retry_fix"] = {}
        if isinstance(d["retry_fix"], dict):
            d["retry_fix"].setdefault(ia, LEAFSLEW_NOTE)


def leafslew_launch(cfg, st, die, item, prev, attempt):
    """-> (released entry key or None, LEAFSLEW form for a new attempt of die/item or None).  A released entry (once
    per source sha) is claimed by the attempt that launches (launch() sets hooked_attempt once the unit is on record);
    an item built with the hook keeps it on every later attempt (the class is proven for it)."""
    if opt(cfg, die, "leafslew_auto") is False:
        return None, None
    env = leafslew_item_env(cfg, die, item)
    def with_env(form):
        # COORD 11-05 17:4x: a die's leafslew_items rule (e.g. S81 slice_station: branch rule) rides on every form
        return dict(form, env=env) if env else form
    for k, e in (st.get("leafslew") or {}).items():
        if e.get("die") == die and e.get("item") == item and not e.get("hooked_attempt") \
                and int(e.get("attempt") or 0) < attempt:
            return k, with_env({x: e.get(x) for x in ("attempt", "pins", "worst_ps", "worst_pin", "log", "q_id", "src_sha")})
    if (prev or {}).get("leafslew_form"):
        return None, with_env({x: v for x, v in prev["leafslew_form"].items() if x != "env"} | {"carried_from": prev.get("attempt")})
    if env is not None:
        return None, {"by": "leafslew_items", "env": env}
    return None, None


def leafslew_item_env(cfg, die, item):
    """KW-FIX-17 11-05 (COORD 17:4x, S81 slice_station cross-tap hold): die option leafslew_items {glob: {OT_CLK_LEAF_*:
    value}} builds every matching item with the clk_leaf_repeat hook and those settings (no signature needed); the first
    matching glob wins.  -> env dict ({} = hook with the tool defaults) or None (no match).  Values validated as item_env."""
    for g, env in (opt(cfg, die, "leafslew_items") or {}).items():
        if fnmatch.fnmatchcase(item, g):
            env = dict(env or {})
            for k, v in env.items():
                if not re.fullmatch(r"OT_CLK_LEAF_[A-Z0-9_]+", str(k)) or not ENV_VAL_RE.fullmatch(str(v)):
                    raise ValueError(f"leafslew_items {g}: {k}={v!r} (OT_CLK_LEAF_* names, [A-Za-z0-9_.,:=+-] values)")
            return {str(k): str(v) for k, v in sorted(env.items())}
    return None


def leafslew_patch_cmd(K, form):
    """remote shell: chain clk_leaf_repeat.tcl ahead of the kit's POST_CTS_TCL in K/config.mk (idempotent; a kit that
    already names the hook is left as is) and write K/LEAFSLEW_FORM.json"""
    q = shlex.quote
    block = ("\n# KW-FIX-17 LEAFSLEW (COORD 11-05 16:4x): clk_leaf_repeat post-CTS hook; the kit's own POST_CTS_TCL runs "
             "after it\nexport OT_CLR_NEXT_TCL := $(POST_CTS_TCL)\noverride export POST_CTS_TCL = /work/"
             + LEAFSLEW_TCL + "\n"
             + "".join(f"export {k} = {v}\n" for k, v in sorted((form.get("env") or {}).items())
                       if re.fullmatch(r"OT_CLK_LEAF_[A-Z0-9_]+", k) and ENV_VAL_RE.fullmatch(str(v))))
    meta = json.dumps(dict(schema="opentallas.kw_leafslew_form.v1", lane="KW-FIX-17", note=LEAFSLEW_NOTE,
                           trigger=form), sort_keys=True)
    return (f"cd {q(K)} && test -f config.mk && test -s {LEAFSLEW_TCL} && "
            f"if grep -q 'KW-FIX-17 LEAFSLEW' config.mk; then echo KW_LEAFSLEW already patched; "
            f"elif grep -v '^[[:space:]]*#' config.mk | grep -q 'clk_leaf_repeat'; then echo KW_LEAFSLEW kit already hooked; "
            f"else printf %s {q(block)} >> config.mk && echo KW_LEAFSLEW patched; fi && "
            f"printf '%s\\n' {q(meta)} > LEAFSLEW_FORM.json")


def _merged(AP, cfg):
    cache = {}
    def f(sha, scope, die):
        tip = "origin/main" if scope == "hub" else ((cfg.get("dies") or {}).get(die) or {}).get("src_sha") or ""
        if not tip:
            return False
        if (sha, tip) not in cache:
            rc, _, _ = AP.sh(["git", "-C", str(AP.REPO), "merge-base", "--is-ancestor", sha, tip], timeout=60)
            cache[(sha, tip)] = rc == 0
        return cache[(sha, tip)]
    return f


# ------------------------------------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--config")
    p.add_argument("--owners")
    p.add_argument("--probe", action="store_true", help="read the plan of record on gen_host (ssh) to filter items")
    sub.add_parser("status")
    un = sub.add_parser("unchanged", help="dry run of hold_unchanged: FAIL rows a relaunch would build on the same inputs")
    un.add_argument("--config")
    un.add_argument("--out", help="write the TSV here instead of only counting")
    s_ = sub.add_parser("step", help="one wave pass outside the autopilot tick (canary; AP_DIR names its state dir)")
    s_.add_argument("--config", help="kit_wave.json file instead of coord/state autopilot/kit_wave.json")
    s_.add_argument("--owners", help="OWNERS.tsv to select from (default AP_DIR/OWNERS.tsv)")
    s_.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("run-item")
    r.add_argument("spec")
    rc_ = sub.add_parser("reclassify", help="recompute class/reason of FAIL records from their stored stage logs "
                                            "with the current RULES (dry run unless --write)")
    rc_.add_argument("--write", action="store_true", help="update the state + kit_wave_stages.tsv (under kit_wave.lock)")
    rc_.add_argument("--ap-dir", help="state dir (default AP_DIR)")
    rc_.add_argument("--quiet", action="store_true", help="histogram only")
    rd_ = sub.add_parser("reap-dead", help="KW-FIX-46: dry-run list of rows the REAP-DEAD sweep would reap (read-only)")
    rd_.add_argument("--config", help="kit_wave.json file instead of coord/state autopilot/kit_wave.json")
    rd_.add_argument("--minutes", type=float, default=REAP_DEAD_MIN)
    rj = sub.add_parser("rejudge-geom", help="re-judge stored FAIL@geom verdicts with today's geom_verdict (read-only "
                        "unless --write, which releases the current-plan passes through enqueue_pass in one batch)")
    rj.add_argument("--config", help="kit_wave.json file instead of coord/state autopilot/kit_wave.json")
    rj.add_argument("--write", action="store_true")
    rj.add_argument("--include-old", action="store_true", help="also release records on superseded plan blocks")
    pr_ = sub.add_parser("prov-resign", help="KW-PROV-1 worker: STA-only re-sign of a PROVISIONAL kit on signed child views")
    pr_.add_argument("spec")
    pc_ = sub.add_parser("prov-census", help="KW-PROV-1: per die, WAIT-DEP types launchable on a routed child abstract "
                         "vs a plan-contract abstract (read-only)")
    pc_.add_argument("--config", help="kit_wave.json file instead of coord/state autopilot/kit_wave.json")
    pc_.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "prov-resign":
        return prov_resign_run(a.spec)
    if a.cmd == "reclassify":
        return cmd_reclassify(a)
    if a.cmd == "run-item":
        try:
            return run_item(a.spec)
        except Exception as e:                          # a crash of the pipeline itself is FLOW, recorded
            out = Path(a.spec).parent / "result.json"
            out.write_text(json.dumps({"verdict": "FAIL", "stage": "pipeline", "tail": f"Traceback (most recent call "
                                       f"last) {type(e).__name__}: {e}"}))
            raise
    if a.cmd == "unchanged":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import autopilot as AP
        cfg = load_config(Path(a.config).read_text() if a.config else AP.read_coord("autopilot/kit_wave.json"))
        cfg["_hub"] = AP.HUB_NAME
        rows = redesign_rows(cfg, load_state())
        import collections as _c
        print("unchanged design FAIL rows", len(rows), "released (would relaunch without the hold)",
              sum(x["released"] == "yes" for x in rows))
        print(sorted(_c.Counter((x["die"], x["released"]) for x in rows).items()))
        if a.out:
            cols = ["die", "item", "attempt", "cls", "stage", "released", "reason"]
            Path(a.out).write_text("\n".join(["\t".join(cols)] + ["\t".join(str(x[c]) for c in cols) for x in rows]) + "\n")
        return 0
    if a.cmd == "status":
        st = load_state()
        for k, rec in sorted(st.get("items", {}).items()):
            print(f"{rec.get('status', ''):<12} {rec.get('class', ''):<6} {k:<60} {rec.get('stage', '')} {rec.get('unit', '')} "
                  f"{(rec.get('reason') or rec.get('evidence') or '')[:120]}")
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import autopilot as AP
    if a.cmd == "reap-dead":
        AP.DRY = True
        cfg = load_config(Path(a.config).read_text() if a.config else AP.read_coord("autopilot/kit_wave.json"))
        rows = reap_dead_scan(AP, cfg, load_state(), minutes=a.minutes)
        import collections as _c
        for key, kind, why in rows:
            print(f"{kind}\t{key}\t{why}")
        print("# reap-dead dry run:", len(rows), sorted(_c.Counter((k.split("|")[0], kd) for k, kd, _ in rows).items()))
        return 0
    if a.cmd == "rejudge-geom":
        AP.DRY = not a.write
        cfg = load_config(Path(a.config).read_text() if a.config else AP.read_coord("autopilot/kit_wave.json"))
        rejudge_geom(AP, cfg, load_state(), AP_DIR, write=a.write, include_old=a.include_old)
        return 0
    if a.cmd == "prov-census":
        AP.DRY = True
        cfg = load_config(Path(a.config).read_text() if a.config else AP.read_coord("autopilot/kit_wave.json"))
        print(json.dumps(prov_census(AP, cfg, load_state()), indent=1) if a.json else "\n".join(
            f"{die}: {r.get('error') or ''}WAIT-DEP types {r.get('types', 0)} -> routed child abstract {r.get('routed', 0)}, "
            f"plan-contract abstract {r.get('contract', 0)} (children {r.get('children', 0)}, routed {r.get('children_routed', 0)})"
            for die, r in prov_census(AP, cfg, load_state()).items()))
        return 0
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
    merge_auto_views(cfg, AP_DIR)                # KW-FIX-35-CV: the plan reads the views the pass reads
    owners = parse_owners(Path(a.owners or AP_DIR / "OWNERS.tsv").read_text())
    rc, out, _ = AP.sh([OT_RUN, "--status"], timeout=120)
    status = parse_otrun_status(out if rc == 0 else "")
    st = load_state()
    st.setdefault("items", {})
    prune_stale_retries(cfg, st)                 # KW-FIX-28: as the real pass does, or plan lists rows the pass never takes
    res, todo = plan_dies(AP, cfg, st, owners, status, AP.HUB_NAME, probe=a.probe)
    print(f"# KIT-WAVE plan {now_s()} (dry run; nothing launched) hosts: " +
          ", ".join(f"{h} admits {v['admit']} GB run {v['run']}" for h, v in status.items()))
    for die, ok, why, picks, skip in res:
        print(f"{die}: {'ON' if ok else 'OFF'} -- {why}")
        if ok:
            print(f"  eligible {len(picks)}: " + " ".join(f"{p['item']}({p['kind']},x{p['replicas']})" for p in picks[:40]))
            for w, its in sorted(skip.items(), key=lambda kv: -len(kv[1])):
                print(f"  skip {len(its)} [{w}]: " + " ".join(its[:12]) + (" ..." if len(its) > 12 else ""))
    for line in bind_advisories(AP, cfg, res):
        print(line)
    print(f"would launch now ({len(todo)}): " + " ".join(f"{d}/{r['item']}" for d, r in todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
