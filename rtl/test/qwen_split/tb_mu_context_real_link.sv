`timescale 1ns/1ps
// Context-transport diagnostic only: real die masters/CRC/SRAM/PHY, frozen MU image prefix.
module tb_mu_context_real_link;
parameter integer MUT=0,FULL=0;
`include "d2d_cal_image_mu.svh"
reg ck=0; always #0.4167 ck=~ck;
reg rst_n=0,go=0,boot=0,ctwe=0,crwe=0,ktwe=0,krwe=0;
reg[5:0]ca=0;reg[31:0]cd=0,kd=0;
wire fep,flr;reg[2:0]bep=0,blr=7;
always @(posedge ck) begin bep<={bep,fep};blr<={blr,flr};end
wire[547:0]crx;wire cslot,cv,cf,kf,cab,kab;wire[7:0]ctf,ktf;
wire cup,kup,ctv,ktv,crv,krv,cphy_rst,kphy_rst;wire[582:0]ctp,ktp,crp,krp,clf,klf;wire clv,klv;
wire[1:0]sk;wire txv,txo,txfault;wire[547:0]txr;
reg tev=0,rq=0;reg[15:0]ep=0;reg[58:0]tag=0;reg[1:0]gen=0;
qkd_host_record_port_mu #(.MU(1),.MUT(MUT==1?1:MUT==2?3:0)) host (
 .ck(ck),.rst_n(rst_n),.send_kind(sk),.request_v(rq),.request_tag(tag),.request_gen(gen),
 .request_token(tag[36:19]),.request_position({5'd0,tag[18:6]}),.token_epoch_valid(tev),.token_epoch(ep),
 .begin_v(1'b0),.begin_epoch(16'd0),.expected_pw(11'd0),.expected_dw(4'd0),.auth_v(1'b0),.auth_epoch(16'd0),
 .auth_digest(64'd0),.program_ready(1'b1),.program_epoch(16'h0a51),.program_digest(64'h0123456789abcdef),
 .authorized_footer_valid(1'b0),.authorized_footer(64'd0),.witness_slot(1'b0),.rx_v(1'b0),.rx_record(548'd0),
 .commit_v(),.installed_valid(),.installed_fusedcap(),.commit_epoch(),.commit_digest(),
 .tx_v(txv),.tx_observed_v(txo),.tx_record(txr),.fault(txfault));
reg prev_sk=0;
always @(posedge ck)if(!rst_n)prev_sk<=0;else prev_sk<=(sk==3);
wire refv,refo,reffault;wire[547:0]refr;
qkd_host_record_port_mu #(.MU(0)) su_ref (
 .ck(ck),.rst_n(rst_n),.send_kind((sk==3&&prev_sk)?2'd3:2'd0),.request_v(rq&&tag[44:43]==0),.request_tag(tag),.request_gen(gen),
 .request_token(tag[36:19]),.request_position({5'd0,tag[18:6]}),.token_epoch_valid(tev&&ep[1:0]==0),.token_epoch(ep),
 .begin_v(1'b0),.begin_epoch(16'd0),.expected_pw(11'd0),.expected_dw(4'd0),.auth_v(1'b0),.auth_epoch(16'd0),
 .auth_digest(64'd0),.program_ready(1'b1),.program_epoch(16'h0a51),.program_digest(64'h0123456789abcdef),
 .authorized_footer_valid(1'b0),.authorized_footer(64'd0),.witness_slot(1'b0),.rx_v(1'b0),.rx_record(548'd0),
 .commit_v(),.installed_valid(),.installed_fusedcap(),.commit_epoch(),.commit_digest(),
 .tx_v(refv),.tx_observed_v(refo),.tx_record(refr),.fault(reffault));
qfd_d2d_static #(.PR(1),.TXDP(D2D_TXDP_C)) u_c (
 .ck(ck),
 .por_n(rst_n),
 .rst_n(rst_n),
 .cfg_tx_we(ctwe),
 .cfg_rx_we(crwe),
 .cfg_addr(ca),
 .cfg_data(cd),
 .cal_start(go),
 .cal_seg(1'b1),
 .fwd_epoch(bep[2]),
 .fwd_link_rst_n(blr[2]),
 .native_tx_slot(),
 .native_tx_slot_kind(),
 .native_tx_slot_beat(),
 .native_tx_v('0),
 .native_tx_payload('0),
 .rx_payload(crx),
 .native_rx_v(),
 .native_rx_slot(),
 .native_rx_slot_kind(),
 .native_rx_slot_beat(),
 .prog_witness_slot(),
 .prog_auth_slot(),
 .prog_context_slot(cslot),
 .prog_tx_observed_v('0),
 .prog_tx_record('0),
 .prog_rx_v(cv),
 .emb_rx_v(),
 .emb_rx_slot(),
 .kv_x3_slot(),
 .x3('0),
 .x3_identity('0),
 .x3_generation('0),
 .status_epoch16(16'h40),
 .vm_drained(1'b1),
 .collective_drained(1'b1),
 .collective_busy('0),
 .crom_fault('0),
 .execution_active(1'b1),
 .admit_ready(1'b1),
 .result_v('0),
 .result_done('0),
 .result_fault('0),
 .result_cause('0),
 .result_tag('0),
 .result_gen('0),
 .result_token('0),
 .result_value('0),
 .result_cycles('0),
 .fdi_tx_up(cup),
 .fdi_tx_v(ctv),
 .fdi_tx_flit(ctp),
 .fdi_rx_v(crv),
 .fdi_rx_flit(crp),
 .phy_rst_n(cphy_rst),
 .epoch_abort(cab),
 .transport_fault(ctf),
 .fault(cf)
);
qkd_d2d_static #(.PR(1),.NTX(3),.TXDP(D2D_TXDP_K)) u_k (
 .ck(ck),
 .por_n(rst_n),
 .rst_n(rst_n),
 .cfg_tx_we(ktwe),
 .cfg_rx_we(krwe),
 .cfg_addr(ca),
 .cfg_data(kd),
 .cal_start(go),
 .cal_seg(1'b1),
 .host_link_reset_req('0),
 .host_recovery_clear('0),
 .host_boot_begin(boot),
 .fwd_epoch(fep),
 .fwd_link_rst_n(flr),
 .att_tx_slot(),
 .att_tx_kind(),
 .att_tx_beat(),
 .att_tx_v('0),
 .att_tx_payload('0),
 .att_rx_v(),
 .att_rx_slot(),
 .att_rx_kind(),
 .att_rx_beat(),
 .rx_payload(),
 .emb_tx_slot(),
 .emb_tx_v('0),
 .emb_tx_payload('0),
 .record_tx_observed_v(txo),
 .record_tx(txr ^ ((MUT==4) ? (548'd1<<59) : 548'd0)),
 .record_send_kind(sk),
 .record_witness_slot(),
 .record_rx_v(),
 .record_rx(),
 .kvn_compiled_identity('0),
 .kvn_compiled_generation('0),
 .kvn_word_valid(),
 .kvn_word_tag(),
 .kvn_word_data(),
 .kvn_word_identity(),
 .kvn_word_generation(),
 .kvn_word_slot(),
 .kvn_word_index(),
 .status_epoch16(16'h40),
 .serdes_up(1'b1),
 .kv_drained_local(1'b1),
 .kv_flush_local('0),
 .host_drained_local(1'b1),
 .kv_active_local('0),
 .link_up(),
 .transport_fault(ktf),
 .native_links_drained(),
 .native_link_reset_seen(),
 .native_retrained(),
 .abort_drained(),
 .native_kv_drained(),
 .native_vm_drained(),
 .native_collective_drained(),
 .native_host_drained(),
 .native_collective_busy(),
 .native_kv_flush(),
 .native_admit_ready(),
 .crom_fault(),
 .execution_active(),
 .engine_result_v(),
 .engine_result_done(),
 .engine_result_fault(),
 .engine_result_cause(),
 .engine_result_tag(),
 .engine_result_gen(),
 .engine_result_token(),
 .engine_result_value(),
 .engine_result_cycles(),
 .fdi_tx_up(kup),
 .fdi_tx_v(ktv),
 .fdi_tx_flit(ktp),
 .fdi_rx_v(krv),
 .fdi_rx_flit(krp),
 .phy_rst_n(kphy_rst),
 .epoch_abort(kab),
 .recovery_cycles(),
 .fault(kf)
);

reg corrupt=0,corrupted=0;
always @(negedge ck)begin corrupt<=0;if(MUT==3&&klv&&!corrupted)begin corrupt<=1;corrupted<=1;end end
// The same declared PHY model as the historical paired exchange, LAT=5.
ot_qkvd_ucie_x64_phy_model #(.LAT(5),.FW(583)) cp(.clk(ck),.rst_n(cphy_rst),.tx_up(cup),.tx_v(ctv),.tx_flit(ctp),
 .rx_v(crv),.rx_flit(crp),.link_v(clv),.link_flit(clf),.far_v(klv),.far_flit(klf^(corrupt?(583'd1<<76):583'd0)));
ot_qkvd_ucie_x64_phy_model #(.LAT(5),.FW(583)) kp(.clk(ck),.rst_n(kphy_rst),.tx_up(kup),.tx_v(ktv),.tx_flit(ktp),
 .rx_v(krv),.rx_flit(krp),.link_v(klv),.link_flit(klf),.far_v(clv),.far_flit(clf));
wire hev,hcap,hfault;wire[15:0]hep,hie;wire[58:0]htag;wire[1:0]hgen;wire[63:0]hdg;
qfd_host_native_context_rx face(.ck(ck),.rst_n(rst_n),.receive_slot(cslot),.rx_v(cv),.rx_record(crx),
 .program_begin_v(1'b0),.program_ready(1'b1),.installed_fusedcap(1'b0),.program_epoch(16'h0a51),.program_digest(64'h0123456789abcdef),
 .head_context_v(1'b0),.head_stage(6'd0),.head_token(18'd0),.head_position(18'd0),.native_active(1'b0),
 .host_epoch_valid(hev),.host_epoch(hep),.host_tag(htag),.host_gen(hgen),.host_fusedcap(hcap),
 .host_image_epoch(hie),.host_image_digest(hdg),.fault(hfault));
wire[128:0]cx;wire[1:0]cu;wire mf;
qfd_mu_ctx_rx #(.NU(4)) mu(.ck(ck),.rst_n(rst_n),.context_slot(cslot),.rx_v(cv),.rx_hdr(crx[547:517]),
 .rx_beat(crx[516:512]),.rx_tag(crx[58:0]),.ctx_x(cx),.ctx_user(cu),.mu_fault(mf));
reg[58:0]expected[0:3];reg[1:0]eg[0:3];integer n=0,nload=0,nref=0,errs=0,cyc=0,run=0;
always @(posedge ck)cyc<=cyc+1;
always @(negedge ck)if(rst_n)begin
 if(sk==3)$display("MUCTX_SLOT cycle=%0d run=%0d",cyc,run);
 if(txo)$display("MUCTX_HOST_TX cycle=%0d run=%0d owner=%h gen=%h",cyc,run,txr[58:0],txr[60:59]);
 if(refo)begin
  $display("MUCTX_SU_REF cycle=%0d run=%0d identical=%0d",cyc,run,(txo&&txr===refr));
  if(!txo||txr!==refr||reffault)errs=errs+1;nref=nref+1;
 end
 if(cv&&cslot)begin
  $display("MUCTX_WIRE cycle=%0d run=%0d n=%0d user=%0d owner=%h gen=%h",cyc,run,n,crx[44:43],crx[58:0],crx[60:59]);
  if(n>=6)errs=errs+1;
  else if(crx[58:0]!==expected[(n%2==0)?(n/2+1):0]||crx[60:59]!==eg[(n%2==0)?(n/2+1):0])errs=errs+1;
  n=n+1;
 end
 if(cx[128])begin
  $display("MUCTX_LOAD cycle=%0d user=%0d ctx=%h",cyc,cu,cx);
  if(cu<1||cu>3||cx[36*(cu-1)+:18]!=={5'd0,expected[cu][18:6]}||cx[36*(cu-1)+18+:18]!==expected[cu][36:19])errs=errs+1;
  nload=nload+1;
 end
end
function automatic[31:0]word(input[1023:0]img,input integer idx,input integer lastidx);
 reg[31:0]v;begin v=img[32*idx+:32];if(!FULL&&idx==lastidx)v[17]=1'b1;
 if(MUT==5&&img===D2D_CAL_C_RX_IMG&&idx==D2D_CAL_C_RX_SEG1)v=v+32'h40000;word=v;end
endfunction
task tick(input integer t);repeat(t)@(negedge ck);endtask
integer i,u,start;
initial begin
 tick(3);rst_n=1;tick(6);
 for(i=0;i<32;i=i+1)begin
 ca=6'(i);cd=word(D2D_CAL_C_TX_IMG,i,D2D_CAL_C_TX_SEG1);kd=word(D2D_CAL_K_TX_IMG,i,D2D_CAL_K_TX_SEG1+1);ctwe=1;ktwe=1;tick(1);ctwe=0;ktwe=0;
 cd=word(D2D_CAL_C_RX_IMG,i,D2D_CAL_C_RX_SEG1+1);kd=word(D2D_CAL_K_RX_IMG,i,D2D_CAL_K_RX_SEG1);crwe=1;krwe=1;tick(1);crwe=0;krwe=0;
 end
 ca=32;cd=D2D_CAL_C_TX_SEG1;kd=D2D_CAL_K_TX_SEG1;ctwe=1;ktwe=1;tick(1);ctwe=0;ktwe=0;
 cd=D2D_CAL_C_RX_SEG1;kd=D2D_CAL_K_RX_SEG1;crwe=1;krwe=1;tick(1);crwe=0;krwe=0;
 wait(cup&&kup);tick(2);boot=1;tick(1);boot=0;wait(u_k.u_core.eb);tick(100);
 for(u=0;u<4;u=u+1)begin
 ep=16'h40+16'(u);tev=1;tick(1);tev=0;tick(1);
 expected[u]={ep,6'd0,18'(100+u),13'(20+u),6'd0};eg[u]=2'(u);
 tag=expected[u];gen=eg[u];rq=1;tick(1);rq=0;tick(1);
 end
 for(run=0;run<(FULL?1:3);run=run+1)begin
 start=cyc;go=1;tick(1);go=0;tick(FULL?60:80);
 $display("MUCTX_END run=%0d n=%0d loads=%0d native=%b%b abort=%b%b transport=%h/%h host=%b face=%b mu=%b faceowner=%h facegen=%h",run,n,nload,cf,kf,cab,kab,ctf,ktf,txfault,hfault,mf,htag,hgen);
 if(!FULL&&(cf||kf||cab||kab||txfault||hfault||mf||htag!==expected[0]||hgen!==eg[0]))errs=errs+1;
 if(run<2&&!FULL)tick(D2D_TOKEN_PERIOD-(cyc-start));
 end
 if(FULL)begin
  if(cf||kf||cab||kab)$display("MUCTX_FULL_STREAM_DIAGNOSTIC_NATIVE_FAULT expected unsupported later producer scope");
  else $display("MUCTX_FULL_STREAM_DIAGNOSTIC_NO_NATIVE_FAULT_YET");
 end else if(errs==0&&n==6&&nload==3&&nref==3)$display("MUCTX_REAL_LINK_PASS four distinct contexts; three filler loads; user0 restored; component only");
 else $display("MUCTX_REAL_LINK_FAIL errors=%0d n=%0d loads=%0d",errs,n,nload);
 $finish;
end
endmodule
