`timescale 1ps/1fs
`default_nettype none
// ot_hbm_index_global_order_mt: full-rate successor of ot_hbm_index_global_order (tputx-gord 2026-10-11).
// Same ports and the same per-response checks; finite TP96 merge of the ranks' published ascending candidate lists.
//
// Why: the original holds ONE outstanding provider read and re-settles an unpipelined 7-level tournament after every
// refill (12.6 cyc a read; STATIC_SCAN=1 walks all 131,072 ids: 135,815 cyc for the 704-read indexer record vs a
// 2,680.6-cyc price).  This variant runs at the provider port rate (1 read / cycle) and merges 1 tuple / cycle:
//  * per-rank 2-entry head FIFOs (leaves), refilled by up to 96 concurrent reads (at most ONE outstanding per rank, so
//    no read is ever issued past a rank's last slot, and leaf space is reserved at issue: occupancy + outstanding <= 2);
//  * read issue: 8 groups x 12 ranks (group = rank mod 8), a registered round-robin 12:1 candidate {rank, ordinal} per
//    group from registered wants only (an empty leaf's refill before a prefetch; prefetch only after every leaf has held
//    a head once; a granted group skips one cycle), one 8:1
//    round-robin grant into a registered read request (no 96-way arbitration in one cycle);
//  * responses: R1 register (rank-independent checks) -> R2 = 8 registered group copies (fanout) -> group-local check
//    of the expected ordinal for that rank (responses may return in any rank order; per rank they are in order);
//  * merge: a 7-level tree (96->48->24->12->6->3->2->1) of 2:1 merge nodes, each with a 2-entry shift FIFO; a node
//    pushes on its own registered count, so no combinational path crosses a level; 1 tuple / cycle at the root.
//    Every port carries a key: its head id, or a registered LOWER BOUND on its next id when empty (see p_key), so a
//    node emits one side while the other is empty but provably larger (no stall on in-flight refills);
//  * the root push checks strict ascending order, which catches any non-ascending rank list before it is emitted.
// Interface differences vs the original (documented): several reads may be outstanding (one per rank) and their order
// is rank-interleaved; responses are always accepted while running (a response that does not match an outstanding
// read faults instead of back-pressuring); faults are detected 1-2 edges later (always before the bad tuple leaves).
// done can precede the drain of a downstream output FIFO: the registered-boundary wrapper holds it (gen_regbound out_after).
// Benches: tools/throughput_budget/tput_gorder_mt.py (mutant = RTL text mutant on the out_tuple line).
module ot_hbm_index_global_order_mt #(parameter integer ENABLE=0)(
 input wire clk,por_n,start,output wire start_r,
 input wire [72:0] start_frame,input wire publication_complete,
 input wire owner_valid,input wire [72:0] owner_frame,
 output wire read_v,input wire read_r,output wire [72:0] read_frame,
 output wire [6:0] read_rank,output wire [16:0] read_ordinal,
 input wire rsp_v,output wire rsp_r,input wire [72:0] rsp_frame,
 input wire [6:0] rsp_rank,input wire [16:0] rsp_ordinal,
 input wire [33:0] rsp_tuple,input wire rsp_last,rsp_empty,
 output wire out_v,input wire out_r,output wire [33:0] out_tuple,
 output wire [72:0] out_frame,output wire [6:0] out_rank,
 output wire retained,output wire done,output wire fault
);
 localparam [2:0] IDLE=3'd0,RUN=3'd1,DONE=3'd2,FAULT=3'd3,ARM=3'd4;   // ARM: one clear cycle between start and RUN
 localparam integer NR=96,NG=8,GS=12,NP=192,ROOT=191;   // group g = rank[2:0], member k = rank[6:3]
 function automatic [6:0] mod96(input [16:0] id);   // id % 96 = {((id>>5) % 3), id[4:0]} (tb_hbm_gorder_mod96)
  reg [11:0] q; reg [4:0] sum; reg [1:0] r3; integer d;
  begin q=id[16:5]; sum=0; for(d=0;d<6;d=d+1) sum=sum+q[2*d+:2]; r3=sum%3; mod96={r3,id[4:0]}; end
 endfunction
 function automatic integer lvl_n(input integer l); integer k,n; begin n=NR; for(k=0;k<l;k=k+1) n=(n+1)/2; lvl_n=n; end endfunction
 function automatic integer lvl_base(input integer l); integer k,n,b;
  begin n=NR; b=0; for(k=0;k<l;k=k+1) begin b=b+n; n=(n+1)/2; end lvl_base=b; end endfunction
 function automatic [3:0] pick12(input [11:0] m,input [3:0] p);   // round robin: lowest set index >= p, else lowest
  integer k; begin pick12=0; for(k=11;k>=0;k=k-1) if(m[k]) pick12=k[3:0]; for(k=11;k>=0;k=k-1) if(m[k]&&k>=p) pick12=k[3:0]; end
 endfunction

 reg [2:0] state;
 reg [72:0] frame;
 // lease registered (73-bit compare off the handshake paths); it is valid from RUN on (frame is loaded entering ARM)
 reg lease_ok; always @(posedge clk or negedge por_n) if(!por_n) lease_ok<=1'b0; else lease_ok<=owner_valid&&owner_frame==frame;
 wire run=ENABLE&&state==RUN;
 assign start_r=ENABLE&&state==IDLE&&publication_complete&&owner_valid;
 // Record clear: per-rank / node state carries no power-on reset (no reset on the datapath, por_n fanout ~150); it is
 // cleared in the ARM cycle by 29 registered copies of the start acceptance (<= ~200 loads each):
 // clrv[2g+h] = leaves of group g (h: members 0-5 / 6-11), clrv[16+j] = merge nodes 8j..8j+7, clrv[28] = misc.
 wire start_go=ENABLE&&state==IDLE&&start&&start_r&&start_frame==owner_frame;
 wire [28:0] clrv;
 genvar ci;
 generate for(ci=0;ci<29;ci=ci+1)begin:g_clr
  ot_sc_rep_ff u_c(.clk(clk),.rst_n(por_n),.d(start_go),.q(clrv[ci]));
 end endgenerate
 wire clr=clrv[28];

 // ---------------- response path: R1 (rank-independent checks) ----------------
 assign rsp_r=run&&lease_ok;
 reg r1_v; reg [6:0] r1_rank; reg [16:0] r1_ord; reg [33:0] r1_tup; reg r1_last,r1_empty,r1_fok;
 always @(posedge clk or negedge por_n) if(!por_n) r1_v<=1'b0; else r1_v<=rsp_v&&rsp_r;
 always @(posedge clk) begin r1_rank<=rsp_rank;r1_ord<=rsp_ordinal;r1_tup<=rsp_tuple;r1_last<=rsp_last;r1_empty<=rsp_empty;
  r1_fok<=rsp_frame==frame; end
 wire [16:0] r1_id=r1_tup[33:17];
 wire r1_val=!r1_empty&&r1_tup[0];
 wire r1_bad=!r1_fok||r1_rank>=7'd96||r1_ord[16:11]!=6'd0||(r1_empty&&!r1_last)||(!r1_last&&r1_ord[10:0]>=11'd1379)||
             (r1_val&&((r1_tup[15:8]==8'hff&&|r1_tup[7:1])||mod96(r1_id)!=r1_rank||r1_id>frame[72:56]));
 // R2: 8 registered group copies (fanout tree for the 34-bit tuple into 96 leaves x 2 entries)
 reg [NG-1:0] g_v; reg [3:0] g_li[0:NG-1]; reg [10:0] g_ord[0:NG-1]; reg [33:0] g_tup[0:NG-1]; reg [NG-1:0] g_last,g_val;
 integer gi;
 always @(posedge clk or negedge por_n)
  if(!por_n) g_v<=0; else for(gi=0;gi<NG;gi=gi+1) g_v[gi]<=r1_v&&!r1_bad&&r1_rank[2:0]==gi[2:0];
 always @(posedge clk) for(gi=0;gi<NG;gi=gi+1) begin
  g_li[gi]<=r1_rank[6:3];g_ord[gi]<=r1_ord[10:0];g_tup[gi]<=r1_tup;g_last[gi]<=r1_last;g_val[gi]<=r1_val; end

 // ---------------- per-rank state, read issue, leaves ----------------
 wire [NR-1:0] want,want_hi;           // want_hi: the leaf is empty (refill before prefetch)
 wire [10:0] ordw[0:NR-1];
 wire [NG-1:0] gnt;                       // global grant to group g (its registered candidate)
 wire [NG-1:0] cand_v,cand_hi; wire [3:0] cand_li[0:NG-1]; wire [10:0] cand_ord[0:NG-1];
 wire [NG-1:0] g_mis,g_empty;           // g_empty: a non-ended leaf of the group is empty (registered)
 reg primed;                             // every leaf has held a head once: prefetch (2nd entry) allowed from then on
 always @(posedge clk or negedge por_n) if(!por_n) primed<=1'b0; else if(clr) primed<=1'b0; else if(run&&!(|g_empty)) primed<=1'b1;
                     // response to a rank without that outstanding ordinal
 // merge-tree ports: 0..95 leaves, 96..191 node outputs (191 = root)
 // p_key: the head id when the port holds one, else a LOWER BOUND on its next id (18'h3ffff = ended).  A rank's ids are
 // = rank (mod 96) and strictly ascending, so an empty leaf's next id is >= last popped + 96 (rank before any); a node
 // with an empty FIFO is bounded by min(children keys), registered (keys only grow, so a stale bound stays valid).
 // A node may then emit b while a is empty but provably larger: one entry a leaf streams at 1 tuple / cycle.
 // Any list that breaks the bound (non-ascending) makes the root order check fault.
 wire [NP-1:0] p_has,p_end,p_pop; wire [33:0] p_head[0:NP-1]; wire [17:0] p_key[0:NP-1];
 genvar g,k,l,n;
 generate for(g=0;g<NG;g=g+1)begin:g_grp
  // group-local response check (8:1 of the per-rank state)
  wire [GS-1:0] outst_g,empty_g,want_g,wanthi_g; reg gempty;
  always @(posedge clk) gempty<=|empty_g;
  assign g_empty[g]=gempty;
  wire [10:0] ord_g[0:GS-1];
  assign g_mis[g]=g_v[g]&&!(outst_g[g_li[g]]&&ord_g[g_li[g]]==g_ord[g]);
  for(k=0;k<GS;k=k+1)begin:g_rank
   localparam integer R=g+NG*k;
   reg outst,ended; reg [10:0] ord; reg [1:0] c; reg [33:0] e0,e1; reg [17:0] lb;
   wire hit=g_v[g]&&g_li[g]==k&&outst&&ord==g_ord[g];
   wire push=hit&&g_val[g];
   wire pop=p_pop[R];
   wire issue=gnt[g]&&cand_li[g]==k;
   assign outst_g[k]=outst; assign ord_g[k]=ord; assign ordw[R]=ord;
   assign want[R]=run&&!outst&&!ended&&c!=2'd2&&(primed||c==2'd0); assign want_hi[R]=want[R]&&c==2'd0;
   assign empty_g[k]=c==2'd0&&!ended; assign want_g[k]=want[R]; assign wanthi_g[k]=want_hi[R];
   assign p_has[R]=c!=2'd0; assign p_end[R]=ended&&c==2'd0; assign p_head[R]=e0;
   assign p_key[R]=(c!=2'd0)?{1'b0,e0[33:17]}:ended?18'h3ffff:lb;
   wire lclr=clrv[2*g+(k>=6)];
   always @(posedge clk)
    if(lclr)begin outst<=1'b0;ended<=1'b0;ord<=11'd0;c<=2'd0;lb<=18'(R);end
    else begin
     if(issue)outst<=1'b1;
     if(hit)begin outst<=1'b0;ord<=ord+11'd1;if(g_last[g])ended<=1'b1;end
     c<=c+{1'b0,push}-{1'b0,pop};
     if(pop)lb<={1'b0,e0[33:17]}+18'd96;
    end
   always @(posedge clk) case({push,pop})        // 2-entry shift FIFO, e0 = head (datapath: no reset)
    2'b10:if(c==2'd0)e0<=g_tup[g];else e1<=g_tup[g];
    2'b01:e0<=e1;
    2'b11:if(c==2'd1)e0<=g_tup[g];else begin e0<=e1;e1<=g_tup[g];end
    default:;
   endcase
  end
  // registered 12:1 candidate, picked from the registered wants only (no grant in the pick path); a granted group shows
  // no candidate the next cycle (its want bits then reflect the issue), so a group issues at most every other cycle
  reg cv,chi; reg [3:0] cli,gp; reg [10:0] cord;
  wire [GS-1:0] wm=want_g,wh=wanthi_g;
  wire [3:0] nli=|wh?pick12(wh,gp):pick12(wm,gp);
  always @(posedge clk or negedge por_n) if(!por_n) gp<=4'd0; else if(gnt[g]) gp<=(cli==GS-1)?4'd0:cli+4'd1;
  assign cand_v[g]=cv; assign cand_hi[g]=chi; assign cand_li[g]=cli; assign cand_ord[g]=cord;
  always @(posedge clk or negedge por_n) if(!por_n) begin cv<=1'b0;chi<=1'b0;end else begin cv<=|wm&&!clrv[2*g]&&!gnt[g];chi<=|wh&&!clrv[2*g]&&!gnt[g];end
  always @(posedge clk) begin cli<=nli; cord<=ord_g[nli]; end
 end endgenerate

 // global 8:1 round-robin grant into the registered read request
 reg rq_v; reg [6:0] rq_rank; reg [10:0] rq_ord; reg [3:0] rr;
 assign read_v=run&&lease_ok&&rq_v;
 assign read_frame=frame; assign read_rank=rq_rank; assign read_ordinal={6'd0,rq_ord};
 wire rq_free=!rq_v||(read_v&&read_r);
 reg [3:0] gsel; reg gany; integer q;
 always @* begin gany=1'b0; gsel=4'd0;
  for(q=NG-1;q>=0;q=q-1) if(cand_v[q]) begin gany=1'b1; gsel=q[3:0]; end
  for(q=NG-1;q>=0;q=q-1) if(cand_v[q]&&q>=rr) gsel=q[3:0];
  if(|cand_hi)begin                      // an empty leaf's refill goes first (round robin among those)
   for(q=NG-1;q>=0;q=q-1) if(cand_hi[q]) gsel=q[3:0];
   for(q=NG-1;q>=0;q=q-1) if(cand_hi[q]&&q>=rr) gsel=q[3:0];
  end
 end
 wire do_gnt=run&&rq_free&&gany;
 generate for(g=0;g<NG;g=g+1)begin:g_gnt assign gnt[g]=do_gnt&&gsel==g; end endgenerate
 always @(posedge clk or negedge por_n)
  if(!por_n)begin rq_v<=1'b0;rr<=4'd0;end
  else if(clr)begin rq_v<=1'b0;rr<=4'd0;end
  else if(do_gnt)begin rq_v<=1'b1;rr<=(gsel==NG-1)?4'd0:gsel+4'd1;end
  else if(read_v&&read_r)rq_v<=1'b0;
 always @(posedge clk) if(do_gnt)begin rq_rank<={cand_li[gsel],gsel[2:0]};rq_ord<=cand_ord[gsel];end

 // ---------------- merge tree ----------------
 wire root_bad;
 generate for(l=0;l<7;l=l+1)begin:g_lvl
  localparam integer NI=lvl_n(l),NO=lvl_n(l+1),IB=lvl_base(l),OB=lvl_base(l+1);
  for(n=0;n<NO;n=n+1)begin:g_node
   localparam integer A=IB+2*n,B=IB+2*n+1,O=OB+n;
   localparam integer HASB=(2*n+1<NI);
   wire a_has=p_has[A],a_end=p_end[A]; wire [33:0] ah=p_head[A];
   wire b_has=HASB?p_has[B]:1'b0,b_end=HASB?p_end[B]:1'b1; wire [33:0] bh=HASB?p_head[B]:34'd0;
   wire [17:0] ak=p_key[A],bk=HASB?p_key[B]:18'h3ffff;
   reg [1:0] c; reg [33:0] e0,e1; reg alldone; reg [17:0] bnd;
   wire space=c!=2'd2;
   wire take_a=space&&a_has&&ak<bk;
   wire take_b=space&&b_has&&bk<ak;
   wire push=take_a||take_b;
   wire [33:0] din=take_a?ah:bh;
   wire pop=p_pop[O];
   assign p_pop[A]=take_a;
   if(HASB)begin:g_popb assign p_pop[B]=take_b; end
   assign p_has[O]=c!=2'd0; assign p_end[O]=alldone&&c==2'd0; assign p_head[O]=e0;
   assign p_key[O]=(c!=2'd0)?{1'b0,e0[33:17]}:bnd;
   wire nclr=clrv[16+(O-NR)/8];
   always @(posedge clk)
    if(nclr)begin c<=2'd0;alldone<=1'b0;bnd<=18'd0;end
    else begin c<=c+{1'b0,push}-{1'b0,pop};alldone<=a_end&&b_end;bnd<=ak<bk?ak:bk;end
   always @(posedge clk) case({push,pop})
    2'b10:if(c==2'd0)e0<=din;else e1<=din;
    2'b01:e0<=e1;
    2'b11:if(c==2'd1)e0<=din;else begin e0<=e1;e1<=din;end
    default:;
   endcase
   if(O==ROOT)begin:g_root_check                   // strict ascending at the root push
    reg [16:0] last; reg last_v;
    assign root_bad=run&&push&&last_v&&din[33:17]<=last;
    always @(posedge clk or negedge por_n)
     if(!por_n) last_v<=1'b0; else if(clr) last_v<=1'b0; else if(push) last_v<=1'b1;
    always @(posedge clk) if(push) last<=din[33:17];
   end
  end
 end endgenerate

 // ---------------- output, control ----------------
 assign out_v=run&&lease_ok&&p_has[ROOT];
 assign out_tuple=p_head[ROOT];
 assign out_frame=frame; assign out_rank=mod96(out_tuple[33:17]);
 assign p_pop[ROOT]=out_v&&out_r;
 assign retained=ENABLE&&state!=IDLE;
 assign done=ENABLE&&state==DONE&&lease_ok;
 assign fault=ENABLE&&state==FAULT;
 wire any_fault=((state==RUN||state==DONE)&&!lease_ok)||(rsp_v&&state!=RUN)||(r1_v&&r1_bad)||(|g_mis)||root_bad;
 always @(posedge clk) if(start_go) frame<=start_frame;
 always @(posedge clk or negedge por_n)
  if(!por_n)state<=IDLE;
  else if(ENABLE)begin
   if(state!=FAULT&&any_fault)state<=FAULT;
   else case(state)
    IDLE:if(start&&start_r)begin
     if(start_frame!=owner_frame)state<=FAULT;
     else state<=ARM;
    end
    ARM:state<=RUN;
    RUN:if(p_end[ROOT])state<=DONE;
    DONE:state<=IDLE;
    default:state<=FAULT;
   endcase
  end
endmodule
`default_nettype wire
