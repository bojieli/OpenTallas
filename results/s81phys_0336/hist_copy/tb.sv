`timescale 1ps/1ps
module tb;
  reg clk=0;
  always begin #416 clk=1; #417 clk=0; end
  reg rst_n=0;
  reg [7:0] clr=0;
  reg iv=0;
  reg [15:0] en=0;
  reg [127:0] dg=0;
  reg [31:0] gs=0;
  wire [239:0] sum_r,sum_c,sum_m;
  wire [175:0] bin_r,bin_c,bin_m;
  wire busy_r,busy_c,busy_m;
  hist_ref r(.clk(clk),.rst_n(rst_n),.clr(clr),.i_v(iv),.i_en(en),.i_dg(dg),.gsel_d(gs),.gsum(sum_r),.gbin(bin_r),.busy(busy_r));
  hist_copy c(.clk(clk),.rst_n(rst_n),.clr(clr),.i_v(iv),.i_en(en),.i_dg(dg),.gsel_d(gs),.gsum(sum_c),.gbin(bin_c),.busy(busy_c));
  hist_mut m(.clk(clk),.rst_n(rst_n),.clr(clr),.i_v(iv),.i_en(en),.i_dg(dg),.gsel_d(gs),.gsum(sum_m),.gbin(bin_m),.busy(busy_m));
  reg [31:0] rng=32'h48192837;
  integer cyc,checks=0,mutants=0,resets=0;
  initial begin
    for(cyc=0;cyc<12000;cyc=cyc+1)begin
      @(negedge clk);
      rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
      rst_n=!(cyc<64 || (cyc%3000>=2900 && cyc%3000<2964));
      if(!rst_n)resets=resets+1;
      clr=cyc%97==0 ? 8'hff : (cyc%31==0 ? 8'(rng>>8) : 8'h00);
      iv=rng[0] | (cyc%3==0);
      en=16'(rng);
      dg={rng, rng^32'h813d93a5, {rng[15:0],rng[31:16]},~rng};
      gs=rng^32'(cyc);
      @(posedge clk);#1;
      if(cyc>72 && rst_n)begin
        checks=checks+1;
        if({sum_r,bin_r,busy_r} !== {sum_c,bin_c,busy_c})
          $fatal(1,"HIST_COPY FAIL cyc=%0d",cyc);
        if({sum_r,bin_r,busy_r} !== {sum_m,bin_m,busy_m})mutants=mutants+1;
      end
    end
    if(mutants==0)$fatal(1,"HIST_COPY mutant blind");
    $display("HIST_COPY PASS cycles=%0d checks=%0d reset_edges=%0d mismatches=0 mutant_mismatches=%0d",cyc,checks,resets,mutants);
    $finish;
  end
endmodule
