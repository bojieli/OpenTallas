`timescale 1ns/1ps
module tb_global_x_join;
  localparam integer IBW=379,DESC=73,HW=1+IBW+DESC+2+18+6+64+1024,FV=1+IBW+DESC;
  reg ck=0;always #5 ck=~ck;
  reg rst=0,pv=0,sv=0;reg[23:0] xb=0,sa=0;reg[11:0] k=8;reg[3:0] sp=9;
  wire[HW-1:0] hw,he;wire fault,stream_fault,xt_v,xt_bad;wire[23:0]xt_a;wire[1023:0]xt_d;reg[191:0]lane_a;wire[2047:0]fp_data;
  genvar l;generate for(l=0;l<64;l=l+1)assign fp_data[32*l+:32]={xt_d[16*l+:16],16'd0};endgenerate
  integer lane;always @*for(lane=0;lane<8;lane=lane+1)lane_a[24*lane+:24]=24'h400000| (sa+lane);
  qfd_dv_stream stream(.ck(ck),.rst_n(rst),.sid(4'd0),.cfg_v(pv),.cfg_dir(2'd1),.cfg_tag(28'd1),.sw_i(1088'd0),.se_i(1088'd0),.so_e(),.so_w(),.xw_we(sv?8'hff:8'd0),.xw_addr(lane_a),.xw_data({8{32'h3f800000}}),.tw_we(),.tw_kind(),.tw_addr(),.tw_data(),.xt_v(xt_v),.xt_a(xt_a),.xt_d(xt_d),.xt_bad(xt_bad),.fault(stream_fault));
  ot_qfd_xs_tap #(.STATIC_SCHEDULE(1),.NATIVE_AFFINE(1)) dut(.clk(ck),.rst_n(rst),.xpf_v(pv),.xpf_xbase(xb),
   .xpf_xcs(k),.xpf_xks(12'd1),.xpf_split(sp),.xpf_k({6'd0,k}),.xpf_round(1'b1),
   .sw_v(xt_v),.sw_a(xt_a),.sw_m(64'hffffffffffffffff),.sw_d(fp_data),
   .aw_v(1'b0),.aw_a(24'd0),.aw_m(16'd0),.aw_d(512'd0),.gi(380'd0),.hw(hw),.he(he),.fw_i(1'b0),.fe_i(1'b0),.fault(fault));
  integer fd,n,mut=0,cases=0,got=0,expected=0,errors=0,j,ret;reg[23:0] producer;reg[1023:0] file;
  always @(negedge ck) if(rst && hw[FV]) begin
    got=got+1;
    if(hw!==he || hw[HW-1 -:1024]!=={64{16'h3f80}}) errors=errors+1;
  end
  initial begin
    if(!$value$plusargs("INPUT=%s",file))$fatal(1,"INPUT");
    ret=$value$plusargs("MUT=%d",mut);fd=$fopen(file,"r");
    repeat(4)@(negedge ck);rst=1;
    while(!$feof(fd)) begin
      ret=$fscanf(fd,"%h %h %d %d %d\n",xb,producer,k,sp,n);
      if(ret==5)begin
        cases=cases+1;pv=1;@(negedge ck);pv=0;repeat(7)@(negedge ck);
        for(j=0;j<n*8;j=j+1)begin
          sv=1;sa=producer+8*j;
          if(mut==1)sa=sa+65536;
          if(mut==2)sa=sa+64;
          if(mut==4 && (producer%65536==16384 || producer%65536==32768))sa=sa+48;
          if(mut==3)sa={8'd0,sa[15:0]};
          @(negedge ck);
        end
        sv=0;repeat(8)@(negedge ck);expected=expected+n;
      end
    end
    if(got!=expected || fault || stream_fault || xt_bad)errors=errors+1;
    $display("GLOBAL_X_JOIN cases=%0d got=%0d expected=%0d errors=%0d fault=%0d mut=%0d",cases,got,expected,errors,(fault|stream_fault|xt_bad),mut);
    if(errors)$fatal(1,"GLOBAL_X_JOIN_FAIL");
    $display("GLOBAL_X_JOIN_PASS");$finish;
  end
endmodule
