`timescale 1ns/1ps
module tb_tx_rne;
 parameter integer MUT=0;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg [127:0] x=0,wupper=0;
 reg [5:0]ctrl=0;reg [3:0]gm=0;reg round=0;
 wire [206:0] r0;wire [197:0]q;
 qwen_tx_rne_r0 #(.MUT(MUT)) a(.clk(clk),.rst_n(rst_n),.x(x),.wupper(wupper),.ctrl(ctrl),.gm(gm),.round(round),.q(r0));
 qwen_tx_rne_r1 #(.MUT(MUT)) b(.clk(clk),.rst_n(rst_n),.d(r0),.q(q));
 // Independent behavioral reference models both actual reset release windows.
 // The reference stores267 bits at R0; rounding stays full32 until reference R1.
 reg [266:0] ref0=0;reg [197:0]ref1=0;
 integer release_age=0;
 integer checks=0,async_checks=0,reset_checks=0,captures=0,ties=0,above=0,below=0,masks=0,wraps=0;
 reg [197:0] expected0;
 reg [31:0] rw,rounded32,selected32;
 integer i,c,g;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin release_age=0;ref0<=0;ref1<=0;end
  else begin
   release_age=release_age+1;
   if(release_age<=3)begin ref0<=0;ref1<=0;end
   else begin
    ref0<={round,gm,ctrl,wupper,x};
    for(i=0;i<4;i=i+1)begin
     rw=ref0[32*i+:32];rounded32=rw+32'h7fff+{31'b0,rw[16]};
     selected32=!ref0[262+i]?32'b0:ref0[266]?(rounded32&32'hffff0000):rw;
     ref1[16*i+:16]<=selected32[31:16];
    end
    ref1[197:64]<=ref0[261:128];
   end
  end
 end
 task compare;
 begin
  if(q!==ref1)$fatal(1,"FAIL RNE two-edge/reset c=%0d age=%0d ref=%h got=%h",c,release_age,ref1,q);
  if(!rst_n||release_age<=3)begin
   if(r0!==207'b0||q!==198'b0)$fatal(1,"FAIL RNE reset/warmup c=%0d age=%0d",c,release_age);
   reset_checks=reset_checks+1;
  end
  checks=checks+1;
 end endtask
 initial begin
  // Force a real async reset transition, then check before any clock edge.
  #1;rst_n=1;#1;rst_n=0;#1;compare();async_checks=async_checks+1;
  for(c=0;c<4096;c=c+1)begin
   @(negedge clk);
   if(c==16||c==1043||c==2068||c==3081)rst_n=1;
   if(c==1027||c==2067||c==3065)begin
    #1;rst_n=0;#1;compare();async_checks=async_checks+1;
   end
   ctrl=c%64;gm=(c/4)%16;round=c%2;
   wupper={$random,$random,$random,$random};
   for(g=0;g<4;g=g+1)begin
    x[32*g+:32]=$random;
    case((c/2+g)%12)
     0:begin x[32*g+:16]=16'h7fff;below=below+1;end
     1:begin x[32*g+:16]=16'h8000;x[32*g+16]=0;ties=ties+1;end
     2:begin x[32*g+:16]=16'h8000;x[32*g+16]=1;ties=ties+1;end
     3:begin x[32*g+:16]=16'h8001;above=above+1;end
     4:begin x[32*g+:32]=32'hffff8001;wraps=wraps+1;end
     5:x[32*g+:32]=32'h7f7fffff;
     6:x[32*g+:32]=32'h7fc18000;
     7:x[32*g+:32]=32'h00008000;
     8:x[32*g+:32]=32'h80008000;
     9:x[32*g+:32]=32'hff800001;
     default:;
    endcase
    if(!gm[g])masks=masks+1;
   end
   // R0/R1 outputs must remain stable between edges after arbitrary input changes.
   #1;compare();
   @(posedge clk);#1;compare();
   if(rst_n&&release_age>4)captures=captures+1;
  end
  if(checks<8192||captures<3900||async_checks!=4||reset_checks<80||ties<2000||masks<8000||wraps<1000)$fatal(1,"FAIL RNE coverage");
  $display("PASS RNE207to198 two-existing-edges checks=%0d captures=%0d async=%0d reset=%0d ties=%0d above=%0d below=%0d masks=%0d wraps=%0d",checks,captures,async_checks,reset_checks,ties,above,below,masks,wraps);
  $finish;
 end
endmodule
