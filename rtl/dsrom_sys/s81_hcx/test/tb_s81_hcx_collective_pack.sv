`timescale 1ns/1ps
// Actual four-rank digital collective + actual native compactor. Only PHY
// wires have zero external flight. VM port commits are boundary stimulus;
// this does not qualify a native VM provider or physical inter-die timing.
module tb_s81_hcx_collective_pack;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,issue=0,commit=0,start=0;
 reg[511:0]raw[0:3],want[0:1],got[0:1];
 wire[11:0]txv,rxv;wire[6143:0]txd,rxd;
 wire[15:0]we;wire[8191:0]data;wire[3:0]ef;
 wire wv,done,pf;wire[13:0]wa;wire[15:0]wm;wire[511:0]wd;
 reg[3:0]commit_pipe=0;
 integer cyc=0,t0,wi0=-1,wi1=-1,dc=-1,nwrites=0;string dir;
 generate for(genvar r=0;r<4;r=r+1)begin:R
`ifdef MUT_RANK
  wire sv=issue && r!=2;
`else
  wire sv=issue;
`endif
  s81_static_tp4_rank #(.RANK(r))rank(
   .clk(clk),.rst_n(rn),.issue_slot(issue),.src_valid(sv),.src_data(raw[r]),
   .tag(32'h48435831),.seq(16'd0),.last(1'b1),.rankmask(4'hf),
   .commit_slot(commit),.commit_tag(32'h48435831),.commit_seq(16'd0),
   .commit_last(1'b1),.commit_rankmask(4'hf),.commit_rows({15'd3,15'd2,15'd1,15'd0}),
   .phy_tx_valid(txv[3*r+:3]),.phy_tx_data(txd[1536*r+:1536]),
   .phy_rx_valid(rxv[3*r+:3]),.phy_rx_data(rxd[1536*r+:1536]),
   .vm_we(we[4*r+:4]),.vm_rows(),.vm_data(data[2048*r+:2048]),.fault(ef[r]));
  for(genvar g=0;g<3;g=g+1)begin:L
   localparam integer PEER=g<r ? g:g+1, REV=r<PEER ? r:r-1;
   assign rxv[3*r+g]=txv[3*PEER+REV];
   assign rxd[1536*r+512*g+:512]=txd[1536*PEER+512*REV+:512];
  end
 end endgenerate
 ot_s81_hcx_gatherpack #(.WL(4),.R_CYC({4{16'd6}}))pack(
  .clk(clk),.rst_n(rn),.start(start),.raw_base_row(14'd2624),
  .i_v(we[3:0]),.i_d(data[2047:0]),.wq_v(wv),.wq_row(wa),.wq_mask(wm),.wq_d(wd),
  .wq_commit(commit_pipe[3]),.done(done),.fault(pf));
 always @(posedge clk)begin
  cyc<=cyc+1;commit_pipe<={commit_pipe[2:0],wv};
  if(wv)begin
   if(wm!=16'hffff)$fatal(1,"HCX_COLLECTIVE_PACK FAIL partialwrite");
   got[wa-2624]<=wd;
   if(nwrites==0)wi0=cyc-t0;else wi1=cyc-t0;nwrites=nwrites+1;
  end
  if(done)dc=cyc-t0;
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
  $readmemh({dir,"/raw4.mem"},raw);$readmemh({dir,"/want2.mem"},want);
  repeat(3)@(negedge clk);rn=1;t0=cyc;
  for(integer step=0;step<20;step=step+1)begin
   issue=step==0;start=step==0;commit=step==4;@(negedge clk);
  end
  if(nwrites!=2||wi0!=8||wi1!=9||dc!=15)$fatal(1,"HCX_COLLECTIVE_PACK FAIL calendar writes%0d,%0d done%0d",wi0,wi1,dc);
  if(|ef||pf)$fatal(1,"HCX_COLLECTIVE_PACK FAIL endpoint%h pack%0d fixedwrites%0d,%0d done%0d",ef,pf,wi0,wi1,dc);
  if(got[0]!==want[0]||got[1]!==want[1])$fatal(1,"HCX_COLLECTIVE_PACK FAIL actualHCP24wordpayload");
  $display("HCX_COLLECTIVE_PACK PASS actual4rankRTL+CRC+parallelcompactor actualHCP24words fixedwrites%0d,%0d completion%0d",wi0,wi1,dc);$finish;
 end
endmodule
