`timescale 1ns/1ps
module check_writer #(parameter D=4, W=1031, K=D/2)(output reg done=0);
  reg ck=0; always #5 ck=~ck;
  localparam NC=(W+23)/24, NR=(NC+31)/32, AW=$clog2(D);
  reg [NR-1:0] rst=0; reg [W-1:0] din=0;
  wire [D*W-1:0] b0,b1; wire [D*(AW+1)-1:0] ep0,ep1;wire[D*NC-1:0]v0,v1; wire[W-1:0]q0,q1;
  ot_pl_land_split_w #(.W(W),.D(D)) refw(ck,rst,din,b0,ep0,v0);
  ot_pl_land_n32_split_w #(.W(W),.D(D)) dutw(ck,rst,din,b1,ep1,v1);
  ot_pl_land_split_r #(.W(W),.D(D),.K(K)) refr(ck,rst,b0,ep0,v0,q0);
  ot_pl_land_split_r #(.W(W),.D(D),.K(K)) dutr(ck,rst,b1,ep1,v1,q1);
  integer cyc,i,s,c,errors=0,checks=0;
  initial begin
    for(cyc=0;cyc<1400;cyc=cyc+1)begin
      @(negedge ck);
      // Repeated resets, including unequal per-group offsets; each ref/dut sees exactly the same reset.
      for(i=0;i<NR;i=i+1)rst[i]=cyc>8+i && !(cyc>=410+i&&cyc<421+i) && !(cyc>=915+i&&cyc<924+i);
      for(i=0;i<W;i=i+1)din[i]=$random;
      @(posedge ck);#1;
      if(cyc>3)begin
        if(v0!==v1)errors=errors+1;
        if(q0!==q1)errors=errors+1;
        // Unwritten banks differ intentionally; valid slots must be bit identical, including epoch tags.
        for(c=0;c<NC;c=c+1)for(s=0;s<D;s=s+1)if(v0[c*D+s])begin
          for(i=c*24;i<W && i<(c+1)*24;i=i+1)if(b0[s*W+i]!==b1[s*W+i])errors=errors+1;
          if(c==0&&ep0[s*(AW+1)+:AW+1]!==ep1[s*(AW+1)+:AW+1])errors=errors+1;
        end
        checks=checks+1;
      end
    end
    if(errors)$fatal(1,"S2_WRITER FAIL D=%0d errors=%0d",D,errors);
    $display("S2_WRITER PASS D=%0d W=%0d checks=%0d",D,W,checks);done=1;
  end
endmodule
module tb_writer;
wire d4,d8;
check_writer #(.D(4)) a(d4);check_writer #(.D(8)) b(d8);
initial begin wait(d4&&d8);$finish;end
endmodule
