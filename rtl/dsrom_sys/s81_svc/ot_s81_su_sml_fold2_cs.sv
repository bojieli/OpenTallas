`timescale 1ns/1ps
// DIE-S81-85 svc census 11-10 (COORD loopgap-153x-1109): census-safe copy of ot_s81_su_sml_fold2
// (rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_sml_fold2.sv, unchanged without the define), used only under
// -DOT_S81_SVC_CS (the box keeps its name: ot_s81_su_sml_fold2's body under the define).  Same ports, same function at the ports, same cycles.  Only drivers above 64 load pins change:
//   - rn: NRN kept copies of the reset relay's second flop (each = rr1 cycle for cycle), one per load group;
//   - the score store read address 2*rcnt+rctx (rcnt[0] 2545 / rctx 1298 pins) -> a kept one-hot read pointer roh
//     (advances with the address: +1 per read edge, 0 on mv); the write address 2*wcnt[wc]+wc -> one-hot per-lane
//     pointers beside wcnt (which stays for the counts and compares): two copies per lane (store word low / high
//     bits), each advancing on its lane's write and wrapping on its own bit nv-1 (nl: one-hot of nv-1, loaded with
//     nv), so pointer = one-hot(wcnt[lane]) under the configuration contract (cv only between rows, 1 <= nv <= NVMAX);
//   - cv / mv / rd_on / wc / smv / inactive / es / ei: kept replicas, each driving one slice of the consumers;
//   - the score line data (scaled, 80 store words + max) -> one copy per logical lane from replica selects;
//   - sp: selected by kept copies of pending (hi loads every edge, the hold term is dropped: sp is consumed only
//     with sv).  This equals the original on every edge where i_sv && pending is low -- the fold2 schedule leaves an
//     idle edge after every two-lane vector, and the overlap is the original's own o_fault (still raised as before);
//   - sd: the hold term is dropped (sd is consumed only with av); the score store keeps the multiplier word (lane 0
//     from u_m's y, lane 1 from its kept replica) and one inactive flag per word, applied at the read;
//   - the context / inactive / sink / last / ctx tag lines are DRST 0 (data, qualified by their valid lines);
//   - u_m / u_a / u_e: the census-safe f12 / exp copies (rtl/dsrom_sys/s81_svc/ot_s81_svc_fp32_f12_cs.sv,
//     ot_s81_svc_exp_cs.sv; yosys EQ vs rtl/hdc).
// Lock-step bench against the original: tools/s81_dv/svc_cs/tb_sml_cs.sv.
module ot_s81_su_sml_fold2_cs #(
 parameter integer NVMAX=40, LM=5, LA=4, MUT=0
)(
 input wire clk, rst_in, sk_en, i_cv,
 input wire [6:0] i_nv,
 input wire [31:0] i_scale, i_sink,
 input wire i_sv, input wire [63:0] i_s,
 input wire i_mv, input wire [31:0] i_nmb,
 output reg o_mxv, output reg [63:0] o_mx,
 output reg o_ev, o_es, o_el, output reg [63:0] o_e,
 output reg o_fault
);
 localparam integer D_EXP=7*LM+8*LA+4, DE=LA+D_EXP;
 localparam integer NS=2*NVMAX;
 // reset relay: rr1 copies.  0 control, 1-2 write pointers lane 0 / 1, 3-4 roh, 5 u_m, 6 u_a, 7 u_mv, 8-9 u_ev, 10-26 u_e
 localparam integer NRN=27;
 reg rr0,rr1;
 always @(posedge clk or negedge rst_in)
  if(!rst_in) begin rr0<=0;rr1<=0;end else begin rr0<=1;rr1<=rr0;end
 (* keep = 1 *) reg [NRN-1:0] rnk;
 always @(posedge clk or negedge rst_in)
  if(!rst_in) rnk<={NRN{1'b0}}; else rnk<={NRN{rr0}};
 wire rn=rnk[0];
 function automatic [31:0] okey(input [31:0] x);
  okey=x[31]?~x:{1'b1,x[30:0]};
 endfunction
 reg sv,ske,pending;
 (* keep = 1 *) reg [4:0] cvk;          // cv: [0] nv, [1] scale[15:0], [2] scale[31:16], [3] sink[15:0], [4] sink[31:16]
 (* keep = 1 *) reg [8:0] mvk;          // mv: [0] control, [1] sd[15:0], [2] sd[31:16], [3] mbn[15:0], [4] mbn[31:16],
                                        //     [5..8] roh quarters
 (* keep = 1 *) reg [1:0] pk;           // pending: [0] sp[15:0], [1] sp[31:16]
 reg [6:0] nvp,nv;
 reg [NVMAX-1:0] nl;                    // one-hot of nv-1 (the write pointers' wrap bit)
 reg [31:0] scalep,sinkp,scale,sink,nmbp,sp,hi;
 reg ctx;
 always @(posedge clk) begin
  nvp<=i_nv;scalep<=i_scale;sinkp<=i_sink;nmbp<=i_nmb;ske<=sk_en;
  hi<=i_s[63:32];
  sp[15:0]<=pk[0]?hi[15:0]:i_s[15:0];
  sp[31:16]<=pk[1]?hi[31:16]:i_s[31:16];
  if(cvk[0]) begin nv<=nvp; nl<={{(NVMAX-1){1'b0}},1'b1}<<(nvp-7'd1); end
  if(cvk[1]) scale[15:0]<=scalep[15:0];
  if(cvk[2]) scale[31:16]<=scalep[31:16];
  if(cvk[3]) sink[15:0]<=sinkp[15:0];
  if(cvk[4]) sink[31:16]<=sinkp[31:16];
 end
 always @(posedge clk or negedge rn)
  if(!rn) begin cvk<=0;sv<=0;mvk<=0;pending<=0;pk<=0;ctx<=0;o_fault<=0;end
  else begin
   cvk<={5{i_cv}};mvk<={9{i_mv}};sv<=i_sv||pending;ctx<=pending;
   pending<=i_sv;pk<={2{i_sv}};
   if(i_sv&&pending) o_fault<=1;
  end
 wire mv=mvk[0];
 // score-side lines: smv (valid, reset) with 2 kept last-stage copies; ctx / inactive (data, DRST 0) with kept
 // last-stage copies: wc [0] wcnt / rmax / mx control, [1] lane 0 writes, [2] lane 1 writes; inactive per lane
 reg [LM:1] mvl;
 always @(posedge clk or negedge rnk[7]) if(!rnk[7]) mvl[LM-1:1]<=0; else mvl[LM-1:1]<={mvl[LM-2:1],sv};
 // smv / wc copies: [0] wcnt / o_mxv control, [1..4] rmax[0] lo / hi, rmax[1] lo / hi, [5..8] mxlo lo / hi, o_mx
 // lo / hi quarters ... (see below), [9..14] lane 0 pointer A lo / hi, B lo / hi, data A / B, [15..20] lane 1 the same
 localparam integer NSK=21;
 (* keep = 1 *) reg [NSK-1:0] smvk;
 always @(posedge clk or negedge rnk[7]) if(!rnk[7]) smvk<=0; else smvk<={NSK{mvl[LM-1]}};
 reg [LM-1:1] mcl, mil;
 (* keep = 1 *) reg [NSK:0] wck;       // [0..NSK-1] as smvk, [NSK] rmax read
 (* keep = 1 *) reg [2:0] inak;        // [0] lane 0 flags, [1] lane 1 flags, [2] max
 always @(posedge clk) begin
  mcl<={mcl[LM-2:1],ctx}; mil<={mil[LM-2:1],sv&&sp==32'hff800000};
  wck<={(NSK+1){mcl[LM-1]^(MUT==1)}}; inak<={3{mil[LM-1]}};
 end
 wire [31:0] raw;
 wire mf;
 wire [31:0] rawr, rawm;                            // kept replicas of u_m's y (lane 1 store words / max)
 ot_s81_svc_qmul_lat_cs #(.LAT(LM),.YXR(3)) u_m(clk,rnk[5],sv,sp==32'hff800000 ? 32'd0:sp,scale,raw,mf,rawr,rawm);
 wire [31:0] scaled=inak[2]?32'hff800000:rawm;     // max / mx
 wire wc=wck[0];
 reg [31:0] sbuf[0:NS-1];                           // multiplier words; sflag: the word is the inactive -inf
 reg [NS-1:0] sflag;
 reg [6:0] wcnt[0:1];reg [31:0] rmax[0:1];reg [31:0] mxlo;
 wire [31:0] rmax_w=rmax[wck[NSK]];
 wire [31:0] maxnow=(wcnt[wc]==0 || okey(scaled)>okey(rmax_w))?scaled:rmax_w;
 // one-hot write pointers wp[lane][copy] = one-hot(wcnt[lane]); copy A: store word bits [15:0] + flag, B: [31:16]
 localparam integer PH=NVMAX/2;
 genvar gk, gl, gc;
 generate for(gl=0;gl<2;gl=gl+1) begin : g_wl
  for(gc=0;gc<2;gc=gc+1) begin : g_wc
   reg [NVMAX-1:0] wp;
   wire elo=smvk[9+6*gl+2*gc]&&(wck[9+6*gl+2*gc]==gl), ehi=smvk[10+6*gl+2*gc]&&(wck[10+6*gl+2*gc]==gl);
   wire wrap=|(wp&nl);
   always @(posedge clk or negedge rnk[1+gl])
    if(!rnk[1+gl]) wp<={{(NVMAX-1){1'b0}},1'b1};
    else begin
     if(elo) wp[PH-1:0]<={wp[PH-2:0]&~nl[PH-2:0],wrap};
     if(ehi) wp[NVMAX-1:PH]<=wp[NVMAX-2:PH-1]&~nl[NVMAX-2:PH-1];
    end
  end
  wire ed0=smvk[13+6*gl]&&(wck[13+6*gl]==gl), ed1=smvk[14+6*gl]&&(wck[14+6*gl]==gl);
  wire [31:0] wd=(gl==0)?raw:rawr;
  for(gk=0;gk<NVMAX;gk=gk+1) begin : g_sw
   always @(posedge clk) begin
    if(ed0&&g_wc[0].wp[gk]) begin sbuf[2*gk+gl][15:0]<=wd[15:0]; sflag[2*gk+gl]<=inak[gl]; end
    if(ed1&&g_wc[1].wp[gk]) sbuf[2*gk+gl][31:16]<=wd[31:16];
   end
  end
 end endgenerate
 wire smv=smvk[0];
 wire last=(wcnt[wc]+7'd1==nv);
 always @(posedge clk) begin
  if(smvk[1]&&!wck[1]) rmax[0][15:0]<=maxnow[15:0];
  if(smvk[2]&&!wck[2]) rmax[0][31:16]<=maxnow[31:16];
  if(smvk[3]&&wck[3]) rmax[1][15:0]<=maxnow[15:0];
  if(smvk[4]&&wck[4]) rmax[1][31:16]<=maxnow[31:16];
  if(smvk[5]&&!wck[5]&&last) mxlo[15:0]<=maxnow[15:0];
  if(smvk[6]&&!wck[6]&&last) mxlo[31:16]<=maxnow[31:16];
  if(smvk[7]&&wck[7]&&last) begin o_mx[15:0]<=mxlo[15:0]; o_mx[47:32]<=maxnow[15:0]; end
  if(smvk[8]&&wck[8]&&last) begin o_mx[31:16]<=mxlo[31:16]; o_mx[63:48]<=maxnow[31:16]; end
 end
 always @(posedge clk or negedge rn)
  if(!rn) begin wcnt[0]<=0;wcnt[1]<=0;o_mxv<=0;end
  else begin
   o_mxv<=smv&&wc&&(wcnt[1]+7'd1==nv);
   if(smv) wcnt[wc]<=(wcnt[wc]+7'd1==nv)?7'd0:wcnt[wc]+7'd1;
  end
 // Read alternate logical lanes from one score word per edge. A single sink
 // event precedes lane0 of row0; only physical lane0 enables that event.
 reg [31:0] mbn,sd;
 reg [6:0] rcnt;
 reg rd_on,rctx,rv,rsink,rlast,rectx;
 (* keep = 1 *) reg [3:0] rdk;          // rd_on copies: roh quarter shifts
 // one-hot read pointer roh[i] = (2*rcnt+rctx == i), four quarters (two reset halves)
 localparam integer RQ=NS/4;
 reg [NS-1:0] roh;
 always @(posedge clk or negedge rnk[3])
  if(!rnk[3]) roh[RQ-1:0]<={{(RQ-1){1'b0}},1'b1};
  else if(mvk[5]) roh[RQ-1:0]<={{(RQ-1){1'b0}},1'b1};
  else if(rdk[0]) roh[RQ-1:0]<={roh[RQ-2:0],1'b0};
 genvar gq;
 generate for(gq=1;gq<4;gq=gq+1) begin : g_rq
  always @(posedge clk or negedge rnk[3+gq/2])
   if(!rnk[3+gq/2]) roh[gq*RQ+RQ-1:gq*RQ]<={RQ{1'b0}};
   else if(mvk[5+gq]) roh[gq*RQ+RQ-1:gq*RQ]<={RQ{1'b0}};
   else if(rdk[gq]) roh[gq*RQ+RQ-1:gq*RQ]<=roh[gq*RQ+RQ-2:gq*RQ-1];
 end endgenerate
 reg [31:0] rdw;
 reg rdf;
 integer ki;
 always @* begin
  rdw=32'd0; rdf=1'b0;
  for(ki=0;ki<NS;ki=ki+1) begin rdw=rdw|({32{roh[ki]}}&sbuf[ki]); rdf=rdf|(roh[ki]&sflag[ki]); end
 end
 wire [31:0] rds=rdf?32'hff800000:rdw;              // = the original's stored (scaled) word
 always @(posedge clk) begin
  if(mvk[3]) mbn[15:0]<=nmbp[15:0];
  if(mvk[4]) mbn[31:16]<=nmbp[31:16];
  sd[15:0]<=mvk[1]?sink[15:0]:rds[15:0];
  sd[31:16]<=mvk[2]?sink[31:16]:rds[31:16];
 end
 always @(posedge clk or negedge rn)
  if(!rn) begin rd_on<=0;rdk<=0;rcnt<=0;rctx<=0;rv<=0;rsink<=0;rlast<=0;rectx<=0;end
  else begin
   rv<=rd_on;rsink<=mv&&ske;rlast<=rd_on&&rctx&&(rcnt+7'd1==nv);rectx<=rctx;
   if(mv) begin rd_on<=1;rdk<=4'hf;rcnt<=0;rctx<=0;end
   else if(rd_on) begin
    rctx<=~rctx;
    if(rctx) begin rcnt<=rcnt+7'd1;if(rcnt+7'd1==nv) begin rd_on<=0;rdk<=4'h0;end end
   end
  end
 wire av=rv||rsink;
 // exp-side lines: ev (valid, two reset halves, last stage kept x7); el / es / ec / ei (data, DRST 0), last stages
 // kept: es / ec x7 ([0..3] o_e 16-bit quarters, [4..5] elo halves, [6] o_ev / o_es / o_el), ei x4 (val 16-bit
 // halves for o_e low / elo and o_e high)
 wire [DE-1:0] evl;
 ot_s81_svc_vline2_cs #(.D(DE-1)) u_ev(.clk(clk),.rst_a(rnk[8]),.rst_b(rnk[9]),.v(av),.vd(evl));
 (* keep = 1 *) reg [6:0] evk;
 always @(posedge clk or negedge rnk[9]) if(!rnk[9]) evk<=7'b0; else evk<={7{evl[DE-1]}};
 wire [DE:0] ev={evk[0],evl};
 reg [DE-1:1] ell, esl, ecl, eil;
 (* keep = 1 *) reg [6:0] esk, eck;
 (* keep = 1 *) reg [3:0] eik;
 reg el_d;
 always @(posedge clk) begin
  ell<={ell[DE-2:1],rlast}; esl<={esl[DE-2:1],rsink}; ecl<={ecl[DE-2:1],rectx}; eil<={eil[DE-2:1],rv&&sd==32'hff800000};
  el_d<=ell[DE-1]; eck<={7{ecl[DE-1]}}; esk<={7{esl[DE-1]}}; eik<={4{eil[DE-1]}};
 end
 wire [31:0] ad,ex;wire af,ef;
 ot_s81_svc_qadd_lat_cs #(.KEEP(1),.LAT(LA)) u_a(clk,rnk[6],av,sd,mbn,ad,af);
 ot_s81_svc_exp_cs #(.LM(LM),.LA(LA)) u_e(.clk(clk),.rst_n(rnk[26:10]),.v(ev[LA]),.x(ad),.y(ex),.vo(),.fault(ef));
 wire [31:0] val0={eik[1]?16'd0:ex[31:16],eik[0]?16'd0:ex[15:0]};   // o_e[31:0] / elo
 wire [31:0] val1={eik[3]?16'd0:ex[31:16],eik[2]?16'd0:ex[15:0]};   // o_e[63:32]
 reg [31:0] elo;
 // = if(ev) begin if(es) o_e<={0,val}; else if(!ec) elo<=val; else o_e<={val,elo}; end
 always @(posedge clk) begin
  if(evk[0]&&(esk[0]||eck[0])) o_e[15:0]<=esk[0]?val0[15:0]:elo[15:0];
  if(evk[1]&&(esk[1]||eck[1])) o_e[31:16]<=esk[1]?val0[31:16]:elo[31:16];
  if(evk[2]&&(esk[2]||eck[2])) o_e[47:32]<=esk[2]?16'd0:val1[15:0];
  if(evk[3]&&(esk[3]||eck[3])) o_e[63:48]<=esk[3]?16'd0:val1[31:16];
  if(evk[4]&&!esk[4]&&!eck[4]) elo[15:0]<=val0[15:0];
  if(evk[5]&&!esk[5]&&!eck[5]) elo[31:16]<=val0[31:16];
 end
 always @(posedge clk or negedge rn)
  if(!rn)begin o_ev<=0;o_es<=0;o_el<=0;end
  else begin o_ev<=evk[6]&&(esk[6]||eck[6]);o_es<=evk[6]&&esk[6];o_el<=evk[6]&&el_d;end
endmodule
