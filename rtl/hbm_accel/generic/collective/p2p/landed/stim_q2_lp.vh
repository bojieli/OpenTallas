// PL-COLLQ 10-18: lockstep stimulus for tb_ot_hfd_coll_q2_lp (lp.py spec tb_stimulus; module-level include).
// The v5 hard-parent bench programme (tb_hgi_coll_q_hard_v5: actual F20 frames, reduce rows 12-29, scen-7 VM read /
// assembly / slot capture / delivery rows 4, 14, 15) plus writer rows (REDSRC -> rgx sinks 6..9 with rgx_vm and every
// VM slot valid) so the VM-writer region and its landed inputs carry traffic; two launches. Every data bus (VM read
// data, inject data, rc_d, ring lanes, ra_* ring commands, link rx flits) is random every edge; link rx valids stay 0.
localparam integer S_NR = 36, S_ND = 15, S_RED = 8;
localparam [7:0] S_TGT = 8'd53;                       // 52 + qid 1
reg [1535:0] s_code [0:S_NR-1];
reg [54:0] s_ar;
reg s_rand = 1'b0;
reg [2079:0] s_t;
integer s_i;
always @(negedge clk) if (s_rand) begin
    for (s_i = 0; s_i < 2080; s_i = s_i + 32) s_t[s_i +: 32] = $urandom;
    fi_vm_rr = s_t[2055:0];
    for (s_i = 0; s_i < 1056; s_i = s_i + 32) s_t[s_i +: 32] = $urandom;
    fi_inj_d = s_t[1023:0];
    for (s_i = 0; s_i < 1248; s_i = s_i + 32) s_t[s_i +: 32] = $urandom;
    fi_rx_pin_flit = s_t[1223:0];
    for (s_i = 0; s_i < 1152; s_i = s_i + 32) s_t[s_i +: 32] = $urandom;
    fi_pr_cw_i = s_t[279:0]; fi_pr_ccw_i = s_t[559:280]; fi_rc_d = s_t[815:560]; fi_ra_lp_data = s_t[1071:816];
    s_t[31:0] = $urandom; s_t[63:32] = $urandom;
    {fi_ra_lp_we, fi_ra_lp_tag, fi_ra_state_read_add, fi_ra_state_read_tx, fi_ra_state_read_rr, fi_ra_state_add_tag,
     fi_ra_state_tx_tag, fi_ra_state_rr_tag, fi_ra_state_add_src, fi_ra_state_add_rhs_acc, fi_ra_state_tx_acc,
     fi_ra_add_v, fi_ra_add_tag, fi_ra_add_src, fi_ra_add_rhs_acc, fi_ra_tx_inject, fi_ra_tx_forward, fi_ra_tx_tag,
     fi_ra_tx_dst, fi_ra_tx_result, fi_ra_tx_acc, fi_ra_tx_gather, fi_ra_tx_ttl} = s_t[49:0];
    s_t[31:0] = $urandom;
    {fi_ra_rx_slot, fi_ra_rx_kind, fi_ra_rx_src, fi_ra_rx_tag, fi_ra_rr_local, fi_ra_rr_local_tag} = s_t[19:0];
    fi_rc_tag = $urandom;
end
// activity witness (the lockstep must see traffic in every region): flat-parent outputs
integer s_del = 0, s_kq = 0, s_rr = 0, s_tx = 0; reg [2247:0] s_kq_q = 0;
always @(negedge clk) begin
    if (fo_del_valid != 0) s_del = s_del + 1;
    if (fo_vm_kq != s_kq_q) s_kq = s_kq + 1;
    s_kq_q = fo_vm_kq;
    if (fo_rr_v) s_rr = s_rr + 1;
    if (fo_tx_pin_v != 0) s_tx = s_tx + 1;
end
task s_frame(input [7:0] tgt, input integer row, input integer seg, input [255:0] v);
    begin @(negedge clk); fi_cfg_v = 1'b1; fi_cfg_target = tgt; fi_cfg_addr = 12'(row * 8 + seg); fi_cfg_data = v; end
endtask
task s_pack_ar(input integer row, input [54:0] c);
    begin s_code[row][1505 +: 31] = c[30:0]; s_code[row][688 +: 24] = c[54:31]; end
endtask
initial begin : s_main
    integer row, seg, c, l;
    reg [63:0] md;
    fi_qid = 2'd1; fi_qid_rg = 2'd1; fi_qid_wr = 2'd1; fi_cfg_v = 0; fi_cfg_target = S_TGT; fi_cfg_addr = 0; fi_cfg_data = 0; fi_desc_v = 0;
    fi_desc_base = 12'd0; fi_desc_limit = 13'(S_NR); fi_desc_loops = 16'd1; fi_launch_v = 0; fi_rc_v = 0;
    fi_phy_up = 2'b11; fi_rx_pin_v = 2'b00; fi_vm_rr = 0; fi_inj_d = 0; fi_rx_pin_flit = 0; fi_pr_cw_i = 0; fi_pr_ccw_i = 0;
    fi_rc_d = 0; fi_rc_tag = 0; fi_ra_lp_data = 0;
    {fi_ra_lp_we, fi_ra_lp_tag, fi_ra_state_read_add, fi_ra_state_read_tx, fi_ra_state_read_rr, fi_ra_state_add_tag,
     fi_ra_state_tx_tag, fi_ra_state_rr_tag, fi_ra_state_add_src, fi_ra_state_add_rhs_acc, fi_ra_state_tx_acc,
     fi_ra_add_v, fi_ra_add_tag, fi_ra_add_src, fi_ra_add_rhs_acc, fi_ra_tx_inject, fi_ra_tx_forward, fi_ra_tx_tag,
     fi_ra_tx_dst, fi_ra_tx_result, fi_ra_tx_acc, fi_ra_tx_gather, fi_ra_tx_ttl} = 0;
    {fi_ra_rx_slot, fi_ra_rx_kind, fi_ra_rx_src, fi_ra_rx_tag, fi_ra_rr_local, fi_ra_rr_local_tag} = 0;
    for (row = 0; row < S_NR; row = row + 1) s_code[row] = 0;
    // v5 bench programme (q2: NPT 2, ND 15, REDSRC 8)
    s_code[0][90] = 1; s_code[0][284 +: 33] = {1'b1, 8'hff, 8'd0, 16'd0};
    s_code[1][90] = 1; s_code[1][92 +: 16] = 16'd1; s_code[1][284 +: 33] = {1'b1, 8'hff, 8'd1, 16'd1};
    s_code[12][0] = 1; s_code[13][0] = 1;
    s_code[13][10 + S_ND - 1] = 1; s_code[13][26 + (S_ND - 1) * 4 +: 4] = 0;
    s_code[14][10 + S_ND - 1] = 1; s_code[14][26 + (S_ND - 1) * 4 +: 4] = 0;
    s_ar = 0; s_ar[0] = 1; s_pack_ar(15, s_ar);
    s_ar = 0; s_ar[5] = 1; s_pack_ar(16, s_ar);
    s_ar = 0; s_ar[10] = 1; s_pack_ar(17, s_ar);
    s_ar = 0; s_ar[11] = 1; s_ar[21] = 1; s_ar[23 +: 8] = 8'd7; s_ar[31 +: 16] = 16'd13; s_pack_ar(26, s_ar);
    s_ar = 0; s_ar[22] = 1; s_pack_ar(27, s_ar);
    s_code[28][S_RED] = 1;
    s_code[29][10 + 2] = 1; s_code[29][26 + 2 * 4 +: 4] = 4'(S_RED);
    // scen 7: legal VM read (banks 0 and 7), assembly select, slot capture, delivery
    s_code[4][1034 + 16] = 1; s_code[4][1034 + 7 * 17 + 16] = 1;
    s_code[4][1383 +: 6] = {3'd7, 3'd0};
    s_code[4][1170 +: 33] = {1'b1, 8'h56, 8'h4d, 16'h0700};
    s_code[14][2 + 2] = 1;
    s_code[15][10 + 2] = 1; s_code[15][26 + 2 * 4 +: 4] = 4'(2 + 2);
    // writer traffic: the captured reduce publication to rgx sinks 6..9, VM ingress on, every VM slot valid
    for (row = 30; row < 34; row = row + 1) begin
        s_code[row][10 + 6 + (row - 30)] = 1; s_code[row][26 + (6 + row - 30) * 4 +: 4] = 4'(S_RED);
        s_code[row][584] = 1; s_code[row][585 +: 5] = 5'(row - 30); s_code[row][590 +: 8] = 8'hff;
        s_code[row][598 +: 32] = 32'h76543210;
    end
    s_code[S_NR - 1][874 +: 40] = 40'h12345;
    s_rand = 1'b1;
    repeat (16) @(negedge clk);
    rst = 1'b1;                                         // release (bench.reset_cycles = 16)
    repeat (8) @(negedge clk);
    for (row = 0; row < S_NR; row = row + 1) begin
        md = 64'(row + 1); if (row == S_NR - 1) md[44] = 1;
        for (seg = 0; seg < 6; seg = seg + 1) s_frame(S_TGT, row, seg, s_code[row][seg * 256 +: 256]);
        s_frame(S_TGT, row, 6, {192'b0, md});
        @(negedge clk); fi_cfg_v = 0;
        repeat (55) @(negedge clk);
    end
    @(negedge clk); fi_desc_v = 1; fi_cfg_target = S_TGT;
    @(negedge clk); fi_desc_v = 0; repeat (66) @(negedge clk);
    for (l = 0; l < 2; l = l + 1) begin
        @(negedge clk); fi_launch_v = 1;
        @(negedge clk); fi_launch_v = 0;
        repeat (160) @(negedge clk);
    end
    // a second reset pulse under live random ring traffic: every region's reset run must release on its documented
    // edge (MUT 4 delays one child's run by one stage; an idle release would hide it)
    @(negedge clk); rst = 1'b0; repeat (6) @(negedge clk); rst = 1'b1; repeat (200) @(negedge clk);
    $display("LP_ACTIVITY del_valid_cycles=%0d vm_kq_changes=%0d rr_v_cycles=%0d tx_v_cycles=%0d fault=%0d cause=%h",
             s_del, s_kq, s_rr, s_tx, fo_fault, fo_fault_cause);
    lp_finish("q2_v5prog_vm_writer_ring_random");
end
