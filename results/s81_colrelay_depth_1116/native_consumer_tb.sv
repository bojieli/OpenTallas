`timescale 1ns/1ps
module tb; parameter integer MUT=0; reg clk=0; always #5 clk=~clk; reg rst_n=0; integer cyc=0; integer bad=0; integer badmode=0; integer hb=0; integer hn=0; integer lastb=0; integer lastn=0; integer mb=0; integer mn=0; reg[31:0] gold[0:31]; reg[31:0] seenb=0,seenn=0; reg[65:0] vb=0,vn=0;
function automatic[65:0] stim_b(input integer c); begin case(c)
396:stim_b=66'h0200008911ed7f4b5;
397:stim_b=66'h0200088931b4b3aa5;
398:stim_b=66'h0200100911b7b0421;
399:stim_b=66'h0200180911e07b3c5;
408:stim_b=66'h0200000931d521c09;
409:stim_b=66'h0200080931ed2b485;
415:stim_b=66'h0200208911dd2a3c1;
416:stim_b=66'h0200288931e1356e5;
424:stim_b=66'h0200200931da50fad;
425:stim_b=66'h02002809119f2be9d;
429:stim_b=66'h0200108911c8c3bf9;
430:stim_b=66'h0200188912010bb51;
1196:stim_b=66'h02004089100000001;
1197:stim_b=66'h02004889300000001;
1198:stim_b=66'h02005009000000001;
1199:stim_b=66'h02005809000000001;
1208:stim_b=66'h02004009000000001;
1209:stim_b=66'h02004809000000001;
1215:stim_b=66'h02006089100000001;
1216:stim_b=66'h02006889300000001;
1224:stim_b=66'h02006009000000001;
1225:stim_b=66'h02006809000000001;
1229:stim_b=66'h02005089100000001;
1230:stim_b=66'h02005889300000001;
1996:stim_b=66'h020080892fdfffffd;
1997:stim_b=66'h020088892fdfffffd;
1998:stim_b=66'h020090090fe000001;
1999:stim_b=66'h020098090fe000001;
2008:stim_b=66'h020080090fe000001;
2009:stim_b=66'h020088090fe000001;
2015:stim_b=66'h0200a0892fdfffffd;
2016:stim_b=66'h0200a8892fdfffffd;
2024:stim_b=66'h0200a0090fe000001;
2025:stim_b=66'h0200a8090fe000001;
2029:stim_b=66'h020090892fdfffffd;
2030:stim_b=66'h020098892fdfffffd;
default:stim_b=66'd0; endcase end endfunction
function automatic[65:0] stim_n(input integer c); begin case(c)
393:stim_n=66'h0200000131ce5a105;
394:stim_n=66'h0200080131e09e3ed;
400:stim_n=66'h0200004131763d821;
401:stim_n=66'h0200084131b234261;
406:stim_n=66'h0200008911ed7f4b5;
407:stim_n=66'h0200088931b4b3aa5;
412:stim_n=66'h0200200931da50fad;
413:stim_n=66'h02002809119f2be9d;
419:stim_n=66'h0200208911dd2a3c1;
420:stim_n=66'h0200288931e1356e5;
428:stim_n=66'h0200100911b7b0421;
429:stim_n=66'h0200180911e07b3c5;
433:stim_n=66'h0200108911c8c3bf9;
434:stim_n=66'h0200188912010bb51;
1193:stim_n=66'h0200400112e000001;
1194:stim_n=66'h0200480132e000001;
1200:stim_n=66'h0200404132e000001;
1201:stim_n=66'h0200484112e000001;
1206:stim_n=66'h02004089100000001;
1207:stim_n=66'h02004889300000001;
1212:stim_n=66'h02006009000000001;
1213:stim_n=66'h02006809000000001;
1219:stim_n=66'h02006089100000001;
1220:stim_n=66'h02006889300000001;
1228:stim_n=66'h02005009000000001;
1229:stim_n=66'h02005809000000001;
1233:stim_n=66'h02005089100000001;
1234:stim_n=66'h02005889300000001;
1993:stim_n=66'h020080010fe000001;
1994:stim_n=66'h020088010fe000001;
2000:stim_n=66'h020080410ce000001;
2001:stim_n=66'h020088410ce000001;
2006:stim_n=66'h020080892fdfffffd;
2007:stim_n=66'h020088892fdfffffd;
2012:stim_n=66'h0200a0090fe000001;
2013:stim_n=66'h0200a8090fe000001;
2019:stim_n=66'h0200a0892fdfffffd;
2020:stim_n=66'h0200a8892fdfffffd;
2028:stim_n=66'h020090090fe000001;
2029:stim_n=66'h020098090fe000001;
2033:stim_n=66'h020090892fdfffffd;
2034:stim_n=66'h020098892fdfffffd;
default:stim_n=66'd0; endcase end endfunction
function automatic[65:0] stim_x(input integer c); begin case(c)
393:stim_x=66'h0200000131ce5a105;
394:stim_x=66'h0200080131e09e3ed;
400:stim_x=66'h0200004131763d821;
401:stim_x=66'h0200084131b234261;
406:stim_x=66'h0200008911ed7f4b5;
407:stim_x=66'h0200088931b4b3aa5;
412:stim_x=66'h0200200931da50fad;
413:stim_x=66'h02002809119f2be9d;
419:stim_x=66'h0200208911dd2a3c1;
420:stim_x=66'h0200288931e1356e5;
428:stim_x=66'h0200100911b7b0421;
429:stim_x=66'h0200180911e07b3c5;
433:stim_x=66'h0200108911c8c3bf9;
434:stim_x=66'h0200188912010bb51;
1193:stim_x=66'h0200400112e000001;
1194:stim_x=66'h0200480132e000001;
1200:stim_x=66'h020040410fe000001;
1201:stim_x=66'h020048412fe000001;
1206:stim_x=66'h0200408932dfffffd;
1207:stim_x=66'h0200488912dfffffd;
1212:stim_x=66'h0200600912e000001;
1213:stim_x=66'h0200680932e000001;
1219:stim_x=66'h0200608932dfffffd;
1220:stim_x=66'h0200688912dfffffd;
1228:stim_x=66'h0200500912e000001;
1229:stim_x=66'h0200580932e000001;
1233:stim_x=66'h0200508932dfffffd;
1234:stim_x=66'h0200588912dfffffd;
1993:stim_x=66'h020080010fe000001;
1994:stim_x=66'h020088010fe000001;
2000:stim_x=66'h020080410ce000001;
2001:stim_x=66'h020088410ce000001;
2006:stim_x=66'h020080892fdfffffd;
2007:stim_x=66'h020088892fdfffffd;
2012:stim_x=66'h0200a0090fe000001;
2013:stim_x=66'h0200a8090fe000001;
2019:stim_x=66'h0200a0892fdfffffd;
2020:stim_x=66'h0200a8892fdfffffd;
2028:stim_x=66'h020090090fe000001;
2029:stim_x=66'h020098090fe000001;
2033:stim_x=66'h020090892fdfffffd;
2034:stim_x=66'h020098892fdfffffd;
default:stim_x=66'd0; endcase end endfunction
ot_s81sl_cap_rt #(.MUT(MUT)) u_b (.clk(clk),.rst_n(rst_n),.w_v(vb[0]),.w_t(vb[65:34]),.w_d(vb[33:2]),.w_e(vb[1]),.w_f(1'b0),.e_v(1'b0),.e_t(32'd0),.e_d(32'd0),.e_e(1'b0),.e_f(1'b0),.cfg_v(1'b0),.cfg_d(160'd0),.cw_s_v(),.cw_s_a(),.cw_s_d(),.cw_n_v(),.cw_n_a(),.cw_n_d(),.fault());
always @(posedge clk) if(rst_n) begin
 if(u_b.m3_v) begin mb=mb+1; $display("MERGE b %0d %08x %08x %08x",cyc,u_b.m3_t,u_b.m3_q,u_b.m3_d); end
 if(u_b.re_v && u_b.re_t[12:8]==0 && (6'd1 << u_b.re_t[7:5]) >= u_b.re_t[4:0]) begin
  if(u_b.re_t[28:13]<16'h4000 || u_b.re_t[28:13]>=16'h4020) begin bad=bad+1;$display("BADROW b");end
  else begin
   if(seenb[u_b.re_t[17:13]]) begin bad=bad+1; $display("DUPLICATE b");end
   seenb[u_b.re_t[17:13]]=1;
   if(u_b.re_e || u_b.re_d!==gold[u_b.re_t[17:13]]) begin bad=bad+1; $display("VALUE_MISMATCH b %0d %08x expected %08x",u_b.re_t[17:13],u_b.re_d,gold[u_b.re_t[17:13]]);end
   hb=hb+1;lastb=cyc;$display("COMPLETE b %0d row%0d %08x",cyc,u_b.re_t[17:13],u_b.re_d);
  end
 end
end
ot_s81sl_cap_rt #(.MUT(MUT)) u_n (.clk(clk),.rst_n(rst_n),.w_v(vn[0]),.w_t(vn[65:34]),.w_d(vn[33:2]),.w_e(vn[1]),.w_f(1'b0),.e_v(1'b0),.e_t(32'd0),.e_d(32'd0),.e_e(1'b0),.e_f(1'b0),.cfg_v(1'b0),.cfg_d(160'd0),.cw_s_v(),.cw_s_a(),.cw_s_d(),.cw_n_v(),.cw_n_a(),.cw_n_d(),.fault());
always @(posedge clk) if(rst_n) begin
 if(u_n.m3_v) begin mn=mn+1; $display("MERGE n %0d %08x %08x %08x",cyc,u_n.m3_t,u_n.m3_q,u_n.m3_d); end
 if(u_n.re_v && u_n.re_t[12:8]==0 && (6'd1 << u_n.re_t[7:5]) >= u_n.re_t[4:0]) begin
  if(u_n.re_t[28:13]<16'h4000 || u_n.re_t[28:13]>=16'h4020) begin bad=bad+1;$display("BADROW n");end
  else begin
   if(seenn[u_n.re_t[17:13]]) begin bad=bad+1; $display("DUPLICATE n");end
   seenn[u_n.re_t[17:13]]=1;
   if(u_n.re_e || u_n.re_d!==gold[u_n.re_t[17:13]]) begin bad=bad+1; $display("VALUE_MISMATCH n %0d %08x expected %08x",u_n.re_t[17:13],u_n.re_d,gold[u_n.re_t[17:13]]);end
   hn=hn+1;lastn=cyc;$display("COMPLETE n %0d row%0d %08x",cyc,u_n.re_t[17:13],u_n.re_d);
  end
 end
end
initial begin if($value$plusargs("BAD=%d",badmode)) begin end
gold[0]=32'h47177358;
gold[1]=32'hc7e960cb;
gold[2]=32'h478937c1;
gold[3]=32'h4845254c;
gold[4]=32'h45365050;
gold[5]=32'hc74a7f88;
gold[8]=32'h40000000;
gold[9]=32'hc0000000;
gold[10]=32'h40000000;
gold[11]=32'hc0000000;
gold[12]=32'h40000000;
gold[13]=32'hc0000000;
gold[16]=32'h33800000;
gold[17]=32'h33800000;
gold[18]=32'h33800000;
gold[19]=32'h33800000;
gold[20]=32'h33800000;
gold[21]=32'h33800000;
for(cyc=0;cyc<3000;cyc=cyc+1) begin
 @(negedge clk);rst_n=(cyc>=16);vb=stim_b(cyc);vn=badmode?stim_x(cyc):stim_n(cyc);@(posedge clk);#1;
end
$display("NATIVE_CONSUMER_RESULT bad=%0d rows=%0d/%0d merges=%0d/%0d last=%0d/%0d mutant=%0d",bad,hb,hn,mb,mn,lastb,lastn,badmode);
if(bad || hb!=18 || hn!=18) $fatal(1,"native consumer mismatch");
$display("NATIVE_CONSUMER_PASS");$finish;end endmodule
