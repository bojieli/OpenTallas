#!/usr/bin/env python3
"""loopgaps.py -- LOOP-GAP detection for the AUTOPILOT tick (owner 2026-10-25: the design -> review -> route -> review ->
design loop must never sit idle).  Read-only: it parses coordination files and the autopilot state and returns gap lines;
autopilot.py writes them to ~/coord/autopilot/LOOP-GAPS.txt (overwritten each tick, oldest first) and uses
geom_verdicts() to submit a queued kit within one tick of its GEOM PASS (the only action, done by autopilot.py).

Gaps:
  (1) GEOM-REQ-UNANSWERED    a GEOM REQ in lanes/GEOM-REVIEW.md with no REPLY / VERDICT / ACK of its tag after 20 min
  (2) GEOM-PASS-NOT-ROUTED   a GEOM PASS / PASS-COND reply that clears a route, with no autopilot submit of a kit under
                             that tag after 20 min (queued kits are submitted by the tick itself), unless coord/state
                             autopilot/resolved.tsv carries that verdict (tag + verdict time): its kits were signed off,
                             superseded, routed outside the autopilot or the reply is not a route clearance
  (3) RUN-NOT-CLASSIFIED     an autopilot run whose client / render ended but is still unclassified after one tick
  (4) REVIEW-NO-ACTION       a review.tsv / structural.tsv row with no GEOM REQ or fix line (naming its type or id) in
                             the owning lane file or GEOM-REVIEW.md after 60 min
  (5) READY-NO-COORD         a READY line in lanes/COORD-REVIEW-QUEUE.md with no later COORD line naming its branch or sha
                             after 30 min
  (6) HOST-IDLE              a fleet host admitting > 100 GB at load < 60 % of its cores while the autopilot queue has
                             nothing waiting
  (7) UNOWNED-ITEM           (ownership.py) a release-plan partition type / hard core, not SIGNED, with no live job and
                             no lane activity for > 60 min, grouped per die + owner lane; the OWNERSHIP summary
                             ('#' lines) heads the file and the full table is autopilot/OWNERS.tsv
"""
import re
import time

TS = re.compile(r"(20\d\d-\d\d-\d\d) (\d\d:\d\d)(?::\d\d)?")
HHMM = re.compile(r"\b(\d\d:\d\d)\b")
REQ_RE = re.compile(r"GEOM REQ\s*(?:\[([^\]]+)\]|\(([^)]+)\))")
REPLY_RE = re.compile(r"(?:REPLY|VERDICT|ACK)\s*\[([^\]]+)\]")
VERDICT_WORD = re.compile(r"\b(PASS-COND|PASS|FAIL)\b")
ROUTE_OK = re.compile(r"route|P&R", re.I)
WINDOW_S = 24 * 3600


def parse_ts(line, default=None):
    m = TS.search(line)
    if not m:
        return default
    try:
        return time.mktime(time.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M"))
    except ValueError:
        return default


def tag_of(s):
    """Keep the full review identity, including batch/variant words; remove only dates/times."""
    s = TS.sub("", s)
    s = HHMM.sub("", s)
    s = re.sub(r"\b(?:PDT|PST)\b", "", s)
    return re.sub(r"\s+", " ", s).strip(" ,;+ ")


def geom_events(text):
    """Parse complete review entries, including their indented kit/verdict lists."""
    reqs, reps, last_t = [], [], None
    entries = []
    for line in text.splitlines():
        if line[:1].isspace() and entries and parse_ts(line) is None:
            entries[-1] += " " + line.strip()
        else:
            entries.append(line)
    for line in entries:
        t = parse_ts(line, None)
        if t is not None:
            last_t = t
        m = REQ_RE.search(line)
        if m and "REPLY" not in line[:m.start()]:
            reqs.append((t or last_t, tag_of(m.group(1) or m.group(2)), line))
            continue
        m = REPLY_RE.search(line)
        if m:
            v = VERDICT_WORD.search(line[m.end():])
            reps.append((t or last_t, tag_of(m.group(1)), v.group(1) if v else None, line))
    return reqs, reps


def _names(line, kit_type, sha):
    suf = kit_type.split("__")[-1]
    return (kit_type in line or re.search(r"(?<![\w])" + re.escape(suf) + r"(?![\w])", line) is not None or
            bool(sha and sha[:9] in line))


def _verdict_for(line, start, kit_type, sha):
    """verdict word for this kit in a reply line: the one in the clause that names the kit (FAIL when that clause
    mixes FAIL with a PASS word), else the line's only verdict word; None when the line mixes verdicts and no clause
    names the kit (ambiguous -> no automatic action)"""
    tail = line[start:]
    for seg in re.split(r";|\||\.\s", tail):
        if _names(seg, kit_type, sha):
            words = {m.group(1) for m in VERDICT_WORD.finditer(seg)}
            if len(words) == 1:
                return words.pop()
            if "FAIL" in words:
                return "FAIL"                             # 'FAIL (corrects my PASS-COND)', 'PASS for one, FAIL for
                                                          # the other': fail-safe, never leaves a PASS standing
            if words:
                return None                               # PASS vs PASS-COND mix: ambiguous, earlier verdict stands
    words = {m.group(1) for m in VERDICT_WORD.finditer(tail)}
    return words.pop() if len(words) == 1 else None


def geom_verdicts(text, tag, kit_type, sha):
    """GEOM verdict (PASS / PASS-COND / FAIL, time, line) for one queued kit: a REPLY/VERDICT of the tag that names the
    kit (type, its __suffix or the src sha), given at or after the latest GEOM REQ of that tag (the one naming the kit if
    any) -- an older verdict for an earlier kit of the same name never counts.  None if there is none."""
    reqs, reps = geom_events(text)
    want = tag_of(tag)
    rq = [t for t, rt, line in reqs if rt == want and t is not None]
    rq_named = [t for t, rt, line in reqs if rt == want and t is not None and _names(line, kit_type, sha)]
    if not rq:
        return None
    req_t = max(rq_named or rq)
    best = None
    for t, rtag, v, line in reps:
        if not v or rtag != want or t is None or t < req_t or not _names(line, kit_type, sha):
            continue
        m = REPLY_RE.search(line)
        vv = _verdict_for(line, m.end(), kit_type, sha)
        if vv and (best is None or t >= best[1]):
            best = (vv, t, line)
    return best


def _answers(tag, req_line, rtag, rep_line):
    """gap (1) only (never used to submit): same tag, or the same tag family ('QC-CQB' / 'QC ...') with the reply naming
    a kit token of the REQ"""
    if rtag == tag:
        return True
    fam = lambda x: re.split(r"[-/\s]", x)[0]
    if fam(rtag) != fam(tag):
        return False
    toks = {w for w in re.findall(r"[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+", req_line) if len(w) >= 6}
    return any(w in rep_line for w in toks)


RESOLVED_HEAD = "# tag\tverdict_time (YYYY-MM-DD HH:MM of the REPLY line)\tresolution\tkits\tlane\trecorded\tnote"


def parse_resolved(text):
    """coord/state autopilot/resolved.tsv -> {(tag, verdict epoch)}: GEOM PASS verdicts whose kits need no autopilot
    submit (SIGNED / SUPERSEDED / ROUTED by hand / NOT-ROUTE); gap (2) stops flagging exactly that verdict, so a later
    PASS under the same tag is still flagged"""
    out = set()
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        f = raw.split("\t")
        if len(f) < 3 or not f[2].strip():
            continue                                       # a resolution is required
        t = parse_ts(f[1], None)
        if t is not None and tag_of(f[0]):
            out.add((tag_of(f[0]), t))
    return out


def gaps_geom(text, now, queue_tags_submitted, resolved=frozenset()):
    out = []
    reqs, reps = geom_events(text)
    for t, tag, line in reqs:
        if t is None or now - t > WINDOW_S or now - t < 20 * 60:
            continue
        if not any((rtime or 0) >= t and _answers(tag, line, rt, rline) for rtime, rt, _, rline in reps):
            out.append((t, f"GEOM-REQ-UNANSWERED [{tag}] {line.strip()[:160]}"))
    for t, tag, v, line in reps:
        if v not in ("PASS", "PASS-COND") or t is None or now - t > WINDOW_S or now - t < 20 * 60:
            continue
        tail = line[line.find(v):]
        if not ROUTE_OK.search(tail) or re.search(r"\bno (new )?(route|P&R)\b|not for route", tail, re.I):
            continue
        if tag not in queue_tags_submitted and (tag, t) not in resolved:
            out.append((t, f"GEOM-PASS-NOT-ROUTED [{tag}] {v}: no autopilot submit under this tag (if the lane routed "
                           f"it by hand, enqueue it next time: tools/autopilot/enqueue.py; signed / superseded: "
                           f"autopilot/resolved.tsv) -- {line.strip()[:140]}"))
    return out


def gaps_ready(text, now):
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("READY"):
            continue
        t = parse_ts(line)
        if t is None or now - t > WINDOW_S or now - t < 30 * 60:
            continue
        m = re.search(r"\]\s*([\w./-]+)@([0-9a-f]{7,40})", line)
        if not m:
            continue
        br, sha = m.group(1), m.group(2)
        later = [l for l in lines[i + 1:] if "COORD" in l[:40] and (br in l or sha[:9] in l)]
        if not later:
            out.append((t, f"READY-NO-COORD {br}@{sha[:10]} {line.strip()[:140]}"))
    return out


def gaps_review(rows, lane_texts, geom_text, now):
    """rows: dicts with time (epoch), id, type, lane, file; lane_texts {LANE: text or None}"""
    out = []
    for r in rows:
        t = r["t"]
        if t is None or now - t > 2 * WINDOW_S or now - t < 60 * 60:
            continue
        lane = r.get("lane") or ""
        txt = (lane_texts.get(lane) or "") + "\n" + geom_text
        hit = False
        for line in txt.splitlines():
            lt = parse_ts(line)
            if lt is not None and lt >= t - 60 and (r["type"] in line or r["id"] in line):
                hit = True
                break
        if not hit:
            miss = "" if lane_texts.get(lane) is not None else f" (no lane file lanes/{lane}.md)"
            out.append((t, f"REVIEW-NO-ACTION {r['file']} {r['id']} {r['type']} lane {lane or '?'}{miss}: no GEOM REQ "
                           f"or fix line naming it"))
    return out


def gaps_runs(jobs, now, tick_s=600):
    out = []
    for j in jobs:
        st = j.get("status", "")
        if st in ("RUNNING", "ORPHAN") and j.get("client_done_at") and now - j["client_done_at"] > tick_s:
            out.append((j["client_done_at"], f"RUN-NOT-CLASSIFIED {j['id']} {j.get('die')}/{j.get('type')} {st}: client "
                                             f"ended, still unclassified ({j.get('kit')})"))
        if st.startswith("REVIEW-") and j.get("review_done_at") and now - j["review_done_at"] > tick_s:
            out.append((j["review_done_at"], f"RUN-NOT-CLASSIFIED {j['id']} {st}: render ended, not recorded"))
        if st == "SIGNED" and now - j.get("updated", now) > tick_s:
            out.append((j.get("updated", now), f"RUN-NOT-CLASSIFIED {j['id']} SIGNED but archive pending"))
    return out


STATUS_RE = re.compile(r"(\S+) admits (-?\d+) GB .*? load (\d+)/(\d+)")


def gaps_hosts(status_text, queue_waiting, now):
    if queue_waiting:
        return []
    out = []
    for part in status_text.split("|"):
        m = STATUS_RE.search(part)
        if m:
            h, adm, load, cores = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
            h = "epyc1" if h == "localhost" else h                # ot-run --status runs on the hub
            if adm > 100 and load < 0.6 * cores:
                out.append((now, f"HOST-IDLE {h} admits {adm} GB at load {load}/{cores} and nothing waits in the autopilot queue"))
    return out


def render(gaps, now, head=()):
    lines = [f"# LOOP-GAPS -- autopilot tick {time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(now))} "
             f"(read-only; oldest first; age = since the event)"] + list(head)
    for t, msg in sorted(gaps, key=lambda g: g[0]):
        age = max(0, now - t) / 60
        lines.append(f"{age / 60:6.1f} h  {msg}" if age >= 120 else f"{age:6.0f} m  {msg}")
    if not gaps:
        lines.append("no gaps")
    return "\n".join(lines) + "\n"
