`timescale 1ns/1ps
module tb_hbm_p_native_producer_static;
 localparam AW=12,CHUNK=221,PCLO=222;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,cfg_we=0,io_cfg_we=0,aux_cfg_we=0,io_start_v=0;
 reg[2:0]cfg_stripe=0;reg[1:0]io_cfg_stripe=0;
 reg[AW-1:0]cfg_addr=0,io_cfg_addr=0,aux_cfg_addr=0;
 reg[255:0]cfg_data=0,io_cfg_data=0,aux_cfg_data=0;
 reg[1741:0]controls[0:4095];reg[470:0]ios[0:4095];reg[181:0]auxs[0:4095];
 reg[255:0]init_image[0:79];
 reg[31:0]scaled[0:639],es[0:639],ebs[0:639],mbs[0:0],ses[0:0];
 integer rows,head,ninst,iolen,scbase,scaledbase,ebase,ebbase,mbase,sebase,sword;
 integer cf,rc,checks=0,observed=0,phase=0,scalar_count=0;
 reg init=0,guard_init=0,readback=0,running=0;
 reg[15:0]init_sector=0,guard_sector=0;
 reg[7:0]pf_v=0;reg[127:0]pf_sec=0;
 wire[135:0]rq,nrq0,nrq1;wire[2247:0]wq,nwq0,nwq1;
 wire[2055:0]rr,brr,frr0,observer_rr;wire[7:0]done,bdone,fdone0;
 wire[143:0]bs;wire t0f,t1f,fault,programme_done,io_done,sv;wire[31:0]st,sy;
 reg pd=0,id=0;string dir;
 ot_hbm_p_native_producer_static dut(
 .clk(clk),.rst_n(rst_n),.clk_lane({16{clk}}),.clk_map({16{clk}}),.rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),
 .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_base(12'd0),.start_limit(13'(ninst)),.start_loops(16'd1),
 .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),
 .io_start_v(io_start_v),.io_start_base(12'd0),.io_start_limit(13'(iolen)),.io_start_loops(16'd1),
 .aux_cfg_we(aux_cfg_we),.aux_cfg_addr(aux_cfg_addr),.aux_cfg_data(aux_cfg_data),
 .local_rq(rq),.local_rr(rr),.local_wq(wq),.local_w_done(done),
 .scalar_valid(sv),.scalar_tag(st),.scalar_fp32(sy),.programme_done(programme_done),.io_done(io_done),.fault(fault));
 ot_hbm_vm_lg_static_tap #(.READ_RETURN(14),.WRITE_RETURN(11)) mid(
 .clk(clk),.rst_n(rst_n),.local_rq(readback?136'd0:rq),.far_rq(136'd0),.local_wq(wq),.far_wq(2248'd0),
 .local_read(readback?8'd0:{rq[135],rq[118],rq[101],rq[84],rq[67],rq[50],rq[33],rq[16]}),
 .local_write({wq[2247],wq[1966],wq[1685],wq[1404],wq[1123],wq[842],wq[561],wq[280]}),
 .near_rq(nrq1),.near_wq(nwq1),.near_rr(frr0),.near_w_done(fdone0),.local_rr(rr),.local_w_done(done),.fault(t1f));
 wire[135:0]observer_rq;
 for(genvar b=0;b<8;b++)assign observer_rq[17*b+:17]={readback&&pf_v[b],pf_sec[16*b+:16]};
 ot_hbm_vm_lg_static_tap near_tap(.clk(clk),.rst_n(rst_n),.local_rq(observer_rq),.far_rq(nrq1),.local_wq(2248'd0),.far_wq(nwq1),
 .local_read(readback?pf_v:8'd0),.local_write(8'd0),.near_rq(nrq0),.near_wq(nwq0),.near_rr(brr),.near_w_done(bdone),
 .local_rr(observer_rr),.far_rr(frr0),.far_w_done(fdone0),.fault(t0f));
 for(genvar b=0;b<8;b++)begin:bank
  wire[280:0]iw={1'b1,init?16'(init_sector+b):16'(guard_sector+b),
    init?init_image[int'(init_sector)-scbase+b]:{8{32'h5a123456}},8'hff};
  wire[770:0]br;assign brr[b*257+:257]=br[256:0];
  ot_vms_bank_static #(.RG(3),.WG(1)) memory(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rslot_v(1'b1),.rslot(2'd0),.wslot_v(1'b1),.wslot(3'd0),.rq({34'd0,nrq0[b*17+:17]}),.rr(br),
   .wq((init||guard_init)?iw:nwq0[b*281+:281]),.wq_done(bdone[b]),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
   .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(bs[b*18+:18]));
 end
 always @(posedge clk)begin
  if(programme_done)pd<=1;if(io_done)id<=1;
  if(running&&sv)begin
   if(st==32'(2*head))begin if(sy!==mbs[0])$fatal(1,"real MB tag%0d got%h expected%h",st,sy,mbs[0]);end
   else if(st==32'(2*head+1))begin if(sy!==ses[0])$fatal(1,"real SE tag%0d got%h expected%h",st,sy,ses[0]);end
   else $fatal(1,"scalar identity");
   scalar_count<=scalar_count+1;
  end
 end
 always @(negedge clk)if(readback)for(integer b=0;b<8;b++)if(observer_rr[257*b+256])
  for(integer w=0;w<8;w++)begin
   reg[31:0]want;
   if(phase<3)want=phase==0?scaled[observed]:(phase==1?es[observed]:ebs[observed]);
   else want=(observed/8==(phase==3?mbase:sebase)%8&&observed%8==sword)?(phase==3?mbs[0]:ses[0]):32'h5a123456;
   if(observer_rr[257*b+32*w+:32]!==want)$fatal(1,"real VM phase%0d word%0d got%h expected%h",phase,observed,observer_rr[257*b+32*w+:32],want);
   observed++;checks++;
  end
 initial begin
  if(!$value$plusargs("CASE_DIR=%s",dir))$fatal(1,"CASE_DIR required");
  cf=$fopen({dir,"/config.txt"},"r");rc=$fscanf(cf,"%d %d %d %d %d %d %d %d %d %d %d",rows,head,ninst,iolen,scbase,scaledbase,ebase,ebbase,mbase,sebase,sword);
  if(rc!=11)$fatal(1,"invalid compiler config");$fclose(cf);
  $readmemh({dir,"/arithmetic.hex"},controls,0,ninst-1);$readmemh({dir,"/io.hex"},ios,0,iolen-1);$readmemh({dir,"/aux.hex"},auxs,0,iolen-1);
  $readmemh({dir,"/raw_sc_sectors.hex"},init_image,0,rows/8-1);
  $readmemh({dir,"/expected_scaled.hex"},scaled,0,rows-1);$readmemh({dir,"/expected_e.hex"},es,0,rows-1);$readmemh({dir,"/expected_eb.hex"},ebs,0,rows-1);
  $readmemh({dir,"/expected_mb.hex"},mbs);$readmemh({dir,"/expected_se.hex"},ses);
  repeat(16)@(negedge clk);rst_n=1;
  for(integer beat=0;beat<rows/64;beat++)begin init=1;init_sector=16'(scbase+8*beat);@(negedge clk);end
  init=0;guard_init=1;guard_sector=16'(mbase/8*8);@(negedge clk);guard_sector=16'(sebase/8*8);@(negedge clk);guard_init=0;
  repeat(20)@(negedge clk);rst_n=0;repeat(8)@(negedge clk);rst_n=1;
  for(integer p=0;p<ninst;p++)for(integer s=0;s<8;s++)begin
   reg[1741:0]row;integer width_s;row=controls[p];width_s=s==7?1742-7*CHUNK:CHUNK;
   cfg_we=1;cfg_addr=12'(p);cfg_stripe=3'(s);cfg_data=(256'(row>>(CHUNK*s))&((256'd1<<width_s)-1))|(256'hc7a1<<240)|(256'(p)<<PCLO);@(negedge clk);
  end
  cfg_we=0;repeat(3)@(negedge clk);
  for(integer p=0;p<iolen;p++)for(integer s=0;s<3;s++)begin
   integer width_s;width_s=s==2?471-2*CHUNK:CHUNK;
   io_cfg_we=1;io_cfg_addr=12'(p);io_cfg_stripe=2'(s);io_cfg_data=(256'(ios[p]>>(CHUNK*s))&((256'd1<<width_s)-1))|(256'hc7a1<<240)|(256'(p)<<PCLO);@(negedge clk);
  end
  io_cfg_we=0;repeat(3)@(negedge clk);
  for(integer p=0;p<iolen;p++)begin
   reg[181:0]row;row=auxs[p];if($test$plusargs("MUT_SOURCE")&&row[1])row[11:2]=0;
   aux_cfg_we=1;aux_cfg_addr=12'(p);aux_cfg_data=256'(row)|(256'hc7a1<<240)|(256'(p)<<PCLO);@(negedge clk);
  end
  aux_cfg_we=0;repeat(3)@(negedge clk);running=1;io_start_v=1;@(negedge clk);io_start_v=0;
  repeat(iolen+32)begin @(negedge clk);if(fault||t0f||t1f||bs!=0)$fatal(1,"real producer fault sf%0b rf%0b schedule%0b aux%0b vm%h",dut.sfu_fault,dut.reduce_fault,dut.schedule_fault,dut.aux_fault,bs);end
  if(!pd||!id||scalar_count!=2)$fatal(1,"incomplete fixed programme");
  readback=1;
  for(phase=0;phase<5;phase++)begin
   integer base,nbeats;base=phase==0?scaledbase:(phase==1?ebase:(phase==2?ebbase:(phase==3?mbase/8*8:sebase/8*8)));
   nbeats=phase<3?rows/64:1;observed=0;
   for(integer beat=0;beat<nbeats;beat++)begin pf_v=8'hff;for(integer b=0;b<8;b++)pf_sec[16*b+:16]=16'(base+8*beat+b);@(negedge clk);end
   pf_v=0;repeat(16)@(negedge clk);
   if(observed!=(phase<3?rows:64))$fatal(1,"VM readback incomplete");
  end
  if(fault||t0f||t1f||bs!=0)$fatal(1,"final real producer fault");
  $display("PASS actual SFU/VM/SRAM/MAX/MB/EXP/E/SUM/SE/RNE-EB T%0d H%0d words%0d checks%0d fixedIO%0d; rawSC boundary; production physical false",rows,head,rows,checks,iolen);$finish;
 end
endmodule
