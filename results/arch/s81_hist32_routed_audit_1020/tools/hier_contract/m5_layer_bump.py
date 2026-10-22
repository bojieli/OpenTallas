#!/usr/bin/env python3
"""M5 tile layer contract (coordinator 2026-10-12, results/arch/hier_contract_1011/layer_usage_1012.md).

New tile routes cap signals AND PG at M5 (PG stripes on M5 as pins, pins on M4/M5, pin keepout above on M6); M6 only by an
explicit die-lead exception per slot (layer_cap M6 + layer_cap_grant); parent straps on M6; die signals may use M6/M7 over
tiles; M8/M9 die power + global.

  contracts   bump every die contract (versioned): new layer_defaults; each plain tile slot gets layer_cap/pg/strap/
              signal_max = M5/M5/M6/M5 for new routes, and its closed view's own cap as view_cap (valid only while
              child_lint passes at that cap); clusters / hard IP / die-layer elements keep their layers (layer_rule).
              Idempotent: re-run after a contract generator rewrites a die JSON.
  priority    results/arch/hier_contract_1011/m5_reroute_priority.json: closed blocks whose signals reach M7+ (they break
              even the old <= M6 rule), tiered by die region congestion; agents re-route opportunistically, top first.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HC = ROOT / "results/arch/hier_contract_1011"
DIES = ["qwen_rom.json", "qwen_kv.json", "r25gq.json", "s81.json"]
WHEN = "2026-10-12"
SRC = "results/arch/hier_contract_1011/layer_usage_1012.md (coordinator decision, main f964f6b2d)"
DEFAULTS = {
    "rule": "m5_tile_cap_20261012",
    "layer_cap": "M5", "pg_layer": "M5", "strap_layer": "M6", "signal_max_layer": "M5",
    "pin_layers": ["M4", "M5"], "pin_keepout_layer": "M6",
    "exception": {"layer_cap": "M6", "pg_layer": "M6", "strap_layer": "M7", "signal_max_layer": "M6",
                  "needs": "slot layer_cap_grant '<die lead>: <reason>' (pin-dense edge relays / stations only)"},
    "parent_strap_layer": "M6", "die_signal_layers_over_tiles": ["M6", "M7"], "die_power_global_layers": ["M8", "M9"],
    "closed_views": "keep their own cap as slot view_cap; valid only while tools/hier_contract/child_lint.py passes at it "
                    "(strap = cap + 1); re-route at M5 per m5_reroute_priority.json",
    "source": SRC,
}
HARD_IP = re.compile(r"phy|ucie|serdes|ckbump|clkrx")


def metal(x):
    m = re.fullmatch(r"M(\d+)", str(x or ""))
    return int(m.group(1)) if m else None


def measured_top() -> dict:
    d = json.loads((HC / "layer_usage_1012.json").read_text())
    out = {}
    for b in d["per_block"]:
        for k in (b["block"], b["element"]):
            out[k] = max(out.get(k, 0), b["top_signal_layer"])
    return out


# cells whose die slot is a hardened cluster although the slot note says hardened_block (cluster of clusters):
# hfd_quant = ot_hgi_quant_unit -> ot_hgi_quant_wide_h clusters (OT_HARD_CHILDREN) -> qw_* tiles.
CLUSTER_CELLS = {"hfd_quant"}
CHILD_GRANT = ("coordinator 2026-10-12 11:40 (el1012-hbm-verdicts.log): child of hardened cluster {p}; the M5 cap "
               "protects die tracks over DIE-placed tiles only, children follow the cluster's plan (PG on M6, cluster M7)")


def classify(s: dict, parents: set, clusters: set) -> str:
    if HARD_IP.search(s["cell"]):
        return "hard_ip"
    note = str(s.get("notes", ""))
    if "luster" in note or "two_level" in note or s["name"] in parents or s["cell"] in CLUSTER_CELLS:
        return "cluster"                                  # keeps its M7 plan; die tracks above it are M8/M9
    if (metal(s.get("signal_max_layer")) or 0) >= 8:      # signals / pins on the die's M8/M9: the die lead re-plans
        return "die_layer"
    if s.get("parent") in clusters:
        return "cluster_child"                            # inside a hardened cluster: M6 cap (coordinator 10-12 11:40)
    return "tile_m5"


def bump(path: Path, meas: dict) -> dict:
    raw = path.read_text()
    d = json.loads(raw)
    if d.get("layer_defaults", {}).get("rule") == DEFAULTS["rule"]:
        prev, ver = d["layer_defaults"].get("previous"), d["version"]
    else:
        prev, ver = d.get("layer_defaults"), d["version"] + 1
    d["version"], d["updated"] = ver, WHEN
    d["layer_defaults"] = dict(DEFAULTS, previous=prev)
    n = {"tile_m5": 0, "cluster_child": 0, "cluster": 0, "hard_ip": 0, "die_layer": 0, "view_violates_own_cap": 0, "already_m5": 0,
         "pin_replan": 0}
    for s in d["slots"]:                             # already bumped: restore the view's layers to re-derive
        if s["kind"] != "die" and "view_layers" in s:
            s.update(s["view_layers"])
    parents = {s.get("parent") for s in d["slots"]} - {None}
    clusters = {s["name"] for s in d["slots"] if s["kind"] != "die" and classify(s, parents, set()) == "cluster"}
    for s in d["slots"]:
        if s["kind"] == "die":
            continue
        rule = classify(s, parents, clusters)
        s["layer_rule"] = rule
        n[rule] += 1
        if rule not in ("tile_m5", "cluster_child"):
            for k in ("view_layers", "view_cap", "view_status", "layer_cap", "pin_replan"):
                s.pop(k, None)
            if s.get("layer_cap_grant", "").startswith("coordinator 2026-10-12 11:40"):
                s.pop("layer_cap_grant")
            continue
        if rule == "cluster_child" and not s.get("layer_cap_grant"):
            s.update(layer_cap="M6", layer_cap_grant=CHILD_GRANT.format(p=s["parent"]))
        own = max(metal(s["pg_layer"]) or 0, metal(s["signal_max_layer"]) or 0)
        s["view_layers"] = {k: s[k] for k in ("pg_layer", "strap_layer", "signal_max_layer")}
        s["view_cap"] = f"M{own}"
        top = meas.get(s["cell"])
        if top and top > own:
            s["view_status"] = (f"INVALID: closed view routes signals on M{top} above its own cap M{own}; "
                                f"re-route at M5 (m5_reroute_priority.json)")
            n["view_violates_own_cap"] += 1
        elif own <= 5:
            s["view_status"] = "M5-compliant"
            n["already_m5"] += 1
        else:
            s["view_status"] = (f"legacy cap M{own}" + (f" (measured top signal M{top})" if top else " (no closed view measured)")
                                + ": valid while child_lint passes at view_cap; re-route at M5 opportunistically")
        if s.get("layer_cap") != "M6" or not s.get("layer_cap_grant"):
            s.update(layer_cap="M5", pg_layer="M5", strap_layer="M6", signal_max_layer="M5")
        else:
            s.update(pg_layer="M6", strap_layer="M7", signal_max_layer="M6")
        hi = sorted({p.get("layer") for p in s.get("pins", []) if (metal(p.get("layer")) or 0) > metal(s["layer_cap"])}
                    | ({s["clock_entry"].get("layer")} if (metal(s.get("clock_entry", {}).get("layer")) or 0) >
                       metal(s["layer_cap"]) else set()))
        if hi:
            s["pin_replan"] = f"contract pins / clock entry on {'/'.join(hi)} above the cap: move to M4 (H) / M5 (V) before a new route"
            n["pin_replan"] += 1
        else:
            s.pop("pin_replan", None)
        s["version"] = ver
    log = d.setdefault("changelog", [])
    entry = {"version": ver, "when": WHEN,
             "change": f"M5 tile layer contract ({SRC}): new tile routes cap signals AND PG at M5 (strap M6, pins M4/M5, "
                       f"keepout M6; M6 by layer_cap_grant only; die signals M6/M7 over tiles; M8/M9 die power/global). "
                       f"{n['tile_m5']} die-placed tile slots bumped, {n['cluster_child']} cluster children at M6 (coordinator 10-12 11:40) (view_cap = closed view's own cap; {n['view_violates_own_cap']} "
                       f"views INVALID: signals above their own cap; {n['already_m5']} already <= M5; {n['pin_replan']} need "
                       f"a pin re-plan off M6+); unchanged: {n['cluster']} cluster, {n['hard_ip']} hard IP, "
                       f"{n['die_layer']} die-layer slots. Tool: tools/hier_contract/m5_layer_bump.py contracts"}
    log[:] = [e for e in log if not (isinstance(e, dict) and "M5 tile layer contract" in str(e.get("change")))] + [entry]
    path.write_text(json.dumps(d, indent=1, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
    return {"die": d.get("die"), "version": ver, **n}


# ------------------------------------------------------------------------------------------------ re-route priority
DIE_OF = [(re.compile(r"^(qkd_|ot_qkvd)"), "qwen_kv"),
          (re.compile(r"^(qfd_|ot_qwen|qwen)"), "qwen_rom"),
          (re.compile(r"^(hfd_|hgi_|ot_hgi|ot_hbm|ot_hdc|ot_su12|hbm_)"), "hbm"),
          (re.compile(r"^(dsfd_|ot_dsrom|ot_s81|ot_dshbm|s81)"), "ds_s81")]
# congested die regions (die logs 2026-10-12): Qwen ROM heavy M6/M8 H rows (tree-block root rows at 5,167 um pitch,
# qwendie-1012 e9) -- the whole tile array sits in those banded rows; HBM hub centre x 12-16 / y 10-15 mm (HGI lane-group
# buses lge/lgw, VM/vmr, hc_eng tap, vmw_dma, sfu tap) and slice faces (hbmdie-1011 v10, hbm-b2 GRT 07:40 residual bins).
HBM_HOT = re.compile(r"^(hgi_|ot_hgi|hfd_(hc|vm|lg|mcast|svc|stn|index|su|sfu|coll|cmdproc|gath)|ot_hbm_index|ot_su12|"
                     r"ot_hdc_v41x_idx_hslice)")


def priority(out: Path) -> dict:
    d = json.loads((HC / "layer_usage_1012.json").read_text())
    slots = {}
    for f in DIES:
        c = json.loads((HC / f).read_text())
        for s in c["slots"]:
            if s["kind"] != "die":
                slots.setdefault(s["cell"], (c["die"], s))
    rows = []
    for b in d["per_block"]:
        if b["top_signal_layer"] < 7:
            continue
        hit = slots.get(b["block"]) or slots.get(b["element"])
        die = None
        if hit:
            die = {"qwen_rom": "qwen_rom", "qwen_kv": "qwen_kv", "hbm_r25gq": "hbm", "ds_rom_s81_layer1": "ds_s81"}.get(hit[0], hit[0])
        if die is None:
            die = next((dd for rx, dd in DIE_OF if rx.search(b["block"]) or rx.search(b["element"])), None)
        region, tier = None, 3
        if die == "qwen_rom":
            region, tier = "Qwen ROM die: M6/M8 heavy H rows (tile array rows; qwendie-1012 e9)", 1
        elif die == "hbm" and (HBM_HOT.search(b["block"]) or HBM_HOT.search(b["element"])):
            region, tier = "HBM die: hub centre / slice faces (HGI lane groups, VM, HC, svc/stn, sfu/idx taps)", 1
        elif die in ("hbm", "qwen_kv", "ds_s81"):
            region, tier = f"{die} die (not a reported hotspot)", 2
        su = b.get("sig_util_lef", {})
        hi = sum(su.get(L, 0.0) for L in ("M6", "M7", "M8", "M9"))
        rows.append({"block": b["block"], "element": b["element"], "job": b["job"], "kind": b["kind"],
                     "area_mm2": round(b["area_mm2"], 5), "top_signal_layer": f"M{b['top_signal_layer']}",
                     "m6_m9_signal_util": round(hi, 4), "m7_m9_signal_util": round(hi - su.get("M6", 0.0), 4),
                     "die": die, "contract_slot": (hit[1]["name"] if hit else None), "region": region, "tier": tier})
    proj = {x["block"]: x for x in d["alt_contract_reroute"]["blocks"]}
    for r in rows:
        p = proj.get(r["block"])
        r["proj_m4m5_util_at_m5"] = p and p.get("proj_m4m5_util")
        r["difficulty"] = p and p.get("band")
    rows.sort(key=lambda r: (r["tier"], -r["m7_m9_signal_util"], -r["area_mm2"], r["block"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    tiers = {t: sum(1 for r in rows if r["tier"] == t) for t in (1, 2, 3)}
    rec = {"schema": "opentallas.hier_contract.m5_reroute_priority.v1", "date": WHEN, "source": SRC,
           "rule": "closed blocks whose signals reach M7+ (break even the old <= M6 tile rule, collide with parent straps "
                   "and the die's M7); re-route OPPORTUNISTICALLY through tools/ref_tile at the M5 cap, top rank first -- "
                   "no mass re-route. Tier 1 = under a congested die region (Qwen ROM M6/M8 rows; HBM hub / slice faces), "
                   "2 = other die-placed, 3 = die unknown / not die-placed. Within a tier: most M7-M9 signal wire first.",
           "n": len(rows), "tiers": tiers, "blocks": rows}
    out.write_text(json.dumps(rec, indent=1) + "\n")
    return {"n": len(rows), "tiers": tiers}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["contracts", "priority"])
    ap.add_argument("--dies", nargs="*", default=DIES)
    a = ap.parse_args(argv)
    if a.cmd == "contracts":
        meas = measured_top()
        for f in a.dies:
            print(json.dumps(bump(HC / f, meas)))
    else:
        print(json.dumps(priority(HC / "m5_reroute_priority.json")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
