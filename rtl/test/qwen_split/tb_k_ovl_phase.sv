`timescale 1ns/1ps
module tb_k_ovl_phase;
parameter integer MUT=0;parameter integer TXPROBE=0;localparam integer NL=2,NTX=3;
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
reg host_link_reset_req=0;
reg host_recovery_clear=0;
reg host_boot_begin=0;
wire fwd_epoch;
wire fwd_link_rst_n;
wire att_tx_slot;
wire [3:0] att_tx_kind;
wire [4:0] att_tx_beat;
reg att_tx_v=0;
reg [547:0] att_tx_payload=0;
wire att_rx_v;
wire att_rx_slot;
wire [3:0] att_rx_kind;
wire [4:0] att_rx_beat;
wire [547:0] rx_payload;
wire emb_tx_slot;
reg emb_tx_v=0;
reg [547:0] emb_tx_payload=0;
reg record_tx_observed_v=0;
reg [547:0] record_tx=0;
wire [1:0] record_send_kind;
wire record_witness_slot;
wire record_rx_v;
wire [547:0] record_rx;
reg [58:0] kvn_compiled_identity=0;
reg [1:0] kvn_compiled_generation=0;
wire kvn_word_valid;
wire [10:0] kvn_word_tag;
wire [511:0] kvn_word_data;
wire [58:0] kvn_word_identity;
wire [1:0] kvn_word_generation;
wire kvn_word_slot;
wire [1:0] kvn_word_index;
reg [15:0] status_epoch16=0;
reg serdes_up=0;
reg kv_drained_local=0;
reg kv_flush_local=0;
reg host_drained_local=0;
reg kv_active_local=0;
wire [NL-1:0] link_up;
wire [7:0] transport_fault;
wire native_links_drained;
wire native_link_reset_seen;
wire native_retrained;
wire [3:0] abort_drained;
wire native_kv_drained;
wire native_vm_drained;
wire native_collective_drained;
wire native_host_drained;
wire native_collective_busy;
wire native_kv_flush;
wire native_admit_ready;
wire crom_fault;
wire execution_active;
wire engine_result_v;
wire engine_result_done;
wire engine_result_fault;
wire [3:0] engine_result_cause;
wire [58:0] engine_result_tag;
wire [1:0] engine_result_gen;
wire [17:0] engine_result_token;
wire [31:0] engine_result_value;
wire [31:0] engine_result_cycles;
reg fdi_tx_up=0;
wire fdi_tx_v;
wire [582:0] fdi_tx_flit;
reg fdi_rx_v=0;
reg [582:0] fdi_rx_flit=0;
wire phy_rst_n;
wire epoch_abort;
wire [31:0] recovery_cycles;
wire fault;
always #5 ck=~ck;
qkd_d2d_static_ovl #(.NTX(3),.SAFE_RC(1),.TXDP(32'h03030416)) dut(.ck(ck),.por_n(por_n),.rst_n(rst_n),.cfg_tx_we(cfg_tx_we),.cfg_rx_we(cfg_rx_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.cal_start(cal_start),.cal_seg(cal_seg),.cal_start_rx(cal_start_rx),.cal_seg_rx(cal_seg_rx),.cal_user_tx(cal_user_tx),.cal_user_rx(cal_user_rx),.tx_user(tx_user),.rx_user(rx_user),.host_link_reset_req(host_link_reset_req),.host_recovery_clear(host_recovery_clear),.host_boot_begin(host_boot_begin),.fwd_epoch(fwd_epoch),.fwd_link_rst_n(fwd_link_rst_n),.att_tx_slot(att_tx_slot),.att_tx_kind(att_tx_kind),.att_tx_beat(att_tx_beat),.att_tx_v(att_tx_v),.att_tx_payload(att_tx_payload),.att_rx_v(att_rx_v),.att_rx_slot(att_rx_slot),.att_rx_kind(att_rx_kind),.att_rx_beat(att_rx_beat),.rx_payload(rx_payload),.emb_tx_slot(emb_tx_slot),.emb_tx_v(emb_tx_v),.emb_tx_payload(emb_tx_payload),.record_tx_observed_v(record_tx_observed_v),.record_tx(record_tx),.record_send_kind(record_send_kind),.record_witness_slot(record_witness_slot),.record_rx_v(record_rx_v),.record_rx(record_rx),.kvn_compiled_identity(kvn_compiled_identity),.kvn_compiled_generation(kvn_compiled_generation),.kvn_word_valid(kvn_word_valid),.kvn_word_tag(kvn_word_tag),.kvn_word_data(kvn_word_data),.kvn_word_identity(kvn_word_identity),.kvn_word_generation(kvn_word_generation),.kvn_word_slot(kvn_word_slot),.kvn_word_index(kvn_word_index),.status_epoch16(status_epoch16),.serdes_up(serdes_up),.kv_drained_local(kv_drained_local),.kv_flush_local(kv_flush_local),.host_drained_local(host_drained_local),.kv_active_local(kv_active_local),.link_up(link_up),.transport_fault(transport_fault),.native_links_drained(native_links_drained),.native_link_reset_seen(native_link_reset_seen),.native_retrained(native_retrained),.abort_drained(abort_drained),.native_kv_drained(native_kv_drained),.native_vm_drained(native_vm_drained),.native_collective_drained(native_collective_drained),.native_host_drained(native_host_drained),.native_collective_busy(native_collective_busy),.native_kv_flush(native_kv_flush),.native_admit_ready(native_admit_ready),.crom_fault(crom_fault),.execution_active(execution_active),.engine_result_v(engine_result_v),.engine_result_done(engine_result_done),.engine_result_fault(engine_result_fault),.engine_result_cause(engine_result_cause),.engine_result_tag(engine_result_tag),.engine_result_gen(engine_result_gen),.engine_result_token(engine_result_token),.engine_result_value(engine_result_value),.engine_result_cycles(engine_result_cycles),.fdi_tx_up(fdi_tx_up),.fdi_tx_v(fdi_tx_v),.fdi_tx_flit(fdi_tx_flit),.fdi_rx_v(fdi_rx_v),.fdi_rx_flit(fdi_rx_flit),.phy_rst_n(phy_rst_n),.epoch_abort(epoch_abort),.recovery_cycles(recovery_cycles),.fault(fault));
wire[566:0]body={1'b0,8'd1,1'b0,1'b1,8'd0,548'h123456789abc};wire[15:0]crc;
ot_qwen_crc_parallel #(.DW(567),.CW(16)) crcgen(.d(body),.q(crc));

 reg seqepoch=0;wire[11:0]ta,ra;reg[31:0]tq=0,rq=0,tc=0,rc=0;
 always @(posedge ck)begin
  tq<=TXPROBE && ta==0 ? (32'd8<<12)|(1<<11) : (32'd1000<<12)|(1<<7);
  rq<=!TXPROBE && ra==0 ? (32'd8<<12)|(1<<11) : (32'd1000<<12)|(1<<7);
  tc<=tq;rc<=rq;
 end
 ot_qwen_d2d_ovl_seq #(.AW(12),.ADM(0),.FIRST_OFS(200),.TX_IMG((20<<18)|(1<<17)),.RX_IMG((20<<18)|(1<<17)|(1<<14)|(14<<10)|(1<<5))) seq(
 .ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(seqepoch),.halt(1'b0),.cfg_tx_we(cfg_tx_we),.cfg_rx_we(cfg_rx_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .cal_start(cal_start),.cal_seg(cal_seg),.cal_start_rx(cal_start_rx),.cal_seg_rx(cal_seg_rx),.cal_user_tx(cal_user_tx),.cal_user_rx(cal_user_rx),
 .tx_rom_addr(ta),.tx_rom_q(tc),.rx_rom_addr(ra),.rx_rom_q(rc),.cal_ready(),.adm_done(),.running(),.fault());
 integer e=0,G=-1,P=-1,X=-1,I=-1,V=-1,O=-1;
 always @(posedge ck)begin:monitor
  integer at;at=e;e<=e+1;
  if(seq.go)begin G=at;$display("PHASE K TX%0d go_sample%0d",TXPROBE,at);end
  if(TXPROBE?cal_start:cal_start_rx)begin X=at;$display("PHASE K TX%0d FACE_wire_external_sample%0d",TXPROBE,at);end
  if(TXPROBE?dut.u_core.u_end.cal_start:dut.u_core.u_end.rx_start)begin I=at;$display("PHASE K TX%0d internal_start_sample%0d",TXPROBE,at);end
  if(TXPROBE?dut.u_core.u_end.tv:dut.u_core.u_end.rv)begin V=at;$display("PHASE K TX%0d calendar_event_sample%0d",TXPROBE,at);end
  if(record_rx_v)begin O=at;$display("PHASE K checked_RX_pin_sample%0d",at);end
  #0.01;
  if((TXPROBE?cal_start:cal_start_rx)&&P<0)begin P=at;$display("PHASE K TX%0d cseq_FACE_wire_publication%0d",TXPROBE,at);end
 end
 initial begin
  fdi_tx_up=1;serdes_up=3;kv_drained_local=1;host_drained_local=1;
  repeat(20)@(negedge ck);por_n=1;rst_n=1;
  while(e<100)@(negedge ck);seqepoch=1;host_boot_begin=1;@(negedge ck);seqepoch=0;host_boot_begin=0;
  if(!TXPROBE)begin
   while(e<(MUT?329:330))@(negedge ck);fdi_rx_v=1;fdi_rx_flit={crc,body};@(negedge ck);fdi_rx_v=0;
   while(e<350)@(negedge ck);
  end else begin wait(V>=0);@(negedge ck);end
  if(G!=300 || P-G!=8 || X-P!=1 || I-X!=1 || V-I!=21)$fatal(1,"PHASE_BAD K TX%0d G%0d P%0d X%0d I%0d V%0d",TXPROBE,G,P,X,I,V);
  if(!TXPROBE)begin
   if(MUT)begin if(O>=0 || !epoch_abort)$fatal(1,"PHASE mutant not caught");end
   else if(O-V!=3 || fault || epoch_abort)$fatal(1,"PHASE checked RX failure O%0d V%0d f%b a%b",O,V,fault,epoch_abort);
  end
  $display("PHASE_PASS K TX%0d MUT%0d G%0d P%0d X%0d I%0d V%0d O%0d",TXPROBE,MUT,G,P,X,I,V,O);$finish;
 end
endmodule
