`timescale 1ns/1ps
// Extension of tb_hbm_integrated_prior_debt: the actual shared owner, not a
// replacement ledger/provider. Native observations are accepted request and
// matched ORIGINAL-consumer edges; service responses echo observed wire tags.
// One binary, independently selected cases. No engine/arithmetic qualification.
module tb_hbm_integrated_borrow_control_russell;
 reg clk=0; always #500 clk=~clk;
 reg por_n=0;
 reg native_clients_drained=1,cdc_drained=1;
 reg [3:0] native_req_v=0,native_req_ready=0,native_rsp_v=0,native_rsp_ready=0;
 reg [3:0] observe_req_we=0,observe_rsp_we=0;
 reg [63:0] observe_req_tag=0,observe_rsp_tag=0;
 wire [3:0] observe_req=native_req_v&native_req_ready;
 wire [3:0] response_authorized;
 wire [3:0] observe_rsp=native_rsp_v&native_rsp_ready&response_authorized;
 wire [3:0] return_offer=native_rsp_v;
 reg [31:0] native_job=32'h92345678;
 reg [3:0] native_gen=4'h9;
 reg [16:0] native_token=17'h10001;
 reg [19:0] native_pos=20'hfffff;
 wire native_credit_empty;
 reg [2:0] lease_v=0,borrower_quiet=7,release_v=0;
 reg [95:0] lease_job=0,release_job=0;
 reg [11:0] lease_gen=0,release_gen=0;
 reg [50:0] lease_token=0,release_token=0;
 reg [59:0] lease_pos=0,release_pos=0;
 wire [2:0] lease_granted,release_r;
 reg [3:0] req_v=0,req_we=0,rsp_rdy=0;
 reg [127:0] req_addr=0,req_wstrb=0;
 reg [1023:0] req_wdata=0;
 reg [63:0] req_tag=0;
 wire [3:0] req_rdy,rsp_v,rsp_we;
 wire [63:0] rsp_tag;
 wire [1023:0] rsp_data;
 wire m_req_v,m_req_we,m_rsp_rdy,idle,fault;
 reg m_req_rdy=0,m_rsp_v=0,m_rsp_we=0;
 wire [31:0] m_req_addr,m_req_wstrb;
 wire [255:0] m_req_wdata;
 wire [15:0] m_req_tag;
 reg [15:0] m_rsp_tag=0;
 reg [255:0] m_rsp_data=0;
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) dut(.*);

 // Independent source receipts: not cleared by DUT reset, grant or response
 // OFFER. The test process's first cold boot starts with no external copies.
 reg live[0:3][0:31];
 reg [15:0] saved_tag[0:3][0:31];
 reg saved_we[0:3][0:31];
 reg [31:0] saved_job[0:3][0:31];
 reg [3:0] saved_gen[0:3][0:31];
 reg [16:0] saved_token[0:3][0:31];
 reg [19:0] saved_pos[0:3][0:31];
 integer external_debt=0,accepted_native=0,consumed_native=0,cycle=0;
 reg service_live=0;
 reg [336:0] original_req=0;
 reg [72:0] original_lease=0;
 reg [255:0] original_response=0;
 integer service_accepted=0,service_consumed=0;
 wire [336:0] actual_backend={m_req_we,m_req_addr,m_req_wdata,m_req_wstrb,m_req_tag};
 integer c,s,found,free_slot;
 always @(posedge clk) begin
  cycle=cycle+1;
  if(por_n) begin
   for(c=0;c<4;c=c+1) begin
    if(observe_rsp[c]) begin
     found=-1;
     for(s=0;s<32;s=s+1)
      if(live[c][s]&&saved_tag[c][s]==observe_rsp_tag[c*16+:16]&&
         saved_we[c][s]==observe_rsp_we[c]&&saved_job[c][s]==native_job&&
         saved_gen[c][s]==native_gen&&saved_token[c][s]==native_token&&
         saved_pos[c][s]==native_pos) begin
       if(found>=0)$fatal(1,"duplicate independent receipt");
       found=s;
      end
     if(found<0)$fatal(1,"native consumed without original CP/tag/kind receipt cycle=%0d",cycle);
     live[c][found]=0;external_debt=external_debt-1;consumed_native=consumed_native+1;
    end
    if(observe_req[c]) begin
     free_slot=-1;
     for(s=0;s<32;s=s+1)begin
      if(live[c][s]&&saved_tag[c][s]==observe_req_tag[c*16+:16])
       $fatal(1,"duplicate native accept in bench");
      if(!live[c][s]&&free_slot<0)free_slot=s;
     end
     if(free_slot<0)$fatal(1,"external native acceptance overflowed32 slots");
     live[c][free_slot]=1;saved_tag[c][free_slot]=observe_req_tag[c*16+:16];
     saved_we[c][free_slot]=observe_req_we[c];saved_job[c][free_slot]=native_job;
     saved_gen[c][free_slot]=native_gen;saved_token[c][free_slot]=native_token;
     saved_pos[c][free_slot]=native_pos;external_debt=external_debt+1;accepted_native=accepted_native+1;
    end
   end
   if(m_req_v) begin
    if(actual_backend!==original_req)
     $fatal(1,"full337 backend tuple changed from held caller cycle=%0d got=%h expected=%h",cycle,actual_backend,original_req);
    if(m_req_rdy)begin
     if(service_live)$fatal(1,"second backend accept before original consumer");
     service_live=1;service_accepted=service_accepted+1;
    end
   end
   if(rsp_v!=0)begin
    if(rsp_v!==4'b0100||rsp_tag[32+:16]!==original_req[15:0]||
       rsp_we[2]!==original_req[336]||rsp_data[512+:256]!==original_response)
     $fatal(1,"full273 client terminal/route mismatch cycle=%0d",cycle);
    if(|(rsp_v&rsp_rdy))begin
     if(!service_live)$fatal(1,"client terminal without accepted provider debt");
     service_live=0;service_consumed=service_consumed+1;
    end
   end
  end
 end
 task settle;begin #1;end endtask
 task step;begin @(posedge clk);#1;@(negedge clk);end endtask
 task require(input bit ok,input string msg);begin
  if(!ok)$fatal(1,"%s cycle=%0d external=%0d service=%0d fault=%b empty=%b grants=%b",msg,cycle,external_debt,service_live,fault,native_credit_empty,lease_granted);
 end endtask
 task idle_steps(input integer n);begin repeat(n)step();end endtask
 task request_lease;begin
  lease_job[32+:32]=32'hfe012345;lease_gen[4+:4]=4'he;
  lease_token[17+:17]=17'h10021;lease_pos[20+:20]=20'hffeed;
  lease_v=3'b010;borrower_quiet=3'b111;
 end endtask
 task wait_owned;integer n;begin
  n=0;while(lease_granted!=3'b010&&n<8)begin step();n=n+1;end
  require(lease_granted==3'b010&&!fault,"real SU lease grant absent after source quiet interval");
  original_lease={lease_pos[20+:20],lease_token[17+:17],lease_gen[4+:4],lease_job[32+:32]};
  lease_v=0;borrower_quiet=3'b101;
 end endtask
 task native_accept(input integer client,input integer tag,input bit we);begin
  native_req_v=4'b0001<<client;native_req_ready=4'b0001<<client;
  observe_req_tag[client*16+:16]=16'(tag);observe_req_we[client]=we;
  step();native_req_v=0;native_req_ready=0;settle();
  require(!native_credit_empty&&lease_granted==0,"accepted native debt did not exclude borrow");
 end endtask
 task native_offer(input integer client,input integer tag,input bit we,input bit ready);begin
  native_rsp_v=4'b0001<<client;native_rsp_ready=ready?(4'b0001<<client):0;
  observe_rsp_tag[client*16+:16]=16'(tag);observe_rsp_we[client]=we;settle();
 end endtask
 task finish_native;begin
  step();native_rsp_v=0;native_rsp_ready=0;settle();
 end endtask
 task saturate;begin
  for(integer k=0;k<32;k=k+1)begin
   native_req_v=4'hf;native_req_ready=4'hf;observe_req_we=4'b1010;
   for(integer j=0;j<4;j=j+1)observe_req_tag[j*16+:16]=16'(16'h8000+32*j+k);
   step();
  end
  native_req_v=0;native_req_ready=0;settle();
  require(external_debt==128&&accepted_native==128&&!native_credit_empty,"4x32 saturation lost a receipt");
  request_lease();idle_steps(8);
  require(lease_granted==0&&!native_credit_empty&&!fault,"saturated native slots allowed borrower grant");
 end endtask
 task drain_all;begin
  for(integer k=0;k<32;k=k+1)begin
   native_rsp_v=4'hf;native_rsp_ready=4'hf;observe_rsp_we=4'b1010;
   for(integer j=0;j<4;j=j+1)observe_rsp_tag[j*16+:16]=16'(16'h8000+32*j+k);
   settle();require(response_authorized==4'hf,"original saturated receipt refused");
   step();require(lease_granted==0,"grant before last native consumer edge/quiet interval");
  end
  native_rsp_v=0;native_rsp_ready=0;settle();
  require(external_debt==0&&consumed_native==128,"not all128 original consumers retired");
  wait_owned();
 end endtask
 task send_service(input bit change_after_accept);integer n;begin
  req_we[2]=1;req_addr[64+:32]=32'hc0000040;req_wstrb[64+:32]=32'hf00ff00f;
  req_tag[32+:16]=16'hf135;
  req_wdata[512+:256]=256'h80000001_abcdef02_92345603_fedcba04_80000005_abcdef06_92345607_fedcba08;
  original_req={req_we[2],req_addr[64+:32],req_wdata[512+:256],req_wstrb[64+:32],req_tag[32+:16]};
  req_v=4'b0100;m_req_rdy=0;n=0;
  while(!req_rdy[2]&&n<8)begin step();n=n+1;end
  require(req_rdy==4'b0100,"shared source acceptance not reached");
  step();req_v=0;
  if(change_after_accept)begin
   req_addr[64+:32]=~req_addr[64+:32];req_wdata[512+:256]=~req_wdata[512+:256];
   req_wstrb[64+:32]=0;req_tag[32+:16]=16'h1234;req_we[2]=0;
   lease_job[32+:32]=~lease_job[32+:32];lease_gen[4+:4]=~lease_gen[4+:4];
   lease_token[17+:17]=~lease_token[17+:17];lease_pos[20+:20]=~lease_pos[20+:20];
  end
  n=0;while(!m_req_v&&n<8)begin step();n=n+1;end
  require(m_req_v&&actual_backend===original_req,"captured337bits did not reach actual backend");
  repeat(5)begin step();require(m_req_v&&actual_backend===original_req&&!release_r[1],"backend held tuple/debt changed");end
  // The provider echoes the actual observed wire identity, never only a manual
  // prelabel. The full tuple above separately proves its caller origin.
  m_rsp_tag=m_req_tag;m_rsp_we=m_req_we;
  original_response=256'hcafef001_80000002_dead0003_12340004_98760005_abcd0006_ffff0007_80000008;
  m_req_rdy=1;step();m_req_rdy=0;
  require(service_live&&service_accepted==1,"actual backend handshake not observed");
  m_rsp_data=original_response;m_rsp_v=1;n=0;
  while(!m_rsp_rdy&&n<8)begin step();n=n+1;end
  require(m_rsp_rdy,"matched physical return not accepted");step();m_rsp_v=0;
  // After provider handshake these input wires may be reused; client output
  // must still contain the captured original response during backpressure.
  m_rsp_data=~original_response;m_rsp_tag=16'hffff;m_rsp_we=0;
  n=0;while(!rsp_v[2]&&n<8)begin step();n=n+1;end
  require(rsp_v==4'b0100,"held actual original-client terminal absent");
 end endtask
 task offer_release;begin
  release_job[32+:32]=original_lease[31:0];release_gen[4+:4]=original_lease[35:32];
  release_token[17+:17]=original_lease[52:36];release_pos[20+:20]=original_lease[72:53];
  release_v=3'b010;settle();
 end endtask
 task consume_service_and_release;begin
  offer_release();repeat(5)begin
   step();require(service_live&&service_consumed==0&&rsp_v[2]&&!release_r[1]&&lease_granted[1],
    "provider arrival retired lease/debt before consumer handshake");
  end
  rsp_rdy=4'b0100;step();rsp_rdy=0;settle();
  require(!service_live&&service_consumed==1,"actual client consumption failed to retire receipt");
  require(release_r[1]&&!fault,"matching release refused after actual consumption");
  step();release_v=0;settle();require(idle&&lease_granted==0,"matched release not completed");
 end endtask
 string selected;
 integer before_count;
 initial begin
  for(integer j=0;j<4;j=j+1)for(integer k=0;k<32;k=k+1)live[j][k]=0;
  if(!$value$plusargs("CASE=%s",selected))$fatal(1,"CASE required");
  step();por_n=1;step();
  if(selected=="saturation")begin
   saturate();drain_all();
  end else if(selected=="late_prior_native")begin
   native_accept(1,16'hf101,0);request_lease();idle_steps(8);
   require(lease_granted==0,"grant with late original native response pending");
   native_offer(1,16'hf101,0,0);repeat(5)begin
    step();require(response_authorized[1]&&external_debt==1&&!native_credit_empty&&lease_granted==0,
     "late original return OFFER retired native receipt");
   end
   native_rsp_ready=2;finish_native();
   require(external_debt==0&&consumed_native==1,"late original consumer not counted");wait_owned();
  end else if(selected=="consumption_only")begin
   request_lease();wait_owned();send_service(0);consume_service_and_release();
  end else if(selected=="source_changed_while_held")begin
   request_lease();wait_owned();send_service(1);consume_service_and_release();
  end else if(selected=="foreign_cp_tuple")begin
   native_accept(1,16'hf102,1);request_lease();
   native_offer(1,16'hf102,1,1);before_count=external_debt;
   // All wire tag/kind/client fields still match. Only the real CP tuple is
   // foreign, including high token/position bits; no field truncation oracle.
   native_job=32'h02345678;native_gen=4'ha;native_token=17'h00001;native_pos=20'h7ffff;
   settle();require(response_authorized[1]==0&&observe_rsp[1]==0,"foreign CP tuple ACKed");
   step();native_rsp_v=0;native_rsp_ready=0;settle();
   require(fault&&external_debt==before_count&&!native_credit_empty&&lease_granted==0,
    "foreign CP context erased credit or enabled borrower");
  end else if(selected=="reset_retained_accepted_debt")begin
   native_accept(1,16'hf103,0);request_lease();idle_steps(5);
   require(external_debt==1&&!native_credit_empty&&lease_granted==0,"pre-reset receipt absent");
   // Actual enclosing u_shared.por_n is wired to rst_sm_n. This is an SM-local
   // reset, NOT an authoritative provider all-copies-discard callback.
   // Independent source receipts intentionally survive this edge.
   por_n=0;step();por_n=1;step();
   require(external_debt==1&&!native_credit_empty&&lease_granted==0,
    "SM-local reset erased accepted provider debt without all-copies retirement");
   idle_steps(5);require(lease_granted==0,"local reset enabled borrower ahead of old provider terminal");
  end else $fatal(1,"unknown CASE=%s",selected);
  $display("CASE_PASS %s cycles=%0d native_accepted=%0d native_consumed=%0d external=%0d service_accepted=%0d service_consumed=%0d",
   selected,cycle,accepted_native,consumed_native,external_debt,service_accepted,service_consumed);
  $finish;
 end
endmodule
