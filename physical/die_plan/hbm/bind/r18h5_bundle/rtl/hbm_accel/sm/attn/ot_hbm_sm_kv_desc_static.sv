`timescale 1ns/1ps
`default_nettype none
// ot_hbm_sm_kv_desc_static: the SM's 64-bit KV_DESC port (v15 contract attention_on_sm, driven by the quadrant VM hub)
// for CANONICAL packed KV rows (H-SM-ATT r2 2026-10-15; replaces the 4-lines-a-row pair descriptor of the 544-B layout).
// An op's rows lie back to back in the SM's own stack, so one descriptor is one contiguous LINE RUN:
//   kv_desc[31:0]  = first 136-B line address of the run (own stack; no stack selector is inferred from address bits)
//   kv_desc[47:32] = lines in the run (>= 1)        kv_desc[63:48] = 0 (reserved: non-zero is a fault)
// load (compiler slot) installs the run; every request slot (compiler slot) emits the next line address with its tag,
// registered.  No ready, arbitration or retry: a request with no line left, a load over an unfinished run or a
// malformed descriptor is a sticky fault and never reschedules.  MUT 1 = address off by one line (bench negative control).
module ot_hbm_sm_kv_desc_static #(parameter integer MUT=0)(
    input wire clk,rst_n,
    input wire [63:0] kv_desc,
    input wire load,
    input wire request_v,
    input wire [9:0] request_tag,
    output reg req_v,
    output reg [31:0] req_addr,
    output reg [9:0] req_tag,
    output reg fault
);
    reg [31:0] next_line;
    reg [15:0] left;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin left<=0;req_v<=0;fault<=0;next_line<=0;end
        else begin
            req_v<=request_v;
            if(request_v)begin
                req_addr<=next_line ^ ((MUT==1)?32'd1:32'd0);req_tag<=request_tag;
                if(left==0 || load)fault<=1;
                next_line<=next_line+32'd1;left<=left-16'd1;
            end
            if(load)begin
                if(left!=0 || kv_desc[47:32]==0 || kv_desc[63:48]!=0)fault<=1;
                next_line<=kv_desc[31:0];left<=kv_desc[47:32];
            end
        end
endmodule
`default_nettype wire
