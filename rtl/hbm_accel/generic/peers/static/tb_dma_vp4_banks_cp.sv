`timescale 1ns/1ps
// H-HARDEN 2026-10-16: the folded DMA parent ot_hgi_dma_back_static_vp4_banks_cp programmed through the REAL host ingress
// (ot_hbm_host_static_ingress, AXI-lite F20..F30), in lockstep with the die composition it replaces (separate
// ot_static_cmd_target MODE1/CW308/RELF2/TGT_PIN collar -> ot_hgi_dma_back_static_vp4_banks, wired as die.v cp_dma_<q>).
// Valid DMA moves from the compiled calendar: every output of both must match on every edge, every write beat must
// arrive (sum nsec*rows), no fault; the identity strap is honoured (a calendar sent to target 105 is ignored).
`ifndef CP_MUT
`define CP_MUT 0
`endif
module tb_dma_vp4_banks_cp;
 localparam integer LEAD=8;
 reg clk=0; always #5 clk=~clk; reg rst_n=0;
 reg awv=0,wv=0,arv=0,rr_=1,br=1; reg [11:0] awa=0,ara=0; reg [31:0] wdat=0;
 wire awr,wr,bv,arr,rv; wire [1:0] bresp; wire [31:0] rdata;
 wire cfg_v,desc_v,launch_v,ing_fault; wire [7:0] cfg_target; wire [11:0] cfg_addr,desc_base; wire [255:0] cfg_data;
 wire [12:0] desc_limit; wire [15:0] desc_loops; wire any_active;
 ot_hbm_host_static_ingress #(.TARGET_MASK((256'd1<<104)|(256'd1<<105))) ing(
  .clk(clk),.rst_n(rst_n),.s_awvalid(awv),.s_awready(awr),.s_awaddr(awa),.s_wvalid(wv),.s_wready(wr),
  .s_wdata(wdat),.s_wstrb(4'hf),.s_bvalid(bv),.s_bready(br),.s_bresp(bresp),.s_arvalid(arv),.s_arready(arr),
  .s_araddr(ara),.s_rvalid(rv),.s_rready(rr_),.s_rdata(rdata),.block_ready(1'b1),.program_active(any_active),
  .program_fault(1'b0),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.fault(ing_fault));
 // ---- reference: the die composition (collar + DMA parent)
 wire r_cv,r_cfgd,r_flt,r_act; wire [307:0] r_cmd; wire [31:0] r_cyc;
 wire srca,donea,faulta,quieta,busya,reservea,banka,fillbanka,filla; wire [135:0] rqa; wire [2311:0] wda;
 wire [15:0] epocha,fillepocha; wire [11:0] sectorsa; wire [31:0] basea;
 wire srcb,doneb,faultb,quietb,busyb,reserveb,bankb,fillbankb,fillb; wire [135:0] rqb; wire [2311:0] wdb;
 wire [15:0] epochb,fillepochb; wire [11:0] sectorsb; wire [31:0] baseb; wire d_cfgd,d_flt,d_act;
 wire [2055:0] rr; reg [6:0] response_v[0:7]; reg [11:0] wa=0; reg [11:0] ack[0:4]; reg [31:0] tick=0;
 ot_static_cmd_target #(.MODE(1),.CW(308),.RELF(2),.NA(1),.NF(1),.TGT_PIN(1)) ref_cp(.clk(clk),.rst_n(rst_n),.tgt(8'd104),
  .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),
  .desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.tgt_active(busya),.tgt_fault(faulta),
  .a_we(),.a_addr(),.a_data(),.b_we(),.b_addr(),.b_data(),.run_v(),.run_base(),.run_count(),
  .cmd_v(r_cv),.cmd(r_cmd),.cycle(r_cyc),.configured(r_cfgd),.fault(r_flt),.active(r_act));
 ot_hgi_dma_back_static_vp4_banks ref_dbk(.clk(clk),.clk_bank({8{clk}}),.rst_n(rst_n),.stk(2'd0),.cycle(r_cyc),
  .mv_v(r_cv),.mv(r_cmd[290:64]),.issue_at(r_cmd[31:0]),.drain_at(r_cmd[63:32]),.mv_wb_bank(r_cmd[291]),.mv_wb_epoch(r_cmd[307:292]),
  .mv_src(srca),.mv_done(donea),.mv_fault(faulta),.quiet(quieta),.busy(busya),.rq(rqa),.rr(rr),.wb_reserve_v(reservea),
  .wb_reserve_bank(banka),.wb_fill_bank(fillbanka),.wb_reserve_epoch(epocha),.wb_fill_epoch(fillepocha),
  .wb_reserve_sectors(sectorsa),.wb_reserve_base(basea),.wb_fill_start(filla),.wb_ready(1'b1),.wd(wda),.wa(wa));
 // ---- DUT: the folded parent
 ot_hgi_dma_back_static_vp4_banks_cp #(.CP_MUT(`CP_MUT)) dut(.clk(clk),.clk_cp(clk),.clk_tab({2{clk}}),.rst_n(rst_n),.stk(2'd0),.tgt(8'd104),.clk_bank({8{clk}}),
  .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),
  .desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.cp_configured(d_cfgd),.cp_fault(d_flt),.cp_active(d_act),
  .mv_src(srcb),.mv_done(doneb),.mv_fault(faultb),.quiet(quietb),.busy(busyb),.rq(rqb),.rr(rr),.wb_reserve_v(reserveb),
  .wb_reserve_bank(bankb),.wb_fill_bank(fillbankb),.wb_reserve_epoch(epochb),.wb_fill_epoch(fillepochb),
  .wb_reserve_sectors(sectorsb),.wb_reserve_base(baseb),.wb_fill_start(fillb),.wb_ready(1'b1),.wd(wdb),.wa(wa));
 assign any_active=r_act|d_act;
 always @(posedge clk)begin
  tick<=tick+1;
  for(integer b=0;b<8;b=b+1)response_v[b]<=rst_n?{response_v[b][5:0],rqa[b*17+16]}:7'b0;
  begin:ACK_SUM integer n; n=0;for(integer b=0;b<8;b=b+1)if(wda[b*289+288])n=n+1;ack[0]<=12'(n);end
  for(integer k=1;k<5;k=k+1)ack[k]<=ack[k-1];
 end
 for(genvar b=0;b<8;b=b+1)begin:R assign rr[b*257+:257]={response_v[b][6],{8{32'h39c10000+32'(b*271)+tick}}}; end
 integer checks=0,beats=0,cmds=0;
 always @(negedge clk)if(rst_n)begin
  wa=ack[4];checks=checks+1;
  if({srca,donea,faulta,quieta,busya,reservea,banka,fillbanka,epocha,fillepocha,sectorsa,basea,filla,r_cfgd,r_flt,r_act}!==
     {srcb,doneb,faultb,quietb,busyb,reserveb,bankb,fillbankb,epochb,fillepochb,sectorsb,baseb,fillb,d_cfgd,d_flt,d_act})
   $fatal(1,"CP_FOLD control mismatch tick%0d",tick);
  if(rqa!==rqb)$fatal(1,"CP_FOLD rq mismatch tick%0d",tick);
  for(integer b=0;b<8;b=b+1)begin
   if(wda[b*289+288]!==wdb[b*289+288] || (wda[b*289+288] && wda[b*289+:289]!==wdb[b*289+:289]))$fatal(1,"CP_FOLD write beat mismatch tick%0d bank%0d",tick,b);
   if(wda[b*289+288])beats=beats+1;
  end
  if(r_cv)cmds=cmds+1;
  if(faulta||r_flt||ing_fault)$fatal(1,"CP_FOLD unexpected fault tick%0d dma%0d collar%0d ingress%0d",tick,faulta,r_flt,ing_fault);
 end
 task automatic axw(input [11:0] a,input [31:0] d);
  reg ad,dd;
  begin
   ad=0;dd=0;@(negedge clk);awv=1;awa=a;wv=1;wdat=d;
   while(!(ad&&dd))begin
    begin:HS reg ha,hw;ha=awv&&awr;hw=wv&&wr;@(posedge clk);#0.01;if(ha)begin ad=1;awv=0;end if(hw)begin dd=1;wv=0;end end
    @(negedge clk);
   end
   while(!bv)@(posedge clk);
   if(bresp!=0)$fatal(1,"CP_FOLD bresp %0d at %h",bresp,a);
   @(posedge clk);
  end
 endtask
 task automatic row(input [7:0] t,input [11:0] addr,input [255:0] data);
  begin axw(12'hf20,{12'd0,addr,t});for(integer p=0;p<8;p=p+1)axw(12'hf24,data[p*32+:32]);end
 endtask
 task automatic desc(input [7:0] t,input [11:0] base,input [12:0] lim,input [15:0] loops);
  begin axw(12'hf20,{12'd0,12'd0,t});axw(12'hf28,{7'd0,lim,base});axw(12'hf2c,{16'd0,loops});end
 endtask
 function automatic [226:0] descriptor(input integer nsec,input integer rows);
  descriptor={21'(nsec*8),20'(rows),16'd1,32'(nsec*32),40'h100000,3'd0,2'd0,16'd1,32'(((nsec+7)/8)*64),40'd0,3'd0,2'd1};
 endfunction
 localparam integer NE=7;
 integer NS[0:NE-1],RW[0:NE-1],DL[0:NE-1];
 integer expect_beats=0,at,e;
 initial begin : TMO #20000000; $display("CP_FOLD FAIL timeout"); $finish; end
 initial begin
  NS[0]=1;RW[0]=1;DL[0]=0; NS[1]=17;RW[1]=1;DL[1]=3; NS[2]=8;RW[2]=2;DL[2]=0; NS[3]=64;RW[3]=16;DL[3]=0;
  NS[4]=8;RW[4]=80;DL[4]=5; NS[5]=1023;RW[5]=1;DL[5]=2; NS[6]=16;RW[6]=3;DL[6]=0;
  for(integer b=0;b<8;b=b+1)response_v[b]=0; for(integer k=0;k<5;k=k+1)ack[k]=0;
  repeat(5)@(posedge clk);rst_n=1;repeat(5)@(posedge clk);
  // the strap selects 104: the same calendar addressed to 105 must be ignored by both
  at=20;
  for(e=0;e<NE;e=e+1)begin : ENT
   reg [511:0] ent; reg [307:0] pl;
   pl={16'h1234,1'b0,descriptor(NS[e],RW[e]),32'(at+17+DL[e]),32'(at+7)};
   ent={172'd0,pl,32'(at)};
   row(8'd105,12'h800+12'(2*e),~ent[255:0]);
   row(8'd104,12'h800+12'(2*e),ent[255:0]);row(8'd104,12'h800+12'(2*e+1),ent[511:256]);
   expect_beats=expect_beats+NS[e]*RW[e];
   at=at+((NS[e]+7)/8)*RW[e]+DL[e]+60;
  end
  desc(8'd104,12'd0,13'(NE),16'd1);
  repeat(10)@(posedge clk); axw(12'hf30,32'd1);
  repeat(at+400)@(posedge clk);
  if(cmds!=NE)$fatal(1,"CP_FOLD issued %0d of %0d commands",cmds,NE);
  if(beats!=expect_beats)$fatal(1,"CP_FOLD beats %0d expected %0d",beats,expect_beats);
  if(r_act||d_act||busya)$fatal(1,"CP_FOLD still active");
  $display("CP_FOLD PASS commands=%0d beats=%0d checks=%0d (folded parent == die composition, every output every edge)",cmds,beats,checks);
  $finish;
 end
endmodule
