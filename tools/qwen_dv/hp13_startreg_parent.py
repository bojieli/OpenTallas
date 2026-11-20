#!/usr/bin/env python3
"""QC-TTCTLM-1119 R1: HP13 tt_ctlm STARTREG form (+1 segment-start edge), frontend source rewrite.

u_cal CALREG 1 -> 3 (FQREG + STARTREG: the start interface start/stage/user/range, its one-hot, range check and stage
class are registered in front of the playheads; QE3-CTLM3 10-21, 'the parent delays its other start consumers by the
same edge').  This tool writes the HP13 parent half of that contract into qfd_tt_ctlm_dv_lpf_hp13_parts.sv (parameter
SREG, default 1 in the rewritten frontend copy): every start consumer OUTSIDE u_cal reads the start bundle one edge
later (sd_* / sl_* registers): head-stage bank stg_b, head start/stage to u_hr (hd_start/hd_stage), ME start s_me and
the st capture, the per-user token/position bank write, the typed-witness start event (token identity registered at
the original edge), and dc tok_clr.  u_cal reads the undelayed bundle and registers it itself.  Fault detectors
(op_coll, x_hit, init_u0_bad) keep the pin edge.  Result: calendar, head and ME play every start one edge later;
native emb/st/fctx outputs +1 edge.  Cause: tt_ctlm TT setup, 840 of 891 >= 24-level endpoints start at dh_q[36]
(d_stage) and the dh_q[42] replicas (u_75259) through the u_cal start decode.
Usage: hp13_startreg_parent.py PARTS.sv CAL_FQREG.sv   (rewritten in place, in a frontend tree copy)
"""
import hashlib, sys
from pathlib import Path


def sub(t, old, new, n=1):
    assert t.count(old) == n, (old, t.count(old))
    return t.replace(old, new)


def main():
    parts, cal = Path(sys.argv[1]), Path(sys.argv[2])
    t = parts.read_text()
    t = sub(t, "    parameter integer F16WTN = 0,",
            "    parameter integer SREG = 1,                  // QC-TTCTLM-1119 R1: u_cal STARTREG parent map (+1 start edge)\n"
            "    parameter integer F16WTN = 0,")
    t = sub(t, "    wire [UB-1:0] u_user = l_start ? l_user : s_user;\n",
            "    wire [UB-1:0] u_user = l_start ? l_user : s_user;\n"
            "    // QC-TTCTLM-1119 R1 (u_cal CALREG[1] STARTREG): the start consumers outside u_cal read the start bundle one\n"
            "    // edge later, as u_cal's playheads do, so calendar / head / ME play every start one edge later together.\n"
            "    reg sd_start_q, sl_start_q; reg [5:0] sd_stage_q, sl_stage_q; reg [17:0] sd_tok_q, sd_pos_q;\n"
            "    reg [UB-1:0] sd_user_q, sl_user_q;\n"
            "    always @(posedge ck or negedge rst_n)\n"
            "        if (!rst_n) begin sd_start_q <= 1'b0; sl_start_q <= 1'b0; end\n"
            "        else begin sd_start_q <= d_start; sl_start_q <= l_start; end\n"
            "    always @(posedge ck) begin\n"
            "        sd_stage_q <= d_stage; sl_stage_q <= op_stage; sd_tok_q <= s_tok; sd_pos_q <= s_pos;\n"
            "        sd_user_q <= s_user; sl_user_q <= l_user;\n"
            "    end\n"
            "    wire        e_dstart = (SREG != 0) ? sd_start_q : d_start;\n"
            "    wire        e_lstart = (SREG != 0) ? sl_start_q : l_start;\n"
            "    wire [5:0]  e_dstage = (SREG != 0) ? sd_stage_q : d_stage;\n"
            "    wire [5:0]  e_lstage = (SREG != 0) ? sl_stage_q : op_stage;\n"
            "    wire [17:0] e_tok = (SREG != 0) ? sd_tok_q : s_tok, e_pos = (SREG != 0) ? sd_pos_q : s_pos;\n"
            "    wire [UB-1:0] e_suser = (SREG != 0) ? sd_user_q : s_user;\n"
            "    wire [UB-1:0] e_luser = (SREG != 0) ? sl_user_q : l_user;\n"
            "    wire        e_ustart = e_dstart || e_lstart;\n"
            "    wire [5:0]  e_ustage = e_lstart ? e_lstage : e_dstage;\n"
            "    wire [UB-1:0] e_uuser = e_lstart ? e_luser : e_suser;\n")
    t = sub(t, "    wire        s_u0 = (NU == 1) || (s_user == {UB{1'b0}});",
            "    wire        s_u0 = (NU == 1) || (e_suser == {UB{1'b0}});")
    t = sub(t, "            if (d_start) stg_b[s_user] <= d_stage;\n            else if (l_start) stg_b[l_user] <= op_stage;",
            "            if (e_dstart) stg_b[e_suser] <= e_dstage;\n            else if (e_lstart) stg_b[e_luser] <= e_lstage;")
    t = sub(t, "    wire        hd_start = (NU == 1 || 1'b0) ? d_start : ((d_start && s_u0) || c_seg);\n"
               "    wire [5:0]  hd_stage = (NU == 1 || 1'b0) ? d_stage : ((d_start && s_u0) ? d_stage : stg_b[c_user]);",
            "    wire        hd_start = (NU == 1 || 1'b0) ? e_dstart : ((e_dstart && s_u0) || c_seg);\n"
            "    wire [5:0]  hd_stage = (NU == 1 || 1'b0) ? e_dstage : ((e_dstart && s_u0) ? e_dstage : stg_b[c_user]);")
    t = sub(t, "    wire        s_me0 = (STAGE_ME == 0) ? d_start : (d_start && d_stage != 6'd0 && d_stage < LAST_STAGE[5:0]);",
            "    wire        s_me0 = (STAGE_ME == 0) ? e_dstart : (e_dstart && e_dstage != 6'd0 && e_dstage < LAST_STAGE[5:0]);")
    t = sub(t, "            if (d_start) begin tok_b[s_user] <= s_tok; pos_b[s_user] <= s_pos; end",
            "            if (e_dstart) begin tok_b[e_suser] <= e_tok; pos_b[e_suser] <= e_pos; end")
    t = sub(t, "            if (s_me) begin st_tok <= s_tok; st_pos <= s_pos; st_base <= 12'd0; end",
            "            if (s_me) begin st_tok <= e_tok; st_pos <= e_pos; st_base <= 12'd0; end")
    t = sub(t, "    wire [15:0] u_tokid = l_start ? tok_b[l_user][15:0] : s_tok[15:0];   // the context's token identity at its start\n",
            "    wire [15:0] u_tokid = l_start ? tok_b[l_user][15:0] : s_tok[15:0];   // the context's token identity at its start\n"
            "    reg  [15:0] sd_tokid_q;\n"
            "    always @(posedge ck) sd_tokid_q <= u_tokid;                       // R1: read at the pin edge, delivered +1\n"
            "    wire [15:0] e_tokid = (SREG != 0) ? sd_tokid_q : u_tokid;\n")
    t = sub(t, ".start({u_start, 2'(u_user), u_stage, u_tokid})", ".start({e_ustart, 2'(e_uuser), e_ustage, e_tokid})")
    t = sub(t, "    assign dcs = {d_start && d_stage == 6'd0,", "    assign dcs = {e_dstart && e_dstage == 6'd0,")
    parts.write_text(t)
    c = cal.read_text()
    c = sub(c, "    parameter integer CALREG = 1 ", "    parameter integer CALREG = 3 ")
    cal.write_text(c)
    for p in (parts, cal):
        print(p.name, hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
