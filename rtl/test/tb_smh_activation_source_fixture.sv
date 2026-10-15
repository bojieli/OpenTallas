`timescale 1ps/1fs
`default_nettype none
module tb_smh_activation_source_fixture(input wire clk,rst_n,
 output wire xw_en,xw_last,output wire [6:0]xw_addr,xw_grp,output wire [2047:0]xw_data,
 output reg fixture_done=0);
 parameter integer MUT=0;
 wire[11:0]root_clk={12{clk}};
 reg initializing=1,cfg_we=0,vm_start=0,engine_start=0;
 reg[9:0]cfg_addr=0;reg[255:0]vm_cfg=0,engine_cfg=0;
 reg[8*281-1:0]dq=0;wire[7:0]dq_done;
 wire[135:0]rq;wire[2055:0]rr;wire[143:0]bank_status;
 wire[201:0]vm_calendar;wire vm_calendar_v,vm_programme_done,vm_active,vm_fault;wire[31:0]vm_ordinal;
 wire busy,done,retire_fault,fault,programme_active;wire[31:0]programme_ordinal;
 ot_vms_calendar_static #(.W(202)) vm_programme(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(vm_cfg),
 .start_v(vm_start),.start_base(10'd0),.start_limit(11'd703),.start_loops(16'd1),.calendar(vm_calendar),.calendar_v(vm_calendar_v),.ordinal(vm_ordinal),.active(vm_active),.done(vm_programme_done),.fault(vm_fault));
 ot_hbm_sm_activation_programmed_static #(.MUT(MUT)) dut(.clk_program(root_clk[0]),.clk_control(root_clk[1]),
 .clk_aq_core(root_clk[3:2]),.clk_aq_delay(root_clk[5:4]),.clk_aq_encode(root_clk[7:6]),.clk_code(root_clk[11:8]),.rst_n(rst_n),
 .cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(engine_cfg),.start_v(engine_start),.start_base(10'd0),.start_limit(11'd703),.start_loops(16'd1),
 .rq(rq),.rr(rr),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),.xw_last(xw_last),.busy(busy),.done(done),.retire_fault(retire_fault),.fault(fault),.programme_active(programme_active),.programme_ordinal(programme_ordinal));
 wire[7:0]rslot_v=vm_calendar_v?vm_calendar[80+:8]:8'd0;
 wire[23:0]rslot=vm_calendar[96+:24];
 // Runtime owners come ONLY from the independent programme SRAM. DQ setup
 // occurs before either programme launches and never derives a read selector.
 for(genvar b=0;b<8;b=b+1)begin:BANK
  wire[1535:0]unused_payload;wire[256:0]rr0,rr1,rr3,rr4,rr5;wire[7:0]owner;
  hfd_vms_bank_static_rg6wg2 memory(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
   .rslot_v(rslot_v[b]),.rslot(rslot[b*3+:3]),.wslot_v(initializing?dq[b*281+280]:(vm_calendar_v&&vm_calendar[88+b])),.wslot(initializing?3'd6:vm_calendar[120+b*3+:3]),
   .rq0(17'd0),.rr0(rr0),.rq1(17'd0),.rr1(rr1),.rq2(rq[b*17+:17]),.rr2(rr[b*257+:257]),.rq3(17'd0),.rr3(rr3),.rq4(17'd0),.rr4(rr4),.rq5(17'd0),.rr5(rr5),
   .wq0(281'd0),.wq_done0(),.wq1(281'd0),.wq_done1(),.dq(dq[b*281+:281]),.dq_done(dq_done[b]),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(bank_status[b*18+:18]));
  integer main_writes=0,ecc_writes=0,main_reads=0,ecc_reads=0;
  always @(posedge clk)if(rst_n)begin
   if(memory.bank.u_a.w_ce_in)main_writes=main_writes+1;
   if(memory.bank.u_b.w_ce_in)ecc_writes=ecc_writes+1;
   if(memory.bank.u_a.r_ce_in)main_reads=main_reads+1;
   if(memory.bank.u_b.r_ce_in)ecc_reads=ecc_reads+1;
   if(memory.bank.u_c.w_ce_in||memory.bank.u_c.r_ce_in)$fatal(1,"native input unexpectedly used mirror");
   if(rr0[256]||rr1[256]||rr3[256]||rr4[256]||rr5[256])$fatal(1,"native read leaked to unselected bank group");
  end
 end
 reg[31:0]raw[0:40959];reg[25215:0]golden[0:39];reg[255:0]vm_image[0:702],engine_image[0:702];reg[15:0]sectors[0:639];
 reg[7:0]expected_dq_done[0:4095];reg[519:0]seen=0;
 integer cycle=0,dq_commits=0,requests=0,aq_waves=0,aq_blocks=0,beats=0,done_count=0,last_count=0;
 integer vm_cfg_commits=0,engine_cfg_commits=0,vm_programme_retired=0,engine_programme_retired=0;
 integer vm_start_edge=-1,engine_start_edge=-1,first_xw=-1,last_xw=-1,done_edge=-1;
 integer code_writes[0:15];
 for(genvar j=0;j<4;j=j+1)begin:CODE_COUNT
  for(genvar p=0;p<2;p=p+1)begin:PARITY
   for(genvar h=0;h<2;h=h+1)begin:HALF
    always @(posedge clk)if(rst_n&&dut.engine.codes[j].parity[p].half[h].mem.w_ce_in)code_writes[j*4+p*2+h]=code_writes[j*4+p*2+h]+1;
   end
  end
 end
 task tick;
 reg[2047:0]expected;integer idx;begin
  @(posedge clk);
  if(rst_n)begin
   if(vm_start)vm_start_edge=cycle;if(engine_start)engine_start_edge=cycle;
   if(vm_programme.u_program.w_ce_in)vm_cfg_commits=vm_cfg_commits+1;
   if(dut.programme.u_program.w_ce_in)engine_cfg_commits=engine_cfg_commits+1;
   for(integer b=0;b<8;b=b+1)if(dq[b*281+280])expected_dq_done[cycle+3][b]=1;
   if(rq[16])begin
    if(requests>=640||!vm_calendar_v||vm_ordinal!=requests+3||rslot_v!=8'hff)$fatal(1,"native independent VM programme owner phase wave%0d cyc%0d vmordinal%0d",requests,cycle,vm_ordinal);
    for(integer b=0;b<8;b=b+1)begin
     if(rslot[b*3+:3]!=2||rq[b*17+:17]!=={1'b1,16'(sectors[requests]+b)})$fatal(1,"native actual bank RG2 request identity wave%0d bank%0d",requests,b);
    end
    requests=requests+1;
   end else for(integer b=1;b<8;b=b+1)if(rq[b*17+16])$fatal(1,"native partial VM request wave");
   if(dut.engine.aq_v)begin
    if(aq_waves>=640)$fatal(1,"native too many actual AQ waves");
    for(integer b=0;b<8;b=b+1)for(integer w=0;w<8;w=w+1)begin
     idx=(int'(sectors[aq_waves])+b)*8+w;
     if(dut.engine.aq_x[b*256+w*32+:32]!==raw[idx])$fatal(1,"native actual VM to AQ raw FP32 mismatch wave%0d bank%0d word%0d",aq_waves,b,w);
    end
    aq_waves=aq_waves+1;aq_blocks=aq_blocks+2;
   end
  end
  #1;
  if(rst_n)begin
   if(bank_status!==0||vm_fault||fault||retire_fault)$fatal(1,"native activation fault cycle%0d engineStart%0d bank%h vm%0b core%0b code%h aqvo%b qv%b",cycle,engine_start_edge,bank_status,vm_fault,dut.engine.own_fault,dut.engine.code_fault,dut.engine.aq_vo,dut.engine.qv);
   if(dq_done!==expected_dq_done[cycle])$fatal(1,"native actual DQ commit phase cycle%0d",cycle);
   for(integer b=0;b<8;b=b+1)if(dq_done[b])dq_commits=dq_commits+1;
   if(vm_programme_done)vm_programme_retired=vm_programme_retired+1;
   if(dut.programme_done)engine_programme_retired=engine_programme_retired+1;
   if(xw_en)begin
    idx=int'(xw_addr)*13+int'(xw_grp);
    if(xw_addr>=40||xw_grp>=13||idx!=beats||seen[idx])$fatal(1,"native activation beat address/group order idx%0d expected%0d",idx,beats);
    expected=golden[xw_addr]>>(2048*int'(xw_grp));
    if(xw_data!==expected)$fatal(1,"native activation actual code SRAM beat payload mismatch idx%0d addr%0d group%0d cycle%0d got%h expected%h",idx,xw_addr,xw_grp,cycle,xw_data,expected);
    if(xw_last!==(idx==519))$fatal(1,"native activation last beat marker");
    if(first_xw<0)first_xw=cycle;last_xw=cycle;seen[idx]=1;beats=beats+1;if(xw_last)last_count=last_count+1;
   end
   if(done)begin
    if(fault||retire_fault||beats!=520||last_count!=1||busy)$fatal(1,"native unsafe Done before exact actual XWRITE completion");
    done_count=done_count+1;done_edge=cycle;
   end
  end
  cycle=cycle+1;@(negedge clk);
 end endtask
 string actdir,xfile;integer input_mutant=0;
 initial begin
  if(!$value$plusargs("ACTDIR=%s",actdir)||!$value$plusargs("XFILE=%s",xfile))$fatal(1,"actual VM input and programme mandatory");
  $readmemh({actdir,"/raw_fp32.hex"},raw);$readmemh(xfile,golden);$readmemh({actdir,"/vm.hex"},vm_image);$readmemh({actdir,"/activation.hex"},engine_image);$readmemh({actdir,"/request_sectors.hex"},sectors);
  if($value$plusargs("MUTANT=%d",input_mutant)&&input_mutant!=0)raw[0]=raw[0]^32'h80000000;
  for(integer c=0;c<4096;c=c+1)expected_dq_done[c]=0;for(integer j=0;j<16;j=j+1)code_writes[j]=0;
  wait(rst_n);@(negedge clk);
  // The raw tensor is written only through the actual DQ protocol.
  for(integer row=0;row<640;row=row+1)begin
   for(integer b=0;b<8;b=b+1)begin
    dq[b*281+:281]=0;dq[b*281+280]=1;dq[b*281+264+:16]=16'(row*8+b);dq[b*281+:8]=8'hff;
    for(integer w=0;w<8;w=w+1)dq[b*281+8+w*32+:32]=raw[(row*8+b)*8+w];
   end tick();
  end
  dq=0;repeat(8)tick();initializing=0;
  if(dq_commits!=5120)$fatal(1,"native missing actual DQ commits %0d",dq_commits);
  for(integer pc=0;pc<703;pc=pc+1)begin cfg_we=1;cfg_addr=10'(pc);vm_cfg=vm_image[pc];engine_cfg=engine_image[pc];tick();end
  cfg_we=0;repeat(5)tick();if(vm_cfg_commits!=703||engine_cfg_commits!=703)$fatal(1,"native both real programme SRAMs not loaded");
  vm_start=1;tick();vm_start=0;tick();engine_start=1;tick();engine_start=0;
  if(engine_start_edge!=vm_start_edge+2)$fatal(1,"native declared start boundary phase");
  while(cycle<engine_start_edge+730)tick();
  if(requests!=640||aq_waves!=640||aq_blocks!=1280||beats!=520||done_count!=1||!(&seen)||programme_active||vm_active||busy||vm_programme_retired!=1||engine_programme_retired!=1)$fatal(1,"native activation coverage request%0d aq%0d beats%0d Done%0d active%0b/%0b",requests,aq_blocks,beats,done_count,programme_active,vm_active);
  for(integer j=0;j<16;j=j+1)if(code_writes[j]!=160)$fatal(1,"native code SRAM write inventory macro%0d count%0d",j,code_writes[j]);
  $display("SM_ACTIVATION_NATIVE PASS rawFP32words40960 actualDQcommits5120 SW8RG6banks24SRAM programmeSRAM2_words703each codeSRAM16_actualwrites2560 AQ2_blocks1280 RQ640 actualVMprogrammeRG2only XWRITE520_exact first_postNBA%0d last_postNBA%0d safeDone%0d engineStart%0d VMstart%0d",first_xw-engine_start_edge,last_xw-engine_start_edge,done_edge-engine_start_edge,engine_start_edge,vm_start_edge);fixture_done=1;
 end
 initial begin #100000000;$fatal(1,"native activation timeout");end
endmodule
`default_nettype wire
