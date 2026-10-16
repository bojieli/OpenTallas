`timescale 1ns/1ps
module tb_programme_local;
  parameter integer MUT=0, PRODUCTION=0;
  localparam integer W=PRODUCTION?9688:1032,E=PRODUCTION?7116:261,C=(W+255)/256,GM=PRODUCTION?301:10,LM=PRODUCTION?474:23,LC=PRODUCTION?41:8;
  localparam integer IB=(E+127)/128,IG=(C+15)/16;
  localparam [32*C-1:0] DB=PRODUCTION?{32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd1,32'd10,32'd2,32'd3,32'd1,32'd1,32'd1,32'd1,32'd1,32'd13,32'd9,32'd10,32'd3,32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd9,32'd10,32'd2,32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3}:{32'd2,32'd1,32'd1,32'd2,32'd1};
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0,cfg_we=0,start=0;
  reg [15:0] cfg_bank=0,length=0;
  reg [6:0] cfg_row=0;
  reg [255:0] cfg_data=0;
  wire bb,bv,bd,bf,lb,lv,ld,lf;
  wire [15:0] be,le;
  wire [W-1:0] bc,lc;
  ot_hbm_su_programme #(.LINE_BITS(W),.EDGES(E),.COLS(C),.DICT_BANKS(DB),.MACROS(GM)) ref_dut(
    .clk(clk),.rst_n(rst_n),.clk_macro({GM{clk}}),.cfg_we(cfg_we),.cfg_bank(cfg_bank),
    .cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),
    .busy(bb),.valid(bv),.done(bd),.fault(bf),.edge_index(be),.command(bc));
  ot_hbm_su_programme_local #(.LINE_BITS(W),.EDGES(E),.COLS(C),.DICT_BANKS(DB),
    .GLOBAL_MACROS(GM),.LOCAL_MACROS(LM),.LOCAL_COLS(LC),.MUT(MUT)) dut(
    .clk_ctl({4{clk}}),.rst_n(rst_n),.clk_cmd({LC{clk}}),.clk_macro({LM{clk}}),
    .cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),
    .busy(lb),.valid(lv),.done(ld),.fault(lf),.edge_index(le),.command(lc));
  function integer nb(input integer c);
    begin nb=DB[c*32+:32]; end
  endfunction
  function integer db(input integer c);
    integer k; begin db=IG*IB; for(k=0;k<c;k=k+1)db=db+nb(k); end
  endfunction
  function integer idx(input integer c,input integer r,input integer patch);
    begin idx=((r*17+c*37)+((patch!=0 && r==0)?19:0))%(nb(c)*128); end
  endfunction
  function [255:0] dictword(input integer c,input integer a);
    integer k; begin
      for(k=0;k<8;k=k+1)dictword[k*32+:32]=(32'h9e3779b9*(a+1)) ^ (32'h1020304*(c+1)) ^ (32'h7654321*k);
    end
  endfunction
  function [255:0] indexword(input integer g,input integer r,input integer patch);
    integer c; begin indexword=0;for(c=g*16;c<C && c<(g+1)*16;c=c+1)indexword[(c%16)*16+:16]=idx(c,r,patch);end
  endfunction
  function [W-1:0] golden(input integer r,input integer patch);
    integer c,k; reg [255:0] x; begin
      golden=0;
      for(c=0;c<C;c=c+1)begin
        x=dictword(c,idx(c,r,patch));
        for(k=0;k<256;k=k+1)if(c*256+k<W)golden[c*256+k]=x[k];
      end
    end
  endfunction
  task write_row(input integer bank,input integer row,input [255:0] data);
    begin
      @(negedge clk);cfg_we=1;cfg_bank=bank;cfg_row=row;cfg_data=data;
      @(negedge clk);cfg_we=0;
    end
  endtask
  integer cycle=0,origin=0,bseen=0,lseen=0,want=0,patch=0;
  integer total=0,runs=0;
  reg checking=0;
  always @(posedge clk)begin
    cycle=cycle+1;
    if(start && rst_n && !bb && !lb && length>0 && length<=E)begin
      origin=cycle;bseen=0;lseen=0;want=length;checking=1;
    end
    #1;
    if(checking)begin
      if(bf || lf)$fatal(1,"unexpected fault base=%b local=%b",bf,lf);
      if(bv)begin
        if(cycle!=origin+3+bseen || be!==bseen || bc!==golden(bseen,patch))
          $fatal(1,"baseline mismatch cycle=%0d row=%0d phase=%0d",cycle,bseen,cycle-origin);
        bseen=bseen+1;
      end else if(cycle>origin && bc!==0)$fatal(1,"baseline nonzero outside valid");
      if(lv)begin
        if(cycle!=origin+5+lseen || le!==lseen || lc!==golden(lseen,patch))
          $fatal(1,"local mismatch MUT=%0d cycle=%0d row=%0d phase=%0d",MUT,cycle,lseen,cycle-origin);
        lseen=lseen+1;
      end else if(cycle>origin && lc!==0)$fatal(1,"local nonzero outside valid MUT=%0d cycle=%0d",MUT,cycle);
      if(bd && (bseen!=want || cycle!=origin+2+want))$fatal(1,"baseline retire timing");
      if(ld)begin
        if(lseen!=want || bseen!=want || cycle!=origin+4+want)$fatal(1,"local retire timing");
        total=total+lseen;runs=runs+1;checking=0;
      end
    end
  end
  task run_image(input integer n);
    integer k;begin
      @(negedge clk);length=n;start=1;
      @(negedge clk);start=0;
      for(k=0;k<n+12;k=k+1)@(negedge clk);
      if(checking || bseen!=n || lseen!=n || bb || lb)$fatal(1,"missing completion");
    end
  endtask
  integer c,a,r,k,g;
  initial begin
    repeat(5)@(negedge clk);rst_n=1;
    for(c=0;c<C;c=c+1)for(a=0;a<nb(c)*128;a=a+1)
      write_row(db(c)+a/128,a%128,dictword(c,a));
    for(g=0;g<IG;g=g+1)for(r=0;r<E;r=r+1)write_row(g*IB+r/128,r%128,indexword(g,r,0));
    repeat(3)@(negedge clk);
    run_image(E);
    run_image(17);
    // Last row write and start on the same external edge: the added local
    // install capture must commit before the first registered read reaches SRAM.
    @(negedge clk);patch=1;
    for(g=1;g<IG;g=g+1)write_row(g*IB,0,indexword(g,0,1));cfg_we=1;cfg_bank=0;cfg_row=0;cfg_data=indexword(0,0,1);length=4;start=1;
    @(negedge clk);cfg_we=0;start=0;
    repeat(18)@(negedge clk);
    if(checking || runs!=3 || total!=282 || bf || lf)$fatal(1,"restart/immediate commit mismatch");
    // Bounds fault checks do not reschedule normal execution.
    @(negedge clk);length=0;start=1;
    @(negedge clk);start=0;
    if(!bf || !lf || bb || lb)$fatal(1,"zero length must fault");
    rst_n=0;repeat(4)@(negedge clk);rst_n=1;
    @(negedge clk);length=E+1;start=1;
    @(negedge clk);start=0;
    if(!bf || !lf || bb || lb)$fatal(1,"oversize length must fault");
    rst_n=0;repeat(4)@(negedge clk);rst_n=1;
    write_row(GM,0,0);
    if(!bf || !lf)$fatal(1,"bank bounds must fault");
    $display("PROGRAMME_LOCAL_PASS rows=%0d runs=%0d extra_edges=2 II=1 actual_macro_instances=%0d production=%0d",total,runs,GM+LM,PRODUCTION);
    $finish;
  end
endmodule
