`timescale 1ps/1fs
module tb;
 reg clk=0; always #416.5 clk=~clk;
 reg rst_n=0,pw_v=0,job_v=0;
 reg [6:0] pw_a=0; reg [27:0] pw_d=0; reg [7:0] prog_len;
 wire ready,busy,job_done,job_kdone,done_slot,fault;
 wire [20:0] kit_tok; wire [4:0] cmd_v; wire [419:0] cmd_d;
 reg [4:0] dn_v=0; reg [39:0] dn_tag=0;
 wire [3:0] fault_code; wire [31:0] st_jobs,st_cmds; wire [1:0] phase;
 wire wc; wire [6:0] wa,ra0,ra1; wire [151:0] wd,wm;
 reg [151:0] mem[128],rd0,rd1;
 always @(posedge clk) begin
  if(wc) mem[wa] <= (mem[wa]&~wm)|(wd&wm);
  rd0 <= mem[ra0]; rd1 <= mem[ra1];
 end
 ot_dsdv_walk_issue #(.STAGE(0)) dut(.clk(clk),.rst_n(rst_n),.pw_v(pw_v),.pw_a(pw_a),.pw_d(pw_d),
  .prog_len(prog_len),.job_v(job_v),.job_user(10'd3),.job_pos(21'd29),.job_tok(21'd7),
  .job_rdy(ready),.busy(busy),.job_done(job_done),.job_kdone(job_kdone),.done_slot(done_slot),.kit_tok(kit_tok),
  .cmd_v(cmd_v),.cmd_d(cmd_d),.engine_available(5'b10111),.dn_v(dn_v),.dn_tag(dn_tag),
  .fault(fault),.fault_code(fault_code),.st_jobs(st_jobs),.st_cmds(st_cmds),.phase(phase),
  .cal_w_ce(wc),.cal_w_addr(wa),.cal_wd(wd),.cal_wm(wm),.cal_r_addr0(ra0),.cal_r_addr1(ra1),.cal_rd0(rd0),.cal_rd1(rd1));
 `include "sizes.svh"
 reg [35:0] pw[386]; reg [75:0] rows[128]; reg [7:0] oldtags[128];
 integer j,i,e,t,commands,total=0,oldtag_mut=0,kit_count,done_count;
 reg [4:0] want; reg [83:0] payload;
 string file;
 initial begin
  if($value$plusargs("OLDTAG=%d",oldtag_mut)) begin end
  for(j=0;j<8;j=j+1) begin
   rst_n=0;pw_v=0;job_v=0;dn_v=0;dn_tag=0;repeat(5) @(negedge clk);
   prog_len=SIZE[j];rst_n=1;repeat(3) @(negedge clk);
   file=$sformatf("job%0d.pw.memh",j);$readmemh(file,pw,0,3*SIZE[j]+1);
   file=$sformatf("job%0d.rows.memh",j);$readmemh(file,rows,0,SIZE[j]-1);
   file=$sformatf("job%0d.oldtags.memh",j);$readmemh(file,oldtags,0,SIZE[j]-1);
   for(i=0;i<3*SIZE[j]+2;i=i+1) begin
    pw_v=1;pw_a=pw[i][34:28];pw_d=pw[i][27:0];@(negedge clk);
   end
   pw_v=0;repeat(145) @(negedge clk);
   if(fault) $fatal(1,"seal fault page%0d code%0d",j,fault_code);
   while(phase!=3) @(negedge clk);
   job_v=1;@(negedge clk);job_v=0;
   commands=0;kit_count=0;done_count=0;
   for(t=0;t<=rows[SIZE[j]-1][51:28]+4;t=t+1) begin
    dn_v=0;dn_tag=0;
    for(i=0;i<SIZE[j];i=i+1) if(rows[i][27:24]<14 && rows[i][75:52]==t) begin
     e=rows[i][27:24];dn_v[e]=1;dn_tag[e*8+:8]=oldtag_mut?oldtags[i]:8'(i);
    end
    @(posedge clk);#0.001;
    want=0;
    for(i=0;i<SIZE[j];i=i+1) if(rows[i][27:24]<14 && rows[i][51:28]==t) begin
     e=rows[i][27:24];want[e]=1;
     payload={1'b0,10'd3,21'd29,21'd7,rows[i][23:0],7'(i)};
     if(cmd_d[e*84+:84]!==payload)$fatal(1,"command payload/tag page%0d row%0d",j,i);
     commands=commands+1;
    end
    if(cmd_v!==want)$fatal(1,"command date page%0d t%0d got%h want%h",j,t,cmd_v,want);
    if(job_kdone) begin
     if(t!=rows[SIZE[j]-2][51:28] || kit_tok!=7)$fatal(1,"KIT date/context page%0d",j);
     kit_count=kit_count+1;
    end
    if(job_done) begin
     if(t!=rows[SIZE[j]-1][51:28])$fatal(1,"END date page%0d",j);
     done_count=done_count+1;
    end
    if(fault)$fatal(1,"runtime page%0d t%0d code%0d",j,t,fault_code);
    @(negedge clk);
   end
   if(commands!=SIZE[j]-2 || kit_count!=1 || done_count!=1)$fatal(1,"incomplete page%0d",j);
   total=total+commands;$display("PAGE_PASS %0d commands%0d",j,commands);
  end
  $display("PASS actual8 pages commands%0d oldtag_mut%0d",total,oldtag_mut);$finish;
 end
 initial begin #100000000; $fatal(1,"watchdog"); end
endmodule
