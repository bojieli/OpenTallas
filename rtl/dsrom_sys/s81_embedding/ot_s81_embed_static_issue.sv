// Full-vocabulary compiler-launched fixed-slot ROM issuer. Canonical S81 table
// geometry matches ot_dsrom_s81_embedding (2525 pairs,4x4096 leaves/pair).
// The physical ROM fabric must reserve the addressed leaf each cycle and return
// its 256 payload bits two cycles after req_v. No readiness or credit ports.
// This issuer handles row crossings: address calculation is per word, not once
// per token. ROM timing/identity violations fault without changing the calendar.
module ot_s81_embed_static_issue(
 input wire clk,rst_n,start,input wire [16:0] token,
 output wire req_v,output wire [13:0] req_macro,output wire [11:0] req_row,
 output wire [8:0] req_idx,
 input wire rsp_v,input wire [13:0] rsp_macro,input wire [11:0] rsp_row,
 input wire [255:0] rsp_d,
 output wire rom_v,output wire [8:0] rom_idx,output wire [511:0] rom_d,
 output reg fault
);
 reg active;reg [8:0] index;
 reg [25:0] word_addr;
 reg [1:0] expected_v;
 reg [13:0] expected_macro[0:1];reg [11:0] expected_row[0:1];
 reg [8:0] expected_idx[0:1];
 assign req_v=active;
 assign req_macro={word_addr[25:14],word_addr[13],word_addr[0]};
 assign req_row=word_addr[12:1];
 assign req_idx=index;
 assign rom_v=expected_v[1];
 assign rom_idx=expected_idx[1];
 for(genvar l=0;l<16;l=l+1)begin: unpack_bf16
   assign rom_d[32*l+:32]={rsp_d[16*l+:16],16'b0};
 end
 always @(posedge clk) begin
   if(!rst_n)begin active<=0;index<=0;word_addr<=0;expected_v<=0;fault<=0;end
   else begin
     expected_v<={expected_v[0],req_v};
     expected_macro[0]<=req_macro;expected_macro[1]<=expected_macro[0];
     expected_row[0]<=req_row;expected_row[1]<=expected_row[0];
     expected_idx[0]<=req_idx;expected_idx[1]<=expected_idx[0];
     if(rsp_v!=expected_v[1])fault<=1;
     if(expected_v[1] && (rsp_macro!=expected_macro[1] || rsp_row!=expected_row[1]))fault<=1;
     if(start)begin
       if(active || expected_v!=0 || token>=129280)fault<=1;
       active<=1;index<=0;word_addr<=26'(token)*26'd320;
     end else if(active)begin
       word_addr<=word_addr+1'b1;index<=index+1'b1;
       if(index==319)active<=0;
     end
   end
 end
endmodule
