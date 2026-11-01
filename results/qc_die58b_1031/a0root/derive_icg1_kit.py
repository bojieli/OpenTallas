#!/usr/bin/env python3
"""DIE-QC-58B (COORD 10-31 22:5x ruling (3) variant B): derive an A0 ICG=1 (single tile-root gate, DIE-QC-16 form)
kit from a GEOM-reviewed ICG=2 (B-hop) A0 kit.  Generated, never hand-edited: every change is listed in DERIVE.json.

Changes (only these):
  * VERILOG_TOP_PARAMS ICG 2 -> ICG 1 (config.mk + rtl_lint.ys chparam); RTL is byte-identical to origin/main.
  * graph homes: the 100 g_icg.g_hop.* rows (37 hop ICGs + relayed enable registers h[*]) are removed (absent in the
    ICG=1 netlist); the one root gate g_icg.g_root.u_icg takes the home of the former ck-entry gate u_hop_ck/u_icg
    (the gate that already drove the body clock ck_g).  All other homes (body/face registers, relay, dr, go_h) kept.
  * IO frame = the DECLARED A0 frame (COORD DIE-QC-18): config OT_VCLK_TT/FF, constraint.sdc / vclk_ff.sdc
    set_clock_latency -source, sdc_lint.json insertion_ps / insertion_ff_ps.
  * CTS_ARGS = DIE-QC-57d V3 (-balance_levels -wire_unit 25 -distance_between_buffers 100) on the kit's base args.
  * optional --lec-hints: the main nb_t[6:0] loaded=0 hints (Codex QC NL parent proof); without them both tiles' LEC
    stops at 7 nb compare points (synthesis drops nb_t[6:0], which are always 0).
       derive_icg1_kit.py --prune KIT nk|nl NETLIST   (after synth: drop homes of cells synthesis removed)
usage: derive_icg1_kit.py SRC DST --tile nk|nl --tt PS --ff PS --suffix SUF [--lec-hints HINTS.json]
"""
import argparse, json, os, re, shutil, hashlib, sys

V3 = "-balance_levels -wire_unit 25 -distance_between_buffers 100"
SKIP = {"run", "__pycache__", "lec", "FAIL_PREFLOOR", "image.txt"}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def sub1(text, pat, rep, what, count=1):
    new, n = re.subn(pat, rep, text, flags=re.M)
    if n != count:
        sys.exit(f"derive: {what}: expected {count} match(es) of {pat!r}, got {n}")
    return new


def prune(kit, tile, netlist):
    """Post-synth step: drop graph homes whose cell is absent from the kit's own synth netlist (graph_homes.tcl
    errors on any missing name).  Every dropped name is listed in DERIVE.json; nothing is added or moved."""
    names = set(re.findall(r"\\(\S+)", open(netlist).read())) | set(re.findall(r"^\s*\S+\s+([A-Za-z_][\w.$]*)\s*\(", open(netlist).read(), re.M))
    gh = os.path.join(kit, f"{tile}_graph_homes.tsv"); rows = open(gh).read().splitlines()
    # the derive-added homes (root gate, B2 en_q) are always kept: an ICG=1 / ICG_EREG netlist has them by construction
    # and --prune may be fed an earlier (pre-B2) synth netlist of the same tile
    added = {"g_icg.g_root.u_icg", "g_icg.g_root.g_er.en_q$_DFF_PN1_"}
    keep, drop = [], []
    for r in rows:
        n = r.split("\t")[0].replace("\\[", "[").replace("\\]", "]")
        (keep if n in names or n in added else drop).append(r)
    open(gh, "w").write("\n".join(keep) + "\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append(f"{os.path.basename(gh)}: post-synth prune -{len(drop)} homes absent from {os.path.basename(netlist)}")
    d["pruned_homes"] = [r.split("\t")[0] for r in drop]
    d["sha16"][os.path.basename(gh)] = sha(gh)
    json.dump(d, open(dj, "w"), indent=1)
    print(f"prune: kept {len(keep)} dropped {len(drop)}: {[r.split(chr(9))[0] for r in drop][:10]}")


EPI_OLD = "  if {$w >= -100.0 && $n <= 2000} { return }\n"
EPI_NEW = EPI_OLD + (
    "  # DIE-QC-58B kit-local (COORD 21:2x (3)(a)): with ws >= -100 the endpoint count is INFO; sign-off FF hold >= 0 stays the gate\n"
    "  if {$w >= -100.0 && [info exists ::env(OT_HOLD_EP_INFO)] && $::env(OT_HOLD_EP_INFO) eq \"1\"} {\n"
    "    puts [format \"OT_HOLD_EP_INFO stage=%s: FF hold ws %.2f ps >= -100, %d failing endpoints > 2000 = INFO (COORD 21:2x (3)(a)) -> repair proceeds\" [ot_hold_stage] $w $n]\n"
    "    return\n  }\n")


def hold_ep_info(kit):
    """B2 (DIE-QC-58 ruling, COORD 21:2x (3)(a)): the structural hold endpoint cap becomes INFO when ws >= -100 ps
    (kit-local, opt-in OT_HOLD_EP_INFO = 1); ws >= -100 and sign-off FF hold >= 0 stay gates."""
    p = os.path.join(kit, "orfs_hold_mm.tcl"); s = open(p).read()
    if "OT_HOLD_EP_INFO" not in s:
        if s.count(EPI_OLD) != 1:
            sys.exit("derive: structural hold gate line not found in orfs_hold_mm.tcl")
        open(p, "w").write(s.replace(EPI_OLD, EPI_NEW))
    c = os.path.join(kit, "config.mk"); t = open(c).read()
    if "OT_HOLD_EP_INFO" not in t:
        open(c, "a").write("# DIE-QC-58B: structural hold endpoint cap = INFO when ws >= -100 (COORD 21:2x (3)(a), DIE-QC-58 ruling)\n"
                           "export OT_HOLD_EP_INFO = 1\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append("orfs_hold_mm.tcl + config.mk: OT_HOLD_EP_INFO = 1 (endpoint cap INFO when ws >= -100)")
    d["sha16"]["orfs_hold_mm.tcl"] = sha(p); d["sha16"]["config.mk"] = sha(c)
    json.dump(d, open(dj, "w"), indent=1)
    print("hold_ep_info: applied")


def grt50(kit):
    """GEOM-99 PASS-COND (A0 root gate): GRT >= 50 congestion iterations with the clock nets included (the kit GRT
    routes 4_cts incl. clock); 0 overflow is checked on 5_1_grt.log before detail route."""
    c = os.path.join(kit, "config.mk"); t = open(c).read()
    if "GLOBAL_ROUTE_ARGS" not in t:
        open(c, "a").write("# DIE-QC-58B: GEOM-99 PASS-COND, GRT >= 50 iterations (ORFS default 30)\n"
                           "export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -congestion_iterations 50\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append("config.mk: GLOBAL_ROUTE_ARGS -congestion_iterations 50 (GEOM-99 PASS-COND)")
    d["sha16"]["config.mk"] = sha(c); json.dump(d, open(dj, "w"), indent=1)
    print("grt50: applied")


def face_lift(kit):
    """DIE-QC-59 NK variant: face-branch clock latency lift to the declared FF frame (face_lift.tcl next to this script):
    after CTS, before the structural hold gate, each port-face leaf clock group below OT_VCLK_FF gets a buffer chain on
    its face sinks only, grown and re-measured per round in the synchronized FF scene (kit-local, OT_FACE_LIFT = 1)."""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_lift.tcl")
    dst = os.path.join(kit, "face_lift.tcl"); shutil.copyfile(src, dst)
    p = os.path.join(kit, "orfs_hold_mm.tcl"); s = open(p).read()
    if "face_lift.tcl" not in s:
        open(p, "a").write("source /work/face_lift.tcl\n")
    c = os.path.join(kit, "config.mk"); t = open(c).read()
    if "OT_FACE_LIFT" not in t:
        open(c, "a").write("# DIE-QC-58B: face-branch clock latency lift to the declared FF frame (DIE-QC-59 NK variant)\n"
                           "export OT_FACE_LIFT = 1\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append("face_lift.tcl + orfs_hold_mm.tcl source + config.mk OT_FACE_LIFT = 1")
    for f in ("face_lift.tcl", "orfs_hold_mm.tcl", "config.mk"):
        d["sha16"][f] = sha(os.path.join(kit, f))
    json.dump(d, open(dj, "w"), indent=1)
    print("face_lift: applied")


def dpl_retry(kit):
    """NL B2 e1 DPL-0033 after a met CTS hold repair: legalization retry on a failing check_placement (dpl_retry.tcl next
    to this script; sourced from the kit orfs_hold_mm.tcl, so it covers every stage that loads the helper)."""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dpl_retry.tcl")
    dst = os.path.join(kit, "dpl_retry.tcl"); shutil.copyfile(src, dst)
    p = os.path.join(kit, "orfs_hold_mm.tcl"); s = open(p).read()
    if "dpl_retry.tcl" not in s:
        open(p, "a").write("source /work/dpl_retry.tcl\n")
    dj = os.path.join(kit, "DERIVE.json"); d = json.load(open(dj))
    d.setdefault("changes", []).append("dpl_retry.tcl + orfs_hold_mm.tcl source (check_placement legalization retry)")
    for f in ("dpl_retry.tcl", "orfs_hold_mm.tcl"):
        d["sha16"][f] = sha(os.path.join(kit, f))
    json.dump(d, open(dj, "w"), indent=1)
    print("dpl_retry: applied")


# DIE-QC-58B form (1) (DIE-QC-59 NK ruling 11-01): the opt-in IRCK edits of the three body files (A0-local copies).  The
# branch RTL (rtl/physical/...) is exactly these edits on origin/main; --ireg applies them to the kit's own copies (the
# kit rp2_45 carries OT_A0_LOCAL_OUT_RESET, absent on main) and checks the result equals the branch file where the bases agree.
IRCK_EDITS = {
 "ot_qwen_rom_tile_w12_land32.sv": [
  ("    parameter integer CHILD_CLOCKS = 0,\n    parameter integer GLOBAL_KV_CONST0 = 0 // opt-in ROM-only global KV port is already hardwired zero\n) (",
   "    parameter integer CHILD_CLOCKS = 0,\n    parameter integer GLOBAL_KV_CONST0 = 0, // opt-in ROM-only global KV port is already hardwired zero\n"
   "    // DIE-QC-58B form (1) (opt-in, default 0 = unchanged): 1 = the IREG input stage (go_q, its kept go_cp copies, ib_q,\n"
   "    // xl_q, the split copy) on ck_ireg instead of clk, so a parent clock gate on clk sees one more cycle of lead\n"
   "    parameter integer IRCK = 0\n) ("),
  ("    input wire [7:0] ck_lsl,\n    input wire ck_node,\n    input  wire              clk,\n    input  wire              rst_n,\n    input  wire [15:0]       tile_id,\n    // instruction broadcast",
   "    input wire [7:0] ck_lsl,\n    input wire ck_node,\n    input wire ck_ireg,      // IRCK 1: the IREG stage clock (unused when IRCK = 0)\n    input  wire              clk,\n    input  wire              rst_n,\n    input  wire [15:0]       tile_id,\n    // instruction broadcast"),
  ("    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) go_q <= 1'b0;\n        else go_q <= ib_go;\n    end\n    (* keep *) always @(posedge clk) begin ib_q <= ib; xl_q <= xl; end",
   "    wire ck_ir = (IRCK != 0) ? ck_ireg : clk;   // IREG stage clock (IRCK 0: clk, unchanged)\n    always @(posedge ck_ir or negedge rst_n) begin\n        if (!rst_n) go_q <= 1'b0;\n        else go_q <= ib_go;\n    end\n    (* keep *) always @(posedge ck_ir) begin ib_q <= ib; xl_q <= xl; end"),
  ("            always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= ib_go;\n            assign go_cp[gc] = q;",
   "            always @(posedge ck_ir or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= ib_go;\n            assign go_cp[gc] = q;"),
  ("      (* keep *) always @(posedge clk) q <= ib[5*AW+5 +: 4];", "      (* keep *) always @(posedge ck_ir) q <= ib[5*AW+5 +: 4];"),
  ("    parameter integer REGROOT = 0,     // Q-ROMPARENT 10-16 (RPH 3 only): ck_reg = {data E, data W, gn W, gs W} regional roots; 0 = ck_reg unused\n    parameter integer CHILD_CLOCKS = 0\n) (",
   "    parameter integer REGROOT = 0,     // Q-ROMPARENT 10-16 (RPH 3 only): ck_reg = {data E, data W, gn W, gs W} regional roots; 0 = ck_reg unused\n    parameter integer CHILD_CLOCKS = 0,\n    parameter integer IRCK = 0         // DIE-QC-58B: ot_qwen_rom_tile_logic_w12 IRCK (IREG stage on ck_ireg)\n) ("),
  ("    input wire [2*CODE_BANKS-1:0] ck_rom,\n    input wire [7:0] ck_lsl,\n    input wire ck_node,\n    input  wire              clk,",
   "    input wire [2*CODE_BANKS-1:0] ck_rom,\n    input wire [7:0] ck_lsl,\n    input wire ck_node,\n    input wire ck_ireg,      // IRCK 1 only\n    input  wire              clk,"),
  (".NDH(NDH), .NODE(NODE), .BMUT(BMUT)) u_logic (\n        .ck_rpair(ck_rpair), .ck_pair1(ck_pair1), .ck_rqr(ck_rqr), .ck_rqre(ck_rqre), .ck_tx(ck_tx), .ck_reg(ck_reg), .ck_lsl(ck_lsl), .ck_node(ck_node),",
   ".NDH(NDH), .NODE(NODE), .BMUT(BMUT), .IRCK(IRCK)) u_logic (\n        .ck_rpair(ck_rpair), .ck_pair1(ck_pair1), .ck_rqr(ck_rqr), .ck_rqre(ck_rqre), .ck_tx(ck_tx), .ck_reg(ck_reg), .ck_lsl(ck_lsl), .ck_node(ck_node), .ck_ireg(ck_ireg),"),
 ],
 "ot_qwen_rom_tile_nk.sv": [
  ("    parameter integer NODE = 1            // q14 r9: 0 = node-less tile (ot_qwen_rom_tile_w12 NODE)\n) (",
   "    parameter integer NODE = 1,           // q14 r9: 0 = node-less tile (ot_qwen_rom_tile_w12 NODE)\n    parameter integer IRCK = 0            // DIE-QC-58B (opt-in): ot_qwen_rom_tile_w12 IRCK, IREG stage on ck_ireg\n) ("),
  ("    input wire ck_node,\n    input  wire              clk,", "    input wire ck_node,\n    input wire ck_ireg,      // IRCK 1 only\n    input  wire              clk,"),
  (".NDH(NDH), .NODE(NODE), .BMUT(BMUT), .KV_SLICE(0)) u_tile (", ".NDH(NDH), .NODE(NODE), .BMUT(BMUT), .KV_SLICE(0), .IRCK(IRCK)) u_tile ("),
  (".ck_lsl(ck_lsl), .ck_node(ck_node),\n        .clk(clk),", ".ck_lsl(ck_lsl), .ck_node(ck_node), .ck_ireg(ck_ireg),\n        .clk(clk),"),
 ],
 "qfd_tile_nk_rp2_45.sv": [
  ("    parameter integer REGROOT = 0     // Q-ROMPARENT: ck_dw/ck_de/ck_rsw/ck_rnw regional roots (RPH 3)\n) (",
   "    parameter integer REGROOT = 0,    // Q-ROMPARENT: ck_dw/ck_de/ck_rsw/ck_rnw regional roots (RPH 3)\n"
   "    // DIE-QC-58B form (1) (opt-in, default 0 = unchanged): 1 = the first stage after the input faces runs on ck_ireg\n"
   "    // (the u_tile IREG stage go_q / go_cp / ib_q / xl_q, and the node-port alignment / fault registers mis_q / fy_q)\n"
   "    // instead of ck / ck_fa3, so a parent clock gate on ck sees one more cycle of lead.  Same values on the same edges.\n"
   "    parameter integer IRCK = 0\n) ("),
  ("    input wire ck_fa4,\n", "    input wire ck_fa4,\n    input wire ck_ireg,      // IRCK 1 only (unused when IRCK = 0)\n"),
  (".RPH(RPH), .RQR(RQR), .XTX(XTX), .ANR(ANR), .NDH(NDH)) u_tile (", ".RPH(RPH), .RQR(RQR), .XTX(XTX), .ANR(ANR), .NDH(NDH), .IRCK(IRCK)) u_tile ("),
  ("        .ck_node(ck_node),\n        .clk(ck),", "        .ck_node(ck_node), .ck_ireg(ck_ireg),\n        .clk(ck),"),
  ("    reg mis_q;\n    always @(posedge ck_fa3)\n        if (!reset_q)", "    reg mis_q;\n    wire ck_fy = (IRCK != 0) ? ck_ireg : ck_fa3;\n    always @(posedge ck_fy)\n        if (!reset_q)"),
 ],
}
IRCK_REPO = {"ot_qwen_rom_tile_w12_land32.sv": "rtl/physical/a0_rc15_selected_2000/ot_qwen_rom_tile_w12_land32.sv",
             "ot_qwen_rom_tile_nk.sv": "rtl/physical/ot_qwen_rom_tile_nk.sv",
             "qfd_tile_nk_rp2_45.sv": "rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_45.sv"}


def irck_apply(text, name):
    for old, new in IRCK_EDITS[name]:
        if text.count(old) != 1:
            sys.exit(f"derive: IRCK edit of {name}: expected 1 match of {old[:60]!r}, got {text.count(old)}")
        text = text.replace(old, new)
    return text


def ireg(kit, repo, b3_dir, log):
    """Form (1): ICG_IREG 1 (params + rtl_lint chparam), the four RTL files, en_q as the only ENA start re-tapped by
    58A's B3 early branch (b3_early.tcl auto MID, ENA repeaters; no early group, no hold pads: DIE-QC-58A NK lesson 2)."""
    for name in IRCK_EDITS:
        p = os.path.join(kit, "rtl", name); t = irck_apply(open(p).read(), name); open(p, "w").write(t)
        r = os.path.join(repo, IRCK_REPO[name])
        same = (open(r).read() == t)
        log.append(f"rtl/{name}: IRCK edits ({len(IRCK_EDITS[name])}) -> sha16 {sha(p)}"
                   + (" == branch file" if same else f" (kit base differs from {IRCK_REPO[name]}; edits applied to the kit copy)"))
        if not same and name != "qfd_tile_nk_rp2_45.sv":
            sys.exit(f"derive: kit {name} + IRCK edits differs from the branch file {r}")
    cfg = os.path.join(kit, "config.mk"); t = open(cfg).read()
    t = sub1(t, r"^(export VERILOG_TOP_PARAMS = .*\bICG 1 ICG_EREG 1)\b", r"\1 ICG_IREG 1", "ICG_IREG param")
    base_pre = re.findall(r"^(?:override )?export PRE_CTS_TCL = (\S+)$", t, re.M)
    if not base_pre or base_pre[-1] != "/work/fc_dt_lift_cts.tcl":
        sys.exit(f"derive: kit PRE_CTS_TCL {base_pre} is not the fc_dt lift hook b3_pre_cts.tcl wraps")
    t += ("# DIE-QC-58B form (1) (DIE-QC-59 11-01): first stage + node leaf on the ungated ck, ENA = en_q alone; en_q re-tapped\n"
          "# on the ungated pre-gate chain by DIE-QC-58A's B3 early branch (auto: ENA deficit vs own D setup), ENA repeaters.\n"
          "override export PRE_CTS_TCL = /work/b3_pre_cts.tcl\n"
          "export OT_B3_ICG = g_icg.g_root.u_icg\n"
          "export OT_B3_MID = g_icg.g_root.g_er.en_q*=auto\n"
          "export OT_B3_ENA_UM = 80\n")
    open(cfg, "w").write(t)
    log.append("config.mk: ICG_IREG 1, PRE_CTS_TCL b3_pre_cts.tcl, OT_B3_ICG / OT_B3_MID en_q auto / OT_B3_ENA_UM 80")
    p = os.path.join(kit, "rtl_lint.ys"); s = open(p).read()
    s = sub1(s, r"(chparam .*-set ICG 1 -set ICG_EREG 1)\b", r"\1 -set ICG_IREG 1", "rtl_lint chparam ICG_IREG")
    open(p, "w").write(s); log.append("rtl_lint.ys: chparam ICG_IREG 1")
    for f in ("b3_early.tcl", "b3_pre_cts.tcl"):
        shutil.copyfile(os.path.join(b3_dir, f), os.path.join(kit, f))
        log.append(f"{f}: DIE-QC-58A B3 from {b3_dir} (sha16 {sha(os.path.join(kit, f))})")


def ireg_kit(argv):
    """Form (1) kit from an ICG=1 kit of this script (the ICG=2 GEOM-59 sources are pruned): + ICG_EREG 1 (B2 en_q, home
    2 um east of the root gate) + ireg() + hold-ep-info + grt50 + face-lift + dpl-retry, all listed in DERIVE.json.
       derive_icg1_kit.py --ireg-kit SRC_ICG1_KIT DST --suffix SUF --repo REPO --b3 DIR --a0c RTL_A0C"""
    ap = argparse.ArgumentParser(prog="derive_icg1_kit.py --ireg-kit")
    ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--suffix", required=True)
    ap.add_argument("--repo", required=True); ap.add_argument("--b3", required=True); ap.add_argument("--a0c", required=True)
    a = ap.parse_args(argv)
    if os.path.exists(a.dst):
        sys.exit(f"derive: {a.dst} exists")
    sd = json.load(open(os.path.join(a.src, "DERIVE.json")))
    if sd.get("tile") != "nk" or sd.get("ereg"):
        sys.exit("derive: --ireg-kit needs an NK ICG=1 (non-EREG) kit of this script")
    if "ICG_IREG" not in open(a.a0c).read():
        sys.exit("derive: --a0c has no ICG_IREG param")
    shutil.copytree(a.src, a.dst, ignore=lambda d, names: [n for n in names if n in SKIP or n.startswith("FAIL")
                                                            or (d == a.src and n.endswith(".log"))])
    log = []
    cfg = os.path.join(a.dst, "config.mk"); t = open(cfg).read()
    old_nick = re.search(r"^export DESIGN_NICKNAME = (\S+)$", t, re.M).group(1)
    nick = f"kq_qfd_tile_nk_a0c_{a.suffix}"
    t = sub1(t, r"^export DESIGN_NICKNAME = \S+$", f"export DESIGN_NICKNAME = {nick}", "nickname")
    t = sub1(t, r"^(export VERILOG_TOP_PARAMS = .*\bICG 1)\b", r"\1 ICG_EREG 1", "ICG_EREG param")
    open(cfg, "w").write(t); log.append(f"config.mk: nickname {nick}, ICG_EREG 1")
    p = os.path.join(a.dst, "rtl_lint.ys"); s = open(p).read()
    s = sub1(s, r"(chparam .*-set ICG 1)\b", r"\1 -set ICG_EREG 1", "rtl_lint chparam ICG_EREG")
    open(p, "w").write(s); log.append("rtl_lint.ys: chparam ICG_EREG 1")
    gh = os.path.join(a.dst, "nk_graph_homes.tsv"); rows = open(gh).read().splitlines()
    g = [r for r in rows if r.split("\t")[0] == "g_icg.g_root.u_icg"]
    if len(g) != 1:
        sys.exit("derive: root gate home not found")
    e = g[0].split("\t"); e[0] = "g_icg.g_root.g_er.en_q$_DFF_PN1_"; e[1] = f"{float(e[1]) + 2.0:.3f}"
    open(gh, "w").write("\n".join(rows + ["\t".join(e)]) + "\n"); log.append(f"nk_graph_homes.tsv: +g_er.en_q at ({e[1]},{e[2]})")
    shutil.copyfile(a.a0c, os.path.join(a.dst, "rtl", "qfd_tile_nk_a0c.sv"))
    log.append(f"rtl/qfd_tile_nk_a0c.sv: ICG_EREG / ICG_IREG RTL from {a.a0c} (sha16 {sha(a.a0c)})")
    ireg(a.dst, a.repo, a.b3, log)
    json.dump({"tool": "derive_icg1_kit.py --ireg-kit", "lane": "DIE-QC-58B", "src": os.path.abspath(a.src), "src_nickname": old_nick,
               "dst_nickname": nick, "tile": "nk", "frame_tt_ps": sd["frame_tt_ps"], "frame_ff_ps": sd["frame_ff_ps"],
               "cts_args_added": sd["cts_args_added"], "ereg": True, "ireg": True, "changes": log,
               "sha16": {n: sha(os.path.join(a.dst, n)) for n in
                         ("config.mk", "rtl_lint.ys", "nk_graph_homes.tsv", "rtl/qfd_tile_nk_a0c.sv", "b3_early.tcl", "b3_pre_cts.tcl")
                         + tuple(f"rtl/{n}" for n in IRCK_EDITS)}},
              open(os.path.join(a.dst, "DERIVE.json"), "w"), indent=1)
    print("\n".join(log))
    hold_ep_info(a.dst); grt50(a.dst); face_lift(a.dst); dpl_retry(a.dst)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--prune":
        return prune(sys.argv[2], sys.argv[3], sys.argv[4])
    if len(sys.argv) > 1 and sys.argv[1] == "--ireg-kit":
        return ireg_kit(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "--dpl-retry":
        return dpl_retry(sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "--face-lift":
        return face_lift(sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "--grt50":
        return grt50(sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "--hold-ep-info":
        return hold_ep_info(sys.argv[2])
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--tile", choices=["nk", "nl"], required=True)
    ap.add_argument("--tt", type=float, required=True); ap.add_argument("--ff", type=float, required=True)
    ap.add_argument("--suffix", required=True)
    ap.add_argument("--lec-hints", help="untrusted LEC register hints copied to KIT/lec_hints.json (proved by lec.py "
                    "induction, never a waiver); A0: results/codex_qc_a0_2340/parent_zero_proof/hints.json (nb_t[6:0])")
    ap.add_argument("--ereg", metavar="RTL_A0C", help="B2: ICG_EREG 1 (registered root-gate enable beside the gate); copies "
                    "this qfd_tile_<t>_a0c.sv (the branch RTL with the opt-in ICG_EREG param) into KIT/rtl and homes en_q "
                    "next to the root gate")
    ap.add_argument("--ireg", metavar="REPO", help="form (1), NK, needs --ereg: ICG_IREG 1 + the IRCK body RTL (checked against "
                    "REPO's branch files) + 58A B3 en_q re-tap (--b3 DIR with b3_early.tcl / b3_pre_cts.tcl)")
    ap.add_argument("--b3", metavar="DIR", help="dir with DIE-QC-58A b3_early.tcl (v3) and b3_pre_cts.tcl")
    ap.add_argument("--no-dpl-retry", action="store_true", help="omit the default-on check_placement legalization retry")
    ap.add_argument("--cts-extra", default="", help="B2: extra clock_tree_synthesis args appended after V3")
    a = ap.parse_args()
    if os.path.exists(a.dst):
        sys.exit(f"derive: {a.dst} exists")
    shutil.copytree(a.src, a.dst, ignore=lambda d, names: [n for n in names if n in SKIP or (d == a.src and n.endswith(".log"))])
    log = []
    cfg = os.path.join(a.dst, "config.mk"); t = open(cfg).read()
    old_nick = re.search(r"^export DESIGN_NICKNAME = (\S+)$", t, re.M).group(1)
    nick = f"kq_qfd_tile_{a.tile}_a0c_{a.suffix}"
    t = sub1(t, r"^export DESIGN_NICKNAME = \S+$", f"export DESIGN_NICKNAME = {nick}", "nickname")
    t = sub1(t, r"^(export VERILOG_TOP_PARAMS = .*\bICG) 2\b", r"\1 1", "ICG param")
    t = sub1(t, r"^export OT_VCLK_TT = \S+$", f"export OT_VCLK_TT = {a.tt}", "OT_VCLK_TT")
    t = sub1(t, r"^export OT_VCLK_FF = \S+$", f"export OT_VCLK_FF = {a.ff}", "OT_VCLK_FF")
    t = re.sub(r"(TT setup vclk) [0-9.]+( / scene BC \(mode ff\) FF hold vclk) [0-9.]+", rf"\g<1> {a.tt}\g<2> {a.ff}", t)
    base = re.findall(r"^(?:override )?export CTS_ARGS = (.*)$", t, re.M)[-1]
    t += (f"\n# DIE-QC-58B (COORD 10-31 ruling 3 variant B): ICG=1 single tile-root gate (DIE-QC-16 form), declared A0 frame\n"
          f"# {a.tt}/{a.ff}, CTS = DIE-QC-57d V3 tree knobs. GENERATED by derive_icg1_kit.py from {old_nick}.\n"
          f"override export CTS_ARGS = {base} {V3}{(' ' + a.cts_extra) if a.cts_extra else ''}\n")
    if a.ereg:
        t = sub1(t, r"^(export VERILOG_TOP_PARAMS = .*\bICG 1)\b", r"\1 ICG_EREG 1", "ICG_EREG param")
    open(cfg, "w").write(t)
    log.append(f"config.mk: nickname, ICG 2->1, OT_VCLK_TT/FF, CTS_ARGS V3{(' + ' + a.cts_extra) if a.cts_extra else ''}"
               f"{', ICG_EREG 1' if a.ereg else ''}")
    for f, v in (("constraint.sdc", a.tt), ("vclk_ff.sdc", a.ff)):
        p = os.path.join(a.dst, f); s = open(p).read()
        s = sub1(s, r"^set_clock_latency -source \S+ \[get_clocks vclk\]$", f"set_clock_latency -source {v} [get_clocks vclk]", f)
        open(p, "w").write(s); log.append(f"{f}: vclk source latency {v}")
    p = os.path.join(a.dst, "sdc_lint.json"); j = json.load(open(p))
    j["insertion_ps"] = a.tt; j["insertion_ff_ps"] = a.ff
    json.dump(j, open(p, "w"), indent=1); log.append(f"sdc_lint.json: insertion {a.tt}/{a.ff}")
    p = os.path.join(a.dst, "clock_binding.json"); j = json.load(open(p))
    if j["insertion_ps"]["tt"] != a.tt or j["insertion_ps"]["ff"] != a.ff:
        j["insertion_ps"] = {"tt": a.tt, "ff": a.ff}
        b = (f"DECLARED A0 frame {a.tt} TT / {a.ff} FF (COORD DIE-QC-18 measured A0 frame; DIE-QC-57d: the old 250/202.5 "
             f"wrapper frame was stale for this tile); DIE-QC-58B derive_icg1_kit.py")
        j["basis"] = {"tt": b, "ff": b}
        json.dump(j, open(p, "w"), indent=1); log.append(f"clock_binding.json: insertion {a.tt}/{a.ff}")
    p = os.path.join(a.dst, "rtl_lint.ys"); s = open(p).read()
    s = sub1(s, r"(chparam .*-set ICG) 2\b", r"\1 1", "rtl_lint chparam")
    if a.ereg:
        s = sub1(s, r"(chparam .*-set ICG 1)\b", r"\1 -set ICG_EREG 1", "rtl_lint chparam ICG_EREG")
    open(p, "w").write(s)
    log.append("rtl_lint.ys: chparam ICG 1" + (" ICG_EREG 1" if a.ereg else ""))
    gh = os.path.join(a.dst, f"{a.tile}_graph_homes.tsv"); rows = open(gh).read().splitlines()
    hop = [r for r in rows if r.startswith("g_icg.g_hop.")]
    ck = [r for r in hop if r.split("\t")[0] == "g_icg.g_hop.u_hop_ck/u_icg"]
    if len(ck) != 1:
        sys.exit("derive: u_hop_ck/u_icg home not found")
    f = ck[0].split("\t"); f[0] = "g_icg.g_root.u_icg"
    keep = [r for r in rows if not r.startswith("g_icg.g_hop.")] + ["\t".join(f)]
    if a.ereg:   # en_q 2 um from the gate (same row): enable wire ~2 um, en_q CLK on the ungated root next to the gate CLK
        e = list(f); e[0] = "g_icg.g_root.g_er.en_q$_DFF_PN1_"; e[1] = f"{float(f[1]) + 2.0:.3f}"; keep.append("\t".join(e))
    open(gh, "w").write("\n".join(keep) + "\n")
    log.append(f"{os.path.basename(gh)}: -{len(hop)} g_hop rows, +g_icg.g_root.u_icg at ({f[1]},{f[2]})"
               + (" +g_er.en_q 2 um east" if a.ereg else ""))
    if a.ereg:
        d = os.path.join(a.dst, "rtl", f"qfd_tile_{a.tile}_a0c.sv")
        if "ICG_EREG" not in open(a.ereg).read():
            sys.exit("derive: --ereg RTL has no ICG_EREG param")
        shutil.copyfile(a.ereg, d); log.append(f"rtl/qfd_tile_{a.tile}_a0c.sv: ICG_EREG RTL from {a.ereg} (sha16 {sha(a.ereg)})")
    if a.ireg:
        if not a.ereg or a.tile != "nk" or not a.b3 or "ICG_IREG" not in open(a.ereg).read():
            sys.exit("derive: --ireg needs --tile nk, --b3 and an --ereg a0c with ICG_IREG")
        ireg(a.dst, a.ireg, a.b3, log)
    if a.lec_hints:
        shutil.copyfile(a.lec_hints, os.path.join(a.dst, "lec_hints.json"))
        log.append(f"lec_hints.json: copied from {a.lec_hints} (sha16 {sha(a.lec_hints)})")
    json.dump({"tool": "derive_icg1_kit.py", "lane": "DIE-QC-58B", "src": os.path.abspath(a.src), "src_nickname": old_nick,
               "dst_nickname": nick, "tile": a.tile, "frame_tt_ps": a.tt, "frame_ff_ps": a.ff, "cts_args_added": (V3 + " " + a.cts_extra).strip(),
               "ereg": bool(a.ereg), "ireg": bool(a.ireg),
               "changes": log, "sha16": {n: sha(os.path.join(a.dst, n)) for n in
                                          ("config.mk", "constraint.sdc", "vclk_ff.sdc", "sdc_lint.json", "rtl_lint.ys",
                                           f"{a.tile}_graph_homes.tsv", f"rtl/qfd_tile_{a.tile}_a0c.sv")
                                          + ((tuple(f"rtl/{n}" for n in IRCK_EDITS) + ("b3_early.tcl", "b3_pre_cts.tcl")) if a.ireg else ())}},
              open(os.path.join(a.dst, "DERIVE.json"), "w"), indent=1)
    print("\n".join(log))
    # class fix, default-on (DIE-QC-59 11-01): CTS legalization retry after a met hold repair (NL e1 DPL-0033)
    if not a.no_dpl_retry:
        dpl_retry(a.dst)


if __name__ == "__main__":
    main()
