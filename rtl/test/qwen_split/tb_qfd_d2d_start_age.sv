`timescale 1ns/1ps
module tb_d2d_start_age;
parameter integer MUT=0;
reg ck=0;
reg por_n=0;
reg rst_n=0;
reg cfg_tx_we=0;
reg cfg_rx_we=0;
reg [5:0] cfg_addr=0;
reg [31:0] cfg_data=0;
reg cal_start=0;
reg cal_seg=0;
reg cal_start_rx=0;
reg cal_seg_rx=0;
reg [1:0] cal_user_tx=0;
reg [1:0] cal_user_rx=0;
wire [1:0] tx_user;
wire [1:0] rx_user;
reg fwd_epoch=0;
reg fwd_link_rst_n=0;
wire native_tx_slot;
wire [3:0] native_tx_slot_kind;
wire [4:0] native_tx_slot_beat;
reg native_tx_v=0;
reg [547:0] native_tx_payload=0;
wire [547:0] rx_payload;
wire native_rx_v;
wire native_rx_slot;
wire [3:0] native_rx_slot_kind;
wire [4:0] native_rx_slot_beat;
wire prog_witness_slot;
wire prog_auth_slot;
wire prog_context_slot;
reg prog_tx_observed_v=0;
reg [547:0] prog_tx_record=0;
wire prog_rx_v;
wire emb_rx_v;
wire emb_rx_slot;
wire kv_x3_slot;
reg [523:0] x3=0;
reg [58:0] x3_identity=0;
reg [1:0] x3_generation=0;
reg [15:0] status_epoch16=0;
reg vm_drained=0;
reg collective_drained=0;
reg collective_busy=0;
reg crom_fault=0;
reg execution_active=0;
reg admit_ready=0;
reg result_v=0;
reg result_done=0;
reg result_fault=0;
reg [3:0] result_cause=0;
reg [58:0] result_tag=0;
reg [1:0] result_gen=0;
reg [17:0] result_token=0;
reg [31:0] result_value=0;
reg [31:0] result_cycles=0;
reg fdi_tx_up=0;
wire fdi_tx_v;
wire [582:0] fdi_tx_flit;
reg fdi_rx_v=0;
reg [582:0] fdi_rx_flit=0;
wire phy_rst_n;
wire epoch_abort;
wire [7:0] transport_fault;
wire fault;
always #5 ck=~ck;
qfd_d2d_static_ovl #(.TXDP(32'h0a010308)) dut(.ck(ck),.por_n(por_n),.rst_n(rst_n),.cfg_tx_we(cfg_tx_we),.cfg_rx_we(cfg_rx_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.cal_start(cal_start),.cal_seg(cal_seg),.cal_start_rx(cal_start_rx),.cal_seg_rx(cal_seg_rx),.cal_user_tx(cal_user_tx),.cal_user_rx(cal_user_rx),.tx_user(tx_user),.rx_user(rx_user),.fwd_epoch(fwd_epoch),.fwd_link_rst_n(fwd_link_rst_n),.native_tx_slot(native_tx_slot),.native_tx_slot_kind(native_tx_slot_kind),.native_tx_slot_beat(native_tx_slot_beat),.native_tx_v(native_tx_v),.native_tx_payload(native_tx_payload),.rx_payload(rx_payload),.native_rx_v(native_rx_v),.native_rx_slot(native_rx_slot),.native_rx_slot_kind(native_rx_slot_kind),.native_rx_slot_beat(native_rx_slot_beat),.prog_witness_slot(prog_witness_slot),.prog_auth_slot(prog_auth_slot),.prog_context_slot(prog_context_slot),.prog_tx_observed_v(prog_tx_observed_v),.prog_tx_record(prog_tx_record),.prog_rx_v(prog_rx_v),.emb_rx_v(emb_rx_v),.emb_rx_slot(emb_rx_slot),.kv_x3_slot(kv_x3_slot),.x3(x3),.x3_identity(x3_identity),.x3_generation(x3_generation),.status_epoch16(status_epoch16),.vm_drained(vm_drained),.collective_drained(collective_drained),.collective_busy(collective_busy),.crom_fault(crom_fault),.execution_active(execution_active),.admit_ready(admit_ready),.result_v(result_v),.result_done(result_done),.result_fault(result_fault),.result_cause(result_cause),.result_tag(result_tag),.result_gen(result_gen),.result_token(result_token),.result_value(result_value),.result_cycles(result_cycles),.fdi_tx_up(fdi_tx_up),.fdi_tx_v(fdi_tx_v),.fdi_tx_flit(fdi_tx_flit),.fdi_rx_v(fdi_rx_v),.fdi_rx_flit(fdi_rx_flit),.phy_rst_n(phy_rst_n),.epoch_abort(epoch_abort),.transport_fault(transport_fault),.fault(fault));
wire[566:0]body={1'b0,8'd1,1'b0,1'b1,8'd0,548'h123456789abc};wire[15:0]crc;
ot_qwen_crc_parallel #(.DW(567),.CW(16)) crcgen(.d(body),.q(crc));
integer e=0,cal=-1,out=-1,slot=-1;always @(posedge ck)begin
 e<=e+1;
 if(cal_start_rx)$display("STARTAGE external_start_sample%0d",e);
 if(dut.u_core.u_end.rx_start)$display("STARTAGE internal_calendar_start_sample%0d",e);
 if(dut.u_core.u_end.rv)begin cal=e;$display("D2DEMBAGE calendar_sample=%0d",e);end
 if(emb_rx_slot)begin slot=e;$display("D2DEMBAGE slot_pin_sample=%0d",e);end
 if(emb_rx_v)begin out=e;$display("D2DEMBAGE payload_pin_sample=%0d payload=%h",e,rx_payload);end
end
initial begin
 fdi_tx_up=1;fwd_link_rst_n=1;
 repeat(20)@(negedge ck);por_n=1;rst_n=1;
 while(e<80)@(negedge ck);cfg_rx_we=1;cfg_addr=0;cfg_data=(20<<18)|(1<<17)|(2<<14)|(6<<10);
 @(negedge ck);cfg_rx_we=0;
 while(e<100)@(negedge ck);fwd_epoch=1;@(negedge ck);fwd_epoch=0;
 while(e<200)@(negedge ck);cal_start_rx=1;cal_user_rx=0;
 @(negedge ck);cal_start_rx=0;
 while(e<(MUT?220:221))@(negedge ck);fdi_rx_v=1;fdi_rx_flit={crc,body};
 @(negedge ck);fdi_rx_v=0;
 while(e<240)@(negedge ck);
 if(cal<0||out<0||slot!=out||out-cal!=3||rx_payload!=548'h123456789abc||fault||epoch_abort)begin
 $display("D2DEMBAGE_FAIL MUT%0d cal%0d out%0d slot%0d fault%0d abort%0d cause%h ep%h",MUT,cal,out,slot,fault,epoch_abort,dut.u_core.u_end.u_link.u_ctl.fault_cause,dut.u_core.ep);$fatal(1);end
 $display("D2DEMBAGE_PASS MUT%0d calendar_to_emb_rx_pin%0d",MUT,out-cal);$finish;
end
endmodule
