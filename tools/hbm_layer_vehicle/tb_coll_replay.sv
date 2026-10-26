`timescale 1ns/1ps
`default_nettype none
// VEH-FMT-COLL (10-18): replay-format pre-check of coll_images.py on the REAL gather RTL of ONE quadrant (q0 = SW):
// ot_hgi_coll_gq (= hcollgi_SW issue + hcollgl_SW land), ring A ot_hgi_coll_ring_ag (AG 1, = hb_coll_SW u_ring),
// ring B ot_hgi_coll_ring_b_stop (= hcollb_SW), read / kq static shares (= hcollrs_SW / hcollks_SW) and the
// tb_hgi_coll_gq VM model (8 banks, sample +1, registered response +6; no calendar: the slice's calendar_SW grant is
// not modelled here).  The neighbour ring outputs (NW cw, SE ccw on both rings) are driven ONLY from the replay's
// far-end D events, the gq programme from its host-CP D events, with the slice TB's edge semantics (gen_slice_tb.py):
// D at cyc c -> value right after edge c; C at cyc c -> the output value AT edge c; vm C -> VM word at edge c.
// Event file (coll_replay_events.py): "<cyc> <kind 1 D|2 C|3 M> <port> <sector hex> <value hex>" sorted by cyc.
// Prints COLLRPL PASS / FAIL, checks, mismatches.
module tb_coll_replay;
    parameter string EV = "events.txt";
    parameter integer PA_DLY = 0;  // TOKg 10-23: die relay depth on the A-ring publish lane into hcollgl (r18h5 SW = 3)
    localparam integer NE = 16384;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    integer cnt = -1;
    // gq programme bus
    reg cfg_v = 0, desc_v = 0, launch_v = 0; reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
    reg [11:0] desc_base = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0;
    reg [279:0] a_cw_i = 0, a_ccw_i = 0, b_cw_i = 0, b_ccw_i = 0;
    wire [279:0] a_cw_o, a_ccw_o, b_cw_o, b_ccw_o;
    wire ra_lp_we, ra_srd_add, ra_srd_tx, ra_srd_rr, ra_srhs, ra_stx_acc, ra_add_v, ra_add_rhs, ra_res, ra_acc, ra_gath, ra_rrl;
    wire [2:0] ra_lp_tag, ra_sat, ra_stt, ra_srt, ra_add_tag, ra_tx_tag, ra_rrl_tag; wire [1:0] ra_sas, ra_add_src, ra_inj, ra_fwd, ra_dst, ra_rx;
    wire [255:0] ra_lp_d; wire [3:0] ra_ttl, ra_kind, ra_src; wire [5:0] ra_rtag;
    wire rb_lp_we, rb_rd; wire [2:0] rb_lp_tag, rb_rdt, rb_tag; wire [255:0] rb_lp_d; wire [1:0] rb_inj, rb_fwd, rb_rx;
    wire [3:0] rb_ttl, rb_kind, rb_src; wire [5:0] rb_rtag;
    wire [1:0] ra_ag_v; wire [3:0] ra_ag_s; wire [5:0] ra_ag_t; wire [511:0] ra_ag_d;
    wire [1:0] pa_v, pb_v; wire [3:0] pa_s, pb_s; wire [5:0] pa_t, pb_t; wire [511:0] pa_d, pb_d;
    wire act, dn, tf, fi, fl, conf, f_ra, f_rb, f_rs, f_ks;
    wire [135:0] g_rq, v_rq; wire [2055:0] g_rr, v_rr, a_rr_unused; wire [2247:0] g_kq, v_kq;
    ot_hgi_coll_gq gq(.clk_issue(clk), .clk_land(clk), .rst_n(rst_n), .qid(2'd0), .tgt(8'd176),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .configured(conf), .tgt_fault(tf), .active(act), .done(dn), .fault(fi), .land_fault(fl),
        .isa_ring(58'd0), .isa_lp_data(256'd0),
        .ra_lp_we(ra_lp_we), .ra_lp_tag(ra_lp_tag), .ra_lp_data(ra_lp_d), .ra_state_read_add(ra_srd_add),
        .ra_state_read_tx(ra_srd_tx), .ra_state_read_rr(ra_srd_rr), .ra_state_add_tag(ra_sat), .ra_state_tx_tag(ra_stt),
        .ra_state_rr_tag(ra_srt), .ra_state_add_src(ra_sas), .ra_state_add_rhs_acc(ra_srhs), .ra_state_tx_acc(ra_stx_acc),
        .ra_add_v(ra_add_v), .ra_add_tag(ra_add_tag), .ra_add_src(ra_add_src), .ra_add_rhs_acc(ra_add_rhs),
        .ra_tx_inject(ra_inj), .ra_tx_forward(ra_fwd), .ra_tx_tag(ra_tx_tag), .ra_tx_dst(ra_dst), .ra_tx_result(ra_res),
        .ra_tx_acc(ra_acc), .ra_tx_gather(ra_gath), .ra_tx_ttl(ra_ttl), .ra_rx_slot(ra_rx), .ra_rx_kind(ra_kind),
        .ra_rx_src(ra_src), .ra_rx_tag(ra_rtag), .ra_rr_local(ra_rrl), .ra_rr_local_tag(ra_rrl_tag),
        .rb_lp_we(rb_lp_we), .rb_lp_tag(rb_lp_tag), .rb_lp_data(rb_lp_d), .rb_state_read_tx(rb_rd), .rb_state_tx_tag(rb_rdt),
        .rb_tx_inject(rb_inj), .rb_tx_forward(rb_fwd), .rb_tx_tag(rb_tag), .rb_tx_ttl(rb_ttl), .rb_rx_slot(rb_rx),
        .rb_rx_kind(rb_kind), .rb_rx_src(rb_src), .rb_rx_tag(rb_rtag),
        .pa_v(pa_v), .pb_v(pb_v), .pa_src(pa_s), .pb_src(pb_s), .pa_tag(pa_t), .pb_tag(pb_t), .pa_d(pa_d), .pb_d(pb_d),
        .vm_rq(g_rq), .vm_rr(g_rr), .vm_kq(g_kq));
    wire rr_v; wire [2:0] rr_tag; wire [255:0] rr_d;
    ot_hgi_coll_ring_ag #(.SPLIT_CLOCKS(1), .AG(1)) ra(
        .clk(clk), .rst_n(rst_n), .clk_ctl(clk), .clk_state({8{clk}}), .clk_add({8{clk}}), .qid(2'd0),
        .cw_i(a_cw_i), .ccw_i(a_ccw_i), .cw_o(a_cw_o), .ccw_o(a_ccw_o),
        .lp_we(ra_lp_we), .lp_tag(ra_lp_tag), .lp_data(ra_lp_d),
        .state_read_add(ra_srd_add), .state_read_tx(ra_srd_tx), .state_read_rr(ra_srd_rr),
        .state_add_tag(ra_sat), .state_tx_tag(ra_stt), .state_rr_tag(ra_srt), .state_add_src(ra_sas),
        .state_add_rhs_acc(ra_srhs), .state_tx_acc(ra_stx_acc),
        .add_v(ra_add_v), .add_tag(ra_add_tag), .add_src(ra_add_src), .add_rhs_acc(ra_add_rhs),
        .tx_inject(ra_inj), .tx_forward(ra_fwd), .tx_tag(ra_tx_tag), .tx_dst(ra_dst), .tx_result(ra_res), .tx_acc(ra_acc),
        .tx_gather(ra_gath), .tx_ttl(ra_ttl), .rx_slot(ra_rx), .rx_kind(ra_kind), .rx_src(ra_src), .rx_tag(ra_rtag),
        .rr_local(ra_rrl), .rr_local_tag(ra_rrl_tag), .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d),
        .ag_v(ra_ag_v), .ag_src(ra_ag_s), .ag_tag(ra_ag_t), .ag_d(ra_ag_d), .fault(f_ra));
    wire [523:0] ra_ag = {ra_ag_v, ra_ag_t, ra_ag_s, ra_ag_d};
    reg [523:0] pa_pipe [0:7];
    always @(posedge clk) begin pa_pipe[0] <= ra_ag; for (integer j = 1; j < 8; j = j + 1) pa_pipe[j] <= pa_pipe[j-1]; end
    wire [523:0] pa_x = (PA_DLY == 0) ? ra_ag : pa_pipe[PA_DLY-1];
    assign {pa_v, pa_t, pa_s, pa_d} = pa_x;
    ot_hgi_coll_ring_b_stop rb(.clk(clk), .rst_n(rst_n), .qid(2'd0),
        .cw_i(b_cw_i), .ccw_i(b_ccw_i), .cw_o(b_cw_o), .ccw_o(b_ccw_o),
        .lp_we(rb_lp_we), .lp_tag(rb_lp_tag), .lp_data(rb_lp_d), .state_read_tx(rb_rd), .state_tx_tag(rb_rdt),
        .tx_inject(rb_inj), .tx_forward(rb_fwd), .tx_tag(rb_tag), .tx_ttl(rb_ttl),
        .rx_slot(rb_rx), .rx_kind(rb_kind), .rx_src(rb_src), .rx_tag(rb_rtag),
        .ag_v(pb_v), .ag_src(pb_s), .ag_tag(pb_t), .ag_d(pb_d), .fault(f_rb));
    ot_hbm_idx_vm_share2_static rs(.clk_pair({4{clk}}), .rst_n(rst_n), .a_rq(136'd0), .b_rq(g_rq), .vm_rq(v_rq),
        .vm_rr(v_rr), .a_rr(a_rr_unused), .b_rr(g_rr), .fault(f_rs));
    ot_hgi_coll_kq_share2 ks(.clk_pair({4{clk}}), .rst_n(rst_n), .a_kq(2248'd0), .b_kq(g_kq), .vm_kq(v_kq), .fault(f_ks));
    // ---- VM model (tb_hgi_coll_gq): rq / kq sampled at the edge, response registered 6 edges later
    reg [255:0] mem [0:16383];
    reg [255:0] rpipe_d [0:7][0:5]; reg rpipe_v [0:7][0:5]; reg [256:0] rr_reg [0:7];
    for (genvar b = 0; b < 8; b = b + 1) begin : g_vrr assign v_rr[b*257 +: 257] = rr_reg[b]; end
    integer vm_errors = 0, reads = 0, writes = 0;
    always @(posedge clk) begin
        for (integer b = 0; b < 8; b = b + 1) begin
            reg [16:0] r; reg [280:0] k; reg [13:0] a;
            r = v_rq[b*17 +: 17]; k = v_kq[b*281 +: 281];
            rr_reg[b] <= {rpipe_v[b][5], rpipe_d[b][5]};
            for (integer d = 5; d > 0; d = d - 1) begin rpipe_v[b][d] <= rpipe_v[b][d-1]; rpipe_d[b][d] <= rpipe_d[b][d-1]; end
            rpipe_v[b][0] <= 1'b0;
            if (rst_n && r[16]) begin
                a = {r[15], r[12:0]};
                if (r[2:0] != 3'(b) || (!r[15] && r[14:13] != 2'd0)) begin vm_errors++; $display("COLLRPL VM b%0d bad read sector %h", b, r[15:0]); end
                reads++; rpipe_v[b][0] <= 1'b1; rpipe_d[b][0] <= mem[a];
            end
            if (rst_n && k[280]) begin
                a = {k[279], k[276:264]};
                if (k[266:264] != 3'(b) || (!k[279] && k[278:277] != 2'd0) || k[7:0] != 8'hff) begin vm_errors++; $display("COLLRPL VM b%0d bad write %h", b, k[279:264]); end
                writes++; mem[a] <= k[263:8];
            end
        end
    end
    // ---- events
    integer e_cyc [0:NE-1]; integer e_kind [0:NE-1]; integer e_port [0:NE-1]; reg [15:0] e_sec [0:NE-1]; reg [279:0] e_val [0:NE-1];
    integer ne = 0, ptr = 0, checks = 0, fails = 0, drives = 0;
    function automatic [279:0] sample(input integer p);
        case (p)
            20: sample = a_cw_o; 21: sample = a_ccw_o; 22: sample = b_cw_o; 23: sample = b_ccw_o;
            40: sample = 280'(fi | fl); 41: sample = 280'(conf); 42: sample = 280'(f_rb); 43: sample = 280'(f_ra);
            44: sample = 280'(f_ks); 45: sample = 280'(f_rs); 46: sample = 280'(tf);
            default: sample = '0;
        endcase
    endfunction
    always @(posedge clk) if (rst_n) begin
        cnt = cnt + 1;
        while (ptr < ne && e_cyc[ptr] <= cnt) begin
            if (e_cyc[ptr] < cnt) begin fails++; $display("COLLRPL late event %0d", ptr); end
            else if (e_kind[ptr] == 1) begin
                drives++;
                case (e_port[ptr])
                    0: cfg_v <= e_val[ptr][0]; 1: cfg_target <= e_val[ptr][7:0]; 2: cfg_addr <= e_val[ptr][11:0];
                    3: cfg_data <= e_val[ptr][255:0]; 4: desc_v <= e_val[ptr][0]; 5: desc_base <= e_val[ptr][11:0];
                    6: desc_limit <= e_val[ptr][12:0]; 7: desc_loops <= e_val[ptr][15:0]; 8: launch_v <= e_val[ptr][0];
                    10: a_cw_i <= e_val[ptr]; 11: a_ccw_i <= e_val[ptr]; 12: b_cw_i <= e_val[ptr]; 13: b_ccw_i <= e_val[ptr];
                    default: ;
                endcase
            end else if (e_kind[ptr] == 2) begin
                reg [279:0] got;
                got = e_port[ptr] == 30 ? {24'd0, mem[{e_sec[ptr][15], e_sec[ptr][12:0]}]} : sample(e_port[ptr]);
                checks++;
                if (got !== e_val[ptr]) begin
                    fails++;
                    if (fails < 25) $display("COLLRPL MISMATCH cyc=%0d port=%0d sec=%h got=%h exp=%h", cnt, e_port[ptr], e_sec[ptr], got, e_val[ptr]);
                end
            end
            ptr++;
        end
    end
    initial begin
        integer fd, c, k, p, n; reg [15:0] s; reg [279:0] v; string ev;
        if (!$value$plusargs("EV=%s", ev)) ev = EV;
        for (integer a = 0; a < 16384; a = a + 1) mem[a] = 256'd0;
        for (integer b = 0; b < 8; b = b + 1) begin rr_reg[b] = 0; for (integer d = 0; d < 6; d = d + 1) rpipe_v[b][d] = 0; end
        fd = $fopen(ev, "r");
        if (fd == 0) begin $display("COLLRPL FAIL no event file %s", ev); $finish; end
        while ($fscanf(fd, "%d %d %d %h %h\n", c, k, p, s, v) == 5) begin
            if (k == 3) mem[{s[15], s[12:0]}] = v[255:0];
            else begin e_cyc[ne] = c; e_kind[ne] = k; e_port[ne] = p; e_sec[ne] = s; e_val[ne] = v; ne++; end
        end
        $fclose(fd);
        repeat (5) @(negedge clk); rst_n = 1;
        while (ptr < ne) @(negedge clk);
        repeat (4) @(negedge clk);
        if (fails == 0 && vm_errors == 0 && checks > 0)
            $display("COLLRPL PASS events=%0d drives=%0d checks=%0d vm_reads=%0d vm_writes=%0d last_cyc=%0d", ne, drives, checks, reads, writes, cnt);
        else $display("COLLRPL FAIL fails=%0d vm_errors=%0d checks=%0d", fails, vm_errors, checks);
        $finish;
    end
endmodule
`default_nettype wire
