#!/usr/bin/env python3
"""ownership.py -- OWNERSHIP table for the AUTOPILOT tick (owner question 2026-10-25: does every non-closing partition
still have an owner?  Ownership is per die lane, so a partition type or hard core can sit with no live job and nobody
working on it).  Read-only: pure functions over inputs that autopilot.py gathers; autopilot.py writes
~/coord/autopilot/OWNERS.tsv and puts the summary + UNOWNED-ITEM gaps into LOOP-GAPS.txt.

Items: every partition type and every hard core module of the release-die plans on origin/main
(S81 incl. head, QC, KV, HBM B2n -- DIES below).  One row per item:
  die  item  kind  state  owner  live_job  last_activity  next_step  evidence
State (first rule that applies):
  SIGNED           a SIGNED signoff record matches the item (release tree cache: per-plan signed lists + the fleet
                   signed_records matched with the cache's own rule, rec_keys) or an autopilot run of it signed off
  ROUTING          a live autopilot run of the item, or a live ot-run client on the hub naming it with a route /
                   finish goal (other live clients -- G2 probes, placements -- fill live_job but keep the state)
  else the LATEST of these events:
    REVIEW         a review.tsv / structural.tsv row (routed failure) with no lane line naming the item after it
    FIX            the same with a lane line naming the item after it, or a GEOM-REVIEW FAIL for the item
    GEOM-REQ       a GEOM REQ naming the item with no REPLY/VERDICT naming it after it, or a queued autopilot kit
                   waiting for its verdict (WAIT-GEOM)
    KIT-PLACED     a GEOM PASS / PASS-COND naming the item (kit placed, not routed yet)
  else PLAN-STRUCTURAL  PROTO (results/proto_1025 geom FAIL or G2 STRUCTURAL) or the cache's G0C bad types name it
  else NEEDS-KIT
Owner: lane of a live autopilot run > lane of its latest autopilot run / review row (24 h) > lane file (lanes/<LANE>.md)
with the latest line naming the item (24 h) > default lane of the die (default_owner(); also its own column).
Last activity: latest of live job (now), any coord line naming the item (lane files incl. GEOM-REVIEW),
review/structural rows, autopilot run updates.
Gap UNOWNED-ITEM: not SIGNED, no live job, last activity > 60 min ago (or none) -- grouped per die + DEFAULT owner
(the lane expected to pick it up), each item tagged with the last lane that touched it.

Names: an item is named by its type key, its module, and a few spellings used by the kit tools (ot_s81hd_X -> hd_X, a
hard core's _cv suffix dropped).  A text token names the item when one of those is the token or a prefix of it ending
at '_' / '.' (longest wins: kv3_hg_v2 is never kv3_hg); leading part_/kl_/kr_/dp_ are dropped
(G2 gen dirs, signoff names).
"""
import json
import re
import time

import loopgaps as LG

# (die key used in OWNERS.tsv / autopilot queue, plan dir under physical/die_plan, PROTO die name)
DIES = [("s81", "s81", "s81"), ("s81_head", "s81_head", "s81_head"), ("qwen_compute", "qwen_compute", "qwen_compute"),
        ("qwen_kvsys", "qwen_kvsys", "qwen_kvsys"), ("hbm", "hbm_arch/B2n", "B2n")]
STATES = ["PLAN-STRUCTURAL", "NEEDS-KIT", "KIT-PLACED", "GEOM-REQ", "ROUTING", "REVIEW", "FIX", "SIGNED"]
UNOWNED_S = 60 * 60
OWNER_WINDOW_S = 24 * 3600
NOT_LANES = re.compile(r"^(_|GEOM-REVIEW|COORD-REVIEW-QUEUE|AUTOPILOT|ROOT-MERGE)")
TS = re.compile(r"(20\d\d-\d\d-\d\d) (\d\d:\d\d)(?::\d\d)?")
TOKEN = re.compile(r"[A-Za-z0-9_.]+")
LEAD = re.compile(r"^(?:part_|kl_|kr_|dp_)")
VERDICT = re.compile(r"\b(PASS-COND|PASS|FAIL)\b")
REQ_RE = re.compile(r"GEOM REQ\s*(?:\[([^\]]+)\]|\(([^)]+)\))")
REPLY_RE = re.compile(r"(?:REPLY|VERDICT|ACK)\s*\[([^\]]+)\]")
NOT_KIT = re.compile(r"skeleton|prototype|G2 (?:probe|sweep)|die plan @|plan delta", re.I)
PROBE_ARGS = re.compile(r"/gen/|grt_probe|proto_sweep|g2_probe|/probe")
NEXT = {
    "PLAN-STRUCTURAL": "plan fix (per-die delta in lanes/COORD-REVIEW-QUEUE.md), then kit",
    "NEEDS-KIT": "kit it, GEOM REQ, enqueue --geom REQ (tools/autopilot/enqueue.py)",
    "KIT-PLACED": "enqueue the PASS kit (tools/autopilot/enqueue.py); the tick submits it",
    "GEOM-REQ": "GEOM-REVIEW verdict owed",
    "ROUTING": "wait: the autopilot classifies the run",
    "REVIEW": "visual review of the bundle, structural fix, GEOM REQ",
    "FIX": "structural fix -> GEOM REQ -> rebuild",
    "SIGNED": "-",
}


def parse_ts(line):
    m = TS.search(line)
    if not m:
        return None
    try:
        return time.mktime(time.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M"))
    except ValueError:
        return None


def default_owner(die, kind, item):
    if die == "s81":
        return "S81-CORES" if kind == "core" else "S81-PLAN"
    if die == "s81_head":
        return "S81-HEAD"
    if die == "qwen_compute":
        return "QC-CQB" if ("cqb" in item or item == "qfd_dv_s8x_vmr") else "QC-PLAN"   # cqb = the vmr core's kit
    if die == "qwen_kvsys":
        return "KV-CORES" if kind == "core" else "KV-PLAN"
    if die == "hbm":
        return "HBM-CORES" if kind == "core" else "HBM-PLAN"
    return "?"


def plan_items(die, plan):
    """die_plan.json -> [{die, item, kind, module}] (types by key, hard cores by module, each once)"""
    T = (plan or {}).get("partition_types") or {}
    out = [dict(die=die, item=k, kind="type", module=(v.get("module") or k)) for k, v in T.items()]
    cores = sorted({h.get("module") for v in T.values() for h in (v.get("hard_cores") or []) if h.get("module")})
    out += [dict(die=die, item=m, kind="core", module=m) for m in cores if m not in T]
    return out


def _ok_alias(a):
    return len(a) >= 4 and ("_" in a or re.search(r"\d", a) is not None)


def aliases(it):
    s = {it["item"], it["module"]}
    for a in list(s):
        if a.startswith("ot_s81hd_"):
            s.add("hd_" + a[len("ot_s81hd_"):])
    if it["kind"] == "core":
        s |= {a[:-3] for a in s if a.endswith("_cv")}
    return {a for a in s if _ok_alias(a)}


class Matcher:
    """text token -> item keys ((die, item)); longest alias that is the token or its prefix at '_' / '.'"""
    def __init__(self, items):
        self.al = {}
        for it in items:
            for a in aliases(it):
                self.al.setdefault(a, set()).add((it["die"], it["item"]))
        self.part = {}                                   # 'part_<key>' (G2 gen dirs) is unambiguous for short keys too
        for it in items:
            if it["kind"] == "type":
                self.part.setdefault(it["item"], set()).add((it["die"], it["item"]))
        self.maxlen = max((len(a) for a in self.al), default=0)
        self._memo = {}

    def token(self, tok):
        r = self._memo.get(tok)
        if r is not None:
            return r
        t = LEAD.sub("", tok)
        r = frozenset()
        if tok.startswith("part_") and t in self.part:
            self._memo[tok] = r = frozenset(self.part[t])
            return r
        cuts = [len(t)] + [i for i in range(min(len(t) - 1, self.maxlen), 3, -1) if t[i] in "_."]
        for c in sorted(set(cuts), reverse=True):
            hit = self.al.get(t[:c])
            if hit:
                r = frozenset(hit)
                break
        self._memo[tok] = r
        return r

    def text(self, s):
        out = set()
        for tok in TOKEN.findall(s or ""):
            if len(tok) >= 4:
                out |= self.token(tok)
        return out


def rec_keys(r):
    """release_tree_plan.py's rule: a SIGNED record counts for a type / core by face_guard top or name (dp_/kr_ dropped)"""
    ks = set()
    for v in (r.get("top"), r.get("name")):
        if not v:
            continue
        ks.add(v)
        m = re.match(r"^(dp|kr)_(.+)$", v)
        if m:
            ks.add(m.group(2))
            ks.add(re.sub(r"_(lfp|r\d+|c\d+)$", "", m.group(2)))
    return ks


def signed_items(items, cache):
    """{(die, item): evidence} from the release tree cache"""
    out = {}
    if not cache:
        return out
    by_plan = {d: k for k, d, _ in DIES}
    for pdir, ent in (cache.get("plans") or {}).items():
        die = by_plan.get(pdir)
        if not die:
            continue                                     # the cache may carry an older plan (B2l): records below
        for k in list((ent.get("signed_types") or {})) + list((ent.get("signed_cores") or {})):
            out.setdefault((die, k), f"release cache {pdir}")
    names = {}
    for it in items:
        for n in ({it["item"], it["module"]} if it["kind"] == "type" else {it["module"]}):
            names.setdefault(n, []).append((it["die"], it["item"]))
    for r in cache.get("signed_records") or []:
        for k in rec_keys(r):
            for key in names.get(k, []):
                out.setdefault(key, f"SIGNED {r.get('scan_host')}:{r.get('path')}")
    return out


def pick_proto(plan_items_, files):
    """PROTO result files {name: json} -> the geom / g2 dict whose type keys overlap the plan most (>= 50 %)"""
    keys = {it["item"] for it in plan_items_ if it["kind"] == "type"}
    best, bo = None, 0
    for name, d in files.items():
        t = d.get("types") if isinstance(d, dict) and isinstance(d.get("types"), dict) else d
        if not isinstance(t, dict):
            continue
        ov = len(keys & set(t))
        if keys and ov >= 0.5 * len(keys) and ov > bo:
            best, bo = (name, t), ov
    return best


def structural(die, items_, proto, cache):
    """{item: reason} PLAN-STRUCTURAL evidence"""
    out = {}
    g = pick_proto(items_, (proto or {}).get("geom") or {})
    if g:
        for t, v in g[1].items():
            if isinstance(v, dict) and v.get("verdict") == "FAIL":
                out[t] = f"PROTO geom FAIL ({g[0]})"
    r = pick_proto(items_, (proto or {}).get("g2") or {})
    if r:
        for t, v in r[1].items():
            c = (v.get("classify") or {}) if isinstance(v, dict) else {}
            if c.get("cls") == "STRUCTURAL":
                out.setdefault(t, f"PROTO G2 STRUCTURAL {c.get('why', '')[:80]} ({r[0]})")
    pdir = {k: d for k, d, _ in DIES}[die]
    ent = ((cache or {}).get("plans") or {}).get(pdir) or {}
    for t in ent.get("g0c_bad_types") or {}:
        out.setdefault(t, "G0C bad type (release cache)")
    return out


def line_events(text):
    """[(t, line)] with the timestamp of the line or of the last line that had one"""
    out, last = [], None
    for line in (text or "").splitlines():
        t = parse_ts(line)
        if t is not None:
            last = t
        out.append((t if t is not None else last, line))
    return out


def _clause_verdict(line, start, keys, M):
    tail = line[start:]
    for seg in re.split(r";|\||\.\s", tail):
        if M.text(seg) & keys:
            w = {m.group(1) for m in VERDICT.finditer(seg)}
            if len(w) == 1:
                return w.pop()
            if w:
                return None
    w = {m.group(1) for m in VERDICT.finditer(tail)}
    return w.pop() if len(w) == 1 else None


def build(inp, now=None):
    """inp: plans {die: plan json}, cache, proto {die: {geom: {name: json}, g2: {...}}}, jobs [autopilot jobs],
    trows [review/structural rows: t, id, die, type, lane, file, cls, review_dir], geom_text, lane_texts {LANE: text},
    coord_texts {name: text} (other coord files that count as activity), live [(pid, etime_s, args)]
    -> (rows, gaps, summary_lines)"""
    now = now or time.time()
    items = []
    for die, _, _ in DIES:
        items += plan_items(die, (inp.get("plans") or {}).get(die))
    M = Matcher(items)
    die_items = {}
    for it in items:
        die_items.setdefault(it["die"], []).append(it)
    E = {(it["die"], it["item"]): dict(it, events=[], mentions=[], live=[], lanes={}) for it in items}

    def keys_for(name, die=None):
        ks = M.text(name)
        if die:
            near = {d for d in (die, "s81_head" if die == "s81" else die, "s81" if die == "s81_head" else die)}
            ks = {k for k in ks if k[0] in near} or ks
        return ks

    signed = signed_items(items, inp.get("cache"))
    for j in inp.get("jobs") or []:
        st = str(j.get("status", ""))
        ks = keys_for(j.get("type", ""), j.get("die"))
        for k in ks:
            e = E[k]
            if st in ("SIGNED", "DONE-SIGNED"):
                signed.setdefault(k, f"autopilot {j.get('id')} SIGNED")
            if st == "RUNNING":
                e["live"].append((f"{j.get('unit') or 'adopted'} {j.get('id')}", j.get("lane") or "", "route"))
            if st == "WAIT-GEOM":
                t = j.get("updated") or now
                e["events"].append((t, "GEOM-REQ", f"autopilot {j.get('id')} WAIT-GEOM {j.get('geom_ref', '')}"[:120]))
            if j.get("updated"):
                e["mentions"].append((j["updated"], ""))
                if j.get("lane"):
                    e["runlane"] = max(e.get("runlane") or (0, ""), (j["updated"], j["lane"]))
    for pid, et, args in inp.get("live") or []:
        kind = "probe" if PROBE_ARGS.search(args) else ("route" if re.search(r" (route|finish)\b", args) else "build")
        m = re.search(r"--dir (\S+)", args)
        where = m.group(1) if m else args[:80]
        for k in M.text(where if m else args):
            E[k]["live"].append((f"ot-run pid {pid} {where[-70:]}", "", kind))
    for r in inp.get("trows") or []:
        for k in keys_for(r.get("type", ""), r.get("die")):
            E[k]["events"].append((r["t"] or now, "RUN", f"{r['file']} {r['id']} {r.get('cls', '')} {r.get('review_dir', '')}".strip()))
            E[k]["mentions"].append((r["t"] or now, ""))
            if r.get("lane"):
                E[k]["runlane"] = max(E[k].get("runlane") or (0, ""), (r["t"] or now, r["lane"]))

    # GEOM-REVIEW: REQ / REPLY lines naming the item (plan prototypes / skeleton reviews are activity, not kit events)
    reqs, reps = LG.geom_events(inp.get("geom_text") or "")
    for t, line in line_events(inp.get("geom_text")):
        if t is None:
            continue
        ks = M.text(line)
        if not ks:
            continue
        for k in ks:
            E[k]["mentions"].append((t, ""))
        if NOT_KIT.search(line):
            continue
        m = REQ_RE.search(line)
        if m and "REPLY" not in line[:m.start()]:
            tag = LG.tag_of(m.group(1) or m.group(2))
            closed = any((rt or 0) >= t and LG._answers(tag, line, rtag, rl) for rt, rtag, _, rl in reps)
            for k in ks:
                E[k]["events"].append((t, "REQ-CLOSED" if closed else "REQ", line.strip()[:120]))
            continue
        m = REPLY_RE.search(line)
        if m:
            for k in ks:
                v = _clause_verdict(line, m.end(), {k}, M)
                if v:
                    E[k]["events"].append((t, "V-" + v, line.strip()[:120]))
    for name, text in (inp.get("lane_texts") or {}).items():
        lane = None if NOT_LANES.match(name) else name
        for t, line in line_events(text):
            if t is None:
                continue
            for k in M.text(line):
                E[k]["mentions"].append((t, lane or ""))
                if lane:
                    E[k]["lanes"][lane] = max(E[k]["lanes"].get(lane, 0), t)

    rows, gaps, unowned = [], [], {}
    for die, _, _ in DIES:
        struct = structural(die, die_items.get(die, []), (inp.get("proto") or {}).get(die), inp.get("cache"))
        for it in die_items.get(die, []):
            k = (die, it["item"])
            e = E[k]
            live_route = [x for x in e["live"] if x[2] == "route"]
            ev, state, why = None, None, ""
            if k in signed:
                state, why = "SIGNED", signed[k]
            elif live_route:
                state, why = "ROUTING", live_route[0][0]
            else:
                cand = []
                lane_after = lambda t: any(lt > t + 60 for lt, ln in e["mentions"] if ln)
                for t, kind, txt in e["events"]:
                    if kind == "RUN":
                        cand.append((t, "FIX" if lane_after(t) else "REVIEW", txt))
                    elif kind in ("REQ", "REQ-CLOSED"):
                        answered = kind == "REQ-CLOSED" or any(t2 >= t and k2.startswith("V-") for t2, k2, _ in e["events"])
                        cand.append((t, "GEOM-REQ" if not answered else "_REQ", txt))
                    elif kind == "V-FAIL":
                        cand.append((t, "FIX", txt))
                    elif kind in ("V-PASS", "V-PASS-COND"):
                        cand.append((t, "KIT-PLACED", txt))
                    else:
                        cand.append((t, kind, txt))
                cand = [c for c in cand if c[1] != "_REQ"]
                if cand:
                    ev = max(cand, key=lambda c: c[0])
                    state, why = ev[1], ev[2]
                elif it["item"] in struct or it["module"] in struct:
                    state, why = "PLAN-STRUCTURAL", struct.get(it["item"]) or struct.get(it["module"])
                else:
                    state, why = "NEEDS-KIT", ""
            last = max([t for t, _ in e["mentions"]] + [t for t, _, _ in e["events"]] or [0])
            if e["live"]:
                last = now
            lanes = {ln: t for ln, t in e["lanes"].items() if now - t <= OWNER_WINDOW_S}
            live_lanes = [x[1] for x in e["live"] if x[1]]
            dflt = default_owner(die, it["kind"], it["item"])
            if live_lanes:
                owner = live_lanes[0]
            elif e.get("runlane") and now - e["runlane"][0] <= OWNER_WINDOW_S:
                owner = e["runlane"][1]                       # lane of its latest autopilot run / review row
            elif lanes:
                owner = max(lanes, key=lanes.get)             # lane file with the latest line naming it
            else:
                owner = dflt
            live = "; ".join(x[0] for x in e["live"][:2]) + (f" (+{len(e['live']) - 2})" if len(e["live"]) > 2 else "") \
                if e["live"] else "none"
            age = f"{(now - last) / 60:.0f}m" if last else "never"
            nxt = NEXT[state]
            if state == "PLAN-STRUCTURAL" or (state == "NEEDS-KIT" and it["item"] in struct):
                why = why or struct.get(it["item"], "")
            rows.append(dict(die=die, item=it["item"], kind=it["kind"], state=state, owner=owner, live_job=live,
                             last_activity=age, next_step=nxt, default_owner=dflt, evidence=(why or "").replace("\t", " ")[:200],
                             _last=last))
            if state != "SIGNED" and not e["live"] and (not last or now - last > UNOWNED_S):
                unowned.setdefault((die, dflt), []).append((last, it["item"], state, owner))

    for (die, owner), lst in sorted(unowned.items()):
        newest = max(x[0] for x in lst)
        t = newest if newest else now - OWNER_WINDOW_S
        by = {}
        for _, name, stt, last_lane in lst:
            by.setdefault(stt, []).append(name + (f"({last_lane})" if last_lane != owner else ""))
        detail = "; ".join(f"{s} {len(v)}: {' '.join(sorted(v)[:12])}{' ...' if len(v) > 12 else ''}"
                           for s, v in sorted(by.items(), key=lambda kv: STATES.index(kv[0])))
        gaps.append((t, f"UNOWNED-ITEM {die} -> {owner}: {len(lst)} items with no live job and no lane activity > 60 min "
                        f"((LANE) = last lane that touched it; OWNERS.tsv) -- {detail}"))
    return rows, gaps, summary(rows, unowned, inp)


def summary(rows, unowned, inp):
    out = [f"# OWNERSHIP (OWNERS.tsv, {len(rows)} items = partition types + hard cores of the release plans): "
           f"state counts per die; UNOWNED = not SIGNED, no live job, no lane activity > 60 min"]
    if not (inp.get("cache") or {}).get("plans"):
        out.append("#   (release tree cache missing: SIGNED only from autopilot runs)")
    for die, pdir, _ in DIES:
        rs = [r for r in rows if r["die"] == die]
        if not rs:
            out.append(f"#   {die:13s} plan {pdir}: no plan read")
            continue
        c = {s: sum(1 for r in rs if r["state"] == s) for s in STATES}
        un = sum(len(v) for (d, _), v in unowned.items() if d == die)
        out.append(f"#   {die:13s} {len(rs):4d}: " + " ".join(f"{s} {c[s]}" for s in STATES if c[s]) + f" | UNOWNED {un}")
    return out


TSV_COLS = ["die", "item", "kind", "state", "owner", "live_job", "last_activity", "next_step", "evidence",
            "default_owner"]


def to_tsv(rows, now):
    head = f"# OWNERS -- autopilot tick {time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(now))} (ownership.py)\n"
    order = {s: i for i, s in enumerate(STATES)}
    rows = sorted(rows, key=lambda r: ([d for d, _, _ in DIES].index(r["die"]), order[r["state"]], r["item"]))
    return head + "\t".join(TSV_COLS) + "\n" + "".join(
        "\t".join(str(r[c]).replace("\t", " ").replace("\n", " ") for c in TSV_COLS) + "\n" for r in rows)


if __name__ == "__main__":
    print(json.dumps(DIES))
