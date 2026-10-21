// Exact selected8916 composed HEAD, actual dsfd_mtp_seq held reset by c_run=0.
// TEST common-clock dates measured in head_producer_r1: pin->postedge ro5,
// following RX capture1. Ordinary ri valid0 with nonzero inactive upper bits.
reg [1:0] actual_hrx_v=0;reg [1105:0] actual_hrx_d=0;
wire actual_head_fault;wire[1:0] actual_htx_v;wire[1105:0] actual_htx_d;
ot_s81hd_ctl real_head(.ck(ck),.rst_n(rst_n),.ri({toctl[1103:533]|571'h123456789abcdef,toctl[532:0]}),.mu_rt(32'd0),.lw(11'd0),.lep_f(1'b0),.ro(from_head),.mu_c(),.mu_rc(),.ctl_f(actual_head_fault),
 .sn_o(),.ss_o(),.sn_i(565'd0),.ss_i(565'd0),.mtx_v(),.mtx_d(),.mrx_v(6'd0),.mrx_d(3318'd0),.mflt(24'd0),
 .htx_v(actual_htx_v),.htx_d(actual_htx_d),.hrx_v(actual_hrx_v),.hrx_d(actual_hrx_d),.hflt(8'd0),.dtx_v(),.dtx_d(),.drx_v(5'd0),.drx_d(2765'd0),.dflt(20'd0));
always @(negedge ck)begin
 #0.001;actual_hrx_v=0;actual_hrx_d=0;
 if(events[cyc+6][0])begin actual_hrx_v[0]=1;actual_hrx_d[552:0]={1'b1,24'd0,events[cyc+6][532:21],8'd0,2'd0,2'd0,4'd7};end
end
always @(posedge ck)begin #0.03;if(cyc==stopat&&actual_head_fault)$fatal(1,"actual HEAD fault");end

`ifdef HBE_REVERSE_PATH
wire[1:0] delivered_host_v;wire[1105:0] delivered_host_d;wire[2:0] egress_fault;
reg event_slot=0;integer egress_count=0;
dsdv_hostb_head_egress #(.ENABLE(1)) real_egress(.ck(ck),.rst_n(rst_n),.legacy_v(actual_htx_v),.legacy_d(actual_htx_d),
 .event_v(htv),.event_d(htd),.event_slot(event_slot),.host_v(delivered_host_v),.host_d(delivered_host_d),.fault(egress_fault));
always @(negedge ck)begin #0.002;event_slot=cyc==stopat-1;end
always @(posedge ck)begin
 #0.04;
 if(delivered_host_v[0])begin
  egress_count++;
  if(delivered_host_d[3:0]!=10||delivered_host_d[366:290]!==sampled_th||delivered_host_d[420:367]!==sampled_tk)$fatal(1,"BAD actual HEAD event egress");
 end
 if(cyc==stopat)begin
  if(egress_count!=1||egress_fault)$fatal(1,"BAD HEAD egress count%0d fault%h",egress_count,egress_fault);
  $display("PASS actual PREV sourceTX2+transitRX1TX2+headcapture1+eventegress2; raw actual L0 status");
 end
end
`endif
