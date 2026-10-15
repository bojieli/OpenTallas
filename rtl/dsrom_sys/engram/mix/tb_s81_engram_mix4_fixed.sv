`timescale 1ns/1ps
// Calendar bench: the ACTUAL fixed issuer (ot_s81_fixed_issue, OP_BASE 2, engine 10) drives the ACTUAL
// dsfd_engram_mix4_c on the layer bench's exact startup edges (issuer reset release on the negedge of
// stream cycle 1000, eight PW boot rows from 1010, job_v at 1250) against the component's declared
// 20R/4W VM boundary (registered 1-cycle row port, the same latency tb_s81_die_layer uses).
// It measures the command-pin -> done-pin latency in issuer age units and checks the compiled done row
// fires exactly on the completion (issuer fault code 8 = done absent/late, 6 = early). Exact BF16 output
// of all four copies is checked as in the component bench. Descriptor row = the compiled arg (+desc=).
module tb_s81_engram_mix4_fixed #(parameter MUT=0);
 reg clk=0;always #1 clk=~clk;
 integer cyc=0;always @(posedge clk)cyc<=cyc+1;
 reg [63:0] cfg[0:0];reg rst=0;wire [8:0] done;wire [1:0] st;wire [19:0] rq;wire [279:0] addr;
 reg [19:0] rv=0;reg [10239:0] rd=0;wire [3:0] wv;wire [55:0] wa;wire [63:0] mask;wire [2047:0] wd;
 reg is_rst_n=0;initial begin while(cyc<1000)@(negedge clk);is_rst_n=1;end
 reg pv=0;reg[6:0]pa=0;reg[27:0]pd=0;reg[34:0]pm[0:7];
 wire[12:0]cv;wire[1091:0]cd;wire is_fault;wire[3:0]is_code;wire[1:0]phase;
 ot_s81_fixed_issue #(.NOPS(2),.NENG(13),.STAGE(0),.OP_BASE(2),.ENG_PRESENT(13'h400)) iss(
  .clk(clk),.rst_n(is_rst_n),.pw_v(pv),.pw_a(pa),.pw_d(pd),.prog_len(8'd2),
  .job_v(cyc==1250),.job_user(10'd0),.job_pos(21'd0),.job_tok(21'd1000),
  .job_rdy(),.busy(),.job_done(),.job_kdone(),.done_slot(),.kit_tok(),.cmd_v(cv),.cmd_d(cd),
  .engine_available({2'b0,st[1],10'b0}),.dn_v({2'b0,done[8],10'b0}),.dn_tag({16'b0,done[7:0],80'b0}),
  .fault(is_fault),.fault_code(is_code),.st_jobs(),.st_cmds(),.phase(phase));
 dsfd_engram_mix4_c #(.MUT(MUT)) dut({133{clk}},rst,{cv[10],cd[840+:84]},done,st,1'b1,rq,addr,rv,rd,wv,wa,mask,wd);
 reg [1023:0] hm[0:639],km[0:639],wm[0:639],vm[0:159],ym[0:639];reg [511:0] mem[0:16383];
 string dir;integer i,j,l,m,bad=0,writes=0,reads=0,desc=11880;
 integer cmd_cyc=-1,done_cyc=-1,job_age0=-1,fault_cyc=-1,fault_code=0,mix_fault_cyc=-1;
 always @(posedge clk)begin
  rv<=rq;
  for(l=0;l<20;l=l+1)if(rq[l])begin rd[512*l+:512]<=mem[addr[14*l+:14]];reads=reads+1;end
  for(l=0;l<4;l=l+1)if(wv[l])begin
   if(mask[16*l+:16]!=16'hffff)$fatal(1,"bad write mask");
   mem[wa[14*l+:14]]<=wd[512*l+:512];writes=writes+1;
  end
  if(cv[10]&&cmd_cyc<0)cmd_cyc=cyc;
  if(done[8]&&done_cyc<0)done_cyc=cyc;
  if(iss.active[0]&&iss.age[0]==0)job_age0=cyc;
  if(is_fault&&fault_cyc<0)begin fault_cyc=cyc;fault_code=is_code;end
  if(st[0]&&mix_fault_cyc<0)begin mix_fault_cyc=cyc;$display("MIX endpoint fault cyc=%0d cluster_faults=%b ep=%b top=%b",cyc,dut.c_fault_q,dut.epf,dut.fault);end
 end
 initial begin
  if(!$value$plusargs("dir=%s",dir))$fatal(1,"dir required");
  if($value$plusargs("desc=%d",desc));
  $readmemh({dir,"/cfg.mem"},cfg);$readmemh({dir,"/h.mem"},hm);$readmemh({dir,"/k.mem"},km);$readmemh({dir,"/w.mem"},wm);$readmemh({dir,"/v.mem"},vm);$readmemh({dir,"/y.mem"},ym);
  $readmemh({dir,"/mix_program.mem"},pm);
  for(i=0;i<640;i=i+1)begin
   for(j=0;j<32;j=j+1)mem[256+i][16*j+:16]=hm[i][32*j+16+:16];
   mem[2048+2*i]=km[i][0+:512];mem[2049+2*i]=km[i][512+:512];
   mem[4096+2*i]=wm[i][0+:512];mem[4097+2*i]=wm[i][512+:512];
  end
  for(i=0;i<160;i=i+1)begin mem[6144+2*i]=vm[i][0+:512];mem[6145+2*i]=vm[i][512+:512];end
  mem[desc]=0;mem[desc][0+:32]=256;mem[desc][32+:32]=2048;mem[desc][64+:32]=4096;mem[desc][96+:32]=6144;mem[desc][128+:32]=256;
  mem[desc][160+:32]=cfg[0][0+:32];mem[desc][192+:32]=cfg[0][32+:32];
  repeat(5)@(negedge clk);rst=1;
  while(cyc<1010)@(negedge clk);
  for(i=0;i<8;i=i+1)begin pv=1;pa=pm[i][34:28];pd=pm[i][27:0];@(negedge clk);pv=0;@(negedge clk);end
  while(cyc<1250+4000)@(negedge clk);
  for(i=0;i<640;i=i+1)for(j=0;j<32;j=j+1)if(mem[256+i][16*j+:16]!==ym[i][32*j+16+:16])bad=bad+1;
  $display("MIX4_FIXED cmd_pin_cycle=%0d done_pin_cycle=%0d cmd_to_done=%0d job_age0_cycle=%0d done_age=%0d compiled_done=%0d issuer_fault=%0d code=%0d at %0d mix_fault=%0d writes=%0d reads=%0d bad_words=%0d",
   cmd_cyc,done_cyc,done_cyc-cmd_cyc,job_age0,done_cyc-job_age0,iss.mem[0][75:52],is_fault,fault_code,fault_cyc,st[0],writes,reads,bad);
  if(is_fault||st[0]||bad||writes!=640||reads!=4161||done_cyc<0)$fatal(1,"MIX4_FIXED FAIL");
  $display("MIX4_FIXED PASS");$finish;
 end
endmodule
