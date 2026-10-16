module tb;
  reg clk=0; always #5 clk=~clk;
  reg rst_in=0;
  reg [6:0] fv_in=0;
  reg [1127:0] fd_in=0;
  wire [6:0] fv, fv_local, rv, rvl;
  wire [1127:0] fdx, fdx_local, rd, rdl;
  ot_s81_hc_ctfx_cap_pinpipe dut(.*);
  ot_s81_hc_ctfx_cap_ref refdut(.clk(clk),.rst_in(rst_in),.fv_in(fv_in),.fd_in(fd_in),.fv(rv),.fdx(rd),.fv_local(rvl),.fdx_local(rdl));
  reg [1127:0] oldrd=0,oldrdl=0;
  reg [6:0] oldrv=0,oldrvl=0;
  integer cy,k,errors=0,checked=0,mut;
  initial begin
    if (!$value$plusargs("mut=%d",mut)) mut=0;
    for(cy=0;cy<8192;cy=cy+1) begin
      @(negedge clk);
      rst_in = (cy%511)>=5;
      fv_in = $random;
      for(k=0;k<1120;k=k+32) fd_in[k+:32]=$random;
      fd_in[1127:1120]=$random;
      @(posedge clk); #1;
      // Reset clears both the original stages and the delayed validity witness.
      // Compare only initialized data and reset epochs after both pipes drain.
      if(cy>4) begin
        checked=checked+1;
        if ((fdx !== oldrd) || (fdx_local !== oldrdl)) errors=errors+1;
        if ((cy%511)>7 && ((fv !== oldrv) || (fv_local !== oldrvl))) errors=errors+1;
      end
      oldrd=rd;oldrdl=rdl;oldrv=rv;oldrvl=rvl;
    end
    if(errors) begin $display("CAP_PINPIPE_FAIL checked=%0d errors=%0d mutant=%0d",checked,errors,mut);$fatal(1);end
    $display("CAP_PINPIPE_PASS checked=%0d bits=1128 extra_cycles=1 reset_epochs=17",checked);$finish;
  end
endmodule
