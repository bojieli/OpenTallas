#!/usr/bin/env python3
"""DIE-QC-57b 10-31 (COORD 18:0x (6)): QC hard cores in the kit wave (tools/autopilot/kit_wave.py core_kit mode), the
KV kv_core_wave.py pattern on gen_core_kit_qc.py plan_pins_contract mode.

    views: python3 qc_core_wave.py views --plan PLAN --out VIEWS
    gen:   python3 qc_core_wave.py gen --views VIEWS --view MODULE@SHA12 --out OUT [--plan PLAN] [gen_core_kit_qc.py args]

views lists every planned hard core of the QC plan of record (partition_types[*].hard_cores with a pins_file and no
lef/lib view) as one view per (module, plan pin table): view = '<module>@<sha256(pins_file)[:12]>' (the kit_wave
plan probe core_views key).  A module gets a recipe only from a known recipe family below; every other module is
listed in no_recipe (picker: CORE_VIEW FAIL ... 0 views = PLAN class, core owner).

Recipe families:
  * su_lane: qfd_qc_su_lane_w_l<k> (the eight SU lane cores, cut RTL rtl/physical/qfd_qc_su_lane_w_l<k>.sv by
    tools/die_plan/qc_su_lane_cut.py; plan pin tables re-pinned by cores/su_lane_repin.py): sources = the cut lane +
    its five as-built leaves, 2x ot_sram_1r1w2c_128x64_m1 (head u_tlm), clk / rst_n, OWNER DECISION 13 reset patches
    (the async 2-flop synchronisers qfd_dv_s5_rst2 (lrly) and qfd_dv_s1_rst_land (head) become synchronous 2-stage
    relays of the same release depth; downstream flops keep their async clear from the relay output).

  * sc_leaf (DIE-QC-63/SC 11-02, QC SC event): the SC leaf hard cores u_core of the nine SC types --
    qfd_dv_s5_sc2_leaf (base, plan params HARD_PINREG=1 -> VERILOG_TOP_PARAMS) and the chain-end variants
    qfd_dv_s5_sc2_leaf_up0 / _dn0 (same HARD_PINREG=1): sources = the leaf wrapper + its k79 netlist + helpers, clk ck / rst_n,
    no macros, util 0.45, M5 ceiling (the Codex db9 HARD1 recipe), kit IO frame = the plan early core tap.

  * coll_fold (DIE-QC-75 11-05, QC coll_core split): ot_coll_fold_slice (the 8 g_pf / g_xf slices of coll_core): sources
    = the slice + its FP32 adder leaves, clk / rst_n, no macros, D13 patch on ot_coll_rst_leaf, util 0.45, M5 ceiling.

gen writes the spec (OUT/_spec/<module>/spec.json) and the one-module recipe file (OUT/_recipes.json) and runs
    gen_core_kit_qc.py --module M --recipes OUT/_recipes.json --plan PLAN --out OUT --seam-hold 25,25 [args]
(hard-core seam contract sender 25 / seam 25, COORD 10-28 19:05; extra args last).  Kit = OUT/<module>_<suffix>/
freeze.json; runner = <kit>/run_kit.sh KIT GOAL MEM CPUS (kit_wave config runner '{kit}/run_kit.sh').
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
GEN = HERE / "legacy/gen_core_kit_qc.py"
SRAM = "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1"
SU_LANE_SOURCES = [
    "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
    "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_sfu_q.sv", "rtl/hdc/ot_hdc_vreduce.sv",
    "rtl/hdc/ot_hdc_vstream_sfu_t.sv", "{lane}", "rtl/qwen_dv/qfd_dv_head_safe1.sv",
    "rtl/qwen_dv/qfd_dv_reset_tree.sv", "rtl/qwen_dv/qfd_dv_scalar2.sv", "rtl/qwen_dv/qfd_dv_slice_tload.sv",
    "rtl/qwen_dv/qfd_dv_stream_rsafe.sv", "rtl/qwen_dv/qfd_dv_table_rom_loader.sv", "rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv",
    "rtl/qwen_dv/s5/qfd_dv_s5_vm.sv"]
D13 = ("OWNER DECISION 13 hard-core reset contract: rst_n is a SYNCHRONOUS registered input at the data IO budget; the "
       "internal async 2-flop synchroniser becomes a synchronous 2-stage relay of the same release depth (assertion "
       "synchronous, release cycle unchanged). Downstream flops keep their async clear from the relay output (timed "
       "recovery/removal).")
SU_LANE_PATCHES = [
    {"file": "rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv", "why": D13 + " qfd_dv_s5_rst2 (lrly u_rlz).", "edits": [[
        "module qfd_dv_s5_rst2 (input wire ck, input wire rst_n, output wire rst);\n    reg rs1, rs2;\n"
        "    always @(posedge ck or negedge rst_n)\n",
        "module qfd_dv_s5_rst2 (input wire ck, input wire rst_n, output wire rst);\n    reg rs1, rs2;\n"
        "    always @(posedge ck)   // QC kit patch (OWNER DECISION 13): synchronous 2-stage relay, same release depth\n"]]},
    {"file": "rtl/qwen_dv/qfd_dv_head_safe1.sv", "why": D13 + " qfd_dv_s1_rst_land (head face landing).", "edits": [[
        "    (* async_reg = \"true\" *) reg [1:0] s;\n    always @(posedge clk or negedge arst_n) if (!arst_n) s <= 2'b00;",
        "    reg [1:0] s;   // QC kit patch (OWNER DECISION 13): synchronous 2-stage relay, same release depth\n"
        "    always @(posedge clk) if (!arst_n) s <= 2'b00;"]]}]


COLL_FOLD = "ot_coll_fold_slice"   # DIE-QC-75 coll_fold family: g_pf / g_xf fold slices out of coll_core
COLL_FOLD_SOURCES = ["rtl/rom/ot_coll_fold_slice.sv", "rtl/rom/ot_coll_rst_leaf.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
                     "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv"]
COLL_FOLD_PATCHES = [
    {"file": "rtl/rom/ot_coll_rst_leaf.sv", "why": D13 + " ot_coll_rst_leaf (fold slice u_rs).", "edits": [[
        "    (* async_reg = \"true\" *) reg [1:0] s;\n    always @(posedge clk or negedge arst_n) if (!arst_n) s <= 2'b00;",
        "    reg [1:0] s;   // QC kit patch (OWNER DECISION 13): synchronous 2-stage relay, same release depth\n"
        "    always @(posedge clk) if (!arst_n) s <= 2'b00;"]]}]


SLE_CTL = "qfd_dv_s5_ctl_repair4_leaf"   # QC-SLECTL-B 11-05 sle_ctl split: u_ctl hard child (ctl family)
SLE_CTL_SOURCES = ["rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4_leaf.sv", "rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4.sv",
                   "rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4_helpers.sv",
                   "rtl/qwen_dv/mu/qfd_dv_amax_mu.sv", "rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv"]
SLE_CLAND_RE = r"sle_cland_w\d+_[nsew](?:_\d+)?"   # QC-SLECTL-B: landing-ring wrapper masters (cland family)
SLE_CLAND_SOURCES = ["rtl/common/ot_dp_clk_landing_ca.sv", "rtl/common/ot_dp_clk_landing.sv",
                     "rtl/common/ot_meso_fifo.sv"]


SC_HELPERS = "rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79_helpers.sv"
SC_LEAF = {   # module -> (wrapper, netlist): DIE-QC-63/SC 11-02 sc_leaf family
    "qfd_dv_s5_sc2_leaf": ("rtl/qwen_dv/s5/qfd_dv_s5_sc2_leaf.sv", "rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79.sv"),
    "qfd_dv_s5_sc2_leaf_up0": ("rtl/qwen_dv/s5/qfd_dv_s5_sc2_ce_leaf.sv", "rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79_up0.sv"),
    "qfd_dv_s5_sc2_leaf_dn0": ("rtl/qwen_dv/s5/qfd_dv_s5_sc2_ce_leaf.sv", "rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79_dn0.sv")}


def sha12(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def family(module, repo=REPO):
    """-> (family, rtl path) or (None, why)"""
    m = re.fullmatch(r"qfd_qc_su_lane_w_l(\d)", module)
    if m:
        f = f"rtl/physical/{module}.sv"
        return ("su_lane", f) if (repo / f).is_file() else (None, f"cut RTL {f} missing")
    if module in SC_LEAF:
        f = SC_LEAF[module][0]
        return ("sc_leaf", f) if (repo / f).is_file() else (None, f"SC leaf RTL {f} missing")
    if module == COLL_FOLD:
        f = COLL_FOLD_SOURCES[0]
        return ("coll_fold", f) if (repo / f).is_file() else (None, f"fold slice RTL {f} missing")
    if module == SLE_CTL:
        f = SLE_CTL_SOURCES[0]
        return ("sle_ctl", f) if (repo / f).is_file() else (None, f"ctl leaf RTL {f} missing")
    if re.fullmatch(SLE_CLAND_RE, module):
        f = f"rtl/physical/sle_ctl/{module}.sv"
        return ("sle_cland", f) if (repo / f).is_file() else (None, f"ring wrapper RTL {f} missing")
    return None, "no QC core recipe family (qc_core_wave.py)"


def plan_views(plan_path, repo=REPO):
    plan = json.load(open(plan_path))
    pdir = Path(plan_path).resolve().parent
    by = {}
    for t, v in sorted((plan.get("partition_types") or {}).items()):
        for c in (v.get("hard_cores") or []) if isinstance(v, dict) else []:
            if not isinstance(c, dict) or not c.get("module") or not c.get("pins_file") or c.get("lef") or c.get("lib"):
                continue
            pf = pdir / c["pins_file"]
            key = (c["module"], sha12(pf) if pf.is_file() else "missing")
            e = by.setdefault(key, dict(module=c["module"], view=f"{key[0]}@{key[1]}", type=t, pins_file=str(pf),
                                        outline_um=c.get("outline_um"), insts=[]))
            e["insts"].append(f"{t}/{c['inst']}")
    views, none = [], []
    for (m, s), e in sorted(by.items()):
        fam, why = family(m, repo)
        if s == "missing" or fam is None:
            none.append(dict(module=m, view=e["view"], why="pins file missing" if s == "missing" else why))
            continue
        views.append(dict(e, family=fam, rtl=why))
    return dict(schema="opentallas.qc.core_views.v1", plan=str(Path(plan_path).resolve()),
                plan_sha256=hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(), view_list=views, no_recipe=none)


def su_lane_lec_hints(m):
    """DIE-QC-58 10-31: LEC correspondence hints for the lane's rsqrt Newton steps (ot_hdc_sfu.sv rsq, g_nr[k]).

    m_yy squares y (yi*yi) so its sign register y[31] is 0 whenever the unit is past fill; m_hm.s1_sign = hd[31] ^
    yy[31] is then the half-x sign one cut earlier, held in d_h line[31] (k < 2).  Synthesis folds both, gold keeps them
    through no-reset cut stages longer than lec.py's reset window.  Each hint is proved by the same induction in lec.py
    (never a waiver); a hint that is false is dropped and the point stays NOT EQUIVALENT.
    """
    n = re.search(r"_l(\d+)$", m)
    if not n:
        return []
    p = f"ff:u_dut.u_u_rsq{n.group(1)}.u_rsq.g_nr[{{}}]."
    return ([["gold", p.format(k) + "m_yy.g_l.u.y[31]", ["const", 0]] for k in range(3)]
            + [["gold", p.format(k) + "m_hm.g_l.u.s1_sign", ["eq", "gold", p.format(k) + "g_h.d_h.g_line.line[31]", 0]]
               for k in range(2)])


def plan_core_tap_insertion(plan, module):
    """ETAP-1101 (DIE-QC-58): the module's plan EARLY core tap insertion -> (tt, ff, budget_owner) or None.  Every
    instance of the module in a type with clock.core_taps 'early' must carry one '<inst>.<pin>' / '<inst>' core tap with
    the same insertion_ps / insertion_ff_ps (the kit IO frame = the core's own insertion, 12.3 v5.0)."""
    vals = set()
    for t in (plan.get("partition_types") or {}).values():
        ck = t.get("clock") or {}
        if ck.get("core_taps") != "early":
            continue
        for c in t.get("hard_cores") or []:
            if c.get("module") != module:
                continue
            tp = [x for x in ck.get("taps") or [] if x.get("kind") == "core"
                  and (x["name"] == c["inst"] or x["name"].startswith(c["inst"] + "."))]
            if len(tp) != 1 or "insertion_ps" not in tp[0] or "insertion_ff_ps" not in tp[0]:
                raise SystemExit(f"CORE_VIEW FAIL {module}: {c['inst']}: {len(tp)} early core taps with TT/FF insertion")
            vals.add((float(tp[0]["insertion_ps"]), float(tp[0]["insertion_ff_ps"]), tp[0].get("budget_owner", "")))
    if len({v[:2] for v in vals}) > 1:
        raise SystemExit(f"CORE_VIEW FAIL {module}: early core tap insertion differs between instances: {sorted(vals)}")
    return sorted(vals)[0] if vals else None


def su_lane_recipe(e, out, plan=None):
    m = e["module"]
    spec = dict(top=m, sources=[f.format(lane=e["rtl"]) for f in SU_LANE_SOURCES], clock_port="clk",
                reset_ports=["rst_n"], macros=[dict(view=SRAM, count=2, at=[190.08, 99.744], orient="R0")],
                params={}, defines=[], route=dict(pd=0.5))
    sd = out / "_spec" / m
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "spec.json").write_text(json.dumps(spec, indent=1) + "\n")
    rec = dict(ref_tile=str(sd), plan_pins_contract=True, suffix="w" + e["view"].split("@")[1][:6],
               rtl_patches=SU_LANE_PATCHES, two_mode=True, sram_pincol_halo=True,
               macro_sites={Path(SRAM).name: [[190.08, 99.744, "R0"], [190.08, 138.144, "R0"]]},
               lec_hints=su_lane_lec_hints(m),
               _why=f"qc_core_wave su_lane view {e['view']} (DIE-QC-57b): plan pin table {e['pins_file']}")
    ins = plan_core_tap_insertion(plan, m) if plan else None
    if ins:   # ETAP-1101: kit IO vclk frame + tap target = the plan early core tap (the core's own insertion)
        rec.update(insertion_ps=ins[0], insertion_ff_ps=ins[1],
                   insertion_basis=f"plan early core tap {ins[0]:g} TT / {ins[1]:g} FF ({ins[2]})")
    return rec


def plan_core_params(plan, module):
    """DIE-QC-63/SC: the explicit plan hard-core params of the module (identical on every instance, else FAIL)."""
    vals = {json.dumps(c.get("params") or {}, sort_keys=True)
            for t in (plan.get("partition_types") or {}).values() for c in t.get("hard_cores") or []
            if c.get("module") == module}
    if len(vals) > 1:
        raise SystemExit(f"CORE_VIEW FAIL {module}: hard-core params differ between instances: {sorted(vals)}")
    return json.loads(vals.pop()) if vals else {}


def sc_leaf_recipe(e, out, plan=None):
    m = e["module"]
    wrap, net = SC_LEAF[m]
    params = plan_core_params(plan, m) if plan else {}
    spec = dict(name=m, top=m, kind="tile", sources=[wrap, net, SC_HELPERS], params=params, clock_port="ck",
                reset_ports=["rst_n"], macros=[], route=dict(pd=0.45))
    sd = out / "_spec" / m
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "spec.json").write_text(json.dumps(spec, indent=1) + "\n")
    rec = dict(ref_tile=str(sd), plan_pins_contract=True, suffix="h" + e["view"].split("@")[1][:6], util=0.45,
               max_layer="M5", insertion_balance=False,
               _why=f"qc_core_wave sc_leaf view {e['view']} (DIE-QC-63/SC QC SC event): plan pin table {e['pins_file']}")
    if params:
        rec["params"] = params
    ins = plan_core_tap_insertion(plan, m) if plan else None
    if ins:
        rec.update(insertion_ps=ins[0], insertion_ff_ps=ins[1],
                   insertion_basis=f"plan early core tap {ins[0]:g} TT / {ins[1]:g} FF ({ins[2]})")
    return rec


def coll_fold_recipe(e, out, plan=None):
    m = e["module"]
    spec = dict(name=m, top=m, kind="tile", sources=COLL_FOLD_SOURCES, params={}, clock_port="clk",
                reset_ports=["rst_n"], macros=[], route=dict(pd=0.45))
    sd = out / "_spec" / m
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "spec.json").write_text(json.dumps(spec, indent=1) + "\n")
    rec = dict(ref_tile=str(sd), plan_pins_contract=True, suffix="h" + e["view"].split("@")[1][:6], util=0.45,
               max_layer="M5", insertion_balance=False, rtl_patches=COLL_FOLD_PATCHES,
               _why=f"qc_core_wave coll_fold view {e['view']} (DIE-QC-75): plan pin table {e['pins_file']}")
    ins = plan_core_tap_insertion(plan, m) if plan else None
    if ins:
        rec.update(insertion_ps=ins[0], insertion_ff_ps=ins[1],
                   insertion_basis=f"plan early core tap {ins[0]:g} TT / {ins[1]:g} FF ({ins[2]})")
    return rec


def sle_ctl_input_share_patch(repo=REPO):
    """Coalesce only identical no-reset input captures. Every C/D must match;
    after one edge each removed Q equals its retained Q, with zero added cycles.
    The immutable production source remains unchanged; patch the child kit only.
    """
    rel = "rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4.sv"
    text = (repo / rel).read_text()
    groups = ((2, (21189, 21190, 21191, 21192)), (124, (20790, 20791, 20792)),
              (0, (20827, 20828, 21188)), (67, (20882, 20883, 21203)),
              (2176, (20959, 20960)), (2671, (20999,)))
    edits = []
    def capture(i):
        hits = re.findall(r"(?m)^.*qfd_bmath_dff_p #\(\.ID\(0\)\) u_" + str(i) +
                          r"\(\.C\(([^()]*)\),\.D\(([^()]*)\),\.Q\(([^()]*)\)\);$", text)
        if len(hits) != 1:
            raise ValueError(f"sle_ctl input share: expected one no-reset capture u_{i}, got {len(hits)}")
        return hits[0]
    for keeper, copies in groups:
        c, d, q = capture(keeper)
        for i in copies:
            cc, dd, qq = capture(i)
            if (cc, dd) != (c, d):
                raise ValueError(f"sle_ctl input share u_{i}: clock/data differ from u_{keeper}")
            old = next(x for x in text.splitlines() if re.search(r" u_" + str(i) + r"\(", x))
            edits.append([old, f"assign {qq} = {q}; // same C/D input capture as u_{keeper}; 0 cycles"])
    return {"file": rel, "why": "QC ctl child: one pin capture per data input; identical no-reset C/D copies coalesced, 0 cycles", "edits": edits}


def sle_ctl_recipe(e, out, plan=None):
    """QC-SLECTL-B 11-05: u_ctl of sle_ctl (HARD=1 production shape, 42.7k cells): one clock ck, rst_n (bound net
    rst_n, reset_net), no macros, util 0.45, M5 ceiling (the sc_leaf / coll_fold conservative form)."""
    m = e["module"]
    spec = dict(name=m, top=m, kind="tile", sources=SLE_CTL_SOURCES, params={}, clock_port="ck",
                reset_ports=["rst_n"], macros=[], route=dict(pd=0.45))
    sd = out / "_spec" / m
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "spec.json").write_text(json.dumps(spec, indent=1) + "\n")
    rec = dict(ref_tile=str(sd), plan_pins_contract=True, suffix="h" + e["view"].split("@")[1][:6], util=0.45,
               max_layer="M5", insertion_balance=False, rtl_patches=[sle_ctl_input_share_patch()],
               _why=f"qc_core_wave sle_ctl view {e['view']} (QC-SLECTL-B): plan pin table {e['pins_file']}")
    ins = plan_core_tap_insertion(plan, m) if plan else None
    if ins:
        rec.update(insertion_ps=ins[0], insertion_ff_ps=ins[1],
                   insertion_basis=f"plan early core tap {ins[0]:g} TT / {ins[1]:g} FF ({ins[2]})")
    return rec


def sle_cland_recipe(e, out, plan=None):
    """QC-SLECTL-B 11-05: a landing-ring wrapper master (rtl/physical/sle_ctl/<m>.sv = param_wrap.wrapper_sv of
    ot_dp_clk_landing_cas #(W, DEPTH 4, WFALL 1, WREG 1, DSREP 1)): core clock clk, RELATED forwarded write clock fclk
    (its own root; d / t_rst_n timed on fclk, the landing_contract.ring_input_sdc law), rst_n (bound net cland_start),
    util 0.45, M5 ceiling."""
    m = e["module"]
    spec = dict(name=m, top=m, kind="tile", sources=[e["rtl"]] + SLE_CLAND_SOURCES, params={}, clock_port="clk",
                reset_ports=["rst_n", "t_rst_n"], macros=[], route=dict(pd=0.45))
    sd = out / "_spec" / m
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "spec.json").write_text(json.dumps(spec, indent=1) + "\n")
    rec = dict(ref_tile=str(sd), plan_pins_contract=True, suffix="h" + e["view"].split("@")[1][:6], util=0.45,
               max_layer="M5", insertion_balance=False,
               related_clocks={"fclk": ["d", "t_rst_n"]}, strap_ports=["strap_k"],
               land_slots={"d": {"D": 4, "form": "hold_mux"}, "t_rst_n": {"form": "ring_start", "ring": "d"}},
               _why=f"qc_core_wave sle_cland view {e['view']} (QC-SLECTL-B): plan pin table {e['pins_file']}")
    # Small START-only rings need real rows inside the narrow face band.
    # The ordinary 4.32um margin would invert an 8.208um outline's core.
    if min(e["outline_um"]) < 12.96:
        rec["core_margin"] = 1.08
    ins = plan_core_tap_insertion(plan, m) if plan else None
    if ins:
        rec.update(insertion_ps=ins[0], insertion_ff_ps=ins[1],
                   insertion_basis=f"plan early core tap {ins[0]:g} TT / {ins[1]:g} FF ({ins[2]})")
    return rec


def gen(a, extra):
    v = json.load(open(a.views))
    e = next((x for x in v.get("view_list") or [] if x["view"] == a.view), None)
    if e is None:
        sys.exit(f"CORE_VIEW FAIL {a.view}: not in {a.views}")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rec = {"su_lane": su_lane_recipe, "sc_leaf": sc_leaf_recipe, "coll_fold": coll_fold_recipe,
           "sle_ctl": sle_ctl_recipe, "sle_cland": sle_cland_recipe}[e["family"]](e, out, json.load(open(a.plan or v["plan"])))
    (out / "_recipes.json").write_text(json.dumps({e["module"]: rec}, indent=1) + "\n")
    cmd = [sys.executable, str(GEN), "--module", e["module"], "--recipes", str(out / "_recipes.json"),
           "--plan", a.plan or v["plan"], "--out", str(out), "--seam-hold", "25,25"] + list(extra)
    (out / "qc_core_wave.json").write_text(json.dumps(dict(view=a.view, module=e["module"], family=e["family"],
                                                           cmd=cmd), indent=1) + "\n")
    print("QC_CORE_WAVE", " ".join(cmd), flush=True)
    return subprocess.run(cmd).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("views")
    pv.add_argument("--plan", required=True)
    pv.add_argument("--out", required=True)
    pg = sub.add_parser("gen")
    pg.add_argument("--views", required=True)
    pg.add_argument("--view", required=True)
    pg.add_argument("--out", required=True)
    pg.add_argument("--plan")
    a, extra = ap.parse_known_args(argv)
    if a.cmd == "views":
        if extra:
            ap.error(f"unknown args {extra}")
        v = plan_views(a.plan)
        Path(a.out).write_text(json.dumps(v, indent=1) + "\n")
        print(f"QC_CORE_VIEWS {len(v['view_list'])} views, {len(v['no_recipe'])} no_recipe")
        return 0
    return gen(a, extra)


if __name__ == "__main__":
    sys.exit(main())
