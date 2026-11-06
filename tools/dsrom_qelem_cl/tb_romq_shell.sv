`timescale 1ps/1ps
module tb_romq_shell #(parameter integer IN_STAGES=1, OUT_STAGES=1, PAIR_INPUT=0);
  localparam integer TOTAL_STAGES=IN_STAGES+OUT_STAGES;
  reg clk=0;
  initial forever begin #416 clk=1; #417 clk=0; end
  reg rst_n=0;
  reg [603:0] driven=0;
  wire [130:0] ref_face,bypass_face,dut_face,pos_face;
  wire  cfg_v;
  wire [4:0] cfg_a;
  wire [47:0] cfg_d;
  wire  go;
  wire [1:0] go_tag;
  wire  xs_v;
  wire [7:0] xs_p;
  wire [2:0] xs_b;
  wire [255:0] xs_q0;
  wire [9:0] xs_e0;
  wire [255:0] xs_q1;
  wire [9:0] xs_e1;
  wire [2:0] xs_pos;
  assign {cfg_v, cfg_a, cfg_d, go, go_tag, xs_v, xs_p, xs_b, xs_q0, xs_e0, xs_q1, xs_e1, xs_pos}=driven;
  wire  r_walking;
  wire  r_bank_free;
  wire  r_sh_free;
  wire [1:0] r_pv;
  wire [63:0] r_pval;
  wire [31:0] r_prow;
  wire [9:0] r_pseg;
  wire [9:0] r_pnseg;
  wire [1:0] r_perr;
  wire [5:0] r_ppos;
  wire  r_busy;
  wire  r_fault;
  wire  b_walking;
  wire  b_bank_free;
  wire  b_sh_free;
  wire [1:0] b_pv;
  wire [63:0] b_pval;
  wire [31:0] b_prow;
  wire [9:0] b_pseg;
  wire [9:0] b_pnseg;
  wire [1:0] b_perr;
  wire [5:0] b_ppos;
  wire  b_busy;
  wire  b_fault;
  wire  d_walking;
  wire  d_bank_free;
  wire  d_sh_free;
  wire [1:0] d_pv;
  wire [63:0] d_pval;
  wire [31:0] d_prow;
  wire [9:0] d_pseg;
  wire [9:0] d_pnseg;
  wire [1:0] d_perr;
  wire [5:0] d_ppos;
  wire  d_busy;
  wire  d_fault;
  wire  p_walking;
  wire  p_bank_free;
  wire  p_sh_free;
  wire [1:0] p_pv;
  wire [63:0] p_pval;
  wire [31:0] p_prow;
  wire [9:0] p_pseg;
  wire [9:0] p_pnseg;
  wire [1:0] p_perr;
  wire [5:0] p_ppos;
  wire  p_busy;
  wire  p_fault;
  ot_v41_rom_elem_q_qxpq_w10_gb_split_reference #(.OLAT(0)) u_r (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag), .walking(r_walking), .bank_free(r_bank_free), .sh_free(r_sh_free), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .pv(r_pv), .pval(r_pval), .prow(r_prow), .pseg(r_pseg), .pnseg(r_pnseg), .perr(r_perr), .ppos(r_ppos), .busy(r_busy), .fault(r_fault));
  assign ref_face={r_walking, r_bank_free, r_sh_free, r_pv, r_pval, r_prow, r_pseg, r_pnseg, r_perr, r_ppos, r_busy, r_fault};
  ot_v41_rom_elem_q_qxpq_w10_gb_shell #(.OLAT(0),.IOREG(0),.INPUT_PAIR(PAIR_INPUT)) u_b (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag), .walking(b_walking), .bank_free(b_bank_free), .sh_free(b_sh_free), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .pv(b_pv), .pval(b_pval), .prow(b_prow), .pseg(b_pseg), .pnseg(b_pnseg), .perr(b_perr), .ppos(b_ppos), .busy(b_busy), .fault(b_fault));
  assign bypass_face={b_walking, b_bank_free, b_sh_free, b_pv, b_pval, b_prow, b_pseg, b_pnseg, b_perr, b_ppos, b_busy, b_fault};
  ot_v41_rom_elem_q_qxpq_w10_gb_shell #(.OLAT(1),.IOREG(1),.INPUT_PAIR(PAIR_INPUT),.INPUT_STAGES(IN_STAGES),.OUTPUT_STAGES(OUT_STAGES),.OUTPUT_NEG(1)) u_d (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag), .walking(d_walking), .bank_free(d_bank_free), .sh_free(d_sh_free), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .pv(d_pv), .pval(d_pval), .prow(d_prow), .pseg(d_pseg), .pnseg(d_pnseg), .perr(d_perr), .ppos(d_ppos), .busy(d_busy), .fault(d_fault));
  assign dut_face={d_walking, d_bank_free, d_sh_free, d_pv, d_pval, d_prow, d_pseg, d_pnseg, d_perr, d_ppos, d_busy, d_fault};
  ot_v41_rom_elem_q_qxpq_w10_gb_shell #(.OLAT(1),.IOREG(1),.INPUT_PAIR(PAIR_INPUT),.INPUT_STAGES(IN_STAGES),.OUTPUT_STAGES(OUT_STAGES),.OUTPUT_NEG(0)) u_p (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go), .go_tag(go_tag), .walking(p_walking), .bank_free(p_bank_free), .sh_free(p_sh_free), .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .pv(p_pv), .pval(p_pval), .prow(p_prow), .pseg(p_pseg), .pnseg(p_pnseg), .perr(p_perr), .ppos(p_ppos), .busy(p_busy), .fault(p_fault));
  assign pos_face={p_walking, p_bank_free, p_sh_free, p_pv, p_pval, p_prow, p_pseg, p_pnseg, p_perr, p_ppos, p_busy, p_fault};
  reg [130:0] hist [0:15];
  reg [IN_STAGES-1:0] reset_hist=0;
  reg [130:0] expected,expected_early;
  integer j;
  reg sampled_reset;
  integer n,age=0,comparisons=0,errors=0,reset_checks=0;
  function automatic [603:0] random_word;
    reg [603:0] v;
    integer k;
    begin v=0; for(k=0;k<19;k=k+1) v={v[571:0],$urandom}; random_word=v; end
  endfunction
  task automatic compare_words(input reg [130:0] got,input reg [130:0] want,input integer phase);
    begin
      comparisons=comparisons+1;
      if(got!==want) begin
        errors=errors+1;
        if(errors<5) $display("MISMATCH cycle%0d phase%0d got%h expected%h",n,phase,got,want);
      end
    end
  endtask
  initial begin
    for(j=0;j<16;j=j+1) hist[j]=0;
    for(n=0;n<2400;n=n+1) begin
      @(posedge clk); #1;
      for(j=IN_STAGES-1;j>0;j=j-1) reset_hist[j]=reset_hist[j-1];
      reset_hist[0]=rst_n; sampled_reset=reset_hist[IN_STAGES-1];
      if(!rst_n) age=0; else age=age+1;
      expected=hist[TOTAL_STAGES-1]; expected_early=hist[TOTAL_STAGES];
      if(age>TOTAL_STAGES+4) begin
        compare_words(dut_face,expected_early,0);
        compare_words(pos_face,expected,4);
        compare_words(bypass_face,ref_face,1);
      end
      for(j=15;j>0;j=j-1) hist[j]=hist[j-1]; hist[0]=ref_face;
      #(40+25*(n%6));
      if(n%127==8) rst_n=1;
      if(n%127==119) rst_n=0;
      driven=random_word();
      if(!rst_n) begin driven[603]=0;driven[549]=0;driven[546]=0; end
      #1;
      reset_checks=reset_checks+1;
      if(u_d.u_split.u_w.rst_n!==sampled_reset) begin
        errors=errors+1;
        if(errors<5) $display("RESET AGE MISMATCH cycle%0d",n);
      end
      @(negedge clk); #1;
      if(age>TOTAL_STAGES+4) begin
        compare_words(dut_face,expected,2);
        compare_words(pos_face,expected,5);
        compare_words(bypass_face,ref_face,3);
      end
    end
    $display("ROMQ_SHELL comparisons=%0d resetchecks=%0d errors=%0d",comparisons,reset_checks,errors);
    if(errors || comparisons<11000 || reset_checks<2000) $fatal(1,"ROMQ_SHELL FAIL");
    $display("ROMQ_SHELL PASS");$finish;
  end
endmodule
