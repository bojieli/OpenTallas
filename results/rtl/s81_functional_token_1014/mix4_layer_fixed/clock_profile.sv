`timescale 1ns/1ps
module profile;
 reg clk=0;always #1 clk=~clk;reg rst=0;integer cyc=0;always @(posedge clk)cyc<=cyc+1;
 reg pv=0;reg[6:0]pa=0;reg[27:0]pd=0;reg[34:0]m[0:7];
 wire[12:0]cv;wire[1091:0]cd;wire fault;wire[3:0]code;wire[1:0]phase;
 ot_s81_fixed_issue #(.NOPS(2),.STAGE(0),.OP_BASE(2),.ENG_PRESENT(13'h400))dut(
 .clk(clk),.rst_n(rst&&cyc>=1000),.pw_v(pv),.pw_a(pa),.pw_d(pd),.prog_len(8'd2),
 .job_v(cyc==1250),.job_user(10'd0),.job_pos(21'd0),.job_tok(21'd1000),
 .job_rdy(),.busy(),.job_done(),.job_kdone(),.done_slot(),.kit_tok(),.cmd_v(cv),.cmd_d(cd),
 .engine_available(13'h400),.dn_v(13'd0),.dn_tag(104'd0),.fault(fault),.fault_code(code),.st_jobs(),.st_cmds(),.phase(phase));
 initial begin $readmemh("mix_program.mem",m);repeat(5)@(negedge clk);rst=1;
 while(cyc<1010)@(negedge clk);
 for(integer i=0;i<8;i++)begin pv=1;pa=m[i][34:28];pd=m[i][27:0];@(negedge clk);pv=0;@(negedge clk);end
 end
 always @(negedge clk)begin
 if(fault)$fatal(1,"clock/boot profile fault code%0d at%0d phase%0d",code,cyc,phase);
 if(cv[10])begin if(cd[840+:7]!=2)$fatal(1,"opidentity");$display("MIX_FIXED_CLOCK PASS cmd_negedge_cycle=%0d phase=%0d op2=1 landing_write_pin=1892 commit_bound=1903",cyc,phase);$finish;end
 if(cyc>2000)$fatal(1,"no launch");
 end
endmodule
