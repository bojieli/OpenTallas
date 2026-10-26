`timescale 1ns/1ps
module tb_s81hd_add_l4;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0, v=0;
  reg [31:0] a=0,b=0;
  wire [31:0] gy,ny; wire [1:0] ge,ne; wire gv,nv;
  ot_v41_fadd #(.CUT(9'h1ff),.SPLIT9(1)) gold(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(gy),.err(ge),.valid_out(gv));
  ot_hdc_fp32_add_f12_l4 candidate(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(ny),.err(ne),.valid_out(nv));
  reg [33:0] gq[0:250000],nq[0:250000];
  integer ng=0,nn=0,nc=0,bad=0,sent=0,seed=1,mut=0,i,j;
  reg [31:0] special[0:23];
  task sample;
    begin
      @(negedge clk);
      if (rst_n) begin
        if(gv) begin gq[ng]={ge,gy};ng=ng+1;end
        if(nv) begin nq[nn]={ne,ny ^ (mut!=0 ? 32'd1:32'd0)};nn=nn+1;end
        while(nc<ng && nc<nn) begin
          if(gq[nc] !== nq[nc]) begin
            if(bad<8) $display("DIFF index=%0d gold=%h candidate=%h",nc,gq[nc],nq[nc]);
            bad=bad+1;
          end
          nc=nc+1;
        end
      end
    end
  endtask
  initial begin
    if($value$plusargs("SEED=%d",seed)) begin end
    if($value$plusargs("MUT=%d",mut)) begin end
    i=$urandom(seed);
    special[0]=32'h00000000;special[1]=32'h80000000;special[2]=32'h00000001;special[3]=32'h80000001;
    special[4]=32'h007fffff;special[5]=32'h807fffff;special[6]=32'h00800000;special[7]=32'h80800000;
    special[8]=32'h3f800000;special[9]=32'hbf800000;special[10]=32'h3f000000;special[11]=32'hbf000000;
    special[12]=32'h7f7fffff;special[13]=32'hff7fffff;special[14]=32'h7f800000;special[15]=32'hff800000;
    special[16]=32'h7fc00000;special[17]=32'h7f800001;special[18]=32'h3f800001;special[19]=32'h3f7fffff;
    special[20]=32'h33800000;special[21]=32'h33000000;special[22]=32'h01000000;special[23]=32'h81000000;
    repeat(4) sample(); rst_n=1;
    for(i=0;i<24;i=i+1) for(j=0;j<24;j=j+1) begin
      v=1;a=special[i];b=special[j];sent=sent+1;sample();
    end
    for(i=0;i<200000;i=i+1) begin
      v=($urandom_range(0,7)!=0);a=$urandom();b=$urandom();
      if(i%8==0) b={~a[31],a[30:0]};
      if(i%8==1) b=32'd0;
      if(v) sent=sent+1;
      sample();
    end
    v=0; repeat(20) sample();
    if(ng!=sent || nn!=sent || nc!=sent) $fatal(1,"COUNT sent=%0d gold=%0d candidate=%0d compared=%0d",sent,ng,nn,nc);
    if(bad!=0) $fatal(1,"FAIL checks=%0d mismatches=%0d",nc,bad);
    $display("PASS checks=%0d old_latency=11 new_latency=4 mutant=%0d",nc,mut);$finish;
  end
endmodule
