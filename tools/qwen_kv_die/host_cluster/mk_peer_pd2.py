# KV-HOST/PEER r6 (10-19) generator, committed by KV-HOST4; run from anywhere: writes into the repository root of this file.
import sys,re
import os; W=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..')+'/'
src=open(W+'rtl/qwen_sys/host_cluster_20261017/peer_pd/qkd_host_ctrl_token_service_packet_collected_pd.sv').read()
def sub(old,new,count=1):
    global src
    n=src.count(old)
    assert n==count,(n,old[:80])
    src=src.replace(old,new)
hdr_old=src[:src.index('`timescale')]
src=src[len(hdr_old):]
HDR='''// KV-HOST/PEER r6 (10-19): qkd_host_ctrl_token_service_packet_collected_pd2 = the _pd fork (registered queue head h + zero
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
'''
src=HDR+src
sub('module qkd_host_ctrl_token_service_packet_collected_pd #','module qkd_host_ctrl_token_service_packet_collected_pd2 #')
sub('reg[7:0]credits;reg[15:0]seq_tx;reg[127:0]seq_rx;reg[7:0]seq_seen;','reg[7:0]credits;reg[15:0]seq_tx;reg[127:0]seqp1;reg[7:0]seq_seen;')
# peer token frame / accept use flags
sub("wire peer_token_frame=ENABLE_TOKEN&&role!=0&&src==0&&h[7:0]==8'h22&&h[15:8]==2&&h[86]&&h[246]&&hz[5]&&h[65:61]==0&&h[83:66]<18'd151936;",
    "wire peer_token_frame=ENABLE_TOKEN&&role!=0&&src_oh[0]&&f_t22&&f_v2&&f_tok22&&hz[5];")
# flags storage
sub("always @(posedge ck)begin if(q_wr)qz[wp]<=rz;h<=h_fwd?rd:q[rp_n];hz<=h_fwd?rz:qz[rp_n];end",
"""always @(posedge ck)begin if(q_wr)qz[wp]<=rz;h<=h_fwd?rd:q[rp_n];hz<=h_fwd?rz:qz[rp_n];end
 // r6 (1): data-only head flags, computed at queue write and registered with the head (same forwarding as h / hz)
 wire[15:0]rf={rd[86]&&rd[246]&&rd[65:61]==0&&rd[83:66]<18'd151936,rd[47:32]==0,
  (rd[15:8]==1||((ENABLE_SERVICE||ENABLE_TOKEN)&&rd[15:8]==2))&&rd[23:19]==0,rd[7:0]==8'h21,rd[7:0]==8'h22,rd[7:0]==8'h23,
  rd[15:8]==1,rd[15:8]==2,8'd1<<rd[18:16]};
 reg[15:0]hf;reg[15:0]qf[0:3];
 always @(posedge ck)begin if(q_wr)qf[wp]<=rf;hf<=h_fwd?rf:qf[rp_n];end
 wire[7:0]src_oh=hf[7:0];wire f_v2=hf[8],f_v1=hf[9],f_t23=hf[10],f_t22=hf[11],f_t21=hf[12],f_hdrs=hf[13],f_rs0=hf[14],f_tok22=hf[15];
 wire[7:0]role_oh=8'd1<<role;""")
sub("wire hdr=(h[15:8]==1||((ENABLE_SERVICE||ENABLE_TOKEN)&&h[15:8]==2))&&h[23:19]==0&&target==(8'd1<<role);",
    "wire hdr=f_hdrs&&target==role_oh;")
sub("wire sequence_ok=(!seq_seen[src]&&rs==0)||(seq_seen[src]&&rs==seq_rx[src*16+:16]+16'd1);",
"""// r6 (2): per-source compares in parallel, selected by the one-hot source
 reg[7:0]seq_okk;
 always @*for(integer k=0;k<8;k=k+1)seq_okk[k]=seq_seen[k]?rs==seqp1[k*16+:16]:f_rs0;
 wire sequence_ok=|(src_oh&seq_okk);""")
sub("wire stale_service=ENABLE_SERVICE&&h[7:0]==8'h21&&h[15:8]==2&&role==0&&src!=0&&hz[3]&&",
    "wire stale_service=ENABLE_SERVICE&&f_t21&&f_v2&&role==0&&!src_oh[0]&&hz[3]&&")
sub("wire status_changed=!sent_once||lt[92:32]!=last_tk[92:32]||lb!=last_boot||lk!=last_kst||(ENABLE_SERVICE&&(lready!=last_ready||lepoch!=last_epoch));",
"""// r6 (3): sc_q == status_changed, one edge ahead (next-edge lt/lk/lb/lready/lepoch = the inputs; last_* = fire?l*:last_*)
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
 end""")
# reset values
sub("credits<=4;seq_tx<=0;seq_rx<=0;seq_seen<=0;","credits<=4;seq_tx<=0;seqp1<={8{16'd1}};seq_seen<=0;sc_q<=1'b1;dl_src_c<=0;dl_role_c<=0;dl_se_lo_c<=0;dl_se_hi_c<=0;dl_ser<=0;")
sub("hc<=0;tk8<=0;kst8<=0;boot8<=0;seen<=0;fault<=0;","hc<=0;fault<=0;")
sub("service_ready8<=0;pending_ack8<=0;service_epoch8<=0;ingest_permission<=0;\n   allocator_fault_q","service_ready8<=0;pending_ack8<=0;ingest_permission<=0;\n   allocator_fault_q")
# per-edge defaults: insert at start of else branch
sub("  end else begin\n   allocator_fault_q<=token_allocator_fault;",
    "  end else begin\n   sc_q<=sc_n;dl_src_c<=0;dl_se_lo_c<=0;dl_se_hi_c<=0;dl_ser<=0;dl_role_c<={4{role_oh}};\n   allocator_fault_q<=token_allocator_fault;")
# role service epoch write
sub("begin for(integer kq_service_epoch8=0;kq_service_epoch8<8;kq_service_epoch8=kq_service_epoch8+1)if(role==3'(kq_service_epoch8))service_epoch8[kq_service_epoch8*16+:16]<=lepoch; end ",
    "dl_ser<=role_oh; ")
# biv clear
sub("service_ready8<=0;pending_ack8<=0;service_epoch8<=0;ingest_permission<=0;permit_pending<=0;",
    "service_ready8<=0;pending_ack8<=0;dl_se_lo_c<=4'hf;ingest_permission<=0;permit_pending<=0;")
# role tk8/kst8/boot8/seen writes
sub("begin for(integer kq_tk8=0;kq_tk8<8;kq_tk8=kq_tk8+1)if(role==3'(kq_tk8))tk8[kq_tk8*93+:93]<=lt; end begin for(integer kq_kst8=0;kq_kst8<8;kq_kst8=kq_kst8+1)if(role==3'(kq_kst8))kst8[kq_kst8*10+:10]<=lk; end begin for(integer kq_boot8=0;kq_boot8<8;kq_boot8=kq_boot8+1)if(role==3'(kq_boot8))boot8[kq_boot8*2+:2]<=lb; end seen[role]<=1;",
    "// r6 (4): role-slot tk8/kst8/boot8/seen writes are the dl_role_c copies set every edge above")
# RX seq writes (stale, permit, begin, 0x22, 0x21)
old_seq="begin for(integer kq_seq_rx=0;kq_seq_rx<8;kq_seq_rx=kq_seq_rx+1)if(src==3'(kq_seq_rx))seq_rx[kq_seq_rx*16+:16]<=rs; end"
n=src.count(old_seq); assert n==5,n
src=src.replace(old_seq,"begin for(integer kq_seq_rx=0;kq_seq_rx<8;kq_seq_rx=kq_seq_rx+1)if(src_oh[kq_seq_rx])seqp1[kq_seq_rx*16+:16]<=rs+16'd1; end")
# 0x21 branch
sub("""    else if(h[7:0]==8'h21&&role==0&&src!=0&&
      ((!ENABLE_SERVICE&&h[15:8]==1&&hz[2])||(ENABLE_SERVICE&&h[15:8]==2&&hz[3])))begin""",
"""    else if(f_t21&&role==0&&!src_oh[0]&&
      ((!ENABLE_SERVICE&&f_v1&&hz[2])||(ENABLE_SERVICE&&f_v2&&hz[3])))begin""")
sub("""     begin for(integer kq_tk8=0;kq_tk8<8;kq_tk8=kq_tk8+1)if(src==3'(kq_tk8))tk8[kq_tk8*93+:93]<=(MUT==1&&src==7)?h[140:48]^(93'd1<<64):h[140:48]; end 
     begin for(integer kq_kst8=0;kq_kst8<8;kq_kst8=kq_kst8+1)if(src==3'(kq_kst8))kst8[kq_kst8*10+:10]<=h[150:141]; end begin for(integer kq_boot8=0;kq_boot8<8;kq_boot8=kq_boot8+1)if(src==3'(kq_boot8))boot8[kq_boot8*2+:2]<=h[152:151]; end seen[src]<=1;
     if(ENABLE_SERVICE)begin
      begin for(integer kq_service_epoch8=0;kq_service_epoch8<8;kq_service_epoch8=kq_service_epoch8+1)if(src==3'(kq_service_epoch8))service_epoch8[kq_service_epoch8*16+:16]<=h[169:154]; end 
""",
"""     dl_src_c<={4{src_oh}};  // r6 (4): tk8/kst8/boot8/seen/service_epoch8[src] on the next edge (dl_h* data)
     if(ENABLE_SERVICE)begin
""")
# 0x23 branch
sub("""    end else if(ENABLE_SERVICE&&h[7:0]==8'h23&&h[15:8]==2&&role!=0&&src==0&&""",
    """    end else if(ENABLE_SERVICE&&f_t23&&f_v2&&role!=0&&src_oh[0]&&""")
sub("else begin epoch<=h[63:48];epoch_active<=1;service_ready8<=0;pending_ack8<=0;service_epoch8<=0;peer_permit<=0;",
    "else begin epoch<=h[63:48];epoch_active<=1;service_ready8<=0;pending_ack8<=0;dl_se_hi_c<=4'hf;peer_permit<=0;")
# 0x22 branch
sub("""    end else if(h[7:0]==8'h22&&role!=0&&src==0&&
      ((!ENABLE_TOKEN&&h[15:8]==1&&hz[4])||
       (ENABLE_TOKEN&&((!h[86]&&h[15:8]==1&&hz[4])||
        (h[86]&&h[15:8]==2&&h[246]&&hz[5]&&h[65:61]==0&&h[83:66]<18'd151936)))))begin""",
"""    end else if(f_t22&&role!=0&&src_oh[0]&&
      ((!ENABLE_TOKEN&&f_v1&&hz[4])||
       (ENABLE_TOKEN&&((!h[86]&&f_v1&&hz[4])||
        (f_v2&&f_tok22&&hz[5])))))begin""")
import re as _r; left=[m.start() for m in _r.finditer(r"(?<![a-z_])seq_rx\[",src[len(HDR):])]; assert not left,left
for w in ['tk8[','kst8[','boot8[','seen[','service_epoch8[']:
    pass
open(W+'rtl/qwen_sys/host_cluster_20261017/peer_pd/qkd_host_ctrl_token_service_packet_collected_pd2.sv','w').write(src)
print('ok')
