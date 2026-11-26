#!/usr/bin/env python3
"""LEP-PUSHDUP-3 (HEAD-ALLFIX 11-25, Fable C9 / rc140 residual; COORD H9 generator knob): opt-in TXP registered TX pre-stage.

hd_lep0N ep3 CTS -112.9 ps: g_mtx.wn -> stamp OR tree -> tag mux -> rg3 g_txi.g_s[0] was one 833 ps cycle over ~700 um.
TXP[t] puts one kept ot_s81hd_lep_txi_st (word {sq, half} + push + push-group copies, pushes cleared on the lane reset leaf)
on TX lane t's ingress, ahead of the TXI stages, so lane t's FIFO sees the same write sequence one edge later.  The core
parameter defaults to 4'b0000 (no stage, every net unchanged); the knob value is the default of the head wrapper
(ot_s81hd_lep_idx_nr / ot_s81hd_lep_idx_nr_txext), W8 = 4'b1000 (lane 3, rg3, E piece) with the plan TXI 16'h3222 ->
16'h2222, i.e. lane 3 keeps 3 TX ingress stages in total (yosys seq equivalence vs TXI 3222: split 109319/109319,
gen 167116/167116, discriminating mutants NOT EQUIVALENT; evidence epyc12 head-allfix/pushdup3/VERDICT.txt).

Two text forms carry the TX ingress:
  nr     rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv (head_lep_nr_sources.py --txp): the stage feeds g_txi;
  split  the tree-only rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_split_tx_io_stages.sv (no generator on main): the stage
         drives the exported tx_psh / tx_pg / tx_wd of ot_s81hd_lep_core_nr_txext.
The edit is byte-identical to the W8 hand patch (pushdup3/pd3.py).  Fails closed on any missing / repeated anchor.
Usage: head_lep_pushdup3.py IN OUT nr|split [--txp 4'b1000]"""
import argparse
import re

TXI_LINE = "    parameter [15:0]  TXI = 16'h0000,  // DIE-HEAD-84: per-lane TX ingress stages (see g_tx); 0 = none\n"
TXP_DOC = ("    parameter [3:0]   TXP = 4'b0000,   // LEP-PUSHDUP-3 11-25: lane t with TXP[t] gets one registered TX pre-stage\n"
           "                                       // (g_tx[t].g_txp, kept ot_s81hd_lep_txi_st: word + push + push groups, +1 cycle)\n")
STAGE_NOTE = (
    "        // LEP-PUSHDUP-3 (HEAD-ALLFIX 11-25, Fable C9): g_mtx.wn -> stamp OR tree -> tag mux -> rg3 g_txi.g_s[0] was one 833 ps\n"
    "        // cycle over ~700 um (ep3 CTS -112.9 ps).  TXP[t]: lane t's TX word {sq, half}, its push and its push-group copies are\n"
    "        // registered together in one kept leaf on the lane reset leaf of g_txi, so the lane FIFO sees the same write sequence\n"
    "        // one edge later.  Frame / tag / stamp logic and the other lanes are unchanged (lane FIFOs are credit-read and the\n"
    "        // far pair release matches frames by sequence parity, so a one-lane skew is absorbed).  Plan: native_stage_groups.\n")
WRAPPER = {"nr": ("module ot_s81hd_lep_idx_nr #(\n", "    ot_s81hd_lep_core_nr #("),
           "split": ("module ot_s81hd_lep_idx_nr_txext #(\n", "    ot_s81hd_lep_core_nr_txext #(")}


def txp_value(v):
    """'4'b1000' / '1000' / 'off' -> the Verilog literal 4'bXXXX, or None (off / 0000 = no edit)."""
    if v is None or str(v).lower() in ("", "off", "none", "0"):
        return None
    m = re.fullmatch(r"(?:4'b)?([01]{4})", str(v))
    if not m:
        raise SystemExit(f"LEP-PUSHDUP-3: --txp wants 4 binary digits (lane 3..0), got {v!r}")
    return None if m.group(1) == "0000" else "4'b" + m.group(1)


def _rep(s, old, new, cnt=1):
    if s.count(old) != cnt:
        raise SystemExit(f"LEP-PUSHDUP-3 anchor count {s.count(old)} != {cnt}: {old[:90]!r}")
    return s.replace(old, new)


def apply(s, kind, txp):
    """Return s with the TXP stage (kind 'nr' | 'split') and the wrapper default txp; txp None = s unchanged."""
    txp = txp_value(txp)
    if txp is None:
        return s
    if kind not in WRAPPER:
        raise SystemExit("LEP-PUSHDUP-3: kind is nr or split")
    if "LEP-PUSHDUP-3" in s:
        raise SystemExit("LEP-PUSHDUP-3 already applied")
    # 1. core parameter TXP (default 0 = unchanged).  split: the first TXI line is the core (ot_s81hd_lep_core_nr_txext);
    #    the second is ot_s81hd_lep_txlane, which does not take TXP.
    n = s.count(TXI_LINE)
    if n != (2 if kind == "split" else 1):
        raise SystemExit(f"LEP-PUSHDUP-3 TXI parameter line count {n}")
    i = s.find(TXI_LINE) + len(TXI_LINE)
    s = s[:i] + TXP_DOC + s[i:]
    if kind == "split":
        s = _rep(s, "        assign tx_psh[t] = (SAFE_FIFO)?push_lane[2*t+t/2]:pp[t / 2];\n"
                    "        for(genvar c=0;c<TX_NA;c=c+1) begin:g_pg\n",
                 "        wire psh_c; wire [TX_NA-1:0] pg_c; wire [H:0] wd_c;\n"
                 "        assign psh_c = (SAFE_FIFO)?push_lane[2*t+t/2]:pp[t / 2];\n"
                 "        for(genvar c=0;c<TX_NA;c=c+1) begin:g_pg\n")
        s = _rep(s, "          assign tx_pg[t*TX_NA+c] = pp_d[t/2] | pgd_idx[2*c+t/2];\n",
                 "          assign pg_c[c] = pp_d[t/2] | pgd_idx[2*c+t/2];\n")
        s = _rep(s, "        assign tx_wd[t*(H+1)+:H+1] = {sq[t/2],(t%2==0)?hf0:hf1};\n",
                 "        assign wd_c = {sq[t/2],(t%2==0)?hf0:hf1};\n" + STAGE_NOTE +
                 "        if (TXP[t]) begin:g_txp\n"
                 "          ot_s81hd_lep_txi_st #(.W(H+1),.NV(TX_NA+1)) u_st(.clk(clk),.rn(tx_rt[t]),.v_i({pg_c,psh_c}),.d_i(wd_c),\n"
                 "            .v_o({tx_pg[t*TX_NA+:TX_NA],tx_psh[t]}),.d_o(tx_wd[t*(H+1)+:H+1]));\n"
                 "        end else begin:g_ntxp\n"
                 "          assign tx_psh[t] = psh_c; assign tx_pg[t*TX_NA+:TX_NA] = pg_c; assign tx_wd[t*(H+1)+:H+1] = wd_c;\n"
                 "        end\n")
    else:
        s = _rep(s, "        ot_s81hd_lep_txi #(.W(H+1),.NG(TX_NA),.N(TXI[4*t+:4])) g_txi(.clk(clk),.rn(rt),.psh_i(psh_s),.pg_i(pg_s),\n"
                    "            .wd_i({sq[t/2],(t%2==0)?hf0:hf1}),.psh_o(psh),.pg_o(pgx),.wd_o(wdx));\n",
                 "        wire psh_p; wire [TX_NA-1:0] pg_p; wire [H:0] wd_p;\n" + STAGE_NOTE +
                 "        if (TXP[t]) begin:g_txp\n"
                 "          ot_s81hd_lep_txi_st #(.W(H+1),.NV(TX_NA+1)) u_st(.clk(clk),.rn(rt),.v_i({pg_s,psh_s}),\n"
                 "            .d_i({sq[t/2],(t%2==0)?hf0:hf1}),.v_o({pg_p,psh_p}),.d_o(wd_p));\n"
                 "        end else begin:g_ntxp\n"
                 "          assign psh_p = psh_s; assign pg_p = pg_s; assign wd_p = {sq[t/2],(t%2==0)?hf0:hf1};\n"
                 "        end\n"
                 "        ot_s81hd_lep_txi #(.W(H+1),.NG(TX_NA),.N(TXI[4*t+:4])) g_txi(.clk(clk),.rn(rt),.psh_i(psh_p),.pg_i(pg_p),\n"
                 "            .wd_i(wd_p),.psh_o(psh),.pg_o(pgx),.wd_o(wdx));\n")
    # 2. the head wrapper (its only instantiators are the lep0N hub / core wrappers): TXP default = the knob value.
    hdr, core_inst = WRAPPER[kind]
    i = s.find(hdr)
    j = s.find("parameter [15:0] TXI = 16'h0000,", i)
    k = s.find(core_inst, i)
    e = s.find(") u (", k)
    if not (i >= 0 and j > i and k > i and e > k):
        raise SystemExit("LEP-PUSHDUP-3 wrapper anchors missing")
    s = s[:j] + f"parameter [3:0] TXP = {txp}, " + s[j:]
    k += len(f"parameter [3:0] TXP = {txp}, ")
    e = s.find(") u (", k)
    blk = s[k:e]
    if blk.count(".TXI(TXI), .RXH(RXH)") != 1:
        raise SystemExit("LEP-PUSHDUP-3 wrapper core instance pattern changed")
    return s[:k] + blk.replace(".TXI(TXI), .RXH(RXH)", ".TXI(TXI), .TXP(TXP), .RXH(RXH)") + s[e:]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("kind", choices=sorted(WRAPPER))
    ap.add_argument("--txp", default="4'b1000", help="wrapper default TXP (W8: 4'b1000); off = copy unchanged")
    a = ap.parse_args()
    with open(a.src) as f:
        text = f.read()
    with open(a.dst, "w") as f:
        f.write(apply(text, a.kind, a.txp))
    print("LEP-PUSHDUP-3", a.kind, txp_value(a.txp) or "off", a.dst)
