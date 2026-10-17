`timescale 1ns/1ps
// Storage-boundary gate: all128 PCs, real512 SRAM macros and actual four-stack
// V issuers. Fixed3040-edge test frames include external fixture loading; this
// is NOT a2190-edge native-layer timing qualification. EXP is declared zero
// stimulus at the issuer input, not a substitute for native EP/PV arithmetic.
module tb_qkd_frame_four_stack_full128;
 parameter integer MUT=0;
 localparam FRAME=3040;
 reg ck=0;always #0.416667 ck=~ck;
 reg rst_n=0,arm=0,pv=0;
 reg[15:0]epoch=0;reg[5:0]layer=0;
 reg[9:0]ps=0;
 reg[31:0]rq=0,rv=0;reg[13:0]rt[0:31];reg[1023:0]idata[0:31];
 wire[31:0]ov,okind,fault;wire[1023:0]odata[0:31];wire[13:0]ot[0:31];
 wire[15:0]oe[0:31];wire[5:0]ol[0:31];wire[43:0]occ[0:31];wire[3:0]idle[0:31];
 for(genvar g=0;g<32;g++)begin:groups
  wire[63:0]aepoch={4{epoch}} ^ ((MUT==3&&g==0&&pv&&ps==9)?64'd1:64'd0);
  qkd_static_kv_frame_physical_grp #(.STACK(g/8),.GROUP(g%8),.MUT(MUT==1?1:0))dut(
   .ck(ck),.ck_pc({4{ck}}),.ck_req_rly({4{ck}}),.ck_rsp_rly({4{ck}}),.rst_n(rst_n),
   .arm(arm),.epoch(epoch),.layer(layer),.expected_put({4{pv}}),.expected_sector({4{ps}}),
   .expected_epoch({4{epoch}}),.expected_layer({4{layer}}),
   .actual_valid({4{pv}}),.actual_sector({4{ps}}),.actual_epoch(aepoch),.actual_layer({4{layer}}),.actual_data(idata[g]),
   .req_valid(rq[g]),.req_t(rt[g]),.req_v(rv[g]),.req_epoch(epoch),.req_layer(layer),
   .rsp_valid(ov[g]),.rsp_data(odata[g]),.rsp_t(ot[g]),.rsp_v(okind[g]),.rsp_epoch(oe[g]),.rsp_layer(ol[g]),
   .fault(fault[g]),.occupancy(occ[g]),.idle(idle[g]));
 end
 wire[3:0]vreq,vdone,vfault,vout,vfirst,vlast;
 wire[2:0]vslot[0:3];wire[13:0]vtag[0:3],vot[0:3];
 wire[15:0]vepoch[0:3],voepoch[0:3];wire[1023:0]vdata[0:3];wire[63:0]vexp[0:3];
 reg vstart=0;reg[3:0]done_seen=0;
 for(genvar s=0;s<4;s++)begin:issuers
  reg rsp_valid;reg[2:0]rsp_slot;reg[13:0]rsp_t;reg[15:0]rsp_epoch;reg[1023:0]rsp_data;
  always @*begin
   rsp_valid=0;rsp_slot=0;rsp_t=0;rsp_epoch=0;rsp_data=0;
   for(integer g=0;g<8;g++)if(ov[8*s+g]&&okind[8*s+g])begin
    rsp_valid=1;rsp_slot=ot[8*s+g][2:0];rsp_t=ot[8*s+g];rsp_epoch=oe[8*s+g];rsp_data=odata[8*s+g];
   end
  end
  ot_qwen_tp8_vrow_stack_static #(.STACK(s),.RETURN_LATENCY(8))u_issuer(
   .clk(ck),.rst_n(rst_n),.start(vstart),.context_len(14'd8192),.epoch(epoch),
   .req_valid(vreq[s]),.req_ready(1'b1),.req_slot(vslot[s]),.req_t(vtag[s]),.req_epoch(vepoch[s]),
   .rsp_valid(rsp_valid),.rsp_slot(rsp_slot),.rsp_t(rsp_t ^ ((MUT==2&&s==0)?14'd1:14'd0)),
   .rsp_epoch(rsp_epoch),.rsp_vrow(rsp_data),.rsp_exp(64'd0),
   .out_valid(vout[s]),.out_ready(1'b1),.out_vrow(vdata[s]),.out_exp(vexp[s]),.out_t(vot[s]),
   .out_epoch(voepoch[s]),.out_first(vfirst[s]),.out_last(vlast[s]),.done(vdone[s]),.fault(vfault[s]));
 end
 function automatic[9:0]sector(input integer kind,n);
  sector=kind?10'(512+((n&8)<<4)+((n>>4)<<3)+(n&7)):10'(n);
 endfunction
 function automatic[13:0]tag(input[9:0]sec,input integer stack,group);
  tag={1'b0,sec[6:3],2'(stack),sec[7],sec[2:0],3'(group)};
 endfunction
 function automatic integer ordinal_of(input[13:0]t,input integer kind);
  reg[9:0]sec;begin sec={kind!=0,1'b0,t[6],t[12:9],t[5:3]};ordinal_of=kind?{sec[6:3],sec[7],sec[2:0]}:sec[7:0];end
 endfunction
 function automatic[1023:0]word(input integer st,group,kind,n);
  for(integer q=0;q<4;q++)for(integer i=0;i<8;i++)
   word[256*q+32*i+:32]=32'hd1300780 ^ 32'(st*1048573+group*65537+kind*32771+n*71+q*8191+i*31);
 endfunction
 reg[31:0]ev[0:7],ek[0:7];reg[13:0]et[0:7][0:31];reg[1023:0]ed[0:7][0:31];
 reg[15:0]ee[0:7];reg[5:0]el[0:7];
 integer errors=0,seen=0,vseen=0,peak=0,full_frames=0,edge_count=0;
 integer req_count[0:3],out_count[0:3],first_req[0:3],last_req[0:3];
 reg[8191:0]token_seen=0;
 always @(posedge ck)begin
  edge_count++;done_seen<=done_seen|vdone;
  ev[0]<=rq;ek[0]<=rv;ee[0]<=epoch;el[0]<=layer;
  for(integer g=0;g<32;g++)begin et[0][g]<=rt[g];ed[0][g]<=word(layer,g,rv[g],ordinal_of(rt[g],rv[g]));end
  for(integer d=1;d<8;d++)begin
   ev[d]<=ev[d-1];ek[d]<=ek[d-1];ee[d]<=ee[d-1];el[d]<=el[d-1];
   for(integer g=0;g<32;g++)begin et[d][g]<=et[d-1][g];ed[d][g]<=ed[d-1][g];end
  end
  for(integer s=0;s<4;s++)if(vreq[s])begin
   if(req_count[s]==0)first_req[s]=edge_count;last_req[s]=edge_count;req_count[s]++;
   if(((vtag[s]>>7)&3)!=s||vtag[s]>=8192)errors++;
  end
  #0.001;
  if(rst_n)begin
   if(ov!==ev[7])begin if(errors<5)$display("BAD physical group valid");errors++;end
   if((|fault)||(|vfault))begin if(errors<5)$display("BAD storage/actual issuer fault");errors++;end
   for(integer g=0;g<32;g++)begin
    for(integer q=0;q<4;q++)if(occ[g][11*q+:11]>peak)peak=occ[g][11*q+:11];
    if(ov[g])begin
     seen++;
     if(odata[g]!==ed[7][g]||ot[g]!==et[7][g]||okind[g]!==ek[7][g]||oe[g]!==ee[7]||ol[g]!==el[7])begin
      if(errors<5)$display("BAD real SRAM row/meta group%0d",g);errors++;
     end
    end
   end
   for(integer s=0;s<4;s++)if(vout[s])begin
    automatic integer g=8*s+(vot[s]&7);
    vseen++;out_count[s]++;
    if(token_seen[vot[s]])errors++;token_seen[vot[s]]=1;
    if(vdata[s]!==word(layer,g,1,ordinal_of(vot[s],1))||voepoch[s]!=epoch||vexp[s]!=0||
       vfirst[s]!=(vot[s]<256)||vlast[s]!=(vot[s]+256>=8192))begin
     if(errors<5)$display("BAD actual V issuer data/metadata stack%0d tag%0d",s,vot[s]);errors++;
    end
   end
  end
 end
 initial begin
  for(integer d=0;d<8;d++)begin ev[d]=0;ek[d]=0;end
  for(integer s=0;s<4;s++)begin req_count[s]=0;out_count[s]=0;first_req[s]=0;last_req[s]=0;end
  for(integer g=0;g<32;g++)begin rt[g]=0;idata[g]=0;end
  repeat(12)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
  for(integer st=0;st<36;st++)begin
   epoch=16'(37+st);layer=6'(st);done_seen=0;token_seen=0;
   for(integer s=0;s<4;s++)begin req_count[s]=0;out_count[s]=0;end
   for(integer f=0;f<FRAME;f++)begin
    arm=f==16;pv=f>=32&&f<544;vstart=f==832;rq=0;rv=0;
    if(pv)begin
     ps=sector((f-32)/256,(f-32)%256);
     for(integer g=0;g<32;g++)idata[g]=word(st,g,(f-32)/256,(f-32)%256);
    end
    for(integer g=0;g<32;g++)begin
     if(f>=560&&f<816)begin rq[g]=1;rt[g]=tag(sector(0,f-560),g/8,g%8);end
     if(vreq[g/8]&&vtag[g/8][2:0]==g%8)begin rq[g]=1;rv[g]=1;rt[g]=vtag[g/8];end
    end
    if(f==552)begin
     for(integer g=0;g<32;g++)for(integer q=0;q<4;q++)if(occ[g][11*q+:11]!=512)$fatal(1,"capacity");
     full_frames++;
    end
    @(negedge ck);
   end
   if(done_seen!=15||token_seen!={8192{1'b1}})$fatal(1,"FULL128_FAIL missing rows/done");
   for(integer s=0;s<4;s++)if(req_count[s]!=2048||out_count[s]!=2048||last_req[s]-first_req[s]!=2047)$fatal(1,"FULL128_FAIL V rate");
   for(integer g=0;g<32;g++)if(idle[g]!=15||occ[g]!=0)$fatal(1,"FULL128_FAIL not drained");
  end
  $display("MEASURE stages36 PCs128 SRAM512 fullframes%0d group_rows%0d quarter_words%0d Vrows%0d peakPC%0d errors%0d testframe%0d",full_frames,seen,4*seen,vseen,peak,errors,FRAME);
  if(errors||seen!=36*16384||vseen!=36*8192||peak!=512)$fatal(1,"FULL128_FAIL");
  $display("PASS actual4 V issuers/all128PC full512 mapped storage,36 fixed testframes,7edge rows,2048edge four-row feed; native2190/EP/PV/writer/physical join OPEN");$finish;
 end
 initial begin #200000000;$fatal(1,"timeout");end
endmodule
