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
  (8) AMBIGUOUS-GEOM         a REPLY under a tag shared by several queued rows names none of them by type / kit dir /
                             row id, only a token they share (the branch sha): no verdict is applied to any of them
"""
import re
import time

TS = re.compile(r"(20\d\d-\d\d-\d\d) (\d\d:\d\d)(?::\d\d)?")
HHMM = re.compile(r"\b(\d\d:\d\d)\b")
REQ_RE = re.compile(r"GEOM REQ\s*(?:\[([^\]]+)\]|\(([^)]+)\))")
REPLY_RE = re.compile(r"(?:REPLY|VERDICT|ACK|RECONCILE|AMEND)\s*\[([^\]]+)\]")
WITHDRAW = re.compile(r"\bwithdr[ae]w", re.I)   # 'This WITHDRAWS my 06:59 route PASS-COND' reads FAIL
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


def geom_events(text, keep_lines=False):
    """Parse complete review entries, including their indented kit/verdict lists (joined with ' ', or with '\\n' when
    keep_lines: geom_verdicts reads which physical line names a kit).  A RECONCILE / AMEND [tag] counts as a reply; an
    entry that withdraws a verdict reads FAIL."""
    reqs, reps, last_t = [], [], None
    entries = []
    for line in text.splitlines():
        if line[:1].isspace() and entries and parse_ts(line) is None:
            entries[-1] += ("\n" if keep_lines else " ") + line.strip()
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
            v = "FAIL" if WITHDRAW.search(line[m.end():]) else v.group(1) if v else None
            reps.append((t or last_t, tag_of(m.group(1)), v, line))
    return reqs, reps


GENERIC_KIT_DIRS = {"kit", "kits", "run", "runs", "flow", "work"}


def kit_tokens(kit_type, kit="", sha="", rid=""):
    """(strong, weak) identity tokens of one queued kit.  strong = its type, its kit dir basename, its autopilot row id
    (kit hash): each always names the kit.  weak = the type's __suffix and the src sha: they name the kit only when no
    other queued row under the same GEOM tag shares them (2026-10-25: btab_s7 + prog_s7 share @90bf56dfa and the
    suffix 's7', so a PASS-COND for btab_s7 quoting the branch sha would also have cleared prog_s7)."""
    strong = {kit_type} if kit_type else set()
    parts = [x for x in (kit or "").split(":")[-1].split("/") if x]
    while parts and parts[-1] in GENERIC_KIT_DIRS:
        parts.pop()
    if parts and len(parts[-1]) >= 5:
        strong.add(parts[-1])
    for name in (kit_type, parts[-1] if parts else ""):
        h = re.search(r"_([0-9a-f]{8,40})$", name or "")
        if h:
            strong.add(h.group(1))                        # kit hash in the type / dir name (HBM-KITS ..._324c16535028)
    if rid:
        strong.add(rid)
    weak = set()
    suf = kit_type.split("__")[-1] if kit_type else ""
    if suf and suf != kit_type:
        weak.add(suf)
    if sha:
        weak.add(sha[:9])
    return strong, weak


def _hit(tok, s):
    if re.fullmatch(r"[0-9a-f]{7,40}", tok):
        return tok in s                                   # shas are quoted inside branch@sha
    return re.search(r"(?<![\w])" + re.escape(tok) + r"(?![\w])", s) is not None


class KitIdent:
    """one queued row's identity inside its GEOM tag group; others = (kit_type, kit, sha, rid) of the other queued rows
    under the same tag"""

    def __init__(self, kit_type, kit="", sha="", rid="", others=()):
        self.kit_type = kit_type
        self.strong, weak = kit_tokens(kit_type, kit, sha, rid)
        shared = set()
        for o in others:
            if o[0] == kit_type:
                continue                                  # variants of one type: one verdict covers them (as before)
            s2, w2 = kit_tokens(*o)
            shared |= s2 | w2
        self.weak = weak - shared
        self.weak_shared = weak & shared

    def names(self, s):
        return any(_hit(t, s) for t in self.strong) or any(_hit(t, s) for t in self.weak)

    def shared_only(self, s):
        """s names this kit only through a token another row of the tag shares (the branch sha, a common suffix)"""
        return not self.names(s) and any(_hit(t, s) for t in self.weak_shared)


def _group_idents(kit_type, sha, kit="", rid="", others=()):
    allk = [(kit_type, kit, sha, rid)] + [tuple(o) for o in others]
    return [KitIdent(*a, others=allk[:i] + allk[i + 1:]) for i, a in enumerate(allk)]


def _names(line, kit_type, sha):
    """single-row form (no other queued row under the tag): type, its __suffix or the src sha"""
    return KitIdent(kit_type, "", sha).names(line)


def _words(seg):
    w = {m.group(1) for m in VERDICT_WORD.finditer(seg)}
    return w | {"FAIL"} if WITHDRAW.search(seg) else w


def _verdict_for(line, start, names, strict=False):
    """verdict word for this kit in a reply line: the one in the clause that names the kit (FAIL when that clause
    mixes FAIL with a PASS word), else the line's only verdict word; None when the line mixes verdicts and no clause
    names the kit (ambiguous -> no automatic action).  strict (the entry also names a queued row of another type under
    the tag): the lone verdict word counts only from the physical lines that name this kit, never from the entry.  A
    clause that withdraws a verdict reads FAIL."""
    tail = line[start:]
    for seg in re.split(r";|\||\.\s", tail):
        if names(seg):
            words = _words(seg)
            if len(words) == 1:
                return words.pop()
            if "FAIL" in words:
                return "FAIL"                             # 'FAIL (corrects my PASS-COND)', 'PASS for one, FAIL for
                                                          # the other': fail-safe, never leaves a PASS standing
            if words:
                return None                               # PASS vs PASS-COND mix: ambiguous, earlier verdict stands
    if strict:
        tail = "\n".join(pl for pl in tail.split("\n") if names(pl))
    words = _words(tail)
    if "FAIL" in words and len(words) > 1 and WITHDRAW.search(tail):
        return "FAIL"
    return words.pop() if len(words) == 1 else None


def _latest_req(reqs, want, idents=()):
    rq = [t for t, rt, line in reqs if rt == want and t is not None]
    rq_named = [t for t, rt, line in reqs if rt == want and t is not None and idents and idents[0].names(line)]
    return max(rq_named or rq) if rq else None


def geom_verdicts(text, tag, kit_type, sha, kit="", rid="", others=()):
    """GEOM verdict (PASS / PASS-COND / FAIL, time, line) for one queued kit: a REPLY/VERDICT of the tag that names the
    kit, given at or after the latest GEOM REQ of that tag (the one naming the kit if any) -- an older verdict for an
    earlier kit of the same name never counts.  None if there is none.
    Naming: the type, the kit dir basename or the row id always name it; the __suffix or the src sha only when no other
    queued row under the tag (others: (kit_type, kit, sha, rid) tuples) shares them.  Latest verdict wins; a clause
    mixing FAIL with PASS reads FAIL."""
    reqs, reps = geom_events(text, keep_lines=True)
    want = tag_of(tag)
    idents = _group_idents(kit_type, sha, kit, rid, others)
    me = idents[0]
    req_t = _latest_req(reqs, want, idents)
    if req_t is None:
        return None
    best = None
    for t, rtag, v, line in reps:
        if not v or rtag != want or t is None or t < req_t:
            continue
        m = REPLY_RE.search(line)
        if not me.names(line[m.end():]):
            continue
        strict = any(o.kit_type != kit_type and o.names(line[m.end():]) for o in idents[1:])
        vv = _verdict_for(line, m.end(), me.names, strict)
        if vv and (best is None or t >= best[1]):
            best = (vv, t, line.replace("\n", " "))
    return best


def geom_ambiguous(text, tag, group):
    """REPLY/VERDICT lines of a tag shared by several queued rows (group: (kit_type, kit, sha, rid) tuples) that reach
    some of those rows only through a token they share with a row of another type (the branch sha): no verdict is
    applied to those rows, the tick reports AMBIGUOUS-GEOM.  A row stops being reported once a LATER reply of the tag
    names it (type, kit dir basename or row id: the reviewer re-posted per row, so geom_verdicts reads that one).
    -> [(time, line, [types reached only that way])]"""
    if len(group) < 2:
        return []
    reqs, reps = geom_events(text)
    want = tag_of(tag)
    allk = [tuple(g) for g in group]
    idents = [KitIdent(*a, others=allk[:i] + allk[i + 1:]) for i, a in enumerate(allk)]
    req_ts = [_latest_req(reqs, want, [i]) for i in idents]   # each row's own latest REQ, as geom_verdicts reads it
    mine = [(t, line, line[REPLY_RE.search(line).end():]) for t, rtag, v, line in reps
            if v and rtag == want and t is not None]

    def named_later(ident, t):
        return any(t2 > t and ident.names(b2) for t2, _, b2 in mine)

    out = []
    for t, line, body in mine:
        amb = [i.kit_type for i, rt in zip(idents, req_ts)
               if rt is not None and t >= rt and i.shared_only(body) and not named_later(i, t)]
        if amb:
            out.append((t, line, sorted(set(amb))))
    return out


def gaps_geom_ambiguous(text, groups, now):
    """groups {tag: [(kit_type, kit, sha, rid), ...]} -> AMBIGUOUS-GEOM gap lines (24 h window)"""
    out = []
    for tag, group in sorted(groups.items()):
        for t, line, types in geom_ambiguous(text, tag, group):
            if now - t <= WINDOW_S:
                out.append((t, f"AMBIGUOUS-GEOM [{tag}] reply reaches {', '.join(types)[:200]} only through the "
                               f"branch sha / suffix that {len(group)} queued rows of the tag share: NO verdict applied "
                               f"to them -- reviewer: re-post naming each type (or kit dir / row id) -- "
                               f"{line.strip()[:140]}"))
    return out


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
