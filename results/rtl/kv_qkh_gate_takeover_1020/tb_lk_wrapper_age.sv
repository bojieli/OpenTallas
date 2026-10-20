`timescale 1ns/1ps
// Complete 16-lane LK head, actual shipped lane wrapper, original LK source oracle.
// Only valid scaled-score retire edges are compared; invalid sc_d is unspecified.
module tb_lk_wrapper_age;
  reg ck=0,rst_n=0; always #1 ck=~ck;
  reg [3:0] c_in=0; reg [1023:0] row_in=0; reg [15:0] e_in=0;
  reg [11:0] lt_in=0; reg [1:0] hid=1;
  reg q_valid_in=0; reg [5:0] q_beat_in=0; reg [511:0] q_data_in=0;
  wire [31:0] old_d,new_d; wire old_f,old_g,new_f,new_g;
  ot_qkh_head_native_r4_s_lk ua(.ck_front({4{ck}}),.ck_score(ck),.ck_kt(ck),
    .ck_stin({16{ck}}),.ck_stk({16{ck}}),.ck_lane({16{ck}}),.rst_n(rst_n),
    .c_in(c_in),.row_in(row_in),.e_in(e_in),.lt_in(lt_in),.hid(hid),
    .q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),
    .sc_d(old_d),.sc_f(old_f),.g_f(old_g));
  ot_qkh_head_native_r4_s_lk_nc32c ub(.ck_front({4{ck}}),.ck_score(ck),.ck_kt(ck),
    .ck_stin({16{ck}}),.ck_stk({16{ck}}),.ck_lane({16{ck}}),.rst_n(rst_n),
    .c_in(c_in),.row_in(row_in),.e_in(e_in),.lt_in(lt_in),.hid(hid),
    .q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),
    .sc_d(new_d),.sc_f(new_f),.g_f(new_g));
  reg [1:0] valid_retire=0;
  always @(posedge ck) if(!rst_n) valid_retire<=0;
    else valid_retire<={valid_retire[0],ua.u_kt.u_kt.sv};
  reg [31:0] hist[0:8]; reg vh[0:8];
  integer checked[0:8],mism[0:8];
  integer seed=11,edge_count=0,t,w,b,i,expect_lag=2,rows=600;
  always @(negedge ck) begin
    if(!rst_n)begin
      for(i=0;i<9;i=i+1)begin hist[i]=0;vh[i]=0;end
    end else begin
      edge_count=edge_count+1;
      for(i=8;i>0;i=i-1)begin hist[i]=hist[i-1];vh[i]=vh[i-1];end
      hist[0]=old_d; vh[0]=valid_retire[1];
      for(i=0;i<9;i=i+1)if(edge_count>200 && vh[i])begin
        checked[i]=checked[i]+1;
        if(new_d!==hist[i])begin
          mism[i]=mism[i]+1;
          if(i==expect_lag && mism[i]<6)
            $display("LK_AGE_MISMATCH edge=%0d lag=%0d expected=%h actual=%h flags=%b%b/%b%b",edge_count,i,hist[i],new_d,old_f,old_g,new_f,new_g);
        end
      end
    end
  end
  task automatic pass(input integer count);
    for(b=0;b<32;b=b+1)begin
      q_valid_in=1;q_beat_in=6'(b);
      for(w=0;w<16;w=w+1)q_data_in[32*w+:32]=32'h3c000000^($random(seed)&32'h807fffff);
      @(negedge ck);
    end
    q_valid_in=0;
    for(t=0;t<count;t=t+1)begin
      c_in={1'b1,1'b0,t==0,1'b0};
      for(w=0;w<32;w=w+1)row_in[32*w+:32]=$random(seed);
      e_in=$random(seed);@(negedge ck);
    end
    c_in=0;repeat(160)@(negedge ck);
  endtask
  initial begin
    if($value$plusargs("seed=%d",seed))begin end
    if($value$plusargs("expect_lag=%d",expect_lag))begin end
    if($value$plusargs("rows=%d",rows))begin end
    for(i=0;i<9;i=i+1)begin checked[i]=0;mism[i]=0;hist[i]=0;vh[i]=0;end
    repeat(8)@(negedge ck);rst_n=1;repeat(96)@(negedge ck);
    pass(rows);hid=2;pass(rows/2);
    for(i=0;i<9;i=i+1)$display("LK_AGE lag=%0d checked=%0d mism=%0d",i,checked[i],mism[i]);
    if(checked[expect_lag]>200 && mism[expect_lag]==0)
      $display("LK_AGE_PASS seed=%0d measured_lag=%0d compared=%0d",seed,expect_lag,checked[expect_lag]);
    else $display("LK_AGE_FAIL seed=%0d expected_lag=%0d checked=%0d mism=%0d",seed,expect_lag,checked[expect_lag],mism[expect_lag]);
    $finish;
  end
endmodule
