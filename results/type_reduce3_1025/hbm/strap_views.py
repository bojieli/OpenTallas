#!/usr/bin/env python3
"""TYPE-REDUCE-3/HBM 10-25: views for the three B2n ID-strap masters (core_templates.py *_strap modules) and for the
old constant variants they replace (one view per old module from views_b2n.json).  Run from the repo root:
    python3 results/type_reduce3_1025/hbm/strap_views.py   -> physical/die_plan/hbm_arch_cores/views_b2n_strap.json
                                                              + results/type_reduce3_1025/hbm/variants.json"""
import hashlib, json, re
from pathlib import Path
R = Path(__file__).resolve().parents[3]
PD = R / "physical/die_plan/hbm_arch/B2n"
plan = json.load(open(PD / "die_plan.json"))
V = json.load(open(R / "physical/die_plan/hbm_arch_cores/views_b2n.json"))
MASTERS = {"ot_hgi_sfu_split3_lane_core_strap": ("sfu_lane", "rtl/hbm_accel/cores_split/ot_hgi_sfu_core_split3/ot_hgi_sfu_split3_lane_core_strap.sv"),
           "ot_hbm_su_pg_lane_exp_core_strap": ("pg_lane_exp", "rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_pg_lane_exp_core_strap.sv"),
           "ot_hbm_su_pg_lanes4_core_strap": ("pg_lanes4", "rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_pg_lanes4_core_strap.sv")}
oldviews = {}
for x in V["view_list"]:
    oldviews.setdefault(x["module"], x)
hc = {}
for tn, t in plan["partition_types"].items():
    for h in t.get("hard_cores", []):
        if h["module"] in MASTERS:
            old = re.search(r"was (\S+) ", h["note"]).group(1)
            hc.setdefault(h["module"], []).append(dict(type=tn, inst=h["inst"], pins_file=h["pins_file"], old=old,
                                                       straps={s["port"]: s["value"] for s in h["straps"]}))
views, variants = [], {}
for m, (ct, wrap) in MASTERS.items():
    rows = sorted(hc[m], key=lambda r: r["pins_file"])
    pf = rows[0]["pins_file"]
    sha = hashlib.sha256((PD / pf).read_bytes()).hexdigest()
    pins = json.load(open(PD / pf))
    olds = sorted({r["old"] for r in rows}, key=lambda s: [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", s)])
    first_old = oldviews[olds[0]]
    views.append(dict(view=f"{m}@{sha[:12]}", module=m, outline_um=json.load(open(PD / "die_plan.json")) and
                      next(h["outline_um"] for t in plan["partition_types"].values() for h in t.get("hard_cores", []) if h["pins_file"] == pf),
                      pins_file=pf, pins_sha256=sha, pins=len(pins), family=first_old.get("family"),
                      instances=[f'{r["type"]}.{r["inst"]}' for r in rows if r["pins_file"] == pf],
                      placed=len(rows), tables_for_module=len({r["pins_file"] for r in rows}), canonical_type=None,
                      recipe_keys=first_old["recipe_keys"], blockers=[],
                      strap_master=dict(canonical_type=ct, wrapper=wrap)))
    vv = {}
    for r in rows:
        vv.setdefault(r["old"], r["straps"])
    variants[m] = [dict(old_module=o, old_view=oldviews[o]["view"], straps=vv[o]) for o in olds]
out = dict(schema=V["schema"], plan=V["plan"], plan_sha256=hashlib.sha256((PD / "die_plan.json").read_bytes()).hexdigest(),
           views=len(views), view_list=views, note="TYPE-REDUCE-3/HBM 10-25: strap master views (results/type_reduce3_1025/hbm/strap_views.py)")
(R / "physical/die_plan/hbm_arch_cores/views_b2n_strap.json").write_text(json.dumps(out, indent=1) + "\n")
(R / "results/type_reduce3_1025/hbm").mkdir(parents=True, exist_ok=True)
(R / "results/type_reduce3_1025/hbm/variants.json").write_text(json.dumps(variants, indent=1) + "\n")
for x in views:
    print(x["view"], x["pins"], x["recipe_keys"], x["placed"])
print({m: len(v) for m, v in variants.items()})
