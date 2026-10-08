module tb;
    parameter FAST=0,ACC=5,TREE=3,MUL=5,STALL=0;
    reg rawclk=0,rst_n=0,go=0,en=1;
    wire clk=rawclk & en;
    wire[6143:0] xre;wire[6144*24-1:0] xaddr;
    wire idle,ready,mxwe;wire[15:0] progress;wire[47:0] owe;wire[48*24-1:0] oaddr;wire[48*16-1:0] omask;
    native_me_address_slice #(.G(6144),.GT(6144),.W(16),.AW(24),.NW(18),.PART(2),.SMIN(7),.TCUT(7),.NX(2048),.GOUT(48),.XD(105),.ORD(7),.MEM_EXTRA(1),.INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.FAST_ISSUE(FAST),.ACC_LAT(ACC),.TREE_LAT(TREE),.MUL_LAT(MUL)) dut(.clk(clk),.rst_n(rst_n),.go(go),.i_gbase(0),.x_re(xre),.x_addr(xaddr),.o_we(owe),.o_addr(oaddr),.o_mask(omask),.idle(idle),.ready(ready),.progress(progress),.mx_we(mxwe),.i_nout(32'd6144),.i_tiles(32'd1),.i_k(32'd32),.i_wsrc(32'd0),.i_wbase(32'd384),.i_ts(32'd256),.i_ks(32'd8),.i_js(32'd1),.i_xbase(32'd4096),.i_round(32'd1),.i_obase(32'd5175),.i_oen(32'd1),.i_amax(32'd0),.i_xks(32'd1),.i_xjs(32'd0),.i_jsh(32'd0),.i_ots(32'd8),.i_ojs(32'd1),.i_mmode(32'd0),.i_split(32'd7),.i_xcs(32'd32),.i_wcs(32'd384),.i_rmax(32'd0),.i_mbase(32'd0));
    integer n,fd;
    initial begin
     fd=$fopen("trace.csv","w");
     $fdisplay(fd,"cycle,me_clk_en,xre,xaddr,owe,oaddr,omask,idle,ready,progress,mxwe");
     #1;rst_n=1;#1;rst_n=0;#1;
     for(n=0;n<700;n=n+1) begin
      rawclk=0;en=!(STALL && n>8 && n%7==0);go=n==5;rst_n=n>=4;
      #5;
      $fdisplay(fd,"%0d,%0d,%h,%h,%h,%h,%h,%0d,%0d,%0d,%0d",n,en,xre[2047:0],xaddr[2048*24-1:0],owe,oaddr,omask,idle,ready,progress,mxwe);
      rawclk=1;#5;
     end
     $fclose(fd);$display("PASS captured700 PRE edges");$finish;
    end
    endmodule
    diff --git a/results/uarch/qwen_rom_vm_native_status_20261007/slice.sv b/results/uarch/qwen_rom_vm_native_status_20261007/slice.sv
