// Additive minimum integration. E/BF16 events are destination-visible receipts;
// config snapshot and numerical engine are not implemented by this component.
module ot_dsrom_softmax_epoch_join(
 input wire clk_chain,clk_stream,cold_abort,
 input wire in_valid,output wire in_ready,input wire [1083:0] in_packet,
 output wire done_valid,input wire done_ready,output wire [63:0] done_packet,
 input wire endpoint_event_valid,input wire [2:0] endpoint_event_kind,
 input wire [31:0] endpoint_epoch,input wire [15:0] endpoint_tag,
 output wire endpoint_event_ready,
 input wire den_valid,input wire [31:0] den_epoch,input wire [15:0] den_tag,
 output wire core_valid,core_pv,output wire [8191:0] core_data,
 output wire [15:0] core_tag,output wire [6:0] core_addr,
 output wire [2:0] phase_kind,output wire [6:0] phase_row,
 output wire active_out,fault
);
 wire crst,srst;
 ot_hbm_collective_reset_entry #(.ENABLE(1)) resets(.clk_stream(clk_stream),.clk_link(clk_chain),
  .por_stream(cold_abort),.por_link(cold_abort),.rst_n(srst),.prst_n(crst));
 wire qv,qr,qe,qwe,qfault,fifo_in_ready,raw_done_valid;
 assign in_ready=crst&&fifo_in_ready;
 assign done_valid=crst&&raw_done_valid;wire [1083:0] q;
 ot_hbm_collective_protected_cdc #(.ENABLE(1),.W(1084),.AW(6)) ingress(
  .wclk(clk_chain),.wrst_n(crst),.in_v(in_valid&&crst),.in_r(fifo_in_ready),.in_d(in_packet),
  .rclk(clk_stream),.rrst_n(srst),.out_v(qv),.out_r(qr),.out_d(q),.wempty(qwe),.rempty(qe),.fault(qfault));
 (* keep="true",dont_touch="true" *) reg active,active_n,have_epoch,have_epoch_n,failed,failed_n;
 (* keep="true",dont_touch="true" *) reg [31:0] epoch,epoch_n,last_epoch,last_epoch_n;
 (* keep="true",dont_touch="true" *) reg [15:0] tag,tag_n;
 wire integrity=(active_n==~active)&&(have_epoch_n==~have_epoch)&&(failed_n==~failed)
  &&(epoch_n==~epoch)&&(last_epoch_n==~last_epoch)&&(tag_n==~tag);
 wire [1:0] opcode=q[1083:1082];wire [31:0] packet_epoch=q[1081:1050];
 wire [15:0] packet_tag=q[1049:1034];wire [6:0] packet_addr=q[1033:1027];wire [2:0] packet_beat=q[1026:1024];
 wire bankfault,phasefault,donefault,bankready,bankwrready,bankbusy,score_done,pv_done;
 wire phasebusy,phasecmdready,phaseready,unusedhalf;wire [15:0] phase_tag;
 wire replayready,writecommit,corrected,raw_core_valid;
 assign core_valid=raw_core_valid&&!fault&&srst;wire [6:0] commitaddr;
 wire done_wready,done_wempty,done_rempty;
 assign fault=failed||!integrity||qfault||donefault||bankfault||phasefault;
 assign active_out=active;
 wire fill=(phase_kind==0||phase_kind==4)&&phaseready&&active;
 `ifdef SOFTMAX_EPOCH_IGNORE_EPOCH
 wire epoch_matches=1'b1;
`else
 wire epoch_matches=(packet_epoch==epoch);
`endif
 wire data_match=active&&epoch_matches&&(packet_tag==tag)&&(packet_addr==phase_row);
 wire begin_bad=(q[1023:1]!=0)||(packet_addr!=0)||(packet_beat!=0)||active||!bankready||!phasecmdready||(have_epoch&&packet_epoch<=last_epoch);
 wire badpacket=qv&&((opcode>=2)||(opcode==0&&begin_bad)||(opcode==1&&!data_match));
 assign qr=srst&&!fault && (badpacket || opcode==0 || (opcode==1&&fill&&bankwrready));
 wire take=qv&&qr;
 wire start=take&&opcode==0&&!badpacket;
 wire writevalid=take&&opcode==1&&!badpacket;
 wire ext_bad=endpoint_event_valid&&(!active||endpoint_epoch!=epoch||endpoint_tag!=tag||
    !(endpoint_event_kind==2||endpoint_event_kind==3||endpoint_event_kind==6||endpoint_event_kind==7));
 wire den_bad=den_valid&&(!active||den_epoch!=epoch||den_tag!=tag);
 assign endpoint_event_ready=srst&&active&&phaseready&&!fault&&
    (phase_kind==2||phase_kind==3||phase_kind==6||phase_kind==7);
 wire external_event=endpoint_event_valid&&!ext_bad&&!fault;
 wire collision=(writecommit&&core_valid)||((writecommit||core_valid)&&external_event);
 `ifdef SOFTMAX_EPOCH_EARLY_COMPLETION
 wire retirement=1'b1;
`else
 wire retirement=!phasebusy;
`endif
 wire finish=active&&retirement&&score_done&&pv_done&&qe&&!fault;
 wire release_bank=finish&&done_wready;
 ot_hbm_collective_protected_cdc #(.ENABLE(1),.W(64),.AW(6)) completion(
  .wclk(clk_stream),.wrst_n(srst),.in_v(finish),.in_r(done_wready),.in_d({epoch,tag,16'd0}),
  .rclk(clk_chain),.rrst_n(crst),.out_v(raw_done_valid),.out_r(done_ready&&crst),.out_d(done_packet),
  .wempty(done_wempty),.rempty(done_rempty),.fault(donefault));
 wire event_v=writecommit||core_valid||external_event;
 wire [2:0] event_kind=writecommit?(commitaddr>=40?3'd4:3'd0):core_valid?(core_pv?3'd5:3'd1):endpoint_event_kind;
 ot_dsrom_softmax_phase phases(.clk(clk_stream),.rst_n(srst),.cmd_v(start),.cmd_short(q[0]),.cmd_fault(1'b0),
  .cmd_tag(packet_tag),.cmd_ready(phasecmdready),.event_v(event_v),.event_kind(event_kind),.event_tag(tag),
  .event_ready(phaseready),.expected_kind(phase_kind),.memory_row(phase_row),.bf16_upper_half(unusedhalf),
  .den_v(den_valid&&!den_bad&&!fault),.den_tag(den_tag),.busy(phasebusy),.fault(phasefault),.active_tag(phase_tag));
 wire replayvalid=active&&!fault&&phaseready&&(phase_kind==1||phase_kind==5)&&replayready;
 ot_dsrom_softmax_sram_join bank(.clk(clk_stream),.rst_n(srst),.begin_valid(start),.begin_short(q[0]),
  .begin_tag(packet_tag),.begin_ready(bankready),.release_valid(release_bank),
  .wr_valid(writevalid),.wr_pv(phase_kind==4),.wr_beat(packet_beat),.wr_tag(packet_tag),.wr_data(q[1023:0]),
  .wr_ready(bankwrready),.write_commit(writecommit),.write_commit_addr(commitaddr),
  .replay_valid(replayvalid),.replay_pv(phase_kind==5),.replay_tag(tag),.replay_ready(replayready),
  .core_valid(raw_core_valid),.core_pv(core_pv),.core_data(core_data),.core_tag(core_tag),.core_addr(core_addr),
  .corrected(corrected),.fault(bankfault),.busy(bankbusy),.score_done(score_done),.pv_done(pv_done));
 always @(posedge clk_stream)begin
  if(!srst)begin
   active<=0;active_n<=1;have_epoch<=0;have_epoch_n<=1;failed<=0;failed_n<=1;
   epoch<=0;epoch_n<=~32'd0;last_epoch<=0;last_epoch_n<=~32'd0;tag<=0;tag_n<=~16'd0;
  end else if(fault||badpacket||ext_bad||den_bad||collision)begin failed<=1;failed_n<=0;end
  else begin
   if(start)begin active<=1;active_n<=0;have_epoch<=1;have_epoch_n<=0;
    epoch<=packet_epoch;epoch_n<=~packet_epoch;last_epoch<=packet_epoch;last_epoch_n<=~packet_epoch;
    tag<=packet_tag;tag_n<=~packet_tag;end
   if(release_bank)begin active<=0;active_n<=1;end
  end
 end
endmodule
