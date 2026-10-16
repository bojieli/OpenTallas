`timescale 1ns/1ps
// Actual die-master pins. Functional clocks share a phase; physical skew is a separate gate.
// 2026-10-15 clock-structure pass: programme pin -> io_clk flop -> lockup latch -> ck core flop -> issue (+1 edge vs
// the first static front; the producer absorbs it with DELTA -1), so every public age below is one edge later.
module tb_bf_static_front;
  reg clk=0; always #5 clk=~clk;
  wire io_clk=clk;
  reg rst=0,cv=0,go=0,bv=0,pi=0,qy0=0,qy1=0;
  reg [4:0] ca=0;reg [47:0] cd=0;reg [2:0] bb=0;reg [31:0] bu=0;
  reg [1023:0] bd=0;
  reg [13:0] pa=0;reg [14:0] po=0;reg [3:0] pc=0;
  wire [775:0] c0[0:2],c1[0:2];wire [1:0] st[0:2];
  wire [37:0] prog={pc,1'b0,3'd0,po,pa,pi};
  genvar m;
  for(m=0;m<3;m=m+1) begin:g
    dsfd_bf_front_static dut(.ck(clk),.io_clk(io_clk),.rs(rst),.qy0(qy0),.qy1(qy1),
      .x0(283'd0),.x1(266'd0),.go(go),.cfg({cv,cd,ca}),
      .xb({bd,bu,4'hf,bb,(bv && m!=1),3'd0,1'b1}),
      .f_prog(prog ^ (m==2 ? 38'd2:38'd0)),.c0(c0[m]),.c1(c1[m]),.st(st[m]));
  end
  reg [37:0] prev_prog=0,prev2_prog=0,prev3_prog=0,prev4_prog=0;
  reg [37:0] sampled;
  reg [16:0] expected_tag;
  integer n=0,b,j,k;
  task tick;begin @(negedge clk);end endtask
  task cfg(input [4:0] a,input [47:0] d);begin cv=1;ca=a;cd=d;tick();end endtask
  always @(posedge clk) begin
    sampled=prog;
    #9;   // end of cycle (clk low): a seam latch without its CPIN register is transparent here and fails
    if(rst) begin
      for(integer z=0;z<3;z=z+1) begin
        if(c0[z][0] !== prev2_prog[0] || c1[z][0] !== prev2_prog[0])
          $fatal(1,"public pin issue edge shifted variant=%d",z);
        if(prev2_prog[0] && (c0[z][14:1] !== prev2_prog[14:1] || c1[z][14:1] !== prev2_prog[14:1]))
          $fatal(1,"public pin address shifted");
        if(c0[z][15] !== prev3_prog[0] || c1[z][15] !== prev3_prog[0])
          $fatal(1,"public i1 valid shifted");
        if(prev3_prog[0]) begin
          expected_tag={prev3_prog[37:34],3'd0,4'd0,
            prev3_prog[25:23]==3'd0,prev3_prog[25:23]==3'd7,
            (prev3_prog[25:23]==3'd7 && prev3_prog[22:15]==8'd7),3'd0};
          if(c0[z][34:18] !== expected_tag || c1[z][34:18] !== expected_tag)
            $fatal(1,"public source-calendar tag mismatch actual=%h expected=%h",c0[z][34:18],expected_tag);
        end
      end
      // Data traverses PINREG/PINLAT, the real XF8 FIFO, i1/i2x and CPIN.
      // The expected word comes directly from the immutable input programme.
      if(prev4_prog[0]) begin
        if(c0[0][290:35] !== 256'(prev4_prog[22:15]+1) ||
           c1[0][290:35] !== 256'(prev4_prog[22:15]+1))
          $fatal(1,"public operand payload mismatch or data age shifted");
      end
      if(prev_prog[0]) n=n+1;
    end
    prev4_prog=prev3_prog;prev3_prog=prev2_prog;prev2_prog=prev_prog;prev_prog=sampled;
  end
  initial begin
    repeat(3)tick();rst=1;repeat(5)tick();
    for(k=0;k<8;k=k+1)cfg(5'(k),(48'd1<<42)|(48'd1<<28)|(48'd1<<27)|48'(k));
    cfg(5'd8,(48'd1<<22)|(48'd8<<9)|48'd1);
    for(k=1;k<8;k=k+1)cfg(5'(8+k),48'd0);
    cfg(5'd16,48'd0);
    for(k=0;k<8;k=k+1)cfg(5'(17+k),48'(k+10));
    cv=0;repeat(8)tick();go=1;tick();go=0;repeat(9)tick();
    for(b=0;b<8;b=b+1)begin
      bb=3'(b);bv=1;bu=32'h03020100;
      bd={256'd4,256'd3,256'd2,256'd1};tick();
      bu=32'h07060504;bd={256'd8,256'd7,256'd6,256'd5};tick();bv=0;
      repeat(8)tick();
      for(j=0;j<8;j=j+1)begin pi=1;pa=14'(8*b+j);po={1'b1,3'd0,3'(b),8'(j)};pc=4'(j);tick();end
      pi=0;
    end
    repeat(260)tick();
    if(n!=64)$fatal(1,"missing public issues %d",n);
    if(st[0][1] !== 1'b0 || st[1][1] !== 1'b1 || st[2][1] !== 1'b1)
      $fatal(1,"public sticky fault qualification %b/%b/%b",st[0],st[1],st[2]);
    // Each column-return fault is captured at its own face, then the existing
    // fault OR and boundary status stages. A one-edge pulse exits exactly +3.
    for(integer q=0;q<2;q=q+1) begin
      if(q==0) qy0=1; else qy1=1;
      tick(); qy0=0;qy1=0;
      if(st[0][1] !== 1'b0)$fatal(1,"fault pin capture first edge shifted");
      tick();
      if(st[0][1] !== 1'b0)$fatal(1,"fault pin capture bypass or early status");
      tick();
      if(st[0][1] !== 1'b1)$fatal(1,"fault pin capture missing or late status");
      tick();
      if(st[0][1] !== 1'b0)$fatal(1,"fault pin capture pulse width shifted");
    end
    $display("PASS actual BF static die front:64 public-pin slots, fixed pin+programme+CPIN ages; dropped payload and address mutant fault without schedule shifts");
    $finish;
  end
endmodule
