`timescale 1ns/1ps
`default_nettype none
// Native VM8 service root (ONE union of the 22 existing 128x256 macros; two physical banks, 2R+1W).
// Physical spec: codex-vm8-service-1013.log 2026-10-13 02:45 PT (written before this RTL).
//
// A producer beat {v1, addr7, grp7, data2048} under an opaque 192-b owner lease is
//   accepted  -> ticket {generation GENW, bank 1, slot 4} allocated (32 outstanding, alternating bank,
//                row = floor(seq / 2) mod 128; never reused before release),
//   written   -> SECDED coded into the bank row; the expected copy is kept in the bank's 9 local islands,
//   verified  -> the row is read back and compared in full against the expected copy (ECC checked),
//   published -> the row is read AGAIN (ECC, owner and padding checked) and offered, in acceptance order,
//                to the 4 receivers; each receiver has its own issued bit,
//   released  -> only after every targeted receiver returned an ACK that matches owner + ticket; the
//                release is in acceptance order (native_release / release_ticket / release_last).
// A bad ACK (stale generation, not live, duplicate, not issued, wrong owner) never sets a bit: it raises the
// sticky fault, which stops acceptance and publication (quarantine). Every check error does the same.
// The generation wrap is refused while any ticket is live or an ACK is in flight.
// The publication payload has no FIFO: when a receiver is not ready the in-flight publication reads are
// flushed and re-issued from the stalled beat (rewind).
// Owner contract: wr_owner changes only while wr_v is low and is stable two edges before wr_v. A beat
// accepted under any other owner than the registered lease raises the fault one edge later.
// Mutants (default off): MUT_SVC_TICKET_REUSE, MUT_SVC_ACK3, MUT_SVC_EARLYREL, MUT_SVC_STALE,
//   MUT_SVC_DUP, MUT_SVC_NOVERIFY, MUT_SVC_WRAP, MUT_SVC_NOQUAR, MUT_SVC_LEASE.
module vm_service_root #(parameter integer GENW=11)(
 input wire clk,rst_n,
 input wire [3:0] rcv_mask,
 input wire wr_v,output wire wr_ready,input wire [2062:0] wr_data,input wire wr_last,
 input wire [191:0] wr_owner,
 output wire [3:0] tap_v,input wire [3:0] tap_ready,output wire [2062:0] tap_data,
 output wire [191:0] tap_owner,output wire [15:0] tap_ticket,output wire tap_last,
 input wire [3:0] tap_ACK_v,input wire [4*192-1:0] tap_ACK_owner,input wire [4*16-1:0] tap_ACK_ticket,
 output reg native_release,output reg [15:0] release_ticket,output reg release_last,
 output wire drained,output reg fault,output reg [3:0] fault_code,
 output reg [15:0] stale_count,dup_count,wrap_epochs
);
 localparam integer NE=32;
 localparam [3:0] F_LEASE=1,F_VERIFY=2,F_PUB=3,F_STALE=4,F_DUP=5,F_UNISSUED=6,F_OWNER=7,F_CTRL=8;
 function automatic [4:0] idx_of(input [4:0] n);idx_of={n[0],n[4:1]};endfunction
 // ---------------- ticket table ----------------
 reg [NE-1:0] e_live,e_live_sh,e_written,e_vissued,e_verified,e_last;
 reg [GENW:0] e_gen[0:NE-1];
 reg [6:0] e_row[0:NE-1];
 reg [3:0] e_target[0:NE-1],e_issued[0:NE-1],e_acked[0:NE-1];
 reg [4:0] alloc_n,rel_n,pub_n;reg [7:0] rowseq;reg [GENW-1:0] gen_round;
 reg [5:0] count,pcount;reg wrap_pend;
 reg [3:0] vptr[0:1];
 // ---------------- lease ----------------
 reg [191:0] own_q,own_in_q;reg eq_lease_q,eq_in_q,acc_q;
 wire [4:0] a_idx=idx_of(alloc_n);
`ifdef MUT_SVC_TICKET_REUSE
 wire room=1'b1;
`else
 wire room=(count<6'd32)&&!e_live[a_idx];
`endif
 assign wr_ready=!fault&&eq_lease_q&&eq_in_q&&room&&!wrap_pend&&(rcv_mask!=0);
 wire acc=wr_v&&wr_ready;
 // ---------------- write stage ----------------
 reg w0_v,w0_bank;reg [3:0] w0_slot;reg [6:0] w0_row;reg [2062:0] w0_data;
 wire [2303:0] raw={49'b0,own_q,w0_data};
 wire [2591:0] enc[0:1];
 wire [2815:0] mem_wd={224'b0,(w0_bank?enc[1]:enc[0])}
`ifdef VM_SVC_FAULT_HOOK
  ^tb_wr_xor
`endif
  ;
 // ---------------- read requests and tags ----------------
 // tag = {v, kind (1 publication, 0 verify), seq5}; six positions: request, then five edges to the verdict
 reg [1:0] rq_v,rq_k;reg [4:0] rq_n[0:1];reg [6:0] rq_a[0:1];
 reg [1:0] t_v[1:5],t_k[1:5];reg [4:0] t_n[1:5][0:1];
 wire [2815:0] rd_bank[0:1];wire [1:0] slice_rv[0:3];
 wire [8:0] ck_valid[0:1],ck_error[0:1];wire [2303:0] ck_data[0:1];
 genvar gb,gw,gk;
 generate for(gk=0;gk<4;gk=gk+1)begin:slices
  localparam integer NM=(gk<3)?3:2;
  wire [2*NM*256-1:0] rd;
  vm_service_slice #(.NM(NM)) u_slice(.clk(clk),.rst_n(rst_n),.w_v(w0_v),.w_bank(w0_bank),.w_addr(w0_row),
   .w_data(mem_wd[gk*768+:NM*256]),.r_v(rq_v),.r_addr({rq_a[1],rq_a[0]}),.rv(slice_rv[gk]),.rd(rd));
  assign rd_bank[0][gk*768+:NM*256]=rd[0+:NM*256];
  assign rd_bank[1][gk*768+:NM*256]=rd[NM*256+:NM*256];
 end endgenerate
 generate for(gb=0;gb<2;gb=gb+1)begin:banks
  wire [2815:0] returned=rd_bank[gb]
`ifdef VM_SVC_FAULT_HOOK
   ^tb_rd_xor[gb]
`endif
   ;
  for(gw=0;gw<9;gw=gw+1)begin:words
   vm_service_wordbank #(.OWNER_BANK(gw==8?1:0)) u_wb(.clk(clk),.rst_n(rst_n),
    .expect_v(w0_v&&w0_bank==1'(gb)),.expect_slot(w0_slot),.expect_data(raw[gw*256+:256]),
    .encoded(enc[gb][gw*288+:288]),
    .capture_v(t_v[3][gb]),.check_v(t_v[4][gb]),.check_write(!t_k[3][gb]),.check_slot(t_n[3][gb][4:1]),
    .returned(returned[gw*288+:288]),
`ifdef VM_SVC_FAULT_HOOK
    .tb_exp_xor(tb_exp_word==4'(gw)?tb_exp_xor[gb]:288'b0),
`endif
    .valid(ck_valid[gb][gw]),.error(ck_error[gb][gw]),.repaired_data(ck_data[gb][gw*256+:256]));
  end
 end endgenerate
`ifdef VM_SVC_FAULT_HOOK
 // bench-only injection points (never synthesised): returned-row and written-row XOR masks, control upset
 reg [2815:0] tb_rd_xor[0:1];reg [2815:0] tb_wr_xor;reg tb_upset;
 reg [287:0] tb_exp_xor[0:1];reg [3:0] tb_exp_word; // expected-seat upset of one island
`endif
 // ---------------- scheduling ----------------
 wire [4:0] p_idx=idx_of(pub_n);
 wire [4:0] v_idx0={1'b0,vptr[0]},v_idx1={1'b1,vptr[1]};
 wire [1:0] v_elig={e_live[v_idx1]&&e_written[v_idx1]&&!e_vissued[v_idx1],
                    e_live[v_idx0]&&e_written[v_idx0]&&!e_vissued[v_idx0]};
 // ---------------- publication register ----------------
 reg p_v,p_last;reg [4:0] p_n;reg [2062:0] p_data;reg [191:0] p_owner;reg [15:0] p_ticket;
 reg [3:0] p_target,p_iss;
`ifdef MUT_SVC_NOQUAR
 wire quar=1'b0;
`else
 wire quar=fault;
`endif
 assign tap_v={4{p_v&&!quar}}&p_target&~p_iss;
 assign tap_data=p_data;assign tap_owner=p_owner;assign tap_ticket=p_ticket;assign tap_last=p_last;
 wire [3:0] hs=tap_v&tap_ready;
 wire p_free_next=!p_v||(((p_iss|hs)&p_target)==p_target);
 // verdicts (five edges after the request)
 wire [1:0] res_v=t_v[5];
 wire [1:0] res_bad={(|ck_error[1])||!(&ck_valid[1]),(|ck_error[0])||!(&ck_valid[0])};
 wire res_pub_b=res_v[1]&&t_k[5][1];
 wire res_pub=(res_v[0]&&t_k[5][0])||res_pub_b;
 wire [4:0] res_pub_n=t_n[5][res_pub_b];
 wire res_pub_bad=res_bad[res_pub_b];
 wire load_p=res_pub&&!res_pub_bad&&p_free_next&&!quar;
 wire rewind=res_pub&&!res_pub_bad&&!p_free_next&&!quar;
 wire p_elig=e_live[p_idx]&&e_verified[p_idx]&&(pcount!=0)&&!quar&&!rewind;
 wire [1:0] do_pub={p_elig&&p_idx[4],p_elig&&!p_idx[4]};
`ifdef MUT_SVC_NOVERIFY
 wire [1:0] do_ver=2'b00;
`else
 wire [1:0] do_ver=v_elig&~do_pub;
`endif
 wire [GENW-1:0] gmax={GENW{1'b1}};
 // ---------------- ACK pin stage ----------------
 reg [3:0] a_v,a_oeq;reg [15:0] a_t[0:3];
 // ---------------- release ----------------
 wire [4:0] r_idx=idx_of(rel_n);
`ifdef MUT_SVC_ACK3
 wire rel_acked=((e_acked[r_idx]|4'b1000)&e_target[r_idx])==e_target[r_idx];
`elsif MUT_SVC_EARLYREL
 wire rel_acked=1'b1;
`else
 wire rel_acked=e_acked[r_idx]==e_target[r_idx];
`endif
 wire rel_ok=(count!=0)&&e_live[r_idx]&&(e_issued[r_idx]==e_target[r_idx])&&rel_acked;
 assign drained=(count==0)&&!w0_v&&!native_release&&!p_v;
 wire lease_load=!eq_lease_q&&eq_in_q&&(count==0)&&!w0_v&&!acc;
 wire eq_in=wr_owner==own_in_q;
 integer i,r;reg [4:0] ai;reg [GENW-1:0] ag;reg [15:0] hi;reg nf;reg [3:0] nc;reg [4:0] back;
 always @(posedge clk)begin
  own_in_q<=wr_owner;
  if(lease_load)own_q<=own_in_q;
  if(acc)begin w0_data<=wr_data;w0_bank<=alloc_n[0];w0_slot<=alloc_n[4:1];w0_row<=rowseq[7:1];end
  for(i=0;i<2;i=i+1)begin
   rq_k[i]<=do_pub[i];
   rq_n[i]<=do_pub[i]?pub_n:{vptr[i],1'(i)};
   rq_a[i]<=do_pub[i]?e_row[p_idx]:e_row[i?v_idx1:v_idx0];
   t_n[1][i]<=rq_n[i];t_n[2][i]<=t_n[1][i];t_n[3][i]<=t_n[2][i];t_n[4][i]<=t_n[3][i];t_n[5][i]<=t_n[4][i];
  end
  t_k[1]<=rq_k;t_k[2]<=t_k[1];t_k[3]<=t_k[2];t_k[4]<=t_k[3];t_k[5]<=t_k[4];
  for(r=0;r<4;r=r+1)begin a_t[r]<=tap_ACK_ticket[r*16+:16];a_oeq[r]<=tap_ACK_owner[r*192+:192]==own_q;end
  if(load_p)begin
   p_n<=res_pub_n;p_data<=ck_data[res_pub_b][2062:0];p_owner<=ck_data[res_pub_b][2063+:192];
   p_last<=e_last[idx_of(res_pub_n)];p_target<=e_target[idx_of(res_pub_n)];
   p_ticket<=16'({e_gen[idx_of(res_pub_n)][GENW-1:0],idx_of(res_pub_n)});
  end
  if(rel_ok)begin release_ticket<=16'({e_gen[r_idx][GENW-1:0],r_idx});release_last<=e_last[r_idx];end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   e_live<=0;e_live_sh<=0;e_written<=0;e_vissued<=0;e_verified<=0;e_last<=0;
   alloc_n<=0;rel_n<=0;pub_n<=0;rowseq<=0;gen_round<=0;count<=0;pcount<=0;wrap_pend<=0;
   vptr[0]<=0;vptr[1]<=0;eq_lease_q<=0;eq_in_q<=0;acc_q<=0;w0_v<=0;rq_v<=0;
   for(i=1;i<=5;i=i+1)t_v[i]<=0;
   p_v<=0;p_iss<=0;a_v<=0;native_release<=0;fault<=0;fault_code<=0;stale_count<=0;dup_count<=0;wrap_epochs<=0;
   for(i=0;i<NE;i=i+1)begin e_gen[i]<=0;e_row[i]<=0;e_target[i]<=0;e_issued[i]<=0;e_acked[i]<=0;end
  end else begin
   nf=0;nc=0;
   // on the load edge own_q takes own_in_q, so the lease compare of that edge is the input compare
   eq_in_q<=eq_in;eq_lease_q<=lease_load?eq_in:(wr_owner==own_q);acc_q<=acc;
`ifndef MUT_SVC_LEASE
   if(acc_q&&!eq_lease_q)begin nf=1;nc=F_LEASE;end
`endif
   // allocation
   w0_v<=acc;
   if(acc)begin
    e_live[a_idx]<=1;e_live_sh[a_idx]<=1;e_gen[a_idx]<={^gen_round,gen_round};e_row[a_idx]<=rowseq[7:1];
    e_last[a_idx]<=wr_last;e_target[a_idx]<=rcv_mask;e_written[a_idx]<=0;e_vissued[a_idx]<=0;
`ifdef MUT_SVC_NOVERIFY
    e_verified[a_idx]<=1;
`else
    e_verified[a_idx]<=0;
`endif
    e_issued[a_idx]<=0;e_acked[a_idx]<=0;
    alloc_n<=alloc_n+5'd1;rowseq<=rowseq+8'd1;
    if(alloc_n==5'd31)begin
     gen_round<=gen_round+1'b1;
`ifndef MUT_SVC_WRAP
     if(gen_round==gmax)wrap_pend<=1;
`endif
    end
   end
   if(wrap_pend&&count==0&&!acc&&!w0_v&&a_v==0&&tap_ACK_v==0)begin wrap_pend<=0;wrap_epochs<=wrap_epochs+16'd1;end
   if(w0_v)e_written[{w0_bank,w0_slot}]<=1;
   // read issue; a rewind flushes every publication read in flight
   rq_v<=do_pub|do_ver;
   t_v[1]<=rq_v&~({2{rewind}}&rq_k);
   for(i=2;i<=5;i=i+1)t_v[i]<=t_v[i-1]&~({2{rewind}}&t_k[i-1]);
   if(do_ver[0])begin e_vissued[v_idx0]<=1;vptr[0]<=vptr[0]+4'd1;end
   if(do_ver[1])begin e_vissued[v_idx1]<=1;vptr[1]<=vptr[1]+4'd1;end
   back=pub_n-res_pub_n;
   if(rewind)begin pub_n<=res_pub_n;pcount<=pcount+{1'b0,back}+6'(acc);end
   else begin
    if(|do_pub)pub_n<=pub_n+5'd1;
    pcount<=pcount+6'(acc)-6'(|do_pub);
   end
   // verdicts
   for(i=0;i<2;i=i+1)if(res_v[i])begin
    if(res_bad[i])begin nf=1;nc=t_k[5][i]?F_PUB:F_VERIFY;end
    else if(!t_k[5][i])e_verified[idx_of(t_n[5][i])]<=1;
   end
   // publication register and per-receiver issue
   if(load_p)begin p_v<=1;p_iss<=0;end
   else begin
    if(p_free_next)p_v<=0;
    p_iss<=p_iss|hs;
   end
   if(p_v&&|hs)e_issued[idx_of(p_n)]<=p_iss|hs;
   // ACKs: one registered stage at the pins, then the table
   a_v<=tap_ACK_v;
   for(r=0;r<4;r=r+1)if(a_v[r])begin
    ai=a_t[r][4:0];ag=a_t[r][5+:GENW];hi=a_t[r]>>(5+GENW);
`ifdef MUT_SVC_STALE
    if(e_issued[ai][r]&&!e_acked[ai][r]&&a_oeq[r])e_acked[ai][r]<=1;
`else
    if(!e_live[ai]||e_gen[ai][GENW-1:0]!=ag||hi!=0)begin nf=1;nc=F_STALE;stale_count<=stale_count+16'd1;end
    else if(!a_oeq[r])begin nf=1;nc=F_OWNER;end
    else if(e_acked[ai][r])begin
`ifndef MUT_SVC_DUP
     nf=1;nc=F_DUP;
`endif
     dup_count<=dup_count+16'd1;
    end
    else if(!e_issued[ai][r]||!e_target[ai][r])begin nf=1;nc=F_UNISSUED;end
    else e_acked[ai][r]<=1;
`endif
   end
   // in-order release
   native_release<=rel_ok;
   if(rel_ok)begin
    e_live[r_idx]<=0;e_live_sh[r_idx]<=0;rel_n<=rel_n+5'd1;
    if(^e_gen[r_idx])begin nf=1;nc=F_CTRL;end
   end
   count<=count+6'(acc)-6'(rel_ok);
   // mutable control protection: live shadow, generation parity on use
   if(e_live!=e_live_sh)begin nf=1;nc=F_CTRL;end
   if(load_p&&^e_gen[idx_of(res_pub_n)])begin nf=1;nc=F_CTRL;end
`ifdef VM_SVC_FAULT_HOOK
   if(tb_upset)e_live_sh[5]<=~e_live_sh[5];
`endif
   if(nf&&!fault)begin fault<=1;fault_code<=nc;end
  end
 end
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n)begin
  if(slice_rv[0]!==t_v[3])begin $display("tag/slice valid misaligned");$fatal(1,"vm_service_root internal");end
  if(count>6'd32)$fatal(1,"vm_service_root ticket count overflow");
 end
 initial if(GENW<1||GENW>11)$fatal(1,"GENW 1..11");
`endif
endmodule
`default_nettype wire
