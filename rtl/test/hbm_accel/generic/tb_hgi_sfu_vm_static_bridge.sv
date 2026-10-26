`timescale 1ns/1ps
module tb_hgi_sfu_vm_static_bridge;
 localparam LWB=15;
 reg clk=0;always #0.416667 clk=~clk;
 wire [3:0] clk_lg;
 for(genvar g=0;g<4;g++)begin:lg_root
  // Separate clock nets permit a real missing-group-root negative control.
  assign clk_lg[g]=clk && !($test$plusargs("MUT_LG_CLOCK") && g==1 && rst_n);
 end
 reg rst_n=0,init=0;
 reg [7:0] pf_v=0,pf_scalar=0;
 reg [127:0] pf_sec=0;
 reg [15:0] pf_group=0;
 reg [119:0] pf_addr=0;
 reg [23:0] init_sec=0;
 wire [135:0] rq,nrq0,nrq1;
 wire [2247:0] wq,nwq0,nwq1;
 wire [2055:0] rr,brr,frr0;
 wire [2055:0] bridge_rr=rr & ~($test$plusargs("MUT_DROP")?(2056'd1<<256):2056'd0);
 wire [7:0] done,bdone,fdone0;
 wire [7:0] sv;wire [15:0] sg;wire [119:0] sa;
 wire [2047:0] sd;wire [63:0] sm;
 wire [3:0] sl;wire [95:0] sla;wire [127:0] sld;
 wire fault,sfault,t0f,t1f;
 reg [63:0] rd_re=0;reg [1535:0] rd_addr=0;
 wire [2047:0] rd_q;
 reg [15:0] vm_we=0;reg [383:0] vm_addr=0;reg [511:0] vm_data=0;
 reg [1:0] dv=0;reg [29:0] da=0;reg [31:0] dsec=0;
 wire [511:0] dd;wire [1:0] drv;
 wire [143:0] bs;
 function automatic [31:0] value(input integer a);value=32'h3e000000+32'(a*7);endfunction
 ot_hgi_sfu_vm_static_bridge dut(.clk(clk),.rst_n(rst_n),.clk_lg(clk_lg),.rst_lg_n({4{rst_n}}),.prefetch_v(pf_v),.prefetch_sector(pf_sec),.prefetch_group(pf_group),
 .prefetch_local_addr(pf_addr),.prefetch_scalar(pf_scalar),.prefetch_word(24'd0),.scalar_addr(96'd0),
 .local_rq(rq),.local_rr(bridge_rr),.stage_v(sv),.stage_group(sg),.stage_addr(sa),.stage_data(sd),.stage_mask(sm),
 .scalar_load(sl),.scalar_load_addr(sla),.scalar_data(sld),
 .drain_round_bf16(2'd0),.drain_v(dv),.drain_vm_sector(dsec),.drain_result_v(drv),.drain_data(dd),.local_wq(wq),.local_w_done(done),.fault(fault));
 ot_hgi_sfu_static_operand_store store(.clk(clk),.rst_n(rst_n),.scalar_load(sl),.scalar_enable(4'd0),.scalar_addr(sla),.scalar_data(sld),
 .rd_re(rd_re),.rd_addr(rd_addr),.rd_src(128'd0),.rd_q(rd_q),.vm_we(vm_we),.vm_waddr(vm_addr),.vm_wdata(vm_data),
 .stage_v(sv),.stage_group(sg),.stage_addr(sa),.stage_mask(sm),.stage_data(sd),
 .drain_v(dv),.drain_addr(da),.drain_data(dd),.drain_result_v(drv),.fault(sfault));
 ot_hbm_vm_lg_static_tap #(.READ_RETURN(14),.WRITE_RETURN(11)) mid(.clk(clk),.rst_n(rst_n),.local_rq(rq),.far_rq(136'd0),
 .local_wq(wq),.far_wq(2248'd0),.local_read(pf_v),.local_write({wq[2247],wq[1966],wq[1685],wq[1404],wq[1123],wq[842],wq[561],wq[280]}),
 .near_rq(nrq1),.near_wq(nwq1),.near_rr(frr0),.near_w_done(fdone0),.local_rr(rr),.local_w_done(done),.fault(t1f));
 ot_hbm_vm_lg_static_tap near_tap(.clk(clk),.rst_n(rst_n),.local_rq(136'd0),.far_rq(nrq1),.local_wq(2248'd0),.far_wq(nwq1),
 .local_read(8'd0),.local_write(8'd0),.near_rq(nrq0),.near_wq(nwq0),.near_rr(brr),.near_w_done(bdone),.far_rr(frr0),.far_w_done(fdone0),.fault(t0f));
 for(genvar b=0;b<8;b++)begin:bank
  wire [255:0] idata;
  for(genvar w=0;w<8;w++)assign idata[32*w+:32]=value((init_sec+b)*8+w);
  wire [280:0] iw={init,16'(init_sec+b),idata,8'hff};
  wire [770:0] br;
  assign brr[b*257+:257]=br[256:0];
  ot_vms_bank_static #(.RG(3),.WG(1)) memory(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),
  .rslot_v(1'b1),.rslot(2'd0),.wslot_v(1'b1),.wslot(3'd0),.rq({34'd0,nrq0[b*17+:17]}),.rr(br),
  .wq(init?iw:nwq0[b*281+:281]),.wq_done(bdone[b]),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
  .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(bs[b*18+:18]));
 end
 task tick;begin @(negedge clk);if(fault||sfault||t0f||t1f||bs!=0)$fatal(1,"BRIDGE_FAULT bridge=%b store=%b taps=%b%b bank=%h",fault,sfault,t0f,t1f,bs);end endtask
 integer checks=0;
 initial begin
  repeat(8)@(negedge clk);rst_n=1;
  // Setup writes target actual protected VM macro banks before the bridge's
  // normal epoch; reset then clears all return observers, retaining SRAM.
  for(integer s=0;s<16;s++)begin init=1;init_sec=24'(s*8);@(negedge clk);end
  init=0;repeat(20)@(negedge clk);rst_n=0;repeat(8)@(negedge clk);rst_n=1;
  for(integer beat=0;beat<16;beat++)begin
   pf_v=8'hff;
   for(integer b=0;b<8;b++)begin
    pf_sec[16*b+:16]=16'(beat*8+b);
    pf_group[2*b+:2]=2'(b/2);
    pf_addr[15*b+:15]=15'(beat*16+(b%2)*8);
   end
   tick();
  end
  pf_v=0;repeat(18)tick();
  for(integer beat=0;beat<16;beat++)begin
   rd_re='1;vm_we='1;
   for(integer l=0;l<16;l++)begin
    vm_addr[24*l+:24]=24'(beat*16+l);vm_data[32*l+:32]=value(beat*16+l);
    for(integer g=0;g<4;g++)rd_addr[24*(4*l+g)+:24]=24'(beat*16+l);
   end
   @(posedge clk);#0.001;
   for(integer l=0;l<16;l++)for(integer g=0;g<4;g++)begin
    if(rd_q[32*(4*l+g)+:32]!==value(beat*64+g*16+l))$fatal(1,"BRIDGE_WORD");checks++;
   end
   tick();
  end
  rd_re=0;vm_we=0;
  for(integer beat=0;beat<16;beat++)begin
   dv=3;da={15'(beat*16+8),15'(beat*16)};
   dsec={16'(1024+beat*2+1),16'(1024+beat*2)};
   tick();
  end
  dv=0;repeat(18)tick();
  // Read the actual committed VM words back through the same real tap and
  // copy them into group0, proving data and addresses beyond ACK observation.
  for(integer beat=0;beat<16;beat++)begin
   pf_v=0;
   for(integer s=0;s<2;s++)begin
    integer bank_id;
    bank_id=(1024+beat*2+s)%8;
    pf_v[bank_id]=1;pf_sec[16*bank_id+:16]=16'(1024+beat*2+s);
    pf_group[2*bank_id+:2]=0;pf_addr[15*bank_id+:15]=15'(beat*16+s*8);
   end
   tick();
  end
  pf_v=0;repeat(18)tick();
  for(integer beat=0;beat<16;beat++)begin
   rd_re=0;
   for(integer l=0;l<16;l++)begin rd_re[4*l]=1;rd_addr[24*(4*l)+:24]=24'(beat*16+l);end
   @(posedge clk);#0.001;
   for(integer l=0;l<16;l++)begin
    if(rd_q[32*(4*l)+:32]!==value(beat*16+l))$fatal(1,"BRIDGE_COMMITTED_VM_WORD");checks++;
   end
   tick();
  end
  $display("PASS SFU real VM24SRAM tap14 bridge local80SRAM exact_words=%0d prefetch=8sectors_per_edge drain=2sectors_per_edge commit=11 no_credits=1",checks);$finish;
 end
endmodule
