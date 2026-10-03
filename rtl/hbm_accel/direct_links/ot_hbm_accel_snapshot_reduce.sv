`timescale 1ns/1ps
// Arithmetic endpoint: adjacent-pair tree, odd tail delayed rather than padded.
// N=8 preserves the W19 o-group subtree. Do not reduce 96 ranks for a W19
// 8-contributor op or add inactive zero leaves. Input is a captured snapshot;
// caller owns its lease until output is consumed. LAT7 is unqualified at SS/FF.
module ot_hbm_accel_snapshot_reduce #(
 parameter integer ENABLE=0,N=96,LANES=16,LAT=7,FW=32*LANES
)(input wire clk,rst_n,valid_in,input wire [N*FW-1:0] data_in,
 output wire valid_out,output wire [FW-1:0] data_out,output wire fault);
 function automatic integer count(input integer level);
 integer j,n; begin n=N; for(j=0;j<level;j=j+1) n=(n+1)/2; count=n; end
 endfunction
 generate if(ENABLE) begin:on
 localparam integer L=$clog2(N);
 wire [FW-1:0] d[0:L][0:N-1];
 wire [L:0] v,e;
 assign v[0]=valid_in; assign e[0]=0;
 for(genvar r=0;r<N;r=r+1) begin:leaf
 assign d[0][r]=data_in[r*FW+:FW];
 end
 for(genvar l=1;l<=L;l=l+1) begin:level
 localparam integer NC=count(l),NP=count(l-1);
 wire [NC-1:0] err;
 reg [LAT-1:0] vp,ep;
 always @(posedge clk or negedge rst_n)
 if(!rst_n) begin vp<=0; ep<=0; end
 else begin vp<={vp[LAT-2:0],v[l-1]}; ep<={ep[LAT-2:0],e[l-1]}; end
 assign v[l]=vp[LAT-1]; assign e[l]=ep[LAT-1]|(|err);
 for(genvar i=0;i<NC;i=i+1) begin:node
 if(2*i+1<NP) begin:add
 wire [2*LANES-1:0] errors;
 for(genvar ln=0;ln<LANES;ln=ln+1) begin:lane
 wire unused_v;
 ot_hdc_fp32_add_lat #(.LAT(LAT)) u_add(.clk(clk),.rst_n(rst_n),
 .valid_in(v[l-1]),.a(d[l-1][2*i][ln*32+:32]),.b(d[l-1][2*i+1][ln*32+:32]),
 .y(d[l][i][ln*32+:32]),.err(errors[ln*2+:2]),.valid_out(unused_v));
 end
 assign err[i]=v[l] && (|errors);
 end else begin:pass
 reg [FW-1:0] delay[0:LAT-1];
 always @(posedge clk) begin delay[0]<=d[l-1][2*i];
 for(integer j=1;j<LAT;j=j+1) delay[j]<=delay[j-1]; end
 assign d[l][i]=delay[LAT-1]; assign err[i]=0;
 end
 end
 end
 assign valid_out=v[L]; assign data_out=d[L][0]; assign fault=e[L];
 end else begin:off
 assign valid_out=0; assign data_out=0; assign fault=0;
 end endgenerate
endmodule
