#!/usr/bin/env python3
"""QC-A0C-B5 11-06 vB2 form (COORD 12:4x): two more default-off LQR bits on top of lqr_patch.py (apply that first).

  LQR bit3 (8): one kept register stage on every lane-slice leaf's fault pins {tfault, lfault} beside the leaf, on the
            leaf's own clock (rawleaf fault_q clk->q ~432 ps + the OR-reduce wire across the die to u_me.fault_q failed
            TT by up to -123 ps).  Same form as the REGROOT 8 g_fl stage.  Faults are a status: observed +1 edge
            (PIN CYCLE on the t_out fault bit [513] only; data / valid unchanged).  Passed to the engine as LQRF.
  LQR bit4 (16): reset tree for the ROM request relay: rq_ce_s / rq_ce_n take their async reset from one kept relay
            flop per group (async assert, release one clk edge later) instead of the tile reset net (recovery
            -11.7 .. -49.6 ps through 7 hold buffers + a long buffer tree).  Reset release +1 edge (rst_n is held
            >= 64 clk, owner 10-29); no data cycle changes.
Bench-only (non-synthesis) hooks: `OT_LQR_FINJ = T (ns): a 3-ns fault pulse on slice 2 fault pin 0 in BOTH sides at
time T (fault-path coverage); `OT_LQR_MUT 4 = slice 2 fault stage drops its faults, 5 = two fault stages,
6 = group-south reset relay never released.
usage: lqr2_patch.py RTL_DIR
"""
import sys
from pathlib import Path

R = Path(sys.argv[1])

def sub(path, old, new, count=1):
    p = R / path; s = p.read_text(); n = s.count(old)
    if n != count:
        sys.exit(f"lqr2_patch: {path}: expected {count} x {old!r}, found {n}")
    p.write_text(s.replace(old, new))

W12 = "ot_qwen_rom_tile_w12_land32.sv"
MV = "ot_qwen_w12_matvec_land32.sv"

# --- bit3: engine parameter LQRF + fault stage
sub(MV, "    parameter integer NKP = 0,\n    parameter integer SPLIT_CP = 0,\n",
        "    parameter integer NKP = 0,\n"
        "    // LQRF (QC-A0C-B5 vB2, opt-in, default 0 = unchanged): leaf fault pins registered beside the leaf (+1 fault edge)\n"
        "    parameter integer LQRF = 0,\n    parameter integer SPLIT_CP = 0,\n")
sub(W12, ".MUL_LAT(MUL_LAT), .NKP(NKP)) u_me (", ".MUL_LAT(MUL_LAT), .NKP(NKP), .LQRF((LQR >> 3) & 1)) u_me (")
sub(MV, "                wire              stf_raw;\n",
        "                wire              stf_raw;\n"
        "                //: bench-only fault injection (both sides) and the LQRF mutants (lqr2_patch.py)\n"
        "                wire [G*HIER:0] fsrc;\n"
        "`ifdef OT_LQR_FINJ\n"
        "                reg finj = 1'b0;\n"
        "                initial if (g == 2) begin #(`OT_LQR_FINJ); finj = 1'b1; #3; finj = 1'b0; end\n"
        "                assign fsrc = {stf_raw, lf_raw} | {{G*HIER{1'b0}}, finj};\n"
        "`else\n"
        "                assign fsrc = {stf_raw, lf_raw};\n"
        "`endif\n"
        "`ifdef OT_LQR_MUT\n"
        "                localparam integer FMUT = `OT_LQR_MUT;\n"
        "`else\n"
        "                localparam integer FMUT = 0;\n"
        "`endif\n")
sub(MV, "                end else begin : g_fd\n                    assign lf = lf_raw;\n                    assign stf[g] = stf_raw;\n                end\n",
        "                end else if (LQRF != 0) begin : g_flq\n"
        "                    //: LQR bit3 (QC-A0C-B5 vB2): the leaf's fault pins land in a kept register beside the leaf on the\n"
        "                    //: leaf's own clock; the OR to fault_q gets its own cycle.  Faults are observed one edge later.\n"
        "                    (* keep *) reg [G*HIER:0] q;\n"
        "                    always @(posedge (CHILD_CLOCKS ? ck_lsl[g] : clk) or negedge rst_n) if (!rst_n) q <= 0; else q <= fsrc;\n"
        "                    wire [G*HIER:0] fq;\n"
        "                    if (FMUT == 5) begin : g_m5\n"
        "                        (* keep *) reg [G*HIER:0] q2;\n"
        "                        always @(posedge (CHILD_CLOCKS ? ck_lsl[g] : clk) or negedge rst_n) if (!rst_n) q2 <= 0; else q2 <= q;\n"
        "                        assign fq = q2;\n"
        "                    end else begin : g_m0\n"
        "                        assign fq = (FMUT == 4 && g == 2) ? {(G*HIER+1){1'b0}} : q;\n"
        "                    end\n"
        "                    assign lf = fq[G*HIER-1:0];\n"
        "                    assign stf[g] = fq[G*HIER];\n"
        "                end else begin : g_fd\n"
        "                    assign lf = fsrc[G*HIER-1:0];\n"
        "                    assign stf[g] = fsrc[G*HIER];\n"
        "                end\n")

# --- bit4: reset relay for the request relay ce registers
sub(W12, """        genvar a;
        for (a = 1; a <= ROM_ARELAY; a = a + 1) begin : g_arl
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin rq_ce_s[a] <= {CODE_BANKS{1'b0}}; rq_ce_n[a] <= {CODE_BANKS{1'b0}}; end
                else begin
                    rq_ce_s[a] <= (a == 1) ? ce0 : rq_ce_s[a-1];
                    rq_ce_n[a] <= (a == 1) ? ce0 : rq_ce_n[a-1];
                end
            end
""", """        genvar a;
        //: LQR bit4 (QC-A0C-B5 vB2): reset tree for the request relay: one kept relay flop per group (async assert,
        //: release one clk edge later) resets that group's rq_ce registers instead of the tile reset net.
        wire rst_ce_s, rst_ce_n;
`ifdef OT_LQR_MUT
        localparam integer LQM4 = `OT_LQR_MUT;
`else
        localparam integer LQM4 = 0;
`endif
        if ((LQR & 16) != 0) begin : g_lqrr
            (* keep *) reg rr_s, rr_n;
            always @(posedge clk or negedge rst_n) if (!rst_n) begin rr_s <= 1'b0; rr_n <= 1'b0; end
                else begin rr_s <= (LQM4 == 6) ? 1'b0 : 1'b1; rr_n <= 1'b1; end
            assign rst_ce_s = rr_s; assign rst_ce_n = rr_n;
        end else begin : g_lqrr0
            assign rst_ce_s = rst_n; assign rst_ce_n = rst_n;
        end
        for (a = 1; a <= ROM_ARELAY; a = a + 1) begin : g_arl
            always @(posedge clk or negedge rst_ce_s) begin
                if (!rst_ce_s) rq_ce_s[a] <= {CODE_BANKS{1'b0}};
                else rq_ce_s[a] <= (a == 1) ? ce0 : rq_ce_s[a-1];
            end
            always @(posedge clk or negedge rst_ce_n) begin
                if (!rst_ce_n) rq_ce_n[a] <= {CODE_BANKS{1'b0}};
                else rq_ce_n[a] <= (a == 1) ? ce0 : rq_ce_n[a-1];
            end
""")
sub(W12, "(RPH != 3 || ROM_PIPE == 0 || LQR > 7)", "(RPH != 3 || ROM_PIPE == 0 || LQR > 31)")
sub(W12, "    // bit1 per-leaf request register (+1 ROM cycle), bit2 node t_d register (+1 t_out pin cycle)\n",
         "    // bit1 per-leaf request register (+1 ROM cycle), bit2 node t_d register (+1 t_out pin cycle), bit3 leaf fault\n"
         "    // pin register (+1 fault edge), bit4 request-relay reset tree (lqr2_patch.py)\n", 2)
print(f"lqr2_patch: {R} patched (bits 3, 4)")
