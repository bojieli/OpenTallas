`timescale 1ns/1ps
// Q-VMWB 2026-10-16 (coordinator: prove the 0az ring-64 sizing on the controller, not on a reading of it).
// The ACTUAL KV-die JEDEC timing core ot_qkd_static_kv_timing (REF_MODE 1 REFpb every 118 HBM edges, tRFCpb 196,
// tRREFD 8) in PROFILE 1 (maximum-legal RD slots: an RD issues on every edge JEDEC permits) streams one layer's K pass
// of T = 8192 (256 sectors per PC, descriptor posted before go, as production) for EVERY refresh phase: instance o
// starts at go = G0 + o, o = 0..117 (one REFpb period), for PC parity 0 and 1 (the shared row slot).  Per instance it
// prints the go -> first RD delay, the K-pass span and every RD's lateness against the ideal 1-RD-per-edge stream
// from the earliest first RD; the kv_calendar.py refresh model (block_hbm 0) holds iff lateness is 0 at every phase.
module tb_kv_refresh_rdrate;
 parameter integer PROFILE=1;
 reg [235:0] compiled_slots[0:2117];
 string slots_file;integer slots_fd;
 initial if(PROFILE==0)begin
  if(!$value$plusargs("SLOTS=%s",slots_file))$fatal(1,"compiled slots required");
  slots_fd=$fopen(slots_file,"r");if(!slots_fd)$fatal(1,"required slot image missing");$fclose(slots_fd);
  $readmemh(slots_file,compiled_slots);
 end
 localparam integer NO=118, NP=2, N=NO*NP, NS=256, G0=600, CYCLES=G0+NO+1400;
 reg ck=0; always #0.512 ck=~ck;
 reg rst=0; integer t=0;
 wire [N-1:0] cv, rf, sf;
 integer first[0:N-1], last[0:N-1], cnt[0:N-1], late_max[0:N-1], rdi[0:N-1];
 integer errors=0;
 genvar g;
 generate for(g=0;g<N;g=g+1)begin:i
  localparam integer O=g%NO, PCI=g/NO;
  wire dv=(t==G0+O-64), go=(t==G0+O);
  wire [4:0] cb,cc;
  ot_qkd_static_kv_timing #(.ENABLE(1),.PC(PCI),.REF_PHASE(0),.PROFILE(PROFILE)) u(
   .clk(ck),.rst_n(rst),.desc_v(dv),.desc_r(),.desc_row(19'd67),.desc_n(11'd256),.desc_first(10'd0),.go(go),.next_posted(1'b0),
   .reserved_rd(PROFILE==0 ? compiled_slots[t][g] : 1'b0),.reserved_static_col(1'b0),.reserved_write_col(1'b0),.schedule_fault(sf[g]),.phase_idle(),
   .row_v(),.row_prio(),.row_gnt(1'b1),.row_op(),.row_bank(),.row_row(),
   .col_v(cv[g]),.col_bank(cb),.col_col(cc),.busy(),.ref_fault(rf[g]),
   .wr_v(1'b0),.wr_bank(5'b0),.wr_col(5'b0),.wr_r(),.col_we(),.wr_rd(1'b0),.col_aq(),
   .s_context(347'b0),.col_context(),.s_v(1'b0),.s_we(1'b0),.s_bank(5'b0),.s_col(5'b0),.s_row(19'b0),.s_r(),.col_sr(),.s_pop());
 end endgenerate
 integer p, gfirst, glast, worst_late, worst_span, worst_first;
 initial begin
  for(p=0;p<N;p=p+1)begin first[p]=-1;last[p]=-1;cnt[p]=0;late_max[p]=0;end
  repeat(8)@(negedge ck); rst=1;
  for(t=0;t<CYCLES;t=t+1)begin
   @(posedge ck); #0.1;
   for(p=0;p<N;p=p+1)begin
    if(cv[p])begin
     if(first[p]<0)first[p]=t;
     last[p]=t; cnt[p]=cnt[p]+1;
    end
    if(rf[p]||sf[p])begin if(errors<10)$display("BAD fault inst %0d t %0d ref %0d sched %0d",p,t,rf[p],sf[p]);errors=errors+1;end
   end
   @(negedge ck);
  end
  worst_late=0;worst_span=0;worst_first=0;
  for(p=0;p<N;p=p+1)begin
   if(cnt[p]!=NS)begin $display("BAD inst %0d produced %0d of %0d",p,cnt[p],NS);errors=errors+1;end
   $display("INST pc%0d off%0d first_after_go %0d span %0d lost %0d",p/NO,p%NO,first[p]-(G0+p%NO),last[p]-first[p]+1,last[p]-first[p]+1-NS);
   if(first[p]-(G0+p%NO)>worst_first)worst_first=first[p]-(G0+p%NO);
   if(last[p]-first[p]+1-NS>worst_span)worst_span=last[p]-first[p]+1-NS;
   // lateness of the last RD vs ideal from the EARLIEST first-RD delay over all phases
  end
  for(p=0;p<N;p=p+1)if(last[p]-(G0+p%NO)-(NS-1)-0>worst_late)worst_late=last[p]-(G0+p%NO)-(NS-1);
  $display("SUMMARY phases %0d pcs %0d sectors %0d worst_first_after_go %0d worst_lost_slots %0d worst_last_after_go_minus_255 %0d errors %0d",
   NO,NP,NS,worst_first,worst_span,worst_late,errors);
  if(errors)$fatal(1,"FAIL kv refresh rdrate");else $display("PASS kv refresh rdrate");
  $finish;
 end
endmodule
