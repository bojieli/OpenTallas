#!/usr/bin/env python3
"""DIE-HEAD-76 hd_lep0N_vC (Codex REMEDY Variant B, form D2): derive the split LEP sources from the committed head
LEP master rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv, which stays byte-identical.

  ot_s81hd_lep_core_nr_txext  = ot_s81hd_lep_core_nr with the four per-lane TX landing FIFOs (g_tx[t]) cut out: the
                                core exports, per lane, exactly the nets the g_tx body read (lane reset rt, the lane's
                                TX reset leaves, the push copies psh / push_group, the write word {sq, frame half})
                                and imports the lane overflow flag ovf; lo*_v / lo*_d are driven 0 and lo*_r unread.
  ot_s81hd_lep_idx_nr_txext   = ot_s81hd_lep_idx_nr over the txext core, passing the tx_* ports through.
  ot_s81hd_lep_txlane         = the g_tx body VERBATIM for one lane T (loop t = T..T), so every register keeps its
                                g_tx[T].* name; the core nets it read are rebuilt from the exported ports.

0 added cycles, no data/control/credit change: the composition hub + 4 regions (rtl/dsrom_sys/s81_head/
ot_s81hd_lep0N_split.sv) is checked equal to ot_s81hd_lep0N_noidx_core by tools/s81_head/head_lep_split_equiv.sh.

    python3 -I tools/s81_head/head_lep_split_sources.py [--check]
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv"
OUT = ROOT / "rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_split_nr.sv"

SEG_START = "    wire [NL-1:0] ovf;\n    wire [3:0] lo_v; wire [3:0] lo_r = {lo3_r, lo2_r, lo1_r, lo0_r};\n"
SEG_END = "    assign lo0_v = lo_v[0]; assign lo0_d = lo_d[H:0];\n"
LOOP = "    generate for (t = 0; t < NL; t = t + 1) begin : g_tx\n"
TX_PORTS = """,
    // DIE-HEAD-76 TX_EXT: the per-lane TX landing FIFOs live in ot_s81hd_lep_txlane (one per pair region)
    output wire [3:0]      tx_rt,      // lane reset leaf (rr[t%2] / rr[4+NRX_RST+t-2])
    output wire [4*TX_RST_STRIDE-1:0] tx_rst,  // the lane's TX reset leaves rr[TX_RSTBASE+t*TX_RST_STRIDE +: TX_RST_STRIDE]
    output wire [3:0]      tx_psh,     // push of the lane (push_lane copy)
    output wire [4*TX_NA-1:0] tx_pg,   // push copies of the lane's address groups (push_group[2c+t/2])
    output wire [4*553-1:0] tx_wd,     // write word {sq[t/2], frame half}
    input  wire [3:0]      tx_ovf      // lane TX overflow (sticky) -> fault
"""


def module(text, name):
    m = re.search(r"^module\s+" + re.escape(name) + r"\b.*?^endmodule\b", text, re.M | re.S)
    if not m:
        raise ValueError("missing module " + name)
    return m.group()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("source pattern changed: " + old[:80])
    return text.replace(old, new)


def derive(src):
    core = module(src, "ot_s81hd_lep_core_nr")
    idx = module(src, "ot_s81hd_lep_idx_nr")
    i0, i1 = core.index(SEG_START), core.index(SEG_END)
    seg = core[i0:i1]
    if seg.count(LOOP) != 1:
        raise ValueError("g_tx loop pattern changed")
    head = core[:core.index(") (\n")]                   # parameter header
    params = head[head.index("#(") + 2:].rstrip()
    lp0 = core.index("    localparam integer H = 552;")
    lp1 = core.index("    wire [3+NRX_RST+NXR:0] rr;")
    localparams = core[lp0:lp1]
    # TX_RST_STRIDE / TX_NA are used in the port list: declare them as (derived) parameters there is not possible,
    # so the txext port widths use the head constants and an elaboration check pins them.
    # ---- txext core
    ext_seg = (SEG_START
               + "    wire [4*(H+1)-1:0] lo_d;\n    localparam integer CW = $clog2(CRED + 1);\n    genvar t;\n" + LOOP
               + "        assign tx_rt[t] = (NXR != 0 && t >= 2) ? rr[4+NRX_RST+t-2] : rr[t % 2];\n"
               + "        assign tx_rst[t*TX_RST_STRIDE+:TX_RST_STRIDE] = rr[TX_RSTBASE+t*TX_RST_STRIDE+:TX_RST_STRIDE];\n"
               + "        assign tx_psh[t] = (SAFE_FIFO)?push_lane[2*t+t/2]:pp[t / 2];\n"
               + "        for(genvar c=0;c<TX_NA;c=c+1) begin:g_pg assign tx_pg[t*TX_NA+c] = push_group[2*c+t/2]; end\n"
               + "        assign tx_wd[t*(H+1)+:H+1] = {sq[t/2],(t%2==0)?hf0:hf1};\n"
               + "        assign ovf[t] = tx_ovf[t];\n"
               + "        assign lo_v[t] = 1'b0; assign lo_d[t*(H+1)+:H+1] = '0;\n"
               + "    end\n    if (NL == 2) begin : g_txnb\n        assign lo_v[3:2] = 2'b00; assign lo_d[4*(H+1)-1:2*(H+1)] = '0;\n"
               + "    end endgenerate\n"
               + "`ifndef SYNTHESIS\n    initial if(!(SAFE_FIFO && SRAM!=0 && NL==4 && H==552 && TX_RST_STRIDE==" + "TXS_PORT && TX_NA==TXNA_PORT))\n"
               + "        $fatal(1, \"TX_EXT supports the head SAFE_FIFO/SRAM/AB form only\");\n`endif\n")
    ext = core[:i0] + ext_seg + core[i1:]
    ext = once(ext, "module ot_s81hd_lep_core_nr", "module ot_s81hd_lep_core_nr_txext")
    ext = once(ext, "    output wire [512:0]    ql\n);", "    output wire [512:0]    ql" + TX_PORTS.replace(
        "4*TX_RST_STRIDE", "4*TXS_PORT").replace("4*TX_NA", "4*TXNA_PORT") + ");")
    ext = once(ext, "    parameter integer IN_PIPE = 0 ", "    parameter integer TXS_PORT = 106, parameter integer TXNA_PORT = 18,\n    parameter integer IN_PIPE = 0 ")
    # ---- txext idx wrapper
    xi = once(idx, "module ot_s81hd_lep_idx_nr", "module ot_s81hd_lep_idx_nr_txext")
    xi = once(xi, "    output wire [275:0]    cb\n);", "    output wire [275:0]    cb" + TX_PORTS.replace(
        "4*TX_RST_STRIDE", "4*TXS_PORT").replace("4*TX_NA", "4*TXNA_PORT") + ");")
    xi = once(xi, "parameter integer IDX_EN = 1\n", "parameter integer IDX_EN = 1,\n    parameter integer TXS_PORT = 106, parameter integer TXNA_PORT = 18\n")
    xi = once(xi, "    ot_s81hd_lep_core_nr #(", "    ot_s81hd_lep_core_nr_txext #(.TXS_PORT(TXS_PORT), .TXNA_PORT(TXNA_PORT), ")
    xi = once(xi, ".tl(tl), .ca(ca), .cb(cb));",
              ".tl(tl), .ca(ca), .cb(cb),\n        .tx_rt(tx_rt), .tx_rst(tx_rst), .tx_psh(tx_psh), .tx_pg(tx_pg), .tx_wd(tx_wd), .tx_ovf(tx_ovf));")
    # ---- txlane: the g_tx body verbatim for lane T
    body = once(seg, LOOP, "    generate for (t = T; t < T + 1; t = t + 1) begin : g_tx\n")
    body = once(body, "wire [3:0] lo_r = {lo3_r, lo2_r, lo1_r, lo0_r};", "wire [3:0] lo_r = {4{lo_r_i}};")
    lane = ("module ot_s81hd_lep_txlane #(\n    parameter integer T = 0, parameter integer TX_RST_STRIDE_P = 106, parameter integer TX_NA_P = 18,\n" + params + "\n) (\n"
            "    input  wire clk,\n"
            "    input  wire rt_i,                       // lane reset leaf (core tx_rt[T])\n"
            "    input  wire [TX_RST_STRIDE_P-1:0] rst_i, // lane TX reset leaves (core tx_rst[T])\n"
            "    input  wire psh_i,                      // core tx_psh[T]\n"
            "    input  wire [TX_NA_P-1:0] pg_i,         // core tx_pg[T]\n"
            "    input  wire [552:0] wd_i,               // core tx_wd[T]\n"
            "    input  wire lo_r_i,                     // lane credit pulse (pair k_lo_r)\n"
            "    output wire lo_v_o, output wire [552:0] lo_d_o, output wire ovf_o\n);\n"
            + localparams
            + "    localparam integer RRW = 4+NRX_RST+NXR;\n"
            "    localparam integer RT_IDX = (NXR != 0 && T >= 2) ? 4+NRX_RST+T-2 : T % 2;\n"
            "    wire [RRW-1:0] rr = ({{(RRW-1){1'b0}}, rt_i} << RT_IDX)\n"
            "                      | ({{(RRW-TX_RST_STRIDE){1'b0}}, rst_i} << (TX_RSTBASE+T*TX_RST_STRIDE));\n"
            "    wire [2*NL-1:0] push_lane = {{(2*NL-1){1'b0}}, psh_i} << (2*T+T/2);\n"
            "    wire [1:0] pp = {1'b0, psh_i} << (T/2);\n"
            "    wire [2*PUSH_GROUPS-1:0] push_group;\n"
            "    genvar pgi;\n"
            "    generate for (pgi = 0; pgi < PUSH_GROUPS; pgi = pgi + 1) begin : g_pgi\n"
            "        assign push_group[2*pgi+:2] = (T/2 == 0) ? {1'b0, pg_i[pgi]} : {pg_i[pgi], 1'b0};\n"
            "    end endgenerate\n"
            "    wire [1:0] sq = {2{wd_i[H]}};\n"
            "    wire [H-1:0] hf0 = wd_i[H-1:0], hf1 = wd_i[H-1:0];\n"
            + body
            + "    assign lo_v_o = lo_v[T]; assign lo_d_o = lo_d[T*(H+1)+:H+1]; assign ovf_o = ovf[T];\n"
            "`ifndef SYNTHESIS\n    initial if(TX_RST_STRIDE != TX_RST_STRIDE_P || TX_NA != TX_NA_P) $fatal(1, \"txlane port widths\");\n`endif\n"
            "endmodule\n")
    hdr = ("`timescale 1ns/1ps\n// Generated by tools/s81_head/head_lep_split_sources.py from "
           "rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv; do not edit.\n")
    return hdr + ext + "\n\n" + xi + "\n\n" + lane


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = derive(SRC.read_text())
    if a.check:
        if OUT.read_text() != text:
            raise SystemExit("STALE head LEP split source")
    else:
        OUT.write_text(text)
    print("HEAD_LEP_SPLIT_SOURCES PASS; master unchanged; added cycles 0")


if __name__ == "__main__":
    main()
