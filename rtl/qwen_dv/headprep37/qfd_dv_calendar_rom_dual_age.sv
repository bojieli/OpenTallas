`timescale 1ns/1ps
// Default-uninstantiated immutable calendar port. One request/edge, four128b
// entries/read, two real266b ROMs. Pin register -> macro -> capture register;
// no credit, retry or runtime install. Descriptors are generated with masks.
// QW-CALR 10-20 (depth): the request range check runs on the PIN-REGISTERED request (pf/pn), in parallel with
// the macro read, and gates valid one edge later (mbad) -- it was a 10-bit add+compare in the same cycle as the
// calendar's grant/first mux (CTLM CALR=1 mapped depth 1290 ps / 40 levels). valid/data/out_* edges unchanged; a bad
// request still never returns valid (cal_mu rom_mis faults on that edge as before) and raises `fault` +1 edge later.
module qfd_dv_calendar_rom_dual_age #(
    parameter integer NENT=1,
    parameter integer MUT=0,
    parameter integer COLD_DELTA=0
)(
    input wire ck,rst_n,req,
    input wire [9:0] first,
    input wire [2:0] count,
    input wire [1:0] user_id,
    input wire [5:0] stage,
    input wire install, running,
    output reg valid,
    output wire [511:0] data,
    output reg [1:0] out_user,
    output reg [5:0] out_stage,
    output reg [2:0] out_count,
    output reg fault
);
    reg r1,r2;
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin r1<=0;r2<=0;end
        else begin r1<=1;r2<=r1;end
    reg pv,mv,mbad;reg [11:0] addr;reg [9:0] pf;
    reg [1:0] pu,mu;reg [5:0] ps,ms;reg [2:0] pn,mn;
    wire bad=(NENT<1 || NENT>1023) || pf[1:0]!=0 || pn==0 || pn>4 ||
             ({1'b0,pf}+pn>NENT) || ps>37;
    wire [531:0] raw;
    reg [511:0] captured;
    reg [19:0] codes;
    wire [3:0] invalid_delta;
    generate for (genvar i=0; i<4; i=i+1) begin : g_delta
        if (COLD_DELTA != 0) begin : g_cold
            wire [4:0] code = codes[5*i+:5];
            // Codes 0..29 hold literal flips in the low five delta bits.
            // 30 is the one epoch rebase and 31 restores cold TABLE_NEXT.
            wire [11:0] flips = code == 5'd30 ? 12'h155 :
                                code == 5'd31 ? 12'h300 : {7'd0,code};
            wire cold_active = out_stage == 6'd1;
            wire [11:0] delta = captured[128*i+116+:12] ^
                                (flips & {12{cold_active}});
            assign data[128*i+116+:12] = delta;
            assign data[128*i+:116] = captured[128*i+:116];
            assign invalid_delta[i] = cold_active && (out_count > 3'(i)) &&
                                      delta == 12'd0;
        end else begin : g_default
            assign data[128*i+:128] = captured[128*i+:128];
            assign invalid_delta[i] = 1'b0;
        end
    end endgenerate
    ot_rom_4096x266_m8 #(.INSTANCE("calendar_m0")) m0
        (.clk(ck),.ce_in(pv),.addr_in(addr),.rd_out(raw[265:0]));
    ot_rom_4096x266_m8 #(.INSTANCE("calendar_m1")) m1
        (.clk(ck),.ce_in(pv),.addr_in(addr),.rd_out(raw[531:266]));
    always @(posedge ck)begin
        addr<={4'd0,first[9:2]}+((MUT==1)?1:0);
        pf<=first;pu<=user_id;ps<=stage;pn<=count;
        mu<=pu;ms<=ps;mn<=pn;
        captured<=(MUT==2)?{raw[255:0],raw[511:256]}:raw[511:0];
        if(COLD_DELTA != 0) codes<=raw[531:512];
        out_user<=(MUT==3)?mu+2'd1:mu;
        out_stage<=(MUT==4)?ms+6'd1:ms;
        out_count<=mn;
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin pv<=0;mv<=0;mbad<=0;valid<=0;fault<=0;end
        else if(!r2)begin pv<=0;mv<=0;mbad<=0;valid<=0;fault<=0;end
        else begin
            pv<=req;mv<=pv;mbad<=pv&&bad;valid<=mv&&!mbad;
            // Immutable means even an idle attempted install is illegal.
            if(install || (pv&&bad) || (install&&running))fault<=1;
            if(COLD_DELTA == 0 && mv && raw[531:512]!=0)fault<=1;
            if(COLD_DELTA != 0 && valid && |invalid_delta)fault<=1;
        end
endmodule
