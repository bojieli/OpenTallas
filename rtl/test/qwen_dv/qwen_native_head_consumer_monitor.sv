`timescale 1ns/1ps
// Passive SOURCE PREP monitor for the actual selected NK tap and ROM requests.
// Attach at named real clock domains; this module creates no clock aliases and
// supplies no ready, ROM data, X data, arithmetic result or completion stimulus.
// ib_path is resident_ib379.hex produced from the four actual native descriptors.
module qwen_native_head_consumer_monitor(
 input wire ck_tap,ck_code,rst_n,
 input wire head_context_start,head_end,
 input wire [507:0] tap,
 input wire [4:0] code_ce,
 input wire [59:0] code_addr,
 output reg [2:0] chunks_seen=0,
 output reg [31:0] code_reads=0
);
 reg [378:0] expected[0:3];string ib_path;
 initial begin
  if(!$value$plusargs("HEAD_RESIDENT_IB=%s",ib_path))$fatal(1,"HEAD_RESIDENT_IB required");
  $readmemh(ib_path,expected);
 end
 // Tap layout is read directly by selected qfd_tile_nk_rp2_45:
 // go=tap[0], ib=tap[379:1], xl=tap[507:380].
 always @(posedge ck_tap)begin
  if(!rst_n)chunks_seen<=0;
  else if(head_context_start)chunks_seen<=0;
  else begin
   if(tap[0])begin
    if(chunks_seen>=4)$fatal(1,"HEAD_EXTRA_GO");
    else if(tap[379:1]!==expected[chunks_seen])$fatal(1,"HEAD_ACTUAL_TAP_DESCRIPTOR chunk=%0d",chunks_seen);
    chunks_seen<=chunks_seen+1'b1;
   end
   if(head_end&&chunks_seen!=4)$fatal(1,"HEAD_END_BEFORE_FOUR_CHUNKS");
  end
 end
 // Reconstruct resident logical word from the actual bank and row request.
 // HEAD's entire code range is bank4 rows2048..3647 (18432..20031).
 integer bank,word;
 always @(posedge ck_code)begin
  if(!rst_n)code_reads<=0;
  else for(bank=0;bank<5;bank=bank+1)if(code_ce[bank])begin
   word=4096*bank+code_addr[12*bank+:12];
   if(word<18432||word>=20032)$fatal(1,"HEAD_CODE_BOUND bank=%0d row=%0d",bank,code_addr[12*bank+:12]);
   code_reads<=code_reads+1'b1;
  end
 end
endmodule
