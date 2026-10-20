#!/usr/bin/env python3
"""HBM-PGLG3 2026-10-20 (H.STA.BLK.15.3): the LIGHT SU port-group slice as TWO LANDED HALVES.

The one-column landed parent hbm_su_pgslice_lg_light_d4g (R0 | R1 | S | R2 | R3, 1235.52 x 3045.6, aspect 2.47) failed lg4
(65cea4293: raw macro clock cotiming, fill 67.7 %, read-slot counter rc[0] 4,181 loads, ck_s 23,943 sinks).  SAFE-AUDIT form
(results/arch/safe_audit_1019/hbm.md; lanes/HBM-VMG7-5.md step 3): cut the column through the S band into two hardened
halves, each with its own regional roots, read counters as kept per-chunk copies, wide pads as ring buffers:

  H_LO  ot_hbm_su_static_pglg_lo   R0 | R1 | S_lo   (store groups 0/1)  S_lo = face relays, u_sinh HI 0, u_schk, u_sout
  H_HI  ot_hbm_su_static_pglg_hi   S_hi | R2 | R3   (store groups 2/3)  S_hi = face relays, u_sinh HI 1
  seam  H_HI r2 -> H_LO S: {ret2d, ret3b} 1,042 b LANDED (ot_hbm_su_pglg_seam_w in the H_HI top, _r in the H_LO top)

Flat halves (wires-only, lp.py inputs) ot_hbm_su_static_pglg_{lo,hi}f: their composition with a wire seam is EXACTLY the
flat region parent ot_hbm_su_static_pgslice_rgf (u_sin = 2 x u_sinh + u_schk, same registers/edges).  lp.py lands each half
(landing_chunk_bits 24 + landing_reset_forest: per-chunk kept read/write counters and reset leaves; pad_ring_min 3: wide
alignment pads as ring buffers) -> <half>f_lp; the kit tops add the seam landing.  The H_HI ret outputs leave at a common
offset (out_regs on ret2d) and the seam adds E+1 = 2, which is exactly H_LO's input offset of the seam ports (= u_sout's
offset): the landed composition == the flat composition with the same port offsets as the one-column parent, so the
lockstep bench tb_hbm_su_pglg_h2 (vs pgslice_lg) uses the same RT / IR / SWQ offsets.

usage: su_pglg_half_gen.py rtl|kits [--root REPO] [--tag r1]
   rtl : write the flat halves + lp specs (then run lp.py gen on both specs), then `kits` writes the kit tops,
         the composite ot_hbm_su_static_pglg_h2rg and the ref_tile kit specs (primary + fallback outline).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import su_pgslice_rgf_gen as rgf  # noqa: E402

S = "rtl/hbm_accel/generic/adapters/static_su"
LANE = "HBM-PGLG3"
REC = "results/rtl/hbm_pglg3_1020"
LOF, HIF = "ot_hbm_su_static_pglg_lof", "ot_hbm_su_static_pglg_hif"
LO, HI = "ot_hbm_su_static_pglg_lo", "ot_hbm_su_static_pglg_hi"
H2RG = "ot_hbm_su_static_pglg_h2rg"
SEAM_W = 1042
SEAM_CB = 24
SEAM_C = (SEAM_W + SEAM_CB - 1) // SEAM_CB
SEAM_DEPTH = 4

# ---------------------------------------------------------------- geometry (um, children on the 43.2 lattice)
W_OUT = 1235.52
ROW = rgf.ROW                       # 172.8 (151.2 child + 21.6 channel)
REG_H = rgf.REG_H                   # 691.2 (4 rows)
SB_H = 172.8                        # half S band (incl. the 21.6 channel to the last row)
H_OUT = round(43.2 + 2 * REG_H + SB_H - 21.6 + 0.0, 2)   # 1576.8 -> aspect 1.276
# H_LO: r0 rows from 43.2, r1 above, S_lo band at the top (seam = N face)
Y_LO = {0: 43.2, 1: 43.2 + REG_H}
# H_HI: S_hi band at the bottom (seam = S face), r2 rows from 172.8, r3 above
Y_HI = {2: SB_H, 3: SB_H + REG_H}
X_COL = rgf.X_COL


def child_lines(w, r, rlist_src):
    """region glue + 8 KIND0 lanes + 8 banks of region r (verbatim structure of su_pgslice_rgf_gen)"""
    co, lo = rgf.offsets(rgf.CTL), rgf.offsets(rgf.LO)
    LOW = rgf.LOW
    c_in, rf_in, di_in = rlist_src
    w(f" // ---- region r{r} (store group {r}: h {r % 2}, hi {r // 2}; lanes / banks {8 * r}..{8 * r + 7})")
    w(f" ot_hbm_su_pgrg_rg #(.R({r}),.QID(QID),.G(G),.STRAP(STRAP),.MUT(GMUT)) u_rg{r}(.ck(ck),.rst_n(rst_n),.pos(pos_r{r}),"
      f".control({c_in}),.rf_u({rf_in}),.di({di_in})," + ",".join(f".ctl{j}(ctl_r{r}_{j})" for j in range(8)) +
      f",.lid(lid_r{r}),.rd_q(rdq_r{r}),.lo(lo_r{r}),.b_rv(brv_r{r}),.b_ra(bra_r{r}),.b_wv(bwv_r{r}),.b_wa(bwa_r{r}),"
      f".b_wd(bwd_r{r}),.bq(bq_r{r}),.ret(ret_r{r}));")
    for j in range(8):
        c = f"ctl_r{r}_{j}"
        cs = []
        for n, wd in rgf.CTL:
            lsb, ww = co[n]
            if n == "ld_c":
                parts = [rgf.sel(c, lsb + s * 240, 168) for s in range(4, -1, -1)]
                cs.append(f".ld_c({{{','.join(parts)}}})")
            else:
                cs.append(f".{n}({rgf.sel(c, lsb, ww)})")
        cs.append(f".cx_srcs({rgf.sel(c, co['srcs'][0], 8)})")
        base = j * LOW
        outs = [f".{n}({rgf.sel(f'lo_r{r}', base + lo[n][0], lo[n][1])})" for n, _ in rgf.LO]
        clk = ",".join([f".clk_stage_{k}(ck)" for k in range(8)] + [f".clk_insert_{k}(ck)" for k in range(4)])
        w(f" ot_hbm_su_static_kind0_lat4_leaf1_physical u_ln_r{r}_{j}({clk},.rst_n(rst_n),"
          f".lane_id(lid_r{r}[{j * 11 + 10}:{j * 11}]),{','.join(cs)},.vi_q(bq_r{r}[{j * 192 + 159}:{j * 192 + 128}]),"
          f".rd_q(rdq_r{r}[{j * 128 + 127}:{j * 128}]),{','.join(outs)},.side_v(),.side_x(),.side_y(32'd0));")
        w(f" ot_hbm_su_static_bank6_clock_physical u_bk_r{r}_{j}(.clk(ck),.clk_rd(ck),.clk_ws(ck),"
          + ",".join(f".clk_macro{k}(ck)" for k in range(6)) + f",.rst_n(rst_n),"
          f".read_v(brv_r{r}[{j * 6 + 5}:{j * 6}]),.read_addr(bra_r{r}[{j * 54 + 53}:{j * 54}]),"
          f".read_data(bq_r{r}[{j * 192 + 191}:{j * 192}]),.read_return(),.write_v(bwv_r{r}[{j}]),"
          f".write_addr(bwa_r{r}[{j * 9 + 8}:{j * 9}]),.write_data(bwd_r{r}[{j * 32 + 31}:{j * 32}]));")


def region_wires(w, regs):
    for r in regs:
        w(" wire [1741:0] " + ", ".join(f"ctl_r{r}_{j}" for j in range(8)) + ";")
        w(f" wire [87:0] lid_r{r}; wire [1023:0] rdq_r{r}; wire [{8 * rgf.LOW - 1}:0] lo_r{r}; wire [47:0] brv_r{r};"
          f" wire [431:0] bra_r{r}; wire [7:0] bwv_r{r}; wire [71:0] bwa_r{r}; wire [255:0] bwd_r{r}; wire [1535:0] bq_r{r};")


W_IN = [("control", 1742), ("vmr_cmd", 60), ("vmw_cmd", 78), ("rf_bword", 128), ("rf_bcmd", 36)]


def flat(half):
    """wires-only flat half (lp.py input)"""
    lo = half == "lo"
    top = LOF if lo else HIF
    HIb = 0 if lo else 1
    inner, outer = (1, 0) if lo else (2, 3)
    sfx = str(HIb)
    L = []
    w = L.append
    w("`timescale 1ns/1ps")
    w("`default_nettype none")
    w(f"// GENERATED by tools/hbm_static/su_pglg_half_gen.py -- do not edit. {LANE} 2026-10-20 (H.STA.BLK.15.3).")
    w(f"// WIRES-ONLY flat {'LOWER' if lo else 'UPPER'} half of the LIGHT SU port-group slice in two-half form (lp.py input; kit top")
    w(f"// {LO if lo else HI} = {top}_lp + the seam landing {'reader' if lo else 'ring'}). Glue: ot_hbm_su_pgrg_parts.sv + ot_hbm_su_pglg_half_parts.sv.")
    w("// Flat composition lof + hif (seam = wires ret2s = ret2d, ret3s = ret3b) == ot_hbm_su_static_pgslice_rgf (same registers, edges).")
    w(f"module {top} #(")
    w(" parameter integer QID=1, G=2, STRAP=1, PRETREE=0, GMUT=0")
    w(")(")
    ports = ["input wire ck", "input wire rst_n"]
    if lo:
        ports += ["input wire [3:0] pos"]
    ports += [f"input wire [3:0] pos_r{outer}", f"input wire [3:0] pos_r{inner}"]
    ports += [f"input wire [{n_w - 1}:0] {n}" for n, n_w in W_IN]
    if lo:
        ports += ["input wire [255:0] rf_dsec", "input wire [11:0] red_sel", "output wire [31:0] slice_x",
                  "input wire [11:0] tree_cmd", "output wire [66:0] tree_o", "output wire [1023:0] pt_ro_x",
                  "output wire [31:0] pt_ro_v", "output wire [1023:0] inj_q"]
    ports += [f"input wire dw_v{sfx}", f"input wire [8:0] dw_row{sfx}", f"input wire [511:0] dw_d{sfx}"]
    if lo:
        ports += ["output wire fault", "output wire [561:0] su_wq", "input wire [513:0] su_rr", "input wire [3:0] ij_v",
                  "input wire [17:0] ij_row0", "input wire ij_bad", "input wire pg_fault",
                  "input wire [520:0] ret2s", "input wire [520:0] ret3s"]
    else:
        ports += ["input wire [513:0] su_rr", "input wire [1:0] ij_v1", "input wire [17:0] ij_row1",
                  "output wire [520:0] ret2d", "output wire [520:0] ret3b"]
    w(" " + ",\n ".join(ports))
    w(");")
    w(f" wire [163:0] rf_u; wire [541:0] di{inner}, di{outer};")
    w(f" wire [2447:0] rly{inner}_q; wire [520:0] ret_r{inner}, ret_r{outer};")
    if lo:
        w(" wire [520:0] ret0b, ret1d; wire s_cond;")
    region_wires(w, (outer, inner) if lo else (inner, outer))
    wl = W_IN + [(f"dw_v{sfx}", 1), (f"dw_row{sfx}", 9), (f"dw_d{sfx}", 512)]
    el = [("su_rr", 514)] + ([("ij_v", 4), ("ij_row0", 18), ("ij_bad", 1), ("pg_fault", 1)] if lo else
                            [("ij_v1", 2), ("ij_row1", 18)])
    w(" // ---- face relays (S band of the half: +1 edge on every S-bound input; GMUT 23: E relay bypassed)")
    for nm, lst, byp in (("u_wrly", wl, "0"), ("u_erly", el, "(GMUT==23)?1:0")):
        tot = sum(wd for _, wd in lst)
        for n, wd in lst:
            w(f" wire [{wd - 1}:0] {n}_f;")
        w(f" ot_hbm_su_pgrg_frly #(.W({tot}),.BYP({byp})) {nm}(.ck(ck),.d({{{','.join(n for n, _ in lst)}}}),"
          f".q({{{','.join(n + '_f' for n, _ in lst)}}}));")
    ijv = "ij_v_f[1:0]" if lo else "ij_v1_f"
    ijr = "ij_row0_f" if lo else "ij_row1_f"
    w(f" // ---- S_{half}: inbound service of store groups {2 * HIb}/{2 * HIb + 1}")
    w(f" ot_hbm_su_pgrg_sinh #(.HI({HIb}),.MUT(GMUT)) u_sinh(.ck(ck),.rst_n(rst_n),.vmr_cmd(vmr_cmd_f),.vmw_cmd(vmw_cmd_f),"
      f".su_rr(su_rr_f),.ij_v({ijv}),.ij_row({ijr}),.rf_bword(rf_bword_f),.rf_bcmd(rf_bcmd_f),.dw_v(dw_v{sfx}_f),"
      f".dw_row(dw_row{sfx}_f),.dw_d(dw_d{sfx}_f),.rf_u(rf_u),.dia(di{2 * HIb}),.dib(di{2 * HIb + 1}));")
    if lo:
        w(" ot_hbm_su_pgrg_schk #(.QID(QID),.G(G),.STRAP(STRAP),.MUT(GMUT)) u_schk(.ck(ck),.rst_n(rst_n),.pos(pos),"
          ".vmr_cmd(vmr_cmd_f),.vmw_cmd(vmw_cmd_f),.ij_v(ij_v_f),.ij_bad(ij_bad_f),.pg_fault(pg_fault_f),.s_cond(s_cond));")
        w(" ot_hbm_su_pgrg_sout #(.QID(QID),.G(G),.STRAP(STRAP),.PRETREE(PRETREE),.MUT(GMUT),.WQ_PAD(1),.FRLY(1)) u_sout(.ck(ck),"
          ".rst_n(rst_n),.pos(pos),.vmw_cmd(vmw_cmd_f),.rf_dsec_p(rf_dsec),.red_sel_p(red_sel),.tree_cmd_p(tree_cmd),.ret0(ret0b),"
          ".ret1(ret1d),.ret2(ret2s),.ret3(ret3s),.s_cond(s_cond),.slice_x(slice_x),.tree_o(tree_o),.pt_ro_x(pt_ro_x),"
          ".pt_ro_v(pt_ro_v),.inj_q(inj_q),.su_wq(su_wq),.fault(fault));")
    w(f" // ---- inner region r{inner}: relay of the outer region r{outer} (inbound 1 stage; GMUT 20: 2) and the return alignment")
    w(f" ot_hbm_su_pgrg_dly #(.W(2448),.N((GMUT==20)?2:1)) u_rly{inner}(.ck(ck),.d({{control_f,rf_u,di{outer}}}),.q(rly{inner}_q));")
    w(f" ot_hbm_su_pgrg_dly #(.W(521),.N(1)) u_rlyb{inner}(.ck(ck),.d(ret_r{outer}),.q(ret{outer}b));")
    w(f" ot_hbm_su_pgrg_dly #(.W(521),.N(2)) u_dly{inner}(.ck(ck),.d(ret_r{inner}),.q(ret{inner}d));")
    for r in ((outer, inner) if lo else (inner, outer)):
        if r == inner:
            src = ("control_f", "rf_u", f"di{r}")
        else:
            src = (f"rly{inner}_q[2447:706]", f"rly{inner}_q[705:542]", f"rly{inner}_q[541:0]")
        child_lines(w, r, src)
    w("endmodule")
    w("`default_nettype wire")
    return "\n".join(L) + "\n"


def lp_spec(half):
    lo = half == "lo"
    top = LOF if lo else HIF
    inner, outer = (1, 0) if lo else (2, 3)
    Y = Y_LO if lo else Y_HI
    sc = (H_OUT - SB_H / 2) if lo else SB_H / 2
    s_insts = ["u_wrly", "u_erly", "u_sinh"] + (["u_schk", "u_sout"] if lo else [])
    regions = [dict(name="s", insts=s_insts, centre=[W_OUT / 2, round(sc, 2)])]
    for r in (inner, outer):
        ins = [f"u_rg{r}", f"u_ln_r{r}_*", f"u_bk_r{r}_*"] + ([f"u_rly{r}", f"u_rlyb{r}", f"u_dly{r}"] if r == inner else [])
        regions.append(dict(name=f"r{r}", insts=ins, centre=[W_OUT / 2, round(Y[r] + REG_H / 2 - 10.8, 2)]))
    ins_ports = [n for n, _ in W_IN] + [f"dw_v{0 if lo else 1}", f"dw_row{0 if lo else 1}", f"dw_d{0 if lo else 1}", "su_rr"]
    ins_ports += (["rf_dsec", "red_sel", "tree_cmd", "ij_v", "ij_row0", "ij_bad", "pg_fault", "ret2s", "ret3s"] if lo
                  else ["ij_v1", "ij_row1"])
    static = (["pos"] if lo else []) + [f"pos_r{outer}", f"pos_r{inner}"]
    spec = dict(
        top=top, top_lp=(LO if lo else HI), sources=[f"{S}/top/{top}.sv"],
        child_sources=[f"{S}/top/ot_hbm_su_pgrg_parts.sv", f"{S}/top/ot_hbm_su_pglg_half_parts.sv",
                       f"{S}/arithmetic/ot_hbm_su_static_kind0_lat4_leaf1_physical.sv",
                       f"{S}/data_store/ot_hbm_su_static_bank6_clock_physical.sv"],
        defines=["OT_HARD_CHILDREN", "OT_SU_SYNC_RST"], params={},
        out_dir=f"{S}/top/lp", record_dir=f"{REC}/lp",
        clock_ports=["ck"],
        clock_pins=[f"clk_stage_{k}" for k in range(8)] + [f"clk_insert_{k}" for k in range(4)]
        + ["clk", "clk_rd", "clk_ws"] + [f"clk_macro{k}" for k in range(6)] + ["ck"],
        reset_port="rst_n", reset_pins=["rst_n"], reset_region="s",
        regions=regions, port_regions={p: "s" for p in ins_ports}, static=static,
        D=2, E=1, reach_um=405,
        landing_chunk_bits=24, landing_reset_forest=True, pad_ring_min=3,
        mut_child="u_sout" if lo else "u_sinh",
        bench=dict(cycles=1500, reset_cycles=8, sim="verilator"),
        why=(f"{LANE} 10-20: {'lower' if lo else 'upper'} half of the LIGHT SU slice (two landed halves, SAFE-AUDIT form). "
             "D 2 / E 1 as the one-column parent; landing_chunk_bits 24 + landing_reset_forest: every landing's read-slot "
             "counter / slot one-hot / valid is a kept per-chunk copy with its own reset leaf (lg4: rc[0] 4,181 loads); "
             "pad_ring_min 3: wide alignment pads are ring buffers (item 5)."))
    if not lo:
        # common output offset of the seam returns: ret2d (inner, t = 2) padded to ret3b's (outer, t = 6)
        spec["out_regs"] = {"ret2d": 4}
    return spec


def write_rtl(root):
    for half in ("lo", "hi"):
        top = LOF if half == "lo" else HIF
        (root / f"{S}/top/{top}.sv").write_text(flat(half))
        (root / f"tools/landed_parent/specs/{top}.json").write_text(json.dumps(lp_spec(half), indent=1) + "\n")
        print(f"wrote {S}/top/{top}.sv + tools/landed_parent/specs/{top}.json")


# ---------------------------------------------------------------- kit tops (lp output + seam landing)
def inject(root, half):
    """The kit top IS the lp.py output (spec top_lp = the kit top, so its record is the kit's landed_record); the seam
    landing is injected into it here (run after `lp.py gen`): H_LO -- the seam ports ret2s / ret3s become internal wires
    driven by the landing read ot_hbm_su_pglg_seam_r (ck_s) from new ports seam_bank / seam_vld; H_HI -- ret2d / ret3b
    become internal wires feeding the landing ring ot_hbm_su_pglg_seam_w (ck_r2) that drives seam_bank / seam_vld.
    Both seam halves release from rst_n through the same DEPTH forest (G == R0)."""
    import re
    lo = half == "lo"
    top = LO if lo else HI
    f = root / f"{S}/top/lp/{top}.sv"
    txt = f.read_text()
    if "ot_hbm_su_pglg_seam_" in txt:
        raise SystemExit(f"{f}: already injected (re-run lp.py gen first)")
    st = txt.index(f"module {top} #(")
    hend = txt.index("\n);", st)
    hdr, body = txt[st:hend], txt[hend:]
    if lo:
        for n in ("ret2s", "ret3s"):
            hdr, k = re.subn(rf"\n\s*input wire \[520:0\] {n},?", "", hdr)
            assert k == 1, n
        hdr = hdr.replace("parameter integer MUT = 0", "parameter integer MUT = 0,\n    parameter integer SMUT = 0")
        hdr += (f",\n    input wire [{2 * SEAM_W - 1}:0] seam_bank,\n    input wire [{2 * SEAM_C - 1}:0] seam_vld")
        ins = (f"\n    // ---- SEAM landing READ ({LANE} su_pglg_half_gen.py inject): groups 2/3 returns from H_HI, +2 edges (ring in H_HI on\n"
               f"    // its r2 root), D 2 / K 1, {SEAM_C} kept 24-bit chunks, reset forest DEPTH {SEAM_DEPTH} from rst_n (= the ring's)\n"
               f"    wire [520:0] ret2s, ret3s;\n"
               f"    ot_hbm_su_pglg_seam_r #(.W({SEAM_W}),.CB({SEAM_CB}),.DEPTH({SEAM_DEPTH}),.RMUT(SMUT)) u_seam_r (.ck(ck_s), "
               f".rst_n(rst_n), .bank(seam_bank), .vld(seam_vld), .o({{ret3s, ret2s}}));")
    else:
        for n in ("ret2d", "ret3b"):
            hdr, k = re.subn(rf"\n\s*output wire \[520:0\] {n},?", "", hdr)
            assert k == 1, n
        hdr += (f",\n    output wire [{2 * SEAM_W - 1}:0] seam_bank,\n    output wire [{2 * SEAM_C - 1}:0] seam_vld")
        ins = (f"\n    // ---- SEAM landing RING ({LANE} su_pglg_half_gen.py inject): groups 2/3 returns to H_LO (read there on its S\n"
               f"    // root, +2 edges), D 2, {SEAM_C} kept 24-bit chunks on ck_r2 beside the ret registers, reset forest DEPTH {SEAM_DEPTH}\n"
               f"    wire [520:0] ret2d, ret3b;\n"
               f"    ot_hbm_su_pglg_seam_w #(.W({SEAM_W}),.CB({SEAM_CB}),.DEPTH({SEAM_DEPTH})) u_seam_w (.ck(ck_r2), .rst_n(rst_n), "
               f".i({{ret3b, ret2d}}), .bank(seam_bank), .vld(seam_vld));")
    hdr = re.sub(r",\s*,", ",", hdr)
    body = body.replace("\n);", "\n);" + ins, 1)
    note = (f"// {LANE} 10-20: KIT TOP = this lp.py output + the SEAM landing injected by tools/hbm_static/su_pglg_half_gen.py "
            f"inject (do not edit; re-run lp.py gen then inject).\n")
    f.write_text(txt[:st] + note + hdr + body)
    print(f"injected the seam landing into {f.relative_to(root)}")


def h2rg():
    """composite = the full LIGHT slice in two-half form + the stream sibling (port list = ot_hbm_su_static_pgslice_rg's
    plus the H_HI regional roots); bench vehicle for tb_hbm_su_pglg_h2 (lockstep vs pgslice_lg)"""
    return f"""`timescale 1ns/1ps
`default_nettype none
// GENERATED by tools/hbm_static/su_pglg_half_gen.py -- do not edit. {LANE} 2026-10-20 (H.STA.BLK.15.3).
// The LIGHT SU port-group slice in TWO-HALF landed form = H_LO ({LO}) + H_HI ({HI}) abutted at the seam
// (seam_bank / seam_vld wires) + the stream sibling ot_hbm_su_static_pg_stream (as ot_hbm_su_static_pgslice_rg) + the pre-tree
// sibling (PRETREE 1: ot_hbm_su_red_pretree_s on pt_ro_x / pt_ro_v = the closed hbm_su_pretree_s tile beside H_LO's E face;
// its fault joins the slice fault as u_sout's a_q -> sticky fault would). Port list = ot_hbm_su_static_pgslice_rg's + the
// H_HI roots ck_hs (S_hi), ck_r2, ck_r3 (clk_ctl = H_LO's S root).
// MUT: < 100 glue (GMUT, both halves); 101..104 lp mutants of H_LO; 111..114 lp mutants of H_HI; 121 seam read late.
module {H2RG} #(
 parameter integer QID=1,G=2,READ_RETURN=10,WRITE_RETURN=7,FETCH_EXTRA_EDGES=2,MLAT=4,ALAT=3,LEAF=1,MUT=0,MULTIRATE=1,
 parameter integer PIN_REG=1,COLLPORT=1,B39_NOOP=(QID==0),RF_LOCAL=1,RSYNC=1,RSYNC_MUT=0,STRAP=1,PRETREE=0
)(
 input wire clk_ctl, ck_r0, ck_r1, ck_hs, ck_r2, ck_r3, pg_clk,
 input wire rst_n,
 input wire [3:0] pos,
 input wire bridge_rst_n,
 input wire [1741:0] control,
 input wire [2*30-1:0] vmr_cmd,
 input wire [2*39-1:0] vmw_cmd,
 input wire [4*32-1:0] rf_bword,
 input wire [4*9-1:0] rf_bcmd,
 input wire [255:0] rf_dsec,
 input wire [11:0] red_sel,
 output wire [31:0] slice_x,
 input wire [11:0] tree_cmd,
 output wire [66:0] tree_o,
 output wire [1023:0] pt_ro_x,
 output wire [31:0] pt_ro_v,
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 output wire [1023:0] inj_q,
 input wire [1:0] dw_v,
 input wire [17:0] dw_row,
 input wire [1023:0] dw_d,
 output wire fault,
 output wire [33:0] lg_rq,
 output wire [561:0] lg_wq,
 input wire [513:0] lg_rr,
 input wire [1:0] lg_w_done,
 input wire [1:0] lg_read,lg_write,
 input wire [33:0] far_rq,
 input wire [561:0] far_wq,
 output wire [513:0] far_rr,
 output wire [1:0] far_w_done,
 output wire lg_fault
);
 localparam integer GM=(MUT<100)?MUT:0, LM=(MUT>100&&MUT<110)?MUT-100:0, HM=(MUT>110&&MUT<120)?MUT-110:0;
 wire [561:0] su_wq; wire [513:0] su_rr; wire [3:0] ij_v; wire [35:0] ij_row; wire ij_bad, pg_fault;
 wire [{2 * SEAM_W - 1}:0] seam_bank; wire [{2 * SEAM_C - 1}:0] seam_vld;
 wire [66:0] tree_o_lo; wire fault_lo;
 {HI} #(.QID(QID),.G(G),.STRAP(STRAP),.GMUT(GM),.MUT(HM)) u_hi(
  .ck_s(ck_hs),.ck_r2(ck_r2),.ck_r3(ck_r3),.rst_n(rst_n),.pos_r2(pos),.pos_r3(pos),.control(control),.vmr_cmd(vmr_cmd),
  .vmw_cmd(vmw_cmd),.rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.dw_v1(dw_v[1]),.dw_row1(dw_row[17:9]),.dw_d1(dw_d[1023:512]),
  .su_rr(su_rr),.ij_v1(ij_v[3:2]),.ij_row1(ij_row[35:18]),.seam_bank(seam_bank),.seam_vld(seam_vld));
 {LO} #(.QID(QID),.G(G),.STRAP(STRAP),.PRETREE(0),.GMUT(GM),.MUT(LM),.SMUT((MUT==121)?1:0)) u_lo(
  .ck_s(clk_ctl),.ck_r0(ck_r0),.ck_r1(ck_r1),.rst_n(rst_n),.pos(pos),.pos_r0(pos),.pos_r1(pos),.control(control),
  .vmr_cmd(vmr_cmd),.vmw_cmd(vmw_cmd),.rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.rf_dsec(rf_dsec),.red_sel(red_sel),
  .slice_x(slice_x),.tree_cmd(tree_cmd),.tree_o(tree_o_lo),.pt_ro_x(pt_ro_x),.pt_ro_v(pt_ro_v),.inj_q(inj_q),
  .dw_v0(dw_v[0]),.dw_row0(dw_row[8:0]),.dw_d0(dw_d[511:0]),.fault(fault_lo),.su_wq(su_wq),.su_rr(su_rr),.ij_v(ij_v),
  .ij_row0(ij_row[17:0]),.ij_bad(ij_bad),.pg_fault(pg_fault),.seam_bank(seam_bank),.seam_vld(seam_vld));
 // pre-tree sibling (tree_cmd issued with red_sel; one face register = u_sout's FRLY stage; sticky fault join +2)
 if(PRETREE!=0)begin:g_pt
  reg [11:0] tc_q; always @(posedge clk_ctl) tc_q<=tree_cmd;
  wire pt_fault; reg pa, pf;
  ot_hbm_su_red_pretree_s #(.LAT(6)) u_pt(.clk(clk_ctl),.rst_n(rst_n),.tree_cmd(tc_q),.ro_x(pt_ro_x),.ro_v(pt_ro_v),
   .tree_o(tree_o),.fault(pt_fault));
  always @(posedge clk_ctl) pa<=pt_fault;
  always @(posedge clk_ctl) if(!rst_n) pf<=1'b0; else if(pa) pf<=1'b1;
  assign fault=fault_lo|pf;
 end else begin:g_nopt
  assign tree_o=tree_o_lo; assign fault=fault_lo;
 end
 ot_hbm_su_static_pg_stream #(.QID(QID),.G(G),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(GM),
  .MULTIRATE(MULTIRATE),.COLLPORT(COLLPORT),.B39_NOOP(B39_NOOP),.RSYNC(RSYNC),.RSYNC_MUT(RSYNC_MUT),.STRAP(STRAP)) u_stream(
  .clk_ctl(clk_ctl),.pg_clk(pg_clk),.rst_n(rst_n),.bridge_rst_n(bridge_rst_n),.pos(pos),.vmr_cmd(vmr_cmd),.su_wq(su_wq),
  .su_rr(su_rr),.ij_v(ij_v),.ij_row(ij_row),.ij_bad(ij_bad),.pg_fault(pg_fault),.inj_rd(inj_rd),.inj_addr(inj_addr),
  .lg_rq(lg_rq),.lg_wq(lg_wq),.lg_rr(lg_rr),.lg_w_done(lg_w_done),.lg_read(lg_read),.lg_write(lg_write),.far_rq(far_rq),
  .far_wq(far_wq),.far_rr(far_rr),.far_w_done(far_w_done),.lg_fault(lg_fault));
endmodule
`default_nettype wire
"""


def write_kits(root):
    for half in ("lo", "hi"):
        inject(root, half)
    (root / f"{S}/top/{H2RG}.sv").write_text(h2rg())
    print(f"wrote {S}/top/{H2RG}.sv")


# ---------------------------------------------------------------- ref_tile kit specs (primary + parallel fallback)
BENCH = "tools/hbm_static/su_pglg_h2_vl_run.sh"
MUTANTS = [(1, "fill registered early (u_sinh, both halves)"), (2, "drain group select flipped (u_sout)"),
           (20, "outer-region relay 2 stages (both halves)"), (21, "drain delay line one short"),
           (23, "E-face relay u_erly bypassed (both halves)"), (101, "H_LO lp landing 0 bypassed (unlanded)"),
           (103, "H_LO lp pad 0 one stage short (ring pad)"), (111, "H_HI lp landing 0 bypassed (unlanded)"),
           (121, "seam read released one edge late (calendar slip)")]
PITCH = 0.2


def ranges(ports, start):
    lo, out = round(start, 3), {}
    for n, w in ports:
        hi = round(lo + w * PITCH, 3)
        out[n] = [lo, hi]
        lo = round(hi + 0.4, 3)
    return out


def span(ports):
    return sum(w for _, w in ports) * PITCH + 0.4 * len(ports)


def kit_spec(half, variant):
    lo = half == "lo"
    top = LO if lo else HI
    fb = variant == "fb"
    name = f"hbm_su_pglg_{half}_d4g" + ("_fb" if fb else "")
    inner, outer = (1, 0) if lo else (2, 3)
    dx = 43.2 if fb else 0.0                     # fallback: +43.2 channel between the column pairs and at the E edge
    w_out = round(W_OUT + 2 * dx, 3)
    h_out = H_OUT
    xc = [X_COL[0], X_COL[1], round(X_COL[2] + dx, 3), round(X_COL[3] + dx, 3)]
    Y = Y_LO if lo else Y_HI
    sfx = "0" if lo else "1"
    w_ports = [(n, wd) for n, wd in W_IN]
    if lo:
        w_ports += [("rf_dsec", 256), ("red_sel", 12), ("tree_cmd", 12)]
    w_ports += [(f"dw_v{sfx}", 1), (f"dw_row{sfx}", 9), (f"dw_d{sfx}", 512)]
    w_ports += ([("pos", 4)] if lo else []) + [(f"pos_r{outer}", 4), (f"pos_r{inner}", 4)]
    if lo:
        e_ports = [("su_wq", 562), ("su_rr", 514), ("ij_v", 4), ("ij_row0", 18), ("ij_bad", 1), ("pg_fault", 1),
                   ("slice_x", 32), ("tree_o", 67), ("fault", 1), ("inj_q", 1024), ("pt_ro_x", 1024), ("pt_ro_v", 32)]
    else:
        e_ports = [("su_rr", 514), ("ij_v1", 2), ("ij_row1", 18)]
    seam = [("seam_bank", 2 * SEAM_W), ("seam_vld", 2 * SEAM_C)]
    # W / E ranges hug the S band (H_LO: top, H_HI: bottom); seam ranges on the N (H_LO) / S (H_HI) face, same x
    ws, es = span(w_ports), span(e_ports)
    w0 = (h_out - 8.0 - ws) if lo else 8.0
    e0 = (h_out - 8.0 - es) if lo else 8.0
    pr = ranges(w_ports, w0)
    pr.update(ranges(e_ports, e0))
    sx0 = round(w_out - 120.0 - span(seam), 3)
    pr.update(ranges(seam, sx0))
    wlo = min(v[0] for k, v in pr.items() if k in dict(w_ports))
    whi = max(v[1] for k, v in pr.items() if k in dict(w_ports))
    if lo:
        pr.update({"rst_n": [round(wlo - 2.0, 3), round(wlo - 1.8, 3)], "ck_s": [round(whi + 2.0, 3), round(whi + 2.2, 3)]})
    else:
        pr.update({"rst_n": [round(whi + 2.0, 3), round(whi + 2.2, 3)], "ck_s": [round(whi + 4.0, 3), round(whi + 4.2, 3)]})
    for r in (inner, outer):
        c = round(Y[r] + REG_H / 2 - 10.8, 3)
        if wlo <= c <= whi:
            c = round(wlo - 6.0 if r == inner else wlo - 10.0, 3) if lo else round(whi + 8.0, 3)
        pr[f"ck_r{r}"] = [c, round(c + 0.2, 3)]
    children = []
    for r in (inner, outer):
        for k in range(4):
            y = round(Y[r] + k * ROW, 3)
            for c, j in ((0, 2 * k), (2, 2 * k + 1)):
                children.append(dict(view=rgf.KIND0_VIEW, count=1, inst=f"u_ln_r{r}_{j}", at=[xc[c], y], orient="R0"))
                children.append(dict(view=rgf.BANK_VIEW, count=1, inst=f"u_bk_r{r}_{j}", at=[xc[c + 1], y], orient="R0"))
    outs = {n for n, _ in e_ports if n in ("su_wq", "slice_x", "tree_o", "fault", "inj_q", "pt_ro_x", "pt_ro_v")}
    ins_core = [n for n, _ in w_ports if not n.startswith("pos_r")] + ["rst_n"] + [n for n, _ in e_ports if n not in outs]
    if lo:
        ins_core += ["seam_bank", "seam_vld"]
    ced = {"core": dict(ratio=[1, 1], ports=["ck_s"], inputs=ins_core, outputs=sorted(outs))}
    for r in (inner, outer):
        ced[f"r{r}"] = dict(ratio=[1, 1], ports=[f"ck_r{r}"], inputs=[f"pos_r{r}"],
                            outputs=(["seam_bank", "seam_vld"] if (not lo and r == inner) else []))
    benches = [dict(name="h2_lockstep", cmd=f"bash {BENCH} {{RUN}}/bench/m0 0 1200", expect="pass",
                    pass_regex="PGLG_H2 PASS checks=", pass_witness=f"{REC}/m0/bench.log", threads=8,
                    peak_ram_gb=56, needs=["verilator"])]
    for m, why in MUTANTS:
        benches.append(dict(name=f"h2_mut{m}", cmd=f"bash {BENCH} {{RUN}}/bench/m{m} {m} 300", expect="fail",
                            fail_regex="PGLG_H2 FAIL errors=", fail_witness=f"{REC}/m{m}/bench.log", threads=8,
                            peak_ram_gb=56, needs=["verilator"], why=why))
    flat_top = LOF if lo else HIF
    srcs = [f"{S}/top/lp/{top}.sv", f"{S}/top/ot_hbm_su_pgrg_parts.sv",
            f"{S}/top/ot_hbm_su_pglg_half_parts.sv", "rtl/common/landed_parent/ot_pl_land.sv",
            "rtl/common/landed_parent/ot_pl_land_physical.sv", "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
            "rtl/common/landed_parent/ot_pl_land_reset_forest.sv", "rtl/common/landed_parent/ot_pl_pad_ring.sv"]
    if lo:
        srcs += [f"{S}/reduction/ot_hbm_su_red_pretree.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv",
                 "rtl/hdc/ot_hdc_fastfp.sv"]
    other = "hi" if lo else "lo"
    return dict(
        name=name, top=top, kind="cluster", sources=srcs,
        params=dict(QID=1, G=2, STRAP=1, PRETREE=0, GMUT=0, MUT=0, **({"SMUT": 0} if lo else {})),
        clock_port="ck_s", reset_ports=["rst_n"],
        outline=dict(w=w_out, h=h_out, exact=True),
        slot_change_request=(f"{LANE} 10-20 -> HBM-DIE6 / H-D4G: LIGHT su_<q>2/3 slice = TWO landed halves stacked in one "
                             f"column (H_LO = R0|R1|S_lo below, H_HI = S_hi|R2|R3 above, abutting at the seam), each {w_out} x "
                             f"{h_out} (column {w_out} x {round(2 * h_out, 2)}, was 1235.52 x 3045.6); seam = H_LO N face / "
                             f"H_HI S face x [{pr['seam_bank'][0]}, {pr['seam_vld'][1]}] (seam_bank / seam_vld wires, landed); W "
                             "= die command side (commands fan out to both halves), E = stream tile (pg_stream) / pre-tree "
                             "sibling (pt_ro_x / pt_ro_v) / cxport side" + ("; fallback: +43.2 um channels" if fb else "")),
        children=children, macros=[],
        pins=dict(W=[n for n, _ in w_ports] + ["ck_s", "rst_n"] + [f"ck_r{r}" for r in (inner, outer)],
                  E=[n for n, _ in e_ports], **({"N": ["seam_bank", "seam_vld"]} if lo else {"S": ["seam_bank", "seam_vld"]})),
        pin_ranges=pr, pg_layer="M7", refglob="*", recipe=1, inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason=("the RTL registers every data pin: W/E face relays u_wrly / u_erly (flop-first, "
                                            "ck_s), u_sout FRLY on rf_dsec / red_sel / tree_cmd, outputs from u_sout / lp "
                                            "landing-read registers" + (", seam inputs into the landing read ot_pl_land_phys_local_r"
                                            if lo else ", seam outputs from the landing ring slots (ck_r2)") +
                                            "; pos straps are static identity straps (die constants)")),
        reset_landing=dict(enable=True, stages=2, clock="ck_s"),
        route=dict(pd=0.5, period_ps=1111.111, threads=16, peak_ram_gb=96, hold_margin_ns=0.03, io_hold_margin_ns=0.03,
                   macro_halo_um=5.4, pin_h="M4", pin_v="M3 M5", pin_balance=dict(h="M4", v="M3 M5", group_max=1)),
        clock="multiple_cts_roots", clock_ports=["ck_s", f"ck_r{inner}", f"ck_r{outer}"],
        clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=ced,
        landed_record=f"{REC}/lp/{top}_record.json",
        landed_note=(f"{LANE} 10-20: kit top {top} = lp.py landed {flat_top} (3 regions s, r{inner}, r{outer}; landings D 2 / "
                     "E 1 with 24-bit kept chunk counters + reset forest; ring pads) + the seam landing "
                     f"({'read on ck_s' if lo else 'ring on ck_r2'}, {SEAM_W} b, +2). Offsets vs ot_hbm_su_static_pgslice_lg "
                     "unchanged from the one-column parent: frames r1/r2 +3, r0/r3 +6; red_sel / tree_cmd / rf_dsec issued +10; "
                     "slice_x / pt_ro / inj_q +11; fault +12; VM write +12 serial (+16 stream). Lockstep bench "
                     f"tb_hbm_su_pglg_h2 (both halves + seam + pg_stream vs pgslice_lg) + mutants; partner kit hbm_su_pglg_{other}_d4g"
                     + ("_fb" if fb else "") + "."),
        job=dict(owner=f"Claude:{LANE}", branch="claude/hbm-pglg3-1020", tag="r1" + ("f" if fb else ""),
                 purpose=(f"HBM die d4g LIGHT SU port-group slice su_<q>2/3, {'LOWER' if lo else 'UPPER'} landed half "
                          f"(H.STA.BLK.15.3 two-half successor of hbm_su_pgslice_lg_light_d4g): 16 KIND0 r2 leaves + 16 "
                          "CLOSED bank6_clock banks, 3 region roots" + (" [fallback outline +43.2 channels]" if fb else "")),
                 record_to=f"results/rtl/ref_tile/{name}", views_to=f"physical/ref_tile/{name}/views", auto_merge=False,
                 extra_paths=[BENCH, "rtl/test/hbm_accel/generic/tb_hbm_su_pglg_h2.sv",
                              f"{S}/top/{H2RG}.sv", f"{S}/top/lp",
                              f"{S}/top/ot_hbm_su_static_pg_stream.sv", f"{S}/top/ot_hbm_su_static_pgslice_lg.sv",
                              f"{S}/top/ot_hbm_su_static_pgslice.sv", f"{S}/top/ot_hbm_su_static_pg_lg_tap.sv",
                              f"{S}/arithmetic", f"{S}/data_store", f"{S}/reduction", f"{S}/ot_hbm_su_static_vm_ports.sv",
                              f"{S}/ot_hbm_su_static_vm_bank_leaf_s.sv", f"{S}/programme/multirate_bridge.sv",
                              "rtl/lib/ot_rst_relay.sv", "rtl/common/landed_parent", "rtl/hbm_accel/generic/vm/static",
                              "rtl/hdc", "rtl/proto",
                              "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2",
                              "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2",
                              "physical/ref_tile/hbm_su_static_kind0_l4_leaf1_1015",
                              "physical/ref_tile/hbm_su_static_bank6_clock7_1015", REC,
                              "results/arch/hbm_su_f2_static_1014/arithmetic/physical/bank_clock7/hbm_su_static_bank6_clock7_1015-r12-0a5f7732e",
                              "results/arch/hbm_su_f2_static_1014/arithmetic/physical/lat4_kind0_route/hbm_su_static_kind0_l4_leaf1_1015-r2-18978c835",
                              "results/closure_loop/hbm_su_static_bank6_clock7_1015-r12-0a5f7732e",
                              "results/closure_loop/hbm_su_static_kind0_l4_leaf1_1015-r2-18978c835"],
                 benches=benches))


def write_specs(root):
    for half in ("lo", "hi"):
        for variant in ("p", "fb"):
            sp = kit_spec(half, variant)
            f = root / f"tools/ref_tile/specs_hbm_su3/{sp['name']}.json"
            f.write_text(json.dumps(sp, indent=1) + "\n")
            print(f"wrote {f.relative_to(root)}: outline {sp['outline']['w']} x {sp['outline']['h']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["rtl", "kits", "specs"])
    ap.add_argument("--root", default=str(HERE.parents[1]))
    a = ap.parse_args()
    root = Path(a.root)
    if a.what == "rtl":
        write_rtl(root)
    elif a.what == "kits":
        write_kits(root)
    else:
        write_specs(root)


if __name__ == "__main__":
    main()
