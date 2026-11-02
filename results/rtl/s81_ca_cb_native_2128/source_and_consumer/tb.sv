`timescale 1ps/1ps
module counted_lane #(parameter integer D=59)(input wire ck,input wire[275:0] i,output wire[275:0] o);
  reg[275:0] q[0:D-1]; integer k;
  always @(posedge ck)begin q[0]<=i;for(k=1;k<D;k=k+1)q[k]<=q[k-1];end
  assign o=q[D-1];
endmodule
module tb;
 reg ck=0; always begin #416 ck=1;#417 ck=0;end
 reg rst=0;reg rel=0,rpb=0;reg[552:0]h0=0;wire[275:0] sa,sb,a,b,o;wire fault,merr;
 selected_source src(ck,rst,rel,rpb,h0,sa,sb,merr);
 integer gap=2,equal_depth=0,mutdate=0,expected_fault=0,tick;
 integer ca_n=0,cb_n=0,out_n=0,collisions=0,errors=0;
 reg[275:0] expected=0;reg expected_v=0;
 localparam[275:0] A=(276'hA115EED<<21)|(276'h2<<4)|(276'h4<<1)|276'h1;
 localparam[275:0] B=(276'hB225EED<<21)|(276'h3<<4)|(276'h4<<1)|276'h1;
 wire[275:0] b58,b59;
 counted_lane#(.D(59))la(ck,sa,a);
 counted_lane#(.D(58))lb0(ck,sb,b58);
 counted_lane#(.D(59))lb1(ck,sb,b59);
 assign b=equal_depth?b59:b58;
 dsdv_idx_vmux6#(.V(276),.MUT(0)) dut(.ck(ck),.rst(rst),.i_r(276'b0),.i_s(276'b0),.i_a(a),.i_b(b),.i_n(276'b0),.i_l(276'b0),.o(o),.fault(fault));
 reg[275:0] next_expected;reg next_v;
 initial begin
  if($value$plusargs("GAP=%d",gap))begin end
  if($value$plusargs("EQUAL=%d",equal_depth))begin end
  if($value$plusargs("MUTDATE=%d",mutdate))begin end
  if($value$plusargs("EXPECTFAULT=%d",expected_fault))begin end
  for(tick=0;tick<160;tick=tick+1)begin
   @(negedge ck);rst=(tick>=4);rel=(tick==40||tick==40+gap-mutdate);rpb=(tick==40);h0=0;h0[3:1]=3'd5;h0[4+:276]=rpb?A:B;
   @(posedge ck);
   if(a[0])begin ca_n=ca_n+1;$display("PIN_A %0d %h",tick,a);end
   if(b[0])begin cb_n=cb_n+1;$display("PIN_B %0d %h",tick,b);end
   if(a[0]&&b[0])collisions=collisions+1;
   next_v=a[0]|b[0];next_expected=(a&{276{a[0]}})|(b&{276{b[0]}});
   #1;
   if(tick>90)begin
    if(o[0]!==expected_v)errors=errors+1;
    if(expected_v&&o!==expected)errors=errors+1;
   end
   if(o[0])begin out_n=out_n+1;$display("OUTPUT %0d %h",tick,o);end
   expected_v=next_v;expected=next_expected;
  end
  if(ca_n!=1||cb_n!=1||merr)errors=errors+1;
  if(fault!==expected_fault[0])errors=errors+1;
  if(expected_fault==0&&(collisions!=0||out_n!=2))errors=errors+1;
  if(expected_fault!=0&&(collisions!=1||out_n!=1))errors=errors+1;
  $display("CA_CB_RESULT gap%0d equal%0d mutantdate%0d fault%0d collisions%0d outputs%0d errors%0d",gap,equal_depth,mutdate,fault,collisions,out_n,errors);
  if(errors)$fatal(1,"CA_CB_WITNESS_FAIL");
  $display("CA_CB_WITNESS_PASS");$finish;
 end
endmodule
