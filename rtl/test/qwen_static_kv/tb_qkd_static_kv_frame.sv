`timescale 1ns/1ps
// Real four-quarter physical group, full512-sector SRAM fill before any get.
// Test stimuli/expected values live only at the declared storage boundary.
module tb_qkd_static_kv_frame;
 parameter integer MUT=0,FRAME_SLOTS=1;
 reg ck=0;always #0.416667 ck=~ck;
 reg rst_n=0,arm=0,pv=0,rq=0,rv=0;
 reg[15:0]epoch=0;reg[5:0]layer=0;
 reg[9:0]ps=0;reg[13:0]rt=0;
 reg[1023:0]idata=0;
 wire ov,okind,fault;wire[1023:0]odata;wire[13:0]ot;wire[15:0]oe;wire[5:0]ol;
 wire[43:0]occ;wire[3:0]idle;
 wire[63:0]actual_epoch={4{epoch}} ^ ((MUT==3&&pv&&ps==9)?64'd1:64'd0);
 qkd_static_kv_frame_physical_grp #(.STACK(0),.GROUP(0),.MUT(MUT<3?MUT:0),.FRAME_SLOTS(FRAME_SLOTS))dut(
  .ck(ck),.ck_pc({4{ck}}),.ck_req_rly({4{ck}}),.ck_rsp_rly({4{ck}}),.rst_n(rst_n),
  .arm(arm),.epoch(epoch),.layer(layer),.expected_put({4{pv}}),.expected_sector({4{ps}}),
  .expected_epoch({4{epoch}}),.expected_layer({4{layer}}),
  .actual_valid({4{pv}}),.actual_sector({4{ps}}),.actual_epoch(actual_epoch),.actual_layer({4{layer}}),.actual_data(idata),
  .req_valid(rq),.req_t(rt),.req_v(rv),.req_epoch(epoch),.req_layer(layer),
  .rsp_valid(ov),.rsp_data(odata),.rsp_t(ot),.rsp_v(okind),.rsp_epoch(oe),.rsp_layer(ol),.fault(fault),.occupancy(occ),.idle(idle));
 function automatic[9:0]sector(input integer kind,ordinal);
  sector=kind?10'(512+((ordinal&8)<<4)+((ordinal>>4)<<3)+(ordinal&7)):10'(ordinal);
 endfunction
 function automatic[13:0]tag(input[9:0]sec);
  tag={1'b0,sec[6:3],2'd0,sec[7],sec[2:0],3'd0};
 endfunction
 function automatic[1023:0]word(input integer st,kind,ordinal);
  for(integer q=0;q<4;q++)for(integer n=0;n<8;n++)
   word[256*q+32*n+:32]=32'habc38100 ^ 32'(st*1048573+kind*65537+ordinal*71+q*8191+n*31);
 endfunction
 function automatic integer ordinal_of(input[13:0]t,input integer kind);
  reg[9:0]s;begin s={kind!=0,1'b0,t[6],t[12:9],t[5:3]};ordinal_of=kind?{s[6:3],s[7],s[2:0]}:s[7:0];end
 endfunction
 reg[7:0]expected_v=0;reg[13:0]expected_t[0:7];reg expected_kind[0:7];
 reg[15:0]expected_epoch[0:7];reg[5:0]expected_layer[0:7];reg[1023:0]expected_d[0:7];
 integer errors=0,seen=0,peak=0,full_frames=0;
 always @(posedge ck)begin
  expected_v<={expected_v[6:0],rq};expected_t[0]<=rt;expected_kind[0]<=rv;
  expected_epoch[0]<=epoch;expected_layer[0]<=layer;expected_d[0]<=word(layer,rv,ordinal_of(rt,rv));
  for(integer d=1;d<8;d++)begin
   expected_t[d]<=expected_t[d-1];expected_kind[d]<=expected_kind[d-1];
   expected_epoch[d]<=expected_epoch[d-1];expected_layer[d]<=expected_layer[d-1];expected_d[d]<=expected_d[d-1];
  end
  #0.001;
  if(rst_n)begin
   if(occ[10:0]>peak)peak=occ[10:0];
   if(ov!==expected_v[7])begin if(errors<6)$display("BAD valid got%0b expected%0b",ov,expected_v[7]);errors++;end
   if(fault)begin if(errors<6)$display("BAD actual frame fault");errors++;end
   if(ov)begin
    seen++;
    if(odata!==expected_d[7]||ot!==expected_t[7]||okind!==expected_kind[7]||oe!==expected_epoch[7]||ol!==expected_layer[7])begin
     if(errors<6)$display("BAD SRAM group payload/meta row%0d",seen);errors++;
    end
   end
  end
 end
 initial begin
  repeat(8)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
  for(integer st=0;st<36;st++)begin
   epoch=16'(37+st);layer=6'(st);arm=1;@(negedge ck);arm=0;repeat(6)@(negedge ck);
   for(integer kind=0;kind<2;kind++)for(integer n=0;n<256;n++)begin
    pv=1;ps=sector(kind,n);idata=word(st,kind,n);@(negedge ck);
   end
   pv=0;repeat(6)@(negedge ck);
   for(integer q=0;q<4;q++)if(occ[11*q+:11]!=512)$fatal(1,"full frame capacity missing quarter%0d occupancy%0d",q,occ[11*q+:11]);
   full_frames++;
   for(integer kind=0;kind<2;kind++)for(integer n=0;n<256;n++)begin
    rq=1;rv=kind!=0;rt=tag(sector(kind,n));@(negedge ck);
   end
   rq=0;repeat(16)@(negedge ck);
   if(idle!=4'hf||occ!=0)$fatal(1,"frame did not drain");
  end
  $display("MEASURE fullframes%0d group_rows%0d quarter_words%0d peakPC%0d errors%0d",full_frames,seen,4*seen,peak,errors);
  if(errors||seen!=36*512||peak!=512)$fatal(1,"FRAME_FAIL");
  $display("PASS full512 mapped-SRAM physical four-quarter group,36 layers, same7edge transport, exact metadata/data, fully drained");$finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
