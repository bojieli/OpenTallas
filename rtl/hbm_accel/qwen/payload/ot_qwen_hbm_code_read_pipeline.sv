`timescale 1ps/1fs
// Fixed two-edge, II=1 CODE bank/valid pipeline. No payload registers/queue.
// rd_fire MUST be actual leaf rd_v && rd_r, after installed/published span
// authorization. Caller must detect an issued-but-unaccepted ME read itself.
// Virtual bank0..4 is a response tag only; no physical-row translation here.
// Caller consumes every valid response, drains before turnover, and owns the
// original optional MEM_EXTRA capture plus matching tag/x/KV delay of +1.
module ot_qwen_hbm_code_read_pipeline #(
  parameter integer ENABLE=0
)(
  input wire clk, por_n,
  input wire [1:0] rd_fire,
  input wire [5:0] virtual_bank,
  input wire [1:0] leaf_rd_rsp_v,
  input wire [511:0] leaf_rd_data,
  input wire leaf_fault,
  output wire [2659:0] rom_rd,
  output wire [1:0] rsp_v,
  output wire fault
);
  import ot_gpu_w6_secded_pkg::*;
  generate if (!ENABLE) begin : off
    assign rom_rd=0; assign rsp_v=0; assign fault=0;
  end else begin : on
    typedef struct packed {
      logic sticky;
      logic [1:0] v1, v2;
      logic [5:0] bank1, bank2;
    } control_t;
    reg [71:0] control_code;
    wire [65:0] decoded=decode64(control_code);
    control_t c, n;
    assign c=decoded[$bits(control_t)-1:0];
    wire control_bad=decoded[65] || (|decoded[63:$bits(control_t)]);
    wire response_bad=(leaf_rd_rsp_v!=c.v2);
    wire [1:0] request_bad;
    for(genvar p=0;p<2;p=p+1) begin : column
      assign request_bad[p]=rd_fire[p] && (virtual_bank[p*3+:3]>=5);
      assign rsp_v[p]=c.v2[p] && leaf_rd_rsp_v[p] && !fault;
      for(genvar b=0;b<5;b=b+1) begin : bank
        assign rom_rd[(p*5+b)*266+:266]=
          (rsp_v[p] && c.bank2[p*3+:3]==b) ?
          {10'b0,leaf_rd_data[p*256+:256]} : 266'b0;
      end
    end
    // Match both columns exactly, including bubbles. A mismatched response
    // never becomes a successful zero payload; fault persists until cold reset.
    assign fault=c.sticky || control_bad || leaf_fault || response_bad || (|request_bad);
    always @* begin
      n=c;
      n.v1=rd_fire;
      n.v2=c.v1;
      for(integer p=0;p<2;p=p+1) begin
        if(rd_fire[p]) n.bank1[p*3+:3]=virtual_bank[p*3+:3];
        if(c.v1[p]) n.bank2[p*3+:3]=c.bank1[p*3+:3];
      end
      if(control_bad || leaf_fault || response_bad || (|request_bad)) n.sticky=1;
    end
    always @(posedge clk or negedge por_n) begin
      if(!por_n) control_code<=encode64(64'b0);
      else if(!control_bad) control_code<=encode64(64'(n));
    end
  end endgenerate
endmodule
