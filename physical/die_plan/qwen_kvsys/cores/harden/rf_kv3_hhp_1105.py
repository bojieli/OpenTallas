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


# ---- form B (order via DIE-KV-73, 11-05; two strikes, k3 is the 0-cycle form).  Also 0 cycles at every pin in a fault-free run:
# production column events are the compiled slot flops alone (a slot without permission still sets the same sticky fault on the
# same edge and stays off the pins; only state after that fault differs); head context 4:1 split across the following plain flop
# stage, no value while the queue is empty; write-ACT candidate per physical slot; FIFO live and malformed registered.
def _sub(s, old, new, what):
    assert s.count(old) == 1, what
    return s.replace(old, new)


def form_b_timing(s):
    # 1. Compiled schedule: a production column event IS its reservation.
    a = s.index("    wire [5*WQ-1:0] wq_bq;")
    b = s.index("    reg [31:0] hold_n, hold;")
    s = s[:a] + s[b:]
    s = _sub(s, "    assign s_go = legal_static && (PROFILE == 1 || reserved_static_col || boot_static_col);\n",
             "    // DIE-KV-71/HHP 11-05 form B: in production the state machine advances on the compiled slot flop alone, so no JEDEC check\n"
             "    // (open, blk, rcd, ccdl ...) reaches the bank, queue and head state.  A slot without permission still sets the same sticky\n"
             "    // fault on the same edge and is still kept off the pins (s_go_pin / rd_pin / wr_pin); only state after that fault differs.\n"
             "    assign s_go = (PROFILE == 1) ? legal_static : (reserved_static_col || (boot_static_col && legal_static));\n"
             "    wire s_go_pin = s_go && legal_static;\n", "s_go")
    s = _sub(s, "    wire legal_rd = rd_ok0 && !s_go && ", "    wire legal_rd = rd_ok0 && !s_go_pin && ", "legal_rd")
    s = _sub(s, "    assign rd_ok = legal_rd && (PROFILE == 1 || reserved_rd);\n",
             "    assign rd_ok = (PROFILE == 1) ? legal_rd : reserved_rd;\n    wire rd_pin = rd_ok && legal_rd;\n", "rd_ok")
    s = _sub(s, "    wire legal_write = wr_ok0 && !s_go && ", "    wire legal_write = wr_ok0 && !s_go_pin && ", "legal_write")
    s = _sub(s, "    assign wr_ok = legal_write && (PROFILE == 1 || reserved_write_col);\n",
             "    assign wr_ok = (PROFILE == 1) ? legal_write : reserved_write_col;\n    wire wr_pin = wr_ok && legal_write;\n", "wr_ok")
    s = _sub(s, "    assign col_v = rd_ok || (W && wr_ok) || s_go; assign col_we = (W && wr_ok && !(AQ && hr)) || (s_go && swe);\n",
             "    assign col_v = rd_pin || (W && wr_pin) || s_go_pin; assign col_we = (W && wr_pin && !(AQ && hr)) || (s_go_pin && swe);\n", "col_v")
    s = _sub(s, "    assign col_aq = AQ && wr_ok && hr; assign col_sr = s_go;\n",
             "    assign col_aq = AQ && wr_pin && hr; assign col_sr = s_go_pin;\n", "col_sr")
    s = _sub(s, "assign s_pop = s_go;\n", "assign s_pop = s_go_pin;\n", "s_pop")
    # 2. Head context: split the 4:1 across the zero-logic stage that follows it; no value while the queue is empty.
    a = s.index("    // RF-KV2 (b): the static head context IS the queue entry")
    b = s.index("    wire sq_ne = S && sq_n != 0;\n")
    s = s[:a] + ("    // DIE-KV-71/HHP 11-05 form B: col_context is the head entry one edge later, split across this output and the plain\n"
                 "    // flop stage after it (the caller's own col_context flop is gone, so the same edge as before).  Read only with a\n"
                 "    // static column, which needs a head, so the empty-queue value (s_empty_context) is dropped.\n"
                 "    initial if(SQD!=4)$fatal(1,\"context split assumes SQD==4\");\n"
                 "    reg [346:0] ctx_lo, ctx_hi; reg ctx_sel;\n"
                 "    always @(posedge clk) begin\n"
                 "      ctx_lo <= sq_rp[0] ? sq_context[1] : sq_context[0];\n"
                 "      ctx_hi <= sq_rp[0] ? sq_context[3] : sq_context[2];\n"
                 "      ctx_sel <= sq_rp[1];\n"
                 "    end\n"
                 "    assign col_context = ctx_sel ? ctx_hi : ctx_lo;\n") + s[b:]
    # 3. Write-ACT candidate: per physical slot from the stored one-hots, then oldest first (was wq_rp + i -> index -> bank decode).
    a = s.index("    wire [WQ-1:0] wq_act;\n")
    b = s.index("    // The candidate (oldest queued write whose bank can open) is REGISTERED")
    s = s[:a] + ("    // DIE-KV-71/HHP 11-05 form B: eligibility per physical slot (wq_v == the entry is queued), then the oldest eligible slot.\n"
                 "    wire [WQ-1:0] sl_act;\n"
                 "    for (genvar i = 0; i < WQ; i = i + 1) begin : wqa\n"
                 "      assign sl_act[i] = W && wq_v[i] && !(|(wq_oh[i] & (open | blk))) && (|(wq_oh[i] & aok_z)) && rrdl_z[wq_bank[i][1:0]] &&\n"
                 "                         !(REF_MODE && (ref_c == RW'(LEAD) || ref_c == RW'(LEAD + 1)) && wq_bank[i] == bsel);\n"
                 "    end\n") + s[b:]
    s = _sub(s, "    reg wcand; reg [4:0] wab_n; reg wcrd_n;\n", "    reg wcand; reg [4:0] wab_n; reg wcrd_n; reg [31:0] wab_oh_n;\n", "wcand decl")
    s = _sub(s, "      wcand = 1'b0; wab_n = 0; wcrd_n = 1'b0;\n      for (ai = WQ - 1; ai >= 0; ai = ai - 1) if (wq_act[ai]) begin\n"
                "        wcand = 1'b1; wab_n = wq_bq[ai*5 +: 5]; wcrd_n = AQ && wq_rd[WQW'(wq_rp + ai)];\n      end\n",
                "      wcand = 1'b0; wab_n = 0; wcrd_n = 1'b0; wab_oh_n = 32'b1;\n      for (ai = WQ - 1; ai >= 0; ai = ai - 1) if (sl_act[WQW'(wq_rp + ai)]) begin\n"
                "        wcand = 1'b1; wab_n = wq_bank[WQW'(wq_rp + ai)]; wab_oh_n = wq_oh[WQW'(wq_rp + ai)]; wcrd_n = AQ && wq_rd[WQW'(wq_rp + ai)];\n      end\n", "wcand")
    s = _sub(s, "wab_oh <= 32'b1 << wab_n;", "wab_oh <= wab_oh_n;", "wab_oh")
    return s


def form_b_emb(s):
    s = _sub(s, "output reg [346:0] col_context,", "output wire [346:0] col_context,", "col_context port")
    s = _sub(s, " wire live=(ENABLE!=0) && count!=0;\n",
             " // DIE-KV-71/HHP 11-05 form B: live == (ENABLE && count != 0), registered from the next count; malformed computed at push,\n"
             " // kept with the entry and moved with head.\n"
             " reg live_q; wire live=live_q;\n reg mal_fifo[0:7]; reg head_mal;\n", "live")
    a = s.index(" wire malformed=(head[31:30]==3")
    b = s.index(" wire pop=live && (malformed")
    s = s[:a] + (" wire in_ctx=CONTEXT_DESC!=0 && cmd_q[31:30]==3;\n"
                 " wire in_mal=(cmd_q[31:30]==3 && !in_ctx) || (in_ctx && (cmd_q[27:19]>256 || first_q>128)) ||\n"
                 "    (cmd_q[31:30]==0 && (cmd_q[29:19]==0 || cmd_q[29:19]>1024 || first_q>=cmd_q[29:19]));\n"
                 " wire malformed=head_mal;\n") + s[b:]
    s = _sub(s, "  s_context_q<=s_context;col_context<=core_context;\n", "  s_context_q<=s_context;\n", "ctx flop")
    s = _sub(s, "  if(push)begin fifo[wp]<=cmd_q;first_fifo[wp]<=first_q;end\n", "  if(push)begin fifo[wp]<=cmd_q;first_fifo[wp]<=first_q;mal_fifo[wp]<=in_mal;end\n", "fifo")
    s = _sub(s, "  if(count==0 && push)begin head<=cmd_q;head_first<=first_q;end\n", "  if(count==0 && push)begin head<=cmd_q;head_first<=first_q;head_mal<=in_mal;end\n", "h0")
    s = _sub(s, "   if(count>1)begin head<=fifo[rp_next];head_first<=first_fifo[rp_next];end\n   else if(push)begin head<=cmd_q;head_first<=first_q;end\n",
             "   if(count>1)begin head<=fifo[rp_next];head_first<=first_fifo[rp_next];head_mal<=mal_fifo[rp_next];end\n   else if(push)begin head<=cmd_q;head_first<=first_q;head_mal<=in_mal;end\n", "h1")
    s = _sub(s, "s_cr<=0;col_sr<=0;\n", "s_cr<=0;col_sr<=0;live_q<=0;\n", "rst")
    s = _sub(s, "   if(push) wp<=wp+1'b1;\n", "   if(push) wp<=wp+1'b1;\n   if(push&&!pop) live_q<=1'b1; else if(pop&&!push) live_q<=(count!=4'd1);\n", "liven")
    s = s.replace("assign col_context=core_context;", "")
    s = _sub(s, " wire [346:0] core_context;\n", " wire [346:0] core_context;\n assign col_context=core_context;\n", "assign")
    return s


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
    out["ot_qkd_static_kv_timing.sv"] = form_b_timing(out["ot_qkd_static_kv_timing.sv"])
    out["ot_qkd_static_ctrl_pc_emb.sv"] = form_b_emb(out["ot_qkd_static_ctrl_pc_emb.sv"])
    return out
