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
// MUT (bench only): 1 record halves swapped (emit side), 2 flit sequence header, 3 carry slots from the beat instead of W,
//                   4 emit read tap one edge early (latency mutant).
// ---------------------------------------------------------------------------------------------------------------
module ot_hbm_idx_link_p_merge #(parameter integer NA=8,parameter integer NB=8,parameter integer CW=4,
                                 parameter integer RW=36)(
 input wire[NA*RW-1:0]a,input wire[CW-1:0]na,input wire[NB*RW-1:0]b,output wire[(NA+NB)*RW-1:0]y
);
 // y = a | (b shifted up by na slots). Slots of a at/above na are zero by construction.
 localparam integer N=NA+NB,W=N*RW;
 wire[(CW+1)*W-1:0]st;
 assign st[0+:W]={{(NA*RW){1'b0}},b};
 genvar i;
 for(i=0;i<CW;i=i+1)begin:sh
  assign st[(i+1)*W+:W]=na[i]?(st[i*W+:W]<<((1<<i)*RW)):st[i*W+:W];
 end
 assign y=st[CW*W+:W]|{{(NB*RW){1'b0}},a};
endmodule

module ot_hbm_idx_link_p_rot #(parameter integer N=64,parameter integer RW=36,parameter integer SW=6)(
 input wire[N*RW-1:0]x,input wire[SW-1:0]s,output wire[N*RW-1:0]y
);
 localparam integer W=N*RW;
 wire[(SW+1)*W-1:0]st;
 assign st[0+:W]=x;
 genvar i;
 for(i=0;i<SW;i=i+1)begin:rt
  localparam integer K=(1<<i)*RW;
  assign st[(i+1)*W+:W]=s[i]?{st[i*W+:W-K],st[i*W+W-K+:K]}:st[i*W+:W];
 end
 assign y=st[SW*W+:W];
endmodule

module ot_hbm_idx_topk_link_static_p_core #(parameter integer MUT=0)(
 input wire clk,input wire rst_n,
 input wire clear,ingest_v,input wire[2367:0]selected_line,
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
 reg[4:0]clr_d,fl_d,em_d;
 reg[19:0]grp_d;reg[39:0]rk_d,gb_d;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin clr_d<=0;fl_d<=0;em_d<=0;end
  else begin clr_d<={clr_d[3:0],clear};fl_d<={fl_d[3:0],flush};em_d<={em_d[3:0],emit_v};end
 end
 always @(posedge clk)begin grp_d<={grp_d[15:0],emit_group};rk_d<={rk_d[31:0],rank};gb_d<={gb_d[31:0],gbase};end
 wire clr3=clr_d[2],fl3=fl_d[2],em3=em_d[2];
 wire[7:0]rk3=rk_d[23:16],gb3=gb_d[23:16];
 localparam integer RT=(MUT==4)?3:4;            // read tap index (4 = 5 edges)
 wire em5=em_d[RT];wire[3:0]grp5=grp_d[RT*4+:4];wire[7:0]rk5=rk_d[RT*8+:8],gb5=gb_d[RT*8+:8];
 // ---------------- S1
 wire[63:0]m;wire[64*RW-1:0]pay;
 for(j=0;j<64;j=j+1)begin:ln
  assign m[j]=ingest_v&selected_line[j*37];
  assign pay[j*RW+:RW]={selected_line[j*37+17+:20],selected_line[j*37+1+:16]};
 end
 wire[8*8*RW-1:0]gc;wire[8*4-1:0]gcnt;
 for(g=0;g<8;g=g+1)begin:grp
  wire[7:0]gm=m[g*8+:8];
  wire[8*3-1:0]pre;
  for(j=0;j<8;j=j+1)begin:pr
   assign pre[j*3+:3]=3'(pc8(gm&((8'd1<<j)-8'd1)));
  end
  assign gcnt[g*4+:4]=pc8(gm);
  for(s=0;s<8;s=s+1)begin:sl
   reg[RW-1:0]v;integer k;
   always @*begin
    v={RW{1'b0}};
    for(k=s;k<8;k=k+1)if(gm[k]&&pre[k*3+:3]==3'(s))v=v|pay[(g*8+k)*RW+:RW];
   end
   assign gc[(g*8+s)*RW+:RW]=v;
  end
 end
 wire[4*16*RW-1:0]pm;wire[4*5-1:0]pcnt;
 for(p=0;p<4;p=p+1)begin:pair
  ot_hbm_idx_link_p_merge #(.NA(8),.NB(8),.CW(4),.RW(RW)) mg(.a(gc[(2*p)*8*RW+:8*RW]),.na(gcnt[(2*p)*4+:4]),
   .b(gc[(2*p+1)*8*RW+:8*RW]),.y(pm[p*16*RW+:16*RW]));
  assign pcnt[p*5+:5]={1'b0,gcnt[(2*p)*4+:4]}+{1'b0,gcnt[(2*p+1)*4+:4]};
 end
 reg s1_v;reg[4*16*RW-1:0]s1_pm;reg[4*5-1:0]s1_pcnt;
 // ---------------- S2
 wire[2*32*RW-1:0]qm;wire[2*6-1:0]qcnt;
 for(p=0;p<2;p=p+1)begin:quad
  ot_hbm_idx_link_p_merge #(.NA(16),.NB(16),.CW(5),.RW(RW)) mg(.a(s1_pm[(2*p)*16*RW+:16*RW]),.na(s1_pcnt[(2*p)*5+:5]),
   .b(s1_pm[(2*p+1)*16*RW+:16*RW]),.y(qm[p*32*RW+:32*RW]));
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
 wire[2:0]fill=total[2:0];
 wire[6:0]f0=total[9:3];
 wire[6:0]nsum={4'd0,fill}+s3_n;
 wire[64*RW-1:0]rot;
 ot_hbm_idx_link_p_rot #(.N(64),.RW(RW),.SW(6)) rr(.x(s3_c),.s(total[5:0]),.y(rot));
 wire[63:0]mk0=(s3_n[6])?{64{1'b1}}:((64'd1<<s3_n[5:0])-64'd1);
 wire[63:0]mk;
 ot_hbm_idx_link_p_rot #(.N(64),.RW(1),.SW(6)) rm(.x(mk0),.s(total[5:0]),.y(mk));
 reg s4_v;reg[64*RW-1:0]s4_r;reg[63:0]s4_m;reg[2:0]s4_fill;reg[3:0]s4_nf;reg[6:0]s4_f0;
 // ---------------- S5 (write formation) + ring register W
 reg[64*RW-1:0]wr;
 wire[7:0]we_c;wire[47:0]wa_c;wire[8*288-1:0]wd_c;
 for(b=0;b<8;b=b+1)begin:wb
  wire[2:0]k=3'(b)-s4_f0[2:0];
  wire[7:0]fr={1'b0,s4_f0}+{5'd0,k};
  assign we_c[b]=s4_v&&({1'b0,k}<s4_nf);
  assign wa_c[b*6+:6]={1'b0,fr[7:3]};
  for(q=0;q<8;q=q+1)begin:wq
   wire old=(MUT!=3)&&(s4_f0[2:0]==3'(b))&&(3'(q)<s4_fill);
   assign wd_c[b*288+q*RW+:RW]=old?wr[(b*8+q)*RW+:RW]:s4_r[(b*8+q)*RW+:RW];
  end
 end
 reg[7:0]we_r;reg[47:0]wa_r;reg[8*288-1:0]wd_r;
 // ---------------- registers
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin s1_v<=0;s2_v<=0;s3_v<=0;s4_v<=0;we_r<=0;total<=0;fault_c<=0;end
  else begin
   s1_v<=ingest_v;s2_v<=s1_v;s3_v<=s2_v;s4_v<=s3_v;we_r<=we_c;
   if(clr3)total<=0;
   if(s3_v)begin
    total<=total+{3'd0,s3_n};
    if({1'b0,total}+{4'd0,s3_n}>11'd512)fault_c<=1;
   end
   if(em3&&rk3<gb3)fault_c<=1;
   if(fl3&&total!=10'd512)fault_c<=1;
   if((clr3&&s3_v)||(em3&&(s3_v||f0!=7'd64)))fault_c<=1;
  end
 end
 integer pp;
 always @(posedge clk)begin
  s1_pm<=pm;s1_pcnt<=pcnt;
  s2_qm<=qm;s2_qcnt<=qcnt;
  s3_c<=cm;s3_n<=ccnt;
  s4_r<=rot;s4_m<=mk&{64{s3_v}};s4_fill<=fill;s4_nf<=nsum[6:3];s4_f0<=f0;
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
module ot_hbm_idx_topk_link_static_p #(parameter integer MUT=0)(
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
 wire[3:0]c_tx_v;wire[2179:0]c_tx;wire c_fault;wire[9:0]c_count;
 always @(posedge clk)begin
  clear_r<=clear;ingest_r<=ingest_v;line_r<=selected_line;flush_r<=flush;emit_r<=emit_v;group_r<=emit_group;rank_r<=rank;gbase_r<=gbase;
  tx_v<=c_tx_v;tx<=c_tx;fault<=c_fault;selected_count<=c_count;
 end
 ot_hbm_idx_topk_link_static_p_core #(.MUT(MUT)) core(.clk(clk),.rst_n(rst_core_n),.clear(clear_r),.ingest_v(ingest_r),
  .selected_line(line_r),.flush(flush_r),.emit_v(emit_r),.emit_group(group_r),.rank(rank_r),.gbase(gbase_r),
  .tx_v(c_tx_v),.tx(c_tx),.fault(c_fault),.selected_count(c_count));
endmodule
`default_nettype wire
