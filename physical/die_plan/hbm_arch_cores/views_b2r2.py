#!/usr/bin/env python3
"""ELEM-HBM 10-24: inventory of the hardened views the HBM B2r2 plan needs (one per (module, pins table)).

    python3 views_b2r2.py --plan B2r2/die_plan.json --out views_b2r2.json

A view = (module, outline, pins-file sha256).  Replicas (same module + identical pin table) share one view.  Families,
recipe source (core-hbm-1023 harden data: recipes_split / recipes_other / canonical_ports_split) and the blockers that
need the plan owner (HBM-ARCH) are recorded per view.
"""
import argparse
import collections
import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARDEN = HERE.parent / "hbm" / "cores" / "harden"

FAMILY = [
    (r"^hnx_rp3lp3h_", "SM"), (r"^ot_hgi_sfu_core_split3__", "SFU"), (r"^ot_hbm_idx_score_quarter_static__", "IDXS"),
    (r"^ot_hbm_idx_", "IDX"), (r"^ot_hgi_coll_tkm_m_tp192__", "TKM"), (r"^ot_hbm_su_static_pgslice_lg__", "PGS"),
    (r"^ot_hbm_hc_bankq", "HCB"), (r"^ot_hbm_hc_", "HC"), (r"^(ot_hfd_coll_|ot_hgi_coll_)", "COLL"),
    (r"^ot_hbm_su_|^ot_hgi_sfu_programme", "SU"), (r"^(hfd_vms|hfd_hgi_vm|ot_hbm_svc_vm|ot_hbm_svc_wb)", "VM"),
    (r"^(ot_hbm_svc_sm|ot_hgi_sm_|ot_hbm_sm_)", "SMSVC"), (r"^ot_pdie_serdes", "LINK"), (r".*", "MISC")]


def family(m):
    for rx, f in FAMILY:
        if re.match(rx, m):
            return f


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    pdir = Path(a.plan).resolve().parent
    copies = collections.Counter(p["type"] for p in plan["partitions"])
    canon = json.load(open(HARDEN / "canonical_ports_split.json"))["types"]
    canon_of = {}
    for ft, v in canon.items():
        for tid in v.get("type_ids", {}):
            canon_of[re.sub(r"__[\d.]+x[\d.]+$", "", tid)] = ft
    rec = {}
    for f in ("recipes_split.json", "recipes_other.json", "recipes.json"):
        for k, v in json.load(open(HARDEN / f)).items():
            if isinstance(v, dict) and "files" in v:
                rec.setdefault(k, v)
    rec_by_mod = collections.defaultdict(list)
    for k in rec:
        rec_by_mod[re.sub(r"__[\d.]+x[\d.]+(@.*)?$", "", k)].append(k)
    views = {}
    tables = collections.defaultdict(set)
    for tn, t in plan["partition_types"].items():
        for c in t.get("hard_cores", []):
            pf = pdir / c["pins_file"]
            key = f"{c['module']}@{sha(pf)[:12]}"
            v = views.setdefault(key, dict(view=key, module=c["module"], outline_um=c["outline_um"],
                                           pins_file=c["pins_file"], pins_sha256=sha(pf),
                                           pins=len(json.load(open(pf))), family=family(c["module"]),
                                           instances=[], placed=0))
            v["instances"].append(f"{tn}.{c['inst']}")
            v["placed"] += copies[tn]
            tables[c["module"]].add(key)
    for key, v in views.items():
        m = v["module"]
        v["tables_for_module"] = len(tables[m])
        v["canonical_type"] = canon_of.get(m)
        rk = rec_by_mod.get(m) or []
        v["recipe_keys"] = rk
        blk = []
        if len(tables[m]) > 1:
            blk.append("MULTI_TABLE: same module, several pin tables (HBM-ARCH request (a))")
        if not rk and not m.startswith("hnx_"):
            blk.append("NO_RECIPE")
        v["blockers"] = blk
    out = dict(schema="opentallas.hbm_arch.core_views.v1", plan=str(a.plan), plan_sha256=sha(a.plan),
               views=len(views), placed=sum(v["placed"] for v in views.values()),
               modules=len(tables), by_family=dict(collections.Counter(v["family"] for v in views.values())),
               view_list=sorted(views.values(), key=lambda v: (v["family"], v["module"], v["view"])))
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("views", "placed", "modules", "by_family")}))


if __name__ == "__main__":
    main()
