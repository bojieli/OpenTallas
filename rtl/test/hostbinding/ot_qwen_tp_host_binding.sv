`timescale 1ns/1ps
// Host composition boundary only: all state remains in the production RTL.
// Sample desc/VM requests before the rising edge. Publish synchronous read
// responses after every compiled model has evaluated that edge. VM writes
// commit from the pre-edge snapshot, after reads (read-before-write).
module ot_qwen_tp_host_binding (
    input wire clk, rst_n, start,
    input wire [17:0] token, pos,
    input wire [1:0] core_done, core_fault,
    input wire [35:0] core_next_token,
    input wire [63:0] core_next_val,
    input wire [127:0] desc_q,
    input wire [1023:0] vm_rq,
    output wire [1:0] core_start,
    output wire [35:0] core_token, core_pos,
    output wire [23:0] prog_base,
    output wire [1:0] desc_re,
    output wire [11:0] desc_addr,
    output wire [1:0] vm_re, vm_we,
    output wire [15:0] vm_raddr, vm_waddr,
    output wire [1023:0] vm_wdata,
    output wire [1:0] done, seq_fault, coll_fault, coll_busy,
    output wire [35:0] next_token,
    output wire [63:0] next_val,
    output wire [5:0] fault_code,
    output wire [31:0] link_stalls
);
    wire [1:0] cv, crdy, cl, cm, rv, rl, rr, rerr;
    wire [1023:0] cd, rd;
    wire [63:0] ct;
    ot_rom_oneshot_allreduce #(.N(2), .LANES(16), .TAGW(32),
        .DEPTH(16), .LAT(11), .BPC_NUM(3600)) u_coll (
        .clk(clk), .rst_n(rst_n), .in_valid(cv), .in_ready(crdy),
        .in_data(cd), .in_last(cl), .in_mode(cm), .in_tag(ct),
        .out_valid(rv), .out_data(rd), .out_last(rl), .out_rank(rr),
        .out_err(rerr), .fault(coll_fault), .fault_code(fault_code),
        .link_stalls(link_stalls));
    for (genvar d=0; d<2; d=d+1) begin : die
        ot_rom_tp_seq #(.N(2), .NW(18), .PAW(12), .VWA(8),
            .DAW(6), .FW(512), .TAGW(32), .QWEN_FULLSHAPE(1)) seq (
            .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
            .done(done[d]), .next_token(next_token[d*18 +: 18]),
            .next_val(next_val[d*32 +: 32]), .fault(seq_fault[d]),
            .coll_busy(coll_busy[d]), .core_start(core_start[d]),
            .core_token(core_token[d*18 +: 18]), .core_pos(core_pos[d*18 +: 18]),
            .core_done(core_done[d]), .core_fault(core_fault[d]),
            .core_next_token(core_next_token[d*18 +: 18]),
            .core_next_val(core_next_val[d*32 +: 32]),
            .prog_base(prog_base[d*12 +: 12]),
            .desc_re(desc_re[d]), .desc_addr(desc_addr[d*6 +: 6]),
            .desc_q(desc_q[d*64 +: 64]), .vm_re(vm_re[d]),
            .vm_raddr(vm_raddr[d*8 +: 8]), .vm_rq(vm_rq[d*512 +: 512]),
            .vm_we(vm_we[d]), .vm_waddr(vm_waddr[d*8 +: 8]),
            .vm_wdata(vm_wdata[d*512 +: 512]),
            .c_valid(cv[d]), .c_ready(crdy[d]), .c_data(cd[d*512 +: 512]),
            .c_last(cl[d]), .c_mode(cm[d]), .c_tag(ct[d*32 +: 32]),
            .r_valid(rv[d]), .r_data(rd[d*512 +: 512]), .r_last(rl[d]),
            .r_rank(rr[d]), .r_err(rerr[d]));
    end
endmodule
