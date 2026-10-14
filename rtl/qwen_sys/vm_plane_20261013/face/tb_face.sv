`timescale 1ns/1ps
module tb_face;
parameter integer MUT=0;
reg clk=0,me_e=0; reg [511:0] d=0;
wire [511:0] qsn0,qns0,qsn1,qns1;
ot_qfd_vm_face_sn_e0 #(.MUT(MUT)) a(clk,d,qsn0);
ot_qfd_vm_face_ns_e0 #(.MUT(MUT)) b(clk,d,qns0);
ot_qfd_vm_face_sn_e1 #(.MUT(MUT)) c(clk,me_e,d,qsn1);
ot_qfd_vm_face_ns_e1 #(.MUT(MUT)) e(clk,me_e,d,qns1);
reg [511:0] golden0,golden1,changed0=0,changed1=0;
reg previous_enable=0,valid1=0;
integer i,j,seen_stall=0,seen_enabled=0;
// Independent scalar model: previous ENGINE qualifier determines this edge's capture.
// Upstream reset/flush represented by zero data and zero qualifier; leaves have no reset port.
initial begin
for(i=0;i<4200;i=i+1) begin
  clk=0;
  for(j=0;j<16;j=j+1) d[j*32+:32]=$random;
  me_e=($urandom_range(0,3)==0);
  if(i<3 || (i>=1200 && i<1208) || (i>=2500 && i<2510)) begin d=0; me_e=0; end
  if(i%17==0) d={512{1'b1}};
  if(i%19==0) d=0;
  if(i>=100 && i<612) begin d=0;d[i-100]=1;me_e=i%2;end
  #2;
  golden0=d;
  if(previous_enable) begin golden1=d;valid1=1;seen_enabled=seen_enabled+1;end
  else seen_stall=seen_stall+1;
  previous_enable=me_e;
  clk=1;#1;
  if(qsn0!==golden0 || qns0!==golden0) $fatal(1,"DATA/latency mismatch edge=%0d",i);
  if(valid1 && (qsn1!==golden1 || qns1!==golden1)) $fatal(1,"ENGINE/early-consume mismatch edge=%0d",i);
  changed0=changed0|qsn0; if(valid1) changed1=changed1|qsn1;
  #2;
end
if(changed0!={512{1'b1}} || changed1!={512{1'b1}} || seen_stall<100 || seen_enabled<100) $fatal(1,"coverage");
$display("PASS face exact all512bits edges=%0d enable=%0d stalls=%0d upstream_flush=3",i,seen_enabled,seen_stall);$finish;
end
endmodule
