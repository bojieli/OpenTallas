`timescale 1ns/1ps
// Opt-in exact-age reducer delay helper, not a qualified hard master.
// Model: results/arch/qw_slice6_1019/red_bound32/model.json.
// reset_i is the caller's landed reset. Data is meaningful after D fill edges;
// its local phase forest adds two reset-propagation edges, zero data edges.
// Full logical store >2048 bits is rejected, never hidden by slicing.
module qfd_dv_s5_red_ring32 #(parameter integer W=32,D=7,ID=0)(
 input wire ck,reset_i,input wire[W-1:0] d,output wire[W-1:0] q
);
 localparam integer N=D-2, S=(W+7)/8, R=(N+31)/32;
 wire[S*R-1:0] reset_leaf;
 qfd_dv_reset_tree #(.N(S*R)) u_reset(.ck(ck),.rst_n(reset_i),.q(reset_leaf));
 for(genvar s=0;s<S;s=s+1) begin:g_slice
  localparam integer B=(W-8*s<8)?W-8*s:8;
  (* keep_hierarchy="yes" *) qfd_dv_s5_red_ring32_slice #(.W(B),.N(N),.ID(ID*64+s)) u_s(
   .ck(ck),.reset_leaf(reset_leaf[s*R+:R]),.d(d[8*s+:B]),.q(q[8*s+:B]));
 end
 generate if(D<3 || D>51 || W<1 || W>283 || W*(D-2)>2048 || S*R>1024) begin:g_bad
  qfd_red_ring32_requires_D3_51_W1_283_store_le2048 u_reject();
 end endgenerate
endmodule

(* keep_hierarchy="yes" *)
module qfd_dv_s5_red_ring32_slice #(parameter integer W=8,N=5,ID=0)(
 input wire ck,input wire[(N+31)/32-1:0] reset_leaf,
 input wire[W-1:0] d,output reg[W-1:0] q
);
 localparam integer C=(N+15)/16, L=$clog2(N), P=1<<L;
 // Distinct kept slice/phase identities prevent equivalent pointers across
 // data slices from collapsing into the wide shared pointer of redb.
 (* keep *) reg[N-1:0] phase;
 for(genvar j=0;j<N;j=j+1) begin:g_phase
  always @(posedge ck)
   if(!reset_leaf[j/32]) phase[j] <= (j==0);
   else phase[j] <= phase[(j+N-1)%N];
 end
 wire[C*W-1:0] captured;
 for(genvar c=0;c<C;c=c+1) begin:g_capture
  (* keep_hierarchy="yes" *) qfd_dv_s5_red_capture32 #(.W(W),.ID(ID*8+c)) u_c(
   .ck(ck),.d(d),.q(captured[c*W+:W]));
 end
 wire[P*W-1:0] selected[0:L];
 for(genvar j=0;j<P;j=j+1) begin:g_bank
  if(j<N) begin:g_real
   reg[W-1:0] slot;
   always @(posedge ck) if(phase[j]) slot <= captured[(j/16)*W+:W];
   assign selected[0][j*W+:W]=slot & {W{phase[j]}};
  end else begin:g_pad
   assign selected[0][j*W+:W]={W{1'b0}};
  end
 end
 for(genvar l=1;l<=L;l=l+1) begin:g_level
  for(genvar j=0;j<(P>>l);j=j+1) begin:g_pair
   assign selected[l][j*W+:W]=selected[l-1][(2*j)*W+:W] | selected[l-1][(2*j+1)*W+:W];
  end
  if((P>>l)<P) assign selected[l][P*W-1:(P>>l)*W]=0;
 end
`ifdef OT_RED_RING32_AGE_MUT
 always @(posedge ck) q<=captured[0+:W]; // mutant: bypass circular age
`else
 always @(posedge ck) q<=selected[L][0+:W];
`endif
endmodule

(* keep_hierarchy="yes" *)
module qfd_dv_s5_red_capture32 #(parameter integer W=8,ID=0)(
 input wire ck,input wire[W-1:0] d,output reg[W-1:0] q
);
 always @(posedge ck) q<=d;
endmodule
