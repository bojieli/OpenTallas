`timescale 1ns/1ps
// QE3-HROOT-PEER2 10-21: cycle equivalence of the registered-head lifecycle (host_peer_mu_sram_1021pl) against the
// KV-PEER12 lifecycle (host_peer_mu_sram_1020, renamed qkd_host_lifecycle_collected_mu_old), same allocator_mu /
// cohort_mu.  Every output compared every edge.  Reactive stimulus: requests per user, grants accepted, rank
// participants named with the cohort identity, results / cancels naming the user's live grant (terminal form),
// POSTs naming the POST-queue head, random drains, recovery starts; periodic random reset.
module tb_lc_equiv;
 reg ck=0;always #1 ck=~ck;
 reg por_n=0,warm_ready=0,request_valid=0;reg[17:0]request_token=0,request_position=0;reg[1:0]request_generation=0;
 reg grant_ready=0;reg[7:0]participant_valid=0;reg[471:0]participant_tag=0;reg[15:0]participant_generation=0;
 reg engine_admit_ready=0;reg[7:0]participant_ready=0;
 reg result_valid=0,result_done=0,result_fault=0;reg[58:0]result_tag=0;reg[1:0]result_generation=0;
 reg[7:0]cancel_valid=0,cancel_done=0,cancel_fault=0;reg[471:0]cancel_tag=0;reg[15:0]cancel_generation=0;
 reg[7:0]kv=0,vm=0,cl=0,ho=0;reg post_retired=0;reg[58:0]post_tag=0;reg[1:0]post_generation=0;
 reg recovery_start=0;reg[7:0]links_drained=0,link_reset_seen=0,retraining_done=0;
`define LOUT(p) wire p``rr,p``gv,p``av,p``ad,p``dv,p``dd,p``pp,p``lrr,p``trq,p``rc,p``wl,p``idf,p``ta,p``lf;wire[15:0]p``ge;wire[17:0]p``gt,p``gp;wire[1:0]p``gg,p``cg,p``akg;\
 wire[58:0]p``gtag,p``ct,p``akt;wire[7:0]p``pa,p``ar,p``ca;
 `LOUT(o_)
 `LOUT(n_)
`define LCONN(p) (.clk(ck),.por_n(por_n),.warm_ready(warm_ready),.request_valid(request_valid),.request_ready(p``rr),.request_token(request_token),.request_position(request_position),\
 .request_generation(request_generation),.grant_valid(p``gv),.grant_ready(grant_ready),.grant_epoch(p``ge),.grant_token(p``gt),.grant_position(p``gp),.grant_generation(p``gg),.grant_tag(p``gtag),\
 .allocated_valid(p``av),.allocated_delivered(p``ad),.participant_valid(participant_valid),.participant_tag(participant_tag),.participant_generation(participant_generation),.participant_accepted(p``pa),\
 .engine_admit_ready(engine_admit_ready),.participant_ready(participant_ready),.dispatch_valid(p``dv),.dispatched(p``dd),.cohort_tag(p``ct),.cohort_generation(p``cg),.accepted_ranks(p``ar),\
 .result_valid(result_valid),.result_done(result_done),.result_fault(result_fault),.result_tag(result_tag),.result_generation(result_generation),\
 .cancel_valid(cancel_valid),.cancel_done(cancel_done),.cancel_fault(cancel_fault),.cancel_tag(cancel_tag),.cancel_generation(cancel_generation),.cancel_accepted(p``ca),\
 .kv_drained(kv),.vm_drained(vm),.collective_drained(cl),.host_drained(ho),.post_retired(post_retired),.post_tag(post_tag),.post_generation(post_generation),.post_pending(p``pp),\
 .acknowledged_tag(p``akt),.acknowledged_generation(p``akg),.recovery_start(recovery_start),.links_drained(links_drained),.link_reset_seen(link_reset_seen),.retraining_done(retraining_done),\
 .link_reset_request(p``lrr),.retraining_request(p``trq),.recovery_complete(p``rc),.wrap_locked(p``wl),.identity_fault(p``idf),.terminal_accepted(p``ta),.lifecycle_fault(p``lf))
 qkd_host_lifecycle_collected_mu_old #(.MU(1)) uo `LCONN(o_);
 qkd_host_lifecycle_collected_mu #(.MU(1)) un `LCONN(n_);
 wire[511:0]oa={o_rr,o_gv,o_av,o_ad,o_dv,o_dd,o_pp,o_lrr,o_trq,o_rc,o_wl,o_idf,o_ta,o_lf,o_ge,o_gt,o_gp,o_gg,o_cg,o_akg,o_gtag,o_ct,o_akt,o_pa,o_ar,o_ca};
 wire[511:0]na={n_rr,n_gv,n_av,n_ad,n_dv,n_dd,n_pp,n_lrr,n_trq,n_rc,n_wl,n_idf,n_ta,n_lf,n_ge,n_gt,n_gp,n_gg,n_cg,n_akg,n_gtag,n_ct,n_akt,n_pa,n_ar,n_ca};
 reg[58:0]lg[0:3];reg[1:0]lgg[0:3];
 function automatic [58:0] term(input[58:0]t);term={t[58:43],6'd37,t[36:0]};endfunction
 integer cyc,checks=0,acc=0,tacc=0,cacc=0,posts=0,rst=0,disp=0,i;reg[1:0]u;
 always @(posedge ck) if(o_gv&&grant_ready)begin lg[o_gtag[44:43]]<=o_gtag;lgg[o_gtag[44:43]]<=o_gg;end
 initial begin
  for(i=0;i<4;i=i+1)begin lg[i]=0;lgg[i]=0;end
  repeat(3)@(posedge ck);por_n=1;
  for(cyc=0;cyc<3000000;cyc=cyc+1)begin
   @(negedge ck);
   if(por_n)begin checks=checks+1;if(oa!==na)begin $display("LCEQ FAIL cyc=%0d",cyc);for(i=0;i<512;i=i+1)if(oa[i]!==na[i])begin $display(" first diff bit %0d",i);i=512;end $fatal(1);end
    if(o_ta)tacc=tacc+1;if(o_ca!=0)cacc=cacc+1;if(post_retired)posts=posts+1;if(o_dv&&engine_admit_ready&&(&participant_ready))disp=disp+1;end
   if(!por_n)por_n=1;
   else if(($urandom%5000)==0||((o_lf||o_idf)&&($urandom%60)==0))begin por_n=0;rst=rst+1;end
   warm_ready=($urandom%50)!=0;
   request_valid=($urandom%3)==0;u=$urandom;request_position=$urandom;request_position[17:16]=u;request_position[15:13]=0;request_token=$urandom%151936;request_generation=$urandom%2;
   grant_ready=($urandom%2)==0;
   // rank participants name the user's cohort identity
   participant_valid=0;
   for(i=0;i<8;i=i+1)begin u=$urandom;participant_tag[59*i+:59]=uo.cohort.ctag[u];participant_generation[2*i+:2]=uo.cohort.cgen[u];
    if(($urandom%6)==0&&uo.cohort.act[u]&&!uo.cohort.acc[u][i])participant_valid[i]=1;end
   engine_admit_ready=($urandom%3)!=0;participant_ready=($urandom%8)==0?8'($urandom):8'hff;
   {kv,vm,cl,ho}=($urandom%3)==0?32'hffffffff:{4{8'($urandom)|8'hfe}};
   // results / cancels name the user's last grant (terminal form), sometimes a stale / other identity
   result_valid=($urandom%12)==0;u=$urandom;result_tag=($urandom%10)==0?term(lg[u])^59'h4000:term(lg[u]);result_generation=lgg[u];
   result_done=($urandom%5)!=0;result_fault=!result_done||($urandom%7)==0;
   cancel_valid=0;
   for(i=0;i<8;i=i+1)begin u=$urandom;cancel_tag[59*i+:59]=(($urandom%3)==0)?uo.ack_tag[u]:term(lg[u]);cancel_generation[2*i+:2]=(($urandom%3)==0)?uo.ack_gen[u]:lgg[u];
    cancel_done[i]=$urandom;cancel_fault[i]=!cancel_done[i];if(($urandom%30)==0)cancel_valid[i]=1;end
   post_retired=uo.pn!=0&&($urandom%6)==0;post_tag=uo.ack_tag[uo.pq[uo.pr]];post_generation=uo.ack_gen[uo.pq[uo.pr]];if(($urandom%40)==0)post_tag[3]=~post_tag[3];
   recovery_start=($urandom%3000)==0;links_drained=($urandom%2)?8'hff:8'($urandom);link_reset_seen=8'($urandom);retraining_done=8'($urandom);
  end
  $display("LCEQ PASS checks=%0d terminal_accepted=%0d cancel_accepts=%0d posts=%0d dispatches=%0d resets=%0d",checks,tacc,cacc,posts,disp,rst);
  $finish;
 end
endmodule
