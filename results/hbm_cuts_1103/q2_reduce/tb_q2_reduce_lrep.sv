`timescale 1ns/1ps
// DIE-HBM-61/CUTS 11-03: lockstep bench, ot_hgi_coll_reduce_static_pr compiled with OT_HBM_REDUCE_LREP (per-lane kept
// control pin copies, ot_hgi_coll_reduce_static_lr) == gold (main's _pr + reduce_static, modules prefixed gold_), 0 edge
// shift, every output every edge. Random inputs (every control bit random, so faults/conflicts are exercised too) +
// periodic resets. LMUT != 0 must FAIL.
module tb_q2_reduce_lrep;
  parameter integer CYC=60000, DLC=1; // DLC: DUT LOCAL_CTRL (recipe cut1 = 1; gold stays 0)
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0, clear=0, in_v=0, load_v=0, add_read=0, add_issue=0, pub_read=0, pub_bf16=0, pub_release=0, pub_issue=0;
  reg [544:0] in_flit=0; reg [3:0] load_tag=0, read_tag=0, pub_tag_a=0, pub_tag_b=0; reg [32:0] pub_meta=0;
  wire a_v,b_v,a_f,b_f; wire [544:0] a_o,b_o; wire [7:0] a_c,b_c;
  gold_ot_hgi_coll_reduce_static_pr g(.clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),.clear(clear),
    .in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),.add_issue(add_issue),
    .pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),.pub_meta(pub_meta),.pub_release(pub_release),
    .pub_issue(pub_issue),.out_v(a_v),.out_flit(a_o),.fault(a_f),.fault_cause(a_c));
  ot_hgi_coll_reduce_static_pr #(.LOCAL_CTRL(DLC)) d(.clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),.clear(clear),
    .in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),.add_issue(add_issue),
    .pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),.pub_meta(pub_meta),.pub_release(pub_release),
    .pub_issue(pub_issue),.out_v(b_v),.out_flit(b_o),.fault(b_f),.fault_cause(b_c));
  integer cyc, ph, bad=0, nc=0, nv=0, nnz=0, nkn=0, i;
  initial begin
    for(cyc=0;cyc<CYC;cyc=cyc+1) begin
      @(negedge clk);
      ph=cyc%3000; rst_n=(ph>=4);
      clear=($urandom%200)==0; load_v=($urandom%3)==0; add_read=($urandom%3)==0; add_issue=($urandom%3)==0;
      in_v=(($urandom%20)==0)?~(load_v|add_read):(load_v|add_read);
      pub_read=($urandom%3)==0; pub_issue=($urandom%3)==0; pub_release=$urandom; pub_bf16=$urandom;
      load_tag=$urandom; read_tag=$urandom; pub_tag_a=$urandom; pub_tag_b=$urandom; pub_meta={$urandom,$urandom};
      for(i=0;i<18;i=i+1) in_flit[i*32+:32]=$urandom;
      if(cyc>8) begin
        nc=nc+1; nv=nv+a_v; if(a_v===1'b1 && ^a_o[511:0]!==1'bx) begin nkn=nkn+1; if(a_o[511:0]!=0) nnz=nnz+1; end
        if({a_v,a_o,a_f,a_c}!=={b_v,b_o,b_f,b_c}) begin bad=bad+1;
          if(bad<=5) $display("LREP_EQ_MISMATCH cyc=%0d v %b/%b f %b/%b cause %h/%h flit_eq %b",cyc,a_v,b_v,a_f,b_f,a_c,b_c,a_o===b_o); end
      end
    end
    if(bad==0) $display("LREP_EQ PASS compared=%0d out_v=%0d known_flit=%0d known_nonzero_flit=%0d",nc,nv,nkn,nnz);
    else $display("LREP_EQ FAIL mismatches=%0d of %0d",bad,nc);
    $finish;
  end
endmodule
