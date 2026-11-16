`timescale 1ns/1ps
// Smallest full-shape mechanism: 8x512 rate matcher, split resets, cloned read select.
module tb_s81_rate_match_rt_rpc;
    reg wclk=0, rclk=0;
    always #0.416 wclk=~wclk;
    always #0.417 rclk=~rclk;
    reg wrst_n=0, rrst_nc=0;
    reg [7:0] rrst_nd=0;
    reg w_v=0;
    reg [511:0] w_d=512'd2;
    wire [511:0] ref_d, dut_d;
    wire ref_f, dut_f;
    ot_s81_rate_match_rt #(.NRD(8),.RPC(1)) ref_rm
      (.wclk(wclk),.wrst_n(wrst_n),.w_v(w_v),.w_d(w_d),
       .rclk(rclk),.rrst_nc(rrst_nc),.rrst_nd(rrst_nd),.r_d(ref_d),.fault(ref_f));
    ot_s81_rate_match_rt #(.NRD(8)
`ifndef RM_RPC_USE_DEFAULT
      ,.RPC(8)
`endif
    ) dut_rm
      (.wclk(wclk),.wrst_n(wrst_n),.w_v(w_v),.w_d(w_d),
       .rclk(rclk),.rrst_nc(rrst_nc),.rrst_nd(rrst_nd),.r_d(dut_d),.fault(dut_f));
    integer wc=0, rc=0, checks=0, nonidle=0, resets=0;
    integer bitn, random_word;
    function automatic [511:0] beat(input integer n);
      integer j;
      begin
        for(j=0;j<16;j=j+1) beat[j*32+:32]=(n*32'h9e3779b9)^(j*32'h452109ab)^32'h5a3c0901;
        beat[1:0]=2'b00;
      end
    endfunction
    // Bursts and idle cancellation exercise select wraps, full and empty paths.
    always @(negedge wclk) begin
      wc=wc+1;
      w_v=(wc%19!=0);
      w_d=(wc%7==0 || wc%43==0) ? 512'd2 : beat(wc);
      if(wc==8 || wc==1808 || wc==4008) wrst_n=1;
      if(wc==1800 || wc==4000) begin wrst_n=0;resets=resets+1;end
    end
    // Deliberately separate read-control and per-bank output resets. Pointer
    // clones must follow rrst_nc, never a bank's rrst_nd.
    always @(negedge rclk) begin
      rc=rc+1;
      if(rc==10 || rc==1812 || rc==4012) rrst_nc=1;
      if(rc==1804 || rc==4004) begin rrst_nc=0;resets=resets+1;end
      if(rc==13 || rc==1815 || rc==4015) rrst_nd=8'hff;
      if(rc==1806 || rc==4006) begin rrst_nd=0;resets=resets+1;end
      if(rc>40 && rc<1750) begin
        if(rc%127==0) rrst_nd[5]=0;
        if(rc%127==2) rrst_nd[5]=1;
        if(rc%251==0) rrst_nd[2]=0;
        if(rc%251==3) rrst_nd[2]=1;
      end
    end
    always @(posedge rclk) begin
      #0.001;
      checks=checks+1;
      if(ref_d!==dut_d || ref_f!==dut_f)
        $fatal(1,"RM_RT_RPC FAIL cycle=%0d rd_equal=%0b fault=%b/%b bank_reset=%h control_reset=%b",
          rc,ref_d===dut_d,ref_f,dut_f,rrst_nd,rrst_nc);
      if(rrst_nc && ref_d!==512'd2) nonidle=nonidle+1;
      if(rc>=7000) begin
        if(nonidle<1000) $fatal(1,"RM_RT_RPC stimulus insufficient: nonidle=%0d",nonidle);
        $display("RM_RT_RPC PASS checks=%0d nonidle=%0d resets=%0d copies=8 width=512 words=8 cycles_added=0",
          checks,nonidle,resets);
        $finish;
      end
    end
endmodule
