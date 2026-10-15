`timescale 1ns/1ps
// CP (SU kind14): ratio-two compressor pooling. All arithmetic is target RTL.
// Each beat carries four FP32 kv values in bits127:0, four FP32 scores in255:128.
// Two actual128x256 SRAM macros hold the two512-dimensional kv/score slots.
// Compiler reserves128 consecutive input beats beginning IN_CYCLE after start.
// No READY/credit/variable completion exists. Missing/extra beats, wrong history
// identity, overlapping start or late output are faults, never rescheduling.
module ot_s81_su_cp #(parameter integer IN_CYCLE=10,MUT=0) (
    input wire clk,
    input wire rst_n,start,slot_i,pool_i,
    input wire [31:0] group_i,
    input wire i_v,
    input wire [255:0] i_d,
    output wire o_v,
    output wire [127:0] o_d,
    output wire done,fault,active,
    output wire [15:0] scheduled_cycles
);
    // Single-clock functional composition. The native physical parent below
    // exposes every independently delivered child clock pin explicitly.
    ot_s81_su_cp_h #(.IN_CYCLE(IN_CYCLE),.MUT(MUT)) u_h (
        .ck_ctl(clk),.ck_mem({2{clk}}),.ck_lane({4{clk}}),.rst_n(rst_n),
        .start(start),.slot_i(slot_i),.pool_i(pool_i),.group_i(group_i),.i_v(i_v),.i_d(i_d),
        .o_v(o_v),.o_d(o_d),.done(done),.fault(fault),.active(active),.scheduled_cycles(scheduled_cycles));
endmodule

module ot_s81_su_cp_h #(parameter integer IN_CYCLE=10,MUT=0) (
    input wire ck_ctl,
    input wire [1:0] ck_mem,
    input wire [3:0] ck_lane,
    input wire rst_n,start,slot_i,pool_i,
    input wire [31:0] group_i,
    input wire i_v,
    input wire [255:0] i_d,
    output wire o_v,
    output wire [127:0] o_d,
    output wire done,fault,active,
    output wire [15:0] scheduled_cycles
);
    // Wires-only parent: all mutable state belongs to named controller,
    // SRAM or arithmetic children. Die clocks must be delivered at phi-R.
    wire [255:0] old0,old1,mem_wd,previous,current;
    wire [1:0] mem_we,mem_re;
    wire [6:0] mem_addr;
    wire slot,lv_in;
    wire [3:0] lv,lf;
    ot_s81_su_cp_ctl #(.IN_CYCLE(IN_CYCLE)) u_ctl (
        .clk(ck_ctl),.rst_n(rst_n),.start(start),.slot_i(slot_i),.pool_i(pool_i),.group_i(group_i),
        .i_v(i_v),.i_d(i_d),.mem0_q(old0),.mem1_q(old1),.lv(lv),.lf(lf),
        .mem_we(mem_we),.mem_re(mem_re),.mem_addr(mem_addr),.mem_wd(mem_wd),.slot(slot),
        .lane_v(lv_in),.previous(previous),.current(current),.done(done),.fault(fault),
        .active(active),.scheduled_cycles(scheduled_cycles));
    genvar b,l;
    generate for(b=0;b<2;b=b+1) begin:g_bank
        wire [255:0] q;
        if(b==0)assign old0=q;else assign old1=q;
        ot_sram_1r1w_128x256_m1_r2c2 u_sram (
            .clk(ck_mem[b]),.r_ce_in(mem_re[b]),.r_addr_in(mem_addr),.rd_out(q),
            .w_ce_in(mem_we[b]),.w_addr_in(mem_addr),.wd_in(mem_wd),.w_mask_in({256{1'b1}}),
            .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
    end
    for(l=0;l<4;l=l+1) begin:g_lane
        ot_s81_su_cp_lane #(.MUT(MUT)) u_lane (
            .clk(ck_lane[l]),.rst_n(rst_n),.i_v(lv_in),
            .kv0(previous[32*l+:32]),.sc0(previous[128+32*l+:32]),
            .kv1(current[32*l+:32]),.sc1(current[128+32*l+:32]),
            .o_v(lv[l]),.o_d(o_d[32*l+:32]),.fault(lf[l]));
    end endgenerate
    assign o_v=lv[0];
endmodule

module ot_s81_su_cp_ctl #(parameter integer IN_CYCLE=10) (
    input wire clk,rst_n,start,slot_i,pool_i,
    input wire [31:0] group_i,
    input wire i_v,
    input wire [255:0] i_d,mem0_q,mem1_q,
    input wire [3:0] lv,lf,
    output wire [1:0] mem_we,mem_re,
    output wire [6:0] mem_addr,
    output wire [255:0] mem_wd,
    output reg slot,
    output wire lane_v,
    output wire [255:0] previous,current,
    output reg done,fault,active,
    output wire [15:0] scheduled_cycles
);
    localparam integer BEATS=128, LANE_LAT=132, READ_LAT=1;
    localparam integer STORE_END=IN_CYCLE+BEATS;
    localparam integer POOL_END=IN_CYCLE+BEATS+READ_LAT+LANE_LAT;
    reg pool;
    reg [31:0] group;
    reg [15:0] age;
    reg [1:0] valid_slot;
    reg [31:0] owner [0:1];
    reg [8:0] nout;
    wire reserved=active && age>=IN_CYCLE && age<STORE_END;
    wire [6:0] row=7'(age-IN_CYCLE);
    wire [255:0] old0=mem0_q,old1=mem1_q;
    assign mem_addr=row;
    assign mem_wd=i_d;
    assign mem_we={2{reserved}} & {slot,~slot};
    assign mem_re={2{reserved && pool}} & {~slot,slot};
    reg input_q;
    reg [255:0] current_q;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) input_q<=0;
        else input_q<=reserved && pool;
    always @(posedge clk) current_q<=i_d;
    wire [255:0] history=slot?old0:old1;
    assign lane_v=input_q;
    assign previous=history;
    assign current=current_q;
    assign scheduled_cycles=pool?POOL_END:STORE_END;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin active<=0;age<=0;valid_slot<=0;fault<=0;done<=0;nout<=0;slot<=0;pool<=0;group<=0;end
        else begin
            done<=0;
            if(|lf || (lv!={4{lv[0]}})) fault<=1;
            if(start) begin
                if(active) fault<=1;
                active<=1;age<=1;slot<=slot_i;pool<=pool_i;group<=group_i;nout<=0;
                if(pool_i && (!valid_slot[!slot_i] || owner[!slot_i]!=group_i)) fault<=1;
            end else if(active) begin
                age<=age+1;
                if(i_v!=reserved) fault<=1;
                if(reserved && age==STORE_END-1) begin valid_slot[slot]<=1;owner[slot]<=group;end
                if(lv[0]) nout<=nout+1;
                if(age==scheduled_cycles) begin
                    active<=0;done<=1;
                    if(pool && nout+lv[0]!=128) fault<=1;
                end
            end else if(i_v || lv[0]) fault<=1;
        end
    end
endmodule

// Four independent copies are instantiated; every lane accepts one dimension/cycle.
// m=max(sc0,sc1); e=exp(sc-m); p=e/(e0+e1); BF16(kv0*p0+kv1*p1).
// Rounding/order match Model.compressor; both products are rounded before addition.
module ot_s81_su_cp_lane #(parameter integer MUT=0) (
    input wire clk,rst_n,i_v,
    input wire [31:0] kv0,kv1,sc0,sc1,
    output wire o_v,
    output reg [31:0] o_d,
    output wire fault
);
    localparam integer A=5,E=76,D=33,M=6;
    function automatic [31:0] key(input [31:0] x);
        key=x[31]?~x:(x^32'h80000000);
    endfunction
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] y;
        begin y={1'b0,x}+33'h7fff+{32'd0,x[16]};bf16={y[31:16],16'd0};end
    endfunction
    reg vq;
    reg [31:0] mq,s0q,s1q,k0q,k1q;
    always @(posedge clk or negedge rst_n) if(!rst_n) vq<=0;else vq<=i_v;
    always @(posedge clk) begin
        mq<=key(sc0)>=key(sc1)?sc0:sc1;
        s0q<=sc0;s1q<=sc1;k0q<=kv0;k1q<=kv1;
    end
    wire [A:0] av;
    ot_hdc_vline #(.D(A)) u_av(clk,rst_n,vq,av);
    wire [31:0] sub0,sub1,e0,e1,den,p0,p1,t0,t1,sum;
    wire af0,af1,ef0,ef1,df,pf0,pf1,mf0,mf1,sf;
    wire ev0,ev1,pv0,pv1;
    ot_dsrom_qadd #(.LAT(A)) u_sub0(clk,rst_n,vq,s0q,{!mq[31],mq[30:0]},sub0,af0);
    ot_dsrom_qadd #(.LAT(A)) u_sub1(clk,rst_n,vq,s1q,{!mq[31],mq[30:0]},sub1,af1);
    ot_dsrom_exp_f12 #(.LM(5),.LA(4)) u_exp0(clk,rst_n,av[A],sub0,e0,ev0,ef0);
    ot_dsrom_exp_f12 #(.LM(5),.LA(4)) u_exp1(clk,rst_n,av[A],sub1,e1,ev1,ef1);
    ot_dsrom_qadd #(.LAT(A)) u_den(clk,rst_n,ev0,e0,e1,den,df);
    wire [31:0] en0,en1;
    ot_hdc_delay #(.W(32),.D(A)) u_en0(clk,rst_n,e0,en0);
    ot_hdc_delay #(.W(32),.D(A)) u_en1(clk,rst_n,e1,en1);
    wire [A:0] dv;
    ot_hdc_vline #(.D(A)) u_dv(clk,rst_n,ev0,dv);
    ot_dsrom_su_fdiv_f12 u_div0(clk,rst_n,dv[A],en0,den,p0,pv0,pf0);
    ot_dsrom_su_fdiv_f12 u_div1(clk,rst_n,dv[A],en1,den,p1,pv1,pf1);
    wire [31:0] k0,k1;
    ot_hdc_delay #(.W(32),.D(A+E+A+D)) u_k0(clk,rst_n,k0q,k0);
    ot_hdc_delay #(.W(32),.D(A+E+A+D)) u_k1(clk,rst_n,k1q,k1);
    ot_hdc_qmul_lat #(M) u_mul0(clk,rst_n,pv0,k0,p0,t0,mf0);
    ot_hdc_qmul_lat #(M) u_mul1(clk,rst_n,pv1,k1,p1,t1,mf1);
    wire [M+A:0] ov;
    ot_hdc_vline #(.D(M+A)) u_ov(clk,rst_n,pv0,ov);
    ot_dsrom_qadd #(.LAT(A)) u_sum(clk,rst_n,ov[M],t0,(MUT==1)?32'd0:t1,sum,sf);
    reg outv;
    always @(posedge clk or negedge rst_n) if(!rst_n)outv<=0;else outv<=ov[M+A];
    always @(posedge clk) o_d<=bf16(sum);
    assign o_v=outv;
    assign fault=af0|af1|ef0|ef1|df|pf0|pf1|mf0|mf1|sf|(ev0^ev1)|(pv0^pv1);
endmodule
