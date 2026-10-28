#!/usr/bin/env python3
"""DIE-HEAD-11 (RM143 G0C fix): plan pins, PG landing and connectivity for the 4 hd_lep0N PAIR children
(u_core.u.g_pp[k].u_pair, module ot_s81hd_lep_pair, LEP-C0 placement).

    python3 tools/s81_head/head_lep_pair_pins.py [--plan physical/die_plan/s81_head/die_plan.json]

  * writes PLANDIR/cores/lep_pair_pins.json: one plan pin view shared by the 4 children (one module, one child kit),
    core frame, centre form (0.042 um inside the face, as cores/elemA_pins.json), on the symmetric M4-M7 plan tracks:
      W face  coll_i[513:0] on M4, coll_o[511:0] on M6 (lsb at low y) -- the die collective windows: W for g_pp[1..2],
              E for g_pp[3] (MY), N-west of g_pp[0] (L-fan, cos +0.88);
      S face  K-side inputs (k_lo_v, k_lo_d[552:0], k_li_r, k_rxv) on M5, outputs (k_lo_r, k_li_v, k_li_d[552:0],
              k_flt[2:0]) on M7 (lsb at low x) -- toward the parent u_lep (south band, g_tx[k] SRAM);
      rst_n   one M5 pin at the core centre (as elemA); clk enters through the core clock entry (not a face pin).
  * hard_cores[g_pp[k]].pins_file = cores/lep_pair_pins.json;
  * partition_types.hd_lep0N.core_pg_connect = true (its 45 parent SRAM + the children get kit PDN vias);
  * PLANDIR/core_conns.json[hd_lep0N] = coll_i/coll_o -> bus:coll_i<k>/coll_o<k>, K side -> leaf: u_lep g_tx[k] bank 2.
Idempotent.  Ports are read from rtl/dsrom_sys/s81_head/ot_s81hd_lep_pair.sv."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN_FILE = "cores/lep_pair_pins.json"
INSET = 0.042
EDGE_UM = 2.0          # keep pins off the core corners
TRACK = {"M4": (0.048, 0.024), "M5": (0.048, 0.024), "M6": (0.064, 0.032), "M7": (0.064, 0.032)}
SV = "rtl/dsrom_sys/s81_head/ot_s81hd_lep_pair.sv"
K_IN = ("k_lo_v", "k_lo_d", "k_li_r", "k_rxv")
K_OUT = ("k_lo_r", "k_li_v", "k_li_d", "k_flt")


def ports(sv_text):
    hdr = sv_text[sv_text.index("module ot_s81hd_lep_pair"):]
    hdr = hdr[hdr.index(")(") + 2:hdr.index(");")]
    out, cur_w = {}, 1
    for tok in re.split(r",", hdr):
        tok = tok.strip()
        m = re.match(r"(?:(input|output)\s+wire\s*)?(?:\[(\d+):0\])?\s*(\w+)$", tok)
        if not m:
            raise SystemExit(f"cannot parse port token {tok!r}")
        if m.group(1):
            cur_w = int(m.group(2)) + 1 if m.group(2) else 1
        elif m.group(2):
            cur_w = int(m.group(2)) + 1
        out[m.group(3)] = cur_w
    return out


def bits(names, W):
    return [n if W[n] == 1 else f"{n}[{i}]" for n in names for i in range(W[n])]


def spread(names, layer, lo, hi):
    p, off = TRACK[layer]
    k0, k1 = int((lo - off) / p) + 1, int((hi - off) / p)
    n = len(names)
    if k1 - k0 + 1 < n:
        raise SystemExit(f"{n} pins do not fit {layer} [{lo},{hi}]")
    return [(nm, round(off + (k0 + (i * (k1 - k0)) // max(n - 1, 1)) * p, 6)) for i, nm in enumerate(names)]


def build(W, cw, ch):
    pins = []
    for nm, layer in (("coll_i", "M4"), ("coll_o", "M6")):
        for b, y in spread(bits([nm], W), layer, EDGE_UM, ch - EDGE_UM):
            pins.append(dict(name=b, layer=layer, x=INSET, y=y))
    for grp, layer in ((K_IN, "M5"), (K_OUT, "M7")):
        for b, x in spread(bits(grp, W), layer, EDGE_UM, cw - EDGE_UM):
            pins.append(dict(name=b, layer=layer, x=x, y=INSET))
    p, off = TRACK["M5"]
    pins.append(dict(name="rst_n", layer="M5", x=round(off + round((cw / 2 - off) / p) * p, 6), y=round(ch / 2, 3)))
    seen = set(W) - {"clk"}
    got = {re.sub(r"\[\d+\]$", "", q["name"]) for q in pins}
    if got != seen:
        raise SystemExit(f"pin set mismatch: missing {sorted(seen - got)} extra {sorted(got - seen)}")
    return pins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="physical/die_plan/s81_head/die_plan.json")
    a = ap.parse_args()
    plan_f = ROOT / a.plan
    pd = plan_f.parent
    plan = json.loads(plan_f.read_text())
    t = plan["partition_types"]["hd_lep0N"]
    pairs = [h for h in t["hard_cores"] if h["module"] == "ot_s81hd_lep_pair"]
    if len(pairs) != 4 or len({tuple(h["outline_um"]) for h in pairs}) != 1:
        raise SystemExit("expected 4 ot_s81hd_lep_pair cores of one outline")
    cw, ch = pairs[0]["outline_um"]
    W = ports((ROOT / SV).read_text())
    pins = build(W, cw, ch)
    doc = dict(source=f"plan pin view (DIE-HEAD-11 RM143 fix): {SV} ports, no child kit yet", macro="ot_s81hd_lep_pair",
               outline_um=[cw, ch], excluded_pg=["VDD", "VSS"], excluded_clock=["clk"],
               faces=dict(W="coll_i M4 / coll_o M6", S="K-side in M5 / out M7"), pins=pins)
    (pd / PIN_FILE).write_text(json.dumps(doc, indent=1) + "\n")
    for h in pairs:
        h["pins_file"] = PIN_FILE
    t["core_pg_connect"] = True
    plan_f.write_text(json.dumps(plan, indent=2) + "\n")
    cc_f = pd / "core_conns.json"
    cc = json.loads(cc_f.read_text()) if cc_f.is_file() else {}
    ent = {}
    for h in pairs:
        k = int(re.search(r"g_pp\[(\d)\]", h["inst"]).group(1))
        leaf = f"u_core.u.u_lep.u.g_tx[{k}].g_safe_write.u_m.g_bank[2].u_m"
        if not any(c["inst"] == leaf for c in t["contents"]):
            raise SystemExit(f"partner leaf {leaf} not in hd_lep0N contents")
        e = {"coll_i": [f"bus:coll_i{k}"], "coll_o": [f"bus:coll_o{k}"]}
        for p in K_IN + K_OUT:
            e[p] = [f"leaf:{leaf}"]
        ent[h["inst"]] = e
    cc["hd_lep0N"] = ent
    cc_f.write_text(json.dumps(cc, indent=1) + "\n")
    print(json.dumps(dict(pins=len(pins), cores=len(pairs), pins_file=PIN_FILE, core_conns=len(ent))))


if __name__ == "__main__":
    main()
