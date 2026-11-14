# WAVE-FRICTION-1 (Sonnet) handoff, 2026-11-14

Live files (backups `*.bak-wf1-1114` beside each): rt/tools/autopilot/kit_wave.py, autopilot.py, rt/tools/die_plan/eco_loop.py, autopilot/test_kit_wave.py
(rt = /srv/opentallas-scratch2/claude/kw38/rt on intel2). Branch: claude/wave-friction-1-1114 off origin/main (READY to ROOT-MERGE-63).

Deployed (picked up on the next tick):
- #2 AUTO RE-ARM: minimal_auto_retry adds item@attempt for every FAIL / queue-FAIL / CANCELLED-HUNG / CANCELLED-WAIT-FORM row whose attempt spec.json src_sha, src_overlay or host list (a host ADDED) differs from now, or whose kit-tools digest (tools/die_plan, physical/common_flow, tools/autopilot/kit_*.py except kit_wave.py) changed since the first tick after that failure. kit_resume 'nochange', hold_items, plan block, RETRY_CAP still apply. Die option auto_rearm:false turns it off. Log: one KW_REARM line per die and change.
  INFRA: new RULES: ot-run interrupted signal 15 / cancellation requested / stopped by operator / disk floor (any stage); Python exception or 'plan invalid' at kit_rtl/gen not named PLAN/RTL (last rule). fail_signature: INFRA is never counted by RETRY_CAP. Dry check (kit_wave plan --probe, eligible rows before -> after): qc 15->33, kv 1->5, s81 27->45, head 1->4, hbm 0->0.
- #R RETRY_CAP stays 3 (COORD correction). New input_digest(cfg, die) (plan sha, src_sha, src overlay, kit tools digest, gen_env, kit_rtl, event) + the item's plan block are stored with each failure signature; when either differs the count restarts at 0 (blocked_why pops the entry). Older counts are stamped at first check.
- #7 take_states default ["*"] = every OWNERS state except RETIRED (explicit lists still narrow); only_items "plan" (string) or only_items_from_plan:true = no hand list (plan items minus hold_items); GATE_KEYS = (bind, clock): g0c dropped. JSON side (replace die take_states / only_items lists) is KIT-OPS-3's.
- #9 eco_loop.py: minimal_hold_only(rec) (signoff_profile.judge: drc and setup_tt PASS, hold_ff FAIL) -> eligible() and near_miss() accept with no 30 ps / 100 endpoint window; passes() skips the TT pass for it. Checked on the kv3_phy_v1 attempt_2 record (TT -34.25, FF -204 / 297 ep): old NOT_NEAR_MISS 'setup WNS -34.25', new eligible, pass b5. S81 slice_station t36/t37/t43/t49 records are on epyc4 (host key changed, unreachable); the same judge applies (TT +47..+97, FF -72..-114, DRC 0 in state.json).
- #H hung watchdog: busy CPU = growth > 5 % of one core over the window (was flat 60 CPU-s); cancel only with log frozen >= hung_watch_min AND not busy; at 360 min frozen-but-busy: one NO-PROGRESS-6H notice (rec.hung_posted), no cancel.
- #4 tick phase timing added (TICK-TIMES line in log.txt); baseline wall 14-16 min (CPU 10-11 min).

Tests: test_kit_wave / allowlist / class_retry / no_row_source keep the same pass/fail set as the unmodified code (pre-existing: 1 fail + 5 errors + class_retry 1 fail); 2 expectations updated (gen Traceback now INFRA; take_states * picks KIT-PLACED rows).

## Diff
```diff
--- a/kit_wave.py	2026-11-14 00:34:04.640062503 -0800
+++ b/kit_wave.py	2026-11-14 00:48:41.981969662 -0800
@@ -166,12 +166,14 @@
                "s81_head": {"exact": ("src25p", "src25q2", "src25q3", "l44", "l45", "l46", "l47", "l47k", "l47t",
                                       "l48w", "l48x", "l48y", "l48z", "l48h0", "l48h1", "l48rf", "l48tb", "l48rc", "l48tc", "l48sd", "l48se", "l48sf", "l48sg", "l48ua", "l48ub", "l48uc", "l48ud", "l48ue", "l48uf", "l48ug", "l48uh", "l48ui", "l48uj")}}
 COORD_ONLY = ("qwen_compute", "hbm")          # OFF until COORD enables them (coord_enable = ruling reference)
-GATE_KEYS = ("g0c", "bind", "clock")          # plan event checks that must be PASS (12.4a / 12.17 freeze inputs)
+# WF-1 11-14 (OWNER friction removal; EXPERT-REVIEW-6 #7): g0c (a hand-written gate.g0c evidence string per event) is dropped; the
+# bind gate stays.  A config that still carries gate.g0c is ignored for it.
+GATE_KEYS = ("bind", "clock")                 # plan event checks that must be PASS (12.4a / 12.17 freeze inputs)
 # SAFE-STATION-1 11-03 (OWNER TWO-STRIKES): wire-only station types take the relay-bay form (tools/die_plan/relay_bay.py)
 # right after gen: a registered relay at every <=300-um hop, extra cycles declared, per-hop table >= +10% of the period
 # or FAIL_PREBUILD before route.  Class default ON; a die opts out with "relay_bay_re": "".
 RELAY_BAY_RE = {"s81": r"^slice_station__", "qwen_compute": r"^sl[ew]_(?:stm|fw|fe)_v\d"}
-DEFAULTS = {"max_inflight": 40, "max_launch_per_tick": 6, "die_max_inflight": 6, "take_states": ["NEEDS-KIT"],
+DEFAULTS = {"max_inflight": 40, "max_launch_per_tick": 6, "die_max_inflight": 6, "take_states": ["*"],
             "kinds": ["type"], "live_claim_h": 3.0, "place_mem_gb": 48, "place_threads": 8, "geom_mem_gb": 24, "geom_grt_wall_s": 1800,
             "gen_mem_gb": 16, "bind_mem_gb": 24, "lint_mem_gb": 8, "geom_sample": 5, "place_prefer": [], "hosts": ["intel1", "intel2", "epyc2", "epyc4"],
             "work_root": "/srv/opentallas-scratch2/claude/kit-wave", "infra_attempts": 3, "launch_stagger_s": 6,
@@ -445,7 +447,7 @@
 MINIMAL_RETRY = "minimal_retry"       # state ledger {die|item: failed attempt that got the one automatic retry}
 
 
-def minimal_auto_retry(state, die, ev, d, retry, plan_types=None, log=print):
+def minimal_auto_retry(state, die, ev, d, retry, plan_types=None, log=print, cfg=None):
     """R-MINIMAL one automatic retry: every FAILED wave row (design FAIL or queue FAIL; INFRA has its own resubmit) of this
     die whose item has not used its automatic retry joins the in-memory retry set; the ledger keeps the failed attempt, so a
     row still waiting to launch stays released and a second failure (a later attempt) waits for its owner.  -> new set"""
@@ -453,6 +455,21 @@
         return retry
     led = state.setdefault(MINIMAL_RETRY, {})
     out = set(retry)
+    if d.get("auto_rearm", True) is not False and isinstance(d.get("src_sha"), str):       # WF-1 11-14: input-change re-arm
+        try:
+            cand = rearm_candidates(state, cfg or {}, die, d)
+            out |= set(cand)
+            kinds = {}
+            for why in cand.values():
+                for w in why:
+                    kinds[w.split("+")[0]] = kinds.get(w.split("+")[0], 0) + 1
+            sig = f"{len(cand)} " + " ".join(f"{k}={v}" for k, v in sorted(kinds.items()))
+            if (state.setdefault("rearm_logged", {})).get(die, "0 ") != sig:       # one line per die and change, never per row
+                state["rearm_logged"][die] = sig
+                log(f"KW_REARM {die}: {len(cand)} failed attempt(s) with changed inputs since the attempt are re-armed without a "
+                    f"retry key ({sig}); select() still applies holds, the plan block, the cap and the resume 'nochange' refusal")
+        except Exception as ex:                      # a re-arm failure must never stop the wave
+            log(f"KW_REARM {die} failed: {type(ex).__name__}: {ex}")
     for rec in (state.get("items") or {}).values():
         if rec.get("die") != die or not rec.get("item"):
             continue
@@ -474,6 +491,87 @@
     return out
 
 
+# WF-1 11-14 (OWNER "remove these process frictions"; EXPERT-REVIEW-6 #2, 66 % of a night's 249 FAILs had no design content):
+# every FAIL / queue-FAIL / CANCELLED-HUNG / WAIT-FORM row re-arms by itself when an input of the die changed since THAT attempt:
+# the die src_sha, the source content hash (src overlay), the kit-tool digest of this rt tree, or a host added to the die's host
+# list.  No retry key.  The kit_resume 'nochange' refusal still stops an identical relaunch; INFRA (own resubmit), the die's
+# hold_items, the RETRY_CAP block and the plan-block filter are unchanged and still apply in select().
+REARM_LED = "rearm_tools"             # state ledger {die|item: {"a": attempt, "tools": digest at first sight}}
+REARM_CLASSES = ("HUNG", "WAIT-FORM")
+_TOOLS_DIGEST = {}
+
+
+def rt_tools_digest():
+    """stat digest (path, size, mtime_ns) of the kit tools of THIS tools tree: tools/die_plan, physical/common_flow and the
+    kit_*.py files of tools/autopilot (not kit_wave.py itself nor the scheduler: those never change a kit)"""
+    if "v" in _TOOLS_DIGEST:
+        return _TOOLS_DIGEST["v"]
+    root = Path(__file__).resolve().parents[2]
+    h = hashlib.sha1()
+    for rel in ("tools/die_plan", "physical/common_flow", "tools/autopilot"):
+        base = root / rel
+        for dp, dn, fn in os.walk(base):
+            dn[:] = sorted(x for x in dn if x not in (".git", "__pycache__"))
+            for f in sorted(fn):
+                if f.endswith((".pyc", ".orig")) or ".bak" in f:
+                    continue
+                if rel == "tools/autopilot" and (dp != str(base) or not f.startswith("kit_") or f == "kit_wave.py"):
+                    continue
+                try:
+                    s = os.lstat(os.path.join(dp, f))
+                except OSError:
+                    continue
+                h.update(f"{os.path.join(dp, f)}\0{s.st_size}\0{s.st_mtime_ns}\n".encode())
+    _TOOLS_DIGEST["v"] = h.hexdigest()
+    return _TOOLS_DIGEST["v"]
+
+
+def rearm_changes(state, cfg, die, d, rec):
+    """what changed for this failed attempt since it was generated: [] (nothing) or reasons ['src_sha', 'src_overlay', 'rt_tools',
+    'hosts+h'].  Compared against the attempt's own spec.json (src_sha, src_overlay, hosts) and the tools digest seen at the
+    first tick after the failure (the ledger)."""
+    out = []
+    try:
+        sp = json.loads((Path(rec["dir"]) / "spec.json").read_text())
+    except (OSError, ValueError, KeyError, TypeError):
+        sp = {}
+    if sp.get("src_sha") and d.get("src_sha") and sp["src_sha"] != d["src_sha"]:
+        out.append("src_sha")
+    if sp.get("src_overlay") and d.get("_src_overlay") and sp["src_overlay"] != d["_src_overlay"]:
+        out.append("src_overlay")
+    added = sorted(set(opt(cfg, die, "hosts") or []) - set(sp.get("hosts") or [])) if sp.get("hosts") else []
+    if added:
+        out.append("hosts+" + ",".join(added))
+    led = state.setdefault(REARM_LED, {})
+    k, a = f"{die}|{rec.get('item')}", int(rec.get("attempt") or 0)
+    cur = rt_tools_digest()
+    seen = led.get(k)
+    if not isinstance(seen, dict) or seen.get("a") != a:
+        led[k] = {"a": a, "tools": cur}
+    elif seen.get("tools") != cur:
+        out.append("rt_tools")
+    return out
+
+
+def rearm_failed(rec):
+    """a row that ended without a verdict worth waiting on: FAIL, queue FAIL, CANCELLED-HUNG / WAIT-FORM"""
+    if rec.get("status") == "FAIL" or (rec.get("status") == "ENQUEUED" and rec.get("q_status") == "FAIL"):
+        return True
+    return rec.get("status") == "CANCELLED" and str(rec.get("class") or "") in REARM_CLASSES
+
+
+def rearm_candidates(state, cfg, die, d, log=None):
+    """{'item@attempt': [reasons]} of the die's failed rows whose inputs changed since that attempt"""
+    out = {}
+    for rec in (state.get("items") or {}).values():
+        if rec.get("die") != die or not rec.get("item") or not rearm_failed(rec):
+            continue
+        why = rearm_changes(state, cfg, die, d, rec)
+        if why:
+            out[f"{rec['item']}@{int(rec.get('attempt') or 0)}"] = why
+    return out
+
+
 def item_key(die, event, item, block=None):
     """OWNER 12.20 (plans hard-frozen): a kit is keyed on its plan block sha, so a new event with the same
     block reuses the record (no regeneration); only a changed block makes a new wave item"""
@@ -1000,11 +1098,17 @@
     d = cfg["dies"][die]
     ev = d["event"]
     states = set(opt(cfg, die, "take_states"))
+    # WF-1 11-14 (EXPERT-REVIEW-6 #7): take_states "*" (the default) = every OWNERS state except RETIRED, so a row never drops out
+    # of selection because its state is not on a hand list (t40 rows lost on WAIT-PARENT).  An explicit list still narrows.
+    take_all = "*" in states
+    only_plan = isinstance(d.get("only_items"), str) or d.get("only_items_from_plan") is True
+    if only_plan:                                    # only_items "plan": derived = the plan's items minus hold_items, no hand list
+        d = dict(d, only_items=None)
     kinds = set(opt(cfg, die, "kinds"))
     claim_m = float(opt(cfg, die, "live_claim_h")) * 60
     generic = set(opt(cfg, die, "generic_owner_labels") or [])
     retry = set(d.get("retry") or [])                 # "item@attempt": COORD released that failed attempt
-    retry = minimal_auto_retry(state, die, ev, d, retry)   # R-MINIMAL: + one automatic retry per failed item
+    retry = minimal_auto_retry(state, die, ev, d, retry, cfg=cfg)   # R-MINIMAL: + one automatic retry per failed item
     skip = {}
     picked = []
     orphans = no_row_source(rows, d, die, plan_types)
@@ -1056,12 +1160,12 @@
             skip.setdefault("counted by the sign-off counter", []).append(r["item"])
             continue
         rec = (state.get("items") or {}).get(item_key(die, ev, r["item"], blk(r["item"])))
-        bw = blocked_why(cfg, state, die, r["item"])
+        bw = blocked_why(cfg, state, die, r["item"], blk(r["item"]))
         if bw:
             skip.setdefault(bw.split(":", 1)[0] + ": same failure signature at the retry cap (kit_wave_blocked.tsv)", []).append(r["item"])
             continue
         only_retry = False
-        if r["state"] not in states:
+        if r["state"] not in states and not (take_all and r["state"] != "RETIRED"):
             # KW-RELAUNCH-1 11-05: the parent row of a class-split item carries the state of the wave's OWN running class
             # (ROUTING / QUEUED ...).  That hid every released retry of its sibling classes (S81 slice_station t29 / t40 /
             # t6: retry @6 / @8 / @9 set, never launched).  Such a parent still expands, but only into released retries.
@@ -1143,9 +1247,9 @@
                 if same:
                     skip.setdefault(HOLD_UNCHANGED, []).extend(same)
                     todo = [c for c in todo if c not in same]
-            capped = [c for c in todo if blocked_why(cfg, state, die, c)]
+            capped = [c for c in todo if blocked_why(cfg, state, die, c, blk(c))]
             for c in capped:
-                skip.setdefault(blocked_why(cfg, state, die, c).split(":", 1)[0]
+                skip.setdefault(blocked_why(cfg, state, die, c, blk(c)).split(":", 1)[0]
                                 + ": same failure signature at the retry cap (kit_wave_blocked.tsv)", []).append(c)
             todo = [c for c in todo if c not in capped]
             if cfg.get("flow_repeat_gate", True):
@@ -1397,6 +1501,11 @@
     ("INFRA", r"^gen(?:_lint)?$", r"docker: Error response from daemon|Error response from daemon: failed to create|"
                                   r"\brc[ =]+125\b|\bexit(?: status| code)? 125\b|returned non-zero exit status 125\b",
      "infra (docker rc 125: container not created)"),
+    # WF-1 11-14 (OWNER "remove process frictions"; EXPERT-REVIEW-6 #2): a unit stopped from outside (systemd / operator signal
+    # 15, "cancellation requested") and a host disk floor refusal have no design content: INFRA (own resubmit, never counted)
+    ("INFRA", None, r"ot-run: interrupted \(signal 15|cancellation requested on|stopped by operator|"
+                    r"below the (?:gen |scratch |root )?disk floor|scratch floor|disk floor",
+     "infra (unit stopped from outside / disk floor wait: no design result)"),
     ("INFRA", None, r"ot-run: NOT RUN|ot-run: NOT COMPLETED|exit 1(?:37|43)\b|Out of memory|oom-kill|OOMKilled|"
                     r"No space left on device|rsync error|Cannot connect to the Docker daemon|"
                     r"yosys elaboration failed rc[ =]+1(?:25|37)\b|"
@@ -1520,6 +1629,13 @@
     # KIT-TRIAGE-1/G26 11-01 (KV qkd_hr_core_peer gen): a tool input path that does not exist (a cached views file /
     # recipe naming a removed lane worktree) is the flow's, and is named as such instead of a generic traceback
     ("FLOW", None, r"FileNotFoundError|No such file or directory", "tool input file missing (stale path / pruned worktree)"),
+    # WF-1 11-14 (EXPERT-REVIEW-6 #2: 43 kit_rtl AttributeError reset_tree.pin_root_copies tool skew + 42 QC gen 'plan invalid'
+    # schema = 66 % of a night's FAILs, none with design content): a Python exception (or the generator's plan-schema refusal)
+    # at kit_rtl / gen that no rule above names as PLAN / RTL is the tool or source skew, not the design.  INFRA: resubmitted on
+    # its own up to infra_attempts, never counted by RETRY_CAP, and revived by the input-change re-arm (minimal_auto_retry)
+    ("INFRA", r"^(?:kit_rtl|gen)$", r"Traceback \(most recent call last\)|KeyError|TypeError|AttributeError|"
+                                    r"gen phys: ERROR plan invalid",
+     "infra (python exception / plan-schema refusal in the kit tool: tool or source skew)"),
     ("FLOW", None, r"Traceback \(most recent call last\)|KeyError|TypeError|AttributeError|invalid command name|"
                    r"can't read \"|Error: .*\.tcl, \d+", "tool / Tcl error"),
 ]
@@ -3587,7 +3703,7 @@
 # owner, never the wave lane) and is listed in BLOCKED_FILE, which COORD reads.  Released only by the die's 'unblock' list:
 # entries 'pattern' or 'pattern#tag' (fnmatch on the item); each entry releases ONE attempt (the entry is spent); a new
 # release needs a new entry (another #tag).  The same failure after the release blocks the row again at once.
-RETRY_CAP = 3
+RETRY_CAP = 3              # same-recipe small fixes only (OWNER 11-14: stays 3); a changed input digest restarts the count at 0 (WF-1)
 BLOCKED_FILE = "kit_wave_blocked.tsv"
 BLOCKED_COLS = ["die", "item", "block", "n", "owner", "owner_source", "item_default_owner", "stage", "signature", "attempts",
                 "first", "last", "last_reason", "release"]
@@ -3605,7 +3721,7 @@
         i = min([why.find(w) for w in HOST_GAP_WHY if w in why] or [-1])
         if i >= 0:
             why, cls = why[i:], "FLOW"
-    elif cls == "INFRA" and _TRANSIENT_INFRA.search(why):
+    elif cls == "INFRA":              # WF-1 11-14: no INFRA failure counts toward RETRY_CAP (own bounded resubmit, infra_attempts)
         return None
     head, _, rest = why.partition(" @")
     stg = (rest.split(":", 1)[0].strip() if rest else "") or str(stage or "")
@@ -3615,7 +3731,19 @@
     return (cls or "FLOW"), f"{cls}|{stg}|{norm}"
 
 
-def note_fail_sig(st, rec, cls, why, now=None):
+def input_digest(cfg, die):
+    """WF-1 11-14 (OWNER: a redesign resets the retry counter): digest of the die inputs a relaunch would build on, except the
+    plan block (kept apart: it is per item): plan sha, die src_sha, source content hash, kit tools digest, gen env / kit_rtl form"""
+    d = (cfg.get("dies") or {}).get(die) or {}
+    try:
+        body = [d.get("_plan_sha") or d.get("plan_sha"), d.get("src_sha"), d.get("_src_overlay"), rt_tools_digest(),
+                d.get("gen_env"), d.get("kit_rtl"), d.get("event")]
+        return hashlib.sha1(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]
+    except (TypeError, ValueError):
+        return ""
+
+
+def note_fail_sig(st, rec, cls, why, now=None, inp=None):
     """count consecutive identical FAIL signatures per die|item (across attempts and events); -> the counter dict"""
     fs = st.setdefault("fail_sigs", {})
     key = f"{rec.get('die')}|{rec.get('item')}"
@@ -3630,6 +3758,8 @@
     c["n"] = int(c.get("n") or 0) + 1
     c["attempts"] = (list(c.get("attempts") or []) + [f"{rec.get('event')}@{rec.get('attempt')}"])[-8:]
     c.update(last=now, stage=str(rec.get("stage") or ""), reason=re.sub(r"\s+", " ", str(why or ""))[:300])
+    if inp is not None:
+        c["inp"], c["block"] = inp, rec.get("block_sha") or ""
     return c
 
 
@@ -3637,11 +3767,16 @@
     (st.get("fail_sigs") or {}).pop(f"{rec.get('die')}|{rec.get('item')}", None)
 
 
-def blocked_why(cfg, st, die, item):
+def blocked_why(cfg, st, die, item, block=None):
     """'' or the BLOCKED-<class> skip reason of an item at the retry cap that the die's unblock list does not release"""
     c = (st.get("fail_sigs") or {}).get(f"{die}|{item}")
     if not c or int(c.get("n") or 0) < RETRY_CAP:
         return ""
+    if not c.get("inp"):                                              # a count from before the digest existed: stamp it now
+        c["inp"], c["block"] = input_digest(cfg, die), block or ""
+    if c.get("inp") and (c["inp"] != input_digest(cfg, die) or (block and c.get("block") and c["block"] != block)):
+        (st.get("fail_sigs") or {}).pop(f"{die}|{item}", None)       # WF-1: input digest changed = a redesign, attempts restart at 0
+        return ""
     if unblock_entry(cfg, die, item, c):
         return ""
     return (f"BLOCKED-{c.get('cls') or 'FLOW'}: the same failure {c['n']}x in a row ({c.get('sig', '')[:160]}); "
@@ -6137,7 +6272,7 @@
                 continue
             if any(fnmatch.fnmatchcase(item, pat) for pat in (d.get("hold_items") or {})):
                 continue                                  # an operator hold holds the arm too
-            if d.get("only_items") is not None and item not in d["only_items"]:
+            if isinstance(d.get("only_items"), list) and item not in d["only_items"]:
                 continue                                  # KW-FIX-45 11-11: a paused / restricted die (only_items) launches no arm
                                                           # either (QC only_items=[] still got 6 arm relaunches at 08:42)
             if load_hold(cfg, die, item, brec.get("parent_item"), core_module(item)):
@@ -6363,11 +6498,17 @@
     return out
 
 
-def hung_judge(prev, prog, hub_newest, now, minutes, cpu_s=HUNG_CPU_S):
+HUNG_POST_MIN = 360         # WF-1 11-14 (COORD/OWNER #H): a row with a frozen log but busy CPU is never cancelled; at this age it is only posted
+HUNG_BUSY_FRAC = 0.05       # WF-1 11-14: CPU growth over the window above this fraction of ONE core counts as busy (was a flat 60 CPU-s)
+
+
+def hung_judge(prev, prog, hub_newest, now, minutes, cpu_s=None):
     """-> (hung, new_watch, why).  prev = the row's hung_watch {'cpu', 't'} (CPU mark and when it was set), prog = this row's
     progress_on_fleet entry.  The CPU mark moves when the CPU grew by >= cpu_s since it (or went down: a restarted process);
     hung only when the mark is >= minutes old AND the newest stage log (fleet or hub) is >= minutes old."""
     cpu = float(prog.get("cpu") or 0)
+    if cpu_s is None:        # busy = more than HUNG_BUSY_FRAC of one core over the watch window (>= HUNG_CPU_S): ~0 CPU only
+        cpu_s = max(HUNG_CPU_S, HUNG_BUSY_FRAC * minutes * 60.0)
     w = dict(prev or {})
     if not w or cpu - float(w.get("cpu", 0)) >= cpu_s or cpu < float(w.get("cpu", 0)):
         w = {"cpu": cpu, "t": now}
@@ -6436,6 +6577,8 @@
                     watch_out[key] = dict(w, containers=list(p.get("containers") or [])) if hung else w
                 if hung:
                     out.append((key, "HUNG", why))
+                elif m >= HUNG_POST_MIN and not rec.get("hung_posted"):
+                    out.append((key, "POST6H", f"unit active, log frozen {m:.0f} min but CPU busy; not cancelled (WF-1): {why}"))
                 elif m > minutes:
                     out.append((key, "SILENT", f"unit active, no output for {m:.0f} min; alive: {','.join(live[roots[key]][:3])}; "
                                                f"progressing ({why}) (reported only)"))
@@ -6465,6 +6608,12 @@
             AP.log(f"KIT-WAVE REAP-DEAD SILENT {key}: {why}")
             continue
         rec = st["items"][key]
+        if kind == "POST6H":                               # WF-1: post once, never kill a busy job
+            if not AP.DRY:
+                rec["hung_posted"] = time.time()
+                notices.setdefault(rec["die"], []).append(f"{rec['item']}@{rec.get('attempt')} NO-PROGRESS-6H (post only): {why[:200]}")
+                AP.log(f"KIT-WAVE HUNG-WATCH POST {key}: {why}")
+            continue
         if AP.DRY:
             AP.log(f"KIT-WAVE REAP-DEAD would reap {key} {kind}: {why}")
             continue
@@ -6640,7 +6789,7 @@
             free_not_run(rec, (res.get("errors") or "") + "\n" + (res.get("tail") or ""))   # KW-FIX-45 11-11: NOT RUN is no attempt
         if cls == "INFRA" and infra_used(rec) < infra_attempts(cfg, rec["die"]):
             rec["status"] = "RETRY-INFRA"                # relaunched next tick (up to infra_attempts in all)
-        c = note_fail_sig(st, rec, cls, why)
+        c = note_fail_sig(st, rec, cls, why, inp=input_digest(cfg, rec["die"]))
         if c and int(c.get("n") or 0) >= RETRY_CAP and blocked_why(cfg, st, rec["die"], rec["item"]):
             rec["blocked"] = f"BLOCKED-{c.get('cls') or cls}"
             if rec["status"] == "RETRY-INFRA":
```
```diff
--- a/autopilot.py	2026-11-14 00:34:04.641062518 -0800
+++ b/autopilot.py	2026-11-14 00:38:26.312184414 -0800
@@ -2953,9 +2953,17 @@
     except BlockingIOError:
         print("autopilot: previous tick still running", file=sys.stderr)
         return 0
+    _t0 = time.time()
+    _ph = {}                                           # WF-1 11-14: per-phase wall seconds, one TICK-TIMES line at the end
+
+    def _mark(name, _last=[time.time()]):
+        n = time.time()
+        _ph[name] = round(n - _last[0], 1)
+        _last[0] = n
     st = load_state()
     rows = parse_queue(read_queue_text())
     geom_text = read_coord("lanes/GEOM-REVIEW.md")
+    _mark("load")
     global GEOM_TEXT
     GEOM_TEXT = geom_text
     # Resolve explicit visual verdicts before promoting pending requests to measured checks.
@@ -2963,20 +2971,25 @@
     resolve_geom(rows, geom_text)
     AG.prepare(sys.modules[__name__], st, rows)
     resolve_geom(rows, geom_text)
+    _mark("geom")
     load_closure()
     apply_evac(st)
     poll_running(st)
+    _mark("poll_running")
     poll_reviews(st)
     retry_pending(st)
     retry_unversioned(st)
+    _mark("reviews_retry")
     submitted = admit_new(st, rows)
     save_state(st)
+    _mark("admit_new")
     if os.environ.get("AP_WAVE_BALANCE", "1") != "0":   # WAVE-BALANCE-1 11-11: inert unless kit_wave.json wave_balance.enabled
         try:
             WB.step(sys.modules[__name__], st)
             save_state(st)
         except Exception as e:                         # a balance pass must never stop the chain
             log(f"WAVE-BALANCE failed: {type(e).__name__}: {e}")
+    _mark("wave_balance")
     if os.environ.get("AP_KIT_WAVE", "1") != "0":      # KIT-WAVE-1 (owner 10-30 (A)); inert without autopilot/kit_wave.json
         try:
             KW.step(sys.modules[__name__])
@@ -2986,15 +2999,19 @@
             admit_after_wave(st, MAX_SUBMIT_PER_TICK - submitted)
         except Exception as e:                         # the next tick admits these rows anyway
             log(f"ADMIT-AFTER-WAVE failed: {type(e).__name__}: {e}")
+    _mark("kit_wave_step+admit")
     if os.environ.get("AP_AUTO_RESIGN", "1") != "0":   # FLOW-29 owner 11-04: signed runs re-signed on the newest tag, no agent
         try:
             AR.step(sys.modules[__name__])
         except Exception as e:                         # a re-sign pass must never stop the chain
             log(f"AUTO-RESIGN failed: {type(e).__name__}: {e}")
+    _mark("auto_resign")
     try:
         write_loop_gaps(st, rows, geom_text)
     except Exception as e:                             # the gap report must never stop the chain
         log(f"LOOP-GAPS failed: {type(e).__name__}: {e}")
+    _mark("loop_gaps")
+    log("TICK-TIMES total=%.0fs " % (time.time() - _t0) + " ".join(f"{k}={v}s" for k, v in _ph.items()))
     counts = {}
     for j in st["jobs"].values():
         counts[j.get("status")] = counts.get(j.get("status"), 0) + 1
```
```diff
--- a/eco_loop.py	2026-11-14 00:47:00.569131406 -0800
+++ b/eco_loop.py	2026-11-14 00:40:32.452300387 -0800
@@ -187,6 +187,26 @@
     return (None, n) if s.get("nonport_wns") is None else (float(s["nonport_wns"]), n)
 
 
+# WF-1 11-14 (OWNER "remove process frictions"; EXPERT-REVIEW-6 #9): under R-MINIMAL a routed DRC-0 record whose ONLY failing
+# gate is the internal FF hold (TT setup >= -42 ps passes) goes into the hold-buffer ECO whatever the miss size or endpoint count:
+# the legacy near-miss window (NEAR_WNS_PS / NEAR_ENDPOINTS) and the structural-advisory eligibility refusal do not apply to it
+# (kv3_phy_v1 TT -34.25 pass / FF -204 on 297 endpoints was sent to 'GEOMETRY + REDESIGN, no ECO').  The result is re-judged by
+# the same three gates (signoff_chain.signed).
+def minimal_hold_only(rec):
+    """True: R-MINIMAL profile and signoff_profile.judge() fails ONLY hold_ff (drc and setup_tt PASS)"""
+    if os.environ.get("OT_SIGNOFF_PROFILE", "minimal").strip().lower() == "legacy" or not isinstance(rec, dict):
+        return False
+    try:
+        import importlib.util
+        spec = importlib.util.spec_from_file_location("signoff_profile_eco", HERE / "signoff_profile.py")
+        mod = importlib.util.module_from_spec(spec)
+        spec.loader.exec_module(mod)
+        g = mod.judge(rec)["gates"]
+    except Exception:
+        return False
+    return g.get("hold_ff") == "FAIL" and g.get("drc") == "PASS" and g.get("setup_tt") == "PASS"
+
+
 def metrics(rec, signoff_path=None):
     """sign-off record -> {verdict, signed, tt, ff, drv, drc, fails}; with OT_HOLD_REPAIR_SCOPE=nonport and a readable
     FF census next to signoff_path also ff_np / ff_np_n (the non-port hold the ECO repairs), which the stop rule and the
@@ -203,6 +223,7 @@
     out = dict(verdict=verdict, signed=bool(signed), tt=(c.get("setup_tt") or {}).get("wns_ps"),
                 ff=(c.get("hold_ff") or {}).get("wns_ps"), drv=int(drv), drc=int((c.get("drc") or {}).get("count") or 0),
                 drv_tt=int(by.get("tt", 0)), drv_ff=int(by.get("ff", 0)), fails=fails,
+                min_hold_only=minimal_hold_only(rec),
                 vclk_tt=measured_vclk((c.get("setup_tt") or {}).get("vclk_reference")),
                 vclk_ff=measured_vclk((c.get("hold_ff") or {}).get("ff_vclk_reference")))
     if signoff_path and hold_scope() == "nonport":
@@ -219,7 +240,8 @@
     if hold_mm(kit):
         return ["m" + str(hm)]
     tt, ff = prev.get("tt"), prev.get("ff")
-    need_t = (tt is not None and tt < 0) or prev.get("drv_tt", 0) > 0
+    # WF-1 11-14: a record that fails only the FF hold under R-MINIMAL (TT setup within tolerance) needs no TT setup pass
+    need_t = ((tt is not None and tt < 0 and not prev.get("min_hold_only")) or prev.get("drv_tt", 0) > 0)
     need_b = (ff is not None and ff < 0) or prev.get("drv_ff", 0) > 0 or prev.get("drc", 0) > 0
     out = (["t" + str(hm)] if need_t else []) + (["b" + str(hm)] if need_b or not need_t else [])
     return out
@@ -232,6 +254,8 @@
     m = metrics(rec)
     if m["signed"]:
         return False, "already signed"
+    if minimal_hold_only(rec):
+        return True, "ECO class: R-MINIMAL only internal FF hold fails (auto hold-buffer ECO, no near-miss window)"
     if not m["fails"]:
         return False, "no FAIL gate (NOT RUN / parent-only reasons are not an ECO case)"
     other = sorted(set(m["fails"]) - ECO_FAILS)
@@ -298,6 +322,9 @@
     scores hold on the endpoints sign-off leaves to the core (KW-FIX-36 R4: without input-port starts and output-port
     endpoints, core_hold); with no readable split it scores the whole number.  Same numbers as ever: one iteration,
     NEAR_WNS_PS, NEAR_ENDPOINTS of the remaining endpoints."""
+    if minimal_hold_only(rec):
+        return True, [], ["R-MINIMAL auto hold ECO (WF-1): only the internal FF hold fails; the legacy "
+                          f"{NEAR_WNS_PS:g} ps / {NEAR_ENDPOINTS} endpoint window is not applied"]
     c = rec.get("checks") or {}
     far, warn = [], []
     for key, name in (("setup_tt", "setup"), ("hold_ff", "hold")):
```
```diff
--- a/test_kit_wave.py	2026-11-14 00:47:01.806153727 -0800
+++ b/test_kit_wave.py	2026-11-14 00:46:52.756990500 -0800
@@ -162,12 +162,12 @@
     def test_selection_and_order(self):
         rows = KW.parse_owners(OWN)
         picks, skip = KW.select(rows, cfg(), "qwen_kvsys", {"items": {}}, PLAN)
-        self.assertEqual([p["item"] for p in picks], ["kv3_phy_v1", "kv3_hg_v1", "kv3_hub_Eo"])   # replicas desc
+        self.assertEqual([p["item"] for p in picks], ["kv3_phy_v1", "kv3_hg_v1", "kv3_hroot", "kv3_hub_Eo"])   # replicas desc (WF-1 11-14: take_states default * = every state)
         self.assertEqual(skip["live job (another lane)"], ["kv3_io_cor_v1"])
         self.assertIn("kv3_pc", skip["lane activity < 3 h (KV-KITS-W)"])
         self.assertEqual(skip["kind core not in wave"], ["qkd_hr_cdc_ci"])
         self.assertEqual(skip["not in plan of record"], ["kv3_gone"])
-        self.assertNotIn("kv3_hroot", [p["item"] for p in picks])          # KIT-PLACED not in take_states
+        self.assertIn("kv3_hroot", [p["item"] for p in picks])             # WF-1 11-14: KIT-PLACED taken (take_states default *)
 
     def test_own_queue_job_on_parent_is_not_a_claim(self):
         own = lambda lj, owner="KIT-WAVE-12": KW._own_wave_unit({"owner": owner, "item": "sle_su_l1", "live_job": lj})
@@ -379,7 +379,7 @@
             ("place", "FACE_GUARD FAIL shared 7645 bits", "PLAN"),
             ("place", "[ERROR ORD-2013] instance u_m LEF master ot_sram_1r1w_32x64_m1 not found", "PLAN"),
             ("gen", "type kv3_sys_SD: local reset tap [388.8, 596.16] is blocked", "PLAN"),
-            ("gen", "Traceback (most recent call last):\n  File gen.py\nKeyError: 'x'", "FLOW"),
+            ("gen", "Traceback (most recent call last):\n  File gen.py\nKeyError: 'x'", "INFRA"),
             ("preflight", "KIT_PREFLIGHT FAIL\nmissing staged file", "FLOW"),
             ("geom", "AP_AUTO_GEOM FAIL fill .0997 channel_h 1.065", "PLAN"),
             ("cells", "512000 cells", "PLAN"),
```
