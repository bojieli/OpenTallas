#!/usr/bin/env python3
"""PLAN-DELTA/KV 10-25: TYPE-REDUCE KV (COORD/owner-approved items) on the KV die plan v3.9 (main), NON-PATH types only.

Owner priority 10-25: one complete path per design.  KV path (Codex 08:02-08:04): PC_EN_0 -> PHY_EN_0, HG_EN_0 /
HGI_EN_0 heads 0-3, ASTK_EN in hub_Eo, sys_c.  Their types (kv3_pc, kv3_phy, kv3_hg, kv3_hgi_v3, kv3_hub_Eo, kv3_sys_c)
and the hard cores they hold are asserted BYTE-IDENTICAL before/after (the script exits non-zero otherwise).

Edits (in place on PLAN, core_conns.json and cells_evidence.json next to it; deterministic, idempotent):
 (1) hg rows: kv3_hg_v1_r1, r3, r4, r5 and kv3_hg_v2 -> kv3_hg_v1_r2 (the pad-free row type; on v3.9 the five row
     types are identical apart from `module`, kv3_hg_v2 apart from one fault-chain bus name).  kv3_hg_v1_r2 is NOT
     changed (definition byte-identical: its kits / pins stand); the other partitions only switch `type`.  The R8
     per-row pads are replaced by per-row latency published to the compiler (r8_row_publish.py + row_latency.py, run
     by run_delta_kv.sh).
 (2) renames: kv3_hg_v2 i_efault_hg_Q_N_fault -> i_fch_hg_Q_N_q and kv3_pc_v2 i_efault_pc_Q_N_fault -> i_fch_pc_Q_N_q
     (the names of the surviving types); kv3_pc_v2 -> kv3_pc_v1 (pc_v1 unchanged).  pv N/S pairs: chain-bus token
     S/N -> V ONLY on the types of a pair that merges (a merge is refused unless every field except note/module and
     the per-instance pin table are identical after the rename); refused pairs keep their names (no churn).
A merge is refused (reported, nothing changed for it) unless the types are equal in every field except note / module,
core_conns entries are equal and every instance has the identical type-frame pin table (check.py abutment rule).

    delta_kv.py PLAN.json --report R.json
"""
import argparse
import copy
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(R / "tools/die_plan"))
import schema as S  # noqa: E402

PATH_PARTS = ["pc_EN_0", "phy_EN_0", "hg_EN_0", "hgi_EN_0", "hub_Eo", "sys_c"]
RENAME = {"kv3_hg_v2": {"i_efault_hg_Q_N_fault": "i_fch_hg_Q_N_q"},
          "kv3_pc_v2": {"i_efault_pc_Q_N_fault": "i_fch_pc_Q_N_q"}}
# (target that survives, [types merged into it], target unchanged?)
MERGES = [("kv3_hg_v1_r2", ["kv3_hg_v1_r1", "kv3_hg_v1_r3", "kv3_hg_v1_r4", "kv3_hg_v1_r5", "kv3_hg_v2"], True),
          ("kv3_pc_v1", ["kv3_pc_v2"], True)]
PV_PAIRS = [("kv3_pv", "kv3_pv_v8"), ("kv3_pv_v1", "kv3_pv_v9"), ("kv3_pv_v3", "kv3_pv_v10"),
            ("kv3_pv_v5", "kv3_pv_v11"), ("kv3_pv_v7", "kv3_pv_v12")]
PV_RX = re.compile(r"^([io]_(?:fch|efault)_pv)_[SN](_N_.*)$")
TAG = "v3.9pd (PLAN-DELTA/KV 10-25)"


def canon(x):
    if isinstance(x, dict):
        return {k: canon(v) for k, v in x.items()}
    if isinstance(x, list):
        return sorted(canon(v) for v in x) if all(isinstance(v, str) for v in x) else [canon(v) for v in x]
    return x


def strip(t):
    x = copy.deepcopy(t)
    x.pop("note", None)
    x.pop("module", None)
    x["buses"] = sorted(x.get("buses", []), key=lambda b: b["name"])
    return json.dumps(x, sort_keys=True)


def pin_tables(raw):
    """check.py abutment rule: per instance {(bus, bit): (layer, type face, type coord)} of every port end"""
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


def rename(raw, conns, bm):
    """bm: type -> {old bus: new bus}; renames type buses, port ends and core_conns refs"""
    ptype = {p["name"]: p["type"] for p in raw["partitions"]}
    n = defaultdict(int)
    for tn, m in bm.items():
        names = {b["name"] for b in raw["partition_types"][tn]["buses"]}
        for o, nn in m.items():
            if o not in names or (nn in names and nn not in m):
                raise SystemExit(f"delta_kv: bad rename {tn} {o} -> {nn}")
        for b in raw["partition_types"][tn]["buses"]:
            if b["name"] in m:
                b["name"] = m[b["name"]]
                n["type_buses"] += 1
        if conns is not None and tn in conns:
            s = json.dumps(conns[tn])
            for o, nn in m.items():
                n["core_conns_refs"] += s.count(f'"bus:{o}"')
                s = s.replace(f'"bus:{o}"', f'"bus:{nn}"')
            conns[tn] = json.loads(s)
    for p in raw["ports"]:
        for side in ("src", "dst"):
            e = p[side]
            m = bm.get(ptype.get(e["part"]), {})
            if e.get("bus") in m:
                e["bus"] = m[e["bus"]]
                n["port_ends"] += 1
    return dict(n)


def check_merge(raw, conns, tgt, olds, tabs, insts):
    why = []
    names = [tgt] + olds
    sig = {o: strip(raw["partition_types"][o]) for o in names}
    for o in olds:
        a, b = json.loads(sig[tgt]), json.loads(sig[o])
        if a != b:          # value compare: 1 == 1.0 (some ft_slots numbers are int in one type, float in another)
            why.append(f"{o} vs {tgt}: fields differ {sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))}")
    cs = {o: json.dumps(canon(conns.get(o)), sort_keys=True) for o in names}
    if len(set(cs.values())) > 1:
        why.append("core_conns differ")
    ref = None
    for o in names:
        for part in sorted(insts[o]):
            if ref is None:
                ref = (part, tabs.get(part, {}))
            elif tabs.get(part, {}) != ref[1]:
                d = set(tabs.get(part, {}).items()) ^ set(ref[1].items())
                why.append(f"pin table {part} != {ref[0]} ({len(d)} entries)")
                break
    return why


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    pp = Path(a.plan)
    raw = json.loads(pp.read_text())
    sd = pp.parent
    conns = json.loads((sd / "core_conns.json").read_text())
    cev = json.loads((sd / "cells_evidence.json").read_text())
    T = raw["partition_types"]
    rep = dict(input=str(pp), types_before=len(T), path_parts=PATH_PARTS)
    ptype = {p["name"]: p["type"] for p in raw["partitions"]}
    path_types = sorted({ptype[p] for p in PATH_PARTS})
    path_cores = sorted({h["module"] for t in path_types for h in T[t].get("hard_cores", [])})
    before = {t: json.dumps(T[t], sort_keys=True) for t in path_types}
    rep.update(path_types=path_types, path_cores=path_cores)
    if all(t not in T for _, olds, _ in MERGES for t in olds):
        rep["note"] = "already applied (idempotent no-op)"
    insts = defaultdict(list)
    for p in raw["partitions"]:
        insts[p["type"]].append(p["name"])
    # renames needed by the hg / pc merges (only where the old name is still there: idempotent)
    bm = {t: {o: n for o, n in m.items() if any(b["name"] == o for b in T[t]["buses"])}
          for t, m in RENAME.items() if t in T}
    bm = {t: m for t, m in bm.items() if m}
    # pv pairs: try neutral names in a scratch copy, keep only the pairs that merge
    pvm = {}
    for s_, n_ in PV_PAIRS:
        for t in (s_, n_):
            if t in T:
                m = {b["name"]: f"{x.group(1)}_V{x.group(2)}" for b in T[t]["buses"] for x in [PV_RX.match(b["name"])] if x}
                if m:
                    pvm[t] = m
    trial = copy.deepcopy(raw)
    tconns = copy.deepcopy(conns)
    rename(trial, tconns, {**bm, **pvm})
    tabs = pin_tables(trial)
    tinsts = defaultdict(list)
    for p in trial["partitions"]:
        tinsts[p["type"]].append(p["name"])
    merges, refused, keep_pv = [], [], {}
    for tgt, olds, unchanged in MERGES + [(s_, [n_], False) for s_, n_ in PV_PAIRS]:
        olds = [o for o in olds if o in T]
        if not olds:
            continue
        why = check_merge(trial, tconns, tgt, olds, tabs, tinsts)
        if tgt in path_types or any(o in path_types for o in olds):
            why.append("PATH type")
        if why:
            refused.append(dict(type=tgt, from_types=olds, reasons=why[:6]))
            continue
        merges.append((tgt, olds, unchanged))
        for t in [tgt] + olds:          # rename only the types of an accepted merge (no churn on refused ones)
            if t in pvm or t in bm:
                keep_pv[t] = {**bm.get(t, {}), **pvm.get(t, {})}
    rep["renames"] = rename(raw, conns, keep_pv)
    rep["rename_map"] = keep_pv
    for tgt, olds, unchanged in merges:
        tdef = json.dumps(T[tgt], sort_keys=True)
        for p in raw["partitions"]:
            if p["type"] in olds:
                p["type"] = tgt
        for o in olds:
            del T[o]
            conns.pop(o, None)
            cev.get("cells_per_type", {}).pop(o, None)
        if unchanged:
            assert json.dumps(T[tgt], sort_keys=True) == tdef
        rep.setdefault("merges", []).append(dict(type=tgt, from_types=olds, target_definition_unchanged=unchanged,
                                                 instances=sorted(n for o in [tgt] + olds for n in insts[o])))
    rep["refused"] = refused
    for t in path_types:
        if json.dumps(T[t], sort_keys=True) != before[t]:
            raise SystemExit(f"delta_kv: PATH type {t} changed")
    if TAG not in raw.get("note", ""):
        raw["note"] = raw.get("note", "") + f" | {TAG}: TYPE-REDUCE KV on non-path types: hg_v1_r1/r3/r4/r5 + hg_v2 " \
            "-> hg_v1_r2 (R8 row pads -> published per-row latency lat_v39pd/row_latency.json), pc_v2 -> pc_v1, " \
            "pv N/S pairs with neutral chain-bus names where identical; path types untouched"
    rep["types_after"] = len(T)
    pp.write_text(json.dumps(raw, indent=1) + "\n")
    (sd / "core_conns.json").write_text(json.dumps(conns, separators=(",", ":")))   # file style kept
    (sd / "cells_evidence.json").write_text(json.dumps(cev, indent=1))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"delta_kv: types {rep['types_before']} -> {rep['types_after']}; merged "
          f"{[(m['type'], m['from_types']) for m in rep.get('merges', [])]}; refused "
          f"{[(r['type'], r['reasons'][:2]) for r in refused]}", file=sys.stderr)


if __name__ == "__main__":
    main()
