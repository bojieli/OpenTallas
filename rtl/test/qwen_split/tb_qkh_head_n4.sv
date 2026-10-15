`timescale 1ns/1ps
module tb_qkh_head_n4;
  parameter integer MUT=0;
  reg clk=0,rst_n=0;
  always #0.5 clk=~clk;
  reg [3:0] c=0;
  reg [1023:0] row=0;
  reg [15:0] e=0;
  reg [11:0] lt=0;
  reg [1:0] hid=0;
  reg qv=0;
  reg [5:0] qb=0;
  reg [511:0] qd=0;
  wire [31:0] rsc,dsc;
  wire rsf,rgf,dsf,dgf;
  wire [1023:0] rnb,dnb;
  ot_qwen_nearhbm_head_hs u_ref (.clk(clk),.rst_n(rst_n),.c_in(c),.row_in(row),
    .e_in(e),.lt_in(lt),.hid(hid),.q_valid_in(qv),.q_beat_in(qb),.q_data_in(qd),
    .sc_d(rsc),.sc_f(rsf),.g_f(rgf),.nb_d(rnb));
`ifdef QKH_STAGED
  // N4/M2: ABC + gather +2 input +rawR4 +2 score; reference +6score/+4nb.
  ot_qkh_head_native_r4_staged_n4 #(.Q_FP32(1),.MUT(MUT)) u_dut
    (.ck_front({4{clk}}),.ck_score(clk),.ck_kt(clk),.ck_stin({16{clk}}),.ck_stk({16{clk}}),
     .ck_nb1({16{clk}}),.ck_nb2({16{clk}}),.ck_lane({16{clk}}),.ck_t1(clk),.ck_t2(clk),.ck_s1(clk),.ck_s2(clk),.ck_gather(clk),.ck_a(clk),.ck_b(clk),.ck_c(clk),
`elsif QKH_NATIVE_R4
  ot_qkh_head_native_r4 #(.Q_FP32(1),.MUT(MUT)) u_dut
    (.ck_front({4{clk}}),.ck_score(clk),.ck_kt(clk),.ck_stin({16{clk}}),.ck_stk({16{clk}}),
     .ck_nb1({16{clk}}),.ck_nb2({16{clk}}),.ck_lane({16{clk}}),
`elsif QKH_NATIVE_R3
  ot_qkh_head_native_r3 #(.Q_FP32(1),.MUT(MUT)) u_dut
    (.ck_front(clk),.ck_score(clk),.ck_kt(clk),.ck_stin({16{clk}}),.ck_stk({16{clk}}),
     .ck_nb1({16{clk}}),.ck_nb2({16{clk}}),.ck_lane({16{clk}}),
`else
  ot_qkh_head_native #(.Q_FP32(1),.MUT(MUT)) u_dut
    (.ck_front(clk),.ck_score(clk),.ck_kt(clk),.ck_stin({16{clk}}),.ck_stout({16{clk}}),.ck_lane({16{clk}}),
`endif
     .rst_n(rst_n),.c_in(c),.row_in(row),.e_in(e),.lt_in(lt),.hid(hid),
     .q_valid_in(qv),.q_beat_in(qb),.q_data_in(qd),.sc_d(dsc),.sc_f(dsf),.g_f(dgf),.nb_d(dnb));
`ifdef QKH_STAGED
  reg [33:0] rs_q1=0,rs_q2=0,rs_q3=0,rs_q4=0,rs_q5=0,rs_q6=0; reg [1023:0] rnb_q1=0,rnb_q2=0,rnb_q3=0,rnb_q4=0;
  always @(posedge clk) begin
    rs_q1<={rsc,rsf,rgf}; rs_q2<=rs_q1; rs_q3<=rs_q2;rs_q4<=rs_q3;rs_q5<=rs_q4;rs_q6<=rs_q5; rnb_q1<=rnb; rnb_q2<=rnb_q1;rnb_q3<=rnb_q2;rnb_q4<=rnb_q3;
  end
  wire [31:0] csc=rs_q6[33:2]; wire csf=rs_q6[1], cgf=rs_q6[0]; wire [1023:0] cnb=rnb_q4;
`else
  wire [31:0] csc=rsc; wire csf=rsf, cgf=rgf; wire [1023:0] cnb=rnb;
`endif
  integer cycles=0,checks=0,errors=0,resets=0;
  reg check_on=0;
  reg [31:0] last_score=0;
  integer score_changes=0,node_changes=0;
  reg [1023:0] last_node=0;
  always @(posedge clk) begin
    #0.05;
    cycles=cycles+1;
    if(check_on) begin
      checks=checks+1;
      if({csc,csf,cgf,cnb} !== {dsc,dsf,dgf,dnb}) begin
        if(errors<8) $display("HEAD_NATIVE_MISMATCH cycle=%0d sc=%h/%h sf=%b/%b gf=%b/%b nb_equal=%b",
          cycles,csc,dsc,csf,dsf,cgf,dgf,cnb===dnb);
        errors=errors+1;
      end
      if(rsc!=last_score) score_changes=score_changes+1;
      if(rnb!=last_node) node_changes=node_changes+1;
      last_score=rsc;last_node=rnb;
    end
  end
  integer h,b,l,k,j;
  task reset_head;
    begin
      @(negedge clk);rst_n=0;c=0;lt=0;qv=0;check_on=0;
      repeat(6) @(negedge clk);
      rst_n=1;resets=resets+1;
      repeat(100) @(negedge clk);
      check_on=1;
    end
  endtask
  initial begin
    reset_head();
    for(h=0;h<4;h=h+1) begin
      hid=2'(h);
      // Populate both Q rows at the reference's FP32 consumption boundary,
      // including RNE ties and alternating signs. Every head strap is exercised.
      for(b=0;b<64;b=b+1) begin
        @(negedge clk);qv=1;qb=6'(b);
        for(l=0;l<16;l=l+1)
          qd[32*l +:32]=32'h3f000000+32'(b*16+l)*32'h00011000+32'h00008000
            | ((l&1) ? 32'h80000000 : 32'd0);
      end
      @(negedge clk);qv=0;
      repeat(32) @(negedge clk);
      for(k=0;k<8;k=k+1) begin
        for(j=0;j<80;j=j+1) begin
          @(negedge clk);
          for(l=0;l<128;l=l+1) row[8*l +:8]=8'h28+8'((l+k+h)%24);
          e=16'h3f80+16'(k*13);
          c=0;lt=0;
          if(j<32 && j%8==0) c={1'b1,1'b0,j==0,1'(k&1)};
          if(j>=32 && j<64 && j%8==0) c={1'b0,1'b1,j==32,1'(k&1)};
          if(j==48) lt[4]=1;
          if(j==56) lt[0]=1;
          if(j==64) begin lt[5]=1;lt[7:6]=0;end
          if(j==72) lt[8]=1;
          if(j>=76) begin lt[9]=1;lt[11:10]=2'(j-76);end
        end
      end
      @(negedge clk);c=0;lt=0;
      repeat(128) @(negedge clk);
      if(h==1) reset_head();
    end
    // A malformed FP32 pair must still reach the reference's fault output.
    @(negedge clk);qv=1;qb=1;
    @(negedge clk);qv=0;
    repeat(48) @(negedge clk);
    if(checks<3000 || score_changes==0 || node_changes==0 || resets!=2) begin
      $display("HEAD_NATIVE_COVERAGE_FAIL checks=%0d score_changes=%0d node_changes=%0d resets=%0d",
        checks,score_changes,node_changes,resets);
      $fatal(1);
    end
    if(errors!=0) begin
      $display("HEAD_NATIVE_FAIL checks=%0d errors=%0d",checks,errors);$fatal(1);
    end
    $display("HEAD_NATIVE_PASS checks=%0d score_changes=%0d node_changes=%0d resets=%0d",
      checks,score_changes,node_changes,resets);
    $finish;
  end
endmodule
