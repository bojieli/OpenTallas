`timescale 1ns/1ps
module tb_c_ovl_phase;
parameter integer MUT=0;parameter integer TXPROBE=0;
reg ck=0;
reg por_n=0;
reg rst_n=0;
wire cfg_tx_we;
wire cfg_rx_we;
wire [5:0] cfg_addr;
wire [31:0] cfg_data;
wire cal_start;
wire cal_seg;
wire cal_start_rx;
wire cal_seg_rx;
wire [1:0] cal_user_tx;
wire [1:0] cal_user_rx;
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

 reg seqepoch=0;wire[11:0]ta,ra;reg[31:0]tq=0,rq=0,tc=0,rc=0;
 always @(posedge ck)begin
  tq<=TXPROBE && ta==0 ? (32'd8<<12)|(1<<11) : (32'd1000<<12)|(1<<7);
  rq<=!TXPROBE && ra==0 ? (32'd8<<12)|(1<<11) : (32'd1000<<12)|(1<<7);
  tc<=tq;rc<=rq;
 end
 ot_qwen_d2d_ovl_seq #(.AW(12),.ADM(0),.FIRST_OFS(200),.TX_IMG((20<<18)|(1<<17)),.RX_IMG((20<<18)|(1<<17)|(2<<14)|(6<<10))) seq(
 .ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(seqepoch),.halt(1'b0),.cfg_tx_we(cfg_tx_we),.cfg_rx_we(cfg_rx_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .cal_start(cal_start),.cal_seg(cal_seg),.cal_start_rx(cal_start_rx),.cal_seg_rx(cal_seg_rx),.cal_user_tx(cal_user_tx),.cal_user_rx(cal_user_rx),
 .tx_rom_addr(ta),.tx_rom_q(tc),.rx_rom_addr(ra),.rx_rom_q(rc),.cal_ready(),.adm_done(),.running(),.fault());
 integer e=0,G=-1,P=-1,X=-1,I=-1,V=-1,O=-1;
 always @(posedge ck)begin:monitor
  integer at;at=e;e<=e+1;
  if(seq.go)begin G=at;$display("PHASE C TX%0d go_sample%0d",TXPROBE,at);end
  if(TXPROBE?cal_start:cal_start_rx)begin X=at;$display("PHASE C TX%0d FACE_wire_external_sample%0d",TXPROBE,at);end
  if(TXPROBE?dut.u_core.u_end.cal_start:dut.u_core.u_end.rx_start)begin I=at;$display("PHASE C TX%0d internal_start_sample%0d",TXPROBE,at);end
  if(TXPROBE?dut.u_core.u_end.tv:dut.u_core.u_end.rv)begin V=at;$display("PHASE C TX%0d calendar_event_sample%0d",TXPROBE,at);end
  if(emb_rx_v)begin O=at;$display("PHASE C checked_RX_pin_sample%0d",at);end
  #0.01;
  if((TXPROBE?cal_start:cal_start_rx)&&P<0)begin P=at;$display("PHASE C TX%0d cseq_FACE_wire_publication%0d",TXPROBE,at);end
 end
 initial begin
  fdi_tx_up=1;fwd_link_rst_n=1;
  repeat(20)@(negedge ck);por_n=1;rst_n=1;
  while(e<100)@(negedge ck);seqepoch=1;fwd_epoch=1;@(negedge ck);seqepoch=0;fwd_epoch=0;
  if(!TXPROBE)begin
   while(e<(MUT?329:330))@(negedge ck);fdi_rx_v=1;fdi_rx_flit={crc,body};@(negedge ck);fdi_rx_v=0;
   while(e<350)@(negedge ck);
  end else begin wait(V>=0);@(negedge ck);end
  if(G!=300 || P-G!=8 || X-P!=1 || I-X!=1 || V-I!=21)$fatal(1,"PHASE_BAD C TX%0d G%0d P%0d X%0d I%0d V%0d",TXPROBE,G,P,X,I,V);
  if(!TXPROBE)begin
   if(MUT)begin if(O>=0 || !epoch_abort)$fatal(1,"PHASE mutant not caught");end
   else if(O-V!=3 || fault || epoch_abort)$fatal(1,"PHASE checked RX failure O%0d V%0d f%b a%b",O,V,fault,epoch_abort);
  end
  $display("PHASE_PASS C TX%0d MUT%0d G%0d P%0d X%0d I%0d V%0d O%0d",TXPROBE,MUT,G,P,X,I,V,O);$finish;
 end
endmodule
