`timescale 1ns/1ps
`default_nettype none
// The landing macro and raw/extract/decode stages form one independent leaf.
// Both directions cross actual pin registers. Write/read requests come from
// the mover's registered LW/P1 stages; its reservation stays charged until W.
module ot_hgi_b2_dma_land_dp(
 input wire clk,rst_n,input wire [264:0] land_write,
 input wire [63:0] land_read,input wire [6:0] source_format,
 output wire [306:0] decoded
);
 reg [263:0] write_q;reg write_v;
 reg [62:0] read_q;reg read_v;reg [6:0] format_q;
 wire [255:0] macro_data;
 reg pr_v,raw_v,px_v,p2_v;
 reg [54:0] pr_meta,raw_meta;reg [49:0] px_meta,p2_meta;
 reg [6:0] raw_format,px_format;
 reg [255:0] raw_data,px_data,p2_data;
 assign decoded={p2_v,p2_meta,p2_data};
 ot_sram_1r1w_256x256_m2_r2c2 u_land(.clk(clk),.r_ce_in(read_v),.r_addr_in(read_q[62:55]),
  .rd_out(macro_data),.w_ce_in(write_v),.w_addr_in(write_q[263:256]),.wd_in(write_q[255:0]),
  .w_mask_in({256{1'b1}}),.rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
    function automatic [31:0] i8_f(input [7:0] c);               // INT8 -> binary32 (exact)
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);             // FP8 E4M3 -> binary32 (exact; NaN code -> qNaN)
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
 reg [255:0] extracted,converted;
 always @*begin
  extracted=0;
  for(integer j=0;j<8;j=j+1)begin:extract
   reg [4:0] off;reg [31:0] w;
   off=raw_meta[50:46]+(5'(j)<<raw_format[1:0]);
   w=raw_data[{off[4:2],5'd0} +:32];
   extracted[j*32 +:32]=raw_format[1:0]==2'd2 ? w:raw_format[1:0]==2'd1 ? 
    {16'd0,off[1]?w[31:16]:w[15:0]}:{24'd0,w[{off[1:0],3'd0} +:8]};
  end
  converted=0;
  for(integer j=0;j<8;j=j+1)begin:convert
   reg [31:0] r;r=px_data[j*32 +:32];
   if(px_format[6:5]==2'd1)converted[j*32 +:32]=r;
   else case(px_format[4:2])
    3'd1:converted[j*32 +:32]={r[15:0],16'd0};
    3'd2:converted[j*32 +:32]=e4m3_f(r[7:0]);
    3'd4:converted[j*32 +:32]=i8_f(r[7:0]);
    default:converted[j*32 +:32]=r;
   endcase
  end
 end
 always @(posedge clk)begin
  write_q<=land_write[263:0];read_q<=land_read[62:0];format_q<=source_format;
  if(read_v)pr_meta<=read_q[54:0];
  if(pr_v)begin raw_data<=macro_data;raw_meta<=pr_meta;raw_format<=format_q;end
  if(raw_v)begin px_data<=extracted;px_meta<={raw_meta[54:51],raw_meta[45:0]};px_format<=raw_format;end
  if(px_v)begin p2_data<=converted;p2_meta<=px_meta;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin write_v<=0;read_v<=0;pr_v<=0;raw_v<=0;px_v<=0;p2_v<=0;end
  else begin
   write_v<=land_write[264];read_v<=land_read[63];
   pr_v<=read_v;raw_v<=pr_v;px_v<=raw_v;p2_v<=px_v;
  end
 end
endmodule
`default_nettype wire
