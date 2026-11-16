"""pending_actions: LIMIT-GUARD-1116 (FABLE-FLOW-1113 #3).  A release step that used to live in a lane's memory is data in autopilot/pending_actions.json,
and the autopilot runs it in the tick with no LLM.  A lane writes the action and may then stop (usage limit, crash).

  {"actions": [{"id": "s81-adopt-x", "when": [<cond>, ...],            # every condition must hold; empty = always
                "do": [{"set": {"die": "s81", "key": "src", "value": "/srv/.../tree"}},
                       {"delete_hold": {"die": "s81", "key": "*"}},
                       {"relaunch_infra": {"die": "s81"}}]}]}
  cond: {"exists": path} | {"file_contains": {"path": p, "text": t}} | {"json_eq": {"path": p, "key": "a.b", "value": v}} | {"after": epoch_s}
  set / delete_hold edit the loaded config in memory every tick (idempotent, like the tree switch); relaunch_infra turns the die's INFRA-failed
  rows into RETRY-INFRA ONCE per action (ledger pending_actions_done.json).  Remove the action from the file to stop it.  Nothing here launches or
  cancels a job: the wave's own gates decide."""
import json
import time
from pathlib import Path

FILE = "pending_actions.json"
DONE = "pending_actions_done.json"


def _get(o, dotted):
    for k in str(dotted).split("."):
        o = o.get(k) if isinstance(o, dict) else None
    return o


def cond_ok(c, now=None):
    now = time.time() if now is None else now
    try:
        if "exists" in c:
            return Path(c["exists"]).exists()
        if "file_contains" in c:
            return c["file_contains"]["text"] in Path(c["file_contains"]["path"]).read_text(errors="replace")
        if "json_eq" in c:
            j = c["json_eq"]
            return _get(json.loads(Path(j["path"]).read_text()), j["key"]) == j["value"]
        if "after" in c:
            return now >= float(c["after"])
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return False                                         # an unknown condition never fires


def load(text):
    try:
        a = (json.loads(text) if text and text.strip() else {}).get("actions") or []
    except ValueError:
        return []
    return [x for x in a if isinstance(x, dict) and x.get("id")]


def ready(action, now=None):
    return all(cond_ok(c, now) for c in action.get("when") or [] if isinstance(c, dict)) and \
        all(isinstance(c, dict) for c in action.get("when") or [])


def apply_cfg(cfg, actions, log, now=None):
    """set / delete_hold of every ready action, in memory.  -> ids applied"""
    out = []
    for a in actions:
        if not ready(a, now):
            continue
        for step in a.get("do") or []:
            if "set" in step:
                s = step["set"]
                d = (cfg.get("dies") or {}).get(s.get("die"))
                if isinstance(d, dict) and s.get("key") and d.get(s["key"]) != s.get("value"):
                    d[s["key"]] = s.get("value")
                    log(f"KIT-WAVE PENDING-ACTION {a['id']}: {s['die']}.{s['key']} set")
            elif "delete_hold" in step:
                s = step["delete_hold"]
                h = ((cfg.get("dies") or {}).get(s.get("die")) or {}).get("hold_items")
                if isinstance(h, dict) and s.get("key") in h:
                    del h[s["key"]]
                    log(f"KIT-WAVE PENDING-ACTION {a['id']}: {s['die']} hold {s['key']} dropped")
        out.append(a["id"])
    return out


def apply_rows(st, actions, done, log, now=None):
    """relaunch_infra of every ready action not yet in `done` (a dict, updated).  -> rows released"""
    now = time.time() if now is None else now
    n = 0
    for a in actions:
        if a["id"] in done or not ready(a, now):
            continue
        for step in a.get("do") or []:
            if "relaunch_infra" in step:
                die = step["relaunch_infra"].get("die")
                for r in (st.get("items") or {}).values():
                    if r.get("die") == die and r.get("status") == "FAIL" and r.get("class") == "INFRA" and not r.get("blocked"):
                        r.update(status="RETRY-INFRA", updated=now, no_host_at=0)
                        n += 1
        done[a["id"]] = now
        log(f"KIT-WAVE PENDING-ACTION {a['id']}: done" + (f", {n} INFRA row(s) released" if n else ""))
    return n


def step_cfg(AP, cfg, ap_dir):
    try:
        return apply_cfg(cfg, load(AP.read_coord("autopilot/" + FILE)), AP.log)
    except Exception as e:
        AP.log(f"KIT-WAVE pending actions (config) skipped: {type(e).__name__}: {e}")
        return []


def step_rows(AP, st, ap_dir):
    try:
        p = Path(ap_dir) / DONE
        try:
            done = json.loads(p.read_text())
        except (OSError, ValueError):
            done = {}
        acts = load(AP.read_coord("autopilot/" + FILE))
        n = apply_rows(st, acts, done, AP.log)
        done = {k: v for k, v in done.items() if k in {a["id"] for a in acts}}   # a removed action is forgotten
        if not AP.DRY:
            p.write_text(json.dumps(done))
        return n
    except Exception as e:
        AP.log(f"KIT-WAVE pending actions (rows) skipped: {type(e).__name__}: {e}")
        return 0
