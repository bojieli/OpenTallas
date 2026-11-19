#!/usr/bin/env python3
"""Hard-core clock tap retarget (lane DIE-CORETAP-1119, owner: fix every die-level check finding).

DIE-LEVEL-CHECK-1119 found on every die that hard-core early taps are fed late: the plan's declared core insertion
(clock.taps[kind core].insertion_ps / insertion_ff_ps) is below the core's SIGNED clock latency, and the die clock tree
delivers even less early-ness than the plan declares.  This die-agnostic tool fixes both halves from one source:

    core_tap_retarget.py rows  PLAN --root SRC --out-dir OUT [--proof PROOF] [--basis mean|etm_max] [--tools DIR]
        rows.tsv / rows.json: per (type, core tap) the declared insertion, the signed latency (signed pin-register MEAN
        from the core's clock contract / signoff.json = basis 'mean', the canonical plan basis; ETM
        max_clock_tree_path = basis 'etm_max', reported always), the new insertion and the new early offset
        early = max(0, signed - common latency (+ type core_tap_lead_ps)) per corner (schema.core_tap_early_ps).
        With --proof (a die proof holding tap_arrivals_<C>.json): tap_targets.json, the per die-port tree target
        {target_early, die_early (measured: partition regular-tap mean - core tap arrival), retarget_ps = how much
        earlier the die tree must deliver that tap}.  die_clock.py --core-early pad reads the same early offsets from
        the applied plan (plan_tap_early); kit trees (ot_clk, link_htree, templates) take tap_targets.json.
    core_tap_retarget.py apply PLAN ROWS.json --out NEWPLAN        the plan rows applied (insertion_ps/insertion_ff_ps)
    core_tap_retarget.py shift PROOF TARGETS.json --out NEWPROOF   MODEL of a tree that delivers the targets: core tap
        arrivals moved by -retarget_ps (late/early/fall), everything else linked; for a before/after die STA only.
    core_tap_retarget.py kitcheck KIT_DIR ROWS.json --type TYPE    kit-side check: the kit SDC core tap source latency
        (constraint.sdc TT, core_taps_ff.sdc FF) must equal -new early, and a clock.tap_offset per-port row on a core
        tap port must be re-measured (its o_p carries the old early delivery).

    core_tap_retarget.py pairs ROWS.json STA.json [STA.json ...]   which worst die STA pairs (intra/seam hold, setup,
        skew per corner) have an endpoint on an UNSIGNED core tap (declared insertion), a SIGNED core tap, or a regular
        tap; plus per-module counts of unsigned early core taps.

SIGNED-ONLY rule (COORD 11-19): a core tap's early target is set only from a SIGNED core (clock contract / signoff.json
verdict SIGNED); --basis etm_max only changes WHICH signed number (ETM max_clock_tree_path of the signed view instead of
the pin-register mean).  A core without a signed record keeps its declared insertion and is flagged UNSIGNED.  Evidence:
offset rows and region.early helped HEAD (signed cores) but made KV intra hold worse (-222 -> -253 / -260 TT): its
worst pairs sit on unsigned cores with declared insertion.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOL_PS = 0.5
FIELDS = ["type", "tap", "port", "inst", "module", "pins", "status", "basis", "common_TT", "common_FF",
          "old_ins_TT", "old_ins_FF", "signed_mean_TT", "signed_mean_FF", "etm_max_TT", "etm_max_FF",
          "new_ins_TT", "new_ins_FF", "old_early_TT", "old_early_FF", "new_early_TT", "new_early_FF",
          "signed_target_TT", "signed_target_FF", "source"]


def _tools(d):
    d = str(Path(d or HERE).resolve())
    if d not in sys.path:
        sys.path.insert(0, d)
    import schema as S
    import cores as C
    try:
        import core_clock_contract as CC
    except ImportError:          # an older published tree: the signed-mean reader of this tree
        sys.path.append(str(HERE))
        import core_clock_contract as CC
    return S, C, CC


def _types(raw):
    pt = raw["partition_types"]
    return pt if isinstance(pt, dict) else {t["name"]: t for t in pt}


def _early(S, P, tp, c, t):
    try:
        return S.core_tap_early_ps(P, tp, c, t)
    except TypeError:            # trees before the type-override basis (schema.core_tap_early_ps(P, tp, corner))
        return S.core_tap_early_ps(P, tp, c)


def _lead(S, t, c):
    try:
        return S.core_tap_lead_ps(t, c)
    except AttributeError:
        return 0.0


def _common(S, P, c, t):
    try:
        return S.common_latency_ps(P, c, t)
    except TypeError:
        return S.common_latency_ps(P, c)


_PINS_CACHE = {}


def _clock_pins(C, core, root):
    key = (core.get("lib"), core.get("lef"), core.get("module"), str(root))
    if key not in _PINS_CACHE:
        _PINS_CACHE[key] = sorted(C.clock_pins(core, root)) or ["*"]
    return _PINS_CACHE[key]


def _tap_inst_pins(S, C, t, tp, root):
    """(inst, hard core dict, [pins]) of a kind-core tap (core_tap_rows naming rule)."""
    hc = {h["inst"]: h for h in t.get("hard_cores", []) or []}
    nm = tp["name"]
    for i in sorted(hc, key=len, reverse=True):
        if nm == i:
            return i, hc[i], _clock_pins(C, hc[i], root)
        if nm.startswith(i + "."):
            pin = nm[len(i) + 1:]
            return i, hc[i], list(tp.get("merged_clock_ports") or [pin])
    return None, None, []


_SIGNED_CACHE = {}


def _signed(CC, C, core, pins, root, t):
    """({TT, FF} signed mean over the tap's pins or None, {TT, FF} ETM max or None, source); one read per (lib, pins)."""
    key = (core.get("lib"), core.get("module"), tuple(pins), str(root))
    if key not in _SIGNED_CACHE:
        _SIGNED_CACHE[key] = _signed_read(CC, C, core, pins, root)
    return _SIGNED_CACHE[key]


def _signed_read(CC, C, core, pins, root):
    mean, src = None, ""
    try:
        con = CC.load(core, root, require_signed=True)
        sel = [p for p in pins if p in con] or list(con)
        mean = {c: st.mean(con[p]["corners"][c.lower()]["mean_ps"] for p in sel) for c in ("TT", "FF")}
        src = "; ".join(sorted({str(con[p]["contract_source"]) for p in sel}))
    except Exception as e:      # ContractError / missing view: no signed mean
        src = f"no signed mean: {str(e)[:160]}"
    etm = None
    lib = core.get("lib")
    if lib:
        f = {"TT": C.resolve(lib, root)}
        f["FF"] = f["TT"].with_name(f["TT"].name.replace("_tt.lib", "_ff.lib"))
        if all(p.is_file() for p in f.values()):
            v = {c: C.lib_clocks(f[c]) for c in f}
            sel = {c: [v[c][p]["rise"] for p in pins if p in v[c]] or [x["rise"] for x in v[c].values()] for c in v}
            if all(sel.values()):
                etm = {c: max(sel[c]) for c in sel}
    return mean, etm, src


def build_rows(plan_path, root, basis="mean", tools=None, signed_ins=None):
    """signed_ins {module: {TT, FF, source}}: signed insertions measured in a record outside the view directory (e.g. a
    view pack not yet applied to the plan); used as the signed number of that module, labelled with its source."""
    S, C, CC = _tools(tools)
    raw = json.loads(Path(plan_path).read_text())
    P = S.Plan(raw, path=plan_path) if "path" in S.Plan.__init__.__code__.co_varnames else S.Plan(raw)
    rows = []
    for tn in sorted(P.types):
        t = P.types[tn]
        if ((t.get("clock") or {}).get("core_taps")) != "early":
            continue
        for port, _x, _y, tp in S.core_taps(P, tn):
            r = dict(type=tn, tap=tp.get("name", ""), port=port, basis=basis)
            r.update({f"common_{c}": round(_common(S, P, c, t), 3) for c in ("TT", "FF")})
            r.update({f"old_ins_{c}": round(S.core_tap_insertion_ps(tp, c), 3) for c in ("TT", "FF")})
            r.update({f"old_early_{c}": round(_early(S, P, tp, c, t), 3) for c in ("TT", "FF")})
            if "core_group" in tp:
                r.update(inst="", module="", pins="", status="SKIP_CORE_GROUP", source="core_groups (parent budget)")
                rows.append(_fill(r))
                continue
            inst, core, pins = _tap_inst_pins(S, C, t, tp, root)
            r.update(inst=inst or "", module=(core or {}).get("module", ""), pins=",".join(pins))
            if core is None:
                r.update(status="SKIP_NO_HARD_CORE", source="tap names no hard_cores[] inst (bare hard wrapper)")
                rows.append(_fill(r))
                continue
            mean, etm, src = _signed(CC, C, core, pins, root, t)
            if (signed_ins or {}).get(core.get("module")):
                o = signed_ins[core["module"]]
                mean = etm = {"TT": float(o["TT"]), "FF": float(o["FF"])}
                src = f"SIGNED (record): {o.get('source', '')}"
            r.update({f"signed_mean_{c}": round(mean[c], 3) if mean else None for c in ("TT", "FF")})
            r.update({f"etm_max_{c}": round(etm[c], 3) if etm else None for c in ("TT", "FF")})
            # SIGNED-ONLY rule (COORD 11-19, DIE-CORETAP-1119): the target comes from a SIGNED core only; an unsigned
            # core keeps its declared insertion and is flagged UNSIGNED (its declared number is not moved by this tool)
            new = (mean if basis == "mean" else etm) if mean else None
            r["source"] = src if (basis == "mean" or not mean) else f"SIGNED view, ETM max_clock_tree_path {core.get('lib')}"
            if not new:
                r.update(status="UNSIGNED", **{f"new_ins_{c}": r[f"old_ins_{c}"] for c in ("TT", "FF")},
                         **{f"new_early_{c}": r[f"old_early_{c}"] for c in ("TT", "FF")})
                rows.append(_fill(r))
                continue
            ntp = dict(tp, insertion_ps=new["TT"], insertion_ff_ps=new["FF"])
            r.update({f"new_ins_{c}": round(new[c], 3) for c in ("TT", "FF")})
            r.update({f"new_early_{c}": round(_early(S, P, ntp, c, t), 3) for c in ("TT", "FF")})
            # signed target incl. LATE (negative): signed insertion - common (+ lead), not clipped at 0
            r.update({f"signed_target_{c}": round(new[c] - _common(S, P, c, t) + _lead(S, t, c), 3) for c in ("TT", "FF")})
            ch = any(abs(r[f"new_ins_{c}"] - r[f"old_ins_{c}"]) >= TOL_PS for c in ("TT", "FF"))
            r["status"] = "CHANGE" if ch else "KEEP"
            rows.append(_fill(r))
    meta = dict(schema="opentallas.core_tap_retarget.v1", plan=str(plan_path),
                plan_sha256=hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(), root=str(root), basis=basis,
                tools=str(Path(tools or HERE).resolve()))
    return meta, rows, P, S


def _fill(r):
    return {k: r.get(k) for k in FIELDS}


def _part_types(P):
    return {n: p["type"] for n, p in P.parts.items()}


def tap_targets(rows, P, proof, late=False, modules=None):
    """{die port: {part, type, tap, TT/FF: {target_early, die_early, retarget_ps}}}: die port t_<part>__<kit port>.
    late: target = signed_target (a core faster than the common latency is delivered LATE); modules: only taps of
    these core modules get a target (region-local retarget), every other tap keeps its delivered arrival."""
    by = {(r["type"], r["port"]): r for r in rows}
    ptype = _part_types(P)
    out = {}
    for c in ("TT", "FF"):
        taps = json.loads((Path(proof) / f"tap_arrivals_{c}.json").read_text())["taps"]
        reg = defaultdict(list)
        for t in taps:
            if "__clk_t" in t["port"]:
                reg[t["part"]].append(t["late_ps"])
        for t in taps:
            part, kp = t.get("part"), t["port"].rsplit("__", 1)[-1]
            r = by.get((ptype.get(part), kp))
            if r is None or not reg.get(part) or (modules and r["module"] not in modules):
                continue
            m = st.mean(reg[part])
            de = m - t["late_ps"]
            tgt = float(r[f"signed_target_{c}"] if late and r.get(f"signed_target_{c}") is not None
                        else r[f"new_early_{c}"])
            e = out.setdefault(t["port"], dict(part=part, type=r["type"], tap=r["tap"], module=r["module"],
                                               status=r["status"]))
            e[c] = dict(target_early=round(tgt, 3), plan_early_old=r[f"old_early_{c}"], die_early=round(de, 3),
                        retarget_ps=round(tgt - de, 3), reg_mean_ps=round(m, 3))
    return out


def cmd_rows(a):
    sig = json.loads(Path(a.signed_ins).read_text()) if a.signed_ins else None
    meta, rows, P, S = build_rows(a.plan, a.root, a.basis, a.tools, sig)
    od = Path(a.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    with open(od / "rows.tsv", "w") as f:
        w = csv.DictWriter(f, FIELDS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    (od / "rows.json").write_text(json.dumps(dict(meta, rows=rows), indent=1))
    n = defaultdict(int)
    for r in rows:
        n[r["status"]] += 1
    print("ROWS", dict(n), "->", od / "rows.json")
    by = defaultdict(list)
    for r in rows:
        if r["status"] == "CHANGE":
            by[r["module"]].append(r)
    for m, rs in sorted(by.items()):
        r = rs[0]
        print(f"  {m} n{len(rs)} ins TT {r['old_ins_TT']}->{r['new_ins_TT']} FF {r['old_ins_FF']}->{r['new_ins_FF']} "
              f"early TT {r['old_early_TT']}->{r['new_early_TT']} FF {r['old_early_FF']}->{r['new_early_FF']}")
    if a.proof:
        tg = tap_targets(rows, P, a.proof, a.late, set(a.modules.split(",")) if a.modules else None)
        (od / "tap_targets.json").write_text(json.dumps(dict(meta, proof=str(a.proof), targets=tg), indent=1))
        for c in ("TT", "FF"):
            v = [x[c]["retarget_ps"] for x in tg.values() if c in x]
            if v:
                print(f"TARGETS {c} ports {len(v)} retarget_ps {min(v):.1f}..{max(v):.1f} late>50 "
                      f"{sum(x > 50 for x in v)} early>50 {sum(x < -50 for x in v)}")
    return 0


def apply_rows(raw, rows, tag="DIE-CORETAP-1119"):
    types = _types(raw)
    done = 0
    for r in rows:
        if r["status"] != "CHANGE":
            continue
        t = types[r["type"]]
        hit = [tp for tp in (t.get("clock") or {}).get("taps", []) or []
               if tp.get("kind") == "core" and tp.get("name") == r["tap"]]
        if len(hit) != 1:
            raise SystemExit(f"type {r['type']}: core tap {r['tap']} matches {len(hit)} plan taps")
        tp = hit[0]
        old = (tp.get("insertion_ps"), tp.get("insertion_ff_ps"))
        tp["insertion_ps"], tp["insertion_ff_ps"] = r["new_ins_TT"], r["new_ins_FF"]
        tp["budget_owner"] = f"SIGNED:{r['source']}" if r["basis"] == "mean" else f"ETM:{r['source']}"
        tp["note"] = (str(tp.get("note", "")) + f" | {tag}: insertion TT/FF {old[0]}/{old[1]} -> {r['new_ins_TT']}/"
                      f"{r['new_ins_FF']} ({r['basis']}), early {r['old_early_TT']}->{r['new_early_TT']}").lstrip(" |")
        done += 1
    return done


def cmd_apply(a):
    raw = json.loads(Path(a.plan).read_text())
    rows = json.loads(Path(a.rows).read_text())["rows"]
    n = apply_rows(raw, rows)
    Path(a.out).write_text(json.dumps(raw, indent=1))
    print("APPLIED", n, "core taps ->", a.out)
    return 0


def cmd_shift(a):
    src, out = Path(a.proof).resolve(), Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    tg = json.loads(Path(a.targets).read_text())["targets"]
    for p in src.iterdir():
        if not p.name.startswith("tap_arrivals_"):
            os.symlink(p, out / p.name)
    for f in sorted(src.glob("tap_arrivals_*.json")):
        c = f.stem.split("_")[-1]
        d = json.loads(f.read_text())
        n = 0
        for t in d["taps"]:
            e = tg.get(t["port"], {}).get(c)
            if not e:
                continue
            dl = float(e["retarget_ps"])
            for k in ("late_ps", "early_ps", "fall_late_ps", "fall_early_ps"):
                if t.get(k) is not None:
                    t[k] = float(t[k]) - dl
            n += 1
        d["core_tap_retarget_model"] = dict(targets=str(a.targets), shifted_taps=n,
                                            note="MODEL: die tree delivers the retarget; not a built tree")
        (out / f.name).write_text(json.dumps(d))
        print("SHIFT", c, n, "core taps")
    return 0


_LAT = re.compile(r"set_clock_latency\s+-source\s+-clock\s+clk\s+(-?[0-9.]+)\s+\[get_ports\s+(\S+?)\]")


def kit_check(kit, rows, tn, unit_ps=1.0, offsets=None):
    """[(port, corner, sdc_ps, want_ps, verdict)] for the kit core tap ports of type tn."""
    want = {r["port"]: r for r in rows if r["type"] == tn}
    out = []
    for c, fn in (("TT", "constraint.sdc"), ("FF", "core_taps_ff.sdc")):
        f = Path(kit) / fn
        if not f.is_file():
            continue
        for m in _LAT.finditer(f.read_text()):
            v, port = float(m.group(1)) * unit_ps, m.group(2)
            r = want.get(port)
            if r is None:
                continue
            w = -float(r[f"new_early_{c}"])
            out.append((port, c, v, w, "OK" if abs(v - w) < TOL_PS else "MISTIMED"))
    for port in sorted(set(offsets or {}) & set(want)):
        out.append((port, "TT/FF", None, None, "RE-MEASURE tap_offset (o_p carries the old early delivery)"))
    return out


def cmd_kitcheck(a):
    rows = json.loads(Path(a.rows).read_text())["rows"]
    offs = {}
    if a.plan:
        raw = json.loads(Path(a.plan).read_text())
        offs = (((raw.get("clock") or {}).get("tap_offset") or {}).get("per_port_ps") or {}).get(a.type) or {}
    res = kit_check(a.kit, rows, a.type, a.unit_ps, offs)
    for r in res:
        print("\t".join("" if x is None else str(x) for x in r))
    bad = sum(r[4] != "OK" for r in res)
    print("KITCHECK", a.type, "ports", len(res), "not OK", bad)
    return 1 if bad else 0


def _port_map(rows):
    """{kit core port name per type: row}; die ports are t_<part>__<kit port>."""
    return {(r["type"], r["port"]): r for r in rows}


def pair_report(rows, sta, plan_parts):
    """[(corner, class, kind, launch, capture, slack/skew, launch_tag, capture_tag)]: tag = UNSIGNED:<module> |
    SIGNED:<module> | regular."""
    pm = _port_map(rows)

    def tag(port):
        part, _, kp = port[2:].rpartition("__") if port.startswith("t_") else ("", "", port)
        r = pm.get((plan_parts.get(part), kp))
        if r is None:
            return "regular"
        return ("UNSIGNED:" if r["status"] == "UNSIGNED" or r["signed_mean_TT"] is None else "SIGNED:") + str(r["module"])
    out = []
    for c, cd in (sta.get("corners") or {}).items():
        for cl, v in (cd.get("classes") or {}).items():
            if not isinstance(v, dict):
                continue
            for kind in ("worst_hold", "worst_setup"):
                w = v.get(kind)
                if isinstance(w, dict) and w.get("launch"):
                    out.append((c, cl, kind, w["launch"], w["capture"], v.get(kind + "_slack_ps"), tag(w["launch"]),
                                tag(w["capture"])))
            for sk, a, b in (v.get("worst_skew") or [])[:3]:
                out.append((c, cl, "worst_skew", a, b, sk, tag(a), tag(b)))
    return out


def cmd_pairs(a):
    d = json.loads(Path(a.rows).read_text())
    rows = d["rows"]
    raw = json.loads(Path(d["plan"]).read_text())
    parts = {p["name"]: p["type"] for p in raw["partitions"]}
    un = defaultdict(int)
    for r in rows:
        if r["status"] == "UNSIGNED" or (r["status"] != "SKIP_CORE_GROUP" and r["signed_mean_TT"] is None):
            un[(r["module"], r["old_early_TT"] > 0)] += 1
    print("UNSIGNED early core taps (module, declared early>0): n")
    for (m, e), n in sorted(un.items(), key=lambda x: -x[1]):
        print(f"  {m}\tearly>0={e}\t{n}")
    for f in a.sta:
        for row in pair_report(rows, json.loads(Path(f).read_text()), parts):
            print("PAIR", Path(f).parent.name, *row, sep="\t")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("rows")
    r.add_argument("plan")
    r.add_argument("--root", required=True, help="source tree the plan's view paths resolve against")
    r.add_argument("--out-dir", required=True)
    r.add_argument("--proof")
    r.add_argument("--basis", choices=["mean", "etm_max"], default="mean")
    r.add_argument("--tools", help="die_plan tools of the plan's own tree (default: this tree)")
    r.add_argument("--signed-ins", help="JSON {module: {TT, FF, source}} of signed insertions from records")
    r.add_argument("--late", action="store_true", help="tree targets allow LATE delivery (signed - common < 0)")
    r.add_argument("--modules", help="comma list: tree targets only for these core modules (region-local)")
    p = sp.add_parser("apply")
    p.add_argument("plan")
    p.add_argument("rows")
    p.add_argument("--out", required=True)
    s = sp.add_parser("shift")
    s.add_argument("proof")
    s.add_argument("targets")
    s.add_argument("--out", required=True)
    k = sp.add_parser("kitcheck")
    k.add_argument("kit")
    k.add_argument("rows")
    k.add_argument("--type", required=True)
    k.add_argument("--plan")
    k.add_argument("--unit-ps", type=float, default=1.0, help="ps per SDC time unit (ASAP7 kits: 1)")
    q = sp.add_parser("pairs")
    q.add_argument("rows")
    q.add_argument("sta", nargs="+")
    a = ap.parse_args(argv)
    return dict(rows=cmd_rows, apply=cmd_apply, shift=cmd_shift, kitcheck=cmd_kitcheck, pairs=cmd_pairs)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
