// KV-HOST/PEER r6 (10-19): qkd_host_ctrl_token_service_packet_collected_pd2 = the _pd fork (registered queue head h + zero
// flags hz, constant-index slice writes; gen_peer_pd.py) with the SAFE item 3/4 redesign of the r5 gate CTS classes
// (h -> ~17-level accept decode -> 744-flop tk8/kst8 enable -135.2 ps; lt -> 93-b status compare -> 512-b tx_d -88.3 ps;
// h -> seq_rx -73.2; h -> kst8/service_epoch8/hc -110..-58).  Hand-written from _pd (tools/qwen_kv_die/host_cluster/
// mk_peer_pd2.py applies each edit exactly once and records the result; do not edit by hand):
//  (1) DATA-ONLY HEAD FLAGS: type/version/header/rs==0/token-frame tests and the source one-hot are computed from the word
//      at queue write (qf, beside qz) and registered with the head (hf).  Pure functions of the word: identical decode.
//  (2) SEQUENCE: seqp1[src] = seq_rx[src]+1 kept as a register (written rs+1 wherever seq_rx was written rs; reset 1), and
//      the 8 per-source compares run in parallel and are selected by the one-hot source (no 8:1 mux -> adder -> compare).
//      sequence_ok identical.
//  (3) STATUS CHANGE: sc_q == status_changed every edge, computed one edge ahead from the next-edge values (lt'=local_tk,
//      last'=fire?lt:last, ...); the TX status branch reads sc_q.  Bit/cycle exact, 0 cycles.
//  (4) DELAYED OUTPUT ARRAYS (+1 edge): tk8, kst8, boot8, seen, service_epoch8 are outputs only (never read here).  Their
//      writes are registered as one-hot enables + data (dl_*) and applied on the next edge, so each output equals the
//      _pd output one edge earlier (both cleared by rst_n).  The enables are KEPT copies (4 per source / role slot,
//      <= 31 loads each; 4 per service-epoch clear) instead of one decode driving 744 flops.
// Every other output is bit/cycle exact against _pd / the original.  Bench rtl/test/qwen_host/tb_hkv_peer_pd2_equiv.sv
// (tools/qwen_kv_die/host_cluster/bench/peer_pd2_equiv.sh): original vs _pd2, delayed set vs the original one edge
// earlier, all other outputs every edge.  QKD_HR_PEPD2_MUTANT (bench only): sc_q from the current instead of the next-edge values (must FAIL).
`timescale 1ns/1ps
// Separate DEFAULT_OFF token transport candidate. Token epoch0 is valid.
// Seven-copy command storage is reserved before accepting the central grant.
// Abort cancels only a genuine retained allocated identity with four real drains.
// Separate DEFAULT_OFF service candidate. OFF keeps strict original CTRLv1.
// ON uses status21v2 ready153/epoch169:154 and addressed BEGIN23v2 epoch63:48.
// TOKEN candidate uses BEGIN23v2 bit64 PERMIT after all8 real pendingACKs.
// Peers retain early ING in real16-entry queue until matching permit arrives.
// Original HC22v1, rawhc182, tk93, kst10 and genuine boot2 stay exact.
// BEGIN reserves one command credit only at a registered HC-idle boundary.
// DIE0 accepts hc commands against four credits. It delivers locally and
// sends one addressed copy to each of the other seven dies. A credit returns
// only after all copies were emitted. Routing preserves per-source FIFO order.
// Status snapshots send on relevant-state change; active cycle counter changes
// alone do not flood the link. Complete tk including final cycle count is sent.
module qkd_host_ctrl_token_service_packet_collected_pd2 #(parameter integer DIE=0,MUT=0,STRAPPED=0,ENABLE_SERVICE=0,ENABLE_TOKEN=0)(
 input wire ck,rst_n,input wire[2:0]die_id,
 input wire rx_v,input wire[511:0]rx_d,output reg rx_cr,
 output reg tx_v,output reg[511:0]tx_d,input wire tx_cr,
 input wire[92:0] local_tk,input wire[9:0]local_kst,input wire[1:0]local_boot,
 input wire cmd_v,input wire[181:0]cmd_hc,output reg cmd_cr,
 output reg[181:0]hc,
 output reg[743:0]tk8,output reg[79:0]kst8,output reg[15:0]boot8,output reg[7:0]seen,
 output reg fault,
 input wire startup_allowed,input wire local_service_ready,input wire[15:0]local_service_epoch,
 input wire begin_v,input wire[15:0]begin_epoch,
 output reg begin_cr,begin_available,
 output reg service_begin_v,output reg[15:0]service_begin_epoch,
 output reg pending_advertised,output reg[15:0]pending_epoch,
 output reg[7:0]service_ready8,pending_ack8,
 output reg[127:0]service_epoch8,output reg ingest_permission,
 input wire por_n,token_wrap_fence_valid,token_wrap_drained,token_wrap_link_reset_seen,token_wrap_retraining_done,
 input wire token_allocator_fault,
 input wire package_abort,input wire[3:0]abort_drained,
 output reg token_request_valid,input wire token_request_ready,
 output reg[17:0]token_request_token,token_request_position,output reg[1:0]token_request_generation,
 input wire token_grant_valid,output reg token_grant_ready,
 input wire[15:0]token_grant_epoch,input wire[17:0]token_grant_token,token_grant_position,
 input wire[1:0]token_grant_generation,input wire[58:0]token_grant_tag,
 input wire allocated_valid,allocated_delivered,input wire[15:0]allocated_epoch,
 input wire[17:0]allocated_token,allocated_position,input wire[1:0]allocated_generation,
 output reg token_epoch_valid,output reg[15:0]token_epoch,
 output reg cancel_valid,output reg[58:0]cancel_tag,output reg[1:0]cancel_generation,
 output reg cancel_done,cancel_fault,output reg[3:0]cancel_drained,input wire terminal_accepted
);
 reg[2:0]did_q,die_capture;reg role_valid,die_sampled;
 wire[2:0]role=STRAPPED?did_q:3'(DIE);
 reg rv,tc,cv;reg[511:0]rd;reg[181:0]cd;reg[92:0]lt;reg[9:0]lk;reg[1:0]lb;
 reg[511:0]q[0:3];reg[1:0]wp,rp;reg[2:0]count;
 reg[181:0]cq[0:3];reg[1:0]cw,cr;reg[2:0]cn;
 reg[7:0]credits;reg[15:0]seq_tx;reg[127:0]seqp1;reg[7:0]seq_seen;
 reg lready,biv,startup_q;reg[15:0]lepoch,bepoch,epoch,last_epoch;
 reg last_ready,begin_pending,begin_busy,epoch_active;
 reg permit_pending,permit_busy,permit_sent,peer_permit;
 // All allocator/abort faces captured before comparisons, enables or outputs.
 reg abort_q,abort_seen,request_ready_q,grant_valid_q,grant_low,allocated_vq,allocated_dq,terminal_ack_q;
 reg[3:0]drain_q;reg[15:0]grant_epoch_q,allocated_epoch_q;
 reg[17:0]grant_token_q,grant_position_q,allocated_token_q,allocated_position_q;
 reg[1:0]grant_generation_q,allocated_generation_q;reg[58:0]grant_tag_q;
 reg allocator_fault_q,local_emitted;reg allocator_sampled;reg wrap_vq,wrap_dq,wrap_rq,wrap_tq;reg peer_epoch_seen;reg[15:0]peer_last_epoch;
 wire peer_epoch_fresh=MUT==11||!peer_epoch_seen||h[245:230]>peer_last_epoch;
 wire peer_service_fresh=MUT==20||(!ENABLE_SERVICE?h[262:247]==0:(h[262:247]==epoch&&lepoch==epoch&&lready&&((!epoch_active&&startup_q)||pending_ack8[role]))&&(MUT==21||!ENABLE_SERVICE||!epoch_active||peer_permit));
 wire peer_token_frame=ENABLE_TOKEN&&role!=0&&src_oh[0]&&f_t22&&f_v2&&f_tok22&&hz[5];
 wire peer_token_accept=rst_n&&take&&hdr&&sequence_ok&&peer_token_frame&&peer_epoch_fresh&&peer_service_fresh&&!(abort_seen||abort_q||reset_abort_seen);
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin retained_request<=0;retained_allocated_seen<=0;reset_abort_seen<=0;job_token<=0;job_position<=0;job_generation<=0;end
  else begin
   if(!rst_n&&retained_request)reset_abort_seen<=1;
   if(ENABLE_TOKEN&&wrap_vq&&wrap_dq&&wrap_rq&&wrap_tq)reset_abort_seen<=0;
   if(token_request_valid&&request_ready_q)begin
    retained_request<=1;retained_allocated_seen<=0;job_token<=token_request_token;job_position<=token_request_position;job_generation<=token_request_generation;
   end
   if(retained_request&&allocated_vq)retained_allocated_seen<=1;
   if((retained_allocated_seen&&rst_n&&allocator_sampled&&!allocated_vq)||(cancel_valid&&terminal_ack_q))begin
    retained_request<=0;retained_allocated_seen<=0;reset_abort_seen<=0;
   end
  end
 end
 always @(posedge ck or negedge por_n)begin
  if(!por_n)begin peer_epoch_seen<=0;peer_last_epoch<=0;end
  else if(ENABLE_TOKEN&&wrap_vq&&wrap_dq&&wrap_rq&&wrap_tq)begin peer_epoch_seen<=0;end
  else if(peer_token_accept)begin peer_epoch_seen<=1;peer_last_epoch<=h[245:230];end
 end
 reg grant_wait,request_accepted,cancel_consumed;reg[17:0]job_token,job_position;reg[1:0]job_generation;reg retained_request,retained_allocated_seen,reset_abort_seen;reg[15:0]active_epoch;
 reg active_epoch_valid;reg[15:0]active_service_epoch;
 wire tuple_ok=grant_token_q==active[35:18]&&grant_position_q==active[17:0]&&grant_generation_q==active[37:36]&&
  grant_tag_q=={grant_epoch_q,6'd0,active[35:18],active[12:0],6'd0};
 wire allocated_match=allocated_token_q==job_token&&allocated_position_q==job_position&&allocated_generation_q==job_generation;
 reg busy;reg[3:0]dst;reg[181:0]active;
 reg[92:0]last_tk;reg[9:0]last_kst;reg[1:0]last_boot;reg sent_once;
 // HKV-PROMPT6: registered queue head (== q[rp] whenever count != 0) + its wide zero tests (hz)
 reg[511:0]h;reg[5:0]hz;reg[5:0]qz[0:3];
 wire[1:0]rp_n=take?rp+2'd1:rp;wire q_wr=rv&&count<4;
 wire[5:0]rz={rd[511:263]==0,rd[511:230]==0,rd[511:170]==0,rd[511:153]==0,rd[511:65]==0,rd[511:64]==0};
`ifdef QKD_HR_PEPD_MUTANT
 wire h_fwd=1'b0;
`else
 wire h_fwd=q_wr&&wp==rp_n;
`endif
 always @(posedge ck)begin if(q_wr)qz[wp]<=rz;h<=h_fwd?rd:q[rp_n];hz<=h_fwd?rz:qz[rp_n];end
 // r6 (1): data-only head flags, computed at queue write and registered with the head (same forwarding as h / hz)
 wire[15:0]rf={rd[86]&&rd[246]&&rd[65:61]==0&&rd[83:66]<18'd151936,rd[47:32]==0,
  (rd[15:8]==1||((ENABLE_SERVICE||ENABLE_TOKEN)&&rd[15:8]==2))&&rd[23:19]==0,rd[7:0]==8'h21,rd[7:0]==8'h22,rd[7:0]==8'h23,
  rd[15:8]==1,rd[15:8]==2,8'd1<<rd[18:16]};
 reg[15:0]hf;reg[15:0]qf[0:3];
 always @(posedge ck)begin if(q_wr)qf[wp]<=rf;hf<=h_fwd?rf:qf[rp_n];end
 wire[7:0]src_oh=hf[7:0];wire f_v2=hf[8],f_v1=hf[9],f_t23=hf[10],f_t22=hf[11],f_t21=hf[12],f_hdrs=hf[13],f_rs0=hf[14],f_tok22=hf[15];
 wire[7:0]role_oh=8'd1<<role;
wire[2:0]src=h[18:16];wire[7:0]target=h[31:24];
 wire[15:0]rs=h[47:32];wire hdr=f_hdrs&&target==role_oh;
 wire take=count!=0&&!fault;
 // r6 (2): per-source compares in parallel, selected by the one-hot source
 reg[7:0]seq_okk;
 always @*for(integer k=0;k<8;k=k+1)seq_okk[k]=seq_seen[k]?rs==seqp1[k*16+:16]:f_rs0;
 wire sequence_ok=|(src_oh&seq_okk);
 wire stale_service=ENABLE_SERVICE&&f_t21&&f_v2&&role==0&&!src_oh[0]&&hz[3]&&(h[169:154]!=epoch||(!epoch_active&&!startup_q));
 wire send=!fault&&credits!=0&&!tx_v;
 wire load_begin=ENABLE_SERVICE&&role==0&&!busy&&!begin_busy&&!permit_busy&&cn==0&&!cv&&begin_pending&&!fault;
 wire load_permit=ENABLE_TOKEN&&ENABLE_SERVICE&&role==0&&!busy&&!begin_busy&&!permit_busy&&!load_begin&&permit_pending&&!fault;
 wire load_cmd=(role==0)&&!busy&&!begin_busy&&!permit_busy&&!load_begin&&!load_permit&&cn!=0&&!fault;
 // r6 (3): sc_q == status_changed, one edge ahead (next-edge lt/lk/lb/lready/lepoch = the inputs; last_* = fire?l*:last_*)
 reg sc_q;
 wire status_changed=sc_q;
 wire st_fire=send&&role!=0&&sc_q;
 wire st_dh=local_tk[92:32]!=last_tk[92:32]||local_boot!=last_boot||local_kst!=last_kst||
  (ENABLE_SERVICE&&(local_service_ready!=last_ready||local_service_epoch!=last_epoch));
 wire st_df=local_tk[92:32]!=lt[92:32]||local_boot!=lb||local_kst!=lk||(ENABLE_SERVICE&&(local_service_ready!=lready||local_service_epoch!=lepoch));
`ifdef QKD_HR_PEPD2_MUTANT
 // mutant: the change test from the current values instead of the next-edge values (status seen one edge late)
 wire sc_n=!(sent_once||st_fire)||lt[92:32]!=last_tk[92:32]||lb!=last_boot||lk!=last_kst||(ENABLE_SERVICE&&(lready!=last_ready||lepoch!=last_epoch));
`else
 wire sc_n=!(sent_once||st_fire)||(st_fire?st_df:st_dh);
`endif
 // r6 (4): delayed output arrays: registered one-hot enables (KEPT copies) + data, applied on the next edge
 (* keep *) reg[31:0]dl_src_c;   // [c*8+k]: copy c of the source-k RX 0x21 write (c 0..2: tk8 thirds, 3: kst8/boot8/seen/se8)
 (* keep *) reg[31:0]dl_role_c;  // [c*8+k]: copy c of the role-k local write (every edge after reset)
 (* keep *) reg[3:0]dl_se_lo_c,dl_se_hi_c;  // service_epoch8 clears (begin accept before / 0x23 begin after the RX write), 2 slots a copy
 reg[7:0]dl_ser;                 // service_epoch8[role]<=lepoch (16 loads a bit)
 reg[92:0]dl_htk,dl_lt;reg[9:0]dl_hk,dl_lk;reg[1:0]dl_hb,dl_lb;reg[15:0]dl_hep,dl_lep;
 always @(posedge ck)begin
  dl_htk<=(MUT==1&&src==7)?h[140:48]^(93'd1<<64):h[140:48];dl_hk<=h[150:141];dl_hb<=h[152:151];dl_hep<=h[169:154];
  dl_lt<=lt;dl_lk<=lk;dl_lb<=lb;dl_lep<=lepoch;
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin tk8<=0;kst8<=0;boot8<=0;seen<=0;service_epoch8<=0;end
  else for(integer k=0;k<8;k=k+1)begin
   if(dl_src_c[k])tk8[k*93+:31]<=dl_htk[30:0];else if(dl_role_c[k])tk8[k*93+:31]<=dl_lt[30:0];
   if(dl_src_c[8+k])tk8[k*93+31+:31]<=dl_htk[61:31];else if(dl_role_c[8+k])tk8[k*93+31+:31]<=dl_lt[61:31];
   if(dl_src_c[16+k])tk8[k*93+62+:31]<=dl_htk[92:62];else if(dl_role_c[16+k])tk8[k*93+62+:31]<=dl_lt[92:62];
   if(dl_src_c[24+k])begin kst8[k*10+:10]<=dl_hk;boot8[k*2+:2]<=dl_hb;end
   else if(dl_role_c[24+k])begin kst8[k*10+:10]<=dl_lk;boot8[k*2+:2]<=dl_lb;end
   if(dl_src_c[24+k]||dl_role_c[24+k])seen[k]<=1'b1;
   if(dl_se_hi_c[k/2])service_epoch8[k*16+:16]<=16'd0;
   else if(ENABLE_SERVICE&&dl_src_c[24+k])service_epoch8[k*16+:16]<=dl_hep;
   else if(dl_se_lo_c[k/2])service_epoch8[k*16+:16]<=16'd0;
   else if(dl_ser[k])service_epoch8[k*16+:16]<=dl_lep;
  end
 end
 always @(posedge ck)begin
  rd<=rx_d;cd<=cmd_hc;
  if(rv&&count<4)q[wp]<=rd;
  if(cv&&cn<4)cq[cw]<=cd;
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   role_valid<=0;die_sampled<=0;die_capture<=0;did_q<=3'(DIE);rv<=0;tc<=0;cv<=0;lt<=0;lk<=0;lb<=0;wp<=0;rp<=0;count<=0;cw<=0;cr<=0;cn<=0;
   credits<=4;seq_tx<=0;seqp1<={8{16'd1}};seq_seen<=0;sc_q<=1'b1;dl_src_c<=0;dl_role_c<=0;dl_se_lo_c<=0;dl_se_hi_c<=0;dl_ser<=0;busy<=0;dst<=1;active<=0;
   last_tk<=0;last_kst<=0;last_boot<=0;sent_once<=0;rx_cr<=0;cmd_cr<=0;tx_v<=0;tx_d<=0;
   lready<=0;startup_q<=0;lepoch<=0;biv<=0;bepoch<=0;epoch<=0;last_epoch<=0;last_ready<=0;
   begin_pending<=0;begin_busy<=0;epoch_active<=0;permit_pending<=0;permit_busy<=0;permit_sent<=0;peer_permit<=0;begin_cr<=0;begin_available<=ENABLE_SERVICE;
   service_begin_v<=0;service_begin_epoch<=0;pending_advertised<=0;pending_epoch<=0;
   service_ready8<=0;pending_ack8<=0;ingest_permission<=0;
   allocator_fault_q<=0;local_emitted<=0;allocator_sampled<=0;wrap_vq<=0;wrap_dq<=0;wrap_rq<=0;wrap_tq<=0;abort_q<=0;abort_seen<=0;request_ready_q<=0;grant_valid_q<=0;grant_low<=0;allocated_vq<=0;allocated_dq<=0;terminal_ack_q<=0;
   drain_q<=0;grant_epoch_q<=0;allocated_epoch_q<=0;grant_token_q<=0;grant_position_q<=0;allocated_token_q<=0;allocated_position_q<=0;
   grant_generation_q<=0;allocated_generation_q<=0;grant_tag_q<=0;grant_wait<=0;request_accepted<=0;cancel_consumed<=0;
   active_epoch<=0;active_service_epoch<=0;active_epoch_valid<=0;token_request_valid<=0;token_request_token<=0;token_request_position<=0;token_request_generation<=0;
   token_grant_ready<=0;token_epoch_valid<=0;token_epoch<=0;cancel_valid<=0;cancel_tag<=0;cancel_generation<=0;cancel_done<=0;cancel_fault<=0;cancel_drained<=0;
   hc<=0;fault<=0;
  end else begin
   sc_q<=sc_n;dl_src_c<=0;dl_se_lo_c<=0;dl_se_hi_c<=0;dl_ser<=0;dl_role_c<={4{role_oh}};
   allocator_fault_q<=token_allocator_fault;if(ENABLE_TOKEN&&allocator_fault_q&&MUT!=17)fault<=1;allocator_sampled<=1;wrap_vq<=token_wrap_fence_valid;wrap_dq<=token_wrap_drained;wrap_rq<=token_wrap_link_reset_seen;wrap_tq<=token_wrap_retraining_done;
   if(ENABLE_TOKEN&&wrap_vq&&!(wrap_dq&&wrap_rq&&wrap_tq))fault<=1;
   if(ENABLE_TOKEN&&wrap_vq&&wrap_dq&&wrap_rq&&wrap_tq)begin
    if(cancel_valid||retained_request||allocated_vq)fault<=1;
    else begin fault<=0;abort_seen<=0;abort_q<=0;cancel_consumed<=0;active_epoch_valid<=0;end
   end
   abort_q<=package_abort;drain_q<=abort_drained;request_ready_q<=token_request_ready;
   grant_valid_q<=token_grant_valid;grant_epoch_q<=token_grant_epoch;grant_token_q<=token_grant_token;
   grant_position_q<=token_grant_position;grant_generation_q<=token_grant_generation;grant_tag_q<=token_grant_tag;
   allocated_vq<=allocated_valid;allocated_dq<=allocated_delivered;allocated_epoch_q<=allocated_epoch;
   allocated_token_q<=allocated_token;allocated_position_q<=allocated_position;allocated_generation_q<=allocated_generation;terminal_ack_q<=terminal_accepted;
   token_grant_ready<=0;token_epoch_valid<=0;
   startup_q<=startup_allowed;lready<=local_service_ready;lepoch<=local_service_epoch;biv<=begin_v;bepoch<=begin_epoch;
   begin_cr<=0;service_begin_v<=0;pending_advertised<=0;
   if(MUT==6&&role==0&&pending_ack8[7])service_ready8[7]<=1;
   begin_available<=ENABLE_SERVICE&&role==0&&!busy&&cn==0&&!cv&&!(ENABLE_TOKEN&&(abort_seen||abort_q||reset_abort_seen))&&!begin_pending&&!begin_busy&&!permit_pending&&!permit_busy&&(!epoch_active||(&service_ready8));
   ingest_permission<=ENABLE_SERVICE&&epoch_active&&!fault&&(!ENABLE_TOKEN?(&pending_ack8):(role==0?(&pending_ack8):(pending_ack8[role]&&(peer_permit||MUT==21))));
   if(ENABLE_TOKEN&&ENABLE_SERVICE&&role==0&&epoch_active&&(&pending_ack8)&&!permit_sent&&!permit_busy&&!begin_pending&&!begin_busy)permit_pending<=1;
   if(ENABLE_SERVICE&&lepoch==epoch)begin
    dl_ser<=role_oh; 
    if(!lready)begin
     service_ready8[role]<=0;
     if(epoch_active&&role==0&&!pending_ack8[0])begin pending_ack8[0]<=1;pending_advertised<=1;pending_epoch<=epoch;end
    end else if((!epoch_active&&startup_q)||pending_ack8[role])service_ready8[role]<=1;
   end
   if(biv&&ENABLE_SERVICE)begin
    if(role!=0||!begin_available||busy||cn!=0||cv||begin_pending||begin_busy||(epoch_active&&!(&service_ready8))||bepoch<=epoch)fault<=1;
    else begin begin_pending<=1;epoch<=bepoch;epoch_active<=1;
     service_ready8<=0;pending_ack8<=0;dl_se_lo_c<=4'hf;ingest_permission<=0;permit_pending<=0;permit_sent<=0;peer_permit<=0;
     service_begin_v<=1;service_begin_epoch<=bepoch;
    end
   end
   if(load_begin)begin begin_pending<=0;begin_busy<=1;dst<=1;end
   if(load_permit)begin permit_pending<=0;permit_busy<=1;dst<=1;end
   die_capture<=die_id;die_sampled<=1;if(!role_valid&&die_sampled)begin did_q<=die_capture;role_valid<=1;end
   if(role_valid&&STRAPPED&&die_capture!=did_q)fault<=1;rv<=rx_v;tc<=tx_cr;cv<=cmd_v;lt<=local_tk;lk<=local_kst;lb<=local_boot;rx_cr<=take;cmd_cr<=0;tx_v<=0;
   // Pulse fields must be cleared each edge; token/generation/write data persist.
   hc[38]<=0;hc[113]<=0;hc[181]<=0;
   // r6 (4): role-slot tk8/kst8/boot8/seen writes are the dl_role_c copies set every edge above
   if(tc)begin if(credits==4)fault<=1;else credits<=credits+1'b1;end
   if(rv&&!fault)begin if(count==4)fault<=1;else wp<=wp+1'b1;end
   if(take)rp<=rp+1'b1;
   case({rv&&!fault&&count<4,take})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
   if(cv&&!fault)begin if(role!=0||cn==4)fault<=1;else cw<=cw+1'b1;end
   if(!grant_valid_q)grant_low<=1;
   if(ENABLE_TOKEN&&abort_q)abort_seen<=1;
   if(token_request_valid&&request_ready_q)begin token_request_valid<=0;request_accepted<=1;end
   if(ENABLE_TOKEN&&grant_wait&&request_accepted&&grant_valid_q&&grant_low&&!fault&&(MUT==12||!(abort_seen||abort_q||reset_abort_seen)))begin
    if(MUT!=10&&(!tuple_ok||!allocated_vq||allocated_dq||!allocated_match||allocated_epoch_q!=grant_epoch_q))fault<=1;
    else begin token_grant_ready<=1;grant_wait<=0;active_epoch<=grant_epoch_q;active_epoch_valid<=1;
     hc<=active;local_emitted<=1;token_epoch_valid<=MUT!=14;token_epoch<=grant_epoch_q;
    end
   end
   // The central allocator owns an accepted identity even when warm readiness
   // suppresses grant_valid. Cancel that exact retained allocation only after
   // all four genuine drain observations, never a synthesized done.
   if(ENABLE_TOKEN&&(abort_seen||abort_q||reset_abort_seen)&&retained_request&&allocated_vq&&!cancel_consumed)begin
    if(!allocated_match)fault<=1;
    else if((MUT==13||&drain_q)&&!cancel_valid)begin
     cancel_valid<=1;cancel_tag<={allocated_epoch_q,6'd37,allocated_token_q,allocated_position_q[12:0],6'd0};
     cancel_generation<=allocated_generation_q;cancel_done<=0;cancel_fault<=1;cancel_drained<=drain_q;
    end
   end
   if(cancel_valid)cancel_drained<=drain_q;
   if(cancel_valid&&terminal_ack_q)begin cancel_valid<=0;cancel_consumed<=1;end
   // Abort separates the retained cancel identity from real queued metadata.
   // Recipients already sent the whole event are not sent it twice. Remaining
   // copies and an as-yet undelivered local event retain PW/DW with START low.
   if(ENABLE_TOKEN&&(abort_seen||abort_q||reset_abort_seen)&&busy&&active[38]&&MUT!=12)begin
    active[38]<=0;active_epoch_valid<=0;grant_wait<=0;
    if(active[113]||active[181])begin
     if(!local_emitted)begin hc<=active;hc[38]<=0;if(MUT==18)begin hc[113]<=0;hc[181]<=0;end local_emitted<=1;end
    end else begin busy<=0;cmd_cr<=1;end
   end
   if(load_cmd)begin
    active<=cq[cr];active_service_epoch<=ENABLE_SERVICE?epoch:16'd0;local_emitted<=0;busy<=1;dst<=1;cr<=cr+1'b1;
    active_epoch_valid<=0;
    if(ENABLE_TOKEN&&cq[cr][38])begin
     if(abort_seen||abort_q||reset_abort_seen)begin
      active<=cq[cr]&~(182'd1<<38);hc<=cq[cr]&~(182'd1<<38);local_emitted<=1;grant_wait<=0;
      if(!cq[cr][113]&&!cq[cr][181])begin busy<=0;cmd_cr<=1;end
     end else begin
      request_accepted<=0;cancel_consumed<=0;
      if(cq[cr][17:13]!=0||cq[cr][35:18]>=18'd151936)fault<=1;
      else begin grant_wait<=1;token_request_valid<=1;token_request_token<=cq[cr][35:18];
       token_request_position<=cq[cr][17:0];token_request_generation<=cq[cr][37:36];end
     end
    end else begin hc<=cq[cr];local_emitted<=1;grant_wait<=0;end
   end
   case({cv&&!fault&&role==0&&cn<4,load_cmd})2'b10:cn<=cn+1'b1;2'b01:cn<=cn-1'b1;default:;endcase
   if(take)begin
    if(!hdr)fault<=1;
    else if(stale_service&&MUT!=3)begin
     // An in-order old warm snapshot still advances the unchanged source
     // sequence. A reset-era stale replay with an unrelated sequence is
     // ignored, never used to update TK/KST/BOOT/service readiness.
     if(sequence_ok&&(epoch_active||h[169:154]==epoch))begin seq_seen[src]<=1;begin for(integer kq_seq_rx=0;kq_seq_rx<8;kq_seq_rx=kq_seq_rx+1)if(src_oh[kq_seq_rx])seqp1[kq_seq_rx*16+:16]<=rs+16'd1; end end
    end else if(MUT!=5&&!sequence_ok)fault<=1;
    else if(f_t21&&role==0&&!src_oh[0]&&
      ((!ENABLE_SERVICE&&f_v1&&hz[2])||(ENABLE_SERVICE&&f_v2&&hz[3])))begin
     if(!ENABLE_SERVICE||MUT==3||h[169:154]==epoch)begin
     dl_src_c<={4{src_oh}};  // r6 (4): tk8/kst8/boot8/seen/service_epoch8[src] on the next edge (dl_h* data)
     if(ENABLE_SERVICE)begin
      if((MUT==3||h[169:154]==epoch))begin
       if(!h[153])begin if(epoch_active)pending_ack8[src]<=1;service_ready8[src]<=0;end
       else if((!epoch_active&&startup_q)||pending_ack8[src])service_ready8[src]<=1;
      end
     end
     end seq_seen[src]<=1;begin for(integer kq_seq_rx=0;kq_seq_rx<8;kq_seq_rx=kq_seq_rx+1)if(src_oh[kq_seq_rx])seqp1[kq_seq_rx*16+:16]<=rs+16'd1; end 
    end else if(ENABLE_SERVICE&&f_t23&&f_v2&&role!=0&&src_oh[0]&&
      ((!ENABLE_TOKEN&&hz[0])||(ENABLE_TOKEN&&hz[1])))begin
     if(ENABLE_TOKEN&&h[64])begin
      if(MUT!=22&&(!epoch_active||h[63:48]!=epoch||lepoch!=epoch||!pending_ack8[role]||peer_permit))fault<=1;
      else begin peer_permit<=1;seq_seen[src]<=1;begin for(integer kq_seq_rx=0;kq_seq_rx<8;kq_seq_rx=kq_seq_rx+1)if(src_oh[kq_seq_rx])seqp1[kq_seq_rx*16+:16]<=rs+16'd1; end end
     end else if(h[63:48]<=epoch)fault<=1;
     else begin epoch<=h[63:48];epoch_active<=1;service_ready8<=0;pending_ack8<=0;dl_se_hi_c<=4'hf;peer_permit<=0;
      service_begin_v<=1;service_begin_epoch<=h[63:48];
      seq_seen[src]<=1;begin for(integer kq_seq_rx=0;kq_seq_rx<8;kq_seq_rx=kq_seq_rx+1)if(src_oh[kq_seq_rx])seqp1[kq_seq_rx*16+:16]<=rs+16'd1; end 
     end
    end else if(f_t22&&role!=0&&src_oh[0]&&
      ((!ENABLE_TOKEN&&f_v1&&hz[4])||
       (ENABLE_TOKEN&&((!h[86]&&f_v1&&hz[4])||
        (f_v2&&f_tok22&&hz[5])))))begin
     if(ENABLE_TOKEN&&h[86]&&((abort_seen||abort_q||reset_abort_seen)||!peer_epoch_fresh||!peer_service_fresh))fault<=1;
     else begin hc<=h[229:48];token_epoch_valid<=ENABLE_TOKEN&&h[246];token_epoch<=h[245:230];end
     seq_seen[src]<=1;begin for(integer kq_seq_rx=0;kq_seq_rx<8;kq_seq_rx=kq_seq_rx+1)if(src_oh[kq_seq_rx])seqp1[kq_seq_rx*16+:16]<=rs+16'd1; end 
    end else fault<=1;
   end
   if(send)begin
    if(role==0&&begin_busy)begin
     tx_v<=1;tx_d<=512'h0223|((512'd1<<dst)<<24)|(512'(seq_tx)<<32)|(512'(epoch)<<48);
     credits<=credits+8'(tc)-1'b1;
     if(dst==7)begin begin_busy<=0;begin_cr<=1;seq_tx<=seq_tx+1'b1;end else dst<=dst+1'b1;
    end else if(role==0&&permit_busy)begin
     tx_v<=1;tx_d<=512'h0223|((512'd1<<dst)<<24)|(512'(seq_tx)<<32)|(512'(epoch)<<48)|(512'd1<<64);
     credits<=credits+8'(tc)-1'b1;
     if(dst==7)begin permit_busy<=0;permit_sent<=1;seq_tx<=seq_tx+1'b1;end else dst<=dst+1'b1;
    end else if(role==0&&busy&&!grant_wait&&!(ENABLE_TOKEN&&(abort_seen||abort_q||reset_abort_seen)&&active[38]))begin
     tx_v<=1;tx_d<=(ENABLE_TOKEN&&active_epoch_valid?512'h0222:512'h0122)|((512'd1<<dst)<<24)|(512'(seq_tx)<<32)|(512'(active)<<48)|
      (ENABLE_TOKEN&&active_epoch_valid?((512'(active_epoch^(MUT==15?16'd1:16'd0))<<230)|(512'd1<<246)|(512'(active_service_epoch)<<247)):512'd0);
     credits<=credits+8'(tc)-1'b1;
     // Each recipient sees consecutive command sequence numbers, not the
     // sequence of all seven copies. Increment once per broadcast.
     if(dst==7)begin busy<=0;cmd_cr<=1;seq_tx<=seq_tx+1'b1;end else dst<=dst+1'b1;
    end else if(role!=0&&status_changed)begin
     tx_v<=1;tx_d<=(ENABLE_SERVICE?512'h01000221:512'h01000121)|(512'(role)<<16)|(512'(seq_tx)<<32)|(512'(lt)<<48)|(512'(lk)<<141)|(512'(lb)<<151)|(ENABLE_SERVICE?((512'(lready)<<153)|(512'(lepoch)<<154)):512'b0);
     credits<=credits+8'(tc)-1'b1;seq_tx<=seq_tx+1'b1;last_tk<=lt;last_kst<=lk;last_boot<=lb;sent_once<=1;last_ready<=lready;last_epoch<=lepoch;
     if(ENABLE_SERVICE&&epoch_active&&lepoch==epoch&&!lready)begin
      pending_advertised<=1;pending_epoch<=epoch;pending_ack8[role]<=1;
     end
    end
   end
  end
 end
endmodule
