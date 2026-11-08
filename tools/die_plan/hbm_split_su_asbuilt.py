"""HBM d44v SU split as-built manifest from a base manifest (DIE-HBM-92-SU 11-08); never edits a plan or the base.

The d44v plan names the SU Q2/Q3 hard cores inside the composed cuts: u_su_Q<q>_lanes<a>_<b>.u_fcore.u_core.u_p<k>
(ot_hbm_su_pg_lane1_core, one as-built pinned bank + one pinreg lane) and u_su_Q<q>_pretree
(ot_hbm_su_static_pgslice_lg__pretree around the as-built red_pretree_s).  The bind of record composes those cuts
flat (ot_hnx_su_plain4__*, ot_hnx_su_pretree__rst), so the kits have no instance at the plan paths.  This adds:

  compose_split     regroup the cut members under the signed hard-core masters (bind_compose_split, exact)
  sub_core_leaf     plan lanes parent -> as-built cut (+ sub_core_leaf_variants: the mirrored quadrant's cut)
  hard_core_leaf    plan pretree core -> as-built cut + inner instance
  files / prefer    the hard cores' own RTL, staged: the signed lane1 form (oneclk wrapper + its u_core, the
                    reform_1103 lane1 at 308663537a8 under the recipe's rename_top ..__mc) and the pretree wrapper
"""
import argparse
import copy
import json
import re
import shutil
from pathlib import Path

LANE1 = "ot_hbm_su_pg_lane1_core"
PRETREE = "ot_hbm_su_static_pgslice_lg__pretree"
LANE1_WRAP = "physical/die_plan/hbm_arch_cores/wrappers/oneclk/ot_hbm_su_pg_lane1_core.sv"
LANE1_MC = "rtl/hbm_accel/cores_split/reform_1103/ot_hbm_su_static_pgslice_lg__lanes8_11/ot_hbm_su_pg_lane1_core.sv"
PRETREE_SRC = ["physical/die_plan/hbm_arch_cores/wrappers/ot_hbm_su_static_pgslice_lg__pretree.sv",
               "rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_pg_pretree_core.sv"]
QUAD = {"2": ("su_NE2", "su_NW2"), "3": ("su_NE3", "su_NW3")}
LANES = re.compile(r"(u_su_Q([23])_lanes(\d+_\d+))\.u_fcore\.u_core\.u_p\d+")
PRE = re.compile(r"u_su_Q([23])_pretree")


def plan_cores(plan):
    lanes, pretrees = set(), set()
    for t in plan["partition_types"].values():
        for h in t.get("hard_cores", []) or []:
            m = LANES.fullmatch(h.get("physical_inst") or "")
            if m and h.get("module") == LANE1:
                lanes.add(m.groups())
            elif PRE.fullmatch(h["inst"]) and h.get("module") == PRETREE and not h.get("physical_inst"):
                pretrees.add(h["inst"])
    return sorted(lanes), sorted(pretrees)


def stage_sources(source, stage):
    stage.mkdir(parents=True, exist_ok=True)
    out = {}
    src = Path(source)
    wrap = stage / Path(LANE1_WRAP).name
    shutil.copy2(src / LANE1_WRAP, wrap)
    mc_text = (src / LANE1_MC).read_text()
    if len(re.findall(r"\bmodule\s+" + LANE1 + r"\b", mc_text)) != 1:
        raise ValueError("lane1 source must define exactly one " + LANE1)
    mc = stage / (LANE1 + "__mc.sv")
    mc.write_text("// DIE-HBM-92-SU 11-08: " + LANE1_MC + " with the core recipe's rename_top " + LANE1 + "__mc "
                  "(recipes_b2.json ot_hbm_su_pg_lane1_core, files_at 308663537a8); otherwise byte-identical.\n" +
                  re.sub(r"\bmodule\s+" + LANE1 + r"\b", "module " + LANE1 + "__mc", mc_text))
    out["lane1"] = [str(wrap), str(mc)]
    out["pretree"] = []
    for f in PRETREE_SRC:
        shutil.copy2(src / f, stage / Path(f).name)
        out["pretree"].append(str(stage / Path(f).name))
    return out


def candidate(plan, asbuilt, source, stage):
    lanes, pretrees = plan_cores(plan)
    if not lanes:
        raise ValueError("plan names no SU lane1 split sub-cores")
    files = stage_sources(source, Path(stage).resolve())
    out = copy.deepcopy(asbuilt)
    scl = out.setdefault("sub_core_leaf", {})
    var = out.setdefault("sub_core_leaf_variants", {})
    for parent, q, rng in lanes:
        a, b = QUAD[q]
        if parent in scl and scl[parent] != f"{a}.__cut_lanes{rng}":
            raise ValueError(f"sub_core_leaf {parent} already maps to {scl[parent]}")
        scl[parent] = f"{a}.__cut_lanes{rng}"
        var[parent] = [f"{b}.__cut_lanes{rng}"]
    hcl = out.setdefault("hard_core_leaf", {})
    for inst in pretrees:
        q = PRE.fullmatch(inst).group(1)
        hcl[inst] = dict(leaves=[f"{x}.__cut_pretree" for x in QUAD[q]], inner="u_hc")
    out["compose_split"] = [
        dict(inst=r"su_N[EW][23]\.__cut_lanes\d+_\d+", suffix="__l1split", levels=["u_fcore", "u_core"],
             subs=[dict(name="u_p{k}", module=LANE1, sources=files["lane1"],
                        roles={"u_core.u_bank0": r"\.g_bank\[(\d+)\]\.u_bank$",
                               "u_core.u_lane0": r"\.g_lane\[(\d+)\]\.g_pr\.u_lane$"},
                        param_diff_ok=["MLAT", "ALAT"],
                        drop_exports={"u_core.u_bank0.read_data": [128, 159], "u_core.u_lane0.kv_waddr": [18, 23],
                                      "u_core.u_lane0.vm_waddr": [18, 23]},
                        drop_reason="dead parent loads (ot_hbm_su_static_pgslice_s.sv: drain sel reads reader 5 "
                                    "bank_q[..*192+5*32+:32] only, never reader 4 [159:128]; la[23:18] unused, write "
                                    "address {la[17:16],la[13:7]}, id check la[6:0]/la[15:14]); the lane1 pins omit them")],
             reason="d44v p6/p17 split (8dd205e8bcc): u_p<k> = as-built bank k + lane k; signed lane1 = l1r5 "
                    "(MLAT 5 pin-cycle lever, ledger HBM-26); as-built members keep their own parameters"),
        dict(inst=r"su_N[EW][23]\.__cut_pretree", suffix="__hcsplit", levels=[],
             subs=[dict(name="u_hc", module=PRETREE, sources=files["pretree"],
                        roles={"u_core.u_pt": r"\.g_pretree\.u_pt$"})],
             reason="plan hard core u_su_Q<q>_pretree = the pretree split piece around the as-built red_pretree_s"),
    ]
    staged = files["lane1"] + files["pretree"]
    out["files"] = list(dict.fromkeys(out.get("files", []) + staged))
    out["prefer"] = list(dict.fromkeys(out.get("prefer", []) + staged))
    out["note"] = ("DIE-HBM-92-SU p37su: p37 + SU Q2/Q3 lane1/pretree compose_split | " + out.get("note", ""))
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True)
    p.add_argument("--asbuilt", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    result = candidate(json.loads(Path(a.plan).read_text()), json.loads(Path(a.asbuilt).read_text()), a.source,
                       stage=Path(a.out).resolve().parent / "p37su_sources")
    Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
