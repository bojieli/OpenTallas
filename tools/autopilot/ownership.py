#!/usr/bin/env python3
"""ownership.py -- OWNERSHIP table for the AUTOPILOT tick (owner question 2026-10-25: does every non-closing partition
still have an owner?  Ownership is per die lane, so a partition type or hard core can sit with no live job and nobody
working on it).  Read-only: pure functions over inputs that autopilot.py gathers; autopilot.py writes
~/coord/autopilot/OWNERS.tsv and puts the summary + UNOWNED-ITEM gaps into LOOP-GAPS.txt.

Items are DISTINCT DESIGNS (owner 2026-10-25: count what has to be hardened, not instances or pieces) of the
release-die plans on origin/main (S81 incl. head, QC, KV, HBM B2n -- DIES below):
  core  key = (RTL master, outline, pin table).  RTL master = the canonical split type + top of
        physical/die_plan/hbm/cores/harden/canonical_ports_split.json (HBM split pieces: 64 idx hcol piece modules are
        2 masters; straps are tied at the parent, so they are not part of the core) or else the module itself (its
        params are baked into the module name); pin table = sha of the sorted (name, layer, x, y) of the plan's
        pins_file in the core frame.  So one module with N pin tables is N designs (pc_ctrl h9b: 10), and N piece
        modules with one master + table are 1 design with N replicas.  A core without a readable pins file is keyed by
        its module.
  type  key = dedup.netlist_key (outline, buses, ft slots, contents incl. params, hard core inst+module, reset, sources)
        + the pin geometry (bus face/window/layers/order, ft-slot faces/windows/layers/order).  Two types that bind
        identical RTL + outline + pins are one design.
  replicas = placed instances the design clears when it signs off (partition count of the member types; for a core the
        placed count of every member hard-core entry).  members = the type keys / core modules it covers.
One row per design (item = its representative: the member type with most instances, or the member module; a module
whose entries span several pin tables gets item <module>_<pins sha12>):
  die  item  kind  state  owner  live_job  last_activity  next_step  evidence  default_owner  replicas  members
State (first rule that applies):
  SIGNED           a SIGNED signoff record matches ANY member of the item (one sign-off clears every replica; a
                   module-level record of a module with several pin tables counts only for the design whose pins
                   sha12 / pins-file stem appears in the record path or kit) (release tree cache: per-plan signed lists + the fleet
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

Names: an item is named by every member type key / module (and <module>_<pins sha12>, the kit dir spelling), and a
few spellings used by the kit tools (ot_s81hd_X -> hd_X, a
hard core's _cv suffix dropped).  A text token names the item when one of those is the token or a prefix of it ending
at '_' / '.' (longest wins: kv3_hg_v2 is never kv3_hg); leading part_/kl_/kr_/dp_ are dropped
(G2 gen dirs, signoff names).
"""
import hashlib
import json
import re
import time

import loopgaps as LG

# (die key used in OWNERS.tsv / autopilot queue, plan dir under physical/die_plan, PROTO die name)
DIES = [("s81", "s81", "s81"), ("s81_head", "s81_head", "s81_head"), ("qwen_compute", "qwen_compute", "qwen_compute"),
        ("qwen_kvsys", "qwen_kvsys", "qwen_kvsys"), ("hbm", "hbm_arch/B2n", "B2n")]
CANONICAL_SPLIT = "physical/die_plan/hbm/cores/harden/canonical_ports_split.json"   # HBM split piece -> RTL master
STATES = ["PLAN-STRUCTURAL", "NEEDS-KIT", "KIT-PLACED", "GEOM-REQ", "ROUTING", "REVIEW", "FIX", "WAIT-PARENT", "SIGNED"]
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
    "WAIT-PARENT": "matching actual parent seam receipt required; preserve physical views",
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


# dedup.netlist_key (tools/die_plan/dedup.py), kept in step here so the installed autopilot copy needs no die_plan import
CONTENT_GEOM = {"origin_um", "outline_um", "note", "kit", "geom_pass", "cells", "status", "obs_max", "orient"}
BUS_GEOM = {"face", "window_um", "layers", "order", "note"}
SLOT_GEOM = {"in_face", "out_face", "in_window_um", "out_window_um", "layers", "order", "regs_um", "note"}
SLOT_INTERNAL = {"note", "regs_um", "bit_sites_um"}           # register sites inside the type: not pins


def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def _strip(d, drop):
    return {k: v for k, v in d.items() if k not in drop}


def netlist_key(t):
    """= dedup.netlist_key(t) (params and slots kept)"""
    return _canon(dict(
        outline=[round(float(v), 4) for v in t["outline_um"]],
        hard=bool(t.get("hard", False)),
        buses=sorted((_canon(_strip(b, BUS_GEOM)) for b in t.get("buses", []))),
        slots=sorted((_canon(_strip(s, SLOT_GEOM)) for s in t.get("ft_slots", []))),
        contents=sorted((_canon(_strip(c, CONTENT_GEOM)) for c in t.get("contents", []))),
        cores=sorted((c["inst"], c["module"]) for c in t.get("hard_cores", [])),
        reset=t.get("reset", {}).get("sync_stages"),
        sources=sorted(t.get("sources", [])),
    ))


def type_design_key(k, t):
    """same RTL + outline + pins: netlist_key + bus / ft-slot pin geometry.  A type without an outline (partial plan)
    is its own design."""
    if not isinstance(t, dict) or not t.get("outline_um"):
        return "name:" + k
    try:
        pins = dict(b=sorted(_canon(_strip(b, {"note"})) for b in t.get("buses", [])),
                    s=sorted(_canon(_strip(x, SLOT_INTERNAL)) for x in t.get("ft_slots", [])))
        return hashlib.sha1((netlist_key(t) + _canon(pins)).encode()).hexdigest()[:16]
    except (KeyError, TypeError, ValueError):
        return "name:" + k


def pin_sig(text):
    """pins_file text -> (sha256(raw)[:12] = the kit-dir spelling, table sha of sorted (name, layer, x, y)) or None"""
    if not text:
        return None
    try:
        P = json.loads(text)
        if isinstance(P, dict):
            P = P.get("pins", [])
        tab = sorted((str(p["name"]), str(p.get("layer")), round(float(p["x"]), 3), round(float(p["y"]), 3)) for p in P)
    except (ValueError, KeyError, TypeError):
        return None
    return (hashlib.sha256(text.encode()).hexdigest()[:12], hashlib.sha1(_canon(tab).encode()).hexdigest()[:16])


def canonical_masters(ct):
    """canonical_ports_split.json -> {piece module: 'top#canonical type'} (outline suffix of the type id dropped)"""
    out = {}
    for cname, c in ((ct or {}).get("types") or {}).items():
        for tid in (c.get("type_ids") or {}):
            out[re.sub(r"__[\d.]+x[\d.]+$", "", tid)] = f"{c.get('top') or cname}#{cname}"
    return out


BOUND_RTL_DIR = "bind/bound_r8/rtl"                    # dedup.py --bound-rtl default (PLANDIR/bind/bound_r8/rtl)


def _type_groups(T):
    groups = {}
    for k, v in T.items():
        groups.setdefault(type_design_key(k, v), []).append(k)
    return groups


def bound_rtl_paths(pdir, plan):
    """{type: [candidate bound-RTL paths]} for the types that share a plan design key with another type: the plan does
    not carry everything the binder generates (KV hg rows: per-row R8 pads), so such a group merges only where the
    bound partition RTL is identical too"""
    T = (plan or {}).get("partition_types") or {}
    out = {}
    for ks in _type_groups(T).values():
        if len(ks) > 1:
            for k in ks:
                mod = T[k].get("module") or k
                out[k] = [f"physical/die_plan/{pdir}/{BOUND_RTL_DIR}/{c}" for c in (f"{mod}.sv", f"{mod}__{k}.sv", f"{k}.sv")]
    return out


def norm_rtl(text, mod):
    """bound RTL without comments, blank lines and its own module name (dedup.bound_rtl)"""
    t = re.sub(r"//.*", "", text or "").replace(mod, "__MOD__")
    return hashlib.sha1("\n".join(ln.rstrip() for ln in t.splitlines() if ln.strip()).encode()).hexdigest()


def plan_items(die, plan, pins=None, masters=None, bound=None):
    """die_plan.json -> distinct designs [{die, item, kind, module, members, replicas, pin_ids, design}]
    pins {pins_file: text} (the plan's core pin tables), masters {module: RTL master} (canonical_masters),
    bound {type: bound partition RTL text} for the types bound_rtl_paths() names (a type without it stays alone)"""
    T = (plan or {}).get("partition_types") or {}
    pins, masters, bound = pins or {}, masters or {}, bound or {}
    ninst = {}
    for p in (plan or {}).get("partitions") or []:
        ninst[p.get("type")] = ninst.get(p.get("type"), 0) + 1
    groups = {}
    for key, ks in _type_groups(T).items():
        for k in ks:
            if len(ks) == 1:
                groups[key] = ks
            elif bound.get(k):
                groups.setdefault(key + ":" + norm_rtl(bound[k], T[k].get("module") or k)[:12], []).append(k)
            else:
                groups[key + ":unbound:" + k] = [k]
    out = []
    for key, ks in groups.items():
        rep = sorted(ks, key=lambda x: (-ninst.get(x, 0), x))[0]
        out.append(dict(die=die, item=rep, kind="type", module=(T[rep].get("module") or rep), members=sorted(ks),
                        modules=sorted({T[x].get("module") or x for x in ks}), replicas=sum(ninst.get(x, 0) for x in ks),
                        pin_ids=set(), design="type:" + key))
    cores = {}                                            # design key -> {modules, replicas, pin_ids}
    for k, v in T.items():
        for h in (v.get("hard_cores") or []) if isinstance(v, dict) else []:
            m = h.get("module")
            if not m or m in T:
                continue
            ps = pin_sig(pins.get(h.get("pins_file"))) if h.get("pins_file") else None
            outl = "x".join(f"{float(x):g}" for x in (h.get("outline_um") or []))
            key = (masters.get(m, m), outl, ps[1]) if ps else (m, "", "")
            d = cores.setdefault(key, dict(modules=set(), replicas=0, pin_ids=set()))
            d["modules"].add(m)
            d["replicas"] += ninst.get(k, 0) if (plan or {}).get("partitions") else 1
            if ps:
                d["pin_ids"].add(ps[0])
                d["pin_ids"].add(re.sub(r"\.json$", "", h["pins_file"].rsplit("/", 1)[-1]))
    n_of = {}
    for d in cores.values():
        for m in d["modules"]:
            n_of[m] = n_of.get(m, 0) + 1
    for key, d in sorted(cores.items(), key=lambda kv: (min(kv[1]["modules"]), kv[0][2])):
        ms = sorted(d["modules"])
        rep = ms[0]
        ambig = any(n_of[m] > 1 for m in ms)
        sha = min((x for x in d["pin_ids"] if re.fullmatch(r"[0-9a-f]{12}", x)), default="")
        item = f"{rep}_{sha}" if (n_of[rep] > 1 and sha) else rep
        out.append(dict(die=die, item=item, kind="core", module=rep, members=ms, modules=ms, replicas=d["replicas"],
                        pin_ids=d["pin_ids"], ambiguous=ambig, design="core:" + "|".join(key)))
    return out


def _ok_alias(a):
    return len(a) >= 4 and ("_" in a or re.search(r"\d", a) is not None)


def aliases(it):
    s = {it["item"], it["module"]} | set(it.get("members") or []) | set(it.get("modules") or [])
    if it["kind"] == "core":                             # kit dirs: <module>_<pins sha12>
        s |= {f"{m}_{x}" for m in (it.get("modules") or []) for x in it.get("pin_ids") or ()
              if re.fullmatch(r"[0-9a-f]{12}", x)}
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
                for k in it.get("members") or [it["item"]]:
                    self.part.setdefault(k, set()).add((it["die"], it["item"]))
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


def pick(cands, text, by_key):
    """keys a sign-off of one name clears: all when they are one design; when the name is a module with several pin
    tables (several designs), only the designs whose pins sha12 / pins-file stem appears in the evidence text"""
    cands = list(dict.fromkeys(cands))
    cores = [c for c in cands if by_key[c]["kind"] == "core"]
    if len(cores) <= 1:
        return cands
    hit = [c for c in cores if any(x in (text or "") for x in by_key[c].get("pin_ids") or ())]
    return [c for c in cands if c not in cores] + hit


def _names(items):
    names = {}
    for it in items:
        ns = (set(it.get("members") or []) | set(it.get("modules") or []) | {it["item"], it["module"]}) \
            if it["kind"] == "type" else set(it.get("modules") or [it["module"]])
        for n in ns:
            names.setdefault(n, []).append((it["die"], it["item"]))
    return names


def signed_items(items, cache):
    """{(die, item): evidence} from the release tree cache (a record naming any member clears the design)"""
    out = {}
    if not cache:
        return out
    by_key = {(it["die"], it["item"]): it for it in items}
    names = _names(items)
    by_plan = {d: k for k, d, _ in DIES}
    for pdir, ent in (cache.get("plans") or {}).items():
        die = by_plan.get(pdir)
        if not die:
            continue                                     # the cache may carry an older plan (B2l): records below
        for d in ("signed_types", "signed_cores"):
            for k, ev in (ent.get(d) or {}).items():
                text = " ".join(map(str, ev)) if isinstance(ev, (list, tuple)) else str(ev or "")
                cands = [x for x in names.get(k, []) if x[0] == die] or ([(die, k)] if (die, k) in by_key else [])
                for key in pick(cands, text, by_key):
                    out.setdefault(key, f"release cache {pdir}" + (f" ({k})" if k != key[1] else ""))
    for r in cache.get("signed_records") or []:
        text = f"{r.get('path', '')} {r.get('name', '')}"
        for k in rec_keys(r):
            for key in pick(names.get(k, []), text, by_key):
                out.setdefault(key, f"SIGNED {r.get('scan_host')}:{r.get('path')}")
    return out


def pick_proto(plan_items_, files):
    """PROTO result files {name: json} -> the geom / g2 dict whose type keys overlap the plan most (>= 50 %)"""
    keys = {k for it in plan_items_ if it["kind"] == "type" for k in (it.get("members") or [it["item"]])}
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
        items += plan_items(die, (inp.get("plans") or {}).get(die), (inp.get("core_pins") or {}).get(die),
                            canonical_masters(inp.get("canonical")) if die == "hbm" else None,
                            (inp.get("bound_rtl") or {}).get(die))
    M = Matcher(items)
    by_key = {(it["die"], it["item"]): it for it in items}
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
        sel = set(pick(ks, f"{j.get('kit', '')} {j.get('type', '')} {j.get('pins', '')}", by_key))
        for k in ks:
            e = E[k]
            if sel and k not in sel:                     # a run of one pin table of a multi-table module
                continue
            if st in ("SIGNED", "DONE-SIGNED") and k in sel:
                signed.setdefault(k, f"autopilot {j.get('id')} SIGNED")
            if st == "RUNNING":
                e["live"].append((f"{j.get('unit') or 'adopted'} {j.get('id')}", j.get("lane") or "", "route"))
            if st == "WAIT-PARENT":
                t = j.get("updated") or now
                e["events"].append((t, "WAIT-PARENT", f"autopilot {j.get('id')} local physical PASS; actual parent receipt owed"))
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
            skey = next((x for x in [it["item"], it["module"]] + list(it.get("members") or []) + list(it.get("modules") or [])
                         if x in struct), None)
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
                elif skey:
                    state, why = "PLAN-STRUCTURAL", struct[skey] + (f" [{skey}]" if skey != it["item"] else "")
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
            if state == "PLAN-STRUCTURAL" or (state == "NEEDS-KIT" and skey):
                why = why or struct.get(skey, "")
            rows.append(dict(die=die, item=it["item"], kind=it["kind"], state=state, owner=owner, live_job=live,
                             last_activity=age, next_step=nxt, default_owner=dflt, evidence=(why or "").replace("\t", " ")[:200],
                             replicas=it.get("replicas", ""), members=_members(it), _last=last))
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
    out = [f"# OWNERSHIP (OWNERS.tsv, {len(rows)} items = DISTINCT designs of the release plans: partition types by "
           f"RTL+outline+pins, hard cores by RTL master+outline+pin table; one sign-off clears all replicas): "
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
        nt = sum(1 for r in rs if r["kind"] == "type")
        rep = sum(int(r["replicas"] or 0) for r in rs if r["kind"] == "core")
        out.append(f"#   {die:13s} {len(rs):4d}: " + " ".join(f"{s} {c[s]}" for s in STATES if c[s]) + f" | UNOWNED {un}"
                   f" | types {nt} cores {len(rs) - nt} (placed core replicas {rep})")
    return out


TSV_COLS = ["die", "item", "kind", "state", "owner", "live_job", "last_activity", "next_step", "evidence",
            "default_owner", "replicas", "members"]


def _members(it):
    ms = list(it.get("members") or [])
    if len(ms) <= 1:
        return ""
    return f"{len(ms)}: " + " ".join(ms[:24]) + (" ..." if len(ms) > 24 else "")


def to_tsv(rows, now):
    head = f"# OWNERS -- autopilot tick {time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(now))} (ownership.py)\n"
    order = {s: i for i, s in enumerate(STATES)}
    rows = sorted(rows, key=lambda r: ([d for d, _, _ in DIES].index(r["die"]), order[r["state"]], r["item"]))
    return head + "\t".join(TSV_COLS) + "\n" + "".join(
        "\t".join(str(r[c]).replace("\t", " ").replace("\n", " ") for c in TSV_COLS) + "\n" for r in rows)


if __name__ == "__main__":
    print(json.dumps(DIES))
