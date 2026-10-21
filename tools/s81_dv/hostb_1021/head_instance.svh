// Exact selected8916 composed HEAD, actual dsfd_mtp_seq held reset by c_run=0.
// TEST common-clock dates measured in head_producer_r1: pin->postedge ro5,
// following RX capture1. Ordinary ri valid0 with nonzero inactive upper bits.
reg [1:0] actual_hrx_v=0;reg [1105:0] actual_hrx_d=0;
wire actual_head_fault;
ot_s81hd_ctl real_head(.ck(ck),.rst_n(rst_n),.ri({571'h123456789abcdef,533'd0}),.mu_rt(32'd0),.lw(11'd0),.lep_f(1'b0),.ro(from_head),.mu_c(),.mu_rc(),.ctl_f(actual_head_fault),
 .sn_o(),.ss_o(),.sn_i(565'd0),.ss_i(565'd0),.mtx_v(),.mtx_d(),.mrx_v(6'd0),.mrx_d(3318'd0),.mflt(24'd0),
 .htx_v(),.htx_d(),.hrx_v(actual_hrx_v),.hrx_d(actual_hrx_d),.hflt(8'd0),.dtx_v(),.dtx_d(),.drx_v(5'd0),.drx_d(2765'd0),.dflt(20'd0));
always @(negedge ck)begin
 #0.001;actual_hrx_v=0;actual_hrx_d=0;
 if(events[cyc+6][0])begin actual_hrx_v[0]=1;actual_hrx_d[552:0]={1'b1,24'd0,events[cyc+6][532:21],8'd0,2'd0,2'd0,4'd7};end
end
always @(posedge ck)begin #0.03;if(cyc==stopat&&actual_head_fault)$fatal(1,"actual HEAD fault");end
