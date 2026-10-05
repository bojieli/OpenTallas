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
            if (rnd(200000) == 0) rst_n = 0; else rst_n = 1;
            start = rnd(20) == 0;
            token = {$random(seed)}; pos = {$random(seed)};
            core_done = rnd(8) == 0; core_fault = rnd(500) == 0;
            core_next_token = {$random(seed)}; core_next_val = $random(seed);
            desc_q = {$random(seed), $random(seed)};
            case (rnd(4)) 0: desc_q[1:0] = 0; 1, 2: desc_q[1:0] = 1; default: desc_q[1:0] = 2; endcase
            case (rnd(4)) 0: desc_q[17:10] = ENABLE_AR256 ? 0 : 255; 1: desc_q[17:10] = 1 + rnd(4); default: if (desc_q[17:10] == 0 && !ENABLE_AR256) desc_q[17:10] = 7; endcase
            for (i = 0; i < FW / 32; i = i + 1) begin vm_rq[32*i +: 32] = $random(seed); r_data[32*i +: 32] = $random(seed); end
            c_ready = rnd(4) != 0;
            // Legal collective: a result word k returns only after this die sent word k (all-reduce), and the
            // gather returns only after the die's own record left (so a segment never ends with words unsent).
            // Without this, random results can end S_COLL with a full transmit queue, a state the collective
            // cannot produce, in which the original then overwrites its live queue head.
            r_valid = (rnd(3) == 0) && (u_ref.st != 3'd5 || (u_ref.kind == 2'd2 ? u_ref.tx_k != 0 : u_ref.rx_k < u_ref.tx_k));
            r_last = rnd(10) == 0; r_err = rnd(1000) == 0; r_rank = rnd(N);
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
