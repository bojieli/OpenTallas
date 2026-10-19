`timescale 1ns/1ps
// tb_hnx_su_bank6_ws (HBM-NEXT-UNITS 2026-10-19): TILE bench of the hnx pinned SU store bank ot_hnx_su_bank6_ws =
// d4g bank (6 real 128x256 SRAM models) + split write phase ot_hnx_su_wsplit + write mux, as the kit hardens it.
// Phases (every read checked on all 6 replicas, read n -> n+2; conflict / clash pins checked every edge):
//  P1 wsplit=1 defer=1 (HI = 0 bank): fill (ow) and lane write on the SAME edge every 2nd edge, lane commits from the
//     deferral register one edge later (fill-free phase); lane_a / lane_d carry junk on the off edges. No fault.
//  P2 wsplit=1 defer=0 (HI = 1 bank): lane write at once on even edges, fill on odd edges. No fault.
//  P3 wsplit=0: lane-only rows then fill-only rows = the d4g bank write (commit n+1, read-after-write at n+1). No fault.
//  P4 deliberate collision (wsplit=0, ow + lane same edge): conflict must rise one edge later (registered fault pin).
// WMUT (must FAIL): 1 deferral dropped; 2 the HI = 1 half deferred instead; 3 deferred write takes the current address.
module tb_hnx_su_bank6_ws;
 parameter integer WMUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0; reg[5:0]rv=0; reg[53:0]ra=0;
 wire[191:0]rd; wire[5:0]ret;
 reg ow_v=0; reg[8:0]ow_a=0; reg[31:0]ow_d=0;
 reg lv=0; reg[8:0]la=0; reg[31:0]ld=0;
 reg wsplit=0, defer=0;
 wire conflict, clash;
 integer c,r,checks=0,errors=0,faults=0;
 reg fault_ok=0;
 reg [31:0] ref_m [0:511];
 ot_hnx_su_bank6_ws #(.WMUT(WMUT)) d(.clk(clk),.clk_rd(clk),.clk_ws(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),
  .clk_macro3(clk),.clk_macro4(clk),.clk_macro5(clk),.rst_n(rst_n),.read_v(rv),.read_addr(ra),.read_data(rd),.read_return(ret),
  .ow_v(ow_v),.ow_addr(ow_a),.ow_data(ow_d),.lane_v(lv),.lane_a(la),.lane_d(ld),.wsplit(wsplit),.defer(defer),
  .conflict(conflict),.clash(clash));
 function automatic[31:0]word(input integer row,input integer ph);word=32'h12340000^32'(ph<<24)^32'(row*31+1);endfunction
 // fault pins: any conflict / clash outside the deliberate P4 window is an error
 always @(posedge clk) if(rst_n&&!fault_ok&&(conflict||clash))begin
  if(faults<4)$display("ERR fault pin conflict=%b clash=%b",conflict,clash); faults=faults+1; end
 task automatic readback(input integer ph);
  integer cc,rr;
  for(cc=0;cc<514;cc=cc+1)begin
   rv=cc<512?6'h3f:0;
   for(rr=0;rr<6;rr=rr+1)ra[rr*9+:9]=9'((cc+17*rr)%512);
   @(posedge clk);#1;
   checks=checks+1;if(ret!==(cc>=2?6'h3f:6'h00))errors=errors+1;
   if(cc>=2)for(rr=0;rr<6;rr=rr+1)begin
    checks=checks+1;
    if(rd[rr*32+:32]!==ref_m[(cc-2+17*rr)%512])begin
     if(errors<6)$display("ERR P%0d row=%0d replica=%0d data=%h exp=%h",ph,(cc-2+17*rr)%512,rr,rd[rr*32+:32],ref_m[(cc-2+17*rr)%512]);
     errors=errors+1;
    end
   end
   @(negedge clk);
  end
  rv=0;
 endtask
 initial begin
  repeat(3)@(negedge clk); rst_n=1; repeat(4)@(negedge clk);
  // ---- P1: HI = 0 bank, deferral on: fill + lane on the same edge every 2nd edge
  wsplit=1; defer=1;
  for(c=0;c<256;c=c+1)begin
   ow_v=1; ow_a=9'(c); ow_d=word(c,1); lv=1; la=9'(256+c); ld=word(256+c,1); ref_m[c]=word(c,1); ref_m[256+c]=word(256+c,1);
   @(negedge clk);
   ow_v=0; lv=0; la=9'h1ff^9'(c); ld=32'hdeadbeef;     // junk on the free edge (address-capture witness)
   @(negedge clk);
  end
  la=0; ld=0; repeat(3)@(negedge clk);
  readback(1);
  // ---- P2: HI = 1 bank, wsplit on: lane at once on even edges, fill on odd edges
  wsplit=1; defer=0;
  for(c=0;c<256;c=c+1)begin
   lv=1; la=9'(2*c); ld=word(2*c,2); ow_v=0; ref_m[2*c]=word(2*c,2);
   @(negedge clk);
   lv=0; la=9'h1ff; ld=32'hdeadbeef; ow_v=1; ow_a=9'(2*c+1); ow_d=word(2*c+1,2); ref_m[2*c+1]=word(2*c+1,2);
   @(negedge clk);
  end
  ow_v=0; repeat(3)@(negedge clk);
  readback(2);
  // ---- P3: wsplit = 0 (d4g write): lane-only then fill-only, every edge; read-after-write one edge after the write
  wsplit=0; defer=1;
  for(c=0;c<256;c=c+1)begin lv=1; la=9'(c); ld=word(c,3); ref_m[c]=word(c,3); @(negedge clk); end
  lv=0;
  for(c=256;c<512;c=c+1)begin ow_v=1; ow_a=9'(c); ow_d=word(c,3); ref_m[c]=word(c,3); @(negedge clk); end
  ow_v=0;
  // d4g write commit n+1: write row 5 at n, read it at n+1 -> returns the new word at n+3
  lv=1; la=9'd5; ld=32'h5a5a0005; ref_m[5]=32'h5a5a0005; @(negedge clk); lv=0;
  rv=6'h01; ra[8:0]=9'd5; @(negedge clk); rv=0; @(posedge clk);#1; @(posedge clk);#1;
  checks=checks+1; if(rd[31:0]!==32'h5a5a0005)begin $display("ERR P3 read-after-write %h",rd[31:0]); errors=errors+1; end
  @(negedge clk); repeat(2)@(negedge clk);
  readback(3);
  // ---- P4: deliberate collision (wsplit = 0): conflict must be raised one edge later
  fault_ok=1; ow_v=1; ow_a=9'd7; ow_d=32'h0; lv=1; la=9'd8; ld=32'h0;
  @(posedge clk);#1; checks=checks+1; if(conflict!==1'b1)begin $display("ERR P4 collision not flagged"); errors=errors+1; end
  @(negedge clk); ow_v=0; lv=0; @(negedge clk); @(negedge clk); fault_ok=0;
  errors=errors+faults;
  if(errors)$fatal(1,"HNX_SU_BANK_WS FAIL WMUT=%0d checks=%0d errors=%0d",WMUT,checks,errors);
  $display("HNX_SU_BANK_WS PASS checks=%0d phases=4 (defer HI0, at-once HI1, wsplit0 = d4g, collision fault) SRAMs=6",checks);
  $finish;
 end
endmodule
