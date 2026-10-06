"""Map the field / SU records of tools/dsrom_1m_allmeasured.py onto the S81 graph's node names.

Representative layers (one per type, golden 1M operands): SU records L0 (sliding: L0, L1), L3 (CSA re-use), L20
(full: compressor + indexer + candidates; also L2/L8/L14's extra nodes), L24 (re-index), head.  Every returned
entry is (seconds, source, class, modelled_seconds)."""
from __future__ import annotations

import json
from pathlib import Path

SINKHORN_UNIT_S = 41 / 151.9e6     # ot_hdc_sinkhorn: 41 unit clocks measured (hdc_v41_sinkhorn_campaign), routed fmax 151.9 MHz


def rep_layer(L, have):
    if L in (0, 1):
        return "L0"
    if L == 20:
        return "L20"
    if L in (24, 28, 32, 36):
        return "L24"
    return "L3"


def su_rows(g, su):
    nodes = dict(su["nodes"]) if isinstance(su["nodes"], list) else su["nodes"]
    flat = su["node_us"]
    out = {}
    for name in g.nodes:
        head, _, suf = name.partition(".")
        if head == "head":
            key, rep = name, "head"
        elif head.startswith("L") and head[1:].isdigit():
            rep = rep_layer(int(head[1:]), None)
            key = f"{rep}.{suf}"
            if key not in nodes and f"L20.{suf}" in nodes:      # full-layer extras (L2/L8/L14 compressor, indexer)
                key = f"L20.{suf}"
        else:
            continue
        x = nodes.get(key)
        if x is not None:
            cdc = x.get("model_cdc_us", 0.0) * 1e-6
            t = x["wired_us"] * 1e-6
            if suf.endswith("hc.sinkhorn"):
                out[name] = (t + SINKHORN_UNIT_S + cdc, f"{key}: SU front (row max + exp) wired RTL {x['wired_us']} us "
                             f"+ ot_hdc_sinkhorn 41 clocks at routed 151.9 MHz; CDC {x.get('model_cdc_us', 0)} us modelled",
                             "measured", cdc)
            elif x["part"] != "whole":
                lay = su.get("node_us_by_layer", {}).get(key.split(".")[0], {})
                qd = (lay.get(suf) or {}).get("qdq")
                if qd and qd.get("exact"):
                    q = qd["wired_us"] * 1e-6
                    out[name] = (t + q + cdc, f"{key}: RoPE wired RTL {x['wired_us']} us + ot_hdc_actquant QDQ wired "
                                 f"RTL {qd['wired_us']} us (1 instance, golden-exact)", "measured", cdc)
                else:
                    q = x["model_us"] * 1e-6
                    out[name] = (t + q + cdc, f"{key}: RoPE wired RTL {x['wired_us']} us + quantiser (QDQ) MODELLED "
                                 f"{x['model_us']} us", "partial", q + cdc)
            else:
                out[name] = (t + cdc, f"{key}: wired RTL (BCAST 22 / RET 15 stages) {x['wired_us']} us, golden-exact"
                             + (f"; CDC {x['model_cdc_us']} us modelled" if cdc else ""), "measured", cdc)
            continue
        if suf == "attn.pv":
            f = flat["attn.pv@T128" if rep == "L0" else "attn.pv"]
            out[name] = (f["us"] * 1e-6, "attention tile P.V pass, last score -> last P.V (w11_attn_ploader pwords2_psup2, "
                                         "full geometry, synthetic vectors, exact)", "measured", 0.0)
            continue
        if suf in ("ffn.top6", "ffn.top6_order"):
            f = flat[suf]
            out[name] = (f["us"] * 1e-6, "one ot_hdc_select unit, 384 router scores (the 64-unit + merge form the "
                                         "model prices is unbuilt)", "measured", 0.0)
    return out


FIELD_REP = {0: 0, 1: 1, 2: 2, 8: 2, 14: 2, 20: 20, 21: 21, 22: 21, 23: 21}


def field_rep(L):
    if L in FIELD_REP:
        return FIELD_REP[L]
    if L in (24, 28, 32, 36):
        return 24
    return 3 if L < 20 else 21


# CLAUDE DS-REPRICE 2026-10-06: the field wire comes from the wired S81 r8 die (per-frame round trip at 430.56 um a
# stage + the hub stations on the return path, results/rtl/dsrom_field_reprice_r8_20261006/reprice.json) instead of
# the r7 floorplan's 80 cycles a phase.  FIELD_GEOM selects the element-frame geometry; None = the old 80-cycle charge.
REPRICE = Path(__file__).resolve().parents[1] / "results/rtl/dsrom_field_reprice_r8_20261006/reprice.json"
FIELD_GEOM = "f157.68"
_RP = {}


def reprice_table(field, geom):
    """node name -> re-priced entry for this field record (config asbuilt / baseline / pq) at `geom`, or None"""
    if geom is None or not REPRICE.exists():
        return None
    if "rec" not in _RP:
        _RP["rec"] = json.loads(REPRICE.read_text())
    cfg = field.get("config", "asbuilt")
    return _RP["rec"]["geoms"][geom]["configs"][cfg]


def field_rows(g, field, geom="default"):
    """field.json node_summary: per measured layer (0, 1, 2, 3, 20, 21, 24) the slowest die's one-region RTL time
    + field wire stages (r8 die per-region round trip, reprice.json; geom None = the old S81 floorplan 80 a phase);
    other layers take their type's representative (expert-path times are those of the representative layer's
    golden-routed experts)."""
    geom = FIELD_GEOM if geom == "default" else geom
    rp = reprice_table(field, geom)
    by = {x["node"]: x for x in field["node_summary"]}
    out = {}
    for name in g.nodes:
        head, _, suf = name.partition(".")
        if not (head.startswith("L") and head[1:].isdigit()):
            if head.startswith("E") and name in by:
                x = by[name]
            else:
                continue
        else:
            L = int(head[1:])
            x = by.get(name) or by.get(f"L{field_rep(L)}.{suf}")
            if x is None:
                continue
        if rp is None:
            us, wsrc = x["total_us_s81_floorplan_wire"], "+ S81 floorplan wire stages"
        else:
            e = rp[x["node"]]
            us, wsrc = e["us"], (f"+ r8 die wire {e['wire_cycles']} cyc over {e['phases']} phase(s) (per-region round "
                                 f"trip + hub return stations, {geom})")
        out[name] = (us * 1e-6,
                     f"{x['node']}: one-region full-shape ROM field RTL (S81 canonical placement), {x['rows_checked']} "
                     f"rows exact={x['exact']}, {wsrc}", "measured" if x["exact"] else
                     "measured_not_exact", 0.0)
    return out
