`timescale 1ns/1ps
// DIE-HBM-83-OPSG lock-step: old (origin/main group text: 823-pin row banks, lgroup2_lf) vs new (-DOT_OPSG_GP: N32 banks, hub form).
// rd(_q), every bit, every cycle: new(t) == old(t - 5).  flt: new(t) == old(t) every cycle.  Reset every 400 cycles.
// Traffic modes: 0 legal, no collisions; 1 random banks (candidate faults); 2 stage collisions + read row conflicts; 3 write-then-read of the same rows;
// `OPSA adds scalar load / enable / rd_src / stage_group.
module tb;
  localparam integer DS = 5;
  logic clk=0, rst_n=0; logic [15:0] rq=0; logic [383:0] ra=0; logic [7:0] sv=0; logic [119:0] sa=0; logic [63:0] sm='1; logic [2047:0] sd=0;
  wire [511:0] da, db; wire fa, fb;
`ifdef OPSA
  logic sl=0, se=0; logic [31:0] sdt=0; logic [31:0] rs=0; logic [15:0] sg=0;
  `TOP  b(.clk,.rst_n,.scalar_load(sl),.scalar_enable(se),.scalar_data(sdt),.rd_re(rq),.rd_addr(ra),.rd_src(rs),.rd_q(db),.stage_v(sv),.stage_group(sg),.stage_addr(sa),.stage_data(sd),.flt(fb));
  `OTOP a(.clk,.rst_n,.scalar_load(sl),.scalar_enable(se),.scalar_data(sdt),.rd_re(rq),.rd_addr(ra),.rd_src(rs),.rd_q(da),.stage_v(sv),.stage_group(sg),.stage_addr(sa),.stage_data(sd),.flt(fa));
`else
  `TOP  b(.clk,.rst_n,.rq(rq),.ra(ra),.rd(db),.sw_v(sv),.sw_addr(sa),.sw_mask(sm),.sw_d(sd),.flt(fb));
  `OTOP a(.clk,.rst_n,.rq(rq),.ra(ra),.rd(da),.sw_v(sv),.sw_addr(sa),.sw_mask(sm),.sw_d(sd),.flt(fa));
`endif
  always #1 clk=~clk;
  logic [511:0] dq [0:7];
  always @(posedge clk) begin dq[0]<=da; for (int i=1;i<8;i++) dq[i]<=dq[i-1]; end
  wire [511:0] de = dq[DS-1];
  integer cyc=0, errs=0, derr=0, ferr=0, nz=0, fl=0, mode=0, wrc=0, rdc=0, scc=0; logic [14:0] base;
  function automatic logic [3:0] cand(int l, int k);
    case (k%4) 0: return 4'(l); 1: return 4'(l^1); 2: return 4'(l>>1); default: return 4'((l>>1)+8); endcase
  endfunction
  always @(negedge clk) begin
    cyc<=cyc+1; rst_n <= (cyc%400)>=6;
    if (cyc%150==0) mode=$urandom%4; base=15'($urandom%512)<<4;
    // stage writes
    for (int s=0;s<8;s++) begin
      sv[s]=($urandom%(mode==2?2:6))==0;
      if (mode==3) sv[s]=(s==(cyc%8)) && (cyc%3==0);
      sa[s*15+:15]= (mode==2) ? 15'($urandom%64) : (mode==3) ? 15'((cyc/8)%64*8) + 15'(s*8) : 15'($urandom);
    end
    if (mode==0) begin for (int s=1;s<8;s++) if (sv[s]) sv[s-1]=0; end
    sm={$urandom,$urandom}; if ($urandom%2==0) sm='1;
    for (int k=0;k<64;k++) sd[k*32+:32]=$urandom;
    // lane reads
    for (int l=0;l<16;l++) begin
      rq[l]=($urandom%3)==0;
      ra[l*24+:24]={9'($urandom),11'((mode==3)?((cyc/8)%64):((mode==2)?$urandom%4:$urandom%2048)),cand(l,$urandom)};
      if (mode==1) ra[l*24+:4]=4'($urandom);
      if (l==0 && $urandom%3==0) ra[3:0]=4'($urandom);
      if (mode==3) ra[l*24+4+:11]=11'((cyc/8)%64);
    end
`ifdef OPSA
    sl=($urandom%8)==0; se=($urandom%16)==0; sdt=$urandom; rs={$urandom}&{$urandom}; if ($urandom%2==0) rs=0;
    for (int s=0;s<8;s++) sg[2*s+:2]=($urandom%8==0)?2'($urandom):`GVAL;
`endif
    if ((cyc%400)<12) begin rq=0; sv=0; end
    if ((cyc%400)>=20 && cyc>40) begin
      if (fb!==fa) begin errs++; ferr++; if (errs<6) $display("FLT MISMATCH cyc=%0d old %b new %b", cyc, fa, fb); end
      if (db!==de) begin errs++; derr++; if (errs<6) $display("RD MISMATCH cyc=%0d", cyc); end
      if (de!=0) nz++; if (fa) fl++; if (sv!=0) wrc++; if (rq!=0) rdc++;
`ifdef OPSA
      if (se) scc++;
`endif
    end
    if (cyc==`CYC) begin $display("GP LOCKSTEP %s errs=%0d (rd %0d flt %0d) rd_nonzero=%0d flt_cycles=%0d write_cycles=%0d read_cycles=%0d scalar_en=%0d of %0d", errs?"FAIL":"PASS", errs, derr, ferr, nz, fl, wrc, rdc, scc, cyc); $finish; end
  end
endmodule
