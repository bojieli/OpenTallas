`timescale 1ps/1fs
// Bounded CODE-only adapter, not a replacement for the tile's issue/stall logic.
// Caller owns physical mapping/publication and must gate leaf rd_v by ready.
// rd_fire is the ACTUAL leaf rd_v && rd_r, not a proposed request.
// Virtual bank0..4 is only a response tag. The installed-span mapper alone
// authorizes physical rows; this adapter never translates or guesses a row.
// Two leaf edges; MEM_EXTRA=1 preserves one further legacy capture edge.
module ot_qwen_hbm_code_read_align #(
  parameter integer ENABLE=0, MEM_EXTRA=0
)(
  input wire clk, por_n, consumer_enable,
  input wire [1:0] rd_fire,
  input wire [5:0] virtual_bank,
  input wire [1:0] leaf_rd_rsp_v,
  input wire [511:0] leaf_rd_data,
  input wire leaf_fault,
  output wire [1:0] consumer_ready,
  output wire [1:0] rsp_v,
  input wire [1:0] rsp_ready,
  output wire [2659:0] rom_rd,
  output wire fault
);
  import ot_gpu_w6_secded_pkg::*;
  generate if (!ENABLE) begin : off
    assign consumer_ready=0; assign rsp_v=0; assign rom_rd=0; assign fault=0;
  end else if (MEM_EXTRA!=0 && MEM_EXTRA!=1) begin : unsupported
    assign consumer_ready=0; assign rsp_v=0; assign rom_rd=0; assign fault=1;
  end else begin : on
    typedef struct packed {
      logic sticky;
      logic [1:0] pending, v1, v2, held;
      logic [5:0] bank1, bank2;
    } control_t;
    reg [71:0] control_code;
    reg [287:0] held_code [0:1];
    wire [65:0] decoded_control=decode64(control_code);
    control_t c, n;
    assign c=decoded_control[$bits(control_t)-1:0];
    wire control_bad=decoded_control[65] || (|decoded_control[63:$bits(control_t)]);
    wire [511:0] held_data;
    wire [1:0] held_bad;
    for(genvar p=0;p<2;p=p+1) begin : column
      wire [3:0] ue;
      for(genvar k=0;k<4;k=k+1) begin : decode
        wire [65:0] d=decode64(held_code[p][k*72+:72]);
        assign held_data[p*256+k*64+:64]=d[63:0];
        assign ue[k]=d[65];
      end
      assign held_bad[p]=c.held[p] && (|ue);
      assign consumer_ready[p]=consumer_enable && !c.pending[p] &&
          (virtual_bank[p*3+:3]<5) && !fault;
      // Bank2 and leaf response both become valid AFTER the second edge.
      wire live=c.v2[p] && leaf_rd_rsp_v[p];
      assign rsp_v[p]=!fault && (c.held[p] || ((MEM_EXTRA==0) && live));
      wire [255:0] data=c.held[p] ? held_data[p*256+:256] : leaf_rd_data[p*256+:256];
      for(genvar b=0;b<5;b=b+1) begin : bank
        // Select the tagged virtual slot, independent of the physical SRAM bank.
        assign rom_rd[(p*5+b)*266+:266]=
            (rsp_v[p] && c.bank2[p*3+:3]==b) ? {10'b0,data} : 266'b0;
      end
      // MEM_EXTRA capture or an elastic hold; existing W6 is the only codec.
      always @(posedge clk) begin
        if(!fault && live && ((MEM_EXTRA==1) || !rsp_ready[p]))
          for(integer k=0;k<4;k=k+1)
            held_code[p][k*72+:72]<=encode64(leaf_rd_data[p*256+k*64+:64]);
      end
    end
    assign fault=leaf_fault || control_bad || c.sticky || (|held_bad);
    always @* begin
      n=c;
      n.v1=rd_fire & consumer_ready;
      n.v2=c.v1;
      for(integer p=0;p<2;p=p+1) begin
        if(rd_fire[p] && consumer_ready[p]) begin
          n.pending[p]=1;
          n.bank1[p*3+:3]=virtual_bank[p*3+:3];
        end
        if(c.v1[p]) n.bank2[p*3+:3]=c.bank1[p*3+:3];
        if(c.v2[p] && leaf_rd_rsp_v[p] && ((MEM_EXTRA==1) || !rsp_ready[p]))
          n.held[p]=1;
        if(rsp_v[p] && rsp_ready[p]) begin
          n.held[p]=0;
          n.pending[p]=0;
        end
      end
      // A rejected request must never have reached the SRAM. Preserve a
      // caller-protocol failure instead of inventing zero payload/idle success.
      if((|(rd_fire & ~consumer_ready)) || (leaf_rd_rsp_v!=c.v2) ||
         leaf_fault || control_bad || (|held_bad)) n.sticky=1;
    end
    always @(posedge clk or negedge por_n) begin
      if(!por_n) control_code<=encode64(64'b0);
      else if(!control_bad) control_code<=encode64(64'(n));
    end
  end endgenerate
endmodule
