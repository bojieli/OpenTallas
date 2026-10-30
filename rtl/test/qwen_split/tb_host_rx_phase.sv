`timescale 1ns/1ps
// TOK-KV-7 component: actual HOST typed source -> native SFM SRAM sender ->
// registered UCIe macro pair -> actual compute link receiver. The declared
// HOST relay path is 86+67 plus two pin flops; actual HOST adds two edges.
// A late compute calendar needs the compiler's signed start offset in RXDT.
// PHASE/EXPECT_BAD exercise this mechanism only; no die/token/physical claim.
module tb_host_rx_phase;
parameter integer MUT=0, PHASE=0, RXDT=172, EXPECT_BAD=0;
localparam integer HOST_D=157;
reg ck=0; always #0.4165 ck=~ck;
reg rst_n=0, txwe=0, start=0, cstart=0, eb=0;
reg [5:0] addr=0; reg [31:0] word=0;
wire [3:0] slot; wire pv,ab,ef; wire [7:0] fc; wire [582:0] flit;
wire [3:0] crxe; wire cab,cef; wire [7:0] cfc; wire [547:0] crxp; integer nrx=0;
reg [583:0] txpin=0, rxpin=0;
wire klv, prv; wire [582:0] klf, prf;
always @(posedge ck) begin txpin<={pv,flit}; rxpin<={prv,prf}; end
ot_qkvd_ucie_x64_phy_model #(.LAT(5),.FW(583)) kp(.clk(ck),.rst_n(rst_n),.tx_up(),.tx_v(txpin[583]),.tx_flit(txpin[582:0]),.rx_v(),.rx_flit(),.link_v(klv),.link_flit(klf),.far_v(1'b0),.far_flit(583'd0));
ot_qkvd_ucie_x64_phy_model #(.LAT(5),.FW(583)) cp(.clk(ck),.rst_n(rst_n),.tx_up(),.tx_v(1'b0),.tx_flit(583'd0),.rx_v(prv),.rx_flit(prf),.link_v(),.link_flit(),.far_v(klv),.far_flit(klf));
ot_qwen_d2d_static_end #(.TXD(32'h01010101)) cend(
 .ck({5{ck}}),.rst_n(rst_n),.cfg_tx_we(1'b0),.cfg_rx_we(txwe),.cfg_addr(addr),
 .cfg_data((RXDT<<18)|(32'd1<<17)|(32'd1<<14)|(32'd13<<10)),
 .epoch_begin(eb),.epoch(8'd1),.cal_start(cstart),.cal_seg(1'b0),
 .tx_slot(),.tx_kind(),.tx_beat(),.tx_valid(4'd0),.tx_payload(2192'd0),
 .rx_event(crxe),.rx_slot(),.rx_kind(),.rx_beat(),.rx_payload(crxp),
 .p_tx_up(1'b1),.p_tx_v(),.p_tx_flit(),.p_rx_v(rxpin[583]),.p_rx_flit(rxpin[582:0]),
 .epoch_abort(cab),.fault_cause(cfc),.end_fault(cef),.cal_running());
reg [86:0] outbound=0;
reg [67:0] inbound=0;
reg [547:0] data_inbound[0:67];
wire host_obs,host_fault; wire [547:0] host_record;
reg begin_v=0;
integer r;
always @(posedge ck) begin
 if(!rst_n) begin outbound<=0; inbound<=0; end
 else begin outbound<={outbound,slot[1]}; inbound<={inbound,host_obs}; end
 data_inbound[0]<=host_record;
 for(r=1;r<68;r=r+1) data_inbound[r]<=data_inbound[r-1];
end
qkd_host_record_port host(.ck(ck),.rst_n(rst_n),.send_kind(outbound[86]?2'd1:2'd0),
 .request_v(1'b0),.request_tag(59'd0),.request_gen(2'd0),.request_token(18'd0),.request_position(18'd0),
 .token_epoch_valid(1'b0),.token_epoch(16'd0),
 .begin_v(begin_v),.begin_epoch(16'h42a1),.expected_pw(11'd1024),.expected_dw(4'd8),
 .auth_v(1'b0),.auth_epoch(16'd0),.auth_digest(64'd0),.program_ready(1'b0),.program_epoch(16'd0),.program_digest(64'd0),
 .authorized_footer_valid(1'b0),.authorized_footer(64'd0),.witness_slot(1'b0),.rx_v(1'b0),.rx_record(548'd0),
 .commit_v(),.installed_valid(),.installed_fusedcap(),.commit_epoch(),.commit_digest(),
 .tx_v(),.tx_observed_v(host_obs),.tx_record(host_record),.fault(host_fault));
wire ov=inbound[67] && MUT!=2;
localparam [547:0] PAYLOAD={5'd0,4'd13,6'd63,16'h42a1,5'd0,495'd0,4'd8,11'd1024,2'd1};
ot_qwen_d2d_static_end_sfm #(.TXD({8'd3,8'd3,8'(MUT==1?4:157),8'd169}),.FEG(0)) dut(
 .ck({5{ck}}),.rst_n({4{rst_n}}),.por_c({2{rst_n}}),.fg_we({1'b0,txwe}),.fg_addr({6'd0,addr}),
 .cfg_tx_we(txwe),.cfg_rx_we(1'b0),.cfg_addr_c({6'd0,addr}),.cfg_data_c({64'd0,word,word}),.cfg_base_c(10'd0),
 .eb_c({10{eb}}),.epoch_begin(eb),.epoch(8'd1),.cal_start(start),.cal_start_rx(1'b0),
 .start_c({4'd0,{4{start}}}),.seg_c(8'd0),.cal_user_tx(2'd0),.cal_user_rx(2'd0),
 .tx_slot(slot),.tx_kind(),.tx_beat(),.tx_valid({2'd0,ov,1'b0}),.tx_payload({1096'd0,data_inbound[67],548'd0}),
 .tx_user(),.rx_user(),.rx_event(),.rx_slot(),.rx_kind(),.rx_beat(),.rx_payload(),.st_ev_c(),.st_rs_c(),
 .p_tx_up(1'b1),.p_tx_v(pv),.p_tx_flit(flit),.p_rx_v(1'b0),.p_rx_flit(583'd0),
 .epoch_abort(ab),.fault_cause(fc),.end_fault(ef),.cal_running());
integer i,n_tx=0,n_slot=0,n_obs=0,cyc=0;
always @(posedge ck) cyc<=cyc+1;
always @(negedge ck) begin
 if(pv) begin
  n_tx=n_tx+1;
  if(flit[547:0]!==PAYLOAD) $fatal(1,"payload mismatch");
 end
 if(crxe[1]) begin nrx=nrx+1; if(crxp!==PAYLOAD) $fatal(1,"RXpayload mismatch"); end
 if(slot[1]) n_slot=n_slot+1;
 if(start||cstart||pv||prv||rxpin[583]||cend.rv||cend.u_link.u_ctl.new_fault) $display("PHASEOBS cyc %0d Kstart%0d Cstart%0d Ktx%0d phyRx%0d pinRx%0d Cexpect%0d Cnf%h",cyc,start,cstart,pv,prv,rxpin[583],cend.rv,cend.u_link.u_ctl.new_fault);
 if(ov) n_obs=n_obs+1;
end
initial begin
 repeat(4) @(negedge ck); rst_n=1; begin_v=1; @(negedge ck); begin_v=0;
 @(negedge ck); eb=1; @(negedge ck); eb=0;
 // A single terminated calendar event: dt 10, port1, kind13, beat0.
 word=(32'd3<<18)|(32'd1<<17)|(32'd1<<14)|(32'd13<<10); txwe=1;
 for(i=0;i<32;i=i+1) begin addr=i; @(negedge ck); end
 txwe=0; repeat(4) @(negedge ck); start=1; cstart=(PHASE==0); @(negedge ck); start=0; cstart=0;
 if(PHASE>0) begin repeat(PHASE-1) @(negedge ck); cstart=1; @(negedge ck); cstart=0; end
 repeat(200) @(negedge ck);
 if(ab!==0||ef!==0||fc!==0||host_fault!==0||n_tx!=1) $fatal(1,"sender failed");
 if(EXPECT_BAD==0) begin
  if(cab!==0||cef!==0||cfc!==0||nrx!=1) $fatal(1,"RXBASE FAIL fc=%h ab=%b nrx=%0d",cfc,cab,nrx);
  $display("HOST_RX_PHASE_PASS phase=%0d rxdt=%0d exact548=%0d",PHASE,RXDT,nrx);
 end else begin
  if(cab!==1 || cfc==0) $fatal(1,"phase control escaped fc=%h ab=%b",cfc,cab);
  $display("HOST_RX_PHASE_CAUGHT phase=%0d rxdt=%0d fc=%h",PHASE,RXDT,cfc);
 end
 $finish;
end
endmodule
