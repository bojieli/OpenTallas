`timescale 1ns/1ps
// QE3-HROOT-PEER2 10-21: cycle equivalence of the RX pre-decode codec (host_peer_mu_sram_1021pl) against the KV-PEER12
// codec (host_peer_mu_sram_1020, renamed qkd_host_peer_coordinator_codec_pd_mu_old) behind a one-word register slice on
// rx (slice valid = rx_valid & rx_ready, consumed by the old codec as rx_valid & rx_ready = v & !fault).  Every output
// of both is compared every edge.  Stimulus is reactive: words carry the correct header and (mostly) the expected
// sequence number; tags come from a small per-user pool shared with allocated_* and terminal_* so the al/term identity
// compares hit and the same-edge table writes coincide with requests.  Periodic random reset.
module tb_codec_equiv;
 reg ck=0;always #1 ck=~ck;
 reg por_n=0;
 reg[7:0]rx_valid=0;reg[4095:0]rx_data=0;reg[7:0]tx_ready=0;
 reg allocated_valid=0,allocated_delivered=0;reg[58:0]allocated_tag=0;reg[1:0]allocated_gen=0;reg[17:0]allocated_position=0;
 reg[7:0]participant_accepted=0,cancel_accepted=0;
 reg result_v=0;reg[58:0]result_tag=0;reg[1:0]result_gen=0;reg result_done=0,result_fault=0;reg[3:0]result_cause=0;reg[17:0]result_token=0;reg[31:0]result_value=0,result_cycles=0;
 reg terminal_accepted=0;reg[58:0]terminal_tag=0;reg[1:0]terminal_gen=0;reg post_retired=0;
 reg link_reset_request=0,retraining_request=0;
 // slice in front of the old codec
 wire[7:0]rx_ready_o,rx_ready_n;reg[7:0]sv;reg[4095:0]sd;
 always @(posedge ck or negedge por_n) if(!por_n)sv<=0;else sv<=rx_valid&rx_ready_o;
 always @(posedge ck) sd<=rx_data;
`define OUTS(p) wire[7:0]p``tx_valid;wire[4095:0]p``tx_data;wire[7:0]p``pv,p``cv,p``cd,p``cf,p``sr,p``nr,p``kv,p``vm,p``co,p``ho,p``cx,p``ld,p``lr,p``rt,p``pr,p``tr,p``cerv;\
 wire[471:0]p``pt,p``ct;wire[15:0]p``pg,p``cg;wire[255:0]p``ptr,p``cpf;wire[143:0]p``ptk,p``pps;wire[127:0]p``se,p``ce,p``pe;wire[511:0]p``pd;\
 wire p``rcr,p``rti,p``siv,p``srv,p``src,p``cqv,p``flt;wire[15:0]p``sct,p``srct,p``cqct;wire[7:0]p``ss,p``srs,p``cqs;wire[17:0]p``sp,p``srp,p``srt,p``cqp,p``cqt;wire[527:0]p``cer;
 `OUTS(o_)
 `OUTS(n_)
`define CONN(p,rv,rd,rr) (.ck(ck),.por_n(por_n),.rx_valid(rv),.rx_data(rd),.rx_ready(rr),.tx_valid(p``tx_valid),.tx_data(p``tx_data),.tx_ready(tx_ready),\
 .allocated_valid_i(allocated_valid),.allocated_delivered_i(allocated_delivered),.allocated_tag_i(allocated_tag),.allocated_gen_i(allocated_gen),.allocated_position_i(allocated_position),\
 .participant_valid(p``pv),.participant_tag(p``pt),.participant_gen(p``pg),.participant_trace(p``ptr),.participant_token(p``ptk),.participant_pos(p``pps),.participant_accepted(participant_accepted),\
 .cancel_valid(p``cv),.cancel_done(p``cd),.cancel_fault(p``cf),.cancel_tag(p``ct),.cancel_gen(p``cg),.cancel_accepted(cancel_accepted),\
 .service_ready(p``sr),.native_ready(p``nr),.kv_drained(p``kv),.vm_drained(p``vm),.collective_drained(p``co),.host_drained(p``ho),.context_owned(p``cx),.links_drained(p``ld),.link_reset_seen(p``lr),.retrained(p``rt),\
 .service_epoch(p``se),.certificate_epoch(p``ce),.program_ready(p``pr),.program_epoch(p``pe),.program_digest(p``pd),\
 .result_v(result_v),.result_tag(result_tag),.result_gen(result_gen),.result_done(result_done),.result_fault(result_fault),.result_cause(result_cause),.result_token(result_token),.result_value(result_value),.result_cycles(result_cycles),.result_cr(p``rcr),\
 .terminal_accepted(terminal_accepted),.terminal_tag(terminal_tag),.terminal_gen(terminal_gen),.post_retired(post_retired),.terminal_released(p``tr),.result_transport_idle(p``rti),\
 .link_reset_request(link_reset_request),.retraining_request(retraining_request),\
 .step_issue_v(p``siv),.step_client_tag(p``sct),.step_slot(p``ss),.step_pos(p``sp),.step_retire_v(p``srv),.step_retire_cq(p``src),.step_retire_client_tag(p``srct),.step_retire_slot(p``srs),.step_retire_pos(p``srp),.step_retire_token(p``srt),\
 .cq_commit_v(p``cqv),.cq_client_tag(p``cqct),.cq_slot(p``cqs),.cq_pos(p``cqp),.cq_token(p``cqt),.certificate_valid(p``cerv),.certificate(p``cer),.certificate_prefix(p``cpf),.fault(p``flt))
 qkd_host_peer_coordinator_codec_pd_mu_old #(.MU(1)) uo `CONN(o_,sv,sd,rx_ready_o);
 qkd_host_peer_coordinator_codec_pd_mu #(.MU(1)) un `CONN(n_,rx_valid,rx_data,rx_ready_n);
 wire[8191:0]oa={o_tx_valid,o_tx_data,o_pv,o_cv,o_cd,o_cf,o_sr,o_nr,o_kv,o_vm,o_co,o_ho,o_cx,o_ld,o_lr,o_rt,o_pr,o_tr,o_cerv,o_pt,o_ct,o_pg,o_cg,o_ptr,o_cpf,o_ptk,o_pps,o_se,o_ce,o_pe,o_pd,o_rcr,o_rti,o_siv,o_srv,o_src,o_cqv,o_flt,o_sct,o_srct,o_cqct,o_ss,o_srs,o_cqs,o_sp,o_srp,o_srt,o_cqp,o_cqt,o_cer,rx_ready_o};
 wire[8191:0]na={n_tx_valid,n_tx_data,n_pv,n_cv,n_cd,n_cf,n_sr,n_nr,n_kv,n_vm,n_co,n_ho,n_cx,n_ld,n_lr,n_rt,n_pr,n_tr,n_cerv,n_pt,n_ct,n_pg,n_cg,n_ptr,n_cpf,n_ptk,n_pps,n_se,n_ce,n_pe,n_pd,n_rcr,n_rti,n_siv,n_srv,n_src,n_cqv,n_flt,n_sct,n_srct,n_cqct,n_ss,n_srs,n_cqs,n_sp,n_srp,n_srt,n_cqp,n_cqt,n_cer,rx_ready_n};
 // tag pool: user u, variant k (2 per user) -> grant-form tag (bits 42:37 = 0) and its terminal form (37)
 function automatic [58:0] ptag(input [1:0]u,input k,input term);
  ptag={13'h0a5,k,u,(term?6'd37:6'd0),18'h00123+18'(k),12'h0,7'h00};
  ptag[44:43]=u;
 endfunction
 integer cyc=0,checks=0,words=0,c1ok=0,c1=0,c8=0,rst=0,faults=0,fwd=0;
 integer i;reg[511:0]w;reg[1:0]u;reg k;reg[3:0]cls;reg[15:0]sq;
 initial begin
  repeat(3)@(posedge ck); por_n=1;
  for(cyc=0;cyc<3000000;cyc=cyc+1)begin
   @(negedge ck);
   if(por_n)begin checks=checks+1;if(oa!==na)begin $display("CODEQ FAIL cyc=%0d",cyc);for(i=0;i<8192;i=i+1)if(oa[i]!==na[i])begin $display(" first diff bit %0d o=%b n=%b",i,oa[i],na[i]);i=8192;end $fatal(1);end end
   // reset: random, or 40 edges after a fault
   if(!por_n)por_n=1;
   else if(($urandom%2000)==0||(o_flt&&($urandom%40)==0))begin por_n=0;rst=rst+1;end
   // allocation / terminal / post / result / accept inputs
   if(($urandom%4)==0)begin u=$urandom;k=$urandom;allocated_valid=1;allocated_tag=ptag(u,k,0);allocated_gen=$urandom;allocated_gen[1]=0;allocated_position=$urandom;allocated_delivered=$urandom;end
   else if(($urandom%8)==0)allocated_valid=0;
   terminal_accepted=($urandom%6)==0;u=$urandom;k=$urandom;terminal_tag=ptag(u,k,1);terminal_gen=$urandom;terminal_gen[1]=0;
   post_retired=($urandom%10)==0;
   result_v=($urandom%25)==0&&!uo.result_busy;u=$urandom;k=$urandom;result_tag=ptag(u,k,1);result_gen=$urandom;result_done=1;result_fault=($urandom%4)==0;
   result_cause=$urandom;result_token=$urandom;result_value=$urandom;result_cycles=$urandom;
   participant_accepted=uo.request_queued&~uo.request_ack&8'($urandom)&8'($urandom);
   cancel_accepted=o_cv&~uo.cancel_ack&8'($urandom);
   tx_ready=$urandom;link_reset_request=($urandom%50)==0?~link_reset_request:link_reset_request;retraining_request=($urandom%60)==0?~retraining_request:retraining_request;
   // rx words: one per rank at most every other edge (old codec's rx_seq + the word held in the slice)
   rx_valid=0;
   for(i=0;i<8;i=i+1)if(($urandom%3)==0&&!sv[i])begin
    w=0;cls=($urandom%40==0)?4'd10:4'd1+4'($urandom%9);
    if(i!=0&&cls>=5&&cls<=7&&($urandom%4)!=0)cls=1;
    if(i==0&&($urandom%3)==0)cls=4'd5+4'($urandom%3);
    sq=uo.rx_seq[i];if(($urandom%300)==0)sq=sq+1;
    w[7:0]=8'(cls);w[10:8]=3'(i);if(($urandom%400)==0)w[12]=1;w[29:14]=sq;
    u=$urandom;k=$urandom;
    case(cls)
     1:begin w[88:30]=(($urandom%3)==0)?ptag(u,k,1):ptag(u,k,0);w[88:73]=ptag(u,k,0)>>43;w[90:89]=$urandom%2;w[158:91]={$urandom,$urandom,$urandom};end
     2:begin w[88:30]=ptag(u,k,1);w[90:89]=$urandom%2;w[92:91]=1+($urandom%3);end
     3:begin w[136:30]={$urandom,$urandom,$urandom,$urandom};end
     4:begin w[90:30]=(($urandom%2)==0)?{uo.result_word[90:30]}:{$urandom,$urandom};end
     5,6,7:begin w[90:30]={$urandom,$urandom};if(cls!=6)w[90]=0;if(cls==5)w[90:72]=0;end
     8:begin w[88:30]=(($urandom%2)==0)?uo.accepted_tag:ptag(u,k,1);w[90:89]=uo.accepted_gen;end
     9:begin w[143:30]={$urandom,$urandom,$urandom,$urandom,$urandom};end
     default:;
    endcase
    if(($urandom%200)==0)w[300]=1;
    rx_valid[i]=1;rx_data[i*512+:512]=w;words=words+1;if(cls==1)c1=c1+1;if(cls==8)c8=c8+1;
   end
   // count requests consumed without fault, and same-edge table-write forwarding uses
   if(un.v1!=0&&!un.fault)for(i=0;i<8;i=i+1)if(un.v1[i]&&un.c1[i*10+1])begin c1ok=c1ok+1;if((un.alw1&&un.alw1_u==un.u1a[i*2+:2])||(un.tmw1&&un.tmw1_u==un.u1a[i*2+:2]))fwd=fwd+1;end
  end
  $display("CODEQ PASS checks=%0d words=%0d class1=%0d class1_consumed=%0d forwarded_compares=%0d class8=%0d resets=%0d",checks,words,c1,c1ok,fwd,c8,rst);
  $finish;
 end
endmodule
