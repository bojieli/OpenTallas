`timescale 1ns/1ps
// HRORDER 10-18 lock-step equivalence: the restructured qkd_host_ingest_map / qkd_host_commit_order /
// qkd_host_boot_dispatch_debt (+ qkd_host_commit_order_debt) against verbatim copies of the previous forms (ref/*_ref.sv).
// Same inputs every cycle; every output compared every cycle (issue_pc only when issue_v: it is sampled only then).
// Stimulus follows the credit protocols (credits returned for what was emitted, physical ACKs only for outstanding PCs)
// so the queues fill, wrap and drain; rare protocol violations and reset pulses exercise the fault and reset paths.
// usage: +seed=N +cycles=N   prints HRORDER_EQUIV PASS ... or HRORDER_EQUIV FAIL ...
module tb_hrorder_equiv;
 reg ck=0,rst_n=0;
 always #1 ck=~ck;
 integer seed,cycles,cyc=0,errs=0,emits=0,pops=0,sends=0,dpops=0,faults_seen=0,fm=0,fo=0,fd=0,resets=0,i,k;
 reg d_hold;
 integer map_max_count=0, dispatch_max_count=0;
 always @(negedge ck)begin
  if(ma.count>map_max_count)map_max_count=ma.count;
  if(da.count>dispatch_max_count)dispatch_max_count=da.count;
 end
 // ---------------- map ----------------
 reg[289:0]m_ing;reg[127:0]m_out_cr;reg[7:0]m_ack_n;reg m_marker_cr,m_ord_cr;
 wire m_ing_cr_a,m_ing_cr_b,m_mv_a,m_mv_b,m_f_a,m_f_b,m_iv_a,m_iv_b;
 wire[1163:0]m_out_a,m_out_b;wire[65:0]m_mk_a,m_mk_b;wire[31:0]m_is_a,m_is_b,m_la_a,m_la_b;wire[6:0]m_ip_a,m_ip_b;
 qkd_host_ingest_map_ref #(.ORDERED(1))ma(.ck(ck),.rst_n(rst_n),.ing(m_ing),.ing_cr(m_ing_cr_a),.out(m_out_a),.out_cr(m_out_cr),
  .ack_n(m_ack_n),.marker_v(m_mv_a),.marker(m_mk_a),.marker_cr(m_marker_cr),.fault(m_f_a),.issued(m_is_a),.landed(m_la_a),
  .ord_cr(m_ord_cr),.issue_v(m_iv_a),.issue_pc(m_ip_a));
 qkd_host_ingest_map #(.ORDERED(1))mb(.ck(ck),.rst_n(rst_n),.ing(m_ing),.ing_cr(m_ing_cr_b),.out(m_out_b),.out_cr(m_out_cr),
  .ack_n(m_ack_n),.marker_v(m_mv_b),.marker(m_mk_b),.marker_cr(m_marker_cr),.fault(m_f_b),.issued(m_is_b),.landed(m_la_b),
  .ord_cr(m_ord_cr),.issue_v(m_iv_b),.issue_pc(m_ip_b));
 // ---------------- commit order ----------------
 reg o_iv;reg[6:0]o_ipc;reg[127:0]o_acks;
 wire o_pv_a,o_pv_b,o_f_a,o_f_b;wire[31:0]o_pc_a,o_pc_b;
 qkd_host_commit_order_ref oa(.ck(ck),.rst_n(rst_n),.issue_v(o_iv),.issue_pc(o_ipc),.acks(o_acks),.prefix_v(o_pv_a),.prefix_count(o_pc_a),.fault(o_f_a));
 qkd_host_commit_order     ob(.ck(ck),.rst_n(rst_n),.issue_v(o_iv),.issue_pc(o_ipc),.acks(o_acks),.prefix_v(o_pv_b),.prefix_count(o_pc_b),.fault(o_f_b));
 // ---------------- boot dispatch debt ----------------
 reg d_br,d_kcr,d_hcr;reg[289:0]d_ing;reg[127:0]d_acks;
 wire d_icr_a,d_icr_b,d_ic_a,d_ic_b,d_pv_a,d_pv_b,d_f_a,d_f_b,d_dq_a,d_dq_b,d_oq_a,d_oq_b;
 wire[289:0]d_kv_a,d_kv_b;wire[282:0]d_hb_a,d_hb_b;wire[31:0]d_la_a,d_la_b,d_is_a,d_is_b;
 qkd_host_boot_dispatch_debt_ref da(.ck(ck),.ck_order(ck),.rst_n(rst_n),.boot_release(d_br),.ing(d_ing),.ing_cr(d_icr_a),.kv(d_kv_a),
  .kv_cr(d_kcr),.hb(d_hb_a),.hb_cr(d_hcr),.image_check(d_ic_a),.acks(d_acks),.prefix_v(d_pv_a),.landed(d_la_a),.issued(d_is_a),
  .fault(d_f_a),.dispatch_quiet(d_dq_a),.order_quiet(d_oq_a));
 qkd_host_boot_dispatch_debt db(.ck(ck),.ck_order(ck),.rst_n(rst_n),.boot_release(d_br),.ing(d_ing),.ing_cr(d_icr_b),.kv(d_kv_b),
  .kv_cr(d_kcr),.hb(d_hb_b),.hb_cr(d_hcr),.image_check(d_ic_b),.acks(d_acks),.prefix_v(d_pv_b),.landed(d_la_b),.issued(d_is_b),
  .fault(d_f_b),.dispatch_quiet(d_dq_b),.order_quiet(d_oq_b));
 // ---------------- stimulus state (driven from the reference outputs) ----------------
 integer m_cr_due[0:127];integer m_ord_due,m_ack_due,m_in_cr,o_out[0:127],d_out[0:127],d_in_cr,d_kv_due,d_hb_due;
 integer o_issued_tot;
 function automatic [31:0] rnd_addr(input integer r);
  reg[31:0]a;integer sel;
  begin
   sel=r%512;
   if(sel<300)begin a=0;a[13:0]=$urandom;a[17:15]=$urandom;a[23:18]=$urandom%36;a[14]=0;end   // local, legal (sec=a23:7)
   else if(sel<480)begin a=32'h80000000;a[24:0]=25'($urandom%25'd19457304);end                      // embed / scale, legal
   else if(sel<511)a=32'hffffffff;                                                                    // end marker
   else a=$urandom;                                                                                  // anything (faults)
   rnd_addr=a;
  end
 endfunction
 function automatic [6:0] emb_target(input [24:0] e);
  reg[24:0]s;
  begin s=e-25'd19447808;emb_target=(e<25'd19447808)?{e[6:5],e[4:0]}:{s[6:5],s[4:0]};end
 endfunction
 task automatic chk(input bit c,input string what);
  if(!c)begin errs=errs+1;if(errs<=10)$display("HRORDER_EQUIV MISMATCH cyc=%0d %s",cyc,what);end
 endtask
 initial begin
  if(!$value$plusargs("seed=%d",seed))seed=1;
  if(!$value$plusargs("cycles=%d",cycles))cycles=100000;
  void'($urandom(seed));
  for(i=0;i<128;i++)begin m_cr_due[i]=0;o_out[i]=0;d_out[i]=0;end
  m_ord_due=0;m_ack_due=0;m_in_cr=8;d_in_cr=8;d_kv_due=0;d_hb_due=0;o_issued_tot=0;d_hold=0;
  m_ing=0;m_out_cr=0;m_ack_n=0;m_marker_cr=0;m_ord_cr=0;o_iv=0;o_ipc=0;o_acks=0;d_br=0;d_kcr=0;d_hcr=0;d_ing=0;d_acks=0;
  repeat(3)@(negedge ck);rst_n=1;
  while(cyc<cycles)begin
   @(negedge ck);cyc=cyc+1;
   // ---- compare (outputs settled after the posedge) ----
   chk(m_ing_cr_a==m_ing_cr_b,"map.ing_cr");chk(m_out_a==m_out_b,"map.out");chk(m_mv_a==m_mv_b,"map.marker_v");
   chk(m_mk_a==m_mk_b,"map.marker");chk(m_f_a==m_f_b,"map.fault");chk(m_is_a==m_is_b,"map.issued");chk(m_la_a==m_la_b,"map.landed");
   chk(m_iv_a==m_iv_b,"map.issue_v");chk(!m_iv_a||m_ip_a==m_ip_b,"map.issue_pc");
   chk(o_pv_a==o_pv_b,"order.prefix_v");chk(o_pc_a==o_pc_b,"order.prefix_count");chk(o_f_a==o_f_b,"order.fault");
   chk(d_icr_a==d_icr_b,"disp.ing_cr");chk(d_kv_a==d_kv_b,"disp.kv");chk(d_hb_a==d_hb_b,"disp.hb");chk(d_ic_a==d_ic_b,"disp.image_check");
   chk(d_pv_a==d_pv_b,"disp.prefix_v");chk(d_la_a==d_la_b,"disp.landed");chk(d_is_a==d_is_b,"disp.issued");chk(d_f_a==d_f_b,"disp.fault");
   chk(d_dq_a==d_dq_b,"disp.dispatch_quiet");chk(d_oq_a==d_oq_b,"disp.order_quiet");
   if(m_iv_a)emits++;if(o_pv_a)pops++;if(d_kv_a[0]||d_hb_a[0])sends++;if(d_pv_a)dpops++;
   if(m_f_a||o_f_a||d_f_a)faults_seen++;if(m_f_a)fm++;if(o_f_a)fo++;if(d_f_a)fd++;
   // ---- reset pulses: rarely, and soon after any fault so the run keeps exercising the datapath ----
   if(($urandom%20000)==0||((m_f_a||o_f_a||d_f_a)&&($urandom%4)==0))begin
    rst_n=0;resets++;d_hold=0;
    for(i=0;i<128;i++)begin m_cr_due[i]=0;o_out[i]=0;d_out[i]=0;end
    m_ord_due=0;m_ack_due=0;m_in_cr=8;d_in_cr=8;d_kv_due=0;d_hb_due=0;
    m_ing=0;d_ing=0;o_iv=0;o_acks=0;d_acks=0;m_out_cr=0;m_ack_n=0;m_marker_cr=0;m_ord_cr=0;d_kcr=0;d_hcr=0;d_br=0;
    @(negedge ck);cyc=cyc+1;rst_n=1;continue;
   end
   // ---- map stimulus ----
   if(m_ing_cr_a)m_in_cr++;
   if(m_iv_a)begin m_cr_due[m_ip_a]++;m_ord_due++;m_ack_due++;end
   m_ing=0;
   if(m_in_cr>0&&($urandom%4)!=0)begin
    m_ing[0]=1;m_ing[1]=($urandom%1024)!=0;m_ing[33:2]=rnd_addr($urandom);
    for(k=34;k<290;k+=32)m_ing[k+:32]=$urandom;
    if(($urandom%4096)!=0)m_in_cr--;            // rarely overrun the input credit (fault path)
   end
   m_out_cr=0;for(i=0;i<128;i++)if(m_cr_due[i]>0&&($urandom%3)==0)begin m_out_cr[i]=1;m_cr_due[i]--;end
   if(($urandom%50000)==0)m_out_cr[$urandom%128]=1;                  // spurious credit (overflow fault)
   m_ord_cr=0;if(m_ord_due>0&&($urandom%3)==0)begin m_ord_cr=1;m_ord_due--;end
   m_ack_n=0;if(m_ack_due>0&&($urandom%2)==0)begin m_ack_n=1+$urandom%((m_ack_due>3)?3:m_ack_due);m_ack_due-=m_ack_n;end
   m_marker_cr=m_mv_a&&($urandom%8)!=0;
   // ---- commit order stimulus ----
   o_iv=($urandom%3)==0;o_ipc=(($urandom%4)!=0)?7'($urandom%6):7'($urandom);
   if(o_iv)o_out[o_ipc]++;
   o_acks=0;for(i=0;i<128;i++)if(o_out[i]>0&&($urandom%4)==0)begin o_acks[i]=1;o_out[i]--;end
   if(($urandom%50000)==0)o_acks[$urandom%128]=1;                    // unexpected ACK (fault path)
   // ---- dispatch stimulus ----
   if(d_icr_a)d_in_cr++;
   if(d_kv_a[0])begin d_kv_due++;if(d_kv_a[33:2]!=32'hffffffff)d_out[d_kv_a[8:2]]++;end
   if(d_hb_a[0])begin d_hb_due++;if(d_hb_a[1]==0)d_out[emb_target(d_hb_a[26:2])]++;end
   d_ing=0;
   if(d_in_cr>0&&($urandom%3)!=0)begin
    d_ing[0]=1;d_ing[1]=($urandom%1024)!=0;d_ing[33:2]=rnd_addr($urandom);
    if(d_ing[33:2]==32'hffffffff&&($urandom%4)!=0)d_ing[33:2]=rnd_addr(0);   // fewer markers: each holds until release
    for(k=34;k<290;k+=32)d_ing[k+:32]=$urandom;
    if(($urandom%4096)!=0)d_in_cr--;
   end
   d_kcr=d_kv_due>0&&($urandom%3)==0;if(d_kcr)d_kv_due--;
   d_hcr=d_hb_due>0&&($urandom%3)==0;if(d_hcr)d_hb_due--;
   if(d_kv_a[0]&&d_kv_a[33:2]==32'hffffffff)d_hold=1;
   d_br=(d_hold&&($urandom%20)==0)||(($urandom%50000)==0);if(d_br)d_hold=0;
   d_acks=0;for(i=0;i<128;i++)if(d_out[i]>0&&($urandom%4)==0)begin d_acks[i]=1;d_out[i]--;end
  end
  $display("HRORDER_FIFO_CAPACITY map_max=%0d dispatch_max=%0d logical_depth=8",map_max_count,dispatch_max_count);
  $display("HRORDER_EQUIV %s seed=%0d cycles=%0d mismatches=%0d map_emits=%0d order_pops=%0d disp_sends=%0d disp_pops=%0d fault_cycles=%0d (map %0d order %0d disp %0d) resets=%0d",
   (errs==0)?"PASS":"FAIL",seed,cyc,errs,emits,pops,sends,dpops,faults_seen,fm,fo,fd,resets);
  $finish;
 end
endmodule
