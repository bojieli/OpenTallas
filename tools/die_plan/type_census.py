#!/usr/bin/env python3
"""type_census.py -- why is each distinct hardened design distinct?  (TYPE-REDUCE-2, OWNER 2026-10-25 19:53)

The autopilot counts DISTINCT DESIGNS with tools/autopilot/ownership.py plan_items() (type = netlist + pin geometry,
core = RTL master + outline + pin table).  This tool explains that count: for every design it names the FIRST cause
that keeps it apart from another design of the same family, and the class it collapses into once

  (2) ID-only constants become declared strap_* input pins (OWNER option B 10-25 07:01: tied at the parent), and
  (3) pins are assigned per TEMPLATE, not per slot (one pin table per template, instances reuse it with an orient),

are fixed.  The keys loosen in this order (the first one that merges the design with another is its reason):

  pin-positions   bus/ft windows, faces, layers, order, ft bit sites, internal station coordinates, hard-core origins /
                  orients / pins_file / _xm (mirror) views -- all consequences of per-slot pin assignment   [cause 3]
  ID-constant     content params named like an ID (ID/TID/HID/BSEL/LANE/ROW/COL/QUAD/CORNER/SLICE/POS/IDX/...) and
                  module / bus names that differ only by a position number                                   [cause 2]
  --- count after (2)+(3) = distinct classes at this level ---
  ft-population   feed-through slot set (lanes passing through differ by position)
  outline         partition / core outline
  ROM-content     remaining content params (ROM image per instance) or ROM-image notes
  glue-by-position content module names that differ only by a position number (per-slot generated glue)
  edge            bus set differs only in names/widths of chain-end / narrowed ports (same family)
  different-logic nothing else merges it
Families: types are grouped by module stem (__tN, _vN, _rN, trailing digits dropped); cores by RTL master stem.
Read-only.  Usage: type_census.py --plan physical/die_plan/<die>/die_plan.json --die <die> [--owners OWNERS.tsv]
                   [--tsv out.tsv] [--json out.json]
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "autopilot"))
import ownership as OWN  # noqa: E402

ID_PARAM = re.compile(r"(^|_)(I?D|TID|HID|BSEL|SEL_ID|LANE(_J|_ID)?|ROW|COL|Q(UAD)?|CORNER|SLICE|POS|IDX|INDEX|"
                      r"TILE|BANK_?ID|SM_?ID|GROUP(_REL)?_ID|LID|NODE_?ID|HEAD(_ID)?|EIGHTH|PART_?ID|J|K)($|_)", re.I)
POSNUM = re.compile(r"(__t\d+|_v\d+[a-z]?|_r\d+|_p\d+|_e\d+|_l\d+|_q\d+|_h\d+|_c\d+|\d+)")
ROMNOTE = re.compile(r"\brom\b|rom image|image per instance", re.I)
REASONS = ["pin-positions", "ID-constant", "ft-population", "outline", "ROM-content", "glue-by-position", "edge",
           "different-logic"]
FIXED_BY = {"pin-positions": "(3)", "ID-constant": "(2)"}


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def h(x):
    return hashlib.sha1(canon(x).encode()).hexdigest()[:16]


def stem(name):
    return POSNUM.sub("", name or "")


def _strip(d, drop):
    return {k: v for k, v in d.items() if k not in drop}


def type_levels(t):
    """[key per loosening level], level i merges the cause REASONS[i] (the last level = family)"""
    buses = [_strip(b, OWN.BUS_GEOM) for b in t.get("buses", [])]
    slots = [_strip(s, OWN.SLOT_GEOM | {"bit_sites_um"}) for s in t.get("ft_slots", [])]
    cont = [_strip(c, OWN.CONTENT_GEOM) for c in t.get("contents", [])]
    cores = sorted(stem_xm(c.get("module")) for c in t.get("hard_cores", []))
    base = dict(outline=[round(float(v), 4) for v in t.get("outline_um") or []], hard=bool(t.get("hard")),
                reset=(t.get("reset") or {}).get("sync_stages"), cores=cores)
    # L0 after (3): geometry dropped
    # (slot-numbered bus names are part of the per-slot pin table too: one template has neutral port names)
    bus0 = sorted(canon(dict(b, name=stem(b.get("name")))) for b in buses)
    k0 = dict(base, buses=bus0, slots=sorted(map(canon, slots)), cont=sorted(map(canon, cont)))
    # L1 after (2): ID params / position-numbered names dropped
    def noid(c):
        c = dict(c)
        c["params"] = {k: v for k, v in (c.get("params") or {}).items() if not ID_PARAM.search(k)}
        c.pop("parent_id_straps", None)
        c.pop("bind", None)
        return c
    cont1 = [noid(c) for c in cont]
    k1 = dict(base, buses=bus0, slots=k0["slots"], cont=sorted(map(canon, cont1)))
    k2 = dict(k1, slots=None)                                                        # ft population
    k3 = dict(k2, outline=None)                                                      # outline
    cont4 = [dict(c, params=None, note=None) for c in cont1]
    k4 = dict(k3, cont=sorted(map(canon, cont4)))                                    # ROM content / params
    k5 = dict(k4, cont=sorted(canon(dict(c, module=stem(c.get("module")), inst=stem(c.get("inst")))) for c in cont4))
    k6 = dict(k5, buses=sorted({stem(b.get("name")) + ":" + b.get("dir", "") for b in buses}))   # edge
    return [h(k) for k in (k0, k1, k2, k3, k4, k5, k6)]


def stem_xm(m):
    return re.sub(r"_xm$", "", m or "")


def classify(designs):
    """designs: [{id, family, levels:[k0..k6]}] -> {id: (reason, after_class)}"""
    out = {}
    for d in designs:
        reason = "different-logic"
        if d.get("reason"):                              # reviewed override (RTL read): keep it
            out[d["id"]] = d["reason"]
            continue
        for i, r in enumerate(REASONS[:-1]):
            peers = [e for e in designs if e is not d and e["family"] == d["family"] and e["levels"][i] == d["levels"][i]]
            if peers:
                reason = r
                break
        out[d["id"]] = reason
    after = {}
    for d in designs:                                    # class after (2)+(3) = level-1 key within the family
        cls = sorted(e["id"] for e in designs if e["family"] == d["family"] and e["levels"][1] == d["levels"][1])
        after[d["id"]] = cls[0]
    return {k: (out[k], after[k]) for k in out}


def core_levels(h_entries, pins_sig, masters, ids=None):
    """one core design (several plan entries) -> [k0, k1, ...] in the same REASONS order"""
    e = h_entries[0]
    m = e.get("module")
    master = stem_xm(masters.get(m, m))
    outl = "x".join(f"{float(x):g}" for x in (e.get("outline_um") or []))
    k0 = (master, outl)                                  # pin table / _xm view dropped (3)
    # (2) for cores = an approved ID strap master (ids: module -> strap master, from the per-die strap delta); name
    # similarity alone is NOT an ID (S81 dsdv_eng_rr_h0/h1 = per-layer hash constants, gunit_l0..l5 = pipeline levels)
    k1 = ((ids or {}).get(master, master), outl)
    # no name-stem levels for cores: a numbered sibling core is its own RTL unless a reviewed override says otherwise
    return [h(k0), h(k1), h(k1), h((k1[0],)), h((k1[0],)), h((k1[0],)), h((k1[0],))]


def census(die, plan, pins=None, masters=None, bound=None, overrides=None):
    items = OWN.plan_items(die, plan, pins, masters, bound)
    T = plan.get("partition_types") or {}
    entries = collections.defaultdict(list)
    for k, v in T.items():
        for hc in v.get("hard_cores") or []:
            entries[hc.get("module")].append(hc)
    tys, cos = [], []
    for it in items:
        if it["kind"] == "type":
            t = T[it["item"]]
            tys.append(dict(id=it["item"], family="T:" + stem(t.get("module") or it["item"]).replace("s81p_", ""),
                            levels=type_levels(t), it=it))
        else:
            es = [x for m in it["members"] for x in entries.get(m, [])] or [{"module": it["module"]}]
            if it["item"] != it["module"]:              # one module, several pin tables
                es = [x for x in es if any(p in (x.get("pins_file") or "") for p in it["pin_ids"])] or es
            lv = core_levels(es, None, masters or {})
            cos.append(dict(id=it["item"], family="C:" + stem(stem_xm((masters or {}).get(it["module"], it["module"]))
                                                               .split("#")[0]), levels=lv, it=it))
    rows = []
    for group in (tys, cos):
        cl = classify(group)
        for d in group:
            r, a = cl[d["id"]]
            note = ""
            if d["it"]["kind"] == "core" and d["id"] != d["it"]["module"]:
                note = f"module {d['it']['module']} has several pin tables"
            r = (overrides or {}).get(d["id"], {}).get("reason", r)
            note = (overrides or {}).get(d["id"], {}).get("note", note)
            rows.append(dict(die=die, item=d["id"], kind=d["it"]["kind"], replicas=d["it"]["replicas"], reason=r,
                             after_class=a, after_bank=a, family=d["family"], note=note, _k2=d["levels"][2]))
    bank_classes(T, rows)
    for r in rows:
        r.pop("_k2")
    return rows


BANK_SLACK = 1.15      # uniform FT lane bank <= 1.15 x the largest member's FT bits
BANK_DENS = 4.5        # pins/um per face (bank + the members' widest buses) -- face_guard / pin_track headroom


def _ftvec(t):
    v = collections.defaultdict(int)
    for s in t.get("ft_slots", []):
        v[(stem(s["name"]), tuple(sorted((s.get("in_face"), s.get("out_face")))))] += int(s.get("width", 0))
    return v


def bank_ok(T, g):
    """coordinator rule 10-25: a uniform FT lane bank (max of the members per lane kind; unused lanes chained, never
    tied) is acceptable only if it stays small and the faces keep their pin headroom"""
    b = collections.defaultdict(int)
    for k in g:
        for kk, w in _ftvec(T[k]).items():
            b[kk] = max(b[kk], w)
    if sum(b.values()) > BANK_SLACK * max(sum(_ftvec(T[k]).values()) for k in g):
        return False
    W, H = (T[g[0]].get("outline_um") or [1, 1])[:2]
    face = collections.Counter()
    for (_, fs), w in b.items():
        for f in fs:
            face[f] += w
    for f in "NSEW":
        bus = max(sum(x["width"] for x in T[k].get("buses", []) if x.get("face") == f) for k in g)
        if (face[f] + bus) / (W if f in "NS" else H) > BANK_DENS:
            return False
    return True


def bank_classes(T, rows):
    """after_bank: types that differ ONLY by FT population (same level-2 key) greedily packed into uniform-bank
    classes (largest FT first).  Cores and other reasons keep their after_class."""
    by = collections.defaultdict(list)
    for r in rows:
        if r["kind"] == "type":
            by[(r["family"], r["_k2"])].append(r)
    for rs in by.values():
        reps = {}
        for r in rs:
            reps.setdefault(r["after_class"], r)
        cl = []
        for r in sorted(reps.values(), key=lambda r: -sum(_ftvec(T[r["item"]]).values())):
            for g in cl:
                if bank_ok(T, [x["item"] for x in g] + [r["item"]]):
                    g.append(r)
                    break
            else:
                cl.append([r])
        for g in cl:
            head = sorted(x["after_class"] for x in g)[0]
            for x in g:
                for r in rs:
                    if r["after_class"] == x["after_class"]:
                        r["after_bank"] = head


def summarize(rows):
    s = collections.OrderedDict()
    for die in sorted({r["die"] for r in rows}):
        rs = [r for r in rows if r["die"] == die]
        s[die] = dict(before=len(rs), after=len({(r["kind"], r["after_class"]) for r in rs}),
                      types_before=sum(r["kind"] == "type" for r in rs),
                      types_after=len({r["after_class"] for r in rs if r["kind"] == "type"}),
                      cores_before=sum(r["kind"] == "core" for r in rs),
                      cores_after=len({r["after_class"] for r in rs if r["kind"] == "core"}),
                      after_bank=len({(r["kind"], r["after_bank"]) for r in rs}),
                      ft_only=sum(r["reason"] == "ft-population" for r in rs),
                      reasons=dict(collections.Counter(r["reason"] for r in rs)))
    return s


def load_inputs(root, pdir):
    plan = json.loads((root / f"physical/die_plan/{pdir}/die_plan.json").read_text())
    pins = {}
    for t in (plan.get("partition_types") or {}).values():
        for hc in t.get("hard_cores") or []:
            f = hc.get("pins_file")
            p = root / f"physical/die_plan/{pdir}/{f}" if f else None
            if p and p.exists():
                pins[f] = p.read_text()
    masters = {}
    cs = root / OWN.CANONICAL_SPLIT
    if pdir.startswith("hbm") and cs.exists():
        masters = OWN.canonical_masters(json.loads(cs.read_text()))
    bound = {}
    for k, cands in OWN.bound_rtl_paths(pdir, plan).items():
        for c in cands:
            if (root / c).exists():
                bound[k] = (root / c).read_text()
                break
    return plan, pins, masters, bound


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--die", action="append", help="die key (ownership.DIES); default all")
    ap.add_argument("--tsv")
    ap.add_argument("--overrides", help="JSON {die: {item: {reason, note}}}: reviewed reasons (RTL read by hand)")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    root = Path(a.root)
    rows = []
    for die, pdir, _ in OWN.DIES:
        if a.die and die not in a.die:
            continue
        plan, pins, masters, bound = load_inputs(root, pdir)
        ov = json.loads(Path(a.overrides).read_text()).get(die, {}) if a.overrides else {}
        rows += census(die, plan, pins, masters, bound, ov)
    cols = ["die", "item", "kind", "replicas", "reason", "after_class", "after_bank", "family", "note"]
    if a.tsv:
        with open(a.tsv, "w") as f:
            f.write("\t".join(cols) + "\n")
            for r in rows:
                f.write("\t".join(str(r[c]) for c in cols) + "\n")
    s = summarize(rows)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(summary=s, rows=rows), indent=1))
    for die, v in s.items():
        print(f"{die}: {v['before']} -> {v['after']} (types {v['types_before']}->{v['types_after']}, cores "
              f"{v['cores_before']}->{v['cores_after']}); + uniform FT bank -> {v['after_bank']}  {v['reasons']}")


if __name__ == "__main__":
    main()
