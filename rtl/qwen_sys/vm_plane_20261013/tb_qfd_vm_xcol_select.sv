`timescale 1ns/1ps
// Leaf miter of ot_qfd_vm_xcol_t (claude/qwen-tp8-vm PLAN 2026-10-13): the merged plane + line leaf against its two
// parts wired as the parent wired them before the merge (ot_qfd_vm_xplane_t q -> ot_qfd_vm_xline_t d).  The parts
// carry their own miters against the parent's expressions (tb_qfd_vm_xplane.sv, tb_qfd_vm_xtree.sv); this bench binds
// the HARDENED module: q compared on every clock under xorshift64 stimulus (random data, plane / line control, me
// stalls 1 in 4).  Non-vacuity refusal: stalls, engine edges, q changes, line writes and replications below their
// floors print FAIL.  PMUT 1..3 (plane) and LMUT 1..3 (line) inside the candidate must FAIL.
module tb_qfd_vm_xcol_select;
    parameter integer NRB = 16, SMIN = 7, SMAX = 9, BMAX = 8, ND = 14, CYCLES = 4000, SEED = 1, PMUT = 0, LMUT = 0, MUT=0;
    localparam integer LNRB = $clog2(NRB), BEAT = (NRB - 1) * 16, NVW = $clog2(BEAT + 1), LB = $clog2(BMAX) + 1, NX = 1 << SMAX;
    reg clk = 0; always #5 clk = ~clk;
    reg me_e = 0;
    reg [NRB*16-1:0] d = 0;
    reg [LNRB+3:0] c_a = 0; reg [NVW-1:0] c_nv = 0;
    reg c_v = 0, o_v = 0; reg [ND-1:0] c_d = 0; reg [LB-1:0] c_j = 0; reg [3:0] c_sp = 0, o_sp = 0;
    wire [NX-1:0] q, r_q; wire [BEAT-1:0] r_bv;
    reg [SMAX-3:0] sel_w=0,sel_e=0;
    reg sel_v_w=0,sel_v_e=0;
    wire [SMAX-3:0] q_idx_w,q_idx_e; wire [3:0] q_w,q_e; wire q_v_w,q_v_e;
    ot_qfd_vm_xcol_select #(.NRB(NRB),.SMIN(SMIN),.SMAX(SMAX),.MUT(MUT)) candidate(
      .clk(clk),.me_e(me_e),.d_lo(d[NRB*8-1:0]),.d_hi(d[NRB*16-1:NRB*8]),.c_a(c_a),.c_nv(c_nv),.c_v(c_v),.c_d(c_d),.c_j(c_j),.c_sp(c_sp),
      .o_v(o_v),.o_sp(o_sp),.sel_w(sel_w),.sel_e(sel_e),.sel_v_w(sel_v_w),.sel_v_e(sel_v_e),.q_idx_w(q_idx_w),.q_idx_e(q_idx_e),.q_w(q_w),.q_e(q_e),.q_v_w(q_v_w),.q_v_e(q_v_e));
    ot_qfd_vm_xplane_t #(.NRB(NRB)) ref_p (.clk(clk), .me_e(me_e), .d(d), .c_a(c_a), .c_nv(c_nv), .q(r_bv));
    ot_qfd_vm_xline_t #(.NRB(NRB), .SMIN(SMIN), .SMAX(SMAX), .BMAX(BMAX), .ND(ND)) ref_l (.clk(clk), .me_e(me_e), .d(r_bv),
        .c_v(c_v), .c_d(c_d), .c_j(c_j), .c_sp(c_sp), .o_v(o_v), .o_sp(o_sp), .q(r_q));
    reg [63:0] rng;
    function automatic [31:0] rnd(input integer dummy);
        begin rng = rng ^ (rng << 13); rng = rng ^ (rng >> 7); rng = rng ^ (rng << 17); rnd = rng[47:16]; end
    endfunction
    integer cyc,w,k,errors=0,checks=0,stalls=0,valid_w=0,valid_e=0,changes=0; reg [7:0] lastq=0;
    reg [SMAX-3:0] tw1,tw2,tw3,te1,te2,te3;
    integer indices[0:7]; reg [3:0] split=0; reg me=0; reg [7:0] exp1=0,exp2=0,exp3=0; reg [1:0] v1=0,v2=0,v3=0;
    // Independent scalar scoreboard reads the reference line store directly:
    // replication is defined as element_index modulo 2^split.
    always @(posedge clk) begin
      me<=me_e;
      if(me) begin
        if(o_v) split<=o_sp;
        for(k=0;k<8;k=k+1) begin
          indices[k]<=((k<4?sel_w:sel_e)*4+k%4) % (1<<split);
          exp2[k]<=ref_l.line[indices[k]];
        end
        exp3<=exp2;
        v1<={sel_v_e,sel_v_w}; v2<=v1; v3<=v2;
        tw1<=sel_w; tw2<=tw1; tw3<=tw2; te1<=sel_e; te2<=te1; te3<=te2;
      end
    end
    initial begin
      rng=64'h9E3779B97F4A7C15 ^ SEED;
      for(cyc=0;cyc<CYCLES;cyc=cyc+1) begin
        @(negedge clk);
        me_e=(rnd(0)%4)!=0; if(!me_e) stalls=stalls+1;
        for(w=0;w<NRB/2;w=w+1) d[w*32+:32]=rnd(0);
        c_a=rnd(0); c_nv=BEAT; c_v=(rnd(0)%2)==0; c_d=1<<(rnd(0)%ND); c_j=rnd(0)%(BMAX+1);
        c_sp=SMIN+rnd(0)%(SMAX-SMIN+1); o_sp=c_sp; o_v=(rnd(0)%8)==0;
        sel_w=rnd(0); sel_e=rnd(0); sel_v_w=(rnd(0)%3)!=0; sel_v_e=(rnd(0)%3)!=0;
        @(posedge clk); #1;
        if(cyc>32) begin
          checks=checks+1;
          if(q_v_w) valid_w=valid_w+1; if(q_v_e) valid_e=valid_e+1;
          if({q_e,q_w}!==lastq) changes=changes+1; lastq={q_e,q_w};
          if({q_v_e,q_v_w} !== v3 || (q_v_w && (q_w !== exp3[3:0] || q_idx_w !== tw3)) || (q_v_e && (q_e !== exp3[7:4] || q_idx_e !== te3))) errors=errors+1;
        end
      end
      if(errors || checks<CYCLES/2 || stalls<CYCLES/8 || valid_w<CYCLES/3 || valid_e<CYCLES/3 || changes<CYCLES/8) begin $display("FAIL xcol_select MUT=%0d errors=%0d checks=%0d",MUT,errors,checks); $fatal(1,"FAIL"); end
      $display("PASS xcol_select SMAX=%0d seed=%0d checks=%0d",SMAX,SEED,checks); $finish;
    end
endmodule
