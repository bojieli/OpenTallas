`timescale 1ps/1fs
// One real endpoint, full datapath and full PF384 transaction; no fabric/die simulation.
// Reference reducer sees only the transactions actually accepted by the endpoint.
module tb_hbm_collective_native_composed;
 parameter integer PACKET_SRAM=1;
 localparam integer FW=512,PWT=545,PF=384,OF=48,ROF=24;
 reg clk=0,pclk=0;always #416.667 clk=~clk;initial begin #137;forever #416.667 pclk=~pclk;end
 wire rst_n,prst_n;reg go=0,por=1,traffic_start=0;reg[63:0]operation=1;
 bit corrupt_golden;
 initial begin
  corrupt_golden=$test$plusargs("CORRUPT_GOLDEN");
 end
 wire [7:0]rxv;wire[8*PWT-1:0]rxf;
 wire ready,fault;wire [31:0] idx,stall;wire [1:0] rd;
 reg [2*FW-1:0] inj_data;
 wire [7:0] txv,credit;wire [8*PWT-1:0] txf;
 wire [3:0] dv;wire [4*PWT-1:0] df;
 always @*for(integer i=0;i<2;i=i+1)for(integer l=0;l<16;l=l+1)
  inj_data[i*FW+l*32+:32]=32'h3f800000+(32'(idx[i*16+:16])<<6)+l;
 wire cold_start,session_admit,running,peer_quiet,debt_zero,session_fault,data_quiet,phy_quiet;
 wire[23:0]epoch;wire[7:0]source_debt,source_initial;
 wire[7:0]txgv,txgr,txav,txar,rxgv,rxgr,rxav,rxar,peer_retire;
 wire[575:0]txgw,txaw,rxgw,rxaw;wire[8*PWT-1:0]peer_data;
 tb_native_peer_session peer(clk,pclk,por,traffic_start,rst_n,prst_n,cold_start,session_admit,epoch,
 data_quiet,phy_quiet,source_debt,source_initial,txv,txf,rxv,rxf,
 rxgv,rxar,rxgr,rxav,rxgw,rxaw,txgv,txar,txgr,txav,txgw,txaw,
 peer_retire,peer_data,running,peer_quiet,debt_zero,session_fault);
 ot_hbm_collective_native_link_candidate #(.LINK_PROTECTION(1),.PACKET_SRAM(PACKET_SRAM),.OWNER_TRUE_CREDIT(1),.TC_FWD(7),.TC_RET(7),.ENABLE(1),.OWNER_REDUCER(1),.OWNER_BANKED_HALF(1),.PFMAX(PF),.LANES(16)) dut
  (.clk(clk),.rst_n(rst_n),.pclk(pclk),.prst_n(prst_n),.rank(8'd19),.pf(16'(PF)),.go(go),
   .context_operation(operation),.context_phase(32'd0),.endpoint_rearm_ready(ready),
   .cold_link_start(cold_start),.link_epoch(epoch),.session_admit(session_admit),
   .source_debt_zero(source_debt),.source_initial_ack_seen(source_initial),.data_queues_quiet(data_quiet),.endpoint_quiet_phy(phy_quiet),
   .tx_grant_valid(txgv),.tx_grant_ready(txgr),.tx_grant_word(txgw),.tx_ack_valid(txav),.tx_ack_ready(txar),.tx_ack_word(txaw),
   .rx_grant_valid(rxgv),.rx_grant_ready(rxgr),.rx_grant_word(rxgw),.rx_ack_valid(rxav),.rx_ack_ready(rxar),.rx_ack_word(rxaw),
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
 integer first_issue=-1,last_deliver=-1,cold_starts=0;
 reg[1535:0]all_delivered=0;
 reg[383:0]peer_partials=0;reg[23:0]peer_results=0;
 integer peer_partial_count=0,peer_result_count=0;
 // Native reservations precede its actual protected TX flight. This is a
 // structural assertion, not a testbench credit counter feeding the DUT.
 for(genvar p=0;p<8;p=p+1)begin:g_reservation_check
  integer final_retired=0;
  always @(posedge clk)if(rst_n)begin
   if(credit[p])final_retired=final_retired+1;
   if(peer.g_port[p].reservations-final_retired>64||final_retired>peer.g_port[p].reservations)
    $fatal(1,"NATIVE_GATE_FORWARD_WINDOW p=%0d",p);
  end
  always @(posedge clk)if(rst_n&&dut.g_candidate.g_on.tv[p] &&
   !(dut.g_candidate.g_on.g_txq[p].g_protected_tx.u_credit_source.reserve_valid &&
     dut.g_candidate.g_on.g_txq[p].g_protected_tx.u_credit_source.reserve_ready))
    $fatal(1,"NATIVE_GATE_RESERVATION_VIOLATION p=%0d",p);
 end
 always @(posedge pclk)if(prst_n)for(integer p=0;p<8;p=p+1)if(peer_retire[p])begin:check_peer
  integer f,m,destination;reg[511:0]expected;
  f=integer'(peer_data[p*PWT+FW+:16]);destination=integer'(peer_data[p*PWT+FW+24+:8]);
  if(peer_data[p*PWT+PWT-1])begin
   m=f-19*ROF;
   if(m<0||m>=ROF||peer_results[m]||!reference_seen[m]||peer_data[p*PWT+:FW]!==golden[m]||peer_data[p*PWT+FW+16+:17]!=={1'b1,8'hff,8'd2})
    $fatal(1,"NATIVE_GATE_PEER_RESULT numerical or identity mismatch");
   peer_results[m]=1;peer_result_count=peer_result_count+1;
  end else begin
   if(destination<16||destination>=24||destination==19||f>=48||peer_data[p*PWT+FW+16+:8]!=3)$fatal(1,"NATIVE_GATE_PEER_PARTIAL identity");
   m=(destination%8)*48+f;
   for(integer l=0;l<16;l=l+1)expected[l*32+:32]=32'h3f800000+(m<<6)+l;
   if(peer_partials[m]||peer_data[p*PWT+:FW]!==expected)$fatal(1,"NATIVE_GATE_PEER_PARTIAL payload or duplicate");
   peer_partials[m]=1;peer_partial_count=peer_partial_count+1;
  end
 end
 always @(posedge clk)begin
  if(cold_start)begin cold_starts=cold_starts+1;if(cold_starts>1||go)$fatal(1,"NATIVE_GATE_CONTEXT_REGRANT");end
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
   if($test$plusargs("CHANGE_CONTEXT_BUSY")&&operation==2&&dut.g_candidate.g_on.context_fault)$fatal(1,"NATIVE_GATE_CONTEXT_REJECTED");
   if(fault||ref_bad||session_fault)$fatal(1,"ENDPOINT_FAIL unexpected fault endpoint=%b ref=%b session=%b cycle=%0d",fault,ref_bad,session_fault,cycles);
   if(ref_v)begin
    if(ref_m>=ROF||reference_seen[ref_m])$fatal(1,"ENDPOINT_FAIL reference identity");
    golden[ref_m]=ref_d ^ (corrupt_golden ? 512'b1 : 512'b0);reference_seen[ref_m]=1;
   end
   for(integer i=0;i<4;i=i+1)if(dv[i])begin:check_delivery
    integer m;
    integer global_index;reg[511:0]expected_external;
    global_index=integer'(df[i*PWT+FW+:16]);m=global_index-19*ROF;
    if(global_index<0||global_index>=1536||all_delivered[global_index])$fatal(1,"ENDPOINT_FAIL missing/duplicate global delivery");
    if(m>=0&&m<ROF)begin
     if(delivered_seen[m]||!reference_seen[m])$fatal(1,"ENDPOINT_FAIL missing/duplicate own delivery m=%0d",m);
     if(df[i*PWT+:FW]!==golden[m] || df[i*PWT+FW+16+:17]!=={1'b1,8'hff,8'd2})
      $fatal(1,"ENDPOINT_FAIL numerical or identity mismatch m=%0d",m);
     delivered_seen[m]=1;
    end else begin
     for(integer l=0;l<16;l=l+1)expected_external[l*32+:32]=32'h3e800000+(global_index<<4)+l;
     if(df[i*PWT+:FW]!==expected_external||df[i*PWT+FW+16+:17]!=={1'b1,8'hff,8'(global_index/192)})
      $fatal(1,"ENDPOINT_FAIL external result transport or identity");
    end
    all_delivered[global_index]=1;delivered=delivered+1;last_deliver=cycles;
   end
   if(delivered==1536&&ready&&peer_quiet&&debt_zero)begin
    if(issued!=PF||peer_received!=OF*7+1512||peer_stalls==0||peer_partial_count!=336||peer_result_count!=24||cold_starts!=1||epoch!=1)$fatal(1,"ENDPOINT_FAIL traffic coverage issued=%0d peer=%0d stalls=%0d",issued,peer_received,peer_stalls);
    $display("PASS_NATIVE_COMPOSED_ENDPOINT lanes=16 PF=384 total_deliveries=%0d issued=%0d peer_flits=%0d hub_stalls=%0d peer_stalls=%0d first_issue=%0d last_delivery=%0d elapsed=%0d",delivered,issued,peer_received,hub_stalls,peer_stalls,first_issue,last_deliver,last_deliver-first_issue+1);
    $display("SCOPE one endpoint own24 arithmetic golden unchanged; external1512 results deterministic transport fixtures; actual full-duplex credit, finite storage, session and CDC; PHY ACK fixtures; no fullfabric/physical adoption");
    $finish;
   end
   if(cycles>20000)$fatal(1,"ENDPOINT_FAIL simulation-cycle bound delivered=%0d peer=%0d issued=%0d",delivered,peer_received,issued);
  end
 end
 initial begin
  repeat(5)@(negedge clk);por=0;
  wait(running&&ready);@(negedge clk);go=1;@(negedge clk);go=0;
  repeat(12)@(negedge pclk);traffic_start=1;
  if($test$plusargs("CHANGE_CONTEXT_BUSY"))begin
   wait(issued>4);@(negedge clk);operation=2;
  end
 end
 initial begin
  // Startup fence diagnostic, in simulation cycles only; no host resource timeout.
  repeat(2000)@(posedge clk);if(!running)$fatal(1,"NATIVE_GATE_SESSION_STARTUP_TIMEOUT");
 end
endmodule
