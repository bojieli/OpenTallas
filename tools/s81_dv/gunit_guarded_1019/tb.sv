`timescale 1ns/1ps
module tb;
`ifndef BASELINE
`define BASELINE 0
`endif
`ifndef MUT
`define MUT 0
`endif
    localparam integer BASE=`BASELINE, MUT=`MUT;
    `include "source_age.svh"
    localparam integer TAIL_L=BASE ? `GUARDED_MAIN_TAIL_L : `GUARDED_PRIVATE_TAIL_L;
    localparam integer FIRST_CT=TAIL_L+3, FIRST_L2=FIRST_CT+6;
    reg clk=0; always #0.555555 clk=~clk;
    reg rst_n=0,launch=0,mx_v=0,cw_v=0;
    reg [4:0] mx_i=0; reg [31:0] mx_y=0;
    reg [9:0] cw_a=0; reg [255:0] cw_d=0;
    reg t_set=0,t_w=0;
    wire ct_v, fault, xe_v, xd_v, ye_v, yd_v,ye_f,yd_f;
    wire [275:0] ct_b; wire [31:0] xe_x,xd_b,ye_y,yd_y;
    generate if(BASE) begin:g_baseline
      dsdv_gunit_l5 #(.MUT(MUT)) dut(
        .clk(clk),.rst_n(rst_n),.rs_i(276'd0),.rs_o(),.launch(launch),.mx_v(mx_v),.mx_i(mx_i),.mx_y(mx_y),
        .t_set(t_set),.t_w(t_w),.t_row(10'd80),.t_lm(5'd21),.t_sm(16'h35ab),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),.sid_i(4'd3),
        .ct_v(ct_v),.ct_b(ct_b),.fault(fault),.vo_n(),.vi_n(276'd0),
        .xe_v(xe_v),.xe_x(xe_x),.ye_v(ye_v),.ye_y(ye_y),.ye_f(ye_f),.xd_v(xd_v),.xd_b(xd_b),.yd_v(yd_v),.yd_y(yd_y),.yd_f(yd_f));
    end else begin:g_private
      dsdv_gunit_l5_fs_guarded_1019 #(.MUT(MUT)) dut(
        .clk(clk),.rst_n(rst_n),.rs_i(276'd0),.rs_o(),.launch(launch),.mx_v(mx_v),.mx_i(mx_i),.mx_y(mx_y),
        .t_set(t_set),.t_w(t_w),.t_row(10'd80),.t_lm(5'd21),.t_sm(16'h35ab),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),.sid_i(4'd3),
        .ct_v(ct_v),.ct_b(ct_b),.fault(fault),.vo_n(),.vi_n(276'd0),
        .xe_v(xe_v),.xe_x(xe_x),.ye_v(ye_v),.ye_y(ye_y),.ye_f(ye_f),.xd_v(xd_v),.xd_b(xd_b),.yd_v(yd_v),.yd_y(yd_y),.yd_f(yd_f));
    end endgenerate
    dsdv_gunit_l5f side(.clk(clk),.rst_n(rst_n),.xe_v(xe_v),.xe_x(xe_x),.ye_v(ye_v),.ye_y(ye_y),.ye_f(ye_f),
        .xd_v(xd_v),.xd_b(xd_b),.yd_v(yd_v),.yd_y(yd_y),.yd_f(yd_f));
    // Exact current-main CTL subcone of L4 and L0; their arithmetic cones are not involved in returning CTL rows.
    // The original instances are W277/default N2, reset region rq[0], each from ot_rst_relay REGIONS4.
    wire [3:0] rr4,rr0;
    ot_rst_relay #(.REGIONS(4)) r4(.clk(clk),.rst_n_in(rst_n),.rst_n(rr4));
    ot_rst_relay #(.REGIONS(4)) r0(.clk(clk),.rst_n_in(rst_n),.rst_n(rr0));
    wire [276:0] h4,h0;
    dsdv_gunit_pass #(.W(277)) p4(.clk(clk),.rst_n(rr4[0]),.d({ct_b,ct_v}),.q(h4));
    dsdv_gunit_pass #(.W(277)) p0(.clk(clk),.rst_n(rr0[0]),.d(h4),.q(h0));
    wire [275:0] north,south; wire l2fault;
    dsdv_gunit_l2 l2(.clk(clk),.rst_n(rst_n),.rn_i(276'd0),.rn_o(north),.rs_i(276'd0),.rs_o(south),
        .hct_v(h0[0]),.hct_b(h0[276:1]),.hf(1'b0),.rct_v(1'b0),.rct_b(276'd0),.rf(1'b0),
        .fault(l2fault),.sid(4'd3),.cw_v(1'b0),.cw_a(10'd0),.cw_d(256'd0));
    reg [31:0] mem[0:599];
    integer cyc=0,case_n=0,launch_cycle=-1,ct_count=0,n_count=0,s_count=0,checks=0;
    integer offset,age_delta;
    reg monitoring=0;
    function automatic [275:0] expected(input integer row);
      reg [275:0] b;
      begin
        b=0;b[0]=1;b[12:9]=3;b[21+:16]=16'h35ab;b[37+:5]=5;b[42+:5]=21;b[47+:10]=80+row;b[57+:4]=15;
        for(integer i=0;i<4;i=i+1)b[61+32*i+:32]=mem[75*case_n+51+4*row+i];
        expected=b;
      end
    endfunction
    always @(posedge clk) begin
      cyc=cyc+1;
      if(launch) launch_cycle=cyc;
      #0.001;
      if(monitoring) begin
        if(fault || l2fault)$fatal(1,"GUARDED_NUMERIC_FAIL fault case=%0d",case_n);
        if(ct_v)begin
          if(ct_count>=6 || ct_b!==expected(ct_count))$fatal(1,"GUARDED_NUMERIC_FAIL CTL case=%0d row=%0d got=%h expected=%h",case_n,ct_count,ct_b,expected(ct_count));
          if(cyc-launch_cycle!=FIRST_CT+ct_count+age_delta)$fatal(1,"GUARDED_AGE_FAIL ct measured=%0d expected=%0d",cyc-launch_cycle,FIRST_CT+ct_count+age_delta);
          ct_count=ct_count+1;checks=checks+1;
        end
        if(north!=0)begin
          if(n_count>=6 || north!==expected(n_count))$fatal(1,"GUARDED_NUMERIC_FAIL L2_N");
          if(cyc-launch_cycle!=FIRST_L2+n_count+age_delta)$fatal(1,"GUARDED_AGE_FAIL north measured=%0d expected=%0d",cyc-launch_cycle,FIRST_L2+n_count+age_delta);
          n_count=n_count+1;checks=checks+1;
        end
        if(south!=0)begin
          if(s_count>=6 || south!==expected(s_count))$fatal(1,"GUARDED_NUMERIC_FAIL L2_S");
          if(cyc-launch_cycle!=FIRST_L2+s_count+age_delta)$fatal(1,"GUARDED_AGE_FAIL south measured=%0d expected=%0d",cyc-launch_cycle,FIRST_L2+s_count+age_delta);
          s_count=s_count+1;checks=checks+1;
        end
      end
    end
    task automatic tick; @(negedge clk); endtask
    initial begin
      age_delta=0;offset=0;
      if($value$plusargs("AGE_DELTA=%d",age_delta))begin end
      $readmemh("vectors.hex",mem);
      repeat(16)tick();rst_n=1;repeat(16)tick();
      for(case_n=0;case_n<8;case_n=case_n+1)begin
        if(case_n==4)begin rst_n=0;repeat(16)tick();rst_n=1;repeat(16)tick();end
        t_set=case_n[0];t_w=case_n[1];
        for(integer r=0;r<6;r=r+1)begin
          cw_v=1;cw_a={1'b0,t_set,2'b00,6'(56+r)};cw_d=0;
          for(integer k=0;k<8;k=k+1)cw_d[32*k+:32]=((r/3)==t_w)?mem[75*case_n+24+8*(r%3)+k]:32'h3f400000;
          tick();
        end
        cw_a={1'b0,t_set,2'b00,6'd62};cw_d=0;
        for(integer k=0;k<3;k=k+1)cw_d[96*t_w+32*k+:32]=mem[75*case_n+48+k];
        tick();cw_v=0;
        for(integer k=0;k<24;k=k+1)begin mx_v=1;mx_i=5'(k);mx_y=mem[75*case_n+k];tick();end
        mx_v=0;repeat(16)tick();
        ct_count=0;n_count=0;s_count=0;monitoring=1;launch=1;tick();launch=0;
        repeat(FIRST_L2+12)tick();
        if(ct_count!=6 || n_count!=6 || s_count!=6)$fatal(1,"GUARDED_NUMERIC_FAIL missing rows");
        monitoring=0;
        $display("GUARDED_CASE_PASS baseline=%0d case=%0d first_ct=%0d first_l2=%0d",BASE,case_n,FIRST_CT,FIRST_L2);
      end
      $display("GUARDED_NUMERIC_PASS baseline=%0d cases=8 checks=%0d tail_L=%0d",BASE,checks,TAIL_L);$finish;
    end
endmodule
