`timescale 1ns/1ps
// Leaf miter of ot_qfd_vm_xcol_t (claude/qwen-tp8-vm PLAN 2026-10-13): the merged plane + line leaf against its two
// parts wired as the parent wired them before the merge (ot_qfd_vm_xplane_t q -> ot_qfd_vm_xline_t d).  The parts
// carry their own miters against the parent's expressions (tb_qfd_vm_xplane.sv, tb_qfd_vm_xtree.sv); this bench binds
// the HARDENED module: q compared on every clock under xorshift64 stimulus (random data, plane / line control, me
// stalls 1 in 4).  Non-vacuity refusal: stalls, engine edges, q changes, line writes and replications below their
// floors print FAIL.  PMUT 1..3 (plane) and LMUT 1..3 (line) inside the candidate must FAIL.
module tb_qfd_vm_xcol_roots;
    parameter integer NRB = 16, SMIN = 7, SMAX = 9, BMAX = 8, ND = 14, CYCLES = 4000, SEED = 1, PMUT = 0, LMUT = 0, MUT=0,SNAPSHOT=1;
    localparam integer LNRB = $clog2(NRB), BEAT = (NRB - 1) * 16, NVW = $clog2(BEAT + 1), LB = $clog2(BMAX) + 1, NX = 1 << SMAX;
    reg clk = 0; always #5 clk = ~clk;
    reg me_e = 0;
    reg [NRB*16-1:0] d = 0;
    reg [LNRB+3:0] c_a = 0; reg [NVW-1:0] c_nv = 0;
    reg c_v = 0, o_v = 0; reg [ND-1:0] c_d = 0; reg [LB-1:0] c_j = 0; reg [3:0] c_sp = 0, o_sp = 0;
    wire [NX-1:0] q, r_q; wire [BEAT-1:0] r_bv;
    localparam PHW=SMAX-7;
    reg [PHW-1:0] phase=0;reg [15:0] epoch=0;reg sel_v=0;
    wire [127:0] q_roots; wire [PHW-1:0] q_phase;wire [15:0] q_epoch;wire q_v;
    ot_qfd_vm_xcol_roots #(.NRB(NRB),.SMIN(SMIN),.SMAX(SMAX),.MUT(MUT),.SNAPSHOT(SNAPSHOT)) candidate(
      .clk(clk),.me_e(me_e),.d_lo(d[NRB*8-1:0]),.d_hi(d[NRB*16-1:NRB*8]),.c_a(c_a),.c_nv(c_nv),.c_v(c_v),.c_d(c_d),.c_j(c_j),.c_sp(c_sp),
      .o_v(o_v),.o_sp(o_sp),.phase(phase),.epoch(epoch),.sel_v(sel_v),.q(q_roots),.q_phase(q_phase),.q_epoch(q_epoch),.q_v(q_v));
    ot_qfd_vm_xplane_t #(.NRB(NRB)) ref_p (.clk(clk), .me_e(me_e), .d(d), .c_a(c_a), .c_nv(c_nv), .q(r_bv));
    ot_qfd_vm_xline_t #(.NRB(NRB), .SMIN(SMIN), .SMAX(SMAX), .BMAX(BMAX), .ND(ND)) ref_l (.clk(clk), .me_e(me_e), .d(r_bv),
        .c_v(c_v), .c_d(c_d), .c_j(c_j), .c_sp(c_sp), .o_v(o_v), .o_sp(o_sp), .q(r_q));
    reg [63:0] rng;
    function automatic [31:0] rnd(input integer dummy);
        begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 7); rng = rng ^ (rng << 17); rnd = rng[47:16]; end
    endfunction
    integer cyc,w,k,errors=0,checks=0,stalls=0,valids=0,changes=0;reg [127:0] lastq=0;
    reg [PHW-1:0] ph1,ph2,ph3;reg [15:0] ep1,ep2,ep3;
    reg [3:0] split=0;reg me=0;reg [127:0] exp2,exp3;reg v1=0,v2=0,v3=0;
    integer indices[0:127];integer root_changes[0:31];reg [(1<<PHW)-1:0] phase_seen=0;reg [15:0] split_seen=0;
    always @(posedge clk) begin
      me<=me_e;
      if(me) begin
        if(o_v)begin split<=o_sp;split_seen[o_sp]=1;end
        for(k=0;k<128;k=k+1) begin
          indices[k]<=((32*phase+k/4)*4+k%4) % (SNAPSHOT!=0?NX:(1<<split));
          exp2[k]<=(SNAPSHOT!=0)?r_q[indices[k]]:ref_l.line[indices[k]];
        end
        exp3<=exp2;v1<=sel_v;v2<=v1;v3<=v2;
        ph1<=phase;ph2<=ph1;ph3<=ph2;ep1<=epoch;ep2<=ep1;ep3<=ep2;
      end
    end
    initial begin
      rng=64'h9E3779B97F4A7C15 ^ SEED;
      for(w=0;w<32;w=w+1)root_changes[w]=0;
      for(cyc=0;cyc<CYCLES;cyc=cyc+1) begin
        @(negedge clk);
        me_e=(rnd(0)%4)!=0;if(!me_e)stalls=stalls+1;
        for(w=0;w<NRB/2;w=w+1)d[w*32+:32]=rnd(0);
        c_a=rnd(0);c_nv=BEAT;c_v=(rnd(0)%2)==0;c_d=1<<(rnd(0)%ND);c_j=rnd(0)%(BMAX+1);
        c_sp=SMIN+rnd(0)%(SMAX-SMIN+1);o_sp=rnd(0)%16;o_v=(rnd(0)%8)==0;
        phase=rnd(0);epoch=rnd(0);sel_v=(rnd(0)%3)!=0;
        @(posedge clk);#1;
        if(cyc>32)begin
          checks=checks+1;if(q_v)valids=valids+1;
          if(q_roots!==lastq)changes=changes+1;
          if(q_v)begin phase_seen[q_phase]=1;for(w=0;w<32;w=w+1)if(q_roots[w*4+:4]!==lastq[w*4+:4])root_changes[w]=root_changes[w]+1;end
          lastq=q_roots;
          if(q_v!==v3 || (q_v && (q_roots!==exp3 || q_phase!==ph3 || q_epoch!==ep3)))errors=errors+1;
        end
      end
      for(w=0;w<32;w=w+1)if(root_changes[w]<16)errors=errors+1;
      if(phase_seen!=={(1<<PHW){1'b1}} || split_seen!==16'hffff)errors=errors+1;
      if(errors || checks<CYCLES/2 || stalls<CYCLES/8 || valids<CYCLES/3 || changes<CYCLES/8)begin
        $display("FAIL xcol_roots MUT=%0d errors=%0d checks=%0d changes=%0d",MUT,errors,checks,changes);$fatal(1,"FAIL");end
      $display("PASS xcol_roots SMAX=%0d seed=%0d checks=%0d valids=%0d changes=%0d roots=32 all_phase=%h snapshot=%0d",SMAX,SEED,checks,valids,changes,phase_seen,SNAPSHOT);$finish;
    end
endmodule
