// Explicit PREV pair direction, separate from the forward NEXT pair instances.
wire[1103:0] prev1,prev0,transit_return,unused_local;
wire[3:0] pf1,pf0;wire[7:0] prf;
wire return_input_slot=cyc==stopat-7;
dsdv_hostb_tx source_prev(.ck(ck),.rst_n(rst_n),.local_ro(1104'd0),.forward_ro(1104'd0),.return_ro(ret),
 .forward_slot(1'b0),.return_slot(return_input_slot),.next_ro(prev1),.fault(pf1));
dsdv_hostb_rx transit_prev(.ck(ck),.rst_n(rst_n),.configured(1'b1),.local_stage(8'd0),.local_rank(2'd0),
 .epoch_id(32'h1021),.programme_id(64'hf1c617d9224a57bf),.receiver_edge(48'(cyc)),.transit_body_edge(48'd0),
 .expected_tid(16'd37),.expected_header_stage(8'd1),.expected_user(10'd0),.expected_position(21'd1048575),.expected_token(21'd16754),
 .header_slot(cyc==stopat-5),.job_active(1'b0),.starter_armed(1'b0),.ring_i(prev1),.local_ring(unused_local),.forward_ring(transit_return),
 .f_host(),.ks_descriptor(),.ks_slot(),.arm_mask(),.arm_commit(),.fault(prf));
dsdv_hostb_tx transit_prev_tx(.ck(ck),.rst_n(rst_n),.local_ro(1104'd0),.forward_ro(transit_return),.return_ro(1104'd0),
 .forward_slot(cyc==stopat-4),.return_slot(1'b0),.next_ro(to_head),.fault(pf0));
always @(posedge ck)begin #0.03;if(cyc==stopat&&(pf1||pf0||prf))$fatal(1,"PREV fault %h/%h/%h",pf1,pf0,prf);end
