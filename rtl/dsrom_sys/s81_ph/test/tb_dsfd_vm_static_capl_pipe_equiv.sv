`timescale 1ns/1ps
module tb_dsfd_vm_static_capl_pipe_equiv;
  reg ck=0; always #5 ck=~ck;
  reg rn=0, flush=0;
  reg [3:0] gid=0;
  reg [831:0] f_c=0;
  wire va,vb; wire [13:0] ra,rb; wire [15:0] ma,mb;
  wire [511:0] da,db; wire [4:0] fa,fb;
  dsfd_vm_static_capl_pipe a(ck,rn,gid,f_c,flush,va,ra,ma,da,fa);
  dsfd_vm_static_capl b(ck,rn,gid,f_c,flush,vb,rb,mb,db,fb);
  integer cyc,k,e,seed,mode; reg [18:0] addr; reg [31:0] data;
  reg exp_v=0; reg [13:0] exp_r; reg [15:0] exp_m;
  reg [511:0] exp_d; reg [4:0] exp_f=0;
  integer word, rows=0, words=0, partials=0; reg [4:0] all_faults=0;
  task check;
    begin
      // Reset suppresses output immediately. Otherwise every observable row,
      // valid masked word and sticky fault is the legacy result one edge later.
      if ({va,fa} !== {rn && exp_v, rn ? exp_f : 5'd0}) begin
        $display("FAIL output control cycle=%0d actual=%b/%h expected=%b/%h",cyc,va,fa,exp_v,exp_f); $fatal(1);
      end
      all_faults = all_faults | fa;
      if (va) begin
        rows=rows+1; if(ma!=16'hffff) partials=partials+1;
        if ({ra,ma} !== {exp_r,exp_m}) begin
          $display("FAIL output header cycle=%0d actual=%h/%h expected=%h/%h",cyc,ra,ma,exp_r,exp_m); $fatal(1);
        end
        for(word=0;word<16;word=word+1) if(ma[word]) begin
          words=words+1;
          if(da[32*word+:32] !== exp_d[32*word+:32]) begin
          $display("FAIL payload cycle=%0d word=%0d",cyc,word); $fatal(1);
          end
        end
      end
    end
  endtask
  initial begin
    seed=42; if ($value$plusargs("seed=%d",seed)) begin end
    for(cyc=0;cyc<6000;cyc=cyc+1) begin
      @(negedge ck);
      rn=(cyc%100 != 0); if(!rn) gid=(cyc/100)%16;
      flush=(cyc%100==33 || cyc%100==70 || cyc%100==85);
      f_c=0;
      for(k=0;k<16;k=k+1) begin
        mode=cyc%100;
        // Complete rows, duplicates, two full entries on a flush, aliases,
        // random invalid addresses, and sparse partial rows in fixed slots.
        addr=19'(($unsigned($random(seed))%32)<<8);
        addr[7:1]={gid,3'(k/2)};
        addr[0]=(mode<30) ? k%2 : ($unsigned($random(seed))%2);
        if(mode<30) addr[17:8]=(mode/2)%16;
        if(mode>=30 && mode<=32) begin
          addr[17:8] = mode==30 ? 0 : mode==31 ? 1 : k<8 ? 1 : 0;
          addr[0] = k%2;
        end
        if(mode>=90) addr=19'($random(seed));
        data=$random(seed);
        if(mode<30 || (mode==30 && k<8) || (mode==31 && k>=8) || mode==32 ||
           (mode>32 && ($unsigned($random(seed))%3)==0))
          f_c[104*(k/2)+52*(k%2)+:52]={data,addr,1'b1};
      end
      @(posedge ck); #1; check();
      exp_v=vb; exp_r=rb; exp_m=mb; exp_d=db; exp_f=fb;
      if (!rn) begin exp_v=0; exp_f=0; end
    end
`ifndef OT_VM_CAPL_MUT_WORD
    if(rows<1000 || partials==0 || all_faults!=5'h1f) $fatal(1,"vacuous base rows/faults");
`else
    if(rows==0 || partials==0 || words<128) $fatal(1,"vacuous mutant comparison");
`endif
    $display("PASS staged_equivalence cycles=6000 rows=%0d partials=%0d words=%0d fault_classes=%h seed=%0d",rows,partials,words,all_faults,seed); $finish;
  end
endmodule
