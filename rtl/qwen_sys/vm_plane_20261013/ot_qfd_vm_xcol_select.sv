// One plane of two independently selected quad-line root words.
// The stored line is plane-major; there is no 2,048-bit replicated export.
// Request -> registered masked element indices -> 128-entry local mux ranks
// -> group mux and output register: three me-enabled edges. o_v loads split.
module ot_qfd_vm_xcol_select #(
 parameter integer NRB=64, SMIN=7, SMAX=11, BMAX=8, ND=14,
 parameter [ND*8-1:0] DSET={8'd96,8'd64,8'd48,8'd32,8'd24,8'd16,8'd12,8'd8,8'd6,8'd4,8'd3,8'd2,8'd1,8'd0},
 parameter integer MUT=0
)(input wire clk,me_e,
 input wire [NRB*8-1:0] d_lo,d_hi,
 input wire [$clog2(NRB)+3:0] c_a,
 input wire [$clog2((NRB-1)*16+1)-1:0] c_nv,
 input wire c_v, input wire [ND-1:0] c_d,
 input wire [$clog2(BMAX):0] c_j, input wire [3:0] c_sp,
 input wire o_v, input wire [3:0] o_sp,
 input wire [SMAX-3:0] sel_w,sel_e, input wire sel_v_w,sel_v_e,
 output reg [SMAX-3:0] q_idx_w,q_idx_e,
 output reg [3:0] q_w,q_e, output reg q_v_w,q_v_e);
 localparam integer NX=1<<SMAX, NG=NX/128;
 wire [(NRB-1)*16-1:0] bv;
 wire [NX-1:0] line_bits;
 ot_qfd_vm_xplane_t #(.NRB(NRB)) u_p(.clk(clk),.me_e(me_e),.d({d_hi,d_lo}),.c_a(c_a),.c_nv(c_nv),.q(bv));
 ot_qfd_vm_xline_t #(.NRB(NRB),.SMIN(SMIN),.SMAX(SMAX),.BMAX(BMAX),.ND(ND),.DSET(DSET),.SELECT_ONLY(1)) u_l(
 .clk(clk),.me_e(me_e),.d(bv),.c_v(c_v),.c_d(c_d),.c_j(c_j),.c_sp(c_sp),.o_v(o_v),.o_sp(o_sp),.q(),.line_data(line_bits));
 reg me=0; always @(posedge clk) me<=me_e;
 reg [3:0] split;
 reg [SMAX-1:0] idx [0:7];
 reg [7:0] groups [0:NG-1];
 reg [SMAX-8:0] hi [0:7];
 reg [SMAX-3:0] tag1_w,tag1_e,tag2_w,tag2_e;
 reg [1:0] v1=0,v2=0;
 integer k,g;
 always @(posedge clk) if(me) begin
  if(o_v) split<=o_sp;
  v1<={sel_v_e,sel_v_w}; v2<=v1;
  tag1_w<=sel_w; tag1_e<=sel_e; tag2_w<=tag1_w; tag2_e<=tag1_e;
  q_idx_w<=tag2_w; q_idx_e<=tag2_e;
  q_v_w<=v2[0]; q_v_e<=v2[1];
  for(k=0;k<8;k=k+1) begin
   idx[k]<=((((k<4 ? sel_w : sel_e)<<2) | (k%4)) ^ ((MUT==1 && k==0)?1:0)) & ((1<<split)-1);
   hi[k]<=idx[k]>>7;
   for(g=0;g<NG;g=g+1) groups[g][k]<=line_bits[g*128+idx[k][6:0]];
   if(k<4) q_w[k]<=groups[(MUT==2 ? 0 : hi[k])][k];
   else q_e[k-4]<=groups[(MUT==3 ? hi[k-4] : hi[k])][k];
  end
 end
endmodule
