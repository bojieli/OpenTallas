"""HBM d44v hb_idx HCOL h0 split as-built manifest from a base manifest (DIE-HBM-92-SU-IDX 11-08); never edits a plan
or the base.

The d44v plan (part 6, SPLIT c4237519789) names the h0 half-column hard cores inside their parent:
<parent>.u_fcore.u_core.u_ra / .u_rb (ot_hbm_idx_score_hcol_h0_ra / _rb, one clock region each).  The bind of record
substitutes every as-built h0 half column (ot_hidx_score_hcol HALF 0) by the plain ot_hbm_idx_score_hcol_h0, so the
kits have no instance at the plan paths (kit_contract macro_instances TOOL_FAIL).  This adds:

  substitute_inst   a second rule per h0 leaf (after its HALF rule): ot_hbm_idx_score_hcol_h0 -> GLUE, a staged copy
                    of the plan glue (results/die_hbm_1103/reform/split_p6) under its own top name, same ports as the
                    as-built h0 (wires only; ra -> rb running sum cs2/cf2, hid4 halves, broadcast q_b/qv_b/key/rst_col)
  sub_core_leaf     plan parent -> its as-built h0 leaf (t5_map) (+ sub_core_leaf_variants: the mirrored quadrant's leaf)
  files / prefer    the staged glue and the split source the signed ra/rb views were built from (_rgn.sv at c4237519789)

Exactness: the composition is cycle-exact with the as-built h0 only with the two seam face flops (ra cs/cf out face +
rb cs/cf in face) that the signed macros carry: ra pays them back inside (seed and head-1 delay SEAM = 2 shorter).
The glue is wires only (the kit synthesizes it; the hard cores are header-only blackboxes there).
"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

H0 = "ot_hbm_idx_score_hcol_h0"
GLUE = H0 + "__p6glue"
SPLIT_SHA = "c4237519789"
RGN = "rtl/hbm_accel/cores_split/reform_1103/ot_hbm_idx_score_hcol_h0/ot_hbm_idx_score_hcol_h0_rgn.sv"
PARENT = re.compile(r"(u_hb_idx__s_Q2?_r\dc\d_k\dh0)\.u_fcore\.u_core\.u_r([ab])")
PORTS = """    input wire [1:0] clk_pair, input wire rst_col, input wire qv_b, input wire [567:0] q_b, input wire [543:0] key,
    input wire [31:0] hid4, output wire [31:0] cs_out, output wire cf_out, output wire [1:0] prdy"""
CONN = (".clk_pair(clk_pair), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b), .key(key), .hid4(hid4), .cs_out(cs_out), "
        ".cf_out(cf_out), .prdy(prdy)")


def glue_sv():
    return f"""// DIE-HBM-92-SU-IDX 11-08: staged copy of the d44v part-6 plan glue (results/die_hbm_1103/reform/split_p6/
// {H0}__p6glue.sv, SPLIT {SPLIT_SHA}) under its own top name {GLUE}, with the as-built {H0} ports (the composition
// never had cs_in/cf_in: the as-built h0 ties them 0).  The sub-cores are the signed masters {H0}_ra / _rb (not the
// bench face-shell models __fs).  Wires only.  The ra -> rb running sum crosses two face flops inside the signed macros
// (ra out + rb in); ra pays them back inside (SEAM = 2), so the composition is cycle-exact with {H0} through them.
`default_nettype none
module {GLUE} (
{PORTS});
    {GLUE}__fcore u_fcore ({CONN});
endmodule

module {GLUE}__fcore (
{PORTS});
    {GLUE}__split u_core ({CONN});
endmodule

module {GLUE}__split (
{PORTS});
    wire [31:0] cs2; wire cf2;
    {H0}_ra u_ra (.clk(clk_pair[0]), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b), .key(key),
        .hid2(hid4[15:0]), .cs_out(cs2), .cf_out(cf2), .prdy(prdy[0]));
    {H0}_rb u_rb (.clk(clk_pair[1]), .rst_col(rst_col), .qv_b(qv_b), .q_b(q_b), .key(key),
        .hid2(hid4[31:16]), .cs_in(cs2), .cf_in(cf2), .cs_out(cs_out), .cf_out(cf_out), .prdy(prdy[1]));
endmodule
`default_nettype wire
"""


def plan_parents(plan):
    out = {}
    for t in plan["partition_types"].values():
        for h in t.get("hard_cores", []) or []:
            m = PARENT.fullmatch(h.get("physical_inst") or "")
            if m:
                if h.get("module") != f"{H0}_r{m.group(2)}":
                    raise ValueError(f"{h['inst']}: module {h.get('module')} at {h['physical_inst']}")
                out.setdefault(m.group(1), set()).add(m.group(2))
    bad = sorted(p for p, s in out.items() if s != {"a", "b"})
    if bad:
        raise ValueError(f"parents without both ra and rb: {bad}")
    return sorted(out)


def stage_sources(source, stage):
    stage.mkdir(parents=True, exist_ok=True)
    text = subprocess.run(["git", "-C", str(source), "show", f"{SPLIT_SHA}:{RGN}"], check=True,
                          capture_output=True, text=True).stdout
    for top in (H0 + "_ra", H0 + "_rb"):
        if len(re.findall(r"\bmodule\s+" + top + r"\b", text)) != 1:
            raise ValueError(f"{RGN}@{SPLIT_SHA} must define exactly one {top}")
    rgn = stage / Path(RGN).name
    rgn.write_text(text)
    glue = stage / (GLUE + ".sv")
    glue.write_text(glue_sv())
    return [str(glue), str(rgn)]


def candidate(plan, asbuilt, tmap, source, stage):
    parents = plan_parents(plan)
    if not parents:
        raise ValueError("plan names no h0 ra/rb split sub-cores")
    leaves = {}
    for path, v in tmap["parts"].items():
        if len(v) >= 2 and v[1] in parents:
            leaves.setdefault(v[1], []).append(path)
    out = copy.deepcopy(asbuilt)
    half = [r for r in out["substitute_inst"] if r.get("module") == H0]
    by_rule = {}
    for p in parents:
        ls = sorted(leaves.get(p, []))
        if len(ls) != 2:
            raise ValueError(f"{p}: t5_map names {len(ls)} as-built leaves (need the two mirrored quadrants)")
        for leaf in ls:
            rs = [r for r in half if re.fullmatch(r["inst"], leaf)]
            if len(rs) != 1:
                raise ValueError(f"{leaf}: {len(rs)} HALF substitute rules to {H0}")
            by_rule[rs[0]["inst"]] = leaf
    files = stage_sources(source, Path(stage).resolve())
    scl = out.setdefault("sub_core_leaf", {})
    var = out.setdefault("sub_core_leaf_variants", {})
    for p in parents:
        a, b = sorted(leaves[p])
        if p in scl and scl[p] != a:
            raise ValueError(f"sub_core_leaf {p} already maps to {scl[p]}")
        scl[p] = a
        var[p] = [b]
    reason = (f"d44v p6 SPLIT {SPLIT_SHA}: plan h0 = wires-only glue around the signed {H0}_ra/_rb (u_fcore.u_core."
              f"u_ra/u_rb); applies after the HALF rule of this leaf; MUT/DELIVERED_RESET dropped (ra/rb carry one "
              f"ot_rst_relay each, release 3 edges as ot_rst_delivered3; reset held 64 edges)")
    for rx in sorted(by_rule):
        out["substitute_inst"].append(dict(inst=rx, module=GLUE, reason=reason))
    out["files"] = list(dict.fromkeys(out.get("files", []) + files))
    out["prefer"] = list(dict.fromkeys(out.get("prefer", []) + files))
    out["note"] = f"DIE-HBM-92-SU-IDX p37su_idx: + hb_idx h0 ra/rb glue ({len(by_rule)} leaves) | " + out.get("note", "")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plan", required=True)
    p.add_argument("--asbuilt", required=True)
    p.add_argument("--source", required=True, help="repo checkout holding the split commit")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f"{a.out} exists: manifests are never edited in place")
    ab = json.loads(Path(a.asbuilt).read_text())
    result = candidate(json.loads(Path(a.plan).read_text()), ab, json.loads(Path(ab["map_file"]).read_text()),
                       a.source, stage=Path(a.out).resolve().parent / "p37su_idx_sources")
    Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
    print(a.out, hashlib.sha256(Path(a.out).read_bytes()).hexdigest())
