`timescale 1ns/1ps
`default_nettype none
// Timestamped native QDQ record programme. One word per operation rather than
// one word per beat or idle clock. Absolute timestamps determine production
// issue. No result status, ready, credit or dynamic dependency wait is read.
// Payload: start31:0, beats47:32, src63:48, dst79:64, op85:80, block93:86.
// Magic255:240=c7a1, PC233:224; all other bits zero. Real mapped SRAM only.
// One record prefetched at first beat; supported records have >=4 beats.
module ot_hgi_qdq_record_calendar #(
    parameter integer MUT=0 //1 wrong source;2 delayed timestamp
)(
    input wire clk,rst_n,cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    output reg command_v,
    output reg [47:0] command,
    output reg [31:0] cycle,
    output reg active,done,fault
);
    reg cfg_q,start_q;
    reg [9:0] ca,base_q;
    reg [10:0] limit_q;
    reg [255:0] cd;
    always @(posedge clk)begin ca<=cfg_addr;cd<=cfg_data;base_q<=start_base;limit_q<=start_limit;end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin cfg_q<=0;start_q<=0;end
        else begin cfg_q<=cfg_we;start_q<=start_v;end
    reg running,have,waiting;
    reg [9:0] next_pc;
    reg [10:0] limit;
    reg [93:0] current,pending;
    reg pending_v;
    reg [15:0] beat;
    wire due=running && have && cycle>=current[31:0] && beat<current[47:32];
    wire first=due && beat==0;
    wire last=due && beat+16'd1==current[47:32];
    wire more={1'b0,next_pc}<limit;
    wire legal_launch=!running && !cfg_q && limit_q>{1'b0,base_q} && limit_q<=1024;
    wire read_start=start_q && legal_launch;
    wire read_next=first && more;
    wire read_v=read_start|read_next;
    wire [9:0] read_addr=read_start?base_q:next_pc;
    wire [255:0] macro_word;
    ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk),.r_ce_in(read_v),.r_addr_in(read_addr),.rd_out(macro_word),
        .w_ce_in(cfg_q&&!running&&!start_q),.w_addr_in(ca),.wd_in(cd),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    reg rv0,rv1;
    reg [9:0] pc0,pc1;
    reg [255:0] captured;
    always @(posedge clk)begin captured<=macro_word;pc0<=read_addr;pc1<=pc0;end
    wire word_ok=captured[255:240]==16'hc7a1 && captured[233:224]==pc1 &&
        captured[239:234]==0 && captured[223:94]==0 && captured[47:32]>=4 &&
        (captured[85:80]==4 || captured[85:80]==5 || (captured[85:80]==6 && captured[93:86]==16));
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            running<=0;have<=0;waiting<=0;pending_v<=0;beat<=0;next_pc<=0;limit<=0;
            rv0<=0;rv1<=0;command_v<=0;cycle<=0;active<=0;done<=0;fault<=0;
        end else begin
            rv0<=read_v;rv1<=rv0;command_v<=0;done<=0;active<=running;
            if(cfg_q&&running)fault<=1;
            if(start_q)begin
                if(!legal_launch)fault<=1;
                else begin running<=1;cycle<=0;have<=0;pending_v<=0;waiting<=1;
                    next_pc<=base_q+1'b1;limit<=limit_q;beat<=0;end
            end else if(running)cycle<=cycle+1;
            if(read_next)next_pc<=next_pc+1'b1;
            if(rv1)begin
                if(!word_ok)fault<=1;
                if(waiting)begin current<=captured[93:0];have<=1;waiting<=0;beat<=0;end
                else begin pending<=captured[93:0];pending_v<=1;end
            end
            if(due)begin
                command_v<=1;
                command<={(beat+16'd1==current[47:32]),current[79:64]+16'(beat*4),
                    current[63:48]+16'(beat*4)+(MUT==1?16'd1:16'd0),current[93:86],current[85:80],1'b1};
                if(cycle!=current[31:0]+32'(beat)+(MUT==2?32'd1:32'd0))fault<=1;
                beat<=beat+1'b1;
                if(last)begin
                    if(pending_v)begin current<=pending;pending_v<=0;beat<=0;
                        if(pending[31:0]<=cycle)fault<=1;
                    end else if(!more)begin have<=0;running<=0;done<=1;end
                    else begin have<=0;fault<=1;end
                end
            end
            if(running && have && cycle>current[31:0]+32'(beat))fault<=1;
        end
endmodule
`default_nettype wire
