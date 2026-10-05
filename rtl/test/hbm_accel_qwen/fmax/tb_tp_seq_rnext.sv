`timescale 1ns/1ps
// Lockstep bench: ot_qwen_tp_seq_w12 (pinned) vs ot_qwen_tp_seq_w12_f12 REG_OUT=1 under identical random
// inputs (descriptors of every kind and length, core done/fault, collective ready / results / errors, resets
// mid-run; results obey the collective's causality, see r_valid).  EVERY output is compared on EVERY cycle.
module tb_qwen_tp_seq_rnext_lockstep;
    parameter integer N = 4, ENABLE_AR256 = 0, REG_CDATA = 1, CYCLES = 100000, SEED = 1;
    localparam integer NW = 18, PAW = 12, VWA = 8, DAW = 6, FW = 512, TAGW = 32, RB = (N > 1) ? $clog2(N) : 1;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg start, core_done, core_fault, c_ready, r_valid, r_last, r_err;
    reg [NW-1:0] token, pos, core_next_token;
    reg [31:0] core_next_val;
    reg [63:0] desc_q;
    reg [FW-1:0] vm_rq, r_data;
    reg [RB-1:0] r_rank;
    reg rv_d=0, rl_d=0, re_d=0;
    reg [FW-1:0] rd_d=0; reg [RB-1:0] rr_d=0;
    always @(posedge clk or negedge rst_n) if(!rst_n) rv_d<=0; else rv_d<=r_valid && u_ref.st==3'd5;
    always @(posedge clk) if(r_valid && u_ref.st==3'd5) begin rd_d<=r_data;rl_d<=r_last;rr_d<=r_rank;re_d<=r_err;end
    wire [2048:0] o0, o1;
`define TPS_PORTS(o,rv,rd,rl,rr,re) \
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos), \
        .done(o[0]), .next_token(o[1 +: NW]), .next_val(o[19 +: 32]), .fault(o[51]), .coll_busy(o[52]), \
        .core_start(o[53]), .core_token(o[54 +: NW]), .core_pos(o[72 +: NW]), .core_done(core_done), \
        .core_next_token(core_next_token), .core_next_val(core_next_val), .core_fault(core_fault), \
        .prog_base(o[90 +: PAW]), .desc_re(o[102]), .desc_addr(o[103 +: DAW]), .desc_q(desc_q), \
        .vm_re(o[109]), .vm_raddr(o[110 +: VWA]), .vm_rq(vm_rq), .vm_we(o[118]), .vm_waddr(o[119 +: VWA]), \
        .vm_wdata(o[127 +: FW]), .c_valid(o[639]), .c_ready(c_ready), .c_data(o[640 +: FW]), .c_last(o[1152]), \
        .c_mode(o[1153]), .c_tag(o[1154 +: TAGW]), .r_valid(rv), .r_data(rd), .r_last(rl), \
        .r_rank(rr), .r_err(re)
    ot_qwen_tp_seq_w12_f12 #(.REG_OUT(1), .REG_CDATA(REG_CDATA), .N(N), .NW(NW), .PAW(PAW), .VWA(VWA), .DAW(DAW), .FW(FW), .TAGW(TAGW),
        .QWEN_FULLSHAPE(1), .ENABLE_AR256(ENABLE_AR256)) u_ref (`TPS_PORTS(o0,rv_d,rd_d,rl_d,rr_d,re_d));
    ot_qwen_tp_seq_w12_rnext #(.R_NEXT(1), .REG_OUT(1), .REG_CDATA(REG_CDATA), .N(N), .NW(NW), .PAW(PAW), .VWA(VWA), .DAW(DAW), .FW(FW), .TAGW(TAGW),
        .QWEN_FULLSHAPE(1), .ENABLE_AR256(ENABLE_AR256)) u_new (`TPS_PORTS(o1,r_valid,r_data,r_last,r_rank,r_err));
    assign o0[2048:1186] = 0;
    assign o1[2048:1186] = 0;
    // Don't-care data: c_data while c_valid is low (and in reset), vm_waddr / vm_wdata while vm_we is low.
    // The successor's transmit queue and vector-memory write word load every edge (REG_CDATA); every
    // value that is consumed (c_data with c_valid, vm_* with vm_we) is compared bit for bit.
    wire [2048:0] m_cd = {{(2049-512){1'b0}}, {512{1'b1}}} << 640;
    wire [2048:0] m_vw = ({{(2049-8){1'b0}}, {8{1'b1}}} << 119) | ({{(2049-512){1'b0}}, {512{1'b1}}} << 127);
    wire [2048:0] mask = ~(((!rst_n || !o0[639]) ? m_cd : 0) | ((REG_CDATA != 0 && !o0[118]) ? m_vw : 0));
    integer seed, cyc, mism, n_coll_ar, n_coll_gat, n_fire, n_vmre, n_done, i;
    function [31:0] rnd(input integer m);
        rnd = ($random(seed) & 32'h7fffffff) % m;
    endfunction
    initial begin
        seed = SEED; mism = 0; n_coll_ar = 0; n_coll_gat = 0; n_fire = 0; n_vmre = 0; n_done = 0;
        {start, core_done, core_fault, c_ready, r_valid, r_last, r_err} = 0;
        token = 0; pos = 0; core_next_token = 0; core_next_val = 0; desc_q = 0; vm_rq = 0; r_data = 0; r_rank = 0;
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            rst_n = ((cyc % 4096) != 4095);
            start = (u_ref.st == 0) && ((cyc % 17) == 0);
            token = 18'd7; pos = 18'd8191;
            core_done = (u_ref.st == 4); core_fault = 0;
            core_next_token = 18'd65537; core_next_val = 32'h3f800000;
            desc_q = 0;
            desc_q[1:0] = ((cyc / 512) % 2) ? 2'd2 : 2'd1;
            desc_q[9:2] = 8'd37;
            desc_q[17:10] = ((cyc / 1024) % 2) ? 8'd0 : 8'd8;
            for (i = 0; i < FW / 32; i = i + 1) begin
                vm_rq[32*i +: 32] = 32'h3f800000 + 32'(cyc*16+i);
                r_data[32*i +: 32] = 32'h3f000000 + 32'(cyc*16+i);
            end
            c_ready = ((cyc % 11) != 0) && ((cyc % 11) != 1);
            // Do not re-offer a record already resident in the one-edge cut.
            r_valid = (u_ref.st == 5) && ((cyc % 5) != 0) &&
                (u_ref.rx_k + (rv_d ? 1 : 0) < u_ref.rx_total) &&
                (u_ref.kind == 2'd2 ? u_ref.tx_k != 0 :
                 u_ref.rx_k + (rv_d ? 1 : 0) < u_ref.tx_k);
            r_last = (u_ref.rx_k + (rv_d ? 1 : 0) == u_ref.rx_total-1);
            r_err = ((cyc % 97) == 0);
            r_rank = RB'(u_ref.rx_k + (rv_d ? 1 : 0));
            #0.5;
            // c_data is the head register's content; an asynchronous reset clears q_r at once, the head
            // register reloads on the next edge (data is not valid while rst_n is low): masked during reset
            if ((o0 & mask) !== (o1 & mask)) begin
                if (mism < 6) begin
                    for (i = 0; i < 1186; i = i + 1) if ((o0[i] & mask[i]) !== (o1[i] & mask[i])) begin
                        $display("MISMATCH cyc %0d bit %0d rst %b st %0d ref %b new %b", cyc, i, rst_n, u_ref.st, o0[i], o1[i]);
                        i = 2000;
                    end
                end
                mism = mism + 1;
            end
            if (o0[52] && o0[639] && c_ready) n_fire = n_fire + 1;
            if (o0[109]) n_vmre = n_vmre + 1;
            if (o0[0]) n_done = n_done + 1;
        end
        $display("RESULT tp_seq REG_CDATA=%0d N=%0d ENABLE_AR256=%0d SEED=%0d cycles=%0d c_fire=%0d vm_re=%0d done_cycles=%0d mismatches=%0d",
                 REG_CDATA, N, ENABLE_AR256, SEED, CYCLES, n_fire, n_vmre, n_done, mism);
        if(mism!=0 || n_fire==0 || n_done==0) $fatal(1,"return packet/state mismatch or vacuous trace");
        $finish;
    end
endmodule
