#!/usr/bin/env python3
"""RST-FAN-1 (HEAD-CROSSING-1119, OWNER r13 event 11-20): opt-in mapped reset tree for the head no-repair LEP master.

The W-trees (s81_head r13 .. W8b) carry this edit of rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv as a hand patch
on the lane branch; head_lep_nr_sources.py never emitted it, so a regeneration dropped the RTG / rst_nr form that the
hd_lep0N plan binds (RTG 47, RTR 4).  This hook makes the generator emit exactly those lines (HEAD-ALLFIX 11-25).
  RTG 0 (default): ot_rst_relay_tree3 as before, rxvb_q on rr[1] as before, rst_nr unread -> every flop and net unchanged.
  RTG > 0: ot_rst_relay_tree3m (rtl/lib/ot_rst_relay_tree3m.sv) root copies + free group boundaries, same 3 release edges;
           rxvb_q[0] / [1] each on their own local.  0 added cycles.
Usage: head_lep_rst_fan.py IN OUT  (fails closed if any anchor is missing or found more than expected)."""
import sys


def sub(text, old, new, n=1):
    c = text.count(old)
    if c != n:
        raise SystemExit(f"RST-FAN-1 anchor count {c} != {n}: {old[:80]!r}")
    return text.replace(old, new)


RXH_DOC = "// HEAD-PLAN-R4 NF15f: RX head rank before ri / ml_wd (see g_rxh); 0 = none\n"
IDX_TAIL = ", parameter [15:0] TXI = 16'h0000, parameter integer RXH = 0"


def apply(src):
    if "RST-FAN-1" in src:
        raise SystemExit("RST-FAN-1 already applied")
    # 1. core parameters + the per-root-copy reset input
    src = sub(src,
      "    parameter integer RXH = 0          " + RXH_DOC + ") (\n"
      "    input  wire            clk,\n"
      "    input  wire            rst_n,\n"
      "    // slice outward line port\n",
      "    parameter integer RXH = 0,         " + RXH_DOC +
      "    parameter integer RTG = 0,         // RST-FAN-1: reset tree groups (0 = ot_rst_relay_tree3; >0 = ot_rst_relay_tree3m)\n"
      "    parameter integer RTR = 1,         // RST-FAN-1: root copies of the mapped tree (RTG > 0)\n"
      "    parameter [1023:0] RTGS = 1024'd0, // RST-FAN-1: first local of group g at [16g+:16] (RTG > 0)\n"
      "    parameter [255:0]  RTRM = 256'd0   // RST-FAN-1: root copy of group g at [4g+:4] (RTG > 0)\n"
      ") (\n"
      "    input  wire            clk,\n"
      "    input  wire            rst_n,\n"
      "    input  wire [15:0]     rst_nr,     // RST-FAN-1d: per-root-copy resets of the mapped tree (RTG > 0; else unread)\n"
      "    // slice outward line port\n")
    # 2. the reset tree
    src = sub(src,
      "    wire [3+NRX_RST+NXR:0] rr;\n"
      "    generate if(SAFE_FIFO) begin:g_reset_balanced\n"
      "      ot_rst_relay_tree3 #(.REGIONS(4+NRX_RST+NXR)) u_rstr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));\n",
      "    localparam integer NRV=(SAFE_FIFO && NL==4 && RTG>0)?2:0;   // RST-FAN-1: rxvb_q[0] / [1] own locals (mapped tree only)\n"
      "    wire [3+NRX_RST+NXR+NRV:0] rr;\n"
      "    generate if(SAFE_FIFO && RTG==0) begin:g_reset_balanced\n"
      "      ot_rst_relay_tree3 #(.REGIONS(4+NRX_RST+NXR)) u_rstr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));\n"
      "    end else if(SAFE_FIFO) begin:g_reset_mapped   // RST-FAN-1: root copies + free group boundaries, same 3 edges\n"
      "      ot_rst_relay_tree3m #(.REGIONS(4+NRX_RST+NXR+NRV),.GROUPS(RTG),.ROOTS(RTR),.GS(RTGS[16*RTG-1:0]),.RM(RTRM[4*RTG-1:0]),.RIN(1))\n"
      "        u_rstr(.clk(clk),.rst_n_in(rst_n),.rst_n_rt(rst_nr[RTR-1:0]),.rst_n(rr));\n")
    # 3. rxvb_q: one local per lane on the mapped tree
    src = sub(src,
      "        always @(posedge clk or negedge rnb) if (!rnb) rxvb_q <= 2'b00; else rxvb_q <= 2'b11;\n",
      "        if (NRV == 0) begin : g_rxvb_r1\n"
      "            always @(posedge clk or negedge rnb) if (!rnb) rxvb_q <= 2'b00; else rxvb_q <= 2'b11;\n"
      "        end else begin : g_rxvb_own   // RST-FAN-1: one local per lane (rr[4+NRX_RST+NXR+b]), same release edge\n"
      "            wire rnb0 = rr[4+NRX_RST+NXR], rnb1 = rr[5+NRX_RST+NXR];\n"
      "            always @(posedge clk or negedge rnb0) if (!rnb0) rxvb_q[0] <= 1'b0; else rxvb_q[0] <= 1'b1;\n"
      "            always @(posedge clk or negedge rnb1) if (!rnb1) rxvb_q[1] <= 1'b0; else rxvb_q[1] <= 1'b1;\n"
      "        end\n")
    # 4. the idx wrapper passes the knobs and rst_nr through
    src = sub(src,
      IDX_TAIL + "\n) (\n    input  wire            clk,\n    input  wire            rst_n,\n",
      IDX_TAIL + ",\n    parameter integer RTG = 0, parameter integer RTR = 1, parameter [1023:0] RTGS = 1024'd0, parameter [255:0] RTRM = 256'd0\n"
      ") (\n    input  wire            clk,\n    input  wire            rst_n,\n"
      "    input  wire [15:0]     rst_nr,     // RST-FAN-1d: per-root-copy resets of the mapped tree (RTG > 0; else unread)\n")
    src = sub(src,
      ".TXI(TXI), .RXH(RXH)) u (   // L5B-LEPMU 10-21: native32 / face-stage opt-ins exposed (defaults 0 = unchanged)\n"
      "        .clk(clk), .rst_n(rst_n), .ro(ro),",
      ".TXI(TXI), .RXH(RXH),\n"
      "        .RTG(RTG), .RTR(RTR), .RTGS(RTGS), .RTRM(RTRM)) u (   // L5B-LEPMU 10-21: native32 / face-stage opt-ins exposed (defaults 0 = unchanged)\n"
      "        .clk(clk), .rst_n(rst_n), .rst_nr(rst_nr), .ro(ro),")
    return src


if __name__ == "__main__":
    open(sys.argv[2], "w").write(apply(open(sys.argv[1]).read()))
    print("RST-FAN-1 applied")
