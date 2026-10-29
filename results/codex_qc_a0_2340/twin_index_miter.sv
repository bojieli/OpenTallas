module expr #(parameter REGROOT=3, parameter NEW=0, parameter MUT=0)(input wire [31:0] gb, input wire [127:0] gbc,
 input wire [4*((REGROOT>=8)?90:(REGROOT>=7)?45:27)-1:0] spc, output wire [127:0] cv);
 localparam SPB=45; localparam CW=12;
 function automatic [36:0] msk2(input [3:0] sa,input [3:0] sb,input [36:0] m);
  msk2=(((37'd1<<sa)-37'd1)&m)|(((37'd1<<sb)-37'd1)&~m);
 endfunction
 for(genvar gq=0;gq<4;gq=gq+1) begin:g
  wire [31:0] gbq=gbc[32*gq+:32]+gq;
  if(NEW) assign cv[32*gq+:32]=(REGROOT>=8)?({5'd0,gbq}&msk2(spc[4*(14+gq)+:4],spc[4*(14+gq+((REGROOT>=8 && !MUT)?SPB:0))+:4],(37'd1<<(CW/2))-37'd1)):(gb+gq)&((1<<spc[4*(14+gq)+:4])-1);
  else assign cv[32*gq+:32]=(REGROOT>=8)?({5'd0,gbq}&msk2(spc[4*(14+gq)+:4],spc[4*(14+gq+SPB)+:4],(37'd1<<(CW/2))-37'd1)):(gb+gq)&((1<<spc[4*(14+gq)+:4])-1);
 end
endmodule
module tb;
 reg [31:0] gb;reg[127:0]gbc;reg[359:0]spc;
 wire[127:0] old3,new3,old8,new8,bad8;integer n,k;integer caught=0;
 expr #(.REGROOT(3)) a(gb,gbc,spc[107:0],old3);
 expr #(.REGROOT(3),.NEW(1)) b(gb,gbc,spc[107:0],new3);
 expr #(.REGROOT(8)) c(gb,gbc,spc,old8);
 expr #(.REGROOT(8),.NEW(1)) d(gb,gbc,spc,new8);
 expr #(.REGROOT(8),.NEW(1),.MUT(1)) mutant(gb,gbc,spc,bad8);
 initial begin
 for(n=0;n<10000;n=n+1)begin
 gb=$random;for(k=0;k<4;k=k+1)gbc[k*32+:32]=$random;for(k=0;k<90;k=k+1)spc[k*4+:4]=$random;
 #1;if(old3!==new3 || old8!==new8)$fatal(1,"miter mismatch n=%d",n);
 if(bad8!==old8)caught=caught+1;
 end
 if(caught==0)$fatal(1,"mutant escaped");$display("PASS twin-index lockstep 20000 comparisons, active-twin-index mutant caught, zero cycles");$finish;
 end
endmodule
