`timescale 1ns/1ps
module tb_inner_control;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;reg [12:0] op_rows=11;reg [15:0] op_c=8;reg [7:0] op_g=3;
 reg op_gs=1,w_valid=1,x_rdy=1,rdone=0,release_in=0;
 wire w_ready,busy,iss_v,iss_row_ok,iss_first,iss_last,iss_glast,iss_rev_end,arrive,released,issue_fault;
 wire [2:0] iss_slot;wire [12:0] iss_row;wire [6:0] xa;
 wire q_ready,q_busy,q_v,q_ok,q_first,q_last,q_glast,q_rev,q_arrive,q_released;
 wire [2:0] q_slot;wire [12:0] q_row;wire [6:0] q_xa;
 ot_hbrom_issue_protected #(.PROTECT(1)) u_issue(.*,.fault(issue_fault));
 ot_hbm_accel_issue #(.ENABLE(1),.XDEPTH(128)) u_ref(.clk(clk),.rst_n(rst_n),.start(start),.op_rows(op_rows),.op_c(op_c),.op_g(op_g),.op_gs(op_gs),.w_valid(w_valid),.x_rdy(x_rdy),.rdone(rdone),.release_in(release_in),.w_ready(q_ready),.busy(q_busy),.iss_v(q_v),.iss_row_ok(q_ok),.iss_first(q_first),.iss_last(q_last),.iss_glast(q_glast),.iss_rev_end(q_rev),.arrive(q_arrive),.released(q_released),.iss_slot(q_slot),.iss_row(q_row),.xa(q_xa));
 reg iv=0,ilast=0;reg [31:0] d=0;reg [2:0] islot=0;reg [11:0] itag=0;
 wire ov,fault;wire [31:0] y;wire [11:0] otag;
 wire ov_ref,fault_ref;wire [31:0] y_ref;wire [11:0] tag_ref;
 ot_hbrom_stack_protected #(.PROTECT(1)) u_stack(.*);
 ot_hbm_accel_stack #(.LEV(4),.IL(8),.TAGW(12)) s_ref(.clk(clk),.rst_n(rst_n),.iv(iv),.d(d),.ilast(ilast),.islot(islot),.itag(itag),.ov(ov_ref),.y(y_ref),.otag(tag_ref),.fault(fault_ref));
 integer cycle=0,results=0;reg compare=0;
 always @(negedge clk) if(compare) begin
   if(issue_fault || fault || fault_ref) $fatal(1,"unexpected clean-run fault cycle %0d",cycle);
   if({w_ready,busy,iss_v,arrive,released} !== {q_ready,q_busy,q_v,q_arrive,q_released} || (iss_v && {iss_row_ok,iss_slot,iss_row,iss_first,iss_last,iss_glast,iss_rev_end,xa} !== {q_ok,q_slot,q_row,q_first,q_last,q_glast,q_rev,q_xa})) $fatal(1,"issuer differs cycle %0d protected:%h baseline:%h",cycle,{w_ready,busy,iss_v,iss_row_ok,iss_slot,iss_row,iss_first,iss_last,iss_glast,iss_rev_end,xa,arrive,released},{q_ready,q_busy,q_v,q_ok,q_slot,q_row,q_first,q_last,q_glast,q_rev,q_xa,q_arrive,q_released});
   if(ov!==ov_ref || (ov && {y,otag}!=={y_ref,tag_ref})) $fatal(1,"stack differs cycle %0d",cycle);
   if(ov) begin
     if(y!==32'h40e00000) $fatal(1,"stack expected seven got %h",y);
     results=results+1;
   end
   cycle=cycle+1;
 end
 integer g,s;
 initial begin
  repeat(4) @(negedge clk);rst_n=1;
  repeat(12) @(negedge clk);compare=1;start=1;
  @(negedge clk);start=0;
  for(g=0;g<3;g=g+1) for(s=0;s<8;s=s+1) begin
   @(posedge clk);#1;iv=1;ilast=(g==2);islot=s;itag=s;d=(g==0)?32'h3f800000:(g==1)?32'h40000000:32'h40800000;
  end
  @(posedge clk);#1;iv=0;
  repeat(150) @(negedge clk);
  if(results!=8) $fatal(1,"wrong result count %0d",results);
  repeat(60) begin @(posedge clk);#1;w_valid=~w_valid;end
  @(negedge clk);compare=0;
  force u_issue.g_protected.u_b.g_lookahead.rows_q=13'h101;
  #1;if(!issue_fault || iss_v || w_ready) $fatal(1,"issuer upset escaped");
  @(negedge clk);release u_issue.g_protected.u_b.g_lookahead.rows_q;
  #1;if(!issue_fault) $fatal(1,"issuer fault not sticky");
  force u_stack.g_protected.g_lv[0].pend_v_b=8'h80;
  #1;if(!fault || ov) $fatal(1,"stack pending upset escaped");
  @(negedge clk);release u_stack.g_protected.g_lv[0].pend_v_b;
  #1;if(!fault || ov) $fatal(1,"stack fault not sticky");
  $display("PASS issuer lockstep, stack exact G3 padded tree, issuer and stack stored-state fault suppression");$finish;
 end
endmodule
