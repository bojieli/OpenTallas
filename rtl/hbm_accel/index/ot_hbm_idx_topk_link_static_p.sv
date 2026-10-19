`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// ot_hbm_idx_topk_link_static_p : PIPELINED SUCCESSOR of ot_hbm_idx_topk_link_static (HBM-IDXPIPE 2026-10-18).
//
// Why: the historical core packs up to 64 chosen records into a 4,608-b carry at a RUNTIME offset (fill) and
// writes up to 8 flits at RUNTIME banks in ONE edge (42-level pack/carry chain, 4,096-b runtime part-select,
// ~7k-load select nets): hidx_link_pr could never close at 833 ps.
//
// Function (unchanged, exact): every ingest edge carries 64 lanes (selected_line lane j at bit j*37: valid,
// score16, id20). The chosen records of a frame are packed in arrival order (lane order inside an edge) into 64
// flits of 8 records; flit f goes to bank f%8, row f/8 of eight real 64x512 SRAMs. 16 four-flit emit beats read
// them back as the old core does. Faults: identical conditions to the old core.
//
// Structure (fixed latency, no ready/credits, no stalls; every stage is a plain register):
//   S1  lane mask + payload (36 b); compaction inside each 8-lane group (one-hot prefix select); pair merge.
//   S2  merge pairs -> 2 x 32 slots (barrel shift by the left count, 5 constant-shift mux levels).
//   S3  merge halves -> C[64 slots], count c (6 constant-shift mux levels).
//   S4  LOOP stage (the only recurrence, 10-b adder): total += c.  C is rotated by total mod 64 into the
//       64-slot record ring (slot p = bank p/8, flit slot p%8), plus its 64-b slot mask.  Fault checks here.
//   S5  write formation: bank b is written iff its flit completes in this beat; flit slots that were filled
//       by EARLIER beats (first touched bank only, slots < fill) come from the ring register W, all others
//       from the rotated beat. W keeps the beat's slots for the next beats. Write port fully registered.
//   SRAM write is captured 5 edges after the historical core's; every control input (clear/flush/emit/group/
//   rank/gbase) is delayed in a fixed shift register so the core sees exactly the historical relative timeline
//   (checks at the S4 tap = +3, SRAM read at the +5 tap). Every output (tx_v/tx/fault/selected_count) is
//   exactly the historical output +5 edges. Calendar: tools/hbm_idx_static_calendar.py --link-pipe 5.
// One clock root: clk clocks every pin flop, core flop and all 8 SRAMs (clk_mem ports kept, unloaded; same PLL
// phase 0, as idx_q 1a7a712ce / idx_sel 6c9f86511). Datapath registers are not reset; control is.
// AD-HBM-IDXK r2 (10-18 22:50, gate g4p FAIL classified: post-CTS reg->reg -446 ps = ingest_r -> s1_pm, a 1-flop
// broadcast into all 64 lane masks (~700 ps of buffer chain), and total[5:0] (~7k loads: every rotate mux)):
//   * the S1 lane mask is the lane valid bit only; ingest_v rides s1_v..s4_v. Exact: every use of a beat's counts or
//     records (total, faults, ring W, bank writes) is already qualified by s3_v/s4_v.
//   * the rotate selects come from 16 kept region copies of total[5:0] (trep, each 4 slots x 36 b per shift stage),
//     loaded from the same next-state as total. No function or latency change (outputs still historical +5).
// HBM-TOPKLINK r3 (10-19, route hidx_link_g4p-g4p-c94204038 NEEDS_RTL TT -78.45 / FF -30.81 classified): TT = 506 endpoints
//   line_r lane-valid pin flop -> s1_pm (one valid flop = INVx1 275 ps into the whole group's compaction + pair merge,
//   14 levels, 0 ps at GRT) + 8 s4_fill -> wd_r (fill fanout); FF = wd_r -> SRAM wd_in (macro own spine leaf +75 ps).
//   RTL (no latency / function change; outputs still historical +5):
//   * S1 = per-group compaction only, from 4 kept pin-flop copies of each lane valid bit (2 slots per copy);
//     group counts and pair counts registered with kept region copies (s1_nac / s1_nqc).
//   * S2 = pair merge + quad merge, every shift select from a register (merge NC region copies).
//   * S5 ring-W slot selects from per-bank kept copies of fill / f0[2:0].
// MUT (bench only): 1 record halves swapped (emit side), 2 flit sequence header, 3 carry slots from the beat instead of W,
//                   4 emit read tap one edge early (latency mutant).
// ---------------------------------------------------------------------------------------------------------------
// Fixed-age cyclic storage: payload never shifts between adjacent delay registers.
// FIELD is deliberately unique per field bank; physical mapping must retain those banks.
(* keep_hierarchy *) module ot_hbm_idx_link_control_ring #(
 parameter integer W=8, parameter integer FIELD=0, parameter integer RESET_PAYLOAD=0
)(input wire clk,rst_n,input wire[W-1:0]din,
 output reg[W-1:0]age3,age4,age5);
 (* keep *) reg[4:0]wp;
 (* keep *) reg[W-1:0]slots[0:4];
 always @(posedge clk or negedge rst_n)
  if(!rst_n)wp<=5'b00001;else wp<={wp[3:0],wp[4]};
 genvar k;
 for(k=0;k<5;k=k+1)begin:slot
  if(RESET_PAYLOAD)begin:r
   always @(posedge clk or negedge rst_n)
    if(!rst_n)slots[k]<=0;else if(wp[k])slots[k]<=din;
  end else begin:n
   always @(posedge clk)if(wp[k])slots[k]<=din;
  end
 end
 integer i;
 always @*begin
  age3=0;age4=0;age5=0;
  for(i=0;i<5;i=i+1)begin
   age3=age3|({W{wp[i]}}&slots[(i+2)%5]);
   age4=age4|({W{wp[i]}}&slots[(i+1)%5]);
   age5=age5|({W{wp[i]}}&slots[i]);
  end
 end
endmodule

module ot_hbm_idx_link_p_merge #(parameter integer NA=8,parameter integer NB=8,parameter integer CW=4,
                                 parameter integer RW=36,parameter integer NC=1)(
 input wire[NA*RW-1:0]a,input wire[NC*CW-1:0]na,input wire[NB*RW-1:0]b,output wire[(NA+NB)*RW-1:0]y
);
 // y = a | (b shifted up by na slots). Slots of a at/above na are zero by construction.
 // NC identical region copies of na (r3): stage i output slot q uses copy (q*NC)/N, so each select bit drives N/NC slots.
 localparam integer N=NA+NB,W=N*RW;
 wire[(CW+1)*W-1:0]st;
 assign st[0+:W]={{(NA*RW){1'b0}},b};
 genvar i,q;
 for(i=0;i<CW;i=i+1)begin:sh
  for(q=0;q<N;q=q+1)begin:sl
   localparam integer C=(q*NC)/N;
   localparam integer SH=(1<<i);
   if(q>=SH)begin:mv
    assign st[(i+1)*W+q*RW+:RW]=na[C*CW+i]?st[i*W+(q-SH)*RW+:RW]:st[i*W+q*RW+:RW];
   end else begin:lo
    assign st[(i+1)*W+q*RW+:RW]=na[C*CW+i]?{RW{1'b0}}:st[i*W+q*RW+:RW];
   end
  end
 end
 assign y=st[CW*W+:W]|{{(NB*RW){1'b0}},a};
endmodule

module ot_hbm_idx_link_p_rot #(parameter integer N=64,parameter integer RW=36,parameter integer SW=6,parameter integer NC=1)(
 input wire[N*RW-1:0]x,input wire[NC*SW-1:0]s,output wire[N*RW-1:0]y
);
 // rotate up by s slots: y slot p = x slot (p-s) mod N. Stage i output slot p uses select copy p*NC/N (NC identical
 // region copies of s, so each select bit drives N/NC slots x RW muxes per stage).
 localparam integer W=N*RW;
 wire[(SW+1)*W-1:0]st;
 assign st[0+:W]=x;
 genvar i,p;
 for(i=0;i<SW;i=i+1)begin:rt
  for(p=0;p<N;p=p+1)begin:sl
   localparam integer C=(p*NC)/N;
   localparam integer PS=(p+N-((1<<i)%N))%N;
   assign st[(i+1)*W+p*RW+:RW]=s[C*SW+i]?st[i*W+PS*RW+:RW]:st[i*W+p*RW+:RW];
  end
 end
 assign y=st[SW*W+:W];
endmodule

module ot_hbm_idx_topk_link_static_p_core #(parameter integer MUT=0,parameter integer SAFE_RING=0)(
 input wire clk,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,input wire[4*64-1:0]lane_vc,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output wire fault,output wire[9:0]selected_count
);
 localparam integer RW=36;
 function automatic [3:0] pc8(input [7:0] x);
  integer t;begin pc8=4'd0;for(t=0;t<8;t=t+1)pc8=pc8+{3'd0,x[t]};end
 endfunction
 genvar j,g,s,p,b,q;
 // ---------------- control delay line: tap 3 = S4 loop stage, tap 5 = SRAM read stage
 localparam integer RT=(MUT==4)?3:4;
 wire clr3,fl3,em3,em5;
 wire[7:0]rk3,gb3,rk5,gb5;wire[3:0]grp5;
 generate if(SAFE_RING)begin:g_control_ring
  wire[2:0]c3,c4,c5;wire[3:0]g3,g4,g5;
  wire[7:0]r3,r4,r5,b3,b4,b5;
  ot_hbm_idx_link_control_ring #(.W(3),.FIELD(0),.RESET_PAYLOAD(1)) ctl
   (.clk(clk),.rst_n(rst_n),.din({emit_v,flush,clear}),.age3(c3),.age4(c4),.age5(c5));
  ot_hbm_idx_link_control_ring #(.W(4),.FIELD(1)) group_id
   (.clk(clk),.rst_n(rst_n),.din(emit_group),.age3(g3),.age4(g4),.age5(g5));
  ot_hbm_idx_link_control_ring #(.W(8),.FIELD(2)) rank_id
   (.clk(clk),.rst_n(rst_n),.din(rank),.age3(r3),.age4(r4),.age5(r5));
  ot_hbm_idx_link_control_ring #(.W(8),.FIELD(3)) base_id
   (.clk(clk),.rst_n(rst_n),.din(gbase),.age3(b3),.age4(b4),.age5(b5));
  assign {em3,fl3,clr3}=c3;
  assign rk3=r3;assign gb3=b3;
  assign em5=(MUT==4)?c4[2]:c5[2];
  assign grp5=(MUT==4||MUT==5)?g4:g5;
  assign rk5=(MUT==4)?r4:r5;assign gb5=(MUT==4)?b4:b5;
 end else begin:g_control_shift
  reg[4:0]clr_d,fl_d,em_d;
  reg[19:0]grp_d;reg[39:0]rk_d,gb_d;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin clr_d<=0;fl_d<=0;em_d<=0;end
   else begin clr_d<={clr_d[3:0],clear};fl_d<={fl_d[3:0],flush};em_d<={em_d[3:0],emit_v};end
  end
  always @(posedge clk)begin grp_d<={grp_d[15:0],emit_group};rk_d<={rk_d[31:0],rank};gb_d<={gb_d[31:0],gbase};end
  assign clr3=clr_d[2];assign fl3=fl_d[2];assign em3=em_d[2];
  assign rk3=rk_d[23:16];assign gb3=gb_d[23:16];
  assign em5=em_d[RT];assign grp5=grp_d[RT*4+:4];assign rk5=rk_d[RT*8+:8];assign gb5=gb_d[RT*8+:8];
 end endgenerate
 // ---------------- S1 (r3: per-group compaction only; counts registered)
 // lane_vc = 4 kept pin-flop copies of the 64 lane valid bits (copy c at [c*64+j]; copy 0 = line_r[j*37]).
 // Copy c drives slots 2c/2c+1 of every group (its own prefix counts), copy 0 also the group / pair counts.
 wire[64*RW-1:0]pay;
 for(j=0;j<64;j=j+1)begin:ln
  assign pay[j*RW+:RW]={selected_line[j*37+17+:20],selected_line[j*37+1+:16]};
 end
 wire[8*8*RW-1:0]gc;wire[8*4-1:0]gcnt;
 for(g=0;g<8;g=g+1)begin:grp
  assign gcnt[g*4+:4]=pc8(lane_vc[g*8+:8]);
  for(s=0;s<8;s=s+1)begin:sl
   wire[7:0]gm=lane_vc[(s/2)*64+g*8+:8];
   reg[RW-1:0]v;integer k;
   always @*begin
    v={RW{1'b0}};
    for(k=s;k<8;k=k+1)if(gm[k]&&pc8(gm&((8'd1<<k)-8'd1))==4'(s))v=v|pay[(g*8+k)*RW+:RW];
   end
   assign gc[(g*8+s)*RW+:RW]=v;
  end
 end
 wire[4*5-1:0]pcnt;
 for(p=0;p<4;p=p+1)begin:pc
  assign pcnt[p*5+:5]={1'b0,gcnt[(2*p)*4+:4]}+{1'b0,gcnt[(2*p+1)*4+:4]};
 end
 // registered counts + kept region copies of the merge selects (S2 pair merge: count of group 2p, 4 copies per pair;
 // S2 quad merge: count of pair 2q, 8 copies per quad)
 reg s1_v;reg[8*8*RW-1:0]s1_gc;reg[4*5-1:0]s1_pcnt;
 (* keep *) reg[4*4*4-1:0]s1_nac;              // pair p copy c at [(p*4+c)*4]
 (* keep *) reg[2*8*5-1:0]s1_nqc;              // quad q copy c at [(q*8+c)*5]
 // ---------------- S2 (pair merge + quad merge, every select from a register)
 wire[4*16*RW-1:0]pm;
 for(p=0;p<4;p=p+1)begin:pair
  ot_hbm_idx_link_p_merge #(.NA(8),.NB(8),.CW(4),.RW(RW),.NC(4)) mg(.a(s1_gc[(2*p)*8*RW+:8*RW]),.na(s1_nac[p*16+:16]),
   .b(s1_gc[(2*p+1)*8*RW+:8*RW]),.y(pm[p*16*RW+:16*RW]));
 end
 wire[2*32*RW-1:0]qm;wire[2*6-1:0]qcnt;
 for(p=0;p<2;p=p+1)begin:quad
  ot_hbm_idx_link_p_merge #(.NA(16),.NB(16),.CW(5),.RW(RW),.NC(8)) mg(.a(pm[(2*p)*16*RW+:16*RW]),.na(s1_nqc[p*40+:40]),
   .b(pm[(2*p+1)*16*RW+:16*RW]),.y(qm[p*32*RW+:32*RW]));
  assign qcnt[p*6+:6]={1'b0,s1_pcnt[(2*p)*5+:5]}+{1'b0,s1_pcnt[(2*p+1)*5+:5]};
 end
 reg s2_v;reg[2*32*RW-1:0]s2_qm;reg[2*6-1:0]s2_qcnt;
 // ---------------- S3
 wire[64*RW-1:0]cm;
 ot_hbm_idx_link_p_merge #(.NA(32),.NB(32),.CW(6),.RW(RW)) mh(.a(s2_qm[0+:32*RW]),.na(s2_qcnt[0+:6]),
  .b(s2_qm[32*RW+:32*RW]),.y(cm));
 wire[6:0]ccnt={1'b0,s2_qcnt[0+:6]}+{1'b0,s2_qcnt[6+:6]};
 reg s3_v;reg[64*RW-1:0]s3_c;reg[6:0]s3_n;
 // ---------------- S4 (loop)
 reg[9:0]total;reg fault_c;
 wire[9:0]total_nx=s3_v?(total+{3'd0,s3_n}):(clr3?10'd0:total);
 (* keep *) reg[16*6-1:0]trep;                 // r2: 16 region copies of total[5:0] for the rotate selects
 wire[2:0]fill=total[2:0];
 wire[6:0]f0=total[9:3];
 wire[6:0]nsum={4'd0,fill}+s3_n;
 wire[64*RW-1:0]rot;
 ot_hbm_idx_link_p_rot #(.N(64),.RW(RW),.SW(6),.NC(16)) rr(.x(s3_c),.s(trep),.y(rot));
 wire[63:0]mk0=(s3_n[6])?{64{1'b1}}:((64'd1<<s3_n[5:0])-64'd1);
 wire[63:0]mk;
 ot_hbm_idx_link_p_rot #(.N(64),.RW(1),.SW(6),.NC(1)) rm(.x(mk0),.s(trep[0+:6]),.y(mk));
 reg s4_v;reg[64*RW-1:0]s4_r;reg[63:0]s4_m;reg[2:0]s4_fill;reg[3:0]s4_nf;reg[6:0]s4_f0;
 (* keep *) reg[8*3-1:0]s4_fillc,s4_f0c;      // r3: per-bank copies of fill / f0[2:0] for the ring-W slot selects
 // ---------------- S5 (write formation) + ring register W
 reg[64*RW-1:0]wr;
 wire[7:0]we_c;wire[47:0]wa_c;wire[8*288-1:0]wd_c;
 for(b=0;b<8;b=b+1)begin:wb
  wire[2:0]k=3'(b)-s4_f0[2:0];
  wire[7:0]fr={1'b0,s4_f0}+{5'd0,k};
  assign we_c[b]=s4_v&&({1'b0,k}<s4_nf);
  assign wa_c[b*6+:6]={1'b0,fr[7:3]};
  for(q=0;q<8;q=q+1)begin:wq
   wire old=(MUT!=3)&&(s4_f0c[b*3+:3]==3'(b))&&(3'(q)<s4_fillc[b*3+:3]);
   assign wd_c[b*288+q*RW+:RW]=old?wr[(b*8+q)*RW+:RW]:s4_r[(b*8+q)*RW+:RW];
  end
 end
 reg[7:0]we_r;reg[47:0]wa_r;reg[8*288-1:0]wd_r;
 // ---------------- registers
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin s1_v<=0;s2_v<=0;s3_v<=0;s4_v<=0;we_r<=0;total<=0;trep<=0;fault_c<=0;end
  else begin
   s1_v<=ingest_v;s2_v<=s1_v;s3_v<=s2_v;s4_v<=s3_v;we_r<=we_c;
   total<=total_nx;trep<={16{total_nx[5:0]}};
   if(s3_v)begin
    if({1'b0,total}+{4'd0,s3_n}>11'd512)fault_c<=1;
   end
   if(em3&&rk3<gb3)fault_c<=1;
   if(fl3&&total!=10'd512)fault_c<=1;
   if((clr3&&s3_v)||(em3&&(s3_v||f0!=7'd64)))fault_c<=1;
  end
 end
 integer pp;
 always @(posedge clk)begin
  s1_gc<=gc;s1_pcnt<=pcnt;
  for(pp=0;pp<4;pp=pp+1)s1_nac[pp*16+:16]<={4{gcnt[(2*pp)*4+:4]}};
  for(pp=0;pp<2;pp=pp+1)s1_nqc[pp*40+:40]<={8{pcnt[(2*pp)*5+:5]}};
  s2_qm<=qm;s2_qcnt<=qcnt;
  s3_c<=cm;s3_n<=ccnt;
  s4_r<=rot;s4_m<=mk&{64{s3_v}};s4_fill<=fill;s4_nf<=nsum[6:3];s4_f0<=f0;
  s4_fillc<={8{fill}};s4_f0c<={8{f0[2:0]}};
  for(pp=0;pp<64;pp=pp+1)if(s4_v&&s4_m[pp])wr[pp*RW+:RW]<=s4_r[pp*RW+:RW];
  wa_r<=wa_c;wd_r<=wd_c;
 end
 // ---------------- SRAM banks (one clock root) + emit read (historical logic at the +5 tap)
 wire[4095:0]rd;
 for(b=0;b<8;b=b+1)begin:gm
  wire re=em5&&(b/4==int'(grp5[0]));
  ot_sram_1r1w_64x512_m1_r2c2 mem(.clk(clk),.r_ce_in(re),.r_addr_in({3'd0,grp5[3:1]}),.rd_out(rd[b*512+:512]),
   .w_ce_in(we_r[b]),.w_addr_in(wa_r[b*6+:6]),.wd_in({224'd0,wd_r[b*288+:288]}),.w_mask_in({512{1'b1}}),
   .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
 end
 reg read_v;reg[3:0]read_group;reg[7:0]read_rank,read_gbase;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin read_v<=0;tx_v<=0;end
  else begin read_v<=em5;tx_v<={4{read_v}};end
 end
 // SRAM word layout (physical): slot q record {id20,score16} at [q*36+:36], bits 0..287 live, 288..511 written 0.
 // wd_in[0..265] are the macro's W-face pins (the core side); only slot 7's upper 22 bits use E-face pins
 // [266..287]; [288..511] and w_mask are constants at the E face. The emitted flit is the historical layout:
 // slot q low word {score16,16'd0} at [q*32], high word {12'd0,id20} at [256+q*32] (MUT 1 swaps them).
 function automatic [511:0] flit(input [287:0] w);
  integer t;begin
   flit=512'd0;
   for(t=0;t<8;t=t+1)begin
    flit[t*32+:32]=(MUT==1)?{12'd0,w[t*36+16+:20]}:{w[t*36+:16],16'd0};
    flit[256+t*32+:32]=(MUT==1)?{w[t*36+:16],16'd0}:{12'd0,w[t*36+16+:20]};
   end
  end
 endfunction
 integer l;
 always @(posedge clk)begin
  read_group<=grp5;read_rank<=rk5;read_gbase<=gb5;
  for(l=0;l<4;l=l+1)if(read_v)begin
   tx[l*545+:545]<={1'b1,8'hff,read_rank,16'((int'(read_rank)-int'(read_gbase))*64+int'(read_group)*4+l),flit(rd[(int'(read_group[0])*4+l)*512+:288])};
   if(MUT==2)tx[l*545+512+:16]<=16'((int'(read_rank)-int'(read_gbase))*64+int'(read_group)*4+l)^16'd1;
  end
 end
 // fault / count: +3 at S4, two more edges so every output is the historical output +5
 reg[1:0]fault_d;reg[9:0]cnt_d1,cnt_d2;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin fault_d<=0;cnt_d1<=0;cnt_d2<=0;end
  else begin fault_d<={fault_d[0],fault_c};cnt_d1<=total;cnt_d2<=cnt_d1;end
 end
 assign fault=fault_d[1];
 assign selected_count=cnt_d2;
endmodule
`default_nettype wire
`default_nettype none
// PIN-REGISTERED TILE (owner rule 19:50 PT 10-15): die master ot_hbm_idx_topk_link_static_p. Every data input and
// every output passes ONE kept flop at the pin (+1/+1 edge, as the historical shell); rst_n enters a 2-flop release
// synchroniser on clk. Port list identical to ot_hbm_idx_topk_link_static (drop-in); outputs = historical +5 edges.
module ot_hbm_idx_topk_link_static_p #(parameter integer MUT=0,parameter integer SAFE_RING=0)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output reg fault,output reg[9:0]selected_count
);
 (* keep *) reg [1:0] rst_sync;
 always @(posedge clk or negedge rst_n) if(!rst_n) rst_sync<=2'b00; else rst_sync<={rst_sync[0],1'b1};
 wire rst_core_n=rst_sync[1];
 (* keep *) reg clear_r,ingest_r,flush_r,emit_r;(* keep *) reg[2367:0]line_r;(* keep *) reg[3:0]group_r;(* keep *) reg[7:0]rank_r,gbase_r;
 // r3: three more kept pin flops per lane valid bit (selected_line[j*37]); with line_r they are the 4 copies the S1
 // compaction slots use (each copy drives 2 of the 8 slots of its group), so no single valid flop fans into a whole group.
 (* keep *) reg[3*64-1:0]vrep;
 wire[4*64-1:0]lane_vc;
 genvar gj;
 for(gj=0;gj<64;gj=gj+1)begin:lv
  assign lane_vc[gj]=line_r[gj*37];
  assign lane_vc[64+gj]=vrep[gj];
  assign lane_vc[128+gj]=vrep[64+gj];
  assign lane_vc[192+gj]=vrep[128+gj];
 end
 integer vj;
 wire[3:0]c_tx_v;wire[2179:0]c_tx;wire c_fault;wire[9:0]c_count;
 always @(posedge clk)begin
  clear_r<=clear;ingest_r<=ingest_v;line_r<=selected_line;flush_r<=flush;emit_r<=emit_v;group_r<=emit_group;rank_r<=rank;gbase_r<=gbase;
  for(vj=0;vj<64;vj=vj+1)begin vrep[vj]<=selected_line[vj*37];vrep[64+vj]<=selected_line[vj*37];vrep[128+vj]<=selected_line[vj*37];end
  tx_v<=c_tx_v;tx<=c_tx;fault<=c_fault;selected_count<=c_count;
 end
 ot_hbm_idx_topk_link_static_p_core #(.MUT(MUT),.SAFE_RING(SAFE_RING)) core(.clk(clk),.rst_n(rst_core_n),.clear(clear_r),.ingest_v(ingest_r),
  .selected_line(line_r),.lane_vc(lane_vc),.flush(flush_r),.emit_v(emit_r),.emit_group(group_r),.rank(rank_r),.gbase(gbase_r),
  .tx_v(c_tx_v),.tx(c_tx),.fault(c_fault),.selected_count(c_count));
endmodule
`default_nettype wire
