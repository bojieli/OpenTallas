`timescale 1ns/1ps
module tb_s81_hc_programme_source;
 reg sc=0,dc=0,rn=0,cv=0;reg[83:0]cd=0;
 initial begin #12;forever begin sc=1;#3;sc=0;#3;end end
 initial begin #12;forever begin dc=1;#4;dc=0;#4;end end
 wire hv,f;wire[83:0]hd;wire[31:0]da,sa,ra,yt;wire[639:0]pa;
`ifndef HC_SOURCE_MUT
`define HC_SOURCE_MUT 0
`endif
 ot_s81_hc_programme_source #(.MUT(`HC_SOURCE_MUT))dut(.stream_ck(sc),.stream_rst_n(rn),.serial_ck(dc),.serial_rst_n(rn),
 .command_v(cv),.command_d(cd),.hc_v(hv),.hc_d(hd),.hc_done_age(da),.hc_ss_age(sa),.hc_scalar_age(ra),.hc_y_tag(yt),.hc_post_ages(pa),.fault(f));
 integer st=-1,dt=-1,next=0,seen=0,j,mode=0;
 function automatic[31:0] val(input integer op,field);
  val=32'h81c00000+op*32+field;
 endfunction
 function automatic[83:0] command(input integer op);
  command={13'h1abc,21'(op*3),21'(op*7),22'(op*11),7'(op)};
 endfunction
 initial begin
  if($value$plusargs("mode=%d",mode))begin end
  #10;rn=1;
 end
 always @(negedge sc)begin
  cv=0;
  if(next<128 && st+1==4+next*24)begin cv=1;cd=command(next);next=next+1;end
 end
 always @(posedge sc)if(rn)st=st+1;
 always @(posedge dc)if(rn)begin
  dt=dt+1;#1;
  if(hv)begin
   if(dt!=17+seen*18)$fatal(1,"fixed serial delivery moved actual%0d expected%0d",dt,17+seen*18);
   if(hd!==command(seen)||yt!==val(seen,0)||ra!==val(seen,1)||sa!==val(seen,2)||da!==val(seen,3))$fatal(1,"actual ROM command/metadata mismatch op%0d",seen);
   for(j=0;j<20;j=j+1)if(pa[j*32+:32]!==val(seen,4+j))$fatal(1,"POST age mismatch op%0d row%0d",seen,j);
   seen=seen+1;
  end
  if(f)$fatal(1,"legal fixed programme fault");
  if(seen==128)begin $display("HC_PROGRAMME_SOURCE PASS commands128 metadata_fields3072 mappedROM1 fixed_serial_delivery14 serialedges spacing18");$finish;end
 end
 initial begin #200000;$fatal(1,"missed fixed command");end
endmodule
