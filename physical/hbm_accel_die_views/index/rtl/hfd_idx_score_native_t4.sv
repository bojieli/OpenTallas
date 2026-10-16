`timescale 1ps/1fs
`default_nettype none
// Opt-in hierarchical successor for the R25IQG L16 native scorer reservation.
// Full native pins stay compatible; four real L4 taps feed a finite atomic join.
// Taps and join must each be hardened before die adoption; this RTL is not a LEF.
module hfd_idx_score_native_t4 (
 input wire ck, rst, input wire [8791:0] ik, output wire [7:0] ikc,
 input wire [570:0] q, output wire [609:0] s, input wire sc,
 output wire [3:0] st
);
 wire [570:0] qi[0:3], qx[0:3];
 wire [615:0] scores;
 wire [3:0] score_credit;
 wire [3:0] status[0:3];
 wire join_fault;
 assign qi[0]=q;
 generate for(genvar t=0;t<4;t=t+1) begin: gt
   if(t>0) begin:gq
     wire v; wire [569:0] d;
     hfd_idx_pipe #(.W(570),.N(2)) hop(.ck(ck),.rst_n(rst),
       .v(qx[t-1][0]),.d(qx[t-1][570:1]),.qv(v),.q(d));
     assign qi[t]={d,v};
   end
   hfd_idx_score #(.L(4),.LANE0(4*t),.FA(6),.CRED(128),.FWD(0)) tap(
     .ck(ck),.rst(rst),.ik(ik[t*2198 +:2198]),.ikf(2'b0),
     .ikc(ikc[t*2 +:2]),.q(qi[t]),.qx(qx[t]),
     .s(scores[t*154 +:154]),.sc(score_credit[t]),.st(status[t]));
 end endgenerate
 hfd_idx_t4_join u_join(.ck(ck),.rst(rst),.taps(scores),
   .tap_credit(score_credit),.s(s),.sc(sc),.fault(join_fault));
 // Status is an aggregate; the native boundary retains a registered status.
 reg [3:0] status_q;
 always @(posedge ck or negedge rst)
   if(!rst) status_q<=0;
   else status_q<={(join_fault|status[0][3]|status[1][3]|status[2][3]|status[3][3]),
                  (status[0][2]|status[1][2]|status[2][2]|status[3][2]),
                  (status[0][1]&status[1][1]&status[2][1]&status[3][1]),1'b0};
 assign st=status_q;
endmodule
`default_nettype wire
