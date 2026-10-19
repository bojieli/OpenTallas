module tb_z17_boundary; reg ck=0; always #1 ck=~ck; reg rst_n=0; reg [547:0] stimulus; wire [16:0] z;
qkd_d2d_static_z17 #(.Z17(1), .TXDP(32'h03030403)) dut(.ck(ck),.por_n('0),.rst_n(rst_n),.cfg_tx_we('0),.cfg_rx_we('0),.cfg_addr('0),.cfg_data('0),.cal_start('0),.cal_seg('0),.host_link_reset_req('0),.host_recovery_clear('0),.host_boot_begin('0),.fwd_epoch(),.fwd_link_rst_n(),.att_tx_slot(),.att_tx_kind(),.att_tx_beat(),.att_tx_v('0),.att_tx_payload('0),.att_rx_v(),.att_rx_slot(),.att_rx_kind(),.att_rx_beat(),.rx_payload(),.emb_tx_slot(),.emb_tx_v('0),.emb_tx_payload('0),.record_tx_observed_v('0),.record_tx('0),.record_send_kind(),.record_witness_slot(),.record_rx_v(),.record_rx(),.kvn_compiled_identity('0),.kvn_compiled_generation('0),.kvn_word_valid(),.kvn_word_tag(),.kvn_word_data(),.kvn_word_identity(),.kvn_word_generation(),.kvn_word_slot(),.kvn_word_index(),.status_epoch16('0),.serdes_up('0),.kv_drained_local('0),.kv_flush_local('0),.host_drained_local('0),.kv_active_local('0),.link_up(),.transport_fault(),.native_links_drained(),.native_link_reset_seen(),.native_retrained(),.abort_drained(),.native_kv_drained(),.native_vm_drained(),.native_collective_drained(),.native_host_drained(),.native_collective_busy(),.native_kv_flush(),.native_admit_ready(),.crom_fault(),.execution_active(),.engine_result_v(),.engine_result_done(),.engine_result_fault(),.engine_result_cause(),.engine_result_tag(),.engine_result_gen(),.engine_result_token(),.engine_result_value(),.engine_result_cycles(),.fdi_tx_up('0),.fdi_tx_v(),.fdi_tx_flit(),.fdi_rx_v('0),.fdi_rx_flit('0),.phy_rst_n(),.epoch_abort(),.recovery_cycles(),.fault(),.rx_zero17(z));
reg [16:0] expect_z; integer b,j,phase;
initial begin
force dut.c_rx_payload=stimulus;
for(phase=0;phase<2;phase=phase+1) begin
rst_n=phase;
for(b=-1;b<548;b=b+1) begin
@(negedge ck); stimulus=0; if(b>=0) stimulus[b]=1;
expect_z[0]=|stimulus[31:19]; expect_z[1]=|stimulus[31:5];
for(j=1;j<=15;j=j+1) expect_z[j+1]=|stimulus[32*j+:32];
@(posedge ck); #0.01;
if(z !== expect_z || dut.q_rx_payload !== stimulus) $fatal(1,"Z17_BOUNDARY_FAIL reset%0d bit%0d",phase,b);
end end
$display("Z17_BOUNDARY_PASS vectors=1098 reset_and_active=1"); $finish;
end endmodule
