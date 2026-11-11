#!/usr/bin/env python3
"""DIE-KV-97 CLEAN-SLATE cut (COORD 11-11): ONE combined KV plan event.
  base plan -> cland_sreg_1110 step 1 (landing_status_reg) -> step 2 (ring_hold.sender_ps_types)
            -> every ADOPT positions/orients delta {type: {inst: [x, y, orient] | {origin_um, orient, pins_file}}}
EQ by construction: a delta may only change hard_cores[].origin_um / orient (and pins_file when the orient changes);
any other key change is refused.  Run from a repo root whose tools/die_plan has ring_sender_ps + STATUS-REG.
Per-type overlays first (--types-from PLAN=t1,t2 or PLAN=* for every type that differs from BASE): the kit_wave
item_inputs plans (KV-PLAN-2 e2s2 / kvfix1, kw43 kvrs) fold into the one plan; a type taken from two overlays must be
identical in both, else refused.  Non-partition_types keys of an overlay must equal BASE.
Step 3: phyrev_1111 (kv3_phy/_v1 PHY output-bus station order), after the sreg / ring-hold steps.
INTENT RULE (COORD 02:1x): every delta is given as DELTA.json@INTENT_SHEET; a delta without an existing sheet is refused.
usage: compose_cut.py BASE OUT EV_DIR [--types-from PLAN=t1,t2 ...] [DELTA.json@SHEET ...]
"""
import copy, hashlib, importlib.util, json, sys
from pathlib import Path

def load(p, name):
    s = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def apply_delta(plan, delta, src):
    pt = plan["partition_types"]; rec = []
    for tn, insts in delta.items():
        if tn not in pt: raise SystemExit(f"{src}: {tn} not a partition type")
        hcs = {h["inst"]: h for h in pt[tn].get("hard_cores") or []}
        for inst, v in insts.items():
            if inst not in hcs: raise SystemExit(f"{src}: {tn}.{inst} not a hard core")
            h = hcs[inst]; old = (list(h["origin_um"]), h.get("orient", "R0"), h.get("pins_file"))
            if isinstance(v, dict):
                xy, orient, pf = v["origin_um"], v.get("orient", old[1]), v.get("pins_file", old[2])
            else:
                xy, orient, pf = [v[0], v[1]], (v[2] if len(v) > 2 else old[1]), old[2]
            if orient != old[1] and pf == old[2] and old[2] and f"_f{old[1]}_" in old[2]:
                raise SystemExit(f"{src}: {tn}.{inst} orient {old[1]}->{orient} but pins_file {old[2]} is orient-tagged; give pins_file")
            h["origin_um"] = [float(xy[0]), float(xy[1])]
            if orient != "R0" or "orient" in h: h["orient"] = orient
            if pf is not None: h["pins_file"] = pf
            rec.append(dict(type=tn, inst=inst, before=old[:2], after=[h["origin_um"], h.get("orient", "R0")]))
    return rec

def merge3(base, cur, ovl, where):
    """three-way merge: apply ovl's change vs base onto cur; the same path changed two different ways is refused."""
    if ovl == base:
        return cur
    if cur == base or cur == ovl:
        return copy.deepcopy(ovl)
    if isinstance(base, dict) and isinstance(cur, dict) and isinstance(ovl, dict):
        out = {}
        for k in list(cur) + [k for k in ovl if k not in cur]:
            out[k] = merge3(base.get(k), cur.get(k), ovl.get(k), where + "/" + k)
        return {k: v for k, v in out.items() if v is not None or k in cur or k in ovl}
    if isinstance(base, list) and isinstance(cur, list) and isinstance(ovl, list) and len(base) == len(cur) == len(ovl):
        return [merge3(b, c, o, f"{where}[{i}]") for i, (b, c, o) in enumerate(zip(base, cur, ovl))]
    raise SystemExit(f"overlay conflict at {where}")


def strip(plan):
    q = copy.deepcopy(plan)
    for t in q["partition_types"].values():
        for h in t.get("hard_cores") or []:
            for k in ("origin_um", "orient", "pins_file"): h.pop(k, None)
    return q

def main(a):
    base, out, evd = a[0], a[1], Path(a[2])
    overlays, deltas, sheets, i = [], [], {}, 3
    while i < len(a):
        if a[i] == "--types-from":
            pl, _, ts = a[i + 1].partition("="); overlays.append((pl, ts)); i += 2
        else:
            d, _, sheet = a[i].partition("@")
            if not sheet or not Path(sheet).exists():
                raise SystemExit(f"delta {d}: no intent sheet (INTENT RULE: scored, not adopted)")
            deltas.append(d); sheets[d] = sheet; i += 1
    text = open(base).read()
    if overlays:
        bp = json.loads(text); base_pt = copy.deepcopy(bp["partition_types"]); overlay_rec = {}
        for pl, ts in overlays:
            op = json.load(open(pl))
            for k in set(op) | set(bp):
                if k != "partition_types" and op.get(k) != bp.get(k):
                    raise SystemExit(f"overlay {pl}: top-level key {k} differs from base (not a per-type overlay)")
            names = [t for t in op["partition_types"] if op["partition_types"][t] != base_pt.get(t)] \
                if ts in ("", "*") else ts.split(",")
            for t in names:
                if t not in base_pt:
                    raise SystemExit(f"overlay {pl}: new type {t} (not a per-type overlay)")
                bp["partition_types"][t] = merge3(base_pt[t], bp["partition_types"][t], op["partition_types"][t], f"{t} <- {pl}")
                overlay_rec.setdefault(t, []).append(pl)
        text = json.dumps(bp, indent=1) + "\n"
    else:
        overlay_rec = {}
    s1 = load(evd / "event.py", "s1"); s2 = load(evd / "ringhold_event.py", "s2")
    text, changed = s1.apply(text, s1.DEFAULT_TYPES)
    text = s2.apply(text)
    s3 = load(evd / "phyrev_event.py", "s3")
    text, phy_done = s3.apply(text)
    plan = json.loads(text); pre = copy.deepcopy(plan); recs = []
    for d in deltas:
        recs += [dict(r, delta=d) for r in apply_delta(plan, json.load(open(d)), d)]
    assert strip(plan) == strip(pre), "delta changed a non-position key"
    sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan")); import schema as S
    S.Plan(plan, Path(base).resolve())
    body = json.dumps(plan, indent=1) + "\n" if recs else text
    open(out, "w").write(body)
    # sibling files an overlay type references (pins_file) but the output dir lacks: copy (new inode) from the overlay dir
    import shutil
    copied = []
    for t in plan["partition_types"].values():
        for h in t.get("hard_cores") or []:
            pf = h.get("pins_file")
            if not pf or (Path(out).parent / pf).exists():
                continue
            for pl, _ in overlays:
                cand = Path(pl).parent / pf
                if cand.exists():
                    dst = Path(out).parent / pf; dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(cand.resolve(), dst); copied.append((pf, str(cand))); break
            else:
                raise SystemExit(f"pins_file {pf} found in neither the output dir nor any overlay dir")
    rep = dict(base=base, base_md5=hashlib.md5(open(base, "rb").read()).hexdigest(), out_md5=hashlib.md5(body.encode()).hexdigest(),
               overlays=overlay_rec, copied_files=copied, step1_types=changed, step2_types=list(s2.TYPES), step3_phyrev=phy_done, sheets=sheets, deltas=deltas, moves=recs,
               moved_types=sorted({r["type"] for r in recs}))
    json.dump(rep, open(out + ".report.json", "w"), indent=1)
    print("moves", len(recs), "types", len(rep["moved_types"]), "out", rep["out_md5"])

if __name__ == "__main__":
    main(sys.argv[1:])
