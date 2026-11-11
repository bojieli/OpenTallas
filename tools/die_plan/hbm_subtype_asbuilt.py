#!/usr/bin/env python3
"""HBM sub-type rebind manifest from a base as-built manifest (BIND-SUBTYPE 11-11); never edits a plan or the base.

    hbm_subtype_asbuilt.py BASE.json OUT.json --repo DIR [--sfu] [--tkm TKM_RULE.json]

--sfu   q_b110..q_b113 (+__physical_v1): every composed SFU lane cut sfucore_N[EW].__cut_laneK (native
        ot_hnx_sfu_lane__cf694489f05c = ot_hgi_sfu_lane_map + ot_su12_sfu_sp2) binds the d44v part-6 split glue
        ot_hgi_sfu_split3_lane_core__idpin__bsub (u_fcore.u_core.u_{fr,ex,bk} = the bare plan masters), one-to-one
        (bind_subtype, asbuilt.subtype_bind): bound names unchanged.  Port map: glue sfu_* = native lane_* (the cut
        renamed the sp2 ports), glue map_* = native map_*, sfu_clk / sfu_rst_n on the native map_clk / map_rst_n nets
        (the native lane clocks and resets map and sfu from those two pins).  sub_core_leaf_variants u_sfucore_Q_laneK
        -> [sfucore_NW.__cut_laneK, sfucore_NE.__cut_laneK] (the base sub_core_leaf u_sfucore_Q_laneK is no as-built
        path, so bound_macro_paths emitted no row and KIT_PREFLIGHT macro_instances failed); sub_core_leaf unchanged.
--tkm   an N-way rule file (JSON list of subtype_bind rules + "sub_core_leaf" table) appended as given.
Cycle relation: d44v part 6 (+4 on sfu_vm/kv/ro/fault/coll), priced in the plan of record; the bind is wiring only.
"""
import argparse
import copy
import json
from pathlib import Path

GLUE = "physical/die_plan/hbm/bind/subtype/ot_hgi_sfu_split3_lane_core__idpin__bsub.sv"
SUBS = ["rtl/hbm_accel/cores_split/reform_1103/ot_hgi_sfu_split3_lane_core__idpin/ot_hgi_sfu_split3_lane_core_%s.sv" % s
        for s in ("fr", "ex", "bk")]
OUTS = ["coll", "fault", "kv_we", "ro_v", "vi_re", "vm_we", "kv_waddr", "vi_addr", "vm_waddr", "kv_wdata", "ro_x",
        "vm_wdata", "rd_re", "rd_src", "rd_addr", "rd_q", "vi_q"]


def sfu_rule(repo):
    return dict(leaf=r"sfucore_N[EW]\.__cut_lane([0-9]|1[0-5])", native="ot_hnx_sfu_lane__cf694489f05c",
                top="ot_hgi_sfu_split3_lane_core__idpin__bsub", stops=["ot_hgi_sfu_split3_lane_core__idpin__bsub"],
                files=[str(Path(repo) / f) for f in [GLUE] + SUBS],
                rename={"sfu_" + o: "lane_" + o for o in OUTS}, share={"sfu_clk": "map_clk", "sfu_rst_n": "map_rst_n"},
                note="BIND-SUBTYPE 11-11: d44v part 6 SFU split3 lane, one-to-one (bound names unchanged)")


def build(base, repo, sfu=True, tkm=None):
    out = copy.deepcopy(base)
    rules = list(out.get("subtype_bind", []))
    if sfu:
        rules.append(sfu_rule(repo))
        scl, var = dict(out.get("sub_core_leaf", {})), dict(out.get("sub_core_leaf_variants", {}))
        for k in range(16):
            # sub_core_leaf stays the base value (the partition-local leaf name u_sfucore_Q_laneK): bind.py keys the
            # plan's parent_id_straps (h["parent_id_leaf"]) by it; the as-built cut paths go to the variants only,
            # which bound_macro_paths reads (exactly one of NW / NE is in a bound file).  11-11 epyc4 bind: the cut path
            # in sub_core_leaf made EMIT "parent ID q_b110: declarations do not match bound known strap inputs".
            var[f"u_sfucore_Q_lane{k}"] = [f"sfucore_NW.__cut_lane{k}", f"sfucore_NE.__cut_lane{k}"]
        out["sub_core_leaf"], out["sub_core_leaf_variants"] = scl, var
        files = [str(Path(repo) / f) for f in [GLUE] + SUBS]
        out["files"] = list(out.get("files", [])) + [f for f in files if f not in out.get("files", [])]
        out["prefer"] = files + [f for f in out.get("prefer", []) if f not in files]
    if tkm:
        extra = json.loads(Path(tkm).read_text())
        rules.extend(extra["rules"])
        out["sub_core_leaf"] = dict(out.get("sub_core_leaf", {}), **extra.get("sub_core_leaf", {}))
        fs = [f for r in extra["rules"] for f in r["files"]]
        out["files"] = list(out.get("files", [])) + [f for f in fs if f not in out.get("files", [])]
        out["prefer"] = fs + [f for f in out.get("prefer", []) if f not in fs]
    out["subtype_bind"] = rules
    out["note_bind_subtype"] = ("BIND-SUBTYPE 11-11: base + subtype_bind (" + ("sfu" if sfu else "")
                                + (" tkm" if tkm else "") + "); sub_core_leaf_variants sfu lanes -> as-built cut paths")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--no-sfu", action="store_true")
    ap.add_argument("--tkm")
    a = ap.parse_args()
    out = build(json.loads(Path(a.base).read_text()), a.repo, sfu=not a.no_sfu, tkm=a.tkm)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
