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
 // core outputs -> face flops
 reg busy_c,done_c,fault_c,wv_c;reg[31:0]stat_c;reg[39:0]wa_c;reg[15:0]wm_c;reg[511:0]wd_c;
 always @(posedge clk)begin w_addr<=wa_c;w_mask<=wm_c;w_data<=wd_c;stat_cycles<=stat_c;end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin w_v<=0;busy<=0;done<=0;fault<=0;end
  else begin w_v<=wv_c;busy<=busy_c;done<=done_c;fault<=fault_c;end
 end
 // ---------------- calendar state
 reg[31:0]tick,ingress_end,first,clear2,read2,second,finish;
 reg[31:0]valid_pairs;reg[12:0]k;
 reg[23:0]flits;reg[12:0]nout,cells;reg[7:0]gb,g;
 reg[15:0]pf;reg[39:0]ob,rb;reg hr;
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
 // capture / lane decisions made early from tick (busy_c is steady through ingress; a start while busy only faults)
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
 reg s1v,s1h,s1beyond,s1bv;reg[544:0]s1f;reg[4*EW-1:0]s1bd;
 always @(posedge clk)begin
  s1v<=issue1;s1h<=irel[0];s1beyond<=32'(irel>>3)*4+32'(lane)>=32'(flits);s1f<=flit1[544:0];
  s1bv<=buf_valid;s1bd<=buf_data;
 end
 // ---------------- s2: half select (kept copies), rank and rank*pf
 wire[255:0]half2;
 for(genvar c=0;c<NHS;c=c+1)begin:g_hsel
  (* keep="true", dont_touch="true" *) reg hs;
  always @(posedge clk)hs<=irel[0];
  // hs == s1h (same edge); value slots 4*h+s (s 0..3) of the 8 values / 8 ids
  for(genvar b=0;b<32;b=b+1)begin:g_b
   localparam integer BI=32*c+b;           // 0..127 values, 128..255 ids
   localparam integer SRC=(BI<128)?BI:(256+BI-128);
   assign half2[BI]=hs?s1f[SRC+128]:s1f[SRC];
  end
 end
 reg s2v,s2h,s2bv;reg[3:0]s2inv;reg[127:0]s2vv,s2id;reg[7:0]s2rank;reg[15:0]s2f16;reg[23:0]s2prod;reg[4*EW-1:0]s2bd;
 always @(posedge clk)begin:st2
  reg[7:0]r_;
  r_=s1f[535:528]-gb;
  s2v<=s1v;s2h<=s1h;s2bv<=s1bv;s2bd<=s1bd;
  s2vv<=half2[127:0];s2id<=half2[255:128];s2rank<=r_;s2f16<=s1f[527:512];s2prod<=24'(r_)*24'(pf);
  for(integer s=0;s<4;s=s+1)s2inv[s]<=(half2[32*s+:32]==32'hffffffff)||s1beyond;
 end
 // ---------------- s3: element decode (or the re-read element) in key form T = tform(e)
 reg s3v,s3iss;reg[EW-1:0]s3t[0:3];
 always @(posedge clk)begin:st3
  reg[23:0]f,j;reg[31:0]vv,id;reg[EW-1:0]e;
  f=24'(s2f16)-s2prod;
  for(integer s=0;s<4;s=s+1)begin
   vv=s2vv[32*s+:32];id=s2id[32*s+:32];j=f*8+24'(4*s2h)+24'(s);
   e={1'b0,1'b1,okey(vv),~id,~s2rank[RANK_W-1:0],~j[10:0],(vv==32'h80000000)};
   if(s2inv[s])e=0;
   if(s2bv)e=s2bd[EW*s+:EW];
   s3t[s]<=tform(e);
  end
  s3v<=s2v||s2bv;s3iss<=s2v;
 end
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
 // ---------------- chain strobes (calendar)
 wire conv1=busy_c&&tick>=first&&tick<first+32'(cells);
 wire conv2=busy_c&&tick>=second&&tick<second+32'(cells);
 // segment s conveys HOP*s edges ahead of segment 0 (each up crossing adds HOP edges) and its strobe rides s down
 // crossings (HOP edges each): emitted 2*HOP*s edges before segment 0's window. MUT 3: HOP*s (the up crossings
 // are not compensated: the readout tears at the first seam).
 for(genvar s=0;s<NSEG;s=s+1)begin:g_conv
  localparam integer AD=(MUT==3)?HOP*s:2*HOP*s;
  wire[31:0]ta=tick+32'(AD);
  assign conv_s[s]=busy_c&&((ta>=first&&ta<first+32'(cells))||(ta>=second&&ta<second+32'(cells)));
 end
 assign clr=busy_c&&(tick==1||tick==clear2);
 assign read_v=busy_c&&tick>=read2&&tick<read2+32'(cells);
 assign read_addr=10'(tick-read2);
 reg[2:0]conv_pipe;
 reg[31:0]cap1,cap2;
 // conv capture enables, one edge early from conv_pipe[0] (= conv_pipe[1] next edge), kept copies
 wire c1_early=busy_c&&conv_pipe[0]&&(tick1<clear2);
 wire c2_early=busy_c&&conv_pipe[0]&&(tick1>=second);
 wire[NC1-1:0]c1;wire[0:0]c2;
 for(genvar c=0;c<NC1;c=c+1)begin:g_c1
  (* keep="true", dont_touch="true" *) reg q;always @(posedge clk)q<=c1_early;assign c1[c]=q;
 end
 (* keep="true", dont_touch="true" *) reg c2q;always @(posedge clk)c2q<=c2_early;assign c2[0]=c2q;
 // output-cell word group (cap2[1:0]) as a registered one-hot, kept copies (16 ids/values words: 4 groups x 4)
 wire[31:0]cap2n=cap2+(c2[0]?32'd1:32'd0);
 wire[3:0]q_early=c2_early?(4'b1<<cap2n[1:0]):4'b0;
 wire[3:0]qsel[0:NC2-1];
 for(genvar c=0;c<NC2;c=c+1)begin:g_q
  (* keep="true", dont_touch="true" *) reg[3:0]q;always @(posedge clk)q<=q_early;assign qsel[c]=q;
 end
 reg[31:0]ids[0:15],values[0:15];
 reg pending_r;reg[511:0]rline;reg[39:0]raddr;reg[15:0]rmask;
 // A final partial line one cell after a full line (cells%4==1) would share the single write port with the
 // previous line's R write. It is statically deferred one edge (O at +1, R at +2); the timeline is unchanged.
 reg pending_o,r_after_o;reg[511:0]oline_q;reg[39:0]oaddr_q;reg[15:0]omask_q;
 // buffer write tag (pass 1 capture of the chain readout)
 always @(posedge clk)begin
  for(integer s=0;s<4;s=s+1)begin:tag
   reg[EW-1:0]e,tw;e=tinv(up0[EW*s+:EW]);
   tw=((cap1*4+32'(s))<32'(nout))?(e|{e[VB],{(EW-1){1'b0}}}):{EW{1'b0}};
   for(integer b=0;b<EW;b=b+1)if(c1[(EW*s+b)/32])buf_wdata[EW*s+b]<=tw[b];
  end
 end
 // output cell words: ids / values of group q written when qsel (one-hot) says so
 always @(posedge clk)begin
  for(integer q=0;q<4;q=q+1)for(integer s=0;s<4;s=s+1)begin:wr
   reg[EW-1:0]e;e=tinv(up0[EW*s+:EW]);
   if(qsel[s][q])ids[4*q+s]<=~e[ID_HI:ID_LO];
   if(qsel[4+s][q])values[4*q+s]<=unkey(e[VAL_HI:VAL_LO],e[0]);
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy_c<=0;done_c<=0;fault_c<=0;conv_pipe<=0;buf_wv<=0;wv_c<=0;pending_r<=0;pending_o<=0;r_after_o<=0;end
  else begin
   done_c<=0;wv_c<=0;buf_wv<=0;
   conv_pipe<={conv_pipe[1:0],conv1||conv2};
   if(busy_c)begin
    tick<=tick+1;stat_c<=tick+1;
    if(del_valid!=expected||del_slot!=expected)fault_c<=1;
    if(s3iss)begin:count_pairs
     integer added;added=0;for(integer s=0;s<4;s=s+1)added=added+int'(s3t[s][EW-1]);
     valid_pairs<=valid_pairs+32'(added);
    end
    if(capture)for(integer l=0;l<4;l=l+1)if(expected[l])begin
     for(integer s=0;s<8;s=s+1)begin
      if(del_flit_q[545*l+32*s+23+:8]==8'hff&&del_flit_q[545*l+32*s+:23]!=0&&del_flit_q[545*l+32*s+:32]!=32'hffffffff)fault_c<=1;
     end
     if(!del_flit_q[545*l+544]||del_flit_q[545*l+528+:8]<gb||del_flit_q[545*l+528+:8]>=gb+g)fault_c<=1;
    end
    if(c1[0])begin buf_wv<=1;buf_wa<=10'(cap1);cap1<=cap1+1;end
    if(pending_o)begin wv_c<=1;wd_c<=oline_q;wa_c<=oaddr_q;wm_c<=omask_q;pending_o<=0;pending_r<=r_after_o;r_after_o<=0;end
    else if(pending_r)begin wv_c<=1;wd_c<=rline;wa_c<=raddr;wm_c<=rmask;pending_r<=0;end
    if(c2[0])begin:output_cell
     reg[EW-1:0]e;reg[511:0]oline,rl;reg[15:0]mask_;integer count_;
     cap2<=cap2+1;
     for(integer q=0;q<4;q=q+1)for(integer s=0;s<4;s=s+1)begin
      e=tinv(up0[EW*s+:EW]);
      oline[32*(4*q+s)+:32]=qsel[8+s][q]?~e[ID_HI:ID_LO]:ids[4*q+s];
      rl[32*(4*q+s)+:32]=qsel[12+s][q]?unkey(e[VAL_HI:VAL_LO],e[0]):values[4*q+s];
     end
     if(cap2[1:0]==3||cap2+1==32'(cells))begin
      count_=int'(nout)-16*int'(cap2>>2);if(count_>16)count_=16;
      mask_=16'((17'd1<<count_)-1);
      for(integer i=0;i<16;i=i+1)if(i>=count_)begin oline[32*i+:32]=0;rl[32*i+:32]=0;end
      if(pending_r&&MUT!=2)begin pending_o<=1;oline_q<=oline;omask_q<=mask_;oaddr_q<=ob+40'(16*(cap2>>2));r_after_o<=hr;end
      else begin wv_c<=1;wd_c<=oline;wm_c<=mask_;wa_c<=ob+40'(16*(cap2>>2));if(hr)pending_r<=1;end
      if(hr)begin rline<=rl;raddr<=rb+40'(16*(cap2>>2));rmask<=mask_;end
     end
    end
    if(tick==finish)begin
     if(cap1!=32'(cells)||cap2!=32'(cells)||pending_r||pending_o||32'(nout)!=((32'(k)<valid_pairs)?32'(k):valid_pairs))fault_c<=1;
     busy_c<=0;done_c<=1;
    end
   end
   if(start_q)begin:configure
    reg[31:0]i_,c_,a_,b_,r_,s_,f_;reg[31:0]fl_;
    fl_=32'(cfg_g_q)*32'(cfg_pf_q);i_=8+((fl_+3)/4)*8;c_=(32'(cfg_nout_q)+3)/4;
    a_=i_+SETTLE;b_=a_+c_+5;r_=b_+5;s_=r_+c_+6+SETTLE;f_=s_+c_+8;
    if(busy_c)fault_c<=1;
    else begin
     fault_c<=cfg_g_q==0||cfg_g_q>TP||cfg_pf_q!=(16'(cfg_n_q)+7)/8||cfg_nout_q==0||cfg_nout_q>KMAX||cfg_k_q>KMAX||
        cfg_nout_q>cfg_k_q||cfg_obase_q[3:0]!=0||cfg_rbase_q[3:0]!=0;
     busy_c<=1;tick<=0;stat_c<=0;ingress_end<=i_;first<=a_;clear2<=b_;read2<=r_;second<=s_;finish<=f_;
     valid_pairs<=0;k<=cfg_k_q;flits<=24'(fl_);cells<=13'(c_);nout<=cfg_nout_q;gb<=cfg_gbase_q;g<=cfg_g_q;pf<=cfg_pf_q;ob<=cfg_obase_q;rb<=cfg_rbase_q;hr<=cfg_has_r_q;
     cap1<=0;cap2<=0;conv_pipe<=0;pending_r<=0;pending_o<=0;r_after_o<=0;
    end
   end
  end
 end
endmodule
