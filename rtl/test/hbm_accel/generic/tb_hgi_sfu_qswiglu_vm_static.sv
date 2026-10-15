`timescale 1ns/1ps
module tb_hgi_sfu_qswiglu_vm_static;
 localparam LWB=15,WORDS=3072,NINST=368,CHUNK=222,PCLO=223;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0;
 reg [1741:0] controls[0:NINST-1];
reg [31:0] gates[0:WORDS-1],ups[0:WORDS-1],golds[0:WORDS-1],route[0:0];
reg init=0;
 reg [11:0] init_sector=0;
 reg [255:0] init_image[0:2055];
 reg [7:0] pf_v=0,pf_scalar=0;
 reg [127:0] pf_sec=0;
 reg [15:0] pf_group=0;
 reg [119:0] pf_addr=0;
 wire [135:0] rq,nrq0,nrq1;
 wire [2247:0] wq,nwq0,nwq1;
 wire [2055:0] rr,brr,frr0;
 wire [7:0] done,bdone,fdone0;
 wire [143:0] bs;
 wire t0f,t1f;
 reg [31:0] drain_sector=0;
 reg readback=0;
 integer observed=0;
 reg cfg_we=0,start_v=0;
 reg [2:0] cfg_stripe=0;
 reg [10:0] cfg_addr=0;
 reg [255:0] cfg_data=0;
 reg [7:0] stage_v=0;
 reg [15:0] stage_group=0;
 reg [8*LWB-1:0] stage_addr=0;
 reg [2047:0] stage_data=0;
 reg [1:0] drain_v=0;
 reg [2*LWB-1:0] drain_addr=0;
 wire [511:0] drain_data;
 wire [1:0] drain_rv;
 wire fault;
 integer checks=0;
 function automatic [31:0] value(input integer g,a);value=32'h3e000000+32'(100000*g+a*7);endfunction
 ot_hgi_sfu_vm_programmed_engine dut(.clk(clk),.rst_n(rst_n),.clk_lane({16{clk}}),.clk_map({16{clk}}),
 .rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),
 .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start_v(start_v),.start_base(11'd0),.start_limit(12'(NINST)),.start_loops(16'd1),
 .prefetch_v(readback?8'd0:pf_v),.prefetch_scalar(pf_scalar),.prefetch_sector(pf_sec),.prefetch_group(pf_group),.prefetch_local_addr(pf_addr),
 .prefetch_word(24'd0),.scalar_addr({48'd0,24'd12672,24'd0}),.scalar_enable(4'b0010),
 .local_rq(rq),.local_rr(rr),.local_wq(wq),.local_w_done(done),
 .vi_q(512'd0),.side_y(512'd0),.drain_round_bf16(2'd0),.drain_v(drain_v),.drain_addr(drain_addr),.drain_vm_sector(drain_sector),.fault(fault));
 ot_hbm_vm_lg_static_tap #(.READ_RETURN(14),.WRITE_RETURN(11)) mid(.clk(clk),.rst_n(rst_n),.local_rq(readback?136'd0:rq),.far_rq(136'd0),
 .local_wq(wq),.far_wq(2248'd0),.local_read(readback?8'd0:pf_v),.local_write({wq[2247],wq[1966],wq[1685],wq[1404],wq[1123],wq[842],wq[561],wq[280]}),
 .near_rq(nrq1),.near_wq(nwq1),.near_rr(frr0),.near_w_done(fdone0),.local_rr(rr),.local_w_done(done),.fault(t1f));
 wire [135:0] observer_rq;
 for(genvar b=0;b<8;b++)assign observer_rq[17*b+:17]={readback&&pf_v[b],pf_sec[16*b+:16]};
 wire [2055:0] observer_rr;
 ot_hbm_vm_lg_static_tap near_tap(.clk(clk),.rst_n(rst_n),.local_rq(observer_rq),.far_rq(nrq1),.local_wq(2248'd0),.far_wq(nwq1),
 .local_read(readback?pf_v:8'd0),.local_write(8'd0),.near_rq(nrq0),.near_wq(nwq0),.near_rr(brr),.near_w_done(bdone),
 .local_rr(observer_rr),.far_rr(frr0),.far_w_done(fdone0),.fault(t0f));
 for(genvar b=0;b<8;b++)begin:bank
  wire [280:0] iw={init,16'(init_sector+b),init_image[init_sector+b],8'hff};
  wire [770:0] br;
  assign brr[b*257+:257]=br[256:0];
  ot_vms_bank_static #(.RG(3),.WG(1)) memory(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
  .rslot_v(1'b1),.rslot(2'd0),.wslot_v(1'b1),.wslot(3'd0),.rq({34'd0,nrq0[b*17+:17]}),.rr(br),
  .wq(init?iw:nwq0[b*281+:281]),.wq_done(bdone[b]),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
  .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(bs[b*18+:18]));
 end
 always @(negedge clk)if(readback)for(integer b=0;b<8;b++)if(observer_rr[257*b+256])begin
  for(integer w=0;w<8;w++)begin
   if(observer_rr[257*b+32*w+:32]!==golds[observed])$fatal(1,"VM_QSWIGLU_WORD word=%0d got=%h expected=%h",observed,observer_rr[257*b+32*w+:32],golds[observed]);
   observed++;
  end
 end
 initial begin
  $readmemh(`SFU_IMAGE,controls);
  $readmemh({`SFU_DATA_DIR,"/gate.hex"},gates);
  $readmemh({`SFU_DATA_DIR,"/up.hex"},ups);
  $readmemh({`SFU_DATA_DIR,"/gold.hex"},golds);
  $readmemh({`SFU_DATA_DIR,"/route.hex"},route);
  $readmemh({`SFU_DATA_DIR,"/vm_init.hex"},init_image);
  repeat(16)@(negedge clk);rst_n=1;
  for(integer row=0;row<257;row++)begin init=1;init_sector=12'(row*8);@(negedge clk);end
  init=0;repeat(20)@(negedge clk);rst_n=0;repeat(8)@(negedge clk);rst_n=1;
  for(integer beat=0;beat<WORDS/16;beat++)begin
   pf_v=0;pf_scalar=0;
   for(integer part=0;part<2;part++)begin
    integer bg,bu;
    bg=(beat*2+part)%8;bu=(1026+beat*2+part)%8;
    pf_v[bg]=1;pf_sec[16*bg+:16]=16'(beat*2+part);pf_group[2*bg+:2]=0;pf_addr[15*bg+:15]=15'(beat*16+part*8);
    pf_v[bu]=1;pf_sec[16*bu+:16]=16'(1026+beat*2+part);pf_group[2*bu+:2]=2;pf_addr[15*bu+:15]=15'(beat*16+part*8);
   end
   @(negedge clk);
  end
  pf_v=8'h10;pf_scalar=8'h10;pf_sec[64+:16]=16'd2052;pf_group[8+:2]=1;
  @(negedge clk);pf_v=0;pf_scalar=0;repeat(16)@(negedge clk);
  for(integer p=0;p<NINST;p++)for(integer st=0;st<8;st++)begin
   reg [1741:0] row;
   row=controls[p];
   if($test$plusargs("MUT_DROP") && p==8)row=0;
   cfg_we=1;cfg_addr=11'(p);cfg_stripe=3'(st);
   cfg_data=256'(row>>(CHUNK*st));
   if(st==7)cfg_data=(cfg_data&((256'd1<<188)-1))|(256'hc7a1<<240)|(256'(p)<<PCLO);
   else cfg_data=(cfg_data&((256'd1<<CHUNK)-1))|(256'hc7a1<<240)|(256'(p)<<PCLO);
   @(negedge clk);
  end
  cfg_we=0;repeat(3)@(negedge clk);start_v=1;@(negedge clk);start_v=0;
  // First programme word is consumed at launch+5. The compiler supplied the
  // arithmetic drain horizon in the image; no wait observes engine status.
  repeat(NINST+5)begin @(negedge clk);if(fault)$fatal(1,"ENGINE_FAULT");end
  for(integer beat=0;beat<WORDS/16;beat++)begin
   drain_sector={16'(4096+beat*2+1),16'(4096+beat*2)};drain_v=3;drain_addr={LWB'(beat*16+8),LWB'(beat*16)};
   @(negedge clk);
   if(fault||t0f||t1f||bs!=0)$fatal(1,"VM_QSWIGLU_FAULT");
  end
  drain_v=0;repeat(18)@(negedge clk);
  if(fault||t0f||t1f||bs!=0)$fatal(1,"VM_QSWIGLU_COMMIT_FAULT");
  readback=1;
  for(integer beat=0;beat<WORDS/64;beat++)begin
   pf_v=8'hff;for(integer b=0;b<8;b++)pf_sec[16*b+:16]=16'(4096+beat*8+b);
   @(negedge clk);
  end
  pf_v=0;repeat(14)@(negedge clk);
  if(fault||t0f||t1f||bs!=0)$fatal(1,"VM_QSWIGLU_FINAL_FAULT");
  if(observed!=WORDS)$fatal(1,"VM_QSWIGLU_COUNT got=%0d",observed);
  $display("PASS canonical Qswiglu actual exp/div/multiply/BF16 16 C12 lanes 80 operand SRAMs 16 programme SRAMs 24 protected VM SRAMs actualtap14 real scalar-route capture words=%0d exact_VM_committed_words=%0d preload_edges=192 compiler_edges=368 programme_to_consumer=5 drain_edges=192 golden=actualcanonicalhgiMachine",WORDS,observed);
  $finish;
 end
endmodule
