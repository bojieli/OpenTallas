#!/usr/bin/env python3
"""fail_route: every KIT-WAVE FAIL and every waiter RESULT FAIL reaches a live owner, and is escalated when nobody acks
(FAIL-ROUTE-1115, ruling r220, FABLE-FLOWCLASS-RETRY-2030 part P5).

Hub script, run every 10 min by fail_route.timer next to waiter_fail_relay.timer.  Reads
  - autopilot/kit_wave_state.json fail_sigs (one row per die|item with cls, stage, reason, n, last) for rows still FAIL,
  - queue RESULT lines whose text starts with a failure verdict (the waiter_fail_relay filter),
  - the queue and lanes/posts for lane liveness (a lane is live when it posted in the last --live-h hours).
Each failure gets a class key  <die>|<kind>|<stage>|<masked reason>  (item names, digits and hashes masked) and an owner:
the live lane whose recent posts name the item family, else the die default if live, else the newest live lane of the die,
else COORD.  Per (owner, class) one batched post, once:
    NEEDS-ACTION [FAIL-ROUTE-1115 -> OWNER, COORD] FAIL-CLASS <cid> die/stage/cls n items ...
If no RESULT or ACK from that owner (after the post) names the class id, an item or its family
within --ack-min minutes, one NEEDS-LANE [FAIL-ROUTE-1115 -> COORD] with class, items and count is posted, once.
State ~/.local/state/fail-route.json; keys are also looked up in the queue (FAIL-CLASS <cid> owner), so a lost state file never
repeats a post.  A failed post is not recorded and is retried by the next run.

FLOW-OPS-0900 (FABLE-FLOW-0745 d: 4-7 classes bounced between successors, one for 129 min): a class is ONE record per class id across
owners.  A stood-down lane is never picked as owner; a class whose recorded owner stood down goes to the live end of that owner's
successor chain (lanes/LANE-STATUS.tsv, tools/post_redirect.py) with one HANDOVER post that keeps the first-seen time and the owner chain;
an ACK/RESULT from any lane of the chain counts; NEEDS-LANE is posted at most once per class id.  bin/stand-down.sh copies the lane's open
classes (fail_route.py --open-relays LANE) into the successor's handoff as an OPEN-RELAYS block.

usage: fail_route.py [--coord DIR] [--state F] [--post-sh F] [--window-h H] [--live-h H] [--ack-min N] [--dry]
       fail_route.py --open-relays LANE [--state F]     (bin/stand-down.sh)
"""
import argparse
import hashlib
import json
import os
import re
import runpy
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HOME = Path(os.path.expanduser("~"))
LANE = "FAIL-ROUTE-1115"
DIE_DEFAULT = {"s81": "DIE-S81-92", "qwen_compute": "DIE-QC-103", "qwen_kvsys": "KV-102", "head": "HEAD-100"}
DIE_PREFIX = {"s81": ("DIE-S81", "S81-", "FABLE-FIX-S81"), "qwen_compute": ("DIE-QC", "QC-", "FABLE-FIX-QC"),
              "qwen_kvsys": ("KV-", "DIE-KV", "FABLE-FIX-KV"), "head": ("HEAD-", "DIE-HEAD", "FABLE-FIX-HEAD"), "hbm": ("DIE-HBM", "HBM-")}
NOT_OWNER = ("FABLE-", "COORD", "FLOW-HEALTH", "KIT-OPS", "KIT-WAVE", "MERGE-QUEUE", "CLEAN", "PLAN-GATE-PRE", LANE)
# COORD 11-16: S81 kit items go to the lane that owns their item family; first match wins, else the die default
S81_RULES = ((r"^col_", "FABLE-FIX-S81-COL"), (r"^(leaf|ring)|_ring", "FABLE-FIX-S81-RINGS"), (r"strip", "FABLE-FIX-S81-STRIP"),
             (r"serdes|phy", "S81-SERDES-PHY-1116"))
S81_ONLY = {"FABLE-FIX-S81-COL"}   # never the generic pick for non-col items
OWNER_OK = ("FABLE-FIX-",)   # fix lanes own failures; other FABLE-* are reviewers
VERDICT = re.compile(r"did NOT pass|FAIL|REFUSE|Traceback")
POST = re.compile(r"^- (?P<stamp>\d{4}-\d\d-\d\d \d\d:\d\d) (?:PST|PDT)\s+(?P<tag>[A-Z][A-Z-]*)\s+\[(?P<lane>[A-Za-z0-9][A-Za-z0-9._-]*)"
                  r"\s*->\s*(?P<to>[^\];]*)(?:;\s*cc\s*(?P<cc>[^\]]*))?\]\s*(?P<text>.*)$")
LA = ZoneInfo("America/Los_Angeles")
LIVE_STATUS = ("FAIL", "RETRY-INFRA", "ROUTE-HELD")
MAX_NAMES = 12


def stamp_epoch(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=LA).timestamp()
    except ValueError:
        return None


def parse_posts(text):
    out = []
    for ln in text.splitlines():
        m = POST.match(ln)
        if m:
            t = stamp_epoch(m.group("stamp"))
            if t is not None:
                d = m.groupdict()
                d["t"] = t
                d["to"] = [x for x in re.split(r"[,\s]+", d["to"] or "") if x]
                out.append(d)
    return out


def family(item):
    return re.sub(r"(__(cl|pv|t)[0-9a-z]+)+$", "", item)


def mask(reason):
    r = re.sub(r"\b[\w.-]*__[\w.-]+\b", "<item>", reason or "")
    r = re.sub(r"/[\w./@+-]+", "<path>", r)
    r = re.sub(r"\b[0-9a-f]{7,}\b", "<h>", r)
    r = re.sub(r"\d+", "N", r)
    return re.sub(r"\s+", " ", r).strip()[:90]


def cid_of(key):
    return hashlib.sha256(key.encode()).hexdigest()[:10]


def lane_status(coord):
    """LANE-STATUS rows via tools/post_redirect.py ({} when unreadable: the old behaviour)"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import post_redirect as PR
        return PR.load_status(coord)
    except Exception:                       # noqa: BLE001 - routing never stops on the status file
        return {}


def live_end(lane, status):
    """the live lane at the end of LANE's stood-down chain (LANE itself when live / unknown / no successor)"""
    if not lane or lane == "COORD" or not status:
        return lane
    try:
        import post_redirect as PR
        return PR.live_lane(lane, status)[0] or lane
    except Exception:                       # noqa: BLE001
        return lane


def stood_down(lane, status):
    return bool(status) and (status.get(lane) or ("",))[0] == "stood-down"


def live_lanes(posts, now, live_h, status=None):
    """lane -> (last post epoch) for lanes that posted within live_h hours; reviewers and infra lanes are not owners.
    FLOW-OPS-0900: a stood-down lane is not live (its last posts are recent at the moment it stands down)."""
    last = {}
    for p in posts:
        if p["lane"] == "CODEX" or (p["lane"].startswith(NOT_OWNER) and not p["lane"].startswith(OWNER_OK)):
            continue
        if stood_down(p["lane"], status):
            continue
        last[p["lane"]] = max(last.get(p["lane"], 0), p["t"])
    return {k: v for k, v in last.items() if now - v <= live_h * 3600}


def pick_owner(die, fam, live, posts, now, live_h):
    """live owner lane for (die, family) or COORD."""
    pref = DIE_PREFIX.get(die, ())
    if die == "s81":
        live = {k: v for k, v in live.items() if k not in S81_ONLY}
    cand = {k: v for k, v in live.items() if k.startswith(pref) or k == DIE_DEFAULT.get(die)}
    if fam:
        named = [p for p in posts if p["lane"] in live and now - p["t"] <= live_h * 3600 and fam in p["text"]
                 and (p["lane"] in cand or p["lane"].startswith(pref))]
        if named:
            return max(named, key=lambda p: p["t"])["lane"]
    d = DIE_DEFAULT.get(die)
    if d in live:
        return d
    if cand:
        return max(cand, key=cand.get)
    return "COORD"


def explicit_owner(coord, die, items, live):
    """Honor live COORD exact-item assignments; mixed explicit owners return COORD.

    Prefix rows remain the stale-list vocabulary, not inferred failure ownership.
    Missing or retired explicit rows retain the existing liveness fallback.
    """
    try:
        lines = (Path(coord) / "autopilot/COORD-ROUTED-OWNERS.tsv").read_text().splitlines()
    except OSError:
        return ""
    rows = {}
    for line in lines:
        if not line or line.startswith("#"):
            continue
        cells = line.split("\t")
        if len(cells) >= 3 and cells[0] == die and cells[1] in items and "*" not in cells[1]:
            rows[cells[1]] = cells[2]
    owners = {rows[item] for item in items if rows.get(item) in live}
    if len(owners) > 1:
        return "COORD"
    if owners and all(rows.get(item) in live for item in items):
        return next(iter(owners))
    return ""


def kit_failures(state, now, window_h):
    """[(die, item, cls, stage, reason, n, last)] of fail_sigs rows whose item is still failed and failed within the window."""
    sigs = state.get("fail_sigs") or {}
    items = state.get("items") or {}
    open_ = set()
    for k, v in items.items():
        if v.get("status") in LIVE_STATUS:
            open_.add("|".join(k.split("|")[:2]))
    out = []
    for k, v in sigs.items():
        if k not in open_ or now - v.get("last", 0) > window_h * 3600:
            continue
        reason = v.get("reason", "")
        if "signal 15" in reason or v.get("cls") == "STOPPED":
            continue
        die, item = k.split("|", 1)
        out.append((die, item, v.get("cls", ""), v.get("stage", ""), reason, v.get("n", 1), v.get("last", 0)))
    return out


def waiter_die(lane, text):
    s = (lane + " " + text[:200]).upper()
    for key, tok in (("s81", "S81"), ("qwen_kvsys", "KV"), ("head", "HEAD"), ("hbm", "HBM"), ("qwen_compute", "QC")):
        if re.search(r"(?<![A-Z0-9])" + tok + r"(?![A-Z])", s):
            return key
    return "other"


def build_classes(coord, state, posts, now, window_h, live_h, status=None):
    """{class key: dict(die, kind, owner, items{name: epoch}, label)}"""
    live = live_lanes(posts, now, live_h, status)
    classes = {}

    def add(die, kind, label, name, fam, t, ckey, forced=""):
        c = classes.setdefault(ckey, dict(die=die, kind=kind, label=label, items={}, fams=set(), forced=forced))
        c["items"][name] = t
        c["fams"].add(fam)

    for die, item, cls, stage, reason, n, last in kit_failures(state, now, window_h):
        label = f"{die}/{stage}/{cls}"
        forced = next((ln for rx, ln in S81_RULES if re.search(rx, item)), DIE_DEFAULT["s81"]) if die == "s81" else ""
        add(die, "kit", label + " " + mask(reason)[:60], item, family(item), last,
            f"kit|{die}|{cls}|{stage}|{mask(reason)}|{forced}", forced)
    for p in posts:
        if p["tag"] != "RESULT" or p["lane"] == "CODEX" or p["lane"].startswith(NOT_OWNER) or now - p["t"] > window_h * 3600:
            continue
        if not VERDICT.search(p["text"][:300]):
            continue
        die = waiter_die(p["lane"], p["text"])
        name = f"{p['lane']}@{p['stamp'][11:]}"
        add(die, "waiter", f"{die}/waiter RESULT FAIL", name, p["lane"], p["t"], f"waiter|{die}")
    for ckey, c in classes.items():
        fam = sorted(c["fams"])[0] if len(c["fams"]) == 1 else None
        c["owner"] = (explicit_owner(coord, c["die"], c["items"], live) if c["kind"] == "kit" else "") or c.get("forced") or pick_owner(c["die"], fam, live, posts, now, live_h)
        c["owner"] = live_end(c["owner"], status)          # FLOW-OPS-0900: a forced / explicit owner that stood down -> its live successor
        c["cid"] = cid_of(ckey)
    return classes


RUNTIME_FAIL_ROUTE = Path("/srv/opentallas-scratch2/claude/rt/current/tools/autopilot/fail_route.py")


def reset_note(state, cls):
    if cls["kind"] != "kit":
        return ""
    item = max(cls["items"], key=cls["items"].get)
    sig = (state.get("fail_sigs") or {}).get(f"{cls['die']}|{item}") or {}
    if "physical collector_tree differs from captured bound reset identity" not in sig.get("reason", ""):
        return ""
    try:
        report = runpy.run_path(str(RUNTIME_FAIL_ROUTE)).get("reset_evidence")
    except OSError:
        return ""
    return report(state, cls["die"], item) if report else ""


def names_line(c):
    ns = sorted(c["items"], key=lambda n: -c["items"][n])
    s = ", ".join(ns[:MAX_NAMES])
    return s + (f", +{len(ns) - MAX_NAMES} more" if len(ns) > MAX_NAMES else "")


def acked(posts, owner, c, after, chain=()):
    """a RESULT or ACK from the owner (or a lane of its owner chain, FLOW-OPS-0900) after `after` that names the class id, an item or an item family."""
    toks = {c["cid"], *c["items"], *c["fams"]}
    who = {owner, *chain}
    for p in posts:
        if p["lane"] in who and p["tag"] in ("RESULT", "ACK") and p["t"] > after and any(t and t in p["text"] for t in toks):
            return True
    return False


def run(coord, state_f, post_sh, window_h=3.0, live_h=3.0, ack_min=30, dry=False, now=None, poster=None):
    coord = Path(coord)
    now = time.time() if now is None else now
    qtext = (coord / "lanes/COORD-REVIEW-QUEUE.md").read_text(errors="replace")
    ptexts = [f.read_text(errors="replace") for f in sorted((coord / "lanes/posts").glob("*.md"))]
    posts = parse_posts(qtext + "\n" + "\n".join(ptexts))
    try:
        kw = json.loads((coord / "autopilot/kit_wave_state.json").read_text())
    except (OSError, ValueError):
        kw = {}
    try:
        st = json.loads(Path(state_f).read_text())
        assert isinstance(st.get("classes"), dict)
    except (OSError, ValueError, AssertionError, AttributeError):
        st = {"classes": {}}
    status = lane_status(coord)
    classes = build_classes(coord, kw, posts, now, window_h, live_h, status)
    sent = []
    fail = []
    by_cid = {}
    for k, v in st["classes"].items():                 # FLOW-OPS-0900: one record per class id, whatever owner it was filed under
        cid = k.rsplit("|", 1)[-1]
        if cid not in by_cid or v.get("t", 0) >= by_cid[cid][1].get("t", 0):
            by_cid[cid] = (k, v)

    def do_post(text):
        if dry:
            print("DRY", text)
            return True
        return (poster or _post)(post_sh, text)

    for ckey, c in sorted(classes.items(), key=lambda kv: -len(kv[1]["items"])):
        prev_k, prev = by_cid.get(c["cid"], (None, None))
        prev_owner = prev_k.rsplit("|", 1)[0] if prev_k else ""
        if prev and prev_owner != c["owner"] and stood_down(prev_owner, status):
            succ = live_end(prev_owner, status)
            if succ and succ != prev_owner:
                c["owner"] = succ                      # the class stays with the successor of the lane that had it, not a new pick
        rec_k = f"{c['owner']}|{c['cid']}"
        rec = st["classes"].get(rec_k, {})
        if not rec and prev and prev_k != rec_k:      # HANDOVER: carry the record (first seen, ack / NEEDS-LANE flags, owner chain) to the new owner
            chain = list(prev.get("owners") or [prev_owner])
            rec = dict(prev, owners=chain + [c["owner"]], handover=int(now), t_owner=now)
            st["classes"].pop(prev_k, None)
            st["classes"][rec_k] = rec
            by_cid[c["cid"]] = (rec_k, rec)
            if not rec.get("acked"):
                age = int((now - rec.get("t", now)) / 60)
                text = (f"HANDOVER [{LANE} -> {c['owner']}] FAIL-CLASS {c['cid']} owner {c['owner']} {c['label']}: open {age} min, owner chain "
                        f"{' > '.join(rec['owners'])}: {names_line(c)}. You inherit this class from {prev_owner}: post RESULT or ACK naming {c['cid']} "
                        f"within {ack_min} min." + (" NEEDS-LANE already went to COORD; no second one." if rec.get("lane_posted") else ""))
                if not do_post(text):
                    fail.append(c["cid"])
                else:
                    sent.append(("HANDOVER", c["cid"], c["owner"], len(c["items"])))
            continue
        in_q = re.search(r"FAIL-CLASS %s owner %s\b" % (c["cid"], re.escape(c["owner"])), qtext)
        if not rec and in_q:                       # posted earlier, state lost
            tm = [p["t"] for p in posts if p["lane"] == LANE and f"FAIL-CLASS {c['cid']} owner {c['owner']}" in p["text"]]
            rec = {"t": min(tm) if tm else now, "items": sorted(c["items"])}
            st["classes"][rec_k] = rec
        if not rec:
            to = f"{c['owner']}, COORD" if c["owner"] != "COORD" else "COORD"
            text = (f"NEEDS-ACTION [{LANE} -> {to}] FAIL-CLASS {c['cid']} owner {c['owner']} {c['label']}: {len(c['items'])} item(s) "
                    f"failed and not answered: {names_line(c)}{reset_note(kw, c)}. Owner: post RESULT or ACK naming {c['cid']} (or an item) with the "
                    f"cause and the next step within {ack_min} min, else NEEDS-LANE goes to COORD. One post per class; no repeat.")
            if do_post(text):
                st["classes"][rec_k] = {"t": now, "items": sorted(c["items"]), "label": c["label"]}
                sent.append(("ACTION", c["cid"], c["owner"], len(c["items"])))
            else:
                fail.append(c["cid"])
            continue
        if rec.get("lane_posted") or rec.get("acked"):
            continue
        if acked(posts, c["owner"], c, rec["t"], rec.get("owners") or ()):
            rec["acked"] = int(now)
            continue
        if now - rec.get("t_owner", rec["t"]) >= ack_min * 60:
            text = (f"NEEDS-LANE [{LANE} -> COORD] FAIL-CLASS {c['cid']} {c['label']}: {len(c['items'])} item(s), no RESULT/ACK from "
                    f"{c['owner']} in {int((now - rec['t']) / 60)} min: {names_line(c)}. COORD: start or assign a lane for this class; "
                    f"this relay does not repeat (class {c['cid']}).")
            if do_post(text):
                rec["lane_posted"] = int(now)
                sent.append(("LANE", c["cid"], c["owner"], len(c["items"])))
            else:
                fail.append(c["cid"])
    keep = now - 7 * 86400
    st["classes"] = {k: v for k, v in st["classes"].items() if v.get("t", now) > keep}
    if not dry:
        p = Path(state_f)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + f".tmp{os.getpid()}")
        tmp.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, p)
    return sent, fail, classes


def _post(post_sh, text):
    try:
        r = subprocess.run(["bash", str(post_sh), LANE, text], capture_output=True, text=True, timeout=120, cwd="/")
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"post failed: {e}", file=sys.stderr)
        return False
    if r.returncode != 0:
        print(f"post.sh rc {r.returncode}: {r.stderr.strip()[-300:]}", file=sys.stderr)
    return r.returncode == 0


def open_relays(state_f, lane):
    """[(cid, rec)] classes filed under LANE that are not acked (bin/stand-down.sh OPEN-RELAYS block)"""
    try:
        st = json.loads(Path(state_f).read_text()).get("classes") or {}
    except (OSError, ValueError, AttributeError):
        return []
    out = [(k.rsplit("|", 1)[-1], v) for k, v in st.items() if k.rsplit("|", 1)[0] == lane and not v.get("acked")]
    return sorted(out, key=lambda kv: kv[1].get("t", 0))


def open_relays_text(state_f, lane, now=None):
    now = time.time() if now is None else now
    out = []
    for cid, v in open_relays(state_f, lane):
        its = v.get("items") or []
        out.append(f"- FAIL-CLASS {cid} {v.get('label', '')}: open {int((now - v.get('t', now)) / 60)} min, {len(its)} item(s): "
                   f"{', '.join(its[:MAX_NAMES])}{', +%d more' % (len(its) - MAX_NAMES) if len(its) > MAX_NAMES else ''}"
                   f"; owner chain {' > '.join(v.get('owners') or [lane])}{'; NEEDS-LANE posted' if v.get('lane_posted') else ''}")
    return "\n".join(out)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv[:1] == ["--open-relays"] and len(argv) >= 2:
        sf = argv[argv.index("--state") + 1] if "--state" in argv else str(HOME / ".local/state/fail-route.json")
        t = open_relays_text(sf, argv[1])
        if t:
            print(t)
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--coord", default=str(HOME / "coord"))
    ap.add_argument("--state", default=str(HOME / ".local/state/fail-route.json"))
    ap.add_argument("--post-sh", default=str(HOME / "coord/bin/post.sh"))
    ap.add_argument("--window-h", type=float, default=3.0)
    ap.add_argument("--live-h", type=float, default=3.0)
    ap.add_argument("--ack-min", type=int, default=30)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    try:
        sent, fail, classes = run(a.coord, a.state, a.post_sh, a.window_h, a.live_h, a.ack_min, a.dry)
    except OSError as e:
        print(f"fail_route: {e}", file=sys.stderr)
        return 2
    print(f"fail_route: classes={len(classes)} posted={len(sent)} post_failed={len(fail)}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
