`timescale 1ns/1ps
// Component gate of vm_service_root on the real 22 SRAM macros (OT_MEM_NO_INIT) and 18 checker islands.
// Positive phases: II 1 stream of 1,664 beats, 26 / 104 bursts, saturation by a slow receiver, random
// receiver back-pressure (rewind), receiver masks, lease changes, generation wraps, corrected single-bit
// reads. Negative phases (each must raise the stated fault code and never publish the bad beat): double-bit
// verify / publication reads, a valid-code wrong write, stale / old-generation / duplicate / unissued /
// wrong-owner ACKs, a lease change on a valid beat, a control upset, an uncorrectable expected seat (fc58d5470)
// at the verify and at the publication check. A single-bit expected-seat upset is corrected and publishes exact.
module tb_vm_service_root;
 parameter integer GENW=11;
 parameter integer WRAPS=2;
 localparam integer MAXN=1<<19;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0;reg [3:0] rcv_mask=4'hf;
 reg wr_v=0;wire wr_ready;reg [2062:0] wr_data=0;reg wr_last=0;reg [191:0] wr_owner=0;
 wire [3:0] tap_v;reg [3:0] tap_ready=4'hf;wire [2062:0] tap_data;wire [191:0] tap_owner;
 wire [15:0] tap_ticket;wire tap_last;
 reg [3:0] tap_ACK_v=0;reg [4*192-1:0] tap_ACK_owner=0;reg [4*16-1:0] tap_ACK_ticket=0;
 wire native_release;wire [15:0] release_ticket;wire release_last;
 wire drained,fault;wire [3:0] fault_code;wire [15:0] stale_count,dup_count,wrap_epochs;
 vm_service_root #(.GENW(GENW)) dut(.*);
 // ---------------- deterministic stimulus ----------------
 function automatic [2062:0] beat(input integer n);
  reg [31:0] h;
  begin
   beat=0;beat[2062]=1'b1;beat[2061:2055]=7'((n/13)%128);beat[2054:2048]=7'(n%13);
   for(integer j=0;j<64;j=j+1)begin h=32'h9e3779b9*(n*64+j+1);h=h^(h>>15);beat[j*32+:32]=h^32'hab312701;end
  end
 endfunction
 function automatic [191:0] own(input integer id);
  own={6{32'h1b873593*(id+3)}}^192'(id);
 endfunction
 reg [7:0] own_id[0:MAXN-1];reg last_f[0:MAXN-1];reg [3:0] tgt[0:MAXN-1],acked_true[0:MAXN-1];
 integer due[0:3][0:MAXN-1];
 integer base=0,n_acc=0,n_rel=0,cyc=0,stalls=0,max_out=0,rewinds=0;
 integer n_tap[0:3],ap[0:3],lat[0:3],rdy_mode[0:3];
 integer acc_cyc[0:MAXN-1];integer max_a2t=0,max_a2r=0,taps_total=0;
 integer cur_oid=0;
 reg fault_expected=0;reg [31:0] lf=32'h2545f491;
 reg [3:0] inj_ack_v=0;reg [15:0] inj_ack_t=0;reg [191:0] inj_ack_o=0;
 reg inj_armed=0,inj_kind=0;integer inj_seq=0,inj_hit=0;reg [2815:0] inj_mask=0;
 reg winj_armed=0;integer winj_seq=0,winj_hit=0;reg [2815:0] winj_mask=0;
 reg einj_armed=0,einj_kind=0;integer einj_seq=0,einj_hit=0;reg [287:0] einj_mask=0;reg [3:0] einj_word=0;
 function automatic [15:0] tick(input integer n);
  integer m;
  begin m=n-base;tick=16'({GENW'((m/32)),1'(m%2),4'((m/2)%16)});end
 endfunction
 integer k,rr;
 // ---------------- monitors (pre-edge values) ----------------
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(rst_n)begin
   if(fault&&!fault_expected)begin $display("unexpected fault code%0d at cycle%0d",fault_code,cyc);$fatal(1,"SERVICE_ROOT FAIL");end
   if(dut.rewind)rewinds=rewinds+1;
   if(wr_v&&!wr_ready)stalls=stalls+1;
   for(rr=0;rr<4;rr=rr+1)if(tap_v[rr]&&tap_ready[rr])begin
    k=n_tap[rr];while(k<n_acc&&!tgt[k][rr])k=k+1;
    if(k>=n_acc)begin $display("receiver%0d tap without an accepted beat",rr);$fatal(1,"SERVICE_ROOT FAIL");end
    if(tap_data!==beat(k)||tap_owner!==own(own_id[k])||tap_ticket!==tick(k)||tap_last!==last_f[k])begin
     $display("receiver%0d beat%0d payload/owner/ticket/order mismatch ticket%04h want%04h",rr,k,tap_ticket,tick(k));
     $fatal(1,"SERVICE_ROOT FAIL");
    end
    due[rr][k]=cyc+(lat[rr]<0?2+(((cyc*40503+rr*9973+k*7919)>>3)%(-lat[rr])):lat[rr]);
    if(cyc-acc_cyc[k]>max_a2t)max_a2t=cyc-acc_cyc[k];
    n_tap[rr]=k+1;taps_total=taps_total+1;
   end
   if(native_release)begin
    k=n_rel;
    if(k>=n_acc||release_ticket!==tick(k)||acked_true[k]!==tgt[k]||release_last!==last_f[k])begin
     $display("release%0d ticket%04h want%04h acks%b target%b: release before every receiver ACK or out of order",k,release_ticket,tick(k),acked_true[k],tgt[k]);
     $fatal(1,"SERVICE_ROOT FAIL");
    end
    if(cyc-acc_cyc[k]>max_a2r)max_a2r=cyc-acc_cyc[k];
    n_rel=n_rel+1;
   end
   if(wr_v&&wr_ready)begin
    if((n_acc-base)>0&&((n_acc-base)%(32<<GENW))==0&&n_rel!=n_acc)begin
     $display("generation wrapped with%0d live tickets",n_acc-n_rel);$fatal(1,"SERVICE_ROOT FAIL");
    end
    own_id[n_acc]=8'(cur_oid);tgt[n_acc]=rcv_mask;acked_true[n_acc]=0;
    last_f[n_acc]=wr_last;acc_cyc[n_acc]=cyc;
    n_acc=n_acc+1;
   end
   if(n_acc-n_rel>32)begin $display("more than32 outstanding tickets");$fatal(1,"SERVICE_ROOT FAIL");end
   if(n_acc-n_rel>max_out)max_out=n_acc-n_rel;
  end
 end
 // ---------------- receiver ACK drivers and injections ----------------
 always @(negedge clk)begin
  tap_ACK_v=0;
  for(rr=0;rr<4;rr=rr+1)begin
   if(rdy_mode[rr]==1)begin lf=lf^(lf<<13);lf=lf^(lf>>17);lf=lf^(lf<<5);tap_ready[rr]=lf[3]|lf[7];end
   else if(rdy_mode[rr]==0)tap_ready[rr]=1;
   if(inj_ack_v[rr])begin
    tap_ACK_v[rr]=1;tap_ACK_ticket[rr*16+:16]=inj_ack_t;tap_ACK_owner[rr*192+:192]=inj_ack_o;inj_ack_v[rr]=0;
   end else begin
    k=ap[rr];while(k<n_tap[rr]&&!tgt[k][rr])k=k+1;
    if(k<n_tap[rr]&&cyc>=due[rr][k])begin
     tap_ACK_v[rr]=1;tap_ACK_ticket[rr*16+:16]=tick(k);tap_ACK_owner[rr*192+:192]=own(own_id[k]);
     acked_true[k][rr]=1;ap[rr]=k+1;
    end else ap[rr]=k;
   end
  end
  dut.tb_rd_xor[0]=0;dut.tb_rd_xor[1]=0;dut.tb_wr_xor=0;
  if(inj_armed)for(rr=0;rr<2;rr=rr+1)
   if(dut.t_v[3][rr]&&dut.t_k[3][rr]==inj_kind&&dut.t_n[3][rr]==5'(inj_seq-base))begin
    dut.tb_rd_xor[rr]=inj_mask;inj_armed=0;inj_hit=inj_hit+1;
   end
  dut.tb_exp_xor[0]=0;dut.tb_exp_xor[1]=0;
  if(einj_armed)for(rr=0;rr<2;rr=rr+1)
   if(dut.t_v[3][rr]&&dut.t_k[3][rr]==einj_kind&&dut.t_n[3][rr]==5'(einj_seq-base))begin
    dut.tb_exp_xor[rr]=einj_mask;dut.tb_exp_word=einj_word;einj_armed=0;einj_hit=einj_hit+1;
   end
  if(winj_armed&&dut.w0_v&&{dut.w0_slot,dut.w0_bank}==5'(winj_seq-base))begin
   dut.tb_wr_xor=winj_mask;winj_armed=0;winj_hit=winj_hit+1;
  end
 end
 // ---------------- driver tasks ----------------
 task automatic lease(input integer oid);
  begin cur_oid=oid;wr_owner=own(oid);repeat(4)@(negedge clk);end
 endtask
 task automatic send(input integer nb,input integer on,input integer off,input integer rnd);
  integer s,b;
  begin
   for(b=0;b<nb&&!fault;b=b+1)begin
    if(on>0&&b>0&&(b%on)==0)repeat(off)@(negedge clk);
    if(rnd>0)begin lf=lf^(lf<<13);lf=lf^(lf>>17);lf=lf^(lf<<5);if((lf%rnd)==0)repeat(1+(lf[11:8]%7))@(negedge clk);end
    wr_v=1;wr_data=beat(n_acc);wr_last=(b==nb-1);s=n_acc;
    @(negedge clk);while(n_acc==s&&!fault)@(negedge clk);
    wr_v=0;
   end
   wr_v=0;wr_last=0;
  end
 endtask
 task automatic drain;
  integer t;
  begin
   t=0;while(!(drained&&n_rel==n_acc)&&t<200000)begin @(negedge clk);t=t+1;end
   if(!drained||n_rel!=n_acc)begin $display("drain timeout accepted%0d released%0d",n_acc,n_rel);$fatal(1,"SERVICE_ROOT FAIL");end
   for(integer q=0;q<4;q=q+1)begin
    k=n_tap[q];while(k<n_acc&&!tgt[k][q])k=k+1;
    if(k!=n_acc)begin $display("receiver%0d missed beats",q);$fatal(1,"SERVICE_ROOT FAIL");end
   end
  end
 endtask
 task automatic reset_dut;
  begin
   wr_v=0;fault_expected=1;repeat(2)@(negedge clk);rst_n=0;inj_armed=0;winj_armed=0;einj_armed=0;inj_ack_v=0;dut.tb_upset=0;
   repeat(3)@(negedge clk);
   base=n_acc;n_rel=n_acc;for(integer q=0;q<4;q=q+1)begin n_tap[q]=n_acc;ap[q]=n_acc;lat[q]=2;rdy_mode[q]=0;end
   rcv_mask=4'hf;tap_ready=4'hf;rst_n=1;fault_expected=0;repeat(2)@(negedge clk);
  end
 endtask
 task automatic want_fault(input integer code,input [255:0] name);
  integer t,q;integer taps_at;
  begin
   t=0;while(!fault&&t<400)begin @(negedge clk);t=t+1;end
   if(!fault||fault_code!=4'(code))begin
    $display("%0s: expected fault code%0d, got fault%0b code%0d",name,code,fault,fault_code);$fatal(1,"SERVICE_ROOT FAIL");
   end
   // quarantine: no further publication, no acceptance
   repeat(3)@(negedge clk);taps_at=taps_total;
   for(q=0;q<60;q=q+1)begin
    @(negedge clk);
    if(tap_v!=0||wr_ready||taps_total!=taps_at)begin $display("%0s: publication/acceptance after the fault",name);$fatal(1,"SERVICE_ROOT FAIL");end
   end
   $display("NEG %0s fault_code=%0d stale=%0d dup=%0d",name,fault_code,stale_count,dup_count);
  end
 endtask
 task automatic never_published(input integer kbad,input [255:0] name);
  begin
   for(integer q=0;q<4;q=q+1)if(n_tap[q]>kbad)begin $display("%0s: bad beat%0d was published",name,kbad);$fatal(1,"SERVICE_ROOT FAIL");end
  end
 endtask
 function automatic [2815:0] code_delta(input integer word,input [63:0] d);
  begin code_delta=0;code_delta[word*72+:72]=dut.banks[0].words[0].u_wb.encode64(d);end
 endfunction
 integer c0,s0,a0,r0,kb,w,mo;
 initial begin
  for(integer q=0;q<4;q=q+1)begin n_tap[q]=0;ap[q]=0;lat[q]=2;rdy_mode[q]=0;end
  dut.tb_rd_xor[0]=0;dut.tb_rd_xor[1]=0;dut.tb_wr_xor=0;dut.tb_upset=0;dut.tb_exp_xor[0]=0;dut.tb_exp_xor[1]=0;dut.tb_exp_word=0;
  repeat(4)@(negedge clk);rst_n=1;repeat(2)@(negedge clk);
  // ---- A: II 1 stream, 1,664 beats, receivers ready, ACK two edges after the tap ----
  lease(1);c0=cyc;s0=stalls;a0=n_acc;max_a2t=0;max_a2r=0;max_out=0;
  send(1664,0,0,0);r0=cyc;drain();
  if(stalls!=s0||r0-c0!=1664)begin $display("II1 stream stalled: stalls%0d cycles%0d",stalls-s0,r0-c0);$fatal(1,"SERVICE_ROOT FAIL");end
  $display("RATE stream beats=1664 accept_cycles=%0d stalls=0 accept_to_tap=%0d accept_to_release=%0d drain_after_last=%0d max_outstanding=%0d",r0-c0,max_a2t,max_a2r,cyc-r0,max_out);
  // ---- A2: production bursts 26 (FP8) and 104 (BF16) with short gaps, new lease each ----
  lease(2);s0=stalls;send(1664,26,5,0);drain();
  lease(3);send(1664,104,20,0);drain();
  if(stalls!=s0)begin $display("burst phases stalled%0d",stalls-s0);$fatal(1,"SERVICE_ROOT FAIL");end
  $display("RATE bursts26/104 beats=3328 stalls=0");
  // ---- B: saturation by one slow receiver: exactly 32 outstanding, then held ----
  lease(4);lat[3]=70;max_out=0;s0=stalls;send(600,0,0,0);drain();
  if(max_out!=32||stalls==s0)begin $display("saturation not reached: max%0d",max_out);$fatal(1,"SERVICE_ROOT FAIL");end
  $display("SAT beats=600 max_outstanding=%0d held_cycles=%0d",max_out,stalls-s0);
  // ---- B2: random receiver back-pressure, random ACK latency, random producer gaps ----
  lease(5);for(integer q=0;q<4;q=q+1)begin rdy_mode[q]=1;lat[q]=-37;end
  w=rewinds;send(6000,0,0,5);drain();
  if(rewinds==w)begin $display("no rewind exercised");$fatal(1,"SERVICE_ROOT FAIL");end
  $display("BACKPRESSURE beats=6000 rewinds=%0d",rewinds-w);
  for(integer q=0;q<4;q=q+1)begin rdy_mode[q]=0;lat[q]=2;end
  // ---- B3: receiver masks (two of four, then one) ----
  repeat(2)@(negedge clk);rcv_mask=4'b0110;lease(6);send(300,0,0,3);drain();
  rcv_mask=4'b1000;lease(7);send(300,26,3,0);drain();rcv_mask=4'hf;
  // ---- C: generation wraps with a slow receiver; the wrap is refused while tickets are live ----
  lease(8);lat[2]=9;w=wrap_epochs;
  send((32<<GENW)*WRAPS+77,0,0,0);drain();lat[2]=2;
  if(wrap_epochs-w<WRAPS||wrap_epochs-w>WRAPS+1)begin $display("wrap epochs%0d expected%0d",wrap_epochs-w,WRAPS);$fatal(1,"SERVICE_ROOT FAIL");end
  $display("WRAP GENW=%0d beats=%0d wrap_epochs=%0d",GENW,(32<<GENW)*WRAPS+77,wrap_epochs-w);
  // ---- D: corrected single-bit reads (verify and publication, data and check bits, both banks) ----
  reset_dut();lease(9);
  fork
   send(64,0,0,0);
   begin
    inj_hit=0;
    for(integer e=0;e<8;e=e+1)begin
     inj_kind=e[0];inj_seq=base+4+e*5;inj_mask=0;inj_mask[(e*397+11)%2592]=1;inj_armed=1;
     while(inj_armed)@(negedge clk);
    end
   end
  join
  drain();if(inj_hit!=8)begin $display("single-bit injections%0d",inj_hit);$fatal(1,"SERVICE_ROOT FAIL");end
  $display("CORRECTED single_bit_reads=8 data exact");
  // ---- D2: corrected single-bit expected seats (verify and publication, both banks, data and owner islands) ----
  reset_dut();lease(22);
  fork
   send(128,0,0,0);
   begin
    einj_hit=0;
    for(integer e=0;e<8;e=e+1)begin
     einj_kind=e[0];einj_seq=base+5+e*14;einj_word=4'((e*5)%9);einj_mask=0;einj_mask[(e*101+7)%288]=1;einj_armed=1;
     while(einj_armed)@(negedge clk);
    end
   end
  join
  drain();if(einj_hit!=8)begin $display("single-bit expected injections%0d",einj_hit);$fatal(1,"SERVICE_ROOT FAIL");end
  $display("CORRECTED single_bit_expected_seats=8 data exact");
  // ---- negative phases ----
  reset_dut();lease(23);kb=base+10;einj_kind=0;einj_seq=kb;einj_word=4'd2;einj_mask=0;einj_mask[40]=1;einj_mask[61]=1;einj_armed=1;
  fault_expected=1;send(40,0,0,0);want_fault(2,"uncorrectable expected seat at verify");never_published(kb,"uncorrectable expected seat at verify");
  reset_dut();lease(24);kb=base+13;einj_kind=1;einj_seq=kb;einj_word=4'd8;einj_mask=0;einj_mask[150]=1;einj_mask[203]=1;einj_armed=1;
  fault_expected=1;send(40,0,0,0);want_fault(3,"uncorrectable expected seat at publication");never_published(kb,"uncorrectable expected seat at publication");
  if(einj_hit!=10)$fatal(1,"expected-seat injection missed");
  reset_dut();lease(10);kb=base+9;inj_kind=0;inj_seq=kb;inj_mask=0;inj_mask[300]=1;inj_mask[317]=1;inj_armed=1;
  fault_expected=1;send(40,0,0,0);want_fault(2,"double-bit verify read");never_published(kb,"double-bit verify read");
  reset_dut();lease(11);kb=base+12;inj_kind=1;inj_seq=kb;inj_mask=0;inj_mask[2400]=1;inj_mask[2410]=1;inj_armed=1;
  fault_expected=1;send(40,0,0,0);want_fault(3,"double-bit publication read");never_published(kb,"double-bit publication read");
  reset_dut();lease(12);kb=base+7;winj_seq=kb;winj_mask=code_delta(3,64'h20);winj_armed=1;
  fault_expected=1;send(40,0,0,0);want_fault(2,"valid-code wrong write");never_published(kb,"valid-code wrong write");
  if(winj_hit!=1)$fatal(1,"write injection missed");
  // stale ACK for a released ticket
  reset_dut();lease(13);send(20,0,0,0);drain();
  fault_expected=1;inj_ack_t=tick(base+3);inj_ack_o=own(13);inj_ack_v[1]=1;want_fault(4,"stale ACK released ticket");
  if(stale_count!=1)$fatal(1,"stale counter");
  // old-generation ACK aimed at a live slot (same bank/slot, previous generation)
  reset_dut();lease(14);lat[3]=90;send(32+6,0,0,0);
  repeat(8)@(negedge clk);
  fault_expected=1;inj_ack_t=tick(base+34)-16'd32;inj_ack_o=own(14);inj_ack_v[3]=1;want_fault(4,"old-generation ACK live slot");
  // duplicate ACK while the ticket is still live
  reset_dut();lease(15);lat[3]=90;send(6,0,0,0);repeat(30)@(negedge clk);
  if(!acked_true[base+1][0]||n_rel!=base)$fatal(1,"duplicate fixture");
  fault_expected=1;inj_ack_t=tick(base+1);inj_ack_o=own(15);inj_ack_v[0]=1;want_fault(5,"duplicate ACK");
  if(dup_count!=1)$fatal(1,"duplicate counter");
  // ACK from a receiver the beat was never issued to
  reset_dut();lease(16);rdy_mode[2]=2;tap_ready[2]=0;send(3,0,0,0);repeat(30)@(negedge clk);
  if(n_tap[0]!=base+1||n_tap[2]!=base)$fatal(1,"unissued fixture");
  fault_expected=1;inj_ack_t=tick(base);inj_ack_o=own(16);inj_ack_v[2]=1;want_fault(6,"unissued ACK");
  // right ticket, wrong owner
  reset_dut();lease(17);lat[1]=90;send(4,0,0,0);repeat(30)@(negedge clk);
  fault_expected=1;inj_ack_t=tick(base);inj_ack_o=own(18);inj_ack_v[1]=1;want_fault(7,"wrong-owner ACK");
  // owner changed on a valid beat
  reset_dut();lease(19);send(5,0,0,0);
  fault_expected=1;wr_owner=own(20);cur_oid=19;wr_v=1;wr_data=beat(n_acc);@(negedge clk);wr_v=0;
  want_fault(1,"lease changed on a valid beat");
  // control upset
  reset_dut();lease(21);send(5,0,0,0);fault_expected=1;dut.tb_upset=1;@(negedge clk);dut.tb_upset=0;
  want_fault(8,"control upset");
  $display("SERVICE_ROOT PASS GENW=%0d accepted=%0d taps=%0d",GENW,n_acc,taps_total);
  $finish;
 end
endmodule
