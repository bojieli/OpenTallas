`timescale 1ns/1ps
// Actual mapped calendar SRAM. Boot is exceptional initialization; execution
// performs one fixed read per edge, never a demand/ready transaction.  Two
// 512-bit banks form a 1024-bit instruction; no unrestricted behavioral store.
// ctl executes cycle 0 on the edge AFTER arm: the arm edge fetches word 0.
// Subsequent edges fetch cycle+1 while ctl consumes the previous macro output.
module ot_s81_su_calendar_store #(
    parameter integer DEPTH=4096,
    parameter integer AW=(DEPTH>64)?$clog2(DEPTH):6
)(
    input wire clk,rst_n,
    input wire arm,running,
    input wire [31:0] cycle,
    input wire boot_we,boot_commit,
    input wire [AW-1:0] boot_addr,
    input wire [3:0] boot_lane,
    input wire [63:0] boot_data,
    output wire [1023:0] calendar_word,
    output reg program_valid,
    output reg fault
);
    wire [AW-1:0] read_addr=running?AW'(cycle+1):{AW{1'b0}};
    genvar b,l;
    generate for(b=0;b<2;b=b+1)begin:g_b
        wire [511:0] data,mask;
        for(l=0;l<8;l=l+1)begin:g_l
            assign data[64*l+:64]=boot_data;
            assign mask[64*l+:64]=(boot_lane==b*8+l)?64'hffffffffffffffff:64'd0;
        end
        ot_sram_bank #(.DEPTH(DEPTH),.AW(AW)) u_bank(.clk(clk),
            .we(boot_we && !running),.wa(boot_addr),.wd(data),.wm(mask),
            .re(arm || running),.ra(read_addr),.q(calendar_word[512*b+:512]));
    end endgenerate
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin program_valid<=0;fault<=0;end
        else begin
            if(boot_we)program_valid<=0;
            if(boot_commit && !running)program_valid<=1;
            if((boot_we || boot_commit) && running)fault<=1;
            if(running && cycle>=DEPTH)fault<=1;
        end
    end
    initial if(DEPTH<64 || (DEPTH&(DEPTH-1))!=0)$fatal(1,"calendar DEPTH must be power-of-two >=64");
endmodule
