(* blackbox *) module ot_s81_engram_mul4 #(parameter integer LM=5,MUT=0)(
 input wire clk,arst_n,v,phase,input wire [127:0] h,k,w,
 output wire vo,output wire [127:0] hh,kk,dot,output reg fault);
endmodule
(* blackbox *) module ot_s81_engram_chunk8 #(parameter integer LA=4)(
 input wire clk,arst_n,v,input wire [255:0] x,
 output wire vo,output wire [31:0] sum,output reg fault);
endmodule
(* blackbox *) module ot_s81_engram_add8 #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,phase,input wire [255:0] h,value,input wire [31:0] gate,input wire [1:0] copy,
 output reg vo,output reg [255:0] y,output reg fault,output wire [1:0] copy_out);
endmodule
(* blackbox *) module ot_s81_engram_norm #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] sum,eps,
 output wire vo,output wire [31:0] rstd,output reg fault);
endmodule
(* blackbox *) module ot_s81_engram_sum #(parameter integer N=32,D=5120,LA=4)(
 input wire clk,arst_n,go,v,
 output reg vo,output reg [31:0] y,output reg fault,
 input wire [N/8*32-1:0] chunks,input wire [N/8-1:0] chunk_fault,chunk_valid);
endmodule
(* blackbox *) module ot_s81_engram_signed_sqrt #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] x,
 output reg vo,output reg [31:0] y,output reg fault);
endmodule
(* blackbox *) module ot_s81_engram_sigmoid #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] x,
 output reg vo,output reg [31:0] y,output reg fault);
endmodule
(* blackbox *) module ot_s81_engram_mix_control #(parameter integer N=32, D=5120, LM=5, LA=4, MUT=0, RLY=0)(
 input wire clk,arst_n,go,phase,in_v,
 input wire [1:0] copy,
 input wire [31:0] scale,
 output wire gate_v, output wire [1:0] gate_copy,
 output wire [31:0] gate,hh,kk,dd,
 output wire fault,
 output wire g_v,
 output wire [31:0] a_gate,g_x,
 input wire [7:0] mvalid,mfault,input wire [3:0] avalid,af,input wire [7:0] add_copy,
 input wire [1:0] nv,nf,input wire [63:0] norm_rstd,
 input wire eg_valid,input wire [1:0] g_fault,input wire [31:0] gy,
 input wire [2:0] rv,rf,input wire [31:0] rhh,rkk,rdd);
endmodule
(* blackbox *) module ot_s81_engram_rly(input wire clk,arst_n,input wire [68:0] up_i,input wire [35:0] dn_i,
 output reg [68:0] up_o,output reg [35:0] dn_o);
endmodule
(* blackbox *) module ot_s81_engram_mixq_shcol_b #(parameter integer MUT=0)(
 input wire ck,input wire rst,input wire [4:0] rs_v,input wire [639:0] rs_d,input wire ov,
 input wire [255:0] result,
 output reg [255:0] h,kv,w,output reg [127:0] wq_d,output reg iv,ph);
endmodule
(* blackbox *) module ot_s81_engram_mixq_shctl #(parameter integer MUT=0, VM_LAT=3, WRITE_COMMIT_LAT=1, HLAYOUT=1)(
 input wire ck,input wire rst,input wire start,input wire [223:0] desc,
 output reg [4:0] rq_v,output reg [69:0] rq_row,output reg vtag,
 input wire [4:0] rs_v,
 output reg wq_v,output reg [13:0] wq_row,output reg [15:0] wq_mask,
 output reg done,output reg fault,
 output reg go,iv,phase,output wire [1:0] copy,
 output wire [31:0] eps,scale,
 input wire gv,ov,mf,input wire [1:0] gc,oc,
 output reg fr,fa);
endmodule
module ot_s81_engram_mixq_b #(parameter integer MUT=0, VM_LAT=3, WRITE_COMMIT_LAT=1, HLAYOUT=1, N=32, D=5120, LM=5, LA=4)(
 input wire [51:0] ck,input wire rst,input wire start,input wire [223:0] desc,
 output wire [4:0] rq_v,output wire [69:0] rq_row,output wire vtag,
 input wire [4:0] rs_v,input wire [2559:0] rs_d,
 output wire wq_v,output wire [13:0] wq_row,output wire [15:0] wq_mask,output wire [511:0] wq_d,
 output wire done,output wire fault);
 localparam integer MM=(MUT==1)?1:(MUT==22)?22:0;   // multiplier-leaf mutants, as ot_s81_engram_mixq
 wire [30:0] ck_leaf=ck[36:6];
 // ---- shell: control leaf + four own-column payload leaves
 wire go,iv,phase,ov,mf,gv;wire [1:0] copy,gc,oc;wire [31:0] eps,scale;wire fr,fa;
 wire [1023:0] h,kv,w,oy;wire [3:0] avalid,af;wire [7:0] add_copy;
 wire [3:0] c_iv,c_ph;                      // own-column issue valid / phase from shcol_b[c]
 wire [7:0] copy_b;wire [127:0] gate_b;   // relayed per band
 ot_s81_engram_mixq_shctl #(.MUT(MUT),.VM_LAT(VM_LAT),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.HLAYOUT(HLAYOUT)) ctl(
  .ck(ck[0]),.rst(rst),.start(start),.desc(desc),.rq_v(rq_v),.rq_row(rq_row),.vtag(vtag),.rs_v(rs_v),
  .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.done(done),.fault(fault),
  .go(go),.iv(iv),.phase(phase),.copy(copy),.eps(eps),.scale(scale),.gv(gv),.ov(ov),.mf(mf),.gc(gc),.oc(oc),.fr(fr),.fa(fa));
 // the shell's write-row counter takes the result valid of band 2's add8 (the inner band whose add8 pins face the spine) (all four add8 run in lockstep; the control
 // checks it); each payload column takes its own add8's valid (own-column, as the localized candidate).
 assign ov=avalid[2];assign oc=add_copy[5:4];
 genvar c;
 generate for(c=0;c<4;c=c+1)begin:col
  ot_s81_engram_mixq_shcol_b #(.MUT(MUT)) u(.ck(ck[c+1]),.rst(rst),.rs_v(rs_v),
   .rs_d({rs_d[1536+256*c+:256],rs_d[512+256*c+:256],rs_d[128*c+:128]}),
   .ov((MUT==26&&c==3)?1'b0:avalid[c]),.result(oy[256*c+:256]),
   .h(h[256*c+:256]),.kv(kv[256*c+:256]),.w(w[256*c+:256]),.wq_d(wq_d[128*c+:128]),.iv(c_iv[c]),.ph(c_ph[c]));
 end endgenerate
 // ---- arithmetic
 wire [7:0] mvalid,mfault;wire [1023:0] hd,kd,dot;
 wire [383:0] chunk_sums;wire [11:0] chunk_fault,chunk_valid;      // chunk8 outputs (band side)
 wire [383:0] chunk_sums_r;wire [11:0] chunk_fault_r,chunk_valid_r;// after the band relays (spine side)
 wire [7:0] mvalid_r,mfault_r,add_copy_r;wire [3:0] avalid_r,af_r;   // control inputs, two edges (band + side relay)
 wire [7:0] mvalid_b;wire [31:0] band_up;wire [35:0] side_dn[0:1];
 wire go_r,phase_r,in_v_r;wire [1:0] copy_r;wire [31:0] scale_r,eps_r;
 wire gate_v_c,fault_c;wire [1:0] gate_copy_c;wire [31:0] a_gate;
 // central relay: {eps 32, go, phase, in_v, copy 2, scale 32} toward the spine; {a_gate, gate_v, gate_copy, fault}
 // toward the shell (its a_gate output is unused: the add8 take a_gate from their band relay A).
 wire [31:0] a_gate_unused;
 ot_s81_engram_rly relay(ck[37],rst,{eps,go,phase,iv,copy,scale},{a_gate,gate_v_c,gate_copy_c,fault_c},
  {eps_r,go_r,phase_r,in_v_r,copy_r,scale_r},{a_gate_unused,gv,gc,mf});
 genvar b,r,g;
 generate for(b=0;b<4;b=b+1)begin:band
  // Three band relays per band, placed where their traffic is (the band is a vertical column: shell payload leaf at the
  // bottom, add8, mul4 pair, chunk8 rows at the top):
  //  rt0 (top)    up {pad, fault r1, fault r0, vo r1, vo r0, sum r1, sum r0}                    dn 36 pad bits
  //  rt1 (top)    up {pad 33, fault r2, vo r2, sum r2}                                         dn 36 pad bits
  //  rb  (bottom) up {pad 61, add_copy 2, af, avalid, mfault 2, mvalid 2}                       dn = side relay dn
  wire [68:0] t0_up,t1_up,b_up;wire [35:0] b_dn,t0_dn_unused,t1_dn_unused;
  wire [31:0] s0,s1,s2;
  ot_s81_engram_rly rt0(ck[38+b],rst,
   {1'b0,chunk_fault[4*1+b],chunk_fault[4*0+b],chunk_valid[4*1+b],chunk_valid[4*0+b],chunk_sums[32*(4*1+b)+:32],chunk_sums[32*(4*0+b)+:32]},
   36'd0,t0_up,t0_dn_unused);
  ot_s81_engram_rly rt1(ck[42+b],rst,{33'd0,chunk_fault[4*2+b],chunk_valid[4*2+b],chunk_sums[32*(4*2+b)+:32]},36'd0,t1_up,t1_dn_unused);
  ot_s81_engram_rly rb(ck[46+b],rst,{61'd0,add_copy[2*b+:2],af[b],avalid[b],mfault[2*b+:2],mvalid[2*b+:2]},side_dn[b/2],b_up,b_dn);
  assign band_up[8*b+:8]=b_up[7:0];
  assign {s1,s0}=t0_up[63:0];assign s2=t1_up[31:0];
  assign chunk_sums_r[32*(4*0+b)+:32]=(MUT==27&&b==2)?chunk_sums[32*(4*0+b)+:32]:s0;
  assign chunk_sums_r[32*(4*1+b)+:32]=(MUT==27&&b==2)?chunk_sums[32*(4*1+b)+:32]:s1;
  assign chunk_sums_r[32*(4*2+b)+:32]=(MUT==27&&b==2)?chunk_sums[32*(4*2+b)+:32]:s2;
  assign chunk_valid_r[4*0+b]=t0_up[64];assign chunk_valid_r[4*1+b]=t0_up[65];
  assign chunk_fault_r[4*0+b]=t0_up[66];assign chunk_fault_r[4*1+b]=t0_up[67];
  assign chunk_valid_r[4*2+b]=t1_up[32];assign chunk_fault_r[4*2+b]=t1_up[33];
  assign mvalid_b[2*b+:2]=b_up[1:0];                     // one edge: the sums' reference valid (aligned with chunks)
  assign gate_b[32*b+:32]=b_dn[35:4];assign copy_b[2*b+:2]=b_dn[1:0];
 end endgenerate
 // Side relays at the spine's W and E edges (second stage between the band relays and the control, which gathers from
 // both sides): toward the control {band c's mvalid 2, mfault 2, avalid, af, add_copy 2} of the two bands on that side,
 // and on the W side also go/phase/in_v/copy from the central relay, so every control input that is cross-checked against
 // in_v is exactly two edges from its producer (as one edge was through the old central relay); toward the bands
 // {a_gate, pad 2, gate_copy} (static from the gate on: add8 uses them only on ADD beats).
 wire [68:0] sl_up,sr_up;wire [35:0] sl_dn,sr_dn;
 ot_s81_engram_rly rsl(ck[50],rst,{48'd0,go_r,phase_r,in_v_r,copy_r,band_up[15:0]},{a_gate,2'b00,gate_copy_c},sl_up,sl_dn);
 ot_s81_engram_rly rsr(ck[51],rst,{53'd0,band_up[31:16]},{a_gate,2'b00,gate_copy_c},sr_up,sr_dn);
 assign side_dn[0]=sl_dn;assign side_dn[1]=sr_dn;
 wire go_c,phase_c,in_v_c;wire [1:0] copy_c;
 assign {go_c,phase_c,in_v_c,copy_c}=sl_up[20:16];
 wire [31:0] bu={sr_up[15:0],sl_up[15:0]};
 genvar u;
 generate for(u=0;u<4;u=u+1)begin:g_unpack
  assign mvalid_r[2*u+:2]=bu[8*u+:2];assign mfault_r[2*u+:2]=bu[8*u+2+:2];
  assign avalid_r[u]=bu[8*u+4];assign af_r[u]=bu[8*u+5];assign add_copy_r[2*u+:2]=bu[8*u+6+:2];
 end endgenerate
 wire [1:0] nv,nf;wire eg_valid,g_v;wire [1:0] g_fault;wire [31:0] g_x,gy,rhh,rkk,rdd,gate_o,hh_o,kk_o,dd_o;wire [63:0] norm_rstd;wire [2:0] rv,rf;
 ot_s81_engram_mix_control #(.N(N),.D(D),.LM(LM),.LA(LA),.MUT(MUT)) control(
  .clk(ck[5]),.arst_n(rst),.go(go_c),.phase(phase_c),.in_v(in_v_c),.copy(copy_c),.scale(scale_r),
  .gate_v(gate_v_c),.gate_copy(gate_copy_c),.gate(gate_o),.hh(hh_o),.kk(kk_o),.dd(dd_o),.fault(fault_c),
  .g_v(g_v),.a_gate(a_gate),.g_x(g_x),
  .mvalid(mvalid_r),.mfault(mfault_r),.avalid(avalid_r),.af(af_r),.add_copy(add_copy_r),.nv(nv),.nf(nf),.norm_rstd(norm_rstd),
  .eg_valid(eg_valid),.g_fault(g_fault),.gy(gy),.rv(rv),.rf(rf),.rhh(rhh),.rkk(rkk),.rdd(rdd));
 // sums: chunks and their reference valid both cross the band relays (sum v = band 1's / band 2's relayed mul4 valid,
 // as the old mvalid[2] / mvalid[4] choice); go from the central relay as before.
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) hsum(ck_leaf[23],rst,go_r,mvalid_b[2],rv[0],rhh,rf[0],chunk_sums_r[0+:128],chunk_fault_r[0+:4],chunk_valid_r[0+:4]);
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) ksum(ck_leaf[24],rst,go_r,mvalid_b[2],rv[1],rkk,rf[1],chunk_sums_r[128+:128],chunk_fault_r[4+:4],chunk_valid_r[4+:4]);
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) dsum(ck_leaf[25],rst,go_r,mvalid_b[4],rv[2],rdd,rf[2],chunk_sums_r[256+:128],chunk_fault_r[8+:4],chunk_valid_r[8+:4]);
 generate for(g=0;g<8;g=g+1)begin:g_mult
  ot_s81_engram_mul4 #(.LM(LM),.MUT(MM)) leaf(ck_leaf[(g%2)?(26+g/2):(g/2)],rst,(MUT==28&&g/2==3)?1'b0:c_iv[g/2],c_ph[g/2],
   h[128*g+:128],kv[128*g+:128],w[128*g+:128],mvalid[g],hd[128*g+:128],kd[128*g+:128],dot[128*g+:128],mfault[g]);
 end
 for(r=0;r<3;r=r+1)begin:g_reduce
  wire [1023:0] x=(r==0)?hd:(r==1)?kd:dot;
  for(c=0;c<4;c=c+1)begin:g_chunk
   ot_s81_engram_chunk8 #(.LA(LA)) leaf(ck_leaf[4+4*r+c],rst,mvalid[2*c],x[256*c+:256],
    chunk_valid[4*r+c],chunk_sums[32*(4*r+c)+:32],chunk_fault[4*r+c]);
  end
 end
 for(g=0;g<4;g=g+1)begin:g_add
  ot_s81_engram_add8 #(.LM(LM),.LA(LA)) leaf(ck_leaf[16+g],rst,(MUT==28&&g==3)?1'b0:c_iv[g],c_ph[g],
   h[256*g+:256],kv[256*g+:256],gate_b[32*g+:32],copy_b[2*g+:2],avalid[g],oy[256*g+:256],af[g],add_copy[2*g+:2]);
 end
 for(g=0;g<2;g=g+1)begin:g_norm
  ot_s81_engram_norm #(.LM(LM),.LA(LA)) leaf(ck_leaf[20+g],rst,rv[g],g==0?rhh:rkk,eps_r,nv[g],norm_rstd[32*g+:32],nf[g]);
 end endgenerate
 ot_s81_engram_gate #(.LM(LM),.LA(LA)) gate_leaf(ck_leaf[22],rst,g_v,g_x,eg_valid,gy,g_fault,ck_leaf[30]);
endmodule
module ot_s81_engram_gate #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] x,
 output wire vo,output wire [31:0] y,output wire [1:0] fault,input wire clk_sigmoid);
 wire sqrt_v;wire [31:0] signed_sqrt;
 ot_s81_engram_signed_sqrt #(.LM(LM),.LA(LA)) magnitude(clk,arst_n,v,x,sqrt_v,signed_sqrt,fault[0]);
 ot_s81_engram_sigmoid #(.LM(LM),.LA(LA)) sigmoid(clk_sigmoid,arst_n,sqrt_v,signed_sqrt,vo,y,fault[1]);
endmodule