`timescale 1ns/1ps
`default_nettype none
// HBM-HCROOT6 10-20 (H.STA.BLK.1, SAFE-DESIGN items 3 + 4 + 5): ot_hgi_hc_tail_os_static -- the exact HC sigmoid /
// Sinkhorn tail ot_hgi_hc_tail_static, bit for bit and edge for edge, with every runtime-indexed read and write-back
// rebuilt on REGISTERED ONE-HOT selects:
//   * reads: the 24:1 operand reads t[i] / b[i] / mx[..] / s[..] of the four units are AND-OR selects on per-unit one-hot
//     select registers (sm / sa / sx / sd for the multiplier, adder, exp and divider operand, sb for the adder's bases
//     operand, smx / ss / stwo / sone / seps for the constant and short operands).  Each select register is loaded on
//     the previous edge from the decode of the NEXT {active, age} state (the same next-state function as the counter),
//     so it equals the decode of the current state: no edge is added.  Outside an issue window every select is 0, so a
//     unit's operand is 0 instead of the old garbage index (the units are pure pipelines; their outputs are only used
//     under their own valid_out, exactly as before).
//   * write-backs: t[mi] <= my (etc.) used 5-bit index delay lines (D 3 / 3 / 49 / 19; the 49-deep exp line is a
//     245-flop hold chain).  The calendar is static, so the write-back index is a function of the current age alone
//     (issue age + unit latency); one-hot write enables are registered predicted decodes like the read selects, and
//     every delay line is gone.  A unit valid_out that disagrees with its predicted write window raises `fault`
//     (fail closed; never on a legal schedule).
//   * the row-max enable, the result capture enable and the launch capture keep their edges.
// Exactness holds for every fault-free schedule (no launch while active); a faulting schedule raises the same sticky
// fault as ot_hgi_hc_tail_static.  The select / decode registers are unreset: they hold decodes of the reset state
// (active 0 = all 0) after one clock edge inside reset (every reset relay holds reset >= 3 edges with the clock running).
// MUT (bench): 1 = the p3 row-max operand of row group 1 reads row 0's max (mx index off by one group).
module ot_hgi_hc_tail_os_static #(
    parameter integer ITERS=20,
    parameter [31:0] HC_EPS=32'h358637bd,
    parameter integer MUT_PRE=0,
    parameter integer MUT=0
)(
    input wire clk,sink_clk,rst_n,
    input wire launch,
    input wire [767:0] mixes,bases,
    input wire [95:0] scales,
    input wire sink_launch,sink_capture,
    output wire e_ready,
    output reg result_v,
    output wire [767:0] result,
    output reg fault
);
    localparam integer P1=1,P2=28,MAX=55,P3=56,P4=75,P5=148,P6=159,P7=186,EREADY=197;
    localparam integer DM=3,DA=3,DE=49,DD=19;          // unit latencies (the delay lines of ot_hgi_hc_tail_static)
    reg active;
    reg [8:0] age;
    reg [31:0] t[0:23],b[0:23],s[0:2],mx[0:3];
    reg [767:0] final_result;
    assign result=final_result;
    assign e_ready=active&&(age==EREADY);

    // ---------------------------------------------------------------- next {active, age} (the counter's own update)
    wire       n_act = sink_capture ? 1'b0 : (launch ? 1'b1 : active);
    wire [8:0] n_age = launch ? 9'd1 : ((active && age < 9'(EREADY+1)) ? age + 9'd1 : age);
    // issue index of a window [p, p + n) at age a: a - p (valid when inside)
    function automatic win(input act_, input [8:0] a, input integer p, input integer n);
        win = act_ && (a >= 9'(p)) && (a < 9'(p + n));
    endfunction
    // one-hot decodes of the NEXT state (registered below -> decodes of the current state)
    reg [23:0] d_sm, d_sa, d_sx, d_sd, d_sb, d_wm, d_wa, d_we, d_wd;
    reg [3:0]  d_smx; reg [2:0] d_ss; reg d_stwo, d_sone, d_seps, d_mv, d_av, d_xv, d_dv, d_max;
    reg        d_wmv, d_wav, d_wev, d_wdv;
    always @* begin
        d_sm = 0; d_sa = 0; d_sx = 0; d_sd = 0; d_sb = 0; d_wm = 0; d_wa = 0; d_we = 0; d_wd = 0;
        d_smx = 0; d_ss = 0; d_stwo = 0; d_sone = 0; d_seps = 0;
        for (integer j = 0; j < 24; j = j + 1) begin
            // multiplier: p1 (t[j] * s[j < 4 ? 0 : j < 8 ? 1 : 2]); p7, j >= 4 (t[j] * 2.0)
            if (win(n_act, n_age, P1, 24) && n_age - 9'(P1) == 9'(j)) begin
                d_sm[j] = 1'b1; d_ss[(j < 4) ? 0 : (j < 8) ? 1 : 2] = 1'b1;
            end
            if (j >= 4 && j < 8 && win(n_act, n_age, P7, 8) && n_age - 9'(P7) == 9'(j)) begin d_sm[j] = 1'b1; d_stwo = 1'b1; end
            // adder: p2 (t[j] + b[j]); p3 (t[j] - mx[(j - 8) / 4], j = 8 .. 23); p5 (t[j] + 1.0); p7, j < 4 (t[j] + eps)
            if (win(n_act, n_age, P2, 24) && n_age - 9'(P2) == 9'(j)) begin d_sa[j] = 1'b1; d_sb[j] = 1'b1; end
            if (j >= 8 && win(n_act, n_age, P3, 16) && n_age - 9'(P3) + 9'd8 == 9'(j)) begin
                d_sa[j] = 1'b1;
                d_smx[(MUT == 1 && (j - 8) / 4 == 1) ? 0 : (j - 8) / 4] = 1'b1;
            end
            if (j < 8 && win(n_act, n_age, P5, 8) && n_age - 9'(P5) == 9'(j)) begin d_sa[j] = 1'b1; d_sone = 1'b1; end
            if (j < 4 && win(n_act, n_age, P7, 8) && n_age - 9'(P7) == 9'(j)) begin d_sa[j] = 1'b1; d_seps = 1'b1; end
            // exp: p4 (j < 8 ? -t[j] : t[j]); divider: p6 (1.0 / t[j])
            if (win(n_act, n_age, P4, 24) && n_age - 9'(P4) == 9'(j)) d_sx[j] = 1'b1;
            if (j < 8 && win(n_act, n_age, P6, 8) && n_age - 9'(P6) == 9'(j)) d_sd[j] = 1'b1;
            // write-backs: issue age + unit latency (the same windows shifted)
            if (win(n_act, n_age, P1 + DM, 24) && n_age - 9'(P1 + DM) == 9'(j)) d_wm[j] = 1'b1;
            if (j >= 4 && j < 8 && win(n_act, n_age, P7 + DM, 8) && n_age - 9'(P7 + DM) == 9'(j)) d_wm[j] = 1'b1;
            if (win(n_act, n_age, P2 + DA, 24) && n_age - 9'(P2 + DA) == 9'(j)) d_wa[j] = 1'b1;
            if (j >= 8 && win(n_act, n_age, P3 + DA, 16) && n_age - 9'(P3 + DA) + 9'd8 == 9'(j)) d_wa[j] = 1'b1;
            if (j < 8 && win(n_act, n_age, P5 + DA, 8) && n_age - 9'(P5 + DA) == 9'(j)) d_wa[j] = 1'b1;
            if (j < 4 && win(n_act, n_age, P7 + DA, 8) && n_age - 9'(P7 + DA) == 9'(j)) d_wa[j] = 1'b1;
            if (win(n_act, n_age, P4 + DE, 24) && n_age - 9'(P4 + DE) == 9'(j)) d_we[j] = 1'b1;
            if (j < 8 && win(n_act, n_age, P6 + DD, 8) && n_age - 9'(P6 + DD) == 9'(j)) d_wd[j] = 1'b1;
        end
        d_mv = |d_sm; d_av = |d_sa; d_xv = |d_sx; d_dv = |d_sd;
        d_wmv = |d_wm; d_wav = |d_wa; d_wev = |d_we; d_wdv = |d_wd;
        d_max = n_act && (n_age == 9'(MAX));
    end
    (* keep = "true" *) reg [23:0] sm, sa, sx, sd, sb, wm, wa, we, wd;
    (* keep = "true" *) reg [3:0]  smx;
    (* keep = "true" *) reg [2:0]  ss;
    (* keep = "true" *) reg stwo, sone, seps, mv, av, xv, dv, q_max, wmv, wav, wev, wdv;
    always @(posedge clk) begin
        sm <= d_sm; sa <= d_sa; sx <= d_sx; sd <= d_sd; sb <= d_sb; wm <= d_wm; wa <= d_wa; we <= d_we; wd <= d_wd;
        smx <= d_smx; ss <= d_ss; stwo <= d_stwo; sone <= d_sone; seps <= d_seps;
        mv <= d_mv; av <= d_av; xv <= d_xv; dv <= d_dv; q_max <= d_max;
        wmv <= d_wmv; wav <= d_wav; wev <= d_wev; wdv <= d_wdv;
    end

    // ---------------------------------------------------------------- AND-OR operand selects
    reg [31:0] ma, mb, aa, ab, xa, da;
    always @* begin
        ma = 0; aa = 0; xa = 0; da = 0;
        for (integer j = 0; j < 24; j = j + 1) begin
            ma = ma | ({32{sm[j]}} & t[j]);
            aa = aa | ({32{sa[j]}} & t[j]);
            xa = xa | ({32{sx[j]}} & (t[j] ^ ((j < 8) ? 32'h80000000 : 32'h0)));
            da = da | ({32{sd[j]}} & t[j]);
        end
        mb = ({32{ss[0]}} & s[0]) | ({32{ss[1]}} & s[1]) | ({32{ss[2]}} & s[2]) | ({32{stwo}} & 32'h40000000);
        ab = ({32{sone}} & 32'h3f800000) | ({32{seps}} & (MUT_PRE ? 32'd0 : HC_EPS));
        for (integer j = 0; j < 24; j = j + 1) ab = ab | ({32{sb[j]}} & b[j]);
        for (integer r = 0; r < 4; r = r + 1) ab = ab | ({32{smx[r]}} & (mx[r] ^ 32'h80000000));
    end
    wire [31:0] ey,dy,my,ay;
    wire mo,ao,eo,do_,ef,df;
    wire [1:0] me,ae;
    ot_hdc_fp32_mul_fast mul(.clk(clk),.rst_n(rst_n),.valid_in(mv),.a(ma),.b(mb),.y(my),.err(me),.valid_out(mo));
    ot_hdc_fp32_add_fast add(.clk(clk),.rst_n(rst_n),.valid_in(av),.a(aa),.b(ab),.y(ay),.err(ae),.valid_out(ao));
    ot_hdc_v41x_exp #(.LM(3),.LA(3)) exp_(.clk(clk),.rst_n(rst_n),.v(xv),.x(xa),.y(ey),.vo(eo),.fault(ef));
    ot_hdc_v41x_fdiv div_(.clk(clk),.rst_n(rst_n),.v(dv),.a(32'h3f800000),.b(da),.y(dy),.vo(do_),.fault(df));
    function automatic greater(input [31:0] a,c);
        if(a[30:0]==0&&c[30:0]==0)greater=0;
        else if(a[31]!=c[31])greater=!a[31];
        else greater=a[31]?(a[30:0]<c[30:0]):(a[30:0]>c[30:0]);
    endfunction
    wire [511:0] se,sy;
    for(genvar j=0;j<16;j=j+1)assign se[j*32+:32]=t[j+8];
    wire sr,sv,sf,sbusy;
    ot_hdc_sinkhorn #(.ITERS(ITERS),.EPS(HC_EPS)) sink(
        .clk(sink_clk),.rst_n(rst_n),.in_valid(sink_launch),.in_ready(sr),
        .in_e(se),.out_valid(sv),.y(sy),.fault(sf),.busy(sbusy));
    reg sink_fault;
    always @(posedge sink_clk or negedge rst_n)begin
        if(!rst_n)sink_fault<=0;
        else if((sink_launch&&!sr)||sf)sink_fault<=1;
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin active<=0;age<=0;fault<=0;result_v<=0;end
        else begin
            result_v<=sink_capture;
            if(active&&age<EREADY+1)age<=age+1'b1;
            if(launch)begin
                age<=1;active<=1;
                if(active)fault<=1;
            end
            if((mo&&(|me))||(ao&&(|ae))||(eo&&ef)||(do_&&df)||sink_fault)fault<=1;
            if((mo!=wmv)||(ao!=wav)||(eo!=wev)||(do_!=wdv))fault<=1;     // static write calendar check
            if(sink_capture)begin
                if(!active||age<EREADY||!sv||sf)fault<=1;
                active<=0;
            end
        end
    end
    always @(posedge clk)begin
        for(integer j=0;j<24;j=j+1)begin
            if(launch)begin t[j]<=mixes[j*32+:32];b[j]<=bases[j*32+:32];end
            if(wm[j])t[j]<=my;
            if(wa[j])t[j]<=ay;
            if(we[j])t[j]<=ey;
            if(wd[j])t[j]<=dy;
        end
        if(launch)for(integer j=0;j<3;j=j+1)s[j]<=scales[j*32+:32];
        if(q_max)for(integer r=0;r<4;r=r+1)begin:maximum
            reg [31:0] v;
            v=t[8+4*r];
            for(integer c=1;c<4;c=c+1)if(greater(t[8+4*r+c],v))v=t[8+4*r+c];
            mx[r]<=v;
        end
        if(sink_capture)begin
            for(integer j=0;j<8;j=j+1)final_result[j*32+:32]<=t[j];
            final_result[256+:512]<=sy;
        end
    end
endmodule
`default_nettype wire
