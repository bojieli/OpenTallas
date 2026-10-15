`timescale 1ns/1ps
// tb_dsfd_vm_static_cap_leaf_pre_equiv (claude S81 VM F2 2026-10-15): the hard capture lane with pin-stage decode
// (dsfd_vm_static_cap_leaf PIPE=2 = pure pin flops + decode stage) against the staged lane (PIPE=1) delayed by exactly ONE
// serial edge (the added explicit stage), cycle-exact: o_v and the sticky
// faults every cycle, header and every masked word of every emitted row.  Stimulus (the staged-merge equivalence
// generator at the leaf pins): full rows, duplicates, two full entries on a flush, aliases, random invalid / range
// addresses, sparse partial rows, flushes and a reset every 100 cycles with a new lane id.
// Mutant OT_VM_CAP_PRE_MUT_TGT (PIPE=2 only): the registered one-hot entry target is rotated by one entry: must FAIL.
module tb_dsfd_vm_static_cap_leaf_pre_equiv;
  reg ck=0; always #5 ck=~ck;
  reg rn=0, flush=0;
  reg [3:0] gid=0;
  reg [831:0] f_c=0;
  wire va,vb; wire [13:0] ra,rb; wire [15:0] ma,mb;
  wire [511:0] da,db; wire [4:0] fa,fb;
  dsfd_vm_static_cap_leaf #(.E(8), .PIPE(2)) a(.ck(ck),.rn(rn),.gid(gid),.f_c(f_c),.flush(flush),.o_v(va),.o_row(ra),.o_m(ma),.o_d(da),.flt(fa));
  dsfd_vm_static_cap_leaf #(.E(8), .PIPE(1)) b(.ck(ck),.rn(rn),.gid(gid),.f_c(f_c),.flush(flush),.o_v(vb),.o_row(rb),.o_m(mb),.o_d(db),.flt(fb));
  // PIPE=1 outputs one serial edge late (the one added PIPE=2 stage)
  reg pvb; reg [13:0] prb; reg [15:0] pmb; reg [511:0] pdb; reg [4:0] pfb;
  always @(posedge ck) begin pvb <= vb; prb <= rb; pmb <= mb; pdb <= db; pfb <= fb; end
  integer cyc,k,seed,mode,word,rows=0,words=0,partials=0,bad=0; reg [18:0] addr; reg [31:0] data; reg [4:0] all_faults=0;
  initial begin
    seed=42; if ($value$plusargs("seed=%d",seed)) begin end
    for(cyc=0;cyc<12000;cyc=cyc+1) begin
      @(negedge ck);
      if (cyc > 2) begin
      if ({va,fa} !== {pvb,pfb}) begin
        if (bad<5) $display("MISMATCH control cycle=%0d pre=%b/%h staged+1=%b/%h",cyc,va,fa,pvb,pfb); bad=bad+1;
      end
      all_faults = all_faults | pfb;
      if (pvb) begin
        rows=rows+1; if(pmb!=16'hffff) partials=partials+1;
        if ({ra,ma} !== {prb,pmb}) begin if (bad<5) $display("MISMATCH header cycle=%0d",cyc); bad=bad+1; end
        for(word=0;word<16;word=word+1) if(pmb[word]) begin
          words=words+1;
          if(da[32*word+:32] !== pdb[32*word+:32]) begin if (bad<5) $display("MISMATCH payload cycle=%0d word=%0d",cyc,word); bad=bad+1; end
        end
      end
      end
      rn=(cyc%100 != 0); if(!rn) gid=(cyc/100)%16;
      flush=(cyc%100==33 || cyc%100==70 || cyc%100==85);
      f_c=0;
      mode=cyc%100;
      for(k=0;k<16;k=k+1) begin
        addr=19'(($unsigned($random(seed))%32)<<8);
        addr[7:1]={gid,3'(k/2)};
        addr[0]=(mode<30) ? k%2 : ($unsigned($random(seed))%2);
        if(mode<30) addr[17:8]=(mode/2)%16;
        if(mode>=30 && mode<=32) begin
          addr[17:8] = mode==30 ? 0 : mode==31 ? 1 : k<8 ? 1 : 0;
          addr[0] = k%2;
        end
        if(mode>=90) addr=19'($random(seed));
        if(mode>=86 && mode<90 && k==5) addr[18]=1'b1;
        data=$random(seed);
        if(mode<30 || (mode==30 && k<8) || (mode==31 && k>=8) || mode==32 ||
           (mode>32 && ($unsigned($random(seed))%3)==0))
          f_c[104*(k/2)+52*(k%2)+:52]={data,addr,1'b1};
        else if ($unsigned($random(seed))%2) f_c[104*(k/2)+52*(k%2)+1+:51]={data,addr};   // invalid element with data
      end
    end
    if(rows<1000 || partials==0 || all_faults!=5'h1f) $fatal(1,"vacuous base rows/faults rows=%0d partials=%0d faults=%h",rows,partials,all_faults);
    if (bad==0) $display("PASS cap_leaf_pre_equivalence cycles=12000 rows=%0d partials=%0d words=%0d fault_classes=%h seed=%0d",rows,partials,words,all_faults,seed);
    else $display("FAIL cap_leaf_pre_equivalence mismatches=%0d rows=%0d seed=%0d",bad,rows,seed);
    $finish;
  end
endmodule
