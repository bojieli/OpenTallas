#!/usr/bin/env python3
"""bf-hier 2026-10-10: DS ROM AR / MTP with the hierarchical FULL-RATE BF (owner: BF of record, replaces HALF_PHL).

Re-composes the measured 1,792 field phases (tools/s81/field_phases_1792.py, half_dedicated_ksplit regions, 120 stages)
exactly as its `compose` does, with per-region phase transforms instead of the HALF=1 doubling:

  half_rate         the HALF_PHL row (reproduces composition.json half_rate: the basis the headline was priced on)
  full_rate_bf      the full-rate element, no hierarchy cost (the no-cost bound)
  hier_compact      full rate + HIER cycles on every BF-busy region of a phase (partials +3 vs flat QZE: column boundary
                    register +1, BXST/FXST relays +2; bench/hcol.json lag +3).  Keeps 1,792 pairs / 128 regions / r128
                    (compact 450.144 x 220.32 col + 100.224 front fit the 1,040.256 lane zone): no die / stage change.
  hier_col600_ret   MODEL ONLY: col600 at the 33 mm reticle = 7 columns a half = 84 of 128 regions, 1,176 pairs a
                    BF-flavour die.  Not buildable without the 128 -> 84 region re-bin (K slicing in the allocator,
                    PQ root r128, field RTL) -- NOT priced here.  Modelled as: every phase on a 'bf' stage runs its go->
                    last / go->idle x 128/84 (same rows over 84/128 of the pairs) + HIER, and the q pairs the BF dies
                    lose (1,792 - 1,176 per die x bf stages) open extra q stages, each one measured stage hop.

The delta of each row against half_rate (AR_us, MTP step us) is then applied to the CURRENT headline (later charges,
e.g. the MTP block cycles, are on top of the same half-rate basis):  rate = 1 / (1 / base + delta).

    bf_hier_price.py --regions-dir DIR [--ar-base 1447.7 --mtp-base 4199.4] --out results/.../price.json
"""
import argparse, gzip, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "tools/s81"))
import field_phases_1792 as FP  # noqa: E402

HIER = 3
VAR = "half_dedicated_ksplit"


def phase_cycles(phases, wire, tf):
    tot, nph = 0, len(phases)
    for i, R in enumerate(phases):
        regs = {r: tf(v) for r, v in R.items()}
        if i < nph - 1:
            tot += max(max(v[2] + (wire[int(r)] if v[0] > 0 else 0) for r, v in regs.items()),
                       max(v[2] for v in regs.values())) + 1
        else:
            tot += max(v[1] + wire[int(r)] for r, v in regs.items() if v[1] is not None)
    return tot


def nodes(reg, flav, wires, adder, mk):
    grp = {}
    for name, ph in reg["phases"].items():
        node = ph["node"] if ph["node"].startswith("E1.") else f"L{ph['layer']}.{ph['node']}"
        grp.setdefault(node, {}).setdefault(ph["stage"], []).append(ph)
    out = {}
    for node, st in grp.items():
        per = {s: phase_cycles([p["regions"] for p in lst], wires[flav[s]], mk(flav[s])) + adder * len(lst)
               for s, lst in st.items()}
        out[node] = max(per.values())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions-dir", type=Path, default=FP.OUT / "regions")
    ap.add_argument("--ar-base", type=float, default=1447.7)
    ap.add_argument("--mtp-base", type=float, default=4199.4)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    import dsrom_1m_measure as M
    import dsrom_closure_cost_ledger as LED
    rp = json.loads(FP.REPRICE.read_text())["geoms"][FP.PUB_GEOM]["configs"][FP.PUB_CFG]
    for it, _, rows in LED.ITEMS:
        if it in FP.WIRE_ITEMS:
            FP.WIRE_ITEMS[it] = max(c for _, c, _ in rows)
    adder = sum(FP.PHASE_ADDERS.values())
    rep = {L: t["rep"] for t in M.TYPES.values() for L in t["layers"]}
    c = json.loads(FP.CMP.read_text())["ds_rom"]
    links = json.loads(FP.LINKS.read_text())
    hop_us = links["hop"]["us"] + c["link_fec"]["full_fec"]["ii_hop_cable_us"]
    wires = {fl: FP.wire_table(FP.OUT / "geometry", g)[0] for fl, g in (("bf", "m221bf"), ("q", "m221q"))}
    reg = json.load(gzip.open(a.regions_dir / f"{VAR}.json.gz", "rt"))
    bdir = FP.OUT / "binding" / VAR
    inv = json.loads((bdir / "inventory.json").read_text())
    flav = dict(enumerate(json.loads((bdir / "stage_map.json").read_text())["stage_flavour"]))
    nbf = sum(1 for f in flav.values() if f == "bf")
    S = 128 / 84
    half = lambda v: [v[0], 2 * v[1] + FP.HALF_PIN, 2 * v[2] + FP.HALF_PIN, v[3], v[4]] if v[4] else v
    hier = lambda v: [v[0], v[1] + HIER, v[2] + HIER, v[3], v[4]] if v[4] else v
    ret = lambda v: hier([v[0], math.ceil(v[1] * S), math.ceil(v[2] * S), v[3], v[4]])
    lost_q = (1792 - 1176) * nbf
    extra_q_stages = math.ceil(lost_q / 1792)
    rows = dict(half_rate=(lambda fl: half, 0), full_rate_bf=(lambda fl: (lambda v: v), 0),
                hier_compact=(lambda fl: hier, 0),
                hier_col600_ret=(lambda fl: ret if fl == "bf" else (lambda v: v), extra_q_stages))
    res = dict(tool="tools/s81/bf_hier_price.py", variant=VAR, stages=inv["stages"], bf_stages=nbf, hop_us=hop_us,
               tau=c["tau"], hier_cycles=HIER, base=dict(AR=a.ar_base, MTP=a.mtp_base), rows={})
    for k, (mk, xs) in rows.items():
        nc = nodes(reg, flav, wires, adder, mk)
        add = []
        for n, cyc in nc.items():
            p = rp.get(n)
            if p is None:
                continue
            d = cyc - (p["total_cycles"] + sum(FP.WIRE_ITEMS.values()) + adder)
            if n.startswith("E1."):
                add.append((n, d, 0)); continue
            Lr, suf = n.split(".", 1)
            add += [(f"L{L}.{suf}", d, 0) for L, r in rep.items() if r == int(Lr[1:])]
        ar, mtp = LED.compose([it for it, _, _ in LED.ITEMS], extra=[(f"bfh_{k}", "bf-hier price", add)])
        hops = inv["stages"] + xs - FP.BASE_STAGES
        ar_us = 1e6 / ar + hops * hop_us
        mtp_us = c["tau"] * 1e6 / mtp + hops * hop_us
        res["rows"][k] = dict(AR_us=round(ar_us, 4), MTP_step_us=round(mtp_us, 4), AR_tok_s=round(1e6 / ar_us, 1),
                              MTP_tok_s=round(c["tau"] * 1e6 / mtp_us, 1), stages=inv["stages"] + xs,
                              layer_dies=4 * (inv["stages"] + xs))
    h = res["rows"]["half_rate"]
    for k, r in res["rows"].items():
        dar, dmtp = r["AR_us"] - h["AR_us"], r["MTP_step_us"] - h["MTP_step_us"]
        r["vs_half_AR_pct"] = round(100 * (h["AR_us"] / r["AR_us"] - 1), 2)
        r["vs_half_MTP_pct"] = round(100 * (h["MTP_step_us"] / r["MTP_step_us"] - 1), 2)
        r["on_current_base"] = dict(AR_tok_s=round(1e6 / (1e6 / a.ar_base + dar), 1),
                                    MTP_tok_s=round(c["tau"] * 1e6 / (c["tau"] * 1e6 / a.mtp_base + dmtp), 1))
    res["col600_ret_model"] = dict(regions=84, pairs_per_bf_die=1176, phase_scale=round(S, 4), lost_q_pairs=lost_q,
                                   extra_q_stages=extra_q_stages,
                                   unpriced="128 -> 84 region re-bin of the K slicing (dsrom_bf_geometry_alloc / s73), "
                                            "PQ root r128 -> r84, field RTL region count; mapping not built")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: (r["AR_tok_s"], r["MTP_tok_s"], r["stages"], r["on_current_base"]) for k, r in res["rows"].items()}))


if __name__ == "__main__":
    main()
