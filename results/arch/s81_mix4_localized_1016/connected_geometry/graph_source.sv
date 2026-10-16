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
(* blackbox *) module ot_s81_engram_mixq_shcol #(parameter integer MUT=0)(
 input wire ck,input wire rst,input wire [4:0] rs_v,input wire [639:0] rs_d,input wire fr,fa,ov,
 input wire [255:0] result,
 output reg [255:0] h,kv,w,output reg [127:0] wq_d);
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
module ot_s81_engram_mixq_clocked_candidate #(parameter integer MUT=0, VM_LAT=3, WRITE_COMMIT_LAT=1, HLAYOUT=1)(
 input wire [37:0] ck,input wire rst,input wire start,input wire [223:0] desc,
 output wire [4:0] rq_v,output wire [69:0] rq_row,output wire vtag,
 input wire [4:0] rs_v,input wire [2559:0] rs_d,
 output wire wq_v,output wire [13:0] wq_row,output wire [15:0] wq_mask,output wire [511:0] wq_d,
 output wire done,output wire fault);
 // Wires-only composition: shell owns five independent clock entries ck[4:0]; arithmetic owns ck[36:5].
 wire go,iv,phase,gv,ov,mf;wire [1:0] copy,gc,oc;
 wire [1023:0] h,kv,w,result;wire [31:0] eps,scale,gate,hh,kk,dd;
 ot_s81_engram_mixq_shell #(.MUT(MUT),.VM_LAT(VM_LAT),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.HLAYOUT(HLAYOUT)) shell(
  .ck(ck[4:0]),.rst(rst),.start(start),.desc(desc),
  .rq_v(rq_v),.rq_row(rq_row),.vtag(vtag),.rs_v(rs_v),.rs_d(rs_d),
  .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.wq_d(wq_d),.done(done),.fault(fault),
  .go(go),.iv(iv),.phase(phase),.copy(copy),.h(h),.kv(kv),.w(w),.eps(eps),.scale(scale),
  .gv(gv),.gc(gc),.ov(ov),.oc(oc),.result(result),.mf(mf));
 ot_s81_engram_mix_relay_clocked_candidate #(.MUT(MUT==1?1:MUT==22?22:0)) mix(ck[5],rst,go,phase,iv,copy,h,kv,w,kv,eps,scale,
  gv,gc,gate,hh,kk,dd,ov,oc,result,mf,ck[36:6],(MUT==23?1'b0:ck[37]));
endmodule
module ot_s81_engram_mix_relay_clocked_candidate #(parameter integer N=32, D=5120, LM=5, LA=4, MUT=0)(
 input wire clk,arst_n,go,phase,in_v,
 input wire [1:0] copy,
 input wire [N*32-1:0] h,key,weight,value,
 input wire [31:0] eps,scale,
 output wire gate_v, output wire [1:0] gate_copy,
 output wire [31:0] gate,hh,kk,dd,
 output wire out_v, output wire [1:0] out_copy,
 output wire [N*32-1:0] out_data,
 output wire fault,input wire [30:0] ck_leaf,input wire relay_clk);

 wire g_v;
 wire [31:0] a_gate,g_x,gy;wire [63:0] norm_rstd;
 wire [7:0] mvalid,mfault,add_copy;wire [3:0] avalid,af;wire [1023:0] hd,kd,dot,oy;
 // Physical hierarchy (S-ELEM-C 2026-10-15, MIX4 home 771 x 3229, results/arch/s81_mix4_phys_plan_1015): rows N->S
 // shell | add8 | mul4 | mul4 | chunk8 | chunk8+sum | norm/gate/control/sum.  The scalar row is ~470-620 um from the
 // shell, add8 and mul4 rows, so every signal between them crosses ONE registered relay leaf (ot_s81_engram_rly, own
 // clock entry on the control's root, mid-cluster):
 //   toward the control: go, phase, in_v, copy, scale (shell) and the mul4 / add8 valid, fault and copy bits;
 //   toward the shell / add8: gate_v, gate_copy, fault (to the shell) and a_gate (to add8).
 // The control's reference lines (in_v -> mvalid / avalid) see both sides delayed by the same stage, so its checks are
 // unchanged; gate_v reaches the shell one cycle later (ADD issue +1 cycle); a_gate is held from eg_valid until the
 // next go, >= VM_LAT + 3 cycles before add8 uses it (0 cycles).  The chunk8 / sum valids are taken from the mul4 of
 // their own column (mvalid[2c]; all mul4 run in lockstep, the control checks it), not one mvalid[0] broadcast.
 wire [7:0] mvalid_r,mfault_r,add_copy_r;wire [3:0] avalid_r,af_r;wire [31:0] a_gate_r,scale_r;wire go_r,phase_r,in_v_r;wire [1:0] copy_r;
 wire gate_v_c,fault_c;wire [1:0] gate_copy_c;
 ot_s81_engram_rly relay(relay_clk,arst_n,{mvalid,mfault,add_copy,avalid,af,go,phase,in_v,copy,scale},{a_gate,gate_v_c,gate_copy_c,fault_c},
  {mvalid_r,mfault_r,add_copy_r,avalid_r,af_r,go_r,phase_r,in_v_r,copy_r,scale_r},{a_gate_r,gate_v,gate_copy,fault});
 wire [1:0] nv,nf;wire eg_valid;wire [1:0] g_fault;wire [383:0] chunk_sums;wire [11:0] chunk_fault,chunk_valid;wire [2:0] rv,rf;wire [31:0] rhh,rkk,rdd;
 ot_s81_engram_mix_control #(.N(N),.D(D),.LM(LM),.LA(LA),.MUT(MUT)) control(
  .clk(clk),.arst_n(arst_n),.go(go_r),.phase(phase_r),.in_v(in_v_r),.copy(copy_r),.scale(scale_r),
  .gate_v(gate_v_c),.gate_copy(gate_copy_c),.gate(gate),.hh(hh),.kk(kk),.dd(dd),.fault(fault_c),
  .g_v(g_v),.a_gate(a_gate),.g_x(g_x),
  .mvalid(mvalid_r),.mfault(mfault_r),.avalid(avalid_r),.af(af_r),.add_copy(add_copy_r),.nv(nv),.nf(nf),.norm_rstd(norm_rstd),.eg_valid(eg_valid),.g_fault(g_fault),.gy(gy),.rv(rv),.rf(rf),.rhh(rhh),.rkk(rkk),.rdd(rdd));
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) hsum(ck_leaf[23],arst_n,go_r,mvalid[2],rv[0],rhh,rf[0],chunk_sums[0+:128],chunk_fault[0+:4],chunk_valid[0+:4]);
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) ksum(ck_leaf[24],arst_n,go_r,mvalid[2],rv[1],rkk,rf[1],chunk_sums[128+:128],chunk_fault[4+:4],chunk_valid[4+:4]);
 ot_s81_engram_sum #(.N(N),.D(D),.LA(LA)) dsum(ck_leaf[25],arst_n,go_r,mvalid[4],rv[2],rdd,rf[2],chunk_sums[256+:128],chunk_fault[8+:4],chunk_valid[8+:4]);
 genvar group,r,c;
 generate for(group=0;group<8;group=group+1)begin:g_mult
  ot_s81_engram_mul4 #(.LM(LM),.MUT(MUT)) leaf(ck_leaf[(group%2)?(26+group/2):(group/2)],arst_n,in_v,phase,
   h[128*group+:128],key[128*group+:128],weight[128*group+:128],
   mvalid[group],hd[128*group+:128],kd[128*group+:128],dot[128*group+:128],mfault[group]);
 end
 for(r=0;r<3;r=r+1)begin:g_reduce
  wire [1023:0] x=(r==0)?hd:(r==1)?kd:dot;
  for(c=0;c<4;c=c+1)begin:g_chunk
   ot_s81_engram_chunk8 #(.LA(LA)) leaf(ck_leaf[4+4*r+c],arst_n,mvalid[2*c],x[256*c+:256],
    chunk_valid[4*r+c],chunk_sums[32*(4*r+c)+:32],chunk_fault[4*r+c]);
  end
 end
 for(group=0;group<4;group=group+1)begin:g_add
  ot_s81_engram_add8 #(.LM(LM),.LA(LA)) leaf(ck_leaf[16+group],arst_n,in_v,phase,
   h[256*group+:256],value[256*group+:256],a_gate_r,copy,avalid[group],oy[256*group+:256],af[group],add_copy[2*group+:2]);
 end
 for(group=0;group<2;group=group+1)begin:g_norm
  ot_s81_engram_norm #(.LM(LM),.LA(LA)) leaf(ck_leaf[20+group],arst_n,rv[group],group==0?rhh:rkk,eps,nv[group],norm_rstd[32*group+:32],nf[group]);
 end endgenerate
 ot_s81_engram_gate #(.LM(LM),.LA(LA)) gate_leaf(ck_leaf[22],arst_n,g_v,g_x,eg_valid,gy,g_fault,ck_leaf[30]);
 assign out_v=avalid[0];assign out_data=oy;assign out_copy=add_copy[1:0];

endmodule
module ot_s81_engram_mixq_shell #(parameter integer MUT=0, VM_LAT=3, WRITE_COMMIT_LAT=1, HLAYOUT=1)(
 input wire [4:0] ck,input wire rst,input wire start,input wire [223:0] desc,
 output wire [4:0] rq_v,output wire [69:0] rq_row,output wire vtag,
 input wire [4:0] rs_v,input wire [2559:0] rs_d,
 output wire wq_v,output wire [13:0] wq_row,output wire [15:0] wq_mask,output wire [511:0] wq_d,
 output wire done,output wire fault,
 output wire go,iv,phase,output wire [1:0] copy,
 output wire [1023:0] h,kv,w,output wire [31:0] eps,scale,
 input wire gv,ov,mf,input wire [1:0] gc,oc,input wire [1023:0] result);
 wire fr,fa;
 ot_s81_engram_mixq_shctl #(.MUT(MUT),.VM_LAT(VM_LAT),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.HLAYOUT(HLAYOUT)) ctl(
  .ck(ck[0]),.rst(rst),.start(start),.desc(desc),.rq_v(rq_v),.rq_row(rq_row),.vtag(vtag),.rs_v(rs_v),
  .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.done(done),.fault(fault),
  .go(go),.iv(iv),.phase(phase),.copy(copy),.eps(eps),.scale(scale),.gv(gv),.ov(ov),.mf(mf),.gc(gc),.oc(oc),.fr(fr),.fa(fa));
 genvar c;
 generate for(c=0;c<4;c=c+1)begin:col
  ot_s81_engram_mixq_shcol #(.MUT(MUT)) u(.ck(ck[c+1]),.rst(rst),.rs_v(rs_v),
   .rs_d({rs_d[1536+256*c+:256],rs_d[512+256*c+:256],rs_d[128*c+:128]}),.fr(fr),.fa(fa),.ov(ov),.result(result[256*c+:256]),
   .h(h[256*c+:256]),.kv(kv[256*c+:256]),.w(w[256*c+:256]),.wq_d(wq_d[128*c+:128]));
 end endgenerate
endmodule
module ot_s81_engram_gate #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,input wire [31:0] x,
 output wire vo,output wire [31:0] y,output wire [1:0] fault,input wire clk_sigmoid);
 wire sqrt_v;wire [31:0] signed_sqrt;
 ot_s81_engram_signed_sqrt #(.LM(LM),.LA(LA)) magnitude(clk,arst_n,v,x,sqrt_v,signed_sqrt,fault[0]);
 ot_s81_engram_sigmoid #(.LM(LM),.LA(LA)) sigmoid(clk_sigmoid,arst_n,sqrt_v,signed_sqrt,vo,y,fault[1]);
endmodule