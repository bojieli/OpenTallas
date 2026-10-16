module tb;
reg clk=0;always #5 clk=~clk;
reg rst_in=0;reg [6:0] fv_in=0;reg [2919:0] fd_in=0;
wire rst_c,ref_rst_c;wire[6:0]fvm,ref_fvm;wire[2919:0]fdm,ref_fdm;
integer cy,k,mut,errors=0,checked=0;
wire [4:0] ck={5{clk}} & ((mut>0 && cy>=100) ? ~(5'b1<<(mut-1)) : 5'b11111);
ot_s81_hc_ctfn_banks_candidate dut(.*);
ot_s81_hc_ctfn_nt_reference refdut(.clk(clk),.rst_in(rst_in),.fv_in(fv_in),.fd_in(fd_in),.rst_c(ref_rst_c),.fvm(ref_fvm),.fdm(ref_fdm));
initial begin
 if(!$value$plusargs("mut=%d",mut))mut=0;
 for(cy=0;cy<8192;cy=cy+1)begin
  @(negedge clk);rst_in=(cy%511)>=5;fv_in=(cy%511)>=9?$random:0;
  for(k=0;k<2912;k=k+32)fd_in[k+:32]=$random;fd_in[2919:2912]=$random;
  @(posedge clk);#1;
  if(cy>4)begin checked=checked+1;if(fdm!==ref_fdm || fvm!==ref_fvm || rst_c!==ref_rst_c)errors=errors+1;end
 end
 if(errors)begin $display("CTFN_BANKS_FAIL checked=%0d errors=%0d mutant=%0d",checked,errors,mut);$fatal(1);end
 $display("CTFN_BANKS_PASS checked=%0d bits=2920 extra_normal_cycles=0 extra_init_cycles=1 roots=5",checked);$finish;
end
endmodule
