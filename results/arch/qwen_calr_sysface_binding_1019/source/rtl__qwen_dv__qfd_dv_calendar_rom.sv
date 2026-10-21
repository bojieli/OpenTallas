`timescale 1ns/1ps
// Default-uninstantiated immutable calendar port. One request/edge, four128b
// entries/read, two real266b ROMs. Pin register -> macro -> capture register;
// no credit, retry or runtime install. Descriptors are generated with masks.
module qfd_dv_calendar_rom #(
    parameter integer NENT=1,
    parameter integer MUT=0
)(
    input wire ck,rst_n,req,
    input wire [9:0] first,
    input wire [2:0] count,
    input wire [1:0] user_id,
    input wire [5:0] stage,
    input wire install, running,
    output reg valid,
    output reg [511:0] data,
    output reg [1:0] out_user,
    output reg [5:0] out_stage,
    output reg [2:0] out_count,
    output reg fault
);
    reg r1,r2;
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin r1<=0;r2<=0;end
        else begin r1<=1;r2<=r1;end
    reg pv,mv;reg [11:0] addr;
    reg [1:0] pu,mu;reg [5:0] ps,ms;reg [2:0] pn,mn;
    wire bad=(NENT<1 || NENT>1023) || first[1:0]!=0 || count==0 || count>4 ||
             ({1'b0,first}+count>NENT) || stage>37;
    wire [531:0] raw;
    ot_rom_4096x266_m8 #(.INSTANCE("calendar_m0")) m0
        (.clk(ck),.ce_in(pv),.addr_in(addr),.rd_out(raw[265:0]));
    ot_rom_4096x266_m8 #(.INSTANCE("calendar_m1")) m1
        (.clk(ck),.ce_in(pv),.addr_in(addr),.rd_out(raw[531:266]));
    always @(posedge ck)begin
        addr<={4'd0,first[9:2]}+((MUT==1)?1:0);
        pu<=user_id;ps<=stage;pn<=count;
        mu<=pu;ms<=ps;mn<=pn;
        data<=(MUT==2)?{raw[255:0],raw[511:256]}:raw[511:0];
        out_user<=(MUT==3)?mu+2'd1:mu;
        out_stage<=(MUT==4)?ms+6'd1:ms;
        out_count<=mn;
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin pv<=0;mv<=0;valid<=0;fault<=0;end
        else if(!r2)begin pv<=0;mv<=0;valid<=0;fault<=0;end
        else begin
            pv<=req&&!bad;mv<=pv;valid<=mv;
            // Immutable means even an idle attempted install is illegal.
            if(install || (req&&bad) || (install&&running))fault<=1;
            if(mv&&raw[531:512]!=0)fault<=1;
        end
endmodule
