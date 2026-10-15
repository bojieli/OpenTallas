`timescale 1ns/1ps
`default_nettype none
// Actual parser of the granted64bit KV_DESC input. Two32bit row-base LINE
// addresses preserve the grant's4bytes/row. These are not opcodes/programmes.
// Separate static calendar controls load/selection/line/tag and exact request
// edges. No ready, arbitration or runtime retry. The own-stack physical request
// port supplies the home; no other stack selector is inferred from address bits.
module ot_hbm_sm_kv_desc_static #(parameter integer MUT=0)(
    input wire clk,rst_n,
    input wire [63:0] kv_desc,
    input wire [1:0] load_mask,
    input wire request_v,request_entry,h128,
    input wire [1:0] request_line,
    input wire [9:0] request_tag,
    output reg req_v,
    output reg [31:0] req_addr,
    output reg [9:0] req_tag,
    output reg fault
);
    reg [31:0] row_base[0:1];
    reg [1:0] row_valid;
    reg [1:0] next_line[0:1];
    wire last_line=h128 ? request_line==0 : request_line==3;
    wire [32:0] address={1'b0,row_base[request_entry]}+{31'd0,request_line};
    integer k;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin row_valid<=0;next_line[0]<=0;next_line[1]<=0;req_v<=0;fault<=0;end
        else begin
            req_v<=request_v;
            if(request_v)begin
                req_addr<=address[31:0] ^ ((MUT==1)?32'd1:32'd0);req_tag<=request_tag;
                if(!row_valid[request_entry] || request_line!=next_line[request_entry] ||
                   (h128 && request_line!=0) || address[32])fault<=1;
                if(last_line)begin row_valid[request_entry]<=0;next_line[request_entry]<=0;end
                else next_line[request_entry]<=next_line[request_entry]+1;
            end
            // Simultaneous final old-row request and next pair load are legal:
            // the registered request reads the old base, the new pair wins here.
            for(k=0;k<2;k=k+1)if(load_mask[k])begin
                if(row_valid[k] && !(request_v && request_entry==k && last_line))fault<=1;
                row_base[k]<=kv_desc[32*k+:32];row_valid[k]<=1;next_line[k]<=0;
            end
        end
endmodule
`default_nettype wire
