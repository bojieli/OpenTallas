module tb_roots;
 reg clk=0,clk_l=0,clk_ref=0,rst_in=0;
 reg [6:0] fv_in; reg [1127:0] fd_in; reg[7:0]tid;reg[63:0]cs_n,cs_s;reg[274:0]dl_in;reg[32:0]ul_in;
 wire[6:0] fv_a,fv_b,fvl_a,fvl_b;wire[1127:0]fdx_a,fdx_b,fdxl_a,fdxl_b;wire[274:0]dl_a,dl_b;wire[32:0]ul_a,ul_b;
 integer mut=0,cy,i; reg[31:0]state=32'h7483898c;
 function automatic [31:0] rnd(); begin state=state^(state<<13);state=state^(state>>17);state=state^(state<<5);rnd=state;end endfunction
 norm_reference_ctfx #(.CHAIN_STEP(6)) ref_u (.clk(clk_ref),.rst_in(rst_in),.fv_in(fv_in),.fd_in(fd_in),.tid(tid),.cs_n(cs_n),.cs_s(cs_s),.dl_in(dl_in),.ul_in(ul_in),.fv(fv_a),.fdx(fdx_a),.fv_local(fvl_a),.fdx_local(fdxl_a),.dl_out(dl_a),.ul_out(ul_a));
 ot_s81_hc_ctfx_nt2 #(.CHAIN_STEP(6)) dut (.clk(clk),.clk_l(clk_l),.rst_in(rst_in),.fv_in(fv_in),.fd_in(fd_in),.tid(tid),.cs_n(cs_n),.cs_s(cs_s),.dl_in(dl_in),.ul_in(ul_in),.fv(fv_b),.fdx(fdx_b),.fv_local(fvl_b),.fdx_local(fdxl_b),.dl_out(dl_b),.ul_out(ul_b));
 initial begin
 if($value$plusargs("MUT=%d",mut))begin end
 for(cy=0;cy<2048;cy=cy+1)begin
 clk=0;clk_l=0;clk_ref=0;rst_in=(cy%511)>=4;
 fv_in=rnd();for(i=0;i<35;i=i+1)fd_in[i*32+:32]=rnd();fd_in[1127:1120]=rnd();
 tid=rnd();cs_n={rnd(),rnd()};cs_s={rnd(),rnd()};for(i=0;i<8;i=i+1)dl_in[i*32+:32]=rnd();dl_in[274:256]=rnd();ul_in={rnd(),1'b1};
 #5;clk_ref=1;clk=!(mut==1&&cy>=128);clk_l=!(mut==2&&cy>=128);#1;
 if(cy>10&&{fv_a,fdx_a,fvl_a,fdxl_a,dl_a,ul_a}!=={fv_b,fdx_b,fvl_b,fdxl_b,dl_b,ul_b})begin
 $display("ROOT_MISMATCH mutant=%0d cycle=%0d",mut,cy);$fatal(1,"root mismatch");end
 #4;
 end
 $display("ROOT_EXACT_PASS mutant=%0d cycles=2048 normal_edges_added=0",mut);$finish;
 end
endmodule
