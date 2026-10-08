`timescale 1ps/1fs
// One real endpoint, full datapath and full PF384 transaction; no fabric/die simulation.
// Reference reducer sees only the transactions actually accepted by the endpoint.
module tb_ha2_truecredit_endpoint;
 localparam integer FW=512,PWT=545,PF=384,OF=48,ROF=24;
 reg clk=0,pclk=0;always #416.666667 clk=~clk;always #500 pclk=~pclk;
 reg rst_n=0,prst_n=0,go=0;
 bit corrupt_golden;
 initial begin
  corrupt_golden=$test$plusargs("CORRUPT_GOLDEN");
 end
 reg [7:0] rxv=0;reg [8*PWT-1:0] rxf=0;
 wire ready,fault;wire [31:0] idx,stall;wire [1:0] rd;
 reg [2*FW-1:0] inj_data;
 wire [7:0] txv,credit;wire [8*PWT-1:0] txf;
 wire [3:0] dv;wire [4*PWT-1:0] df;
 always @*for(integer i=0;i<2;i=i+1)for(integer l=0;l<16;l=l+1)
  inj_data[i*FW+l*32+:32]=32'h3f800000+(32'(idx[i*16+:16])<<6)+l;
 ot_hbm_accel_tu_endpoint_owner_truecredit #(.OWNER_TRUE_CREDIT(1),.TC_FWD(7),.TC_RET(7),.ENABLE(1),.OWNER_REDUCER(1),.OWNER_BANKED_HALF(1),.PFMAX(PF),.LANES(16)) dut
  (.clk(clk),.rst_n(rst_n),.pclk(pclk),.prst_n(prst_n),.rank(8'd19),.pf(16'(PF)),.go(go),
   .context_operation(64'd1),.context_phase(32'd0),.endpoint_rearm_ready(ready),
   .inj_idx(idx),.inj_rd(rd),.inj_data(inj_data),.ph_tx_v(txv),.ph_tx_flit(txf),.sw_cr_ret(8'b0),
   .ph_rx_v(rxv),.ph_rx_flit(rxf),.rx_credit(credit),.del_valid(dv),.del_flit(df),.fault(fault),.stat_credit_stall(stall));
 wire ref_v,ref_bad;wire [15:0] ref_m;wire [FW-1:0] ref_d;
 ot_ha2_tu_owner_adapter #(.NC(8),.NOG(8),.PFMAX(PF),.LANES(16),.BF16(1),.INJ(2),.NPT(8),.LAT(7),.SLOTREG(1)) reference
  (.clk(clk),.rst_n(rst_n),.active(dut.g_candidate.g_on.context_bound),.arm(dut.g_candidate.g_on.arm),
   .rank(8'd19),.pf(16'(PF)),.h_v(dut.g_candidate.g_on.h_v),.h_d(dut.g_candidate.g_on.h_d),
   .p_v(dut.g_candidate.g_on.partial_v),.p_flit(dut.g_candidate.g_on.partial_flit),
   .r_v(ref_v),.r_m(ref_m),.r_d(ref_d),.dupe(ref_bad),.issue_o(),.quiet());
 reg [FW-1:0] golden[0:ROF-1];reg [ROF-1:0] reference_seen=0,delivered_seen=0;
 integer cycles=0,issued=0,peer_received=0,delivered=0,hub_stalls=0,peer_stalls=0;
 integer first_issue=-1,last_deliver=-1;
 always @(posedge clk)begin
  if(rst_n)begin
   cycles=cycles+1;
   for(integer i=0;i<2;i=i+1)if(rd[i])begin issued=issued+1;if(first_issue<0)first_issue=cycles;end
   for(integer p=0;p<8;p=p+1)begin
    // Observe the real registered receiver credit and the actual FIFO pop.
    // This assertion applies to both baseline and mutated runs.
    if(dut.g_candidate.g_on.rb_pop[p] && !dut.g_candidate.g_on.rb_head[p][PWT-1] &&
       !dut.g_candidate.g_on.owner_p_r[p])
      $fatal(1,"ENDPOINT_CREDIT_VIOLATION peer=%0d cycle=%0d",p,cycles);
    if(credit[p])peer_received=peer_received+1;
    if(!dut.g_candidate.g_on.rb_empty[p]&&!dut.g_candidate.g_on.owner_p_r[p])peer_stalls=peer_stalls+1;
   end
   if(dut.g_candidate.g_on.started&&dut.g_candidate.g_on.k<PF&&!(&dut.g_candidate.g_on.hub_issue_ready))hub_stalls=hub_stalls+1;
   #1;
   if(fault||ref_bad)$fatal(1,"ENDPOINT_FAIL unexpected fault endpoint=%b ref=%b cycle=%0d",fault,ref_bad,cycles);
   if(ref_v)begin
    if(ref_m>=ROF||reference_seen[ref_m])$fatal(1,"ENDPOINT_FAIL reference identity");
    golden[ref_m]=ref_d ^ (corrupt_golden ? 512'b1 : 512'b0);reference_seen[ref_m]=1;
   end
   for(integer i=0;i<4;i=i+1)if(dv[i])begin:check_delivery
    integer m;
    m=integer'(df[i*PWT+FW+:16])-19*ROF;
    if(m<0||m>=ROF||delivered_seen[m]||!reference_seen[m])$fatal(1,"ENDPOINT_FAIL missing/duplicate delivery m=%0d",m);
    if(df[i*PWT+:FW]!==golden[m] || df[i*PWT+FW+16+:17]!=={1'b1,8'hff,8'd2})
      $fatal(1,"ENDPOINT_FAIL numerical or identity mismatch m=%0d",m);
    delivered_seen[m]=1;delivered=delivered+1;last_deliver=cycles;
   end
   if(delivered==ROF)begin
    if(issued!=PF||peer_received!=OF*7||peer_stalls==0)$fatal(1,"ENDPOINT_FAIL traffic coverage issued=%0d peer=%0d stalls=%0d",issued,peer_received,peer_stalls);
    $display("PASS_HA2_TRUECREDIT_ENDPOINT lanes=16 PF=384 owner_results=%0d issued=%0d peer_flits=%0d hub_stalls=%0d peer_stalls=%0d first_issue=%0d last_delivery=%0d elapsed=%0d",delivered,issued,peer_received,hub_stalls,peer_stalls,first_issue,last_deliver,last_deliver-first_issue+1);
    $display("SCOPE one endpoint own-reduction outputs bit-exact vs unchanged adapter on accepted transactions; not full collective/fabric or physical adoption");
    $finish;
   end
   if(cycles>20000)$fatal(1,"ENDPOINT_FAIL simulation-cycle bound delivered=%0d peer=%0d issued=%0d",delivered,peer_received,issued);
  end
 end
 initial begin
  repeat(5)@(negedge clk);rst_n=1;prst_n=1;
  wait(ready);@(negedge clk);go=1;@(negedge clk);go=0;
  repeat(12)@(negedge pclk);
  // Burst all seven remote contributors, then force the real p_r path to drain.
  for(integer m=0;m<OF;m=m+1)begin
   @(negedge pclk);rxv=8'hf7;
   for(integer c=0;c<8;c=c+1)begin
    rxf[c*PWT+FW+:33]={1'b0,8'd19,8'(c),16'(m)};
    for(integer l=0;l<16;l=l+1)rxf[c*PWT+l*32+:32]=32'h3f000000+(c<<12)+(m<<5)+l;
   end
  end
  @(negedge pclk);rxv=0;
 end
endmodule
