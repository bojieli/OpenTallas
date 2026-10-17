`timescale 1ns/1ps
// Compile-time policy realized as arithmetic: fixed RR REFpb, never ready-driven.
// Profiles must bind due_phase to the actual controller reset/strap epoch.
// Quiet windows exclude the bank's 48-edge precharge lead and 196-edge busy.
module qkd_kv_refresh_roots(
 input wire [11:0] now_phase,due_phase,input wire [8:0] nk,nv,
 input wire [7:0] k0,input wire kb,input wire [15:0] v_not_before,
 output wire [15:0] kdesc,kgo,krd,vdesc,vgo,vrd,output wire invalid
);
 localparam integer PERIOD=118, CYCLE=32*PERIOD, LEAD=28+16+4, RFC=196;
 // Old-row RAS28 + RP16 + 8 PRE row slots16 + 8 ACTs32 + RCD19 + pin/row8 =119.
 // Periodic REFpb/forced PRE causes at most19 ACT-blocked edges per118.
 // Fixed point W=119+19*(ceil(W/118)+1) is176.
 localparam integer WARM=176, IO_GUARD=8;
 localparam integer QUIET=CYCLE-7*PERIOD-RFC-WARM-LEAD-IO_GUARD;
 function automatic [15:0] modulo_cycle(input [15:0] x);
 reg [15:0] y;begin y=x;for(integer i=0;i<4;i=i+1)if(y>=CYCLE)y=y-CYCLE;modulo_cycle=y;end endfunction
 function automatic [15:0] choose(input [15:0] earliest,qs,span);
 reg[15:0] ep,distance;begin ep=modulo_cycle(earliest);distance=modulo_cycle(ep+16'(CYCLE)-qs);
 choose=distance+span<=QUIET?earliest:earliest+16'(CYCLE)-distance;end endfunction
 wire [15:0] kp=kb&&k0[1:0]==1?16'd2:kb&&k0[1:0]==2?16'd1:16'd0;
 wire [15:0] kn={7'b0,nk}+kp;
 wire [15:0] vn=nv==0?16'd0:{7'b0,nv}+16'(((nv-9'd1)>>3)*5);
 wire [15:0] kquiet=modulo_cycle({4'b0,due_phase}+16'(7*PERIOD+RFC+WARM));
 wire [15:0] vquiet=modulo_cycle({4'b0,due_phase}+16'(23*PERIOD+RFC+WARM));
 wire [15:0] ka=choose({4'b0,now_phase}+16'(WARM+2),kquiet,kn);
 wire [15:0] va0=ka+kn+16'(WARM+2),va1={4'b0,now_phase}+v_not_before+16'(WARM+2);
 wire [15:0] va=choose(va0>va1?va0:va1,vquiet,vn);
 assign krd=ka-{4'b0,now_phase};assign kdesc=krd-WARM;assign kgo=krd-16;
 assign vrd=va-{4'b0,now_phase};assign vdesc=vrd-WARM;assign vgo=vrd-16;
 assign invalid=now_phase>=CYCLE||due_phase>=CYCLE||nk>256||nv>256||k0>128||v_not_before>16000;
endmodule
