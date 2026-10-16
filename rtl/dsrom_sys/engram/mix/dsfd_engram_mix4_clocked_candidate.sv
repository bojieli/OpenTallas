`timescale 1ns/1ps
// HELD physical clock-partition candidate. Exact arithmetic and fixed RS stages preserved.
// RS5 adds40 real station entries (189 total); top ck0 localization remains unqualified.
module dsfd_engram_mix4_clocked_candidate #(parameter integer MUT=0, VM_LAT=1, WRITE_COMMIT_LAT=1, BC=2, RS=5, HLAYOUT=1)(
 input wire [148+8*RS:0] ck,              // ck[0] top; ck[1+37q +: 37] cluster q roots
 input wire [0:0] rst,input wire [84:0] c_cmd,
 output wire [8:0] c_done,output wire [1:0] c_st,
`ifndef DSFD_ENGRAM_STATIC_ISSUE
 input wire [0:0] f_inp,
`endif
 output reg [19:0] rq_v,output reg [279:0] rq_row,
 input wire [19:0] rs_v,input wire [10239:0] rs_d,
 output wire [3:0] wq_v,output wire [55:0] wq_row,
 output wire [63:0] wq_mask,output wire [2047:0] wq_d);

 reg [1:0] reset_sync;
 always @(posedge ck[0] or negedge rst[0])if(!rst[0])reset_sync<=0;else reset_sync<={reset_sync[0],1'b1};
 wire rn=reset_sync[1];
 wire jv,jnew,epf;wire [83:0] jd,jnd;reg done,fault;reg inp_q;
`ifdef DSFD_ENGRAM_STATIC_ISSUE
 // Compiled issue edge proves operand availability; late/missing VM results remain faults.
 always @(posedge ck[0] or negedge rn)if(!rn)inp_q<=0;else inp_q<=1'b1;
`else
 always @(posedge ck[0] or negedge rn)if(!rn)inp_q<=0;else inp_q<=f_inp[0];
`endif
 ot_s81_slab_ep ep(.c_clk(ck[0]),.c_rst_n(rn),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),
  .e_clk(ck[0]),.e_rst_n(rn),.j_v(jv),.j_d(jd),.j_new(jnew),.j_new_d(jnd),.j_present(1'b1),.j_done(done),.slab_fault(fault),.ep_fault(epf));

 // ---- cluster interfaces
 wire [19:0] c_rqv;wire [279:0] c_rqrow;wire [3:0] c_vtag;   // vtag: this cycle's lanes 1,2 request is V
 wire [3:0] c_done_q,c_fault_q;
 wire [3:0] c_wq_v;wire [2047:0] c_wq_d;                     // cluster write lanes (copy-major data)
 assign wq_v=c_wq_v;
 genvar wj,we,wk;
 generate if(HLAYOUT!=0)begin:g_hwr
  for(wj=0;wj<4;wj=wj+1)for(we=0;we<8;we=we+1)for(wk=0;wk<4;wk=wk+1)begin:p
   assign wq_d[512*wj+16*(4*we+wk)+:16]=c_wq_d[512*wk+16*(8*wj+we)+:16];
  end
 end else begin:g_cwr
  assign wq_d=c_wq_d;
 end endgenerate
 reg [19:0] l_rsv;reg [10239:0] l_rsd;                        // returns delivered to the clusters
 reg [BC:0] st_line;reg [223:0] desc_line[0:BC];

 // ---- descriptor read (top), static: issued only while every cluster is idle
 reg [2:0] tstate;localparam T_IDLE=0,T_DESC=1,T_RUN=2,T_DONE=3,T_POP=4;
 // Descriptor bit18 selects operand storage; it is not part of the H row address.
 wire [31:0] desc_hrow=rdq[0+:32]&32'hfffbffff;
 wire [31:0] desc_kw_span=rdq[18]?32'd5120:32'd1280;
 wire [31:0] desc_v_span=rdq[18]?32'd640:32'd320;
 reg desc_rq;reg [1023:0] v_prev;
 // registered request stage: lane 0 of cluster 0 doubles as descriptor reader,
 // lanes 1,2 of clusters 1..3 are suppressed for V (cluster 0 reads V once).
 integer q,l,hm;
 always @(posedge ck[0] or negedge rn)if(!rn)begin rq_v<=0;rq_row<=0;end else begin
  rq_v<=c_rqv;rq_row<=c_rqrow;
  for(q=1;q<4;q=q+1)if(c_vtag[q])begin rq_v[5*q+1]<=0;rq_v[5*q+2]<=0;end
  if(desc_rq)begin rq_v[0]<=1'b1;rq_row[0+:14]<=jd[7+:14];end
 end
 // fixed-latency tag lines: request flop (+1) -> VM (VM_LAT) -> return pin flop (+1)
 localparam integer TL=VM_LAT+1;
 reg [TL:0] dtag;reg [TL:0] vtag;
 always @(posedge ck[0] or negedge rn)if(!rn)begin dtag<=0;vtag<=0;end else begin
  dtag<={dtag[TL-1:0],desc_rq};vtag<={vtag[TL-1:0],c_vtag[0]};
 end
 reg [19:0] rvq;reg [10239:0] rdq;
 always @(posedge ck[0] or negedge rn)if(!rn)rvq<=0;else rvq<=rs_v;
 always @(posedge ck[0])rdq<=rs_d;
 // return demux (combinational after the registered pin stage; the clusters
 // capture in their own rvq/rdq flops)
 always @*begin
  l_rsv=rvq;l_rsd=rdq;
  if(dtag[TL])begin l_rsv[0]=1'b0;end
  for(q=0;q<4;q=q+1)if(vtag[TL])begin
   l_rsv[5*q+1]=rvq[1];l_rsv[5*q+2]=rvq[2];
   l_rsd[2560*q+512+:1024]=(MUT==3&&q!=0)?v_prev:rdq[512+:1024];
  end
  if(HLAYOUT!=0)for(q=0;q<4;q=q+1)for(hm=0;hm<32;hm=hm+1)
   l_rsd[2560*q+16*hm+:16]=rdq[2560*(hm/8)+16*(4*(hm%8)+q)+:16];
 end

 always @(posedge ck[0] or negedge rn)if(!rn)begin
  tstate<=T_IDLE;desc_rq<=0;done<=0;fault<=0;st_line<=0;
 end else begin
  desc_rq<=0;done<=0;st_line<={st_line[BC-1:0],1'b0};
  if(epf||(|c_fault_q))fault<=1;
  if(dtag[TL]&&!rvq[0])fault<=1;                      // lost descriptor reply
  if(desc_rq&&c_rqv[0])fault<=1;                          // lane 0 reservation clash
  if(c_vtag!=4'b0000&&c_vtag!=4'b1111)fault<=1;           // clusters out of lockstep
  if(HLAYOUT!=0&&!dtag[TL]&&{rvq[15],rvq[10],rvq[5],rvq[0]}!=4'b0000&&{rvq[15],rvq[10],rvq[5],rvq[0]}!=4'b1111)fault<=1; // H rows re-sliced across clusters
  if(HLAYOUT!=0&&c_wq_v!=4'b0000&&c_wq_v!=4'b1111)fault<=1;                       // interleaved H writes need all four
  case(tstate)
  T_IDLE:if(jv&&!fault)begin
   if(!inp_q||jd[30:21]!=0)fault<=1;else begin desc_rq<=1;tstate<=T_DESC;end
  end
  T_DESC:if(dtag[TL])begin
   if(desc_hrow>15744||rdq[32+:32]>16384-desc_kw_span||rdq[64+:32]>16384-desc_kw_span||rdq[96+:32]>16384-desc_v_span||rdq[128+:32]>15744)fault<=1;
   if((rdq[128+:32]!=desc_hrow && rdq[128+:32]<desc_hrow+640 && desc_hrow<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[32+:32]+desc_kw_span && rdq[32+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[64+:32]+desc_kw_span && rdq[64+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[96+:32]+desc_v_span && rdq[96+:32]<rdq[128+:32]+640))fault<=1;
   if(rdq[191] || rdq[183+:8]==255 || rdq[160+:31]==0 || rdq[223] || rdq[215+:8]==255 || rdq[192+:31]==0)fault<=1;
   st_line[0]<=1'b1;tstate<=T_RUN;
  end
  T_RUN:begin
   // four-done join: all four in the same cycle, or fault
   if(|c_done_q)begin if(c_done_q!=4'b1111)fault<=1;tstate<=T_DONE;end
  end
  T_DONE:begin done<=!fault&&!epf;tstate<=T_POP;end
  T_POP:tstate<=T_IDLE;                                   // queue head pops with done
  default:fault<=1;
  endcase
 end
 always @(posedge ck[0])begin
  desc_line[0]<=(tstate==T_DESC&&dtag[TL])?rdq[0+:224]:desc_line[0];
  if(vtag[TL])v_prev<=rdq[512+:1024];
 end
 genvar s,c;
 generate for(s=1;s<=BC;s=s+1)begin:bc_tree
  always @(posedge ck[0])desc_line[s]<=desc_line[s-1];
 end
 for(c=0;c<4;c=c+1)begin:cl
  // cluster-side wires; the top-side ends cross RS relay stations (toward the cluster: start/desc + returns; toward
  // the top/VM: requests, writes, done/fault)
  wire k_rqv_v;wire [4:0] k_rqv;wire [69:0] k_rqrow;wire k_vtag,k_wv,k_done,k_fault;wire [13:0] k_wrow;wire [15:0] k_wmask;wire [511:0] k_wd;
  wire [4:0] k_rsv;wire [2559:0] k_rsd;wire k_start;wire [223:0] k_desc;
  wire [((RS>0)?RS:1)-1:0] up_ck, down_ck;
  if(RS>0)begin:g_station_clocks
   assign up_ck=ck[149+2*RS*c+:RS];
   assign down_ck=ck[149+2*RS*c+RS+:RS];
  end else begin:g_no_station_clocks
   assign up_ck=ck[0];assign down_ck=ck[0];
  end
  ot_s81_engram_vrly_clocked #(.D(RS),.WV(5+1+1+1+1),.WD(70+14+16+512)) up(up_ck,rn,
   {k_rqv,k_vtag,k_wv,k_done,k_fault},{k_rqrow,k_wrow,k_wmask,k_wd},
   {c_rqv[5*c+:5],c_vtag[c],c_wq_v[c],c_done_q[c],c_fault_q[c]},{c_rqrow[70*c+:70],wq_row[14*c+:14],wq_mask[16*c+:16],c_wq_d[512*c+:512]});
  // per-cluster descriptor: the copy's row bases and its copy index are folded here in the top (ONE cluster master
  // for all four clusters, no per-instance constant or strap in the cluster); MUT 2 moves cluster 3's H base onto
  // copy 2's rows.
  localparam [1:0] CC=c;wire [223:0] cdesc;
  assign cdesc[13:0]=(HLAYOUT!=0)?desc_line[BC][13:0]+((MUT==2&&c==3)?14'd2:14'(c)):(MUT==2&&c==3)?desc_line[BC][13:0]+14'd320:desc_line[BC][13:0]+14'd160*c;
  assign cdesc[31:14]={desc_line[BC][31:18],CC,desc_line[BC][15:14]};
  assign cdesc[45:32]=desc_line[BC][18]?desc_line[BC][45:32]:desc_line[BC][45:32]+14'd320*c;assign cdesc[63:46]=desc_line[BC][63:46];
  assign cdesc[77:64]=desc_line[BC][18]?desc_line[BC][77:64]:desc_line[BC][77:64]+14'd320*c;assign cdesc[127:78]=desc_line[BC][127:78];
  assign cdesc[141:128]=desc_line[BC][141:128]+((HLAYOUT!=0)?14'(c):14'd160*c);assign cdesc[223:142]=desc_line[BC][223:142];
  // start leaves the top ONE edge early (st_line[BC-1]); the cluster's shell control registers it in start_q at its
  // input pin (S-ENGRAM 10-15 native capture repair: shctl start capture 224.78 > 190 ps), so start_q is high in the
  // same cycle the old pin was and cdesc (st_line[BC] timing) is sampled on the same edge: 0 added cycles.
  ot_s81_engram_vrly_clocked #(.D(RS),.WV(5+1),.WD(2560+224)) down(down_ck,rn,
   {l_rsv[5*c+:5],st_line[BC-1]},{l_rsd[2560*c+:2560],cdesc},{k_rsv,k_start},{k_rsd,k_desc});
  ot_s81_engram_mixq #(.MUT(MUT),.VM_LAT(VM_LAT+2+2*RS),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.HLAYOUT(HLAYOUT)) u(
   .ck(ck[1+37*c+:37]),.rst(rst[0]),.start(k_start),.desc(k_desc),
   .rq_v(k_rqv),.rq_row(k_rqrow),.vtag(k_vtag),
   .rs_v(k_rsv),.rs_d(k_rsd),
   .wq_v(k_wv),.wq_row(k_wrow),.wq_mask(k_wmask),.wq_d(k_wd),
   .done(k_done),.fault(k_fault));
 end endgenerate
endmodule

// One actual clock entry per physical stage. The die must deliver phi-R independently.
module ot_s81_engram_vrly_clocked #(parameter integer D=1,WV=1,WD=1)(
 input wire [((D>0)?D:1)-1:0] ck,input wire rst_n,
 input wire [WV-1:0] v_i,input wire [WD-1:0] d_i,
 output wire [WV-1:0] v_o,output wire [WD-1:0] d_o);
 generate if(D==0)begin:g_w assign v_o=v_i;assign d_o=d_i;
 end else begin:g_r
  wire [WV-1:0] v[0:D];wire [WD-1:0] d[0:D];
  assign v[0]=v_i;assign d[0]=d_i;
  for(genvar k=0;k<D;k=k+1)begin:stage
   reg [WV-1:0] vr;reg [WD-1:0] dr;
   always @(posedge ck[k] or negedge rst_n)if(!rst_n)vr<=0;else vr<=v[k];
   always @(posedge ck[k])dr<=d[k];
   assign v[k+1]=vr;assign d[k+1]=dr;
  end
  assign v_o=v[D];assign d_o=d[D];
 end endgenerate
endmodule
