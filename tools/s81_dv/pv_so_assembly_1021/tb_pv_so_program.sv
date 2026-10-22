`timescale 1ns/1ps
module tb_pv_so_program;
 reg clk=0;always #0.5 clk=~clk;reg rn=0;reg[514:0]q=0;wire[514:0]qp,q0;
 wire cv,pv,lv,f;wire[19:0]owner,po;wire[20:0]pos,pp;wire[7:0]se,so;wire[15:0]lf,pf;wire[2:0]pr;wire[511:0]pd;
 dsdv_pv_so_program #(.ENABLE(1))dut(.clk(clk),.rst_n(rn),.q(q),.q_pass(qp),.cfg_v(cv),.owner(owner),.position(pos),.se_jid(se),.so_jid(so),.local_first(lf),.peer_first(pf),.param_v(pv),.param_row(pr),.param_owner(po),.param_position(pp),.param_d(pd),.launch(lv),.fault(f));
 dsdv_pv_so_program off(.clk(clk),.rst_n(rn),.q(q),.q_pass(q0));
 function automatic[511:0]header(input integer subop,len);
 reg[511:0]x;begin x=0;x[511:508]=15;x[503]=1;x[502:495]=8'h45;x[491:480]=12'(len);x[479:459]=777;x[458:449]=10'h123;x[447:444]=4'(subop);x[19:0]=20'h92345;x[27:20]=8'h31;x[35:28]=8'h67;x[51:36]=16'd100;x[67:52]=16'd425;header=x;end endfunction
 integer mut=0,nc=0,np=0,nl=0;
 always @(negedge clk)if(rn)begin
 if(q0!==q)$fatal(1,"PROGRAM_DEFAULT_CHANGED");
 if(cv)begin nc=nc+1;if(owner!=20'h92345 || pos!=777 || se!=8'h31 || so!=8'h67 || lf!=100 || pf!=425)$fatal(1,"PROGRAM_CONFIG");end
 if(pv)begin if(pr!==3'(np) || po!=20'h92345 || pp!=777 || pd!==512'(1000+np))$fatal(1,"PROGRAM_PARAM %0d",np);np=np+1;end
 if(lv)nl=nl+1;
 end
 task tick;@(negedge clk);#0.01;endtask
 task send(input[511:0]w,input bit private_);begin q={2'd0,w,1'b1};if(mut==3)q[514]=1;#0.1;if(private_ && qp!==0)$fatal(1,"PROGRAM_PRIVATE_LEAK");if(!private_ && qp!==q)$fatal(1,"PROGRAM_PUBLIC_CHANGED");tick();end endtask
 reg[511:0]h;
 initial begin
 if($value$plusargs("mut=%d",mut));repeat(4)tick();rn=1;repeat(3)tick();
 h=header(0,0);if(mut==1)h[502:495]=8'h46;send(h,1);q=0;tick();
 send(header(1,5),1);for(integer k=0;k<5;k=k+1)send(512'(1000+k),1);q=0;tick();
 h=header(2,0);if(mut==2)h[479:459]=778;send(h,1);q=0;tick();
 // A normal framed payload whose high bits look private must pass unchanged.
 h=header(0,1);h[511:508]=9;send(h,0);send(header(0,0),0);q=0;repeat(3)tick();
 if(mut==0)begin if(f || nc!=1 || np!=5 || nl!=1)$fatal(1,"PROGRAM_COUNTS %0d %0d %0d fault%0d",nc,np,nl,f);$display("PROGRAM_PASS currentq cfg1 params5 launch1 passthrough default0");end
 else begin if(!f)$fatal(1,"PROGRAM_NEGATIVE_ESCAPED");$display("PROGRAM_CAUGHT mut%0d",mut);end
 $finish;
 end
endmodule
