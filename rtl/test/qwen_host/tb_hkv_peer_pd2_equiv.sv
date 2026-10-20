`timescale 1ns/1ps
// KV-HOST/PEER r6 (10-19): qkd_host_ctrl_token_service_packet_collected (original) vs _pd2 (r6: data-only head flags,
// parallel per-source sequence compares, one-edge-ahead status_changed, delayed output arrays with registered KEPT enable
// copies), same stimulus as tb_hkv_peer_pd_equiv (HKV-PROMPT6).  Outputs tk8/kst8/boot8/seen/service_epoch8 of _pd2 must
// equal the original's one edge earlier (both cleared by rst_n; the bench's one-edge history clears with rst_n too); every
// other output is compared every edge.  -DQKD_HR_PEPD2_MUTANT (sc_q from current values, one edge stale) must FAIL.
module tb_hkv_peer_pd2_equiv #(parameter integer ES=1, parameter integer DIEID=0, parameter integer SEED=1);
 reg ck=0; always #1 ck=~ck;
 reg rst_n=0,por_n=0; reg[2:0]die_id=DIEID[2:0];
 reg rx_v=0; reg[511:0]rx_d=0; reg tx_cr=0;
 reg[92:0]local_tk=0; reg[9:0]local_kst=0; reg[1:0]local_boot=0;
 reg cmd_v=0; reg[181:0]cmd_hc=0;
 reg startup_allowed=1,local_service_ready=0; reg[15:0]local_service_epoch=0;
 reg begin_v=0; reg[15:0]begin_epoch=0;
 reg token_wrap_fence_valid=0,token_wrap_drained=0,token_wrap_link_reset_seen=0,token_wrap_retraining_done=0,token_allocator_fault=0;
 reg package_abort=0; reg[3:0]abort_drained=0; reg token_request_ready=0;
 reg token_grant_valid=0; reg[15:0]token_grant_epoch=0; reg[17:0]token_grant_token=0,token_grant_position=0;
 reg[1:0]token_grant_generation=0; reg[58:0]token_grant_tag=0;
 reg allocated_valid=0,allocated_delivered=0; reg[15:0]allocated_epoch=0; reg[17:0]allocated_token=0,allocated_position=0;
 reg[1:0]allocated_generation=0; reg terminal_accepted=0;
`define OT_TS_PORTS(p) \
  .ck(ck),.rst_n(rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(p``rx_cr),.tx_v(p``tx_v),.tx_d(p``tx_d),.tx_cr(tx_cr), \
  .local_tk(local_tk),.local_kst(local_kst),.local_boot(local_boot),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.cmd_cr(p``cmd_cr),.hc(p``hc), \
  .tk8(p``tk8),.kst8(p``kst8),.boot8(p``boot8),.seen(p``seen),.fault(p``fault),.startup_allowed(startup_allowed), \
  .local_service_ready(local_service_ready),.local_service_epoch(local_service_epoch),.begin_v(begin_v),.begin_epoch(begin_epoch), \
  .begin_cr(p``begin_cr),.begin_available(p``begin_available),.service_begin_v(p``service_begin_v),.service_begin_epoch(p``service_begin_epoch), \
  .pending_advertised(p``pending_advertised),.pending_epoch(p``pending_epoch),.service_ready8(p``service_ready8),.pending_ack8(p``pending_ack8), \
  .service_epoch8(p``service_epoch8),.ingest_permission(p``ingest_permission),.por_n(por_n),.token_wrap_fence_valid(token_wrap_fence_valid), \
  .token_wrap_drained(token_wrap_drained),.token_wrap_link_reset_seen(token_wrap_link_reset_seen),.token_wrap_retraining_done(token_wrap_retraining_done), \
  .token_allocator_fault(token_allocator_fault),.package_abort(package_abort),.abort_drained(abort_drained), \
  .token_request_valid(p``token_request_valid),.token_request_ready(token_request_ready),.token_request_token(p``token_request_token), \
  .token_request_position(p``token_request_position),.token_request_generation(p``token_request_generation),.token_grant_valid(token_grant_valid), \
  .token_grant_ready(p``token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token), \
  .token_grant_position(token_grant_position),.token_grant_generation(token_grant_generation),.token_grant_tag(token_grant_tag), \
  .allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_epoch(allocated_epoch),.allocated_token(allocated_token), \
  .allocated_position(allocated_position),.allocated_generation(allocated_generation),.token_epoch_valid(p``token_epoch_valid),.token_epoch(p``token_epoch), \
  .cancel_valid(p``cancel_valid),.cancel_tag(p``cancel_tag),.cancel_generation(p``cancel_generation),.cancel_done(p``cancel_done), \
  .cancel_fault(p``cancel_fault),.cancel_drained(p``cancel_drained),.terminal_accepted(terminal_accepted)
`define OT_TS_DECL(p) \
  wire p``rx_cr,p``tx_v,p``cmd_cr,p``fault,p``begin_cr,p``begin_available,p``service_begin_v,p``pending_advertised,p``ingest_permission; \
  wire p``token_request_valid,p``token_grant_ready,p``token_epoch_valid,p``cancel_valid,p``cancel_done,p``cancel_fault; \
  wire[511:0]p``tx_d; wire[181:0]p``hc; wire[743:0]p``tk8; wire[79:0]p``kst8; wire[15:0]p``boot8,p``service_begin_epoch,p``pending_epoch,p``token_epoch; \
  wire[7:0]p``seen,p``service_ready8,p``pending_ack8; wire[127:0]p``service_epoch8; wire[17:0]p``token_request_token,p``token_request_position; \
  wire[1:0]p``token_request_generation,p``cancel_generation; wire[58:0]p``cancel_tag; wire[3:0]p``cancel_drained; \
  wire[1624:0] p``now = {p``rx_cr,p``tx_v,p``cmd_cr,p``fault,p``begin_cr,p``begin_available,p``service_begin_v,p``pending_advertised, \
   p``ingest_permission,p``token_request_valid,p``token_grant_ready,p``token_epoch_valid,p``cancel_valid,p``cancel_done,p``cancel_fault, \
   p``tx_d,p``hc,p``service_begin_epoch,p``pending_epoch,p``token_epoch,p``service_ready8,p``pending_ack8, \
   p``token_request_token,p``token_request_position,p``token_request_generation,p``cancel_generation,p``cancel_tag,p``cancel_drained}; \
  wire[975:0] p``dly = {p``tk8,p``kst8,p``boot8,p``seen,p``service_epoch8};
 `OT_TS_DECL(a_)
 `OT_TS_DECL(b_)
 qkd_host_ctrl_token_service_packet_collected    #(.STRAPPED(1),.ENABLE_SERVICE(ES),.ENABLE_TOKEN(ES)) ua(`OT_TS_PORTS(a_));
 qkd_host_ctrl_token_service_packet_collected_pd2 #(.STRAPPED(1),.ENABLE_SERVICE(ES),.ENABLE_TOKEN(ES)) ub(`OT_TS_PORTS(b_));
 integer seed=SEED, cyc, mism=0, mismd=0, txs=0, acc=0, tkw=0, hcw=0, rsts=0, i, s, kind;
 reg[15:0] seq[0:7];
 reg[511:0] p;
 task automatic reset_all; begin
  rst_n=0; por_n=($random(seed)&1)?1'b0:por_n; rsts=rsts+1; for(i=0;i<8;i=i+1)seq[i]=0;
  repeat(3)@(negedge ck); por_n=1; repeat(2)@(negedge ck); rst_n=1; end endtask
 initial begin
  for(i=0;i<8;i=i+1)seq[i]=0;
  repeat(3)@(negedge ck); por_n=1; repeat(4)@(negedge ck); rst_n=1;
  for(cyc=0;cyc<60000;cyc=cyc+1)begin
   @(negedge ck);
   if(a_fault && ($random(seed)%16)==0) reset_all();
   if(($random(seed)%3000)==0) reset_all();
   tx_cr = a_tx_v ? (($random(seed)&3)!=0) : 1'b0;
   local_tk = ($random(seed)%8==0) ? {$random(seed),$random(seed),$random(seed)} : local_tk;
   // r6: sparse status changes (the HKV-PROMPT6 stimulus changed local_kst every edge, so status_changed was always 1)
   local_kst = ($random(seed)%16==0) ? $random(seed) : local_kst; local_boot = ($random(seed)%32==0) ? $random(seed) : local_boot;
   local_service_ready = ($random(seed)%16==0) ? ~local_service_ready : local_service_ready; local_service_epoch = ($random(seed)%8==0)?$random(seed)%4:local_service_epoch;
   startup_allowed = ($random(seed)%16)!=0;
   cmd_v = (DIEID==0) && ($random(seed)%24)==0; cmd_hc = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
   begin_v = (DIEID==0) && ($random(seed)%200)==0; begin_epoch = begin_epoch + (($random(seed)%4)!=0);
   token_request_ready=$random(seed); token_grant_valid=($random(seed)%8)==0; allocated_valid=($random(seed)%8)==0;
   package_abort=($random(seed)%500)==0; abort_drained=$random(seed); terminal_accepted=$random(seed);
   rx_v = ($random(seed)%3)==0;
   if(rx_v)begin
    p = 0; kind = $random(seed)%16; if(kind<0)kind=-kind;
    s = (DIEID==0) ? 1+({$random(seed)}%7) : 0;
    if(DIEID==0)begin
     p[7:0]=8'h21; p[15:8]=ES?2:1; p[18:16]=s; p[31:24]=8'd1; p[47:32]=seq[s];
     p[140:48]={$random(seed),$random(seed),$random(seed)}; p[150:141]=$random(seed); p[152:151]=$random(seed);
     if(ES)begin p[153]=$random(seed); p[169:154]=ua.epoch; end
    end else begin
     p[7:0]=(ES&&($random(seed)%4==0))?8'h23:8'h22; p[15:8]=1; p[18:16]=0; p[31:24]=8'd1<<DIEID; p[47:32]=seq[0];
     if(p[7:0]==8'h22) p[229:48]={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)} & {182{1'b1}};
     else begin p[15:8]=2; p[63:48]=ua.epoch+1; end
     if(ES&&p[7:0]==8'h22) p[86]=0;
    end
    if(kind==0) p[300+({$random(seed)}%200)]=1;        // high bit set -> wide zero test fails
    else if(kind==1) p[47:32]=p[47:32]+3;               // sequence error
    else if(kind==2) p[23:19]=1;                        // header error
    if(kind>2 && kind!=15) seq[s]=seq[s]+1;
    rx_d = p;
   end else rx_d = {16{$random(seed)}};
  end
  $display("HKV_PEER_PD2_EQUIV ES=%0d die=%0d cycles=%0d accepted=%0d tk8_writes=%0d hc_writes=%0d tx_status=%0d resets=%0d mismatches=%0d (now %0d, delayed %0d)", ES, DIEID, cyc, acc, tkw, hcw, txs, rsts, mism+mismd, mism, mismd);
  if(mism==0 && mismd==0 && acc>500 && tkw>100) $display("HKV_PEER_PD2_EQUIV PASS"); else $display("HKV_PEER_PD2_EQUIV FAIL");
  $finish;
 end
 always @(posedge ck)begin
  if(ua.take && !a_fault) acc<=acc+1;
  if(a_tx_v) txs<=txs+1;
 end
 reg[743:0] tk_prev; reg[181:0] hc_prev;
 always @(posedge ck)begin tk_prev<=a_tk8; hc_prev<=a_hc; if(tk_prev!==a_tk8)tkw<=tkw+1; if(hc_prev!==a_hc)hcw<=hcw+1; end
// one-edge history of the original's delayed set (cleared with rst_n, as both designs' arrays); compared at negedge
 reg[975:0] a_dly_q;
 always @(posedge ck or negedge rst_n) if(!rst_n) a_dly_q<=0; else a_dly_q<=a_dly;
 always @(negedge ck)begin
  if(a_now !== b_now)begin mism=mism+1; if(mism<5)$display("MISMATCH now t=%0t fault %b/%b tx_v %b/%b hc %h/%h", $time, a_fault, b_fault, a_tx_v, b_tx_v, a_hc, b_hc); end
  if(a_dly_q !== b_dly)begin mismd=mismd+1; if(mismd<5)$display("MISMATCH delayed t=%0t tk8 %h / %h", $time, a_dly_q[975:232], b_tk8); end
 end
endmodule
