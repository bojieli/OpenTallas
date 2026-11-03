#!/usr/bin/env python3
"""DIE-QC-66/CORES-NK 11-03: opt-in NKP (default 0 = unchanged elaboration) logic-depth cuts in ot_qwen_w12_matvec_part
for the A0 NK tile (REGROOT 3, FAST_ISSUE 1, KV_PREP 4, HIER 2 / HIER_HARD 1 / XTX 2).  Bitmask:
  bit0 (1): K-limit prep: the masked chunk index c32 and the pad mask (1<<S)-1 registered before the kdif compare /
            subtract / add, and (1<<S)-1 registered before the kpad_a add.  kdif/klim/kpad_a +1 edge inside the
            KV_PREP window (klim ready edge 3 <= KV_PREP 4; k_r ready edge 4 < first K boundary): 0 visible cycles.
  bit1 (2): the REGROOT 8 rung-0 form at REGROOT < 8: XTX rung 0 captures the RAW s2 x word + round/mask selects, each
            leaf's own BF16 round + mask sits between rung 0 and rung 1 (exact identity, same edges): 0 cycles.
  bit2 (4): round-step products: shifter rows -> carry-save pair REGISTERED -> prefix add into tsh[0] -> tsg_a/otsg_a (the
            ksum then sees one non-zero row).  tstep_r / ot_step ready edge 4 (was 3) < first round boundary
            (edge >= IL = 8): 0 visible cycles.
Generate constructs are only added as new branches of existing if-chains or at the END of a scope (no genblk renumber).
usage: nkp_patch.py RTLDIR   (patches in place; exact anchors, fail-closed)"""
import sys
from pathlib import Path

def rep(t, a, b, n=1):
    assert t.count(a) == n, (a[:90], t.count(a)); return t.replace(a, b)

NKPDOC = ("    // NKP (DIE-QC-66 11-03, opt-in, default 0 = unchanged): ot_qwen_w12_matvec_part logic-depth cuts (bit0 K-limit\n"
          "    // prep, bit1 raw XTX rung 0 + per-leaf round, bit2 round-step sum); 0 visible cycles (see the engine)\n")

def matvec(t):
    t = rep(t, "module ot_qwen_w12_matvec_part #(\n",
            "module ot_qwen_w12_matvec_part #(\n" + NKPDOC + "    parameter integer NKP = 0,\n")
    # ---- bit0 kpad_a / bit2 round-step sum: a new branch g_terms7p of the g_terms8 / g_terms7 chain ----
    a = t.index("    end else begin : g_terms7\n")
    b = t.index("    wire [AW+PRW-1:0] tsum, osum;\n")
    blk = t[a:b]
    assert blk.endswith("        end\n    end\n"), blk[-40:]
    body = blk[len("    end else begin : g_terms7\n"):-len("    end\n")]
    kp = "            kpad_a <= {1'b0, ktc[0 +: NW]} + ((1 << spc[4*((REGROOT >= 7) ? 35 : 8) +: 4]) - 1);\n"
    assert body.count(kp) == 1
    def expr(tag):
        i = body.index("                %s[b] <= " % tag) + len("                %s[b] <= " % tag)
        j = body.index("& SH_Q3);\n", i) + len("& SH_Q3)")
        return body[i:j]
    te, oe = expr("tsh"), expr("osh")
    MSK = "((1 << spc[4*((REGROOT >= 7) ? 35 : 8) +: 4]) - 1)"
    pbody = ("        //: NKP (DIE-QC-66 11-03): the g_terms7 shifter terms (same expressions) as combinational rows, then\n"
             "        //: bit0: (1 << S) - 1 registered one edge before the kpad_a add (kpad_a edge 2, kc_a 3, k_r 4 < the\n"
             "        //:       first K boundary at edge >= KV_PREP + IL).\n"
             "        //: bit2: rows -> carry-save pair REGISTERED (edge 1) -> prefix add into tsh[0] / osh[0] (edge 2; tsh[1..]\n"
             "        //:       = 0), so u_ts / u_os see one non-zero row (tsum = tsh[0], no logic): tsg_a edge 3, tstep_r /\n"
             "        //:       ot_step edge 4 (was 3), first read at the first round boundary (edge >= IL).  Values unchanged.\n"
             "        reg [AW+PRW-1:0] trow [0:NB_GT-1];\n"
             "        reg [AW+PRW-1:0] orow [0:NB_GT-1];\n"
             "        always @(*) begin : p_rows_nkp\n"
             "            integer b;\n"
             "            for (b = 0; b < NB_GT; b = b + 1) begin\n"
             "                trow[b] = " + te + ";\n"
             "                orow[b] = " + oe + ";\n"
             "            end\n"
             "        end\n"
             "        always @(posedge clk) pr_a <= GT >> spc[4*8 +: 4];\n"
             "        if ((NKP & 1) != 0) begin : g_kp1\n"
             "            reg [NW:0] kpm_q;\n"
             "            always @(posedge clk) begin\n"
             "                kpm_q <= " + MSK + ";\n"
             "                kpad_a <= {1'b0, ktc[0 +: NW]} + kpm_q;\n"
             "            end\n"
             "        end else begin : g_kp0\n"
             "            always @(posedge clk) kpad_a <= {1'b0, ktc[0 +: NW]} + " + MSK + ";\n"
             "        end\n"
             "        if ((NKP & 4) != 0) begin : g_ts1\n"
             "            wire [NB_GT*(AW+PRW)-1:0] trf, orf;\n"
             "            genvar t7;\n"
             "            for (t7 = 0; t7 < NB_GT; t7 = t7 + 1) begin : g_rf\n"
             "                assign trf[t7*(AW+PRW) +: AW+PRW] = trow[t7];\n"
             "                assign orf[t7*(AW+PRW) +: AW+PRW] = orow[t7];\n"
             "            end\n"
             "            wire [AW+PRW-1:0] ts_s, ts_c, os_s, os_c, ts_a, os_a;\n"
             "            reg  [AW+PRW-1:0] ts_sq, ts_cq, os_sq, os_cq;\n"
             "            ot_qwen_w12_csa_tree #(.W(AW+PRW), .N(NB_GT)) u_tc (.rows(trf), .s(ts_s), .c(ts_c));\n"
             "            ot_qwen_w12_csa_tree #(.W(AW+PRW), .N(NB_GT)) u_oc (.rows(orf), .s(os_s), .c(os_c));\n"
             "            ot_qwen_w12_kadd #(.W(AW+PRW)) u_tk (.a(ts_sq), .b(ts_cq), .s(ts_a));\n"
             "            ot_qwen_w12_kadd #(.W(AW+PRW)) u_ok (.a(os_sq), .b(os_cq), .s(os_a));\n"
             "            always @(posedge clk) begin : p_sum_nkp\n"
             "                integer b2;\n"
             "                ts_sq <= ts_s; ts_cq <= ts_c; os_sq <= os_s; os_cq <= os_c;\n"
             "                for (b2 = 0; b2 < NB_GT; b2 = b2 + 1) begin\n"
             "                    tsh[b2] <= (b2 == 0) ? ts_a : {(AW+PRW){1'b0}};\n"
             "                    osh[b2] <= (b2 == 0) ? os_a : {(AW+PRW){1'b0}};\n"
             "                end\n"
             "            end\n"
             "        end else begin : g_ts0\n"
             "            always @(posedge clk) begin : p_terms_nkp\n"
             "                integer b2;\n"
             "                for (b2 = 0; b2 < NB_GT; b2 = b2 + 1) begin tsh[b2] <= trow[b2]; osh[b2] <= orow[b2]; end\n"
             "            end\n"
             "        end\n")
    t = t[:a] + ("    end else if ((NKP & 5) == 0) begin : g_terms7\n" + body +
                 "    end else begin : g_terms7p\n" + pbody + "    end\n") + t[b:]
    # ---- bit0: K-limit kdif ----
    k7_old = ("            end else begin : g_k7\n"
              "            wire [31:0] c32 = (gb + gk) & ((1 << sa) - 1);\n"
              "            always @(posedge clk) begin\n"
              "                kdif[gk] <= ({{(32-NW){1'b0}}, kt} > c32) ? (kt - c32[NW:0] + ((1 << sd) - 1)) : {(NW+1){1'b0}};\n"
              "                klim[gk] <= kdif[gk] >> sb;\n"
              "                e_gm[gk] <= (((gb + gk) >> sc) < (GT >> sc)) && (!wsc[2] || ({1'b0, k} < klim[gk]));\n"
              "            end\n"
              "            end\n")
    k7_new = k7_old.replace("            end else begin : g_k7\n", "            end else if ((NKP & 1) == 0) begin : g_k7\n")[:-len("            end\n")] + (
              "            end else begin : g_k7p\n"
              "            //: NKP bit0: the masked chunk index c32 and the pad mask (1 << S) - 1 registered (edge 1), then the\n"
              "            //: compare / subtract / add (kdif edge 2) and the shift (klim edge 3 <= KV_PREP: the first KV element\n"
              "            //: reads klim at edge KV_PREP + 1).  Values unchanged (kdif is NW+1 bits: the mask's low bits suffice).\n"
              "            reg [31:0] c32_q;\n"
              "            reg [NW:0] kdm_q;\n"
              "            always @(posedge clk) begin\n"
              "                c32_q <= (gb + gk) & ((1 << sa) - 1);\n"
              "                kdm_q <= (1 << sd) - 1;\n"
              "            end\n"
              "            always @(posedge clk) begin\n"
              "                kdif[gk] <= ({{(32-NW){1'b0}}, kt} > c32_q) ? (kt - c32_q[NW:0] + kdm_q) : {(NW+1){1'b0}};\n"
              "                klim[gk] <= kdif[gk] >> sb;\n"
              "                e_gm[gk] <= (((gb + gk) >> sc) < (GT >> sc)) && (!wsc[2] || ({1'b0, k} < klim[gk]));\n"
              "            end\n"
              "            end\n")
    t = rep(t, k7_old, k7_new)
    # ---- bit1: REGROOT 8 rung-0 form ----
    t = rep(t, "if (FAST_ISSUE != 0 && !(REGROOT >= 8 && HIER > 0 && HIER_HARD != 0 && XTX >= 2)) begin : g_keep_round",
               "if (FAST_ISSUE != 0 && !((REGROOT >= 8 || (NKP & 2) != 0) && HIER > 0 && HIER_HARD != 0 && XTX >= 2)) begin : g_keep_round")
    t = rep(t, "localparam integer XW0 = (REGROOT >= 8 && XTX >= 2) ?", "localparam integer XW0 = ((REGROOT >= 8 || (NKP & 2) != 0) && XTX >= 2) ?")
    t = rep(t, "if (REGROOT >= 8 && XTX >= 2) begin : g_raw", "if ((REGROOT >= 8 || (NKP & 2) != 0) && XTX >= 2) begin : g_raw")
    t = rep(t, "if (REGROOT >= 8 && XTX >= 2) begin : g_lx", "if ((REGROOT >= 8 || (NKP & 2) != 0) && XTX >= 2) begin : g_lx")
    # ---- applicability check, last construct of the module ----
    idle = ("    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) idle <= 1'b1;\n"
            "        else idle <= idle_c && !(go && ready);\n    end\nendmodule\n")
    t = rep(t, idle, idle[:-len("endmodule\n")] +
            "    //: NKP (DIE-QC-66 11-03): the cuts' timing arguments hold only in this form (last construct: no renumbering)\n"
            "    generate if (NKP != 0) begin : g_nkp_chk\n"
            "        initial if (FAST_ISSUE == 0 || !LANES || REGROOT >= 8 || KV_PREP < 3 || IL < 6 || NKP > 7 ||\n"
            "                    ((NKP & 2) != 0 && !(HIER > 0 && HIER_HARD != 0 && XTX >= 2 && L9 == 0)))\n"
            "            $fatal(1, \"ot_qwen_w12_matvec_part NKP needs FAST_ISSUE, LANES, REGROOT < 8, KV_PREP >= 3, IL >= 6 (bit1: HIER_HARD, XTX >= 2, no L9)\");\n"
            "    end endgenerate\nendmodule\n")
    return t

def plumb_hdr(t, mod, last_old, last_new):
    a = t.index(f"module {mod} #(")
    i = t.index(last_old, a); assert i - a < 20000, mod
    return t[:i] + last_new + t[i + len(last_old):]

def patch(d):
    d = Path(d)
    f = d / "ot_qwen_w12_matvec_land32.sv"; f.write_text(matvec(f.read_text()))
    f = d / "ot_qwen_rom_tile_w12_land32.sv"; t = f.read_text()
    t = plumb_hdr(t, "ot_qwen_rom_tile_logic_w12", "    parameter integer IRCK = 0\n) (",
                  "    parameter integer IRCK = 0,\n" + NKPDOC + "    parameter integer NKP = 0\n) (")
    t = plumb_hdr(t, "ot_qwen_rom_tile_w12", "    parameter integer IRCK = 0         // DIE-QC-58B: ot_qwen_rom_tile_logic_w12 IRCK (IREG stage on ck_ireg)\n) (",
                  "    parameter integer IRCK = 0,        // DIE-QC-58B: ot_qwen_rom_tile_logic_w12 IRCK (IREG stage on ck_ireg)\n" + NKPDOC + "    parameter integer NKP = 0\n) (")
    t = rep(t, ".MUL_LAT(MUL_LAT)) u_me (", ".MUL_LAT(MUL_LAT), .NKP(NKP)) u_me (")
    t = rep(t, ".IRCK(IRCK)) u_logic (", ".IRCK(IRCK), .NKP(NKP)) u_logic (")
    f.write_text(t)
    f = d / "ot_qwen_rom_tile_nk.sv"; t = f.read_text()
    t = plumb_hdr(t, "ot_qwen_rom_tile_nk", "    parameter integer IRCK = 0            // DIE-QC-58B (opt-in): ot_qwen_rom_tile_w12 IRCK, IREG stage on ck_ireg\n) (",
                  "    parameter integer IRCK = 0,           // DIE-QC-58B (opt-in): ot_qwen_rom_tile_w12 IRCK, IREG stage on ck_ireg\n" + NKPDOC + "    parameter integer NKP = 0\n) (")
    t = rep(t, ".IRCK(IRCK)) u_tile (", ".IRCK(IRCK), .NKP(NKP)) u_tile (")
    f.write_text(t)
    f = d / "qfd_tile_nk_rp2_45.sv"; t = f.read_text()
    t = plumb_hdr(t, "qfd_tile_nk_rp2_45", "    parameter integer IRCK = 0\n) (", "    parameter integer IRCK = 0,\n" + NKPDOC + "    parameter integer NKP = 0\n) (")
    t = rep(t, ".IRCK(IRCK)) u_tile (", ".IRCK(IRCK), .NKP(NKP)) u_tile (")
    f.write_text(t)
    f = d / "qfd_tile_nk_a0c.sv"; t = f.read_text()
    t = rep(t, "    parameter integer ICG_K_NODE = 0\n`ifndef SYNTHESIS",
            "    parameter integer ICG_K_NODE = 0,\n" + NKPDOC + "    parameter integer NKP = 0\n`ifndef SYNTHESIS")
    t = rep(t, ".IRCK((ICG == 1 && ICG_IREG != 0) ? 1 : 0)) u_g (", ".IRCK((ICG == 1 && ICG_IREG != 0) ? 1 : 0),.NKP(NKP)) u_g (", n=2)
    f.write_text(t)
    print("NKP_PATCH_OK", d)

if __name__ == "__main__":
    patch(sys.argv[1])
