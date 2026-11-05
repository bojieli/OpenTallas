`timescale 1ns/1ps
// DIE-KV-71/HHP 11-05: old vs new qkd_controller_hbm_calendar, every output on every edge, random images and go's.  +seed= +cycles=
module tb_cal_ls;
  parameter integer MUTP=0;
  reg ck=0, rn=0, we=0, seal=0, go=0; reg [4:0] addr=0; reg [63:0] data=0; reg [15:0] ep=1; reg [5:0] layer=0; always #1 ck=~ck;
  wire o_own,n_own,o_rd,n_rd,o_s,n_s,o_w,n_w,o_raw,n_raw,o_f,n_f,o_i,n_i; wire [42:0] o_c,n_c; wire [15:0] o_e,n_e;
  qkd_controller_hbm_calendar_old #(.MUT(MUTP),.CORE_CLOCK(1)) old(ck,rn,we,addr,data,seal,go,ep,layer,o_own,o_c,o_rd,o_s,o_w,o_e,o_raw,o_f,o_i);
  qkd_controller_hbm_calendar     #(.MUT(MUTP),.CORE_CLOCK(1)) dut(ck,rn,we,addr,data,seal,go,ep,layer,n_own,n_c,n_rd,n_s,n_w,n_e,n_raw,n_f,n_i);
  integer seed=1,cycles=400000,cyc=0,st=0,nw=0,gap=0,glitch=3; longint c_fire=0,c_go=0,c_gapz=0; reg [127:0] w;
  function automatic int r(int m); return $urandom_range(m-1,0); endfunction
  initial begin
    if(!$value$plusargs("seed=%d",seed)) seed=1; if(!$value$plusargs("cycles=%d",cycles)) cycles=400000; void'($urandom(seed));
    forever begin
      @(negedge ck); cyc++; we=0; seal=0; go=0;
      case(st)
       0: begin rn=0; nw++; if(nw>6) begin rn=1; nw=0; st=1; glitch=r(4); end end
       1: begin
         we=1; addr=nw[4:0]; 
         if(nw[4]==0) begin w=0; w[15:0]=r(4)==0?0:r(30); w[25:16]=r(5)==0?0:r(12); w[29:26]=r(4); w[37:30]=r(3)==0?0:r(9); w[83:81]=r(8); w[84]=r(2); w[85]=r(2); w[80:38]={$urandom,$urandom}; data=w[63:0]; end
         else data=64'(w>>64);
         // keep each entry's own word: entry i low at nw=i, its high at nw=16+i (regenerate the high half from random)
         if(nw[4]) begin data={$urandom,$urandom}; data[21:0]={r(2)==1,r(2)==1,3'(r(8)),17'(r(100000))}; end
         nw++; if(nw==32) begin nw=0; st=2; end end
       2: begin seal=1; st=3; gap=r(8); end
       3: begin if(gap==0) begin go=1; ep=$urandom; layer=r(64); st=4; nw=0; c_go++; end else gap--; end
       4: begin nw++; if(r(200)==0) go=1; if(glitch==0 && r(300)==0) we=1; addr=r(32); if(r(1000)==0) seal=1;
            if(n_i && !go && nw>4) begin st=3; gap=r(10); if(r(20)==0) st=0; nw=0; end
            if(nw>4000) begin st=0; nw=0; end end
      endcase
    end
  end
  wire [100:0] ov={o_own,o_rd,o_s,o_w,o_raw,o_f,o_i,o_c,o_e}, nv={n_own,n_rd,n_s,n_w,n_raw,n_f,n_i,n_c,n_e};
  always @(posedge ck) if(st!=0) begin
    if(ov!==nv) begin $display("FAIL cycle %0d old %h new %h",cyc,ov,nv); $finish; end
    c_fire+=$countones(dut.fire);
    if(cyc>=cycles) begin $display("PASS cycles %0d go %0d fires %0d",cyc,c_go,c_fire); $finish; end
  end
endmodule
