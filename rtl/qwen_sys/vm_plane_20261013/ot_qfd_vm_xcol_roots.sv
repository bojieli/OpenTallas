// Cyclic root assignment: root r exports quad NROOT*phase+r (four elements).
// Constant-entry mux ranks replace full-array replication. All roots stream in
// parallel, native SMAX9 needs4 phases and full SMAX11 needs16 phases.
// Request -> local constant-index rank -> output:3 registered-me enabled edges.
module ot_qfd_vm_xcol_roots #(
 parameter integer NRB=64,SMIN=7,SMAX=11,BMAX=8,ND=14,NROOT=32,
 parameter integer PHW=(SMAX-2-$clog2(NROOT)>0?SMAX-2-$clog2(NROOT):1),
 parameter [ND*8-1:0] DSET={8'd96,8'd64,8'd48,8'd32,8'd24,8'd16,8'd12,8'd8,8'd6,8'd4,8'd3,8'd2,8'd1,8'd0},
 parameter integer MUT=0
)(input wire clk,me_e,
 input wire [NRB*8-1:0] d_lo,d_hi,
 input wire [$clog2(NRB)+3:0] c_a,
 input wire [$clog2((NRB-1)*16+1)-1:0] c_nv,
 input wire c_v,input wire [ND-1:0] c_d,
 input wire [$clog2(BMAX):0] c_j,input wire [3:0] c_sp,
 input wire o_v,input wire [3:0] o_sp,
 input wire [PHW-1:0] phase,input wire [15:0] epoch,input wire sel_v,
 output reg [NROOT*4-1:0] q,
 output reg [PHW-1:0] q_phase,output reg [15:0] q_epoch,output reg q_v=0);
 localparam integer NX=1<<SMAX;
 wire [(NRB-1)*16-1:0] bv; wire [NX-1:0] line_bits;
 ot_qfd_vm_xplane_t #(.NRB(NRB)) u_p(.clk(clk),.me_e(me_e),.d({d_hi,d_lo}),.c_a(c_a),.c_nv(c_nv),.q(bv));
 ot_qfd_vm_xline_t #(.NRB(NRB),.SMIN(SMIN),.SMAX(SMAX),.BMAX(BMAX),.ND(ND),.DSET(DSET),.SELECT_ONLY(1)) u_l(
 .clk(clk),.me_e(me_e),.d(bv),.c_v(c_v),.c_d(c_d),.c_j(c_j),.c_sp(c_sp),.o_v(o_v),.o_sp(o_sp),.q(),.line_data(line_bits));
 reg me=0;always @(posedge clk) me<=me_e;
 reg [3:0] split,sp1;
 reg [PHW-1:0] ph1,ph2;
 reg [15:0] ep1,ep2;reg v1=0,v2=0;
 wire [NROOT*4-1:0] rank;
 reg [NROOT*4-1:0] rank2;
 genvar r;
 generate for(r=0;r<NROOT;r=r+1) begin:g_root
  ot_qfd_vm_root_rank #(.SMAX(SMAX),.NROOT(NROOT),.PHW(PHW),.ROOT_ID(r),.MUT(MUT)) u_rank(
   .line_bits(line_bits),.phase(ph1),.split(sp1),.q(rank[r*4+:4]));
 end endgenerate
 always @(posedge clk) if(me) begin
  if(o_v) split<=o_sp;
  ph1<=phase;sp1<=split;ep1<=epoch;v1<=sel_v;
  rank2<=rank;ph2<=ph1;ep2<=ep1;v2<=v1;
  q<=rank2;q_phase<=ph2;q_epoch<=ep2;q_v<=v2;
 end
endmodule

// Four-output rank groups keep Yosys parameter derivation bounded. The source
// expressions remain constant indices; no monolithic128-output AST expansion.
module ot_qfd_vm_root_rank #(
 parameter integer SMAX=11,NROOT=32,PHW=4,ROOT_ID=0,MUT=0
)(input wire [(1<<SMAX)-1:0] line_bits,input wire [PHW-1:0] phase,
 input wire [3:0] split,output wire [3:0] q);
 genvar k;
 generate for(k=0;k<4;k=k+1)begin:g_bit
  reg pick;integer p,s;
  always @*begin
   pick=0;
   for(p=0;p<(1<<PHW);p=p+1)for(s=0;s<16;s=s+1)
    if(phase==p && split==s)pick=line_bits[
     ((NROOT*((MUT==1)?((p+1)%(1<<PHW)):p)+(MUT==2?(ROOT_ID+1)%NROOT:ROOT_ID))*4+k)
     &((1<<(MUT==3?((s+1)%16):s))-1)];
  end
  assign q[k]=pick;
 end endgenerate
endmodule
