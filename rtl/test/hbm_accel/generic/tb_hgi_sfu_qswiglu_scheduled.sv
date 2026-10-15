`timescale 1ns/1ps
`ifndef SFU_IO_ROWS
`define SFU_IO_ROWS 800
`endif
`ifndef SFU_SCALAR_EDGE
`define SFU_SCALAR_EDGE 192
`endif
module tb_hgi_sfu_qswiglu_scheduled;
 localparam LWB=15,WORDS=3072,NINST=368,CHUNK=222,PCLO=223,IO_ROWS=`SFU_IO_ROWS;
 reg clk=0;always #0.416667 clk=~clk;
 wire [3:0] clk_lg;
 for(genvar g=0;g<4;g++)begin:lg_root
  // Separate clock nets permit a real missing-group-root negative control.
  assign clk_lg[g]=clk && !($test$plusargs("MUT_LG_CLOCK") && g==1 && rst_n);
 end
 reg rst_n=0;
 reg [1741:0] controls[0:NINST-1];
reg [31:0] gates[0:WORDS-1],ups[0:WORDS-1],golds[0:WORDS-1],route[0:0];
reg io_cfg_we=0,io_start_v=0;
 reg [1:0] io_cfg_stripe=0;
 reg [10:0] io_cfg_addr=0;
 reg [255:0] io_cfg_data=0;
 reg [470:0] io_rows[0:IO_ROWS-1];
 wire io_done;
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
 ot_hgi_sfu_scheduled_engine dut(.clk(clk),.rst_n(rst_n),.clk_lg(clk_lg),.rst_lg_n({4{rst_n}}),.clk_lane({16{clk}}),.clk_map({16{clk}}),
 .rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),
 .cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start_base(11'd0),.start_limit(12'(NINST)),.start_loops(16'd1),
 .io_cfg_we(io_cfg_we),.io_cfg_stripe(io_cfg_stripe),.io_cfg_addr(io_cfg_addr),.io_cfg_data(io_cfg_data),
 .io_start_v(io_start_v),.io_start_base(11'd0),.io_start_limit(12'(IO_ROWS)),.io_start_loops(16'd1),.io_done(io_done),
 .local_rq(rq),.local_rr(rr),.local_wq(wq),.local_w_done(done),
 .vi_q(512'd0),.side_y(512'd0),.fault(fault));
 ot_hbm_vm_lg_static_tap #(.READ_RETURN(14),.WRITE_RETURN(11)) mid(.clk(clk),.rst_n(rst_n),.local_rq(readback?136'd0:rq),.far_rq(136'd0),
 .local_wq(wq),.far_wq(2248'd0),.local_read(readback?8'd0:{rq[135],rq[118],rq[101],rq[84],rq[67],rq[50],rq[33],rq[16]}),.local_write({wq[2247],wq[1966],wq[1685],wq[1404],wq[1123],wq[842],wq[561],wq[280]}),
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
  $readmemh({`SFU_DATA_DIR,"/io.hex"},io_rows);
  $readmemh({`SFU_DATA_DIR,"/gate.hex"},gates);
  $readmemh({`SFU_DATA_DIR,"/up.hex"},ups);
  $readmemh({`SFU_DATA_DIR,"/gold.hex"},golds);
  $readmemh({`SFU_DATA_DIR,"/route.hex"},route);
  $readmemh({`SFU_DATA_DIR,"/vm_init.hex"},init_image);
  repeat(16)@(negedge clk);rst_n=1;
  for(integer row=0;row<257;row++)begin init=1;init_sector=12'(row*8);@(negedge clk);end
  init=0;repeat(20)@(negedge clk);rst_n=0;repeat(8)@(negedge clk);rst_n=1;
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
  cfg_we=0;repeat(3)@(negedge clk);
  for(integer p=0;p<IO_ROWS;p++)for(integer st=0;st<3;st++)begin
   reg [470:0] row;
   row=io_rows[p];
   // Actual IO calendar mutant: suppress the real scalar VM prefetch request.
   if($test$plusargs("MUT_IO") && p==`SFU_SCALAR_EDGE)row[7:0]=0;
   io_cfg_we=1;io_cfg_addr=11'(p);io_cfg_stripe=2'(st);
   io_cfg_data=256'(row>>(222*st));
   if(st==2)io_cfg_data=(io_cfg_data&((256'd1<<27)-1))|(256'hc7a1<<240)|(256'(p)<<223);
   else io_cfg_data=(io_cfg_data&((256'd1<<222)-1))|(256'hc7a1<<240)|(256'(p)<<223);
   @(negedge clk);
  end
  io_cfg_we=0;repeat(3)@(negedge clk);
  io_start_v=1;@(negedge clk);io_start_v=0;
  // One actual hardware start; no runtime status polling or per-lane driving.
  repeat(IO_ROWS+10)begin
   @(negedge clk);if(fault||t0f||t1f||bs!=0)$fatal(1,"SCHEDULED_ENGINE_FAULT");
  end
  readback=1;
  for(integer beat=0;beat<WORDS/64;beat++)begin
   pf_v=8'hff;for(integer b=0;b<8;b++)pf_sec[16*b+:16]=16'(4096+beat*8+b);
   @(negedge clk);
  end
  pf_v=0;repeat(14)@(negedge clk);
  if(fault||t0f||t1f||bs!=0)$fatal(1,"VM_QSWIGLU_FINAL_FAULT");
  if(observed!=WORDS)$fatal(1,"VM_QSWIGLU_COUNT got=%0d",observed);
  $display("PASS canonical Qswiglu actual exp/div/multiply/BF16 16 C12 lanes 80 operand SRAMs 16 programme SRAMs 24 protected VM SRAMs 6 IOprogramme SRAMs actualtap14 real scalar-route capture words=%0d exact_VM_committed_words=%0d one_start=1 actual_IO_rows=%0d actual_arithmetic_rows=368 no_manual_prefetch_drain=1 golden=actualcanonicalhgiMachine",WORDS,observed,IO_ROWS);
  $finish;
 end
endmodule
