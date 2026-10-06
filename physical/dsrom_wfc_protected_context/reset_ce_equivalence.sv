module tb;
reg clk=0,rst=1,ce=0; reg[7:0]d=8'hbc;reg[7:0]old_q=0,new_q=0;
always @(posedge clk or negedge rst) if(ce||!rst)if(!rst)old_q<=0;else old_q<=d;
always @(posedge clk or negedge rst) if(!rst)new_q<=0;else if(ce)new_q<=d;
task check;begin #1;if(old_q!==new_q)$fatal(1,"CE/reset semantic mismatch");end endtask
initial begin
 #1;rst=0;check();rst=1;check();
 for(integer r=0;r<4;r=r+1)for(integer c=0;c<4;c=c+1)begin
  rst=0;check();rst=1;ce=1;clk=1;check();clk=0;
  case(r)0:rst=0;1:rst=1;2:rst=1'bx;3:rst=1'bz;endcase
  case(c)0:ce=0;1:ce=1;2:ce=1'bx;3:ce=1'bz;endcase
  d=d+1;check();clk=1;check();clk=0;check();
 end
 rst=0;ce=0;check();if(old_q!==0||new_q!==0)$fatal(1,"Async reset lost while stalled");
 $display("RESET_FIRST_CE_EQUIVALENCE PASS all16fourstate pairs asyncreset_understall1");$finish;
end
endmodule
