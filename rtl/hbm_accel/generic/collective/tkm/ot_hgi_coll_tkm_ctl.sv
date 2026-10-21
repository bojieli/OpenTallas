`timescale 1ns/1ps
// TKM control leaf (PL-TP192 10-18): the ot_hgi_coll_tkm_static calendar body with the tile chain and the buffer
// moved out to the (wires-only) parent ot_hgi_coll_tkm_m_tp192_seg, so lp.py can region-clock it.  Differences vs
// tkm_static, all static (no ready / credit / backpressure):
//  * SETTLE += XS = 2*HOP*(NSEG-1): the chain crosses NSEG-1 region seams; each seam is a pre-scheduled HOP-edge
//    crossing (ot_pl_hop in the flat parent, a 4-slot landing in the landed parent) on both the down (insertion) and
//    the up (readout) chain.
//  * one conv strobe per chain segment (conv_s[s]): segment s must convey HOP*s edges before segment 0 (its up words
//    cross s seams) and its strobe itself crosses s seams on the down side -> emitted 2*HOP*s edges early.  clr is
//    shared (it only needs to precede the segment's first insertion and follow its last conveyance).
//  * arg_mode gates del_slot / del_valid here (was glue in ot_hgi_coll_tkm_m).
// Timeline vs tkm_static: every edge after ingress moves by XS+PIPE per pass (done / last write +2*(XS+PIPE)); the
// face flops add +1 in / +1 out (HBM-TP192 10-20, see the block comment below).
module ot_hgi_coll_tkm_ctl #(parameter integer KMAX=2048, MUT=0, TP=192, RANK_W=(TP<=1?1:$clog2(TP)),
  parameter integer NSEG=8, HOP=3, EW_=78+RANK_W)(
 input wire clk,rst_n,start,arg_mode,
 input wire[11:0]cfg_n,input wire[12:0]cfg_k,cfg_nout,
 input wire[7:0]cfg_g,cfg_gbase,input wire[15:0]cfg_pf,
 input wire[39:0]cfg_obase,cfg_rbase,input wire cfg_has_r,
 input wire[3:0]del_slot_i,del_valid_i,input wire[2179:0]del_flit,
 output reg w_v,output reg[39:0]w_addr,output reg[15:0]w_mask,output reg[511:0]w_data,
 output reg busy,done,fault,output reg[31:0]stat_cycles,
 // tile chain head (tile 0) and the per-segment calendar strobes (segment s reaches its tiles over s pre-scheduled
 // HOP-edge crossings: conv_s is emitted 2*HOP*s edges early, clr once for all segments)
 output reg entry_v,output reg[4*EW_-1:0]entry,input wire[4*EW_-1:0]up0,
 output wire clr,output wire[NSEG-1:0]conv_s,
 // pass-1 / pass-2 buffer (ot_hgi_coll_tkm_buffer, its own hard child)
 output reg buf_wv,output reg[9:0]buf_wa,output reg[4*EW_-1:0]buf_wdata,
 output wire read_v,output wire[9:0]read_addr,input wire buf_valid,input wire[4*EW_-1:0]buf_data
);
 localparam integer EW=78+RANK_W,KW=EW-2,VB=EW-2,RB=EW-1,ID_LO=12+RANK_W,ID_HI=43+RANK_W,VAL_LO=44+RANK_W,VAL_HI=75+RANK_W,NT=(KMAX+63)/64,XS=2*HOP*(NSEG-1),PIPE=4,SETTLE=3*NT+8+XS+PIPE;
 localparam integer NCB=(2180+31)/32,NLS=(545+31)/32,NHS=(256+31)/32,NSR=(EW+31)/32,NC1=(4*EW+31)/32,NC2=16;   // qsel copies: ids s / values 4+s / oline 8+s / rl 12+s (<= 32 loads per bit)
    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic [31:0] unkey(input [31:0] k, input nz);
        unkey = nz ? 32'h8000_0000 : (k[31] ? (k & 32'h7FFF_FFFF) : ~k);
    endfunction
    function automatic [KW-1:0] vkey(input [EW-1:0] e);
        vkey = e[VB:1];
    endfunction
    function automatic [KW-1:0] ikey(input [EW-1:0] e);
        ikey = {e[VB], e[ID_HI:ID_LO], e[VAL_HI:VAL_LO], e[ID_LO-1:1]};
    endfunction
    // Insertion key (EW-1 bits): {valid, ~region, body}: region 0 = the value order (selection phase), region 1 = the id
    // order (re-insertion phase, always below region 0); an invalid element is 0 (the lowest)
    function automatic [KW:0] key2(input [EW-1:0] e);
        reg [KW-1:0] b_;
        begin
            b_ = e[RB] ? ikey(e) : vkey(e);
            key2 = e[VB] ? {1'b1, ~e[RB], b_[KW-2:0]} : {(KW+1){1'b0}};
        end
    endfunction
    // KEY FORM (r3, the chain's storage format): T = {key2(e), nz} -- T[EW-1:1] is the EW-1-bit insertion key, so the
    // tiles compare stored bits with no key mux; tinv restores the element (an invalid element is 0 in both forms)
    function automatic [EW-1:0] tform(input [EW-1:0] e);
        tform = e[VB] ? {key2(e), e[0]} : {EW{1'b0}};
    endfunction
    function automatic [EW-1:0] tinv(input [EW-1:0] t);
        reg [EW-4:0] b_;
        begin
            b_ = t[EW-3:1];
            tinv = !t[EW-1] ? {EW{1'b0}} : (!t[EW-2] ? {1'b1, 1'b1, b_[RANK_W+42:RANK_W+11], b_[RANK_W+74:RANK_W+43], b_[RANK_W+10:0], t[0]} : {1'b0, 1'b1, b_, t[0]});
        end
    endfunction

 // ===== HBM-TP192 10-20 (structural, after gate4 FAIL 8: u_ctl wire reach 754 um, 4,226-load capture net,
 // 25-level tick -> entry stage).  All static, no ready / credit / backpressure; cycles added (compiler record
 // results/arch/pl_tp192_1018/compiler_delta.json):
 //  * PIN STAGE: every input port is captured once at the face (start/arg/del_slot/del_valid control flops reset,
 //    datapath unreset) and every output port leaves from a face flop.  Ingress offset vs start is UNCHANGED (start
 //    and del_* both +1); every output edge +2 (in + out).
 //  * INGRESS / RE-READ PIPE (PIPE = 4 edges, folded into SETTLE): s1 lane select (registered one-hot lane, kept
 //    copies per 32 bits), s2 half select + rank / rank*pf, s3 element decode + tform (key form), s4 sort ranks
 //    (registered one-hot selects, kept copies), entry at s5 = the old entry edge + PIPE.  SETTLE += PIPE moves
 //    first / clear2 / read2 / second / finish by PIPE per pass (done +2*PIPE).
 //  * FANOUT: beat capture enable = 69 kept leaf flops (<= 32 beat bits each) from 3 kept mid flops (2 edges early);
 //    conv capture enables (buffer write / output cell) = kept copies; the output-cell word select is a registered
 //    one-hot (no runtime part-select).
 // ---------------- pin stage (face flops)
 reg start_q,arg_q;reg[3:0]dslot_q,dval_q;reg[2179:0]del_flit_q;
 reg[11:0]cfg_n_q;reg[12:0]cfg_k_q,cfg_nout_q;reg[7:0]cfg_g_q,cfg_gbase_q;reg[15:0]cfg_pf_q;reg[39:0]cfg_obase_q,cfg_rbase_q;reg cfg_has_r_q;
 always @(posedge clk)begin
  del_flit_q<=del_flit;cfg_n_q<=cfg_n;cfg_k_q<=cfg_k;cfg_nout_q<=cfg_nout;cfg_g_q<=cfg_g;cfg_gbase_q<=cfg_gbase;cfg_pf_q<=cfg_pf;
  cfg_obase_q<=cfg_obase;cfg_rbase_q<=cfg_rbase;cfg_has_r_q<=cfg_has_r;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin start_q<=0;arg_q<=0;dslot_q<=0;dval_q<=0;end
  else begin start_q<=start;arg_q<=arg_mode;dslot_q<=del_slot_i;dval_q<=del_valid_i;end
 end
 // arg_mode gating (was the tkm_m wrapper's glue): moved into this leaf so the parent stays wires-only
 wire[3:0]del_slot=dslot_q&{4{!arg_q}},del_valid=dval_q&{4{!arg_q}};
 // ===== HBM-TP192 10-21 (SAFE 3, pre-gate native census FAIL 245 drivers / max 1,099 on the 10-20 ctl): every wide
 // select / enable is a KEPT REGISTERED COPY computed one edge early from next-state values (no driver > 32 loads):
 //  * configure: 24 register groups, each with its own kept start copy (face flop from the pin) and kept busy copy;
 //    non-reset registers moved out of the async-reset block (rst_n no longer an enable of ~500 flops).
 //  * readout: up0 registered once (u0q, +1 edge on the readout path: c1/c2 strobes one edge later, all calendar
 //    windows unchanged: last pass-2 write tick s_+c_+4 < finish s_+c_+8); the tinv valid/region selects are kept
 //    copies of the up0 top bits per consumer group (<= 32 bits each).
 //  * output cell: write-port / stash selects (wd/wa/wm, oline_q, rline) as 24 groups of kept one-hot selects from
 //    next-state (pending_o/pending_r/r_after_o next, c2 next, line-end next); zero mask / byte mask kept per word.
 //  * decode (s3): s2bv / invalid / buffered VB,RB / okey equality and sign as kept copies per 16-bit chunk.
 // Function and the done timeline are unchanged; w_* write edges +1 (compiler_delta hbm_tp192_1021).
 // core outputs -> face flops
 reg busy_c,done_c,fault_c,wv_c;reg[31:0]stat_c;reg[39:0]wa_c;reg[15:0]wm_c;reg[511:0]wd_c;
 always @(posedge clk)begin w_addr<=wa_c;w_mask<=wm_c;w_data<=wd_c;stat_cycles<=stat_c;end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin w_v<=0;busy<=0;done<=0;fault<=0;end
  else begin w_v<=wv_c;busy<=busy_c;done<=done_c;fault<=fault_c;end
 end
 // ---------------- calendar state
 reg[31:0]tick,tickc,ingress_end,first,clear2,read2,second,finish;
 reg[31:0]valid_pairs;reg[12:0]k;
 reg[23:0]flits;reg[12:0]nout,cells;reg[7:0]gb,g;
 reg[15:0]pf;reg[39:0]ob,rb;reg hr;
 reg[15:0]cap1,cap2;
 reg pending_r,pending_o,r_after_o;
 reg[2:0]conv_pipe;
 wire[31:0]rel=tick-8;
 wire ingest=busy_c&&tick>=8&&tick<ingress_end;
 wire capture=ingest&&(rel[2:0]==0);
 wire issue1=busy_c&&tick>=9&&tick<=ingress_end;
 wire[31:0]irel=tick-9;
 wire[1:0]lane=irel[2:1];
 wire[31:0]group_index=rel>>3;
 reg[3:0]expected;
 always @*begin
  expected=0;
  for(integer l=0;l<4;l=l+1)expected[l]=capture&&((group_index*4+32'(l))<flits);
 end
 function automatic cap_at(input [31:0] t);
  reg[31:0]r_;begin r_=t-8;cap_at=t>=8&&t<ingress_end&&(r_[2:0]==0);end
 endfunction
 wire[31:0]tick1=tick+1,tick2=tick+2;
 wire[31:0]irel1=tick1-9;
 wire cap_early=busy_c&&cap_at(tick2);
 // beat: 69 x 32-bit slices, each with its own kept capture-enable flop (2-level kept tree, no driver > 32 loads)
 wire[NCB*32-1:0]beat_w;wire[2179:0]beat=beat_w[2179:0];
 wire[NCB*32-1:0]dfx=(NCB*32)'(del_flit_q);
 for(genvar m=0;m<3;m=m+1)begin:g_capm
  (* keep="true", dont_touch="true" *) reg cm;
  always @(posedge clk)cm<=cap_early;
  for(genvar c=m*23;c<((m*23+23)<NCB?(m*23+23):NCB);c=c+1)begin:g_capl
   (* keep="true", dont_touch="true" *) reg cl;reg[31:0]b;
   always @(posedge clk)begin cl<=cm;if(cl)b<=dfx[32*c+:32];end
   assign beat_w[32*c+:32]=b;
  end
 end
 // ---------------- s1: lane select (registered one-hot lane, kept copy per 32 bits) + buffer re-read capture
 wire[3:0]lane1_oh=4'b1<<irel1[2:1];
 wire[NLS*32-1:0]flit1;
 for(genvar c=0;c<NLS;c=c+1)begin:g_lsel
  (* keep="true", dont_touch="true" *) reg[3:0]ls;
  always @(posedge clk)ls<=lane1_oh;
  for(genvar b=0;b<32;b=b+1)begin:g_b
   if(32*c+b<545)begin:g_on
    assign flit1[32*c+b]=(ls[0]&beat[32*c+b])|(ls[1]&beat[545+32*c+b])|(ls[2]&beat[1090+32*c+b])|(ls[3]&beat[1635+32*c+b]);
   end else begin:g_off
    assign flit1[32*c+b]=1'b0;
   end
  end
 end
 reg s1v,s1h,s1bv;reg[544:0]s1f;reg[4*EW-1:0]s1bd;
 always @(posedge clk)begin
  s1v<=issue1;s1h<=irel[0];s1f<=flit1[544:0];
  s1bv<=buf_valid;s1bd<=buf_data;
 end
 // beyond-flag: 2 kept copies (each feeds 2 slots x NDC invalid copies)
 wire s1beyond_n=32'(irel>>3)*4+32'(lane)>=32'(flits);
 wire[1:0]s1by;
 for(genvar c=0;c<2;c=c+1)begin:g_by
  (* keep="true", dont_touch="true" *) reg q;always @(posedge clk)q<=s1beyond_n;assign s1by[c]=q;
 end
 // ---------------- s2: half select (kept copies), rank and rank*pf
 wire[255:0]half2;
 for(genvar c=0;c<NHS;c=c+1)begin:g_hsel
  (* keep="true", dont_touch="true" *) reg hs;
  always @(posedge clk)hs<=irel[0];
  for(genvar b=0;b<32;b=b+1)begin:g_b
   localparam integer BI=32*c+b;           // 0..127 values, 128..255 ids
   localparam integer SRC=(BI<128)?BI:(256+BI-128);
   assign half2[BI]=hs?s1f[SRC+128]:s1f[SRC];
  end
 end
 localparam integer NDC=(EW+15)/16;       // decode chunks of 16 key-form bits per slot
 reg s2v,s2h,s2bv;reg[127:0]s2vv,s2id;reg[7:0]s2rank;reg[15:0]s2f16;reg[23:0]s2prod;reg[4*EW-1:0]s2bd;
 always @(posedge clk)begin:st2
  reg[7:0]r_;
  r_=s1f[535:528]-gb;
  s2v<=s1v;s2h<=s1h;s2bv<=s1bv;s2bd<=s1bd;
  s2vv<=half2[127:0];s2id<=half2[255:128];s2rank<=r_;s2f16<=s1f[527:512];s2prod<=24'(r_)*24'(pf);
 end
 // per slot s, per decode chunk c: kept copies of the re-read select, the invalid flag, the buffered VB / RB bits;
 // per slot: kept copies (2) of the okey equality (value == 8000_0000) and of the value sign bit
 wire[NDC-1:0]bvc[0:3],invc[0:3],bdvc[0:3],bdrc[0:3];
 wire[1:0]eqc[0:3],sgc[0:3];
 for(genvar s=0;s<4;s=s+1)begin:g_dc
  wire inv_n=(half2[32*s+:32]==32'hffffffff)||s1by[s/2];
  wire eq_n=(half2[32*s+:32]==32'h80000000);
  for(genvar c=0;c<NDC;c=c+1)begin:g_c
   (* keep="true", dont_touch="true" *) reg bv,iv,dv,dr;
   always @(posedge clk)begin bv<=s1bv;iv<=inv_n;dv<=s1bd[EW*s+VB];dr<=s1bd[EW*s+RB];end
   assign bvc[s][c]=bv;assign invc[s][c]=iv;assign bdvc[s][c]=dv;assign bdrc[s][c]=dr;
  end
  for(genvar c=0;c<2;c=c+1)begin:g_e
   (* keep="true", dont_touch="true" *) reg eq,sg;
   always @(posedge clk)begin eq<=eq_n;sg<=half2[32*s+31];end
   assign eqc[s][c]=eq;assign sgc[s][c]=sg;
  end
 end
 // ---------------- s3: element decode (or the re-read element) in key form T = tform(e), chunk-local selects
 // decoded e (RB 0, VB 1): T = {1, 1, e[83:1], e[0]} = {1, 1, okey(vv), ~id, ~rank, ~j, nz}; invalid -> 0
 // re-read e (buffer): T[p] = VB & (RB ? e[ik(p)] : e[p]) for 1 <= p <= EW-3, T[0] = VB & e[0], T[EW-2] = VB & ~RB, T[EW-1] = VB
 function automatic integer ik(input integer p);   // ikey source position of key-form bit p (1 <= p <= EW-3)
  integer q;begin
   q=p-1;   // ikey index
   if(q>=KW-1)ik=VB;                                   // ikey[KW-1] = e[VB]
   else if(q>=KW-1-32)ik=ID_LO+(q-(KW-1-32));           // ikey[KW-2 -: 32] = e[ID_HI:ID_LO]
   else if(q>=KW-1-64)ik=VAL_LO+(q-(KW-1-64));          // next 32 = e[VAL_HI:VAL_LO]
   else ik=1+q;                                         // ikey[ID_LO-2:0] = e[ID_LO-1:1]
  end
 endfunction
 reg s3v,s3iss;reg[EW-1:0]s3t[0:3];
 wire[23:0]f3=24'(s2f16)-s2prod;
 for(genvar s=0;s<4;s=s+1)begin:g_s3
  wire[23:0]j3=f3*8+24'(4*s2h)+24'(s);
  wire[EW-1:0]bd=s2bd[EW*s+:EW];
  for(genvar p=0;p<EW;p=p+1)begin:g_p
   localparam integer C=p/16;
   wire bv=bvc[s][C],iv=invc[s][C],dv=bdvc[s][C],dr=bdrc[s][C];
   wire eqp=eqc[s][(p>=VAL_LO+16)?1:0],sgp=sgc[s][(p>=VAL_LO+16)?1:0];
   wire dec;   // decoded key-form bit
   if(p==EW-1||p==EW-2)begin:g_one assign dec=1'b1;end
   else if(p>=VAL_LO&&p<=VAL_HI)begin:g_val
    if(p==VAL_HI)begin:g_hi assign dec=eqp|!sgp;end
    else begin:g_lo assign dec=!eqp&(sgp^s2vv[32*s+(p-VAL_LO)]);end
   end
   else if(p>=ID_LO&&p<=ID_HI)begin:g_id assign dec=~s2id[32*s+(p-ID_LO)];end
   else if(p>=12&&p<ID_LO)begin:g_rk assign dec=~s2rank[p-12];end
   else if(p>=1&&p<12)begin:g_j assign dec=~j3[p-1];end
   else begin:g_nz assign dec=eqc[s][0];end
   wire rr;    // re-read key-form bit
   if(p==EW-1)begin:g_r1 assign rr=dv;end
   else if(p==EW-2)begin:g_r2 assign rr=dv&~dr;end
   else if(p==0)begin:g_r0 assign rr=dv&bd[0];end
   else begin:g_rp assign rr=dv&(dr?bd[ik(p)]:bd[p]);end
   always @(posedge clk)s3t[s][p]<=bv?rr:(iv?1'b0:dec);
  end
 end
 always @(posedge clk)begin s3v<=s2v||s2bv;s3iss<=s2v;end
 // ---------------- s4: sort ranks (key = T[EW-1:1]; ties by slot) as registered one-hot selects, kept copies
 reg s4v;reg[EW-1:0]s4t[0:3];
 always @(posedge clk)begin s4v<=s3v;for(integer s=0;s<4;s=s+1)s4t[s]<=s3t[s];end
 reg[3:0]rsel[0:3];   // rsel[d][s]: slot s goes to sorted position d
 always @*begin:rank_sort
  integer rank_s;
  for(integer d=0;d<4;d=d+1)rsel[d]=0;
  for(integer s=0;s<4;s=s+1)begin
   rank_s=0;
   for(integer j_=0;j_<4;j_=j_+1)if(s3t[j_][EW-1:1]>s3t[s][EW-1:1]||(s3t[j_][EW-1:1]==s3t[s][EW-1:1]&&j_<s))rank_s=rank_s+1;
   rsel[rank_s][s]=1'b1;
  end
 end
 wire[4*EW-1:0]entry_n;
 for(genvar d=0;d<4;d=d+1)begin:g_sd
  for(genvar c=0;c<NSR;c=c+1)begin:g_sc
   (* keep="true", dont_touch="true" *) reg[3:0]rs;
   always @(posedge clk)rs<=rsel[d];
   for(genvar b=32*c;b<((32*c+32)<EW?(32*c+32):EW);b=b+1)begin:g_b
    assign entry_n[EW*d+b]=(MUT==1&&d==3)?1'b0:((rs[0]&s4t[0][b])|(rs[1]&s4t[1][b])|(rs[2]&s4t[2][b])|(rs[3]&s4t[3][b]));
   end
  end
 end
 always @(posedge clk)begin entry_v<=busy_c&&s4v;entry<=entry_n;end
 // ---------------- chain strobes (calendar): tickc = kept copy of tick for the strobe comparators
 wire conv1=busy_c&&tickc>=first&&tickc<first+32'(cells);
 wire conv2=busy_c&&tickc>=second&&tickc<second+32'(cells);
 // segment s conveys HOP*s edges ahead of segment 0 (each up crossing adds HOP edges) and its strobe rides s down
 // crossings (HOP edges each): emitted 2*HOP*s edges before segment 0's window. MUT 3: HOP*s (the up crossings
 // are not compensated: the readout tears at the first seam).
 for(genvar s=0;s<NSEG;s=s+1)begin:g_conv
  localparam integer AD=(MUT==3)?HOP*s:2*HOP*s;
  wire[31:0]ta=tickc+32'(AD);
  assign conv_s[s]=busy_c&&((ta>=first&&ta<first+32'(cells))||(ta>=second&&ta<second+32'(cells)));
 end
 assign clr=busy_c&&(tick==1||tick==clear2);
 assign read_v=busy_c&&tick>=read2&&tick<read2+32'(cells);
 assign read_addr=10'(tick-read2);
 // conv capture enables: up0 is registered (u0q), so the captures are one edge after the 10-20 ctl: built from
 // conv_pipe[1] (= conv_pipe[0] one edge earlier) and tick (= tick1 one edge earlier); registered, kept copies
 wire c1_early=busy_c&&conv_pipe[1]&&(tickc<clear2);
 wire c2_early=busy_c&&conv_pipe[1]&&(tickc>=second);
 localparam integer NBG=(EW+31)/32;      // buffer-tag chunks per slot
 wire c1x,c1y,c2s;wire[NBG-1:0]c1c[0:3];
 (* keep="true", dont_touch="true" *) reg c1xq,c1yq,c2sq;
 always @(posedge clk)begin c1xq<=c1_early;c1yq<=c1_early;c2sq<=c2_early;end
 assign c1x=c1xq;assign c1y=c1yq;assign c2s=c2sq;
 // readout capture stage + kept copies of the tinv selects (v = T[EW-1], r = T[EW-2]) per consumer group
 reg[4*EW-1:0]u0q;always @(posedge clk)u0q<=up0;
 function automatic [EW-1:0] tinv_l(input [EW-1:0] t, input v, input r);
  reg [EW-4:0] b_;
  begin
   b_ = t[EW-3:1];
   tinv_l = !v ? {EW{1'b0}} : (!r ? {1'b1, 1'b1, b_[RANK_W+42:RANK_W+11], b_[RANK_W+74:RANK_W+43], b_[RANK_W+10:0], t[0]} : {1'b0, 1'b1, b_, t[0]});
  end
 endfunction
 // groups per slot: 0..NBG-1 buffer tag chunks, then ids lo/hi, values lo/hi, oline lo/hi, rl lo/hi
 localparam integer NVG=NBG+8;
 wire[NVG-1:0]vg[0:3],rg_[0:3];
 for(genvar s=0;s<4;s=s+1)begin:g_vr
  for(genvar c=0;c<NVG;c=c+1)begin:g_c
   (* keep="true", dont_touch="true" *) reg v,r;
   always @(posedge clk)begin v<=up0[EW*s+EW-1];r<=up0[EW*s+EW-2];end
   assign vg[s][c]=v;assign rg_[s][c]=r;
  end
  for(genvar c=0;c<NBG;c=c+1)begin:g_c1
   (* keep="true", dont_touch="true" *) reg q;always @(posedge clk)q<=c1_early;assign c1c[s][c]=q;
  end
 end
 // output-cell word group (cap2[1:0]) as a registered one-hot, kept copies (16 ids/values words: 4 groups x 4)
 wire[15:0]cap2n=cap2+(c2s?16'd1:16'd0);
 wire[15:0]cap1n=cap1+(c1x?16'd1:16'd0);
 wire[3:0]q_early=c2_early?(4'b1<<cap2n[1:0]):4'b0;
 wire[3:0]qsel[0:NC2-1];
 for(genvar c=0;c<NC2;c=c+1)begin:g_q
  (* keep="true", dont_touch="true" *) reg[3:0]q;always @(posedge clk)q<=q_early;assign qsel[c]=q;
 end
 // buffer write tag (pass 1 capture of the chain readout): per slot per chunk, kept nout-compare copy (next value)
 reg[NBG-1:0]okc[0:3];
 for(genvar s=0;s<4;s=s+1)begin:g_tag
  wire ok_n=(32'(cap1n)*4+32'(s))<32'(nout);
  for(genvar c=0;c<NBG;c=c+1)begin:g_c
   (* keep="true", dont_touch="true" *) reg ok;always @(posedge clk)ok<=ok_n;
   wire[EW-1:0]e=tinv_l(u0q[EW*s+:EW],vg[s][c],rg_[s][c]);
   wire[EW-1:0]tw=ok?(e|{e[VB],{(EW-1){1'b0}}}):{EW{1'b0}};
   for(genvar b=32*c;b<((32*c+32)<EW?(32*c+32):EW);b=b+1)begin:g_b
    always @(posedge clk)if(c1c[s][c])buf_wdata[EW*s+b]<=tw[b];
   end
  end
 end
 // output cell words: ids / values of group q written when qsel (one-hot) says so; e per 16-bit half (own selects)
 reg[31:0]ids[0:15],values[0:15];
 wire[31:0]oid[0:3],orl[0:3];     // the output-cell candidates of slot s (oline id word / rl value word)
 for(genvar s=0;s<4;s=s+1)begin:g_ow
  for(genvar h=0;h<2;h=h+1)begin:g_h
   wire[EW-1:0]ei=tinv_l(u0q[EW*s+:EW],vg[s][NBG+0+h],rg_[s][NBG+0+h]);
   wire[EW-1:0]ev=tinv_l(u0q[EW*s+:EW],vg[s][NBG+2+h],rg_[s][NBG+2+h]);
   wire[EW-1:0]eo=tinv_l(u0q[EW*s+:EW],vg[s][NBG+4+h],rg_[s][NBG+4+h]);
   wire[EW-1:0]er=tinv_l(u0q[EW*s+:EW],vg[s][NBG+6+h],rg_[s][NBG+6+h]);
   wire[31:0]idw=~ei[ID_HI:ID_LO];
   wire[31:0]vaw=unkey(ev[VAL_HI:VAL_LO],ev[0]);
   assign oid[s][16*h+:16]=~eo[ID_LO+16*h+:16];
   wire[31:0]rlw=unkey(er[VAL_HI:VAL_LO],er[0]);
   assign orl[s][16*h+:16]=rlw[16*h+:16];
   for(genvar q=0;q<4;q=q+1)begin:g_q
    always @(posedge clk)begin
     if(qsel[s][q])ids[4*q+s][16*h+:16]<=idw[16*h+:16];
     if(qsel[4+s][q])values[4*q+s][16*h+:16]<=vaw[16*h+:16];
    end
   end
  end
 end
 // ---------------- next state of the control registers (single source; the early group selects read it)
 wire les,hrs;
 reg busy_nx,po_nx,pr_nx,ra_nx;
 always @*begin
  busy_nx=busy_c;po_nx=pending_o;pr_nx=pending_r;ra_nx=r_after_o;
  if(busy_c)begin
   if(pending_o)begin po_nx=1'b0;pr_nx=r_after_o;ra_nx=1'b0;end
   else if(pending_r)pr_nx=1'b0;
   if(c2s&&les)begin
    if(pending_r&&MUT!=2)begin po_nx=1'b1;ra_nx=hrs;end
    else if(hrs)pr_nx=1'b1;
   end
   if(tick==finish)busy_nx=1'b0;
  end
  if(start_q&&!busy_c)begin busy_nx=1'b1;po_nx=1'b0;pr_nx=1'b0;ra_nx=1'b0;end
 end
 // line end / zero masks for the NEXT cap2 (cap2n), registered: kept copies per word (oline, rl, byte mask)
 wire signed[31:0]cnt_n=$signed(32'(nout))-$signed(32'(16*(cap2n>>2)));
 wire le_n=(cap2n[1:0]==2'd3)||(32'(cap2n)+1==32'(cells));
 (* keep="true", dont_touch="true" *) reg lesq;always @(posedge clk)lesq<=le_n;assign les=lesq;
 wire hr_n=(start_q&&!busy_c)?cfg_has_r_q:hr;
 (* keep="true", dont_touch="true" *) reg hrsq;always @(posedge clk)hrsq<=hr_n;assign hrs=hrsq;
 wire[15:0]zo,zr,zm;
 for(genvar i=0;i<16;i=i+1)begin:g_z
  wire z_n=$signed(i)>=cnt_n;
  (* keep="true", dont_touch="true" *) reg a,b,m;
  always @(posedge clk)begin a<=z_n;b<=z_n;m<=z_n;end
  assign zo[i]=a;assign zr[i]=b;assign zm[i]=m;
 end
 wire[511:0]oline,rl;
 for(genvar q=0;q<4;q=q+1)for(genvar s=0;s<4;s=s+1)begin:g_ol
  localparam integer W_=4*q+s;
  assign oline[32*W_+:32]=zo[W_]?32'd0:(qsel[8+s][q]?oid[s]:ids[W_]);
  assign rl[32*W_+:32]=zr[W_]?32'd0:(qsel[12+s][q]?orl[s]:values[W_]);
 end
 wire[15:0]mask_=~zm;
 wire[39:0]oaddr_n=ob+40'(16*(cap2>>2)),raddr_n=rb+40'(16*(cap2>>2));
 // write-port / stash early selects (state at the next edge) -> NWG groups of <= 24 bits, kept one-hot copies
 wire seln_e=busy_nx&&c2_early&&le_n&&!(pr_nx&&MUT!=2);
 wire selo_e=busy_nx&&po_nx&&!seln_e;
 wire selr_e=busy_nx&&!po_nx&&pr_nx&&!seln_e;
 wire enoq_e=busy_nx&&c2_early&&le_n&&pr_nx&&(MUT!=2);
 wire enrl_e=busy_nx&&c2_early&&le_n&&hr_n;
 localparam integer WW=40+16+512,WG=24,NWG=(WW+WG-1)/WG;
 reg[39:0]oaddr_q,raddr;reg[15:0]omask_q,rmask;reg[511:0]oline_q,rline;
 wire[WW-1:0]wcur={wa_c,wm_c,wd_c},woq={oaddr_q,omask_q,oline_q},wrl={raddr,rmask,rline};
 wire[WW-1:0]wnew={oaddr_n,mask_,oline},wrnew={raddr_n,mask_,rl};
 reg[WW-1:0]wcur_n,woq_n,wrl_n;
 for(genvar gi=0;gi<NWG;gi=gi+1)begin:g_wg
  (* keep="true", dont_touch="true" *) reg so,sr,sn,sa,eo,er;
  always @(posedge clk)begin so<=selo_e;sr<=selr_e;sn<=seln_e;sa<=selo_e|selr_e|seln_e;eo<=enoq_e;er<=enrl_e;end
  for(genvar b=WG*gi;b<((WG*gi+WG)<WW?(WG*gi+WG):WW);b=b+1)begin:g_b
   always @*begin
    wcur_n[b]=sa?((so&woq[b])|(sr&wrl[b])|(sn&wnew[b])):wcur[b];
    woq_n[b]=eo?wnew[b]:woq[b];
    wrl_n[b]=er?wrnew[b]:wrl[b];
   end
  end
 end
 always @(posedge clk)begin
  {wa_c,wm_c,wd_c}<=wcur_n;{oaddr_q,omask_q,oline_q}<=woq_n;{raddr,rmask,rline}<=wrl_n;
 end
 // ---------------- configure + counters (no reset: rst_n is not an enable of these registers); 24 groups, each with
 // its own kept start copy (face flop from the start pin) and kept busy copy -> go / busy selects <= 32 loads
 localparam integer NCG=24;
 wire[NCG-1:0]gog,bsg;
 for(genvar c=0;c<NCG;c=c+1)begin:g_cfg
  (* keep="true", dont_touch="true" *) reg sq,bq;
  always @(posedge clk)begin sq<=start;bq<=busy_nx;end
  assign gog[c]=sq&&!bq;assign bsg[c]=bq;
 end
 wire[31:0]i_n,c_n,a_n,b_n,r_n,s_n,f_n,fl_n;
 assign fl_n=32'(cfg_g_q)*32'(cfg_pf_q);assign i_n=8+((fl_n+3)/4)*8;assign c_n=(32'(cfg_nout_q)+3)/4;
 assign a_n=i_n+SETTLE;assign b_n=a_n+c_n+5;assign r_n=b_n+5;assign s_n=r_n+c_n+6+SETTLE;assign f_n=s_n+c_n+8;
 integer added;
 always @*begin added=0;for(integer s=0;s<4;s=s+1)added=added+int'(s3t[s][EW-1]);end
 always @(posedge clk)begin
  if(gog[0])tick[15:0]<=0;else if(bsg[0])tick[15:0]<=tick1[15:0];
  if(gog[1])tick[31:16]<=0;else if(bsg[1])tick[31:16]<=tick1[31:16];
  if(gog[2])tickc[15:0]<=0;else if(bsg[2])tickc[15:0]<=16'(tickc+1);
  if(gog[3])tickc[31:16]<=0;else if(bsg[3])tickc[31:16]<=tickc[31:16]+16'(((tickc[15:0]==16'hffff))?1:0);
  if(gog[4])stat_c[15:0]<=0;else if(bsg[4])stat_c[15:0]<=tick1[15:0];
  if(gog[5])stat_c[31:16]<=0;else if(bsg[5])stat_c[31:16]<=tick1[31:16];
  if(gog[6])ingress_end<=i_n;
  if(gog[7])first<=a_n;
  if(gog[8])clear2<=b_n;
  if(gog[9])read2<=r_n;
  if(gog[10])second<=s_n;
  if(gog[11])finish<=f_n;
  if(gog[12])valid_pairs[15:0]<=0;else if(bsg[12]&&s3iss)valid_pairs[15:0]<=16'(valid_pairs+32'(added));
  if(gog[13])valid_pairs[31:16]<=0;else if(bsg[13]&&s3iss)valid_pairs[31:16]<=16'((valid_pairs+32'(added))>>16);
  if(gog[14])begin k<=cfg_k_q;cells<=13'(c_n);end
  if(gog[15])flits<=24'(fl_n);
  if(gog[16])begin nout<=cfg_nout_q;gb<=cfg_gbase_q;end
  if(gog[17])begin g<=cfg_g_q;pf<=cfg_pf_q;end
  if(gog[18])ob[19:0]<=cfg_obase_q[19:0];
  if(gog[19])ob[39:20]<=cfg_obase_q[39:20];
  if(gog[20])rb[19:0]<=cfg_rbase_q[19:0];
  if(gog[21])rb[39:20]<=cfg_rbase_q[39:20];
  if(gog[22])begin hr<=cfg_has_r_q;cap1<=0;end else if(bsg[22]&&c1x)cap1<=cap1n;
  if(gog[23])cap2<=0;else if(bsg[23]&&c2s)cap2<=cap2n;
 end
 always @(posedge clk)if(c1y&&busy_c)buf_wa<=10'(cap1);
 // ---------------- control registers (reset: control / valid bits only)
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy_c<=0;done_c<=0;fault_c<=0;conv_pipe<=0;buf_wv<=0;wv_c<=0;pending_r<=0;pending_o<=0;r_after_o<=0;end
  else begin
   busy_c<=busy_nx;pending_o<=po_nx;pending_r<=pr_nx;r_after_o<=ra_nx;
   done_c<=busy_c&&(tick==finish);
   wv_c<=busy_c&&(pending_o||pending_r||(c2s&&les));
   buf_wv<=busy_c&&c1y;
   conv_pipe<=(start_q&&!busy_c)?3'd0:{conv_pipe[1:0],conv1||conv2};
   if(busy_c)begin
    if(del_valid!=expected||del_slot!=expected)fault_c<=1;
    if(capture)for(integer l=0;l<4;l=l+1)if(expected[l])begin
     for(integer s=0;s<8;s=s+1)begin
      if(del_flit_q[545*l+32*s+23+:8]==8'hff&&del_flit_q[545*l+32*s+:23]!=0&&del_flit_q[545*l+32*s+:32]!=32'hffffffff)fault_c<=1;
     end
     if(!del_flit_q[545*l+544]||del_flit_q[545*l+528+:8]<gb||del_flit_q[545*l+528+:8]>=gb+g)fault_c<=1;
    end
    if(tick==finish)begin
     if(32'(cap1)!=32'(cells)||32'(cap2)!=32'(cells)||pending_r||pending_o||32'(nout)!=((32'(k)<valid_pairs)?32'(k):valid_pairs))fault_c<=1;
    end
   end
   if(start_q)begin
    if(busy_c)fault_c<=1;
    else fault_c<=cfg_g_q==0||cfg_g_q>TP||cfg_pf_q!=(16'(cfg_n_q)+7)/8||cfg_nout_q==0||cfg_nout_q>KMAX||cfg_k_q>KMAX||
        cfg_nout_q>cfg_k_q||cfg_obase_q[3:0]!=0||cfg_rbase_q[3:0]!=0;
   end
  end
 end
endmodule
