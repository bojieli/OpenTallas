`timescale 1ns/1ps
module tb_hgi_idx_topk;
 parameter MUTANT=0;
 reg clk=0;always #0.4166665 clk=~clk;
 reg rst_n=0,cv=0,iv=0,ready=1;
 reg [3:0] unit_id=9;reg [5:0] op=2;
 reg [15:0] param_k;reg [31:0] n,m,score;
 wire cr,ir,ov,last,vv,done;wire[3:0]error;
 wire[31:0]id,value,row;
 ot_hgi_idx_topk #(.ENABLE(1),.MUTANT_TIE(MUTANT)) dut(
 .clk(clk),.rst_n(rst_n),.cmd_valid(cv),.cmd_ready(cr),.cmd_unit(unit_id),.cmd_op(op),
 .cmd_param(param_k),.cmd_n(n),.cmd_m(m),.cmd_values(1'b1),.in_valid(iv),.in_ready(ir),
 .in_score(score),.out_valid(ov),.out_ready(ready),.out_id(id),.out_score(value),
 .out_row(row),.out_last(last),.out_values_valid(vv),.done(done),.error(error));
 reg[31:0]scores[0:4095];integer refids[0:4095];
 integer i,j,tmp,kidx,ki,ri,t,nn,kk,tests=0;
 function automatic[31:0]key(input[31:0]s);reg[31:0]c;begin c=s[30:0]==0?0:s;key=c[31]?~c:(c|32'h80000000);end endfunction
 task run(input integer count,input integer want,input integer rows);
 begin
  @(negedge clk);n=count;m=rows;param_k=want;cv=1;
  @(negedge clk);cv=0;
  for(ri=0;ri<rows;ri=ri+1)begin
   for(i=0;i<count;i=i+1)begin
    case(i%13)
     0:scores[i]=32'h80000000;1:scores[i]=0;2:scores[i]=32'hff800000;
     3:scores[i]=32'h7f800000;4:scores[i]=32'hbf800000+((i*31+ri*17)%67);
     default:scores[i]=32'h3f800000+((i*31+ri*17)%67);
    endcase
    refids[i]=i;
   end
   for(i=1;i<count;i=i+1)begin
    tmp=refids[i];j=i;
    while(j>0&&((key(scores[tmp])>key(scores[refids[j-1]]))||
      ((key(scores[tmp])==key(scores[refids[j-1]]))&&tmp<refids[j-1])))begin
     refids[j]=refids[j-1];j=j-1;
    end
    refids[j]=tmp;
   end
   for(t=0;t<count;t=t+1)begin
    @(negedge clk);iv=1;score=scores[t];
   end
   @(negedge clk);iv=0;ready=0;
   repeat(3)@(negedge clk);
   for(t=0;t<want;t=t+1)begin
    if(!ov||id!==refids[t]||value!==scores[refids[t]]||row!==ri||last!==(t==want-1)||!vv)
     $fatal(1,"topk case%0d row%0d out%0d id%0d expected%0d",tests,ri,t,id,refids[t]);
    ready=1;@(negedge clk);ready=0;
    if(t<want-1)repeat(t%3)@(negedge clk);
   end
  end
  wait(done);if(error)$fatal(1,"unexpected error");@(negedge clk);tests=tests+1;
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  run(17,1,2);run(17,2,2);run(384,6,2);run(65,8,2);run(1024,512,2);run(4096,2048,1);
  @(negedge clk);n=1;m=1;param_k=1;cv=1;@(negedge clk);cv=0;iv=1;score=32'h7fc00001;
  @(negedge clk);iv=0;if(!done||error!=3||ov)$fatal(1,"NaN did not fail closed");
  @(negedge clk);op=63;cv=1;@(negedge clk);cv=0;if(!done||error!=1)$fatal(1,"invalid op accepted");
  $display("PASS HGI TOPK k1/2/6/8/512/2048 multirow ties NaN invalidop backpressure fullK2048");$finish;
 end
 initial begin repeat(200000)@(posedge clk);$fatal(1,"mechanism timeout");end
endmodule
