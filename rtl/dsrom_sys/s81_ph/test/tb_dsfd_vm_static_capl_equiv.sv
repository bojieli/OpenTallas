`timescale 1ns/1ps
module tb_dsfd_vm_static_capl_equiv;
  reg ck=0; always #5 ck=~ck;
  reg rn=0, flush=0;
  reg [3:0] gid=0;
  reg [831:0] f_c=0;
  wire va,vb; wire [13:0] ra,rb; wire [15:0] ma,mb;
  wire [511:0] da,db; wire [4:0] fa,fb;
  dsfd_vm_static_capl a(ck,rn,gid,f_c,flush,va,ra,ma,da,fa);
  dsfd_vm_static_capl_old b(ck,rn,gid,f_c,flush,vb,rb,mb,db,fb);
  integer cyc,k,e,seed,mode; reg [18:0] addr; reg [31:0] data;
  task check;
    begin
      if ({va,fa} !== {vb,fb} || (va && {ra,ma,da} !== {rb,mb,db})) begin
        $display("FAIL outputs cycle=%0d fault=%h/%h",cyc,fa,fb); $fatal(1);
      end
      if ({a.nV,a.full,a.f_alias,a.f_dup} !== {b.nV,b.full,b.f_alias,b.f_dup}) begin
        $display("FAIL next controls cycle=%0d",cyc); $fatal(1);
      end
      for(e=0;e<8;e=e+1) begin
        if ({a.nK[e],a.nM[e],a.nD[e]} !== {b.nK[e],b.nM[e],b.nD[e]}) begin
          $display("FAIL next entry cycle=%0d entry=%0d",cyc,e); $fatal(1);
        end
      end
    end
  endtask
  initial begin
    seed=42; if ($value$plusargs("seed=%d",seed)) begin end
    for(cyc=0;cyc<6000;cyc=cyc+1) begin
      @(negedge ck);
      rn=(cyc%100 != 0); if(!rn) gid=(cyc/100)%16;
      flush=(cyc%100==70 || cyc%100==85);
      f_c=0;
      for(k=0;k<16;k=k+1) begin
        mode=cyc%100;
        // Complete rows, duplicates, two full entries on a flush, aliases,
        // random invalid addresses, and sparse partial rows in fixed slots.
        addr=19'(($unsigned($random(seed))%32)<<8);
        addr[7:1]={gid,3'(k/2)};
        addr[0]=(mode<30) ? k%2 : ($unsigned($random(seed))%2);
        if(mode<30) addr[17:8]=(mode/2)%16;
        if(mode>=90) addr=19'($random(seed));
        data=$random(seed);
        if(mode<30 || ($unsigned($random(seed))%3)==0)
          f_c[104*(k/2)+52*(k%2)+:52]={data,addr,1'b1};
      end
      #1; check();
      @(posedge ck); #1; check();
    end
    $display("PASS equivalence cycles=6000 seed=%0d",seed); $finish;
  end
endmodule
