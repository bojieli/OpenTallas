`timescale 1ns/1ps
// RTL-BUILD-KV/ASTK 2026-10-18: the static-die heads without the node beat (ot_qkh_head_native_r4_s / _ft_s, generated
// by tools/qwen_kv_die/head_st_rtl.py) in exact lockstep against the current heads ot_qkh_head_native_r4 / _ft on every
// edge: sc_d, sc_f, g_f and the far-neighbour feed-through (ft_ti_b, ft_e_b, ft_s_b).  Stimulus: K passes with real
// row / Q words (c_in = {k issue, v issue, first, g}), random e, lt held 0 (the static ECTL's decision word: proved
// constant 0 by tb_qkd_ectl3_kiss_st) and random ft words; a second phase drives lt random (the removed nb_d path must not
// reach any kept output).  Mutant: +define+KVD_HSTMUT=1 builds the new heads with MUT 1 (hid flipped in the fronts): FAIL.
`ifndef KVD_HSTMUT
`define KVD_HSTMUT 0
`endif
module tb_qkh_head_r4_s;
  reg ck=0,rst_n=0;always #1 ck=~ck;
  reg [3:0] c_in=0;reg [1023:0] row_in=0;reg [15:0] e_in=0;reg [11:0] lt_in=0;reg [1:0] hid=2'd1;
  reg q_valid_in=0;reg [5:0] q_beat_in=0;reg [511:0] q_data_in=0;
  reg [1558:0] ft_ti_a=0;reg [15:0] ft_e_a=0;reg [33:0] ft_s_a=0;
  wire [31:0] sc_a,sc_b,sc_fa,sc_fb;wire sf_a,sf_b,gf_a,gf_b,sf_fa,sf_fb,gf_fa,gf_fb;
  wire [1558:0] ti_fa,ti_fb;wire [15:0] e_fa,e_fb;wire [33:0] s_fa,s_fb;
  ot_qkh_head_native_r4 #(.Q_FP32(1)) ua(.ck_front({4{ck}}),.ck_score(ck),.ck_kt(ck),.ck_stin({16{ck}}),.ck_stk({16{ck}}),
    .ck_nb1({16{ck}}),.ck_nb2({16{ck}}),.ck_lane({16{ck}}),.rst_n(rst_n),.c_in(c_in),.row_in(row_in),.e_in(e_in),.lt_in(lt_in),
    .hid(hid),.q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),.sc_d(sc_a),.sc_f(sf_a),.g_f(gf_a),.nb_d());
  ot_qkh_head_native_r4_s #(.Q_FP32(1),.MUT(`KVD_HSTMUT)) ub(.ck_front({4{ck}}),.ck_score(ck),.ck_kt(ck),.ck_stin({16{ck}}),
    .ck_stk({16{ck}}),.ck_lane({16{ck}}),.rst_n(rst_n),.c_in(c_in),.row_in(row_in),.e_in(e_in),.lt_in(lt_in),
    .hid(hid),.q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),.sc_d(sc_b),.sc_f(sf_b),.g_f(gf_b));
  ot_qkh_head_native_r4_ft #(.Q_FP32(1)) ufa(.ck_front({4{ck}}),.ck_score(ck),.ck_kt(ck),.ck_stin({16{ck}}),.ck_stk({16{ck}}),
    .ck_nb1({16{ck}}),.ck_nb2({16{ck}}),.ck_lane({16{ck}}),.rst_n(rst_n),.c_in(c_in),.row_in(row_in),.e_in(e_in),.lt_in(lt_in),
    .hid(hid),.q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),.sc_d(sc_fa),.sc_f(sf_fa),.g_f(gf_fa),.nb_d(),
    .ck_ft_t(ck),.ck_ft_s(ck),.ft_ti_a(ft_ti_a),.ft_e_a(ft_e_a),.ft_ti_b(ti_fa),.ft_e_b(e_fa),.ft_s_a(ft_s_a),.ft_s_b(s_fa));
  ot_qkh_head_native_r4_ft_s #(.Q_FP32(1),.MUT(`KVD_HSTMUT)) ufb(.ck_front({4{ck}}),.ck_score(ck),.ck_kt(ck),.ck_stin({16{ck}}),
    .ck_stk({16{ck}}),.ck_lane({16{ck}}),.rst_n(rst_n),.c_in(c_in),.row_in(row_in),.e_in(e_in),.lt_in(lt_in),
    .hid(hid),.q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),.sc_d(sc_fb),.sc_f(sf_fb),.g_f(gf_fb),
    .ck_ft_t(ck),.ck_ft_s(ck),.ft_ti_a(ft_ti_a),.ft_e_a(ft_e_a),.ft_ti_b(ti_fb),.ft_e_b(e_fb),.ft_s_a(ft_s_a),.ft_s_b(s_fb));
  integer edges=0,mism=0,scores=0,seed=11,t,b,w;
  always @(negedge ck)if(rst_n)begin
    edges=edges+1;
    if({sc_b,sf_b,gf_b}!=={sc_a,sf_a,gf_a} || {sc_fb,sf_fb,gf_fb}!=={sc_fa,sf_fa,gf_fa} || ti_fb!==ti_fa || e_fb!==e_fa || s_fb!==s_fa)begin
      mism=mism+1;
      if(mism<6)$display("MISMATCH edge=%0d r4 %h/%b%b vs %h/%b%b ft %h/%b%b vs %h/%b%b",edges,sc_a,sf_a,gf_a,sc_b,sf_b,gf_b,sc_fa,sf_fa,gf_fa,sc_fb,sf_fb,gf_fb);
    end
    if(ua.kpv_k[0]===1'b1)scores=scores+1;
  end
  task automatic pass(input integer rows,input integer ltr);
    // Q: 32 FP32 beats (head HD 128 x 4 heads x 32 b / 512), then K rows on every cycle
    for(b=0;b<32;b=b+1)begin q_valid_in=1;q_beat_in=6'(b);for(w=0;w<16;w=w+1)q_data_in[32*w+:32]=32'h3c000000^$random(seed)&32'h807fffff;@(negedge ck);end
    q_valid_in=0;
    for(t=0;t<rows;t=t+1)begin
      c_in={1'b1,1'b0,t==0,1'b0};for(w=0;w<32;w=w+1)row_in[32*w+:32]=$random(seed);e_in=$random(seed);
      lt_in=ltr?12'($random(seed)):12'd0;ft_ti_a={49{$random(seed)}};ft_e_a=$random(seed);ft_s_a={$random(seed),2'($random(seed))};
      @(negedge ck);
    end
    c_in=0;repeat(80)begin lt_in=ltr?12'($random(seed)):12'd0;ft_ti_a={49{$random(seed)}};@(negedge ck);end
  endtask
  initial begin
    repeat(6)@(negedge ck);rst_n=1;repeat(12)@(negedge ck);
    pass(600,0);pass(300,0);hid=2'd2;pass(400,1);
    if(mism==0 && scores>0)$display("PASS qkh_head_r4_s lockstep vs ot_qkh_head_native_r4 / _ft: %0d edges, %0d score edges, mut %0d",edges,scores,`KVD_HSTMUT);
    else $display("FAIL qkh_head_r4_s mismatches=%0d scores=%0d mut %0d",mism,scores,`KVD_HSTMUT);
    $finish;
  end
endmodule
