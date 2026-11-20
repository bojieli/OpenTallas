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

usage: fail_route.py [--coord DIR] [--state F] [--post-sh F] [--window-h H] [--live-h H] [--ack-min N] [--dry]
"""
import argparse
import hashlib
import json
import os
import re
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
# FABLE-FLOW-0555 I: a RESULT of a triage / review / census lane is a table about failures, not a failure of that lane's own job
TABLE_LANES = re.compile(r"TRIAGE|REVIEW|CENSUS|AUDIT|SWEEP|SCAN")
VERDICT_AT = 60                      # the verdict word must start the RESULT text (the waiter_fail_relay filter), not appear deep inside a table
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


def live_lanes(posts, now, live_h):
    """lane -> (last post epoch) for lanes that posted within live_h hours; reviewers and infra lanes are not owners."""
    last = {}
    for p in posts:
        if p["lane"].startswith(NOT_OWNER) and not p["lane"].startswith(OWNER_OK):
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
        # FABLE-FLOW-0445 #6: self-closing class: a later attempt of the item (queued, running, enqueued or signed) means the failure is answered
        moved = [x for kk, x in items.items() if "|".join(kk.split("|")[:2]) == k and x.get("status") not in LIVE_STATUS
                 and float(x.get("updated") or 0) > float(v.get("last") or 0) + 60]
        if moved:
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


def build_classes(coord, state, posts, now, window_h, live_h):
    """{class key: dict(die, kind, owner, items{name: epoch}, label)}"""
    live = live_lanes(posts, now, live_h)
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
        if p["tag"] != "RESULT" or p["lane"].startswith(NOT_OWNER) or TABLE_LANES.search(p["lane"]) or now - p["t"] > window_h * 3600:
            continue
        if not VERDICT.search(p["text"][:VERDICT_AT]):
            continue
        die = waiter_die(p["lane"], p["text"])
        name = f"{p['lane']}@{p['stamp'][11:]}"
        add(die, "waiter", f"{die}/waiter RESULT FAIL", name, p["lane"], p["t"], f"waiter|{die}")
    for ckey, c in classes.items():
        fam = sorted(c["fams"])[0] if len(c["fams"]) == 1 else None
        c["owner"] = c.get("forced") or pick_owner(c["die"], fam, live, posts, now, live_h)
        c["cid"] = cid_of(ckey)
    return classes


def reset_evidence(state, die, item):
    """Locate the exact failed attempt recorded by fail_sigs; a later attempt can use another bind."""
    sig = (state.get("fail_sigs") or {}).get(f"{die}|{item}") or {}
    if sig.get("stage") != "gen" or "physical collector_tree differs from captured bound reset identity" not in sig.get("reason", ""):
        return ""
    attempts = sig.get("attempts") or []
    if not attempts or not sig.get("block"):
        return ""
    event, _, number = str(attempts[-1]).rpartition("@")
    if not event or not number.isdigit():
        return ""
    for row in (state.get("items") or {}).values():
        if (row.get("die"), row.get("item"), row.get("block_sha")) != (die, item, sig["block"]) or not row.get("dir"):
            continue
        attempt = Path(row["dir"]).parent / ("a" + number)
        try:
            spec = json.loads((attempt / "spec.json").read_text())
            if not isinstance(spec, dict) or (spec.get("die"), spec.get("item"), spec.get("event")) != (die, item, event):
                continue
            log = attempt / "gen.log"
            with log.open(errors="replace") as f:
                line = next((s for s in f if s.startswith("gen phys: RESET_IDENTITY ")), "")
        except (OSError, ValueError):
            continue
        # Historical workers report the original refusal only; leave their graph quantities unknown.
        tag = spec.get("gen_tools_manifest_sha") or spec.get("tools_sha") or ""
        basis = "source manifest" if spec.get("gen_tools_manifest_sha") else "runtime"
        pin = f", GEN {basis} {tag[:12]}" if tag else ""
        context = f". Representative {item} {event}@{number}{pin}, {log}"
        if line:
            try:
                d = json.loads(line.removeprefix("gen phys: RESET_IDENTITY "))
                if d["type"] == item and "solved" in d:
                    a, b = d["captured"], d["solved"]
                    context += (f" (captured/solved reach {a['reach_um']}/{b['reach_um']} um, "
                                f"max hop {a['max_hop_um']}/{b['max_hop_um']} um, "
                                f"depth {a['depth']}/{b['depth']}, relays {a['relays']}/{b['relays']})")
                    relay = d.get("first_changed_relay")
                    if isinstance(relay, dict) and isinstance(relay.get("name"), str):
                        context += f", first changed relay {relay['name']}"
                elif d["type"] == item and d.get("solve_error"):
                    context += " (solver error: " + str(d["solve_error"]).replace("\n", " ")[:180] + ")"
            except (TypeError, ValueError, KeyError):
                pass
        return context
    return ""


def names_line(c):
    ns = sorted(c["items"], key=lambda n: -c["items"][n])
    s = ", ".join(ns[:MAX_NAMES])
    return s + (f", +{len(ns) - MAX_NAMES} more" if len(ns) > MAX_NAMES else "")


def coord_closed(posts, c, after):
    """FABLE-FLOW-0555 I: a COORD RULING / ACK / RESULT after the first post that names the class id, the class label (its key) or one of its items closes the class
    for every owner."""
    names = {c["cid"], c.get("label", "").split(" ")[0] if c.get("label") else "", *c["items"]}
    for p in posts:
        if p["lane"] == "COORD" and p["tag"] in ("RULING", "RESULT", "ACK") and p["t"] > after and any(n and n in p["text"] for n in names if len(n) >= 6):
            return True
    return False


def find_rec(st, c):
    """the state record of a class by its id, whoever the owner was when it was posted (the owner flips with lane liveness: 6 posts to 4 lanes for one class)"""
    for k in (f"{c['owner']}|{c['cid']}", c["cid"]):
        if k in st["classes"]:
            return k, st["classes"][k]
    for k, v in st["classes"].items():
        if k.endswith("|" + c["cid"]):
            return k, v
    return c["cid"], {}


def acked(posts, owner, c, after):
    """a RESULT or ACK from the owner after `after` that names the class id, an item or an item family."""
    toks = {c["cid"], *c["items"], *c["fams"]}
    if coord_closed(posts, c, after):
        return True
    for p in posts:
        if p["lane"] == owner and p["tag"] in ("RESULT", "ACK") and p["t"] > after and any(t and t in p["text"] for t in toks):
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
    classes = build_classes(coord, kw, posts, now, window_h, live_h)
    sent = []
    fail = []
    digest = {}       # owner -> [(rec_k, class)] new classes of this run: ONE post per owner per run (FABLE-FLOW-0445 #6)
    lane_digest = []  # classes past the ack window of this run: ONE NEEDS-LANE to COORD

    def do_post(text):
        if dry:
            print("DRY", text)
            return True
        return (poster or _post)(post_sh, text)

    for ckey, c in sorted(classes.items(), key=lambda kv: -len(kv[1]["items"])):
        rec_k, rec = find_rec(st, c)
        if c["cid"] in st.setdefault("closed", {}):
            continue
        if rec and coord_closed(posts, c, rec.get("t", 0)):          # a COORD RULING / ACK names it: closed for good, whoever owns it now
            st["closed"][c["cid"]] = int(now)
            continue
        in_q = re.search(r"FAIL-CLASS %s\b" % c["cid"], qtext)
        if not rec and in_q:                       # posted earlier, state lost
            tm = [p["t"] for p in posts if p["lane"] == LANE and f"FAIL-CLASS {c['cid']} owner {c['owner']}" in p["text"]]
            rec = {"t": min(tm) if tm else now, "items": sorted(c["items"])}
            st["classes"][rec_k] = rec
        if not rec:
            digest.setdefault(c["owner"], []).append((rec_k, c))
            continue
        if rec.get("lane_posted") or rec.get("acked"):
            continue
        if acked(posts, c["owner"], c, rec["t"]):
            rec["acked"] = int(now)
            continue
        if now - rec["t"] >= ack_min * 60:
            lane_digest.append((rec, c))
    for owner, lst in sorted(digest.items()):
        to = f"{owner}, COORD" if owner != "COORD" else "COORD"
        segments = []
        for _, c in lst:
            rep = max(c["items"], key=c["items"].get)
            evidence = reset_evidence(kw, c["die"], rep) if c["kind"] == "kit" else ""
            segments.append(f"FAIL-CLASS {c['cid']} owner {owner} {c['label']}: {len(c['items'])} item(s): {names_line(c)}{evidence}")
        segs = " | ".join(segments)
        text = (f"NEEDS-ACTION [{LANE} -> {to}] {len(lst)} failed class(es), {sum(len(c['items']) for _, c in lst)} item(s) not answered: {segs}. "
                f"Owner: post RESULT or ACK naming a class id (or an item) with the cause and the next step within {ack_min} min, else NEEDS-LANE goes to "
                f"COORD. One digest per owner per run; a class closes by itself when its items have a later attempt, or when COORD names its id.")
        if do_post(text):
            for rec_k, c in lst:
                st["classes"][rec_k] = {"t": now, "items": sorted(c["items"]), "label": c["label"]}
                sent.append(("ACTION", c["cid"], owner, len(c["items"])))
        else:
            fail.extend(c["cid"] for _, c in lst)
    if lane_digest:
        segs = " | ".join(f"FAIL-CLASS {c['cid']} {c['label']}: {len(c['items'])} item(s), no RESULT/ACK from {c['owner']} in "
                          f"{int((now - rec['t']) / 60)} min: {names_line(c)}" for rec, c in lane_digest)
        text = (f"NEEDS-LANE [{LANE} -> COORD] {len(lane_digest)} failed class(es) unanswered: {segs}. COORD: start or assign a lane for each; "
                f"this relay does not repeat these classes.")
        if do_post(text):
            for rec, c in lane_digest:
                rec["lane_posted"] = int(now)
                sent.append(("LANE", c["cid"], c["owner"], len(c["items"])))
        else:
            fail.extend(c["cid"] for _, c in lane_digest)
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


def main(argv=None):
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
