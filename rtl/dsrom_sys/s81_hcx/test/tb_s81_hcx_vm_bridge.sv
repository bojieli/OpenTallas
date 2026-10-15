`timescale 1ns/1ps
module tb_s81_hcx_vm_bridge;
 reg clk=0; always #5 clk=~clk;
 reg rn=0; reg [337:0] q=0; wire [273:0] r;
 wire rv,wv;reg rr=0,wr=0,rc=0,sv=0;wire[13:0]ra,wa;wire[15:0]wm;wire[511:0]wd;reg[511:0]sd=0;wire f;
`ifdef MUT_EARLY_COMMIT
 localparam integer MUT=1;
`else
 localparam integer MUT=0;
`endif
 ot_s81_hcx_vm_bridge #(.MUT_EARLY_COMMIT(MUT)) u(.clk(clk),.rst_n(rn),.job_start(1'b0),.vmq(q),.vmr(r),.rq_v(rv),.rq_rdy(rr),.rq_row(ra),.rs_v(sv),.rs_d(sd),.wq_v(wv),.wq_rdy(wr),.wq_commit(rc),.wq_row(wa),.wq_mask(wm),.wq_d(wd),.fault(f));
 integer cycle=0,responses=0;
 always @(posedge clk) cycle<=cycle+1;
 always @(negedge clk) if(r[273]) responses=responses+1;
 task send(input bit we,input[26:0]sec,input[255:0]data,input[31:0]mask,input[15:0]tag);
  @(negedge clk);q={1'b1,we,sec,5'd0,data,mask,tag};@(negedge clk);q=0;
 endtask
 task read_return(input[13:0]row,input[1:0]quarter,input[15:0]tag);
  wait(rv);@(negedge clk);if(ra!==row)$fatal(1,"wrong row");rr=1;
  @(negedge clk);rr=0;repeat(3)@(negedge clk);sd={{8{16'h4080}},{8{16'h4040}},{8{16'h4000}},{8{16'h3f80}}};sv=1;
  @(negedge clk);sv=0;if(!r[273]||r[272:257]!==tag||r[256]||r[255:0] !== {8{(quarter==0 ? 32'h3f800000 : quarter==1 ? 32'h40000000 : quarter==2 ? 32'h40400000 : 32'h40800000)}})$fatal(1,"wrong BF16 quarter/tag");
 endtask
 initial begin
  repeat(3)@(negedge clk);rn=1;
  send(0,27'd20,0,0,16'h1);send(0,27'd25,0,0,16'h2);
  send(0,27'd30,0,0,16'h3);send(0,27'd35,0,0,16'h4);
  repeat(5)@(negedge clk);if(responses!=0)$fatal(1,"unstalled response");
  read_return(5,0,1);read_return(6,1,2);read_return(7,2,3);read_return(8,3,4);
  send(0,27'd34,0,0,16'h7);@(negedge clk);
  if(!r[273]||r[272:257]!==16'h7||r[255:0]!=={8{32'h40400000}}||rv)$fatal(1,"native row cache failed");
  send(1,27'd31,256'h8765,32'h0000ffff,16'h5);
  wait(wv);@(negedge clk);if(wa!==14'd15||wm!==16'h0f00||wd!=={256'h8765,256'd0})$fatal(1,"write mapping");wr=1;
  @(negedge clk);wr=0;if(r[273])$fatal(1,"write retired at accept before real VM commit");
  repeat(8)begin @(negedge clk);if(r[273])$fatal(1,"write retired before real VM commit");end
  rc=1;@(negedge clk);rc=0;if(!r[273]||!r[256]||r[272:257]!==16'h5)$fatal(1,"commit response");
  @(negedge clk);if(f)$fatal(1,"unexpected fault");
  send(1,27'd1,0,32'h1,16'h6);@(negedge clk);if(!f)$fatal(1,"partial byte mask accepted");
  $display("S81_HCX_VM_BRIDGE PASS four outstanding, stalls, halfrows, commit, invalid-mask cycle=%0d",cycle);$finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
