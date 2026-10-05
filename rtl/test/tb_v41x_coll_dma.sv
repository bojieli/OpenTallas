`timescale 1ns/1ps
module tb_v41x_coll_dma;
    reg clk=0,rst_n=0,go=0,mode=0,rnd=0;
    always #5 clk=~clk;
    reg [4:0] src=0,n=0,dst=0;
    reg [7:0] tag=0;
    wire busy,fault,vm_re,vm_we,e_valid,e_last,e_mode;
    wire [4:0] vm_raddr,vm_waddr;
    reg [31:0] vm_rq=0;
    wire [31:0] vm_wdata,e_data;
    reg o_valid=0,o_last=0,o_err=0,engine_fault=0;
    reg [31:0] o_data=0;
    reg [1:0] o_rank=0;
    wire [31:0] words_out,words_in;
    wire [7:0] e_tag;
    reg [31:0] mem[0:31];
    ot_chip_v41x_coll_dma #(.WA(5),.FW(32),.TAGW(8),.N(4)) dut (
      .clk(clk),.rst_n(rst_n),.go(go),.mode(mode),.rnd(rnd),.tag(tag),
      .src(src),.n(n),.dst(dst),.busy(busy),.fault(fault),
      .words_out(words_out),.words_in(words_in),.vm_re(vm_re),.vm_raddr(vm_raddr),
      .vm_rq(vm_rq),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),
      .e_valid(e_valid),.e_ready(1'b1),.e_data(e_data),.e_last(e_last),
      .e_mode(e_mode),.e_tag(e_tag),.o_valid(o_valid),.o_data(o_data),
      .o_last(o_last),.o_rank(o_rank),.o_err(o_err),.engine_fault(engine_fault));
    always @(posedge clk) begin
      if(vm_re) vm_rq<=mem[vm_raddr];
      if(vm_we) mem[vm_waddr]<=vm_wdata;
    end
    integer cyc=0, sent=0;
    always @(posedge clk) begin
      cyc<=cyc+1;
      if(cyc>150) $fatal(1,"timeout busy=%b sent=%0d",busy,sent);
      if(e_valid) begin
        if(e_data !== mem[2+sent%2]) $fatal(1,"read mismatch %h at %0d",e_data,sent);
        sent<=sent+1;
      end
    end
    task issue(input bit m,input bit r,input [4:0] d);
      begin
        @(negedge clk); mode=m; rnd=r; src=2; n=2; dst=d; go=1;
        @(negedge clk); go=0;
        if(!busy) $fatal(1,"busy did not rise after issue");
      end
    endtask
    task result(input [1:0] rank,input [31:0] data,input bit last);
      begin
        @(negedge clk); o_valid=1; o_rank=rank; o_data=data; o_last=last;
        @(negedge clk); o_valid=0; o_last=0;
      end
    endtask
    initial begin
      for(integer j=0;j<32;j=j+1) mem[j]=0;
      mem[2]=32'h3f800000; mem[3]=32'h40000000;
      repeat(4) @(negedge clk); rst_n=1;
      issue(1,0,10);
      wait(sent==2);
      for(integer k=0;k<2;k=k+1)
        for(integer r=0;r<4;r=r+1)
          result(r,100+10*k+r,k==1 && r==3);
      if(busy || fault) $fatal(1,"gather completion busy=%b fault=%b",busy,fault);
      for(integer k=0;k<2;k=k+1)
        for(integer r=0;r<4;r=r+1)
          if(mem[10+r*2+k] !== 100+10*k+r) $fatal(1,"rank-major dst r=%0d k=%0d got=%0d",r,k,mem[10+r*2+k]);
      issue(0,1,20);
      wait(sent==4);
      result(0,32'h3f808000,0);
      result(0,32'h3f818000,1);
      if(busy || fault) $fatal(1,"reduce completion busy=%b fault=%b",busy,fault);
      if(mem[20] !== 32'h3f800000 || mem[21] !== 32'h3f820000)
        $fatal(1,"BF16 round mismatch %h %h",mem[20],mem[21]);
      // Range/overlap faults are sticky and do not start DMA.
      @(negedge clk); src=2; n=2; dst=3; go=1;
      @(negedge clk); go=0;
      if(!fault || busy) $fatal(1,"overlap did not fault");
      $display("CDMA_PASS gather_rank_major bf16_rne overlap_fault reads=%0d writes=%0d",words_out,words_in);
      $finish;
    end
endmodule
