`timescale 1ns/1ps
// Default-off successor. Uses unchanged ot_v41_ret_pkg and exact LAT5 adder.
// Downstream slots are reserved at launch, not at pipeline arrival.
module ot_v41_ret_credit_node #(
    parameter integer RD = 4,
    parameter integer OUTD = 4,
    parameter integer D = RD,
    parameter integer WAIT = 2,
    parameter integer BYPASS = 0     // 1: a forwarded partial leaves the next cycle (not through the 5-cycle add
                                     //    alignment); it yields to an add result emerging that cycle
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        a_v,
    input  wire [31:0] a_t,
    input  wire [31:0] a_d,
    input  wire        a_e,
    input  wire        b_v,
    input  wire [31:0] b_t,
    input  wire [31:0] b_d,
    input  wire        b_e,
    output wire        o_v,
    output wire [31:0] o_t,
    output wire [31:0] o_d,
    output wire        o_e,
    input wire         o_credit, // registered downstream pop, never an inferred ready
    output reg         a_credit,
    output reg         b_credit,
    output wire        a_ready,
    output wire        b_ready,
    output wire        quiet,
    output reg [31:0]  peak_a, peak_b, credit_stalls,
    output reg         fault
);
    import ot_v41_ret_pkg::*;
    localparam integer AW = $clog2(D);
    localparam integer CW = $clog2(OUTD+1);
    reg [CW-1:0] credits;
    wire room = credits != 0;
    assign a_ready = ac < D;
    assign b_ready = bc < D;
    wire accept_a = a_v && a_ready, accept_b = b_v && b_ready;
    initial begin
      if (D < 2 || (D & (D-1)) || OUTD < 2) $fatal(1,"invalid credit depth");
    end
    reg [31:0] at [0:D-1], bt [0:D-1];
    reg [31:0] ad [0:D-1], bd [0:D-1];
    reg        ae [0:D-1], be [0:D-1];
    reg [AW-1:0] ar, aw, br, bw;
    reg [AW:0] ac, bc;
    reg [4:0] aw8, bw8;
    wire ah = ac != 0, bh = bc != 0;
    wire [31:0] ta = at[ar], tb = bt[br];
    wire want_add = ah && bh && sibling(ta, tb);
    wire add = room && want_add;
    reg [4:0] ap;                        // adds in the adder pipeline, by age
    wire slot_free = (BYPASS == 0) || !ap[3];
    wire fwd_a = room && !want_add && ah && slot_free && (complete(ta) || bh || aw8 >= WAIT || ac == D);
    wire fwd_b = room && !want_add && !fwd_a && bh && slot_free && (complete(tb) || aw8 >= WAIT || bw8 >= WAIT || bc == D);
    wire pop_a = add || fwd_a, pop_b = add || fwd_b;
    wire [31:0] sum;
    wire [1:0] err;
    wire sv;
    ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(add), .a(ad[ar]), .b(bd[br]),
                                .y(sum), .err(err), .valid_out(sv));
    wire [31:0] nt = add ? parent(ta, tb) : (fwd_a ? ta : tb);
    wire [31:0] fd = fwd_a ? ad[ar] : bd[br];
    wire fe = add ? (ae[ar] | be[br]) : (fwd_a ? ae[ar] : be[br]);
    wire [31:0] fdd;
    wire [33:0] dt;
    ot_hdc_delay #(.W(32), .D(5)) u_fd (.clk(clk), .rst_n(rst_n), .d(fd), .q(fdd));
    ot_hdc_delay #(.W(34), .D(5)) u_dt (.clk(clk), .rst_n(rst_n), .d({nt, add, fe}), .q(dt));
    reg [4:0] vp;
    reg        by_v, by_e;
    reg [31:0] by_t;
    reg [31:0] by_d;
    always @(posedge clk) begin by_t <= nt; by_d <= fd; by_e <= fe; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            credits <= OUTD; a_credit <= 0; b_credit <= 0;
            peak_a <= 0; peak_b <= 0; credit_stalls <= 0;
            ar <= 0; aw <= 0; br <= 0; bw <= 0; ac <= 0; bc <= 0; vp <= 0; aw8 <= 0; bw8 <= 0; fault <= 1'b0;
            ap <= 5'd0; by_v <= 1'b0;
        end else begin
            a_credit <= pop_a; b_credit <= pop_b;
            credits <= credits + o_credit - (pop_a || pop_b);
            if (ac > peak_a) peak_a <= ac;
            if (bc > peak_b) peak_b <= bc;
            if (!room && (ah || bh)) credit_stalls <= credit_stalls + 1;
            if ((o_credit && credits == OUTD && !(pop_a || pop_b)) || ((pop_a || pop_b) && !room)) fault <= 1;
            ap <= {ap[3:0], add};
            by_v <= (BYPASS != 0) && (fwd_a | fwd_b);
            vp <= {vp[3:0], add | ((BYPASS == 0) && (fwd_a | fwd_b))};
            if (accept_a) aw <= aw + 1'b1;
            if (accept_b) bw <= bw + 1'b1;
            if (pop_a) ar <= ar + 1'b1;
            if (pop_b) br <= br + 1'b1;
            ac <= ac + (accept_a ? 1'b1 : 1'b0) - (pop_a ? 1'b1 : 1'b0);
            bc <= bc + (accept_b ? 1'b1 : 1'b0) - (pop_b ? 1'b1 : 1'b0);
            aw8 <= (pop_a || !ah) ? 5'd0 : (aw8 == 5'd31 ? aw8 : aw8 + 1'b1);
            bw8 <= (pop_b || !bh) ? 5'd0 : (bw8 == 5'd31 ? bw8 : bw8 + 1'b1);

        end
    end
    always @(posedge clk) begin
        if (accept_a) begin at[aw] <= norm(a_t); ad[aw] <= a_d; ae[aw] <= a_e; end
        if (accept_b) begin bt[bw] <= norm(b_t); bd[bw] <= b_d; be[bw] <= b_e; end
    end
    assign o_v = vp[4] | by_v;
    assign o_t = vp[4] ? dt[33:2] : by_t;
    assign o_d = vp[4] ? (dt[1] ? sum : fdd) : by_d;
    assign o_e = vp[4] ? (dt[0] | (dt[1] && err != 2'd0)) : by_e;
assign quiet = ac == 0 && bc == 0 && vp == 0 && ap == 0 && !by_v && credits == OUTD;
endmodule

// Root queue is associative so a blocked unmatched head cannot hide a queued
// sibling. Every adder launch reserves its eventual held slot until return.
// Legal-program progress still requires bounded distinct unmatched rows; no
// finite queue can admit an unbounded sequence of unrelated rows.
module ot_v41_ret_credit_root #(
    parameter integer ROOTD=128, parameter integer QD=ROOTD
)(
    input wire clk, rst_n,
    input wire i_v, input wire [31:0] i_t, i_d, input wire i_e,
    output wire i_ready, output reg i_credit,
    output reg r_v, output reg [15:0] r_row, output reg [2:0] r_pos,
    output reg [31:0] r_fp32, output reg [15:0] r_bf16, output reg r_e,
    output reg fault, output wire quiet,
    output reg [31:0] peak_q, peak_held, blocked_cycles
);
    import ot_v41_ret_pkg::*;
    reg [QD-1:0] qv;
    reg [31:0] qt[0:QD-1], qd[0:QD-1]; reg qe[0:QD-1];
    reg [ROOTD-1:0] bv;
    reg [31:0] bt[0:ROOTD-1], bd[0:ROOTD-1]; reg be[0:ROOTD-1];
    reg [5:0] pending;
    reg add; reg [31:0] add_a,add_b; reg [32:0] tag_in;
    wire [31:0] sum; wire [1:0] err; wire sv; wire [32:0] st;
    ot_fp32_add_rne_pipe u_add(.clk(clk),.rst_n(rst_n),.valid_in(add),.a(add_a),.b(add_b),.y(sum),.err(err),.valid_out(sv));
    ot_hdc_delay #(.W(33),.D(5)) u_t(.clk(clk),.rst_n(rst_n),.d(tag_in),.q(st));
    integer j,k,qfree,sel,hit,fr,qcount,hcount,pcount;
    reg match_q;
    reg [31:0] ct,cd; reg ce,cv,use_q;
    always @* begin
        qfree=-1; sel=-1; qcount=0; hcount=0; pcount=0; fr=-1;
        for(j=0;j<6;j=j+1) pcount=pcount+pending[j];
        for(j=QD-1;j>=0;j=j-1) begin
            if (!qv[j]) qfree=j; else qcount=qcount+1;
        end
        for(j=ROOTD-1;j>=0;j=j-1) begin
            if(!bv[j]) fr=j; else hcount=hcount+1;
        end
        // Stable available slot priority; only golden siblings may pair.
        for(j=QD-1;j>=0;j=j-1) begin
            match_q=0;
            for(k=0;k<ROOTD;k=k+1)
                if(bv[k] && sibling(bt[k],norm(qt[j]))) match_q=1;
            if(qv[j] && (complete(norm(qt[j])) || match_q || hcount+pcount<ROOTD)) sel=j;
        end
        use_q=!sv && sel>=0;
        cv=sv || use_q;
        ct=sv ? st[32:1] : (sel>=0 ? norm(qt[sel]) : 32'd0);
        cd=sv ? sum : (sel>=0 ? qd[sel] : 32'd0);
        ce=sv ? (st[0] | err!=0) : (sel>=0 ? qe[sel] : 1'b0);
        hit=-1;
        for(k=ROOTD-1;k>=0;k=k-1) if(bv[k] && sibling(bt[k],ct)) hit=k;
    end
    assign i_ready=qfree>=0;
    assign quiet=qv==0 && bv==0 && pending==0 && !add && !sv;
    wire [32:0] rb={1'b0,cd}+33'h7fff+cd[16];
    initial if(ROOTD<2 || QD<2) $fatal(1,"invalid root capacity");
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            qv<=0; bv<=0; pending<=0; add<=0; i_credit<=0; r_v<=0;
            fault<=0; peak_q<=0; peak_held<=0; blocked_cycles<=0;
        end else begin
            pending<={pending[4:0],cv && !complete(ct) && hit>=0};
            add<=0; r_v<=0; i_credit<=use_q;
            if(qcount>peak_q) peak_q<=qcount;
            if(hcount>peak_held) peak_held<=hcount;
            if(qcount!=0 && !sv && sel<0) blocked_cycles<=blocked_cycles+1;
            if(i_v && i_ready) begin qv[qfree]<=1; qt[qfree]<=i_t; qd[qfree]<=i_d; qe[qfree]<=i_e; end
            if(use_q) qv[sel]<=0;
            if(cv) begin
                if(complete(ct)) begin
                    r_v<=1; r_row<=ct[28:13]; r_pos<=ct[31:29];
                    r_fp32<=cd; r_bf16<=rb[31:16]; r_e<=ce;
                end else if(hit>=0) begin
                    add<=1; bv[hit]<=0;
                    if(bt[hit][12:8]<ct[12:8]) begin add_a<=bd[hit]; add_b<=cd; end
                    else begin add_a<=cd; add_b<=bd[hit]; end
                    tag_in<={parent(bt[hit],ct),be[hit]|ce};
                end else if(fr>=0) begin bv[fr]<=1; bt[fr]<=ct; bd[fr]<=cd; be[fr]<=ce; end
                else fault<=1;
            end
            if(hcount+pcount>ROOTD) fault<=1;
        end
    end
endmodule
