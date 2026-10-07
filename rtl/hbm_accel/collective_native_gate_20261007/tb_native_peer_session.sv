`timescale 1ps/1fs
// BENCH COMPONENT: actual credit/storage/session RTL; payload source and vendor
// PHY quiesce/reset acknowledgments are explicitly fixtures, not PHY IP proof.
module tb_native_peer_session #(parameter integer W=545)(
 input wire clk,pclk,por,traffic_start,
 output wire rst_n,prst_n,cold_start,session_admit,output wire[23:0]epoch,
 input wire data_quiet,phy_quiet,input wire[7:0]source_debt_zero,source_initial_seen,
 input wire[7:0]native_tx_v,input wire[8*W-1:0]native_tx_data,
 output wire[7:0]native_rx_v,output wire[8*W-1:0]native_rx_data,
 input wire[7:0]rx_grant_valid,rx_ack_ready,output wire[7:0]rx_grant_ready,rx_ack_valid,
 input wire[8*72-1:0]rx_grant_word,output wire[8*72-1:0]rx_ack_word,
 output wire[7:0]tx_grant_valid,tx_ack_ready,input wire[7:0]tx_grant_ready,tx_ack_valid,
 output wire[8*72-1:0]tx_grant_word,input wire[8*72-1:0]tx_ack_word,
 output wire[7:0]peer_retire,output wire[8*W-1:0]peer_retire_data,
 output wire running,all_peer_quiet,all_debt_zero,output wire fault
);
 wire[1:0]cv,cr,av,ar,af,pq,pr,admit,launch,rn,pn,ss,ls;
 wire[71:0]cw;wire[143:0]aw;wire[47:0]se,le;
 wire cf;wire[7:0]peer_debt,peer_initial,peer_rx_initial,local_rx_initial;
 wire[7:0]peer_qempty,peer_flight_empty;
 wire[7:0]core_control_empty,peer_control_empty,port_fault;
 reg[1:0]phyq=0,phyr=0;
 wire[1:0]initial_seen={(&peer_initial)&&(&peer_rx_initial),(&source_initial_seen)&&(&local_rx_initial)};
 wire[1:0]debt_fence={&peer_debt,&source_debt_zero};
 wire[1:0]data_fence={(&peer_qempty)&&(&peer_flight_empty),data_quiet};
 wire[1:0]phy_fence={(&peer_qempty)&&(&peer_flight_empty)&&!(|native_tx_v)&&!(|native_rx_v),phy_quiet};
 wire[1:0]control_fence={&peer_control_empty,&core_control_empty};
 assign rst_n=rn[0];assign prst_n=pn[0];assign cold_start=ss[0];assign epoch=se[23:0];
 assign session_admit=admit[0]&&!cf;
 assign all_peer_quiet=data_fence[1]&&control_fence[1]&&debt_fence[1];
 assign all_debt_zero=&debt_fence;
 assign fault=cf||(|af)||(|port_fault);
 ot_hbm_link_session_coordinator #(.ENABLE(1)) coordinator(clk,por,1'b0,,cv,cr,cw,av,ar,aw,running,cf);
 // Vendor behavior fixture: explicit request/ack, registered, no elapsed-time purge inference.
 always @(posedge pclk)begin
  if(por)begin phyq<=0;phyr<=0;end else begin phyq<=pq;phyr<=pr;end
 end
 for(genvar a=0;a<2;a=a+1)begin:g_agent
  wire ac=a==0?clk:pclk;
  wire agent_rst,coord_rst,acv,acr,aav,aar,f0,f1;wire[71:0]acw,aaw;
  ot_hbm_collective_reset_entry #(.ENABLE(1)) management_resets(clk,ac,por,por,coord_rst,agent_rst);
  ot_hbm_link_management_cdc #(.ENABLE(1)) commands(clk,coord_rst,cv[a],cr[a],cw,ac,agent_rst,acv,acr,acw,,,f0);
  ot_hbm_link_management_cdc #(.ENABLE(1)) acknowledgments(ac,agent_rst,aav,aar,aaw,clk,coord_rst,av[a],ar[a],aw[a*72+:72],,,f1);
  wire agent_fault;
  ot_hbm_link_session_agent #(.ENABLE(1)) agent(ac,a==0?clk:pclk,pclk,por,
   acv,acr,acw,aav,aar,aaw,data_fence[a],phy_fence[a],debt_fence[a],data_fence[a],control_fence[a],
   phyq[a],phyr[a],initial_seen[a],pq[a],pr[a],admit[a],launch[a],rn[a],pn[a],ss[a],ls[a],se[a*24+:24],le[a*24+:24],agent_fault);
  assign af[a]=agent_fault||f0||f1;
 end
 reg[31:0]peer_cycle=0;always @(posedge pclk)if(!rn[1])peer_cycle<=0;else peer_cycle<=peer_cycle+1;
 for(genvar p=0;p<8;p=p+1)begin:g_port
  wire pgv,pgr,pav,par,rgv,rgr,rav,rar;
  wire[71:0]pgw,paw,rgw,raw;
  wire[3:0]ce_core,ce_peer,cfault;
  // Four data-session crossings per full-duplex port. They reset with their
  // credit endpoints after transport drain; management FIFOs above survive.
  ot_hbm_link_management_cdc #(.ENABLE(1)) incoming_grant(clk,rst_n,rx_grant_valid[p],rx_grant_ready[p],rx_grant_word[p*72+:72],pclk,rn[1],pgv,pgr,pgw,ce_core[0],ce_peer[0],cfault[0]);
  ot_hbm_link_management_cdc #(.ENABLE(1)) incoming_ack(pclk,rn[1],pav,par,paw,clk,rst_n,rx_ack_valid[p],rx_ack_ready[p],rx_ack_word[p*72+:72],ce_peer[1],ce_core[1],cfault[1]);
  ot_hbm_link_management_cdc #(.ENABLE(1)) outgoing_grant(pclk,rn[1],rgv,rgr,rgw,clk,rst_n,tx_grant_valid[p],tx_grant_ready[p],tx_grant_word[p*72+:72],ce_peer[2],ce_core[2],cfault[2]);
  ot_hbm_link_management_cdc #(.ENABLE(1)) outgoing_ack(clk,rst_n,tx_ack_valid[p],tx_ack_ready[p],tx_ack_word[p*72+:72],pclk,rn[1],rav,rar,raw,ce_core[3],ce_peer[3],cfault[3]);
  wire reserve_ready,flight_ready,flight_fault,source_fault,receiver_fault,queue_fault,observer_fault0,observer_fault1;
  localparam integer PARTIALS=(p==3)?0:48;
  reg[7:0]sent=0;wire request=traffic_start&&admit[1]&&sent<PARTIALS+189;
  wire reserve=request&&flight_ready;
  wire send=reserve&&reserve_ready;
  wire[544:0]payload;reg[544:0]payload_r;integer ordinal,contributor,flit;
  always @*begin
   ordinal=integer'(sent)*7+(p<3?p:p-1);contributor=ordinal/48;if(contributor>=3)contributor=contributor+1;flit=ordinal%48;
   payload_r=0;payload_r[512+:33]={1'b0,8'd19,8'(contributor),16'(flit)};
   for(integer l=0;l<16;l=l+1)payload_r[l*32+:32]=32'h3f000000+(contributor<<12)+(flit<<5)+l;
   if(sent>=PARTIALS)begin
    ordinal=(integer'(sent)-PARTIALS)*8+p;flit=ordinal>=456?ordinal+24:ordinal;
    payload_r[512+:33]={1'b1,8'hff,8'(flit/192),16'(flit)};
    for(integer l=0;l<16;l=l+1)payload_r[l*32+:32]=32'h3e800000+(flit<<4)+l;
   end
  end
  assign payload=payload_r;
  always @(posedge pclk)if(!rn[1])sent<=0;else if(send)sent<=sent+1'b1;
  ot_hbm_credit_source_session #(.ENABLE(1)) source(pclk,rn[1],ss[1],se[47:24],reserve,reserve_ready,pgv,pgr,pgw,pav,par,paw,peer_debt[p],peer_initial[p],source_fault);
  ot_hbm_collective_protected_flight #(.ENABLE(1),.W(545),.D(14)) fixture_phy_flight(pclk,rn[1],send,flight_ready,payload,native_rx_v[p],1'b1,native_rx_data[p*W+:W],peer_flight_empty[p],flight_fault);
  wire queue_ready,queue_valid,retire_ready;wire[8:0]queue_count;
  assign peer_retire[p]=queue_valid&&retire_ready&&(peer_cycle%5==0);
  assign peer_qempty[p]=queue_count==0&&!queue_valid&&!native_tx_v[p];
  ot_hbm_collective_packet_fifo #(.ENABLE(1),.DEPTH(64)) storage(pclk,rn[1],native_tx_v[p],native_tx_data[p*W+:W],queue_ready,peer_retire[p],queue_valid,peer_retire_data[p*W+:W],queue_fault,queue_count);
  ot_hbm_credit_rx #(.ENABLE(1)) receiver(pclk,rn[1],ss[1],se[47:24],peer_retire[p],retire_ready,rgv,rgr,rgw,rav,rar,raw,receiver_fault);
  ot_hbm_initial_credit_ack_observer #(.ENABLE(1)) peer_observer(pclk,rn[1],se[47:24],rav,rar,raw,peer_rx_initial[p],observer_fault0);
  ot_hbm_initial_credit_ack_observer #(.ENABLE(1)) native_observer(clk,rst_n,epoch,rx_ack_valid[p],rx_ack_ready[p],rx_ack_word[p*72+:72],local_rx_initial[p],observer_fault1);
  assign core_control_empty[p]=(&ce_core)&&!rx_grant_valid[p]&&!rx_ack_valid[p]&&!tx_grant_valid[p]&&!tx_ack_valid[p];
  assign peer_control_empty[p]=(&ce_peer)&&!pgv&&!pav&&!rgv&&!rav;
  assign port_fault[p]=(|cfault)||source_fault||receiver_fault||queue_fault||flight_fault||observer_fault0||observer_fault1;
  integer reservations=0,received=0,retired=0,launched=0;
  always @(posedge pclk)if(rn[1])begin
   if(send)reservations=reservations+1;
   if(native_tx_v[p])begin received=received+1;if(!queue_ready)$fatal(1,"NATIVE_GATE_PEER_OVERFLOW p=%0d",p);end
   if(peer_retire[p])retired=retired+1;
   if(received-retired>64||retired>received)$fatal(1,"NATIVE_GATE_PEER_WINDOW p=%0d",p);
   if(native_rx_v[p])launched=launched+1;
   if(launched>reservations)$fatal(1,"NATIVE_GATE_UNRESERVED_PEER p=%0d",p);
  end
 end
endmodule
