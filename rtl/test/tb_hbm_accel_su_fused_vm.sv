`timescale 1ns/1fs
// One source-bound actual saved command through real VM reads/writes.
module tb_hbm_accel_su_fused_vm #(
 parameter integer KIND=1,N=256,D=1280,RD=0,PUBLISH_QUANT=0,ROUTED=1,
 parameter integer MEM_WORDS=4192,CR_WORDS=65536,CHECK_WORDS=1280
);
 reg clk=0;always #0.416666667 clk=~clk;
 reg rst_n=0,cmd_valid=0;
 reg [31:0] vm[0:MEM_WORDS-1],cr[0:CR_WORDS-1],expected[0:CHECK_WORDS-1];
 reg [31:0] cmd[0:5],cfg[0:31];
 wire cmd_ready,busy,done,fault;
 wire [4*N*24-1:0] ra;wire [4*N-1:0] re;wire [8*N-1:0] rs;
 reg [4*N*32-1:0] rq=0;
 wire [N-1:0] we;wire [N*24-1:0] wa;wire [N*32-1:0] wd;
 wire qv;wire [7:0] qi;wire [N*8-1:0] qc;
 wire [(N/32)*10-1:0] qe;wire [N*16-1:0] qy;
 wire [31:0] completion;wire [15:0] need;
 // Real exclusive VM destination reservation, released after each accepted
 // vector write. No output buffer preload, and no success without all writes.
 reg owns=0;integer debt=0,cyc=0,first=-1,last=-1,reads=0,writes=0,checked=0,errors=0;
 wire landing_reserved=(owns && debt>0)||(!busy && !owns);
 ot_hbm_accel_su_fused_vm #(.ENABLE(1),.KIND(KIND),.N(N),.D(D),.RD(RD),
   .PUBLISH_QUANT(PUBLISH_QUANT),.ROUTED(ROUTED)) dut
  (.clk(clk),.rst_n(rst_n),.cmd_valid(cmd_valid),.source_ready(1'b1),
   .landing_reserved(landing_reserved),.cmd_ready(cmd_ready),.busy(busy),.done(done),.fault(fault),
   .job_id(cmd[5]),.xbase(cmd[0][23:0]),.ubase(cmd[1][23:0]),.wbase(cmd[2][23:0]),
   .ybase(cmd[3][23:0]),.gain_base(cmd[4][23:0]),
   .comb({cfg[15],cfg[14],cfg[13],cfg[12],cfg[11],cfg[10],cfg[9],cfg[8],cfg[7],cfg[6],cfg[5],cfg[4],cfg[3],cfg[2],cfg[1],cfg[0]}),
   .post_pre({cfg[19],cfg[18],cfg[17],cfg[16]}),.n_f(cfg[20]),.eps(cfg[21]),.lim(cfg[22]),
   .cos_t({((RD?RD/2:1)*32){1'b0}}),.sin_t({((RD?RD/2:1)*32){1'b0}}),
   .rd_addr(ra),.rd_re(re),.rd_src(rs),.rd_q(rq),.vm_we(we),.vm_waddr(wa),.vm_wdata(wd),
   .q_valid(qv),.q_index(qi),.q_codes(qc),.q_exp(qe),.q_bf16(qy),
   .completion_id(completion),.reserve_events(need));
 integer l,a;
 initial begin
  $readmemh("vm.mem",vm);$readmemh("cr_lo.mem",cr);
  $readmemh("cmd.mem",cmd);$readmemh("cfg.mem",cfg);$readmemh("expected.mem",expected);
  repeat(3) @(negedge clk);rst_n=1;cmd_valid=1;
  @(negedge clk);cmd_valid=0;
 end
 always @(posedge clk) begin
  cyc<=cyc+1;
  if(cmd_valid && cmd_ready) begin
   if(owns || busy || need==0) $fatal(1,"invalid real destination reservation");
   owns<=1;debt<=need;first<=cyc;
   $display("VM_EVENT reserve cycle=%0d id=%0d events=%0d",cyc,cmd[5],need);
  end
  for(l=0;l<4*N;l=l+1) begin
   rq[l*32+:32]<=0;
   if(re[l]) begin
    a=ra[l*24+:24];
    if(rs[l*2+:2]==1) begin
     if(a>=CR_WORDS) $fatal(1,"actual CR bound");rq[l*32+:32]<=cr[a];
    end else if(rs[l*2+:2]==0) begin
     if(a>=MEM_WORDS) $fatal(1,"actual VM read bound");rq[l*32+:32]<=vm[a];
    end else $fatal(1,"unbound actual source port");
    reads=reads+1;
   end
  end
  if(|re) $display("VM_EVENT read cycle=%0d",cyc);
  if(|we) begin
   if(!owns || debt<=0) $fatal(1,"write without real destination lease");
   debt<=debt-1;last<=cyc;
   for(l=0;l<N;l=l+1) if(we[l]) begin
    a=wa[l*24+:24];if(a>=MEM_WORDS) $fatal(1,"actual VM write bound");
    vm[a]<=wd[l*32+:32];writes=writes+1;
   end
   $display("VM_EVENT write cycle=%0d debt=%0d",cyc,debt);
  end
  if(qv) $fatal(1,"downstream quantisation must retain actual source grouping");
 end
 always @(negedge clk) begin
  if(fault) $fatal(1,"VM adapter fault; no completion credit");
  if(done) begin
   if(debt!=0 || completion!=cmd[5] || !owns) $fatal(1,"completion without actual drained writes");
   for(l=0;l<CHECK_WORDS;l=l+1) begin
    checked=checked+1;
    if(vm[cmd[3]+l]!==expected[l]) begin
     if(errors<5) $display("VM_MISMATCH word=%0d got=%08x want=%08x",l,vm[cmd[3]+l],expected[l]);
     errors=errors+1;
    end
   end
   owns=0;
   $display("VM_END first=%0d last_write=%0d completion=%0d reads=%0d writes=%0d checked=%0d errors=%0d debt=%0d",first,last,cyc,reads,writes,checked,errors,debt);
   if(errors!=0) $fatal(1,"actual cached VM mismatch");
   $display("PASS");$finish;
  end
 end
endmodule
