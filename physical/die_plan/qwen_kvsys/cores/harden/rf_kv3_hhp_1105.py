#!/usr/bin/env python3
"""DIE-KV-71/HHP 11-05 RE-FORM of qkd_kvs_pcc_h_head_p (two strikes on timing).  0 cycles at every pin; applied only to the
qkd_kvs_pc_h_head_p split (rf_kv3_split.py); qkd_kvs_pcc and qkd_kvs_pcf* sources stay byte-identical.

Chain station: land_es[287:1] loses its hold (u_chain.les_i + 574 mux selects off one compare, routed -152).  The only reader,
qkd_host_static_pc*, reads a[287:1] behind a[0] (a <= land_es), and the old port was X until the first boot word.  So the data
differs only while land_es[0] == 0.  Bits 287:286 (constant 1 in a word) take bh so the face flops stay flops.

Timing core: s_pblk ran the whole row decision (noact_c, rrdl, aok, keys of act/pre candidates -> r_oh) into legal_rd/legal_write
although r_oh == sb_oh whenever r_sp: the static-PRE decision is now its own term, with no act/pre mux on the column path.
swait >= S_STARVE, ref_n == 0, ras == 0 and rtp == 0 && wrr == 0 become flags registered from the next state.

Calendar: live and wait == 0 become flags registered from the next state.  Cycle-identical at every output.
"""


def sub_once(s, old, new, what):
    assert s.count(old) == 1, what
    return s.replace(old, new)


def dedupe_ki_ports(t):
    """The split top declares pc__ki_15 / pc__ki_31 twice: yosys-slang asserts on it (rtlil.cc:2888), so the kit LEC never ran here."""
    d = "    input wire [20:15] pc__ki_15,\n    input wire [32:31] pc__ki_31,\n"
    return t.replace(d + d, d, 1)


def hhp_form_1105(src, top_file):
    out = dict(src)
    out[top_file] = dedupe_ki_ports(out[top_file])
    f = "qkd_kv_pc_chain_station_b_p.sv"
    s = out[f]
    a = s.index("    // KV-CORE-RTL/PC 10-25: land_es[287:1] private port flops")
    b = s.index("    always @(posedge ck or negedge rs_q) if (!rs_q) land_es[0] <= 1'b0; else land_es[0] <= bh;")
    s = s[:a] + ("    // DIE-KV-71/HHP 11-05: no hold on land_es[287:1] (was les_i + bh mux): read only behind land_es[0], X before the\n"
                 "    // first word.  {1,1} -> {bh,bh}: 1 in every valid word, and the face flops stay flops (a constant D folds).\n"
                 "    always @(posedge ck) land_es[287:1] <= {bh, bh, c[F_AD +: 29], c[F_D0 +: 256]};\n") + s[b:]
    out[f] = s

    f = "ot_qkd_static_kv_timing.sv"
    s = out[f]
    s = sub_once(s, "    wire sprio = sq_ne && swait >= 8'(S_STARVE);\n",
                 "    // DIE-KV-71/HHP 11-05: swait_ge == (swait >= S_STARVE), registered from the next swait\n"
                 "    reg swait_ge;\n"
                 "    initial if(S_STARVE<1)$fatal(1,\"swait_ge needs S_STARVE>=1\");\n"
                 "    wire sprio = sq_ne && swait_ge;\n", "sprio")
    s = sub_once(s, "    wire ref_due_n = (ref_n == 0);\n",
                 "    // DIE-KV-71/HHP 11-05: ref_n == 0 <=> ref_c == 1 (PERIOD >= 2); ref_is1 == (ref_c == 1), registered\n"
                 "    reg ref_is1;\n"
                 "    initial if(PERIOD<2)$fatal(1,\"ref_is1 needs PERIOD>=2\");\n"
                 "    wire ref_due_n = ref_is1;\n", "ref_due_n")
    s = sub_once(s, "reg aok_zr, rcd_zr;   // == 0 flags, registered\n",
                 "reg aok_zr, rcd_zr;   // == 0 flags, registered\n"
                 "      reg ras_zr, rtp_zr;   // DIE-KV-71/HHP 11-05: ras == 0, rtp == 0 && (!W || wrr == 0), registered from the next state\n",
                 "bank flags decl")
    s = sub_once(s, "aok_zr <= 1'b1; rcd_zr <= 1'b1; wrr <= 0; end\n",
                 "aok_zr <= 1'b1; rcd_zr <= 1'b1; wrr <= 0; ras_zr <= 1'b1; rtp_zr <= 1'b1; end\n", "bank flags reset")
    s = sub_once(s, "          rcd_zr <= rcd_zn[b];\n",
                 "          rcd_zr <= rcd_zn[b];\n"
                 "          ras_zr <= ras_zn[b];\n"
                 "          rtp_zr <= (rd_e ? (T_RTP - 1 == 0) : rtp_le1[b]) && (!W || (wr_e ? (T_WRR - 1 == 0) : wrr_le1[b]));\n",
                 "bank flags next")
    s = sub_once(s, "assign ras_z[b] = (ras == 0); assign rtp_z[b] = (rtp == 0) && (!W || wrr == 0);\n",
                 "assign ras_z[b] = ras_zr; assign rtp_z[b] = rtp_zr;\n", "bank flags read")
    s = sub_once(s, "    reg [31:0] s_pblk;\n",
                 "    // DIE-KV-71/HHP 11-05: s_pblk = (rp_sp ? sb_oh : 0) | (cp_sp ? c_oh : 0), written out on each head so that no\n"
                 "    // act / pre candidate reaches the column decision: r_oh == sb_oh whenever r_sp.\n"
                 "    wire rp_sp, cp_sp;\n", "s_pblk decl")
    s = sub_once(s, "wire legal_rd = rd_ok0 && !s_go && !(|(rd_oh & s_pblk));\n",
                 "wire legal_rd = rd_ok0 && !s_go && !((rp_sp && |(rd_oh & sb_oh)) || (cp_sp && |(rd_oh & c_oh)));\n", "legal_rd")
    s = sub_once(s, "wire legal_write = wr_ok0 && !s_go && !(|(hb_oh & s_pblk));\n",
                 "wire legal_write = wr_ok0 && !s_go && !((rp_sp && |(hb_oh & sb_oh)) || (cp_sp && |(hb_oh & c_oh)));\n", "legal_write")
    s = sub_once(s, "    always @* s_pblk = ((S && slot_next && r_v && r_sp) ? r_oh : 32'b0) | ((S && c_v && c_sp) ? c_oh : 32'b0);\n",
                 "    // the static-PRE branch of the row decision above, with every branch ahead of it\n"
                 "    assign rp_sp = S && slot_next && sprio && s_pre_ok && !(REF_MODE && ref_due_n && ref_pend) &&\n"
                 "                   !(!REF_MODE && ref_due_n) && !preall_ok && !ep_rdy && !forced_pre;\n"
                 "    assign cp_sp = S && c_v && c_sp;\n", "s_pblk")
    s = sub_once(s, "c_sp <= S && slot_next && r_v && r_sp; c_srow <= srw;", "c_sp <= rp_sp; c_srow <= srw;", "c_sp")
    s = sub_once(s, "ref_c <= RW'(RPH + PERIOD); running <= 0; phase <= 0;\n",
                 "ref_c <= RW'(RPH + PERIOD); ref_is1 <= (RW'(RPH + PERIOD) == RW'(1)); running <= 0; phase <= 0;\n", "ref reset")
    s = sub_once(s, "scm <= 0; swait <= 0;\n", "scm <= 0; swait <= 0; swait_ge <= 0;\n", "swait reset")
    s = sub_once(s, "        ref_c <= ref_n; phase <= ~phase;\n", "        ref_c <= ref_n; ref_is1 <= (ref_n == RW'(1)); phase <= ~phase;\n", "ref next")
    s = sub_once(s, "          if (!sq_ne || chg || s_sw) swait <= 0; else if (swait != 8'hff) swait <= swait + 1'b1;\n",
                 "          if (!sq_ne || chg || s_sw) swait <= 0; else if (swait != 8'hff) swait <= swait + 1'b1;\n"
                 "          swait_ge <= !(!sq_ne || chg || s_sw) && swait >= 8'(S_STARVE - 1);\n", "swait next")
    out[f] = s

    f = "qkd_controller_hbm_calendar.sv"
    s = out[f]
    s = sub_once(s, " assign live[g]=left_q[g]!=0;\n assign fire[g]=live[g]&&(wait_q[g]==0);\n",
                 " assign live[g]=live_r[g];\n assign fire[g]=live_r[g]&&wz_r[g];\n", "cal fire")
    s = sub_once(s, " wire [N-1:0] fire,live;\n",
                 " wire [N-1:0] fire,live;\n"
                 " // DIE-KV-71/HHP 11-05: live_r[i]==(left_q[i]!=0), wz_r[i]==(wait_q[i]==0), registered from the next state\n"
                 " reg [N-1:0] live_r,wz_r;\n", "cal decl")
    s = sub_once(s, " for(i=0;i<N;i=i+1)begin wait_q[i]<=0;left_q[i]<=0;burst_q[i]<=0;end\n",
                 " for(i=0;i<N;i=i+1)begin wait_q[i]<=0;left_q[i]<=0;burst_q[i]<=0;live_r[i]<=0;wz_r[i]<=1;end\n", "cal reset")
    s = sub_once(s, " wait_q[i]<=image[i][15:0]+16'(MUT==1);left_q[i]<=image[i][25:16];burst_q[i]<=0;\n",
                 " wait_q[i]<=image[i][15:0]+16'(MUT==1);left_q[i]<=image[i][25:16];burst_q[i]<=0;\n"
                 " wz_r[i]<=(16'(image[i][15:0]+16'(MUT==1))==16'd0);live_r[i]<=(image[i][25:16]!=10'd0);\n", "cal load")
    s = sub_once(s, " left_q[i]<=left_q[i]-10'd1;\n", " left_q[i]<=left_q[i]-10'd1;live_r[i]<=(left_q[i]!=10'd1);\n", "cal left")
    s = sub_once(s, " if(burst_q[i]==image[i][29:26])begin wait_q[i]<= (MUT==2)?16'd0:{8'b0,image[i][37:30]};burst_q[i]<=0;end\n"
                    " else begin wait_q[i]<=0;burst_q[i]<=burst_q[i]+4'd1;end\n"
                    " end else wait_q[i]<=wait_q[i]-16'd1;\n",
                 " if(burst_q[i]==image[i][29:26])begin wait_q[i]<= (MUT==2)?16'd0:{8'b0,image[i][37:30]};burst_q[i]<=0;"
                 "wz_r[i]<=(MUT==2)||(image[i][37:30]==8'd0);end\n"
                 " else begin wait_q[i]<=0;burst_q[i]<=burst_q[i]+4'd1;wz_r[i]<=1;end\n"
                 " end else begin wait_q[i]<=wait_q[i]-16'd1;wz_r[i]<=(wait_q[i]==16'd1);end\n", "cal wait")
    out[f] = s
    return out
