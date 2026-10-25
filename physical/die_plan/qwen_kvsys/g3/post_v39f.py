#!/usr/bin/env python3
"""KV-PLAN3F 10-25 (plan v3.9f = v3.9e + this pass): TYPE-REDUCE KV items approved by COORD 10-25
(claude/type-reduce-1025@befcf3f66 results/type_reduce_1025/REPORT.md section KV).  No geometry, pin, slot or core change:
types that already have one logic signature and one pin table become one type.

(1) neutral chain-bus names (names only; buses are opaque ids: bind.py / gen_rtl.py reach the leaves through ports and
    lanes, never through the bus name):
      kv3_hg_v2  i_efault_hg_Q_N_fault -> i_fch_hg_Q_N_q   (row 6's fault-OR chain input; its source is row 7's end leaf)
      kv3_pc_v2  i_efault_pc_Q_N_fault -> i_fch_pc_Q_N_q   (same, pc column)
      kv3_pv*    {i,o}_{fch,efault}_pv_{S,N}_N_* -> ..._pv_V_N_*   (column-side token S/N -> V on every pv type)
    in the type buses, the ports and core_conns.json.
(2) type merges (partitions re-pointed; orient stays the whole-instance orient; nothing is unioned: a merge is refused
    unless the types are equal in every field except note / module / ft-slot station count, their core_conns entries are
    equal, and every instance has the identical type-frame pin table, check.py abutment rule):
      kv3_hg_v1  <- kv3_hg_v1_r1 .. r5 + kv3_hg_v2       (8 -> 3 hg types with kv3_hg, kv3_hg_v3)
      kv3_pc_v1  <- kv3_pc_v1 + kv3_pc_v2                 (4 -> 3)
      kv3_pv     <- kv3_pv + kv3_pv_v8      (S0 + N0)     pv N/S pairs: 13 -> 8 when all five pairs merge
      kv3_pv_v1  <- kv3_pv_v1 + kv3_pv_v9   (S1 + N1)
      kv3_pv_v3  <- kv3_pv_v3 + kv3_pv_v10  (S3 + N3)
      kv3_pv_v5  <- kv3_pv_v5 + kv3_pv_v11  (S5 + N5)
      kv3_pv_v7  <- kv3_pv_v7 + kv3_pv_v12  (S7 + N7)
    A pair whose ft slots differ only in station count takes the larger count per slot (stations are raised for the
    405-um hop rule and never lowered); the lanes that gain a station are in the report (lat delta: run_v39f.sh).
    The R8 per-row alignment pads that made hg_v1_r1..r5 distinct are removed by r8/r8_row_publish.py (run_v39f.sh) and
    published per row in lat_v39f/row_latency.json (g3/row_latency_v39f.py) for the compiler (KV-TOK static schedule).
usage: post_v39f.py PLAN.json OUT_PLAN.json --side DIR (core_conns.json / cells_evidence.json, in place)
       --report R.json
"""
import argparse
import copy
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(R / "tools/die_plan"))
import schema as S  # noqa: E402

RENAME = {
    "kv3_hg_v2": {"i_efault_hg_Q_N_fault": "i_fch_hg_Q_N_q"},
    "kv3_pc_v2": {"i_efault_pc_Q_N_fault": "i_fch_pc_Q_N_q"},
}
PV_RX = re.compile(r"^([io]_(?:fch|efault)_pv)_[SN](_N_.*)$")
MERGES = [
    ("kv3_hg_v1", ["kv3_hg_v1_r1", "kv3_hg_v1_r2", "kv3_hg_v1_r3", "kv3_hg_v1_r4", "kv3_hg_v1_r5", "kv3_hg_v2"],
     "kv3_hg_v1_part"),
    ("kv3_pc_v1", ["kv3_pc_v1", "kv3_pc_v2"], None),
    ("kv3_pv", ["kv3_pv", "kv3_pv_v8"], None),
    ("kv3_pv_v1", ["kv3_pv_v1", "kv3_pv_v9"], None),
    ("kv3_pv_v3", ["kv3_pv_v3", "kv3_pv_v10"], None),
    ("kv3_pv_v5", ["kv3_pv_v5", "kv3_pv_v11"], None),
    ("kv3_pv_v7", ["kv3_pv_v7", "kv3_pv_v12"], None),
]
NOTE = "v3.9f (KV-PLAN3F, TYPE-REDUCE KV 10-25): merged from {}"


def bus_map(raw):
    """type -> {old bus: new bus}"""
    out = {}
    for tn, t in raw["partition_types"].items():
        m = dict(RENAME.get(tn, {}))
        if tn.startswith("kv3_pv"):
            for b in t.get("buses", []):
                x = PV_RX.match(b["name"])
                if x:
                    m[b["name"]] = f"{x.group(1)}_V{x.group(2)}"
        if m:
            names = {b["name"] for b in t.get("buses", [])}
            for o, n in m.items():
                if o not in names:
                    raise SystemExit(f"post_v39f: {tn} has no bus {o}")
                if n in names and n not in m:
                    raise SystemExit(f"post_v39f: {tn} already has a bus {n}")
            out[tn] = m
    return out


def rename(raw, conns, rep):
    bm = bus_map(raw)
    ptype = {p["name"]: p["type"] for p in raw["partitions"]}
    nb = np_ = nc = 0
    for tn, m in bm.items():
        for b in raw["partition_types"][tn]["buses"]:
            if b["name"] in m:
                b["name"] = m[b["name"]]
                nb += 1
        cc = conns.get(tn)
        if cc:
            s = json.dumps(cc)
            for o, n in m.items():
                k = s.count(f'"bus:{o}"')
                s = s.replace(f'"bus:{o}"', f'"bus:{n}"')
                nc += k
            conns[tn] = canon(json.loads(s))
    for p in raw["ports"]:
        for side in ("src", "dst"):
            e = p[side]
            m = bm.get(ptype.get(e["part"]), {})
            if e.get("bus") in m:
                e["bus"] = m[e["bus"]]
                np_ += 1
    rep["renames"] = dict(type_buses=nb, port_ends=np_, core_conns_refs=nc,
                          map={tn: m for tn, m in sorted(bm.items())})


def canon(x):
    """core_conns entry with every reference list sorted (the lists are sets of bus / core references)"""
    if isinstance(x, dict):
        return {k: canon(v) for k, v in x.items()}
    if isinstance(x, list):
        return sorted(canon(v) for v in x) if all(isinstance(v, str) for v in x) else [canon(v) for v in x]
    return x


def strip(t):
    """the merge signature: every field except note / module / ft-slot station counts"""
    x = copy.deepcopy(t)
    x.pop("note", None)
    x.pop("module", None)
    x["buses"] = sorted(x.get("buses", []), key=lambda b: b["name"])     # port order is not a signature
    for s in x.get("ft_slots", []):
        s.pop("stations", None)
    return json.dumps(x, sort_keys=True)


def pin_tables(raw):
    """check.py abutment rule: per instance, {(bus, bit): (layer, type face, type coord)} of every port end"""
    P = S.Plan(copy.deepcopy(raw), None)
    tab = defaultdict(dict)
    for pid, pr in P.ports.items():
        try:
            pins = P.port_pins(pid)
        except (ValueError, KeyError):
            continue
        f = pr["face"]
        ends = []
        if pr["src"]["part"] != S.DIE_PART:
            ends.append((pr["src"], f))
        if pr["dst"]["part"] != S.DIE_PART:
            ends.append((pr["dst"], S.OPP[f] if pr["src"]["part"] != S.DIE_PART else f))
        for e, df in ends:
            part = e["part"]
            tf = P.type_face(part, df)
            o = P.orient(part)
            w, h = P.ptype(part)["outline_um"]
            ox, oy = P.parts[part]["origin_um"]
            if df in "EW":
                flip, base, ext = o in ("MX", "R180"), oy, h
            else:
                flip, base, ext = o in ("MY", "R180"), ox, w
            for bit, ln, c in pins:
                tc = (ext - (c - base)) if flip else (c - base)
                tab[part][(e["bus"], bit)] = (ln, tf, round(tc, 4))
    return tab


def merge(raw, side, rep):
    T = raw["partition_types"]
    insts = defaultdict(list)
    for p in raw["partitions"]:
        insts[p["type"]].append(p["name"])
    tabs = pin_tables(raw)
    conns = side["core_conns"]
    done, refused = [], []
    for new, olds, module in MERGES:
        olds = [o for o in olds if o in T]
        why = []
        sig = {o: strip(T[o]) for o in olds}
        if len(set(sig.values())) > 1:
            for o in olds[1:]:
                if sig[o] != sig[olds[0]]:
                    a, b = json.loads(sig[olds[0]]), json.loads(sig[o])
                    ks = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
                    for k in ks:
                        if isinstance(a.get(k), list) and isinstance(b.get(k), list):
                            sa = {json.dumps(v, sort_keys=True) for v in a[k]}
                            sb = {json.dumps(v, sort_keys=True) for v in b[k]}
                            why.append(f"{o} vs {olds[0]}: {k} +{len(sb - sa)} -{len(sa - sb)} "
                                       f"(e.g. {sorted(sb - sa)[:1] or sorted(sa - sb)[:1]})")
                        else:
                            why.append(f"{o} vs {olds[0]}: {k} differs")
        cs = {o: json.dumps(canon(conns.get(o)), sort_keys=True) for o in olds}
        if len(set(cs.values())) > 1:
            why.append(f"core_conns differ: {sorted(set(cs) - {olds[0]})}")
        ref = None
        for o in olds:
            for part in sorted(insts[o]):
                if ref is None:
                    ref = (part, tabs.get(part, {}))
                elif tabs.get(part, {}) != ref[1]:
                    d = set(tabs.get(part, {}).items()) ^ set(ref[1].items())
                    why.append(f"pin table {part} != {ref[0]} ({len(d)} entries, e.g. {sorted(d)[0]})")
                    break
        if why:
            refused.append(dict(type=new, from_types=olds, reasons=why[:12]))
            continue
        base = copy.deepcopy(T[olds[0]])
        st_raised = []
        for s in base.get("ft_slots", []):
            ks = {o: next(x["stations"] for x in T[o]["ft_slots"] if x["name"] == s["name"]) for o in olds}
            k = max(ks.values())
            for o, k0 in ks.items():
                if k0 != k:
                    st_raised.append(dict(slot=s["name"], from_type=o, parts=sorted(insts[o]), before=k0, after=k))
            s["stations"] = k
        if module:
            base["module"] = module
        base["note"] = (base.get("note", "") + " | " + NOTE.format(", ".join(
            f"{o} ({', '.join(sorted(insts[o]))})" for o in olds))).lstrip(" |")
        for o in olds:
            del T[o]
        T[new] = base
        for p in raw["partitions"]:
            if p["type"] in olds:
                p["type"] = new
        for key in ("core_conns", "cells_evidence"):
            d = side.get(key)
            if d is None:
                continue
            tgt = d["cells_per_type"] if key == "cells_evidence" else d
            if olds[0] in tgt:
                v = tgt[olds[0]]
                for o in olds:
                    tgt.pop(o, None)
                tgt[new] = v
        done.append(dict(type=new, from_types=olds, instances=sorted(n for o in olds for n in insts[o]),
                         module=base["module"], stations_raised=st_raised,
                         g2_carry=f"geometry, outline, hard cores and pin table identical to {olds[0]} "
                                  f"(checked per instance): {', '.join(olds)} G2 carries over unchanged"))
    rep["merges"] = done
    rep["refused"] = refused
    rep["types_after"] = len(raw["partition_types"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--side", required=True, help="dir with core_conns.json, cells_evidence.json")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    sd = Path(a.side)
    files = dict(core_conns="core_conns.json", cells_evidence="cells_evidence.json")
    side = {k: json.loads((sd / f).read_text()) if (sd / f).exists() else None for k, f in files.items()}
    if side["core_conns"] is None:
        raise SystemExit("post_v39f: core_conns.json missing in --side")
    rep = dict(input=str(a.plan), types_before=len(raw["partition_types"]))
    rename(raw, side["core_conns"], rep)
    merge(raw, side, rep)
    raw["note"] = raw.get("note", "") + " | v3.9f (KV-PLAN3F 10-25): TYPE-REDUCE hg 8->3 (R8 row pads -> published " \
        "per-row latency lat_v39f/row_latency.json), pv N/S pair merges w/ neutral chain-bus names, pc_v1 = pc_v2"
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    for k, f in files.items():
        if side[k] is not None:
            (sd / f).write_text(json.dumps(side[k], indent=1) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"post_v39f: types {rep['types_before']} -> {rep['types_after']}; merged "
          f"{[m['type'] for m in rep['merges']]}; refused {[(r['type'], r['reasons'][:2]) for r in rep['refused']]}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
