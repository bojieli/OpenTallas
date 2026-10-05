`timescale 1ps/1fs
// Minimal actual command processor + CDC owner handshake; no SM, PHY or token claim.
module tb_ds_hbm_pcwb_owner_join;
reg clk=0,svc=0,por=0; always #416 clk=~clk; always #512 svc=~svc;
reg cmd_we=0; reg [1:0] cmd_addr=0; reg [63:0] cmd_data=0;
reg db_v=0,cpl_r=0,sm_done=0; reg [31:0] job=32'hfedcba98;
reg [3:0] gen=15; reg [19:0] pos=20'hfffff;
wire cp_ready,cpl_v;wire [31:0] heldjob;wire[3:0] heldgen;wire[19:0] heldpos;
wire [16:0] tok;wire[3:0] status;wire[31:0] cycles;
wire [1:0] permit,ov,af;reg[1:0] accept=0,owned=0,fenced=0,rowacc=0;
reg [13:0] rowdie=0;reg[39:0] rowpos={20'hfffff,20'hfffff};
wire[63:0] oj;wire[7:0] og;wire[39:0] op;
wire issuer_v=db_v && (&permit);
ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(1),.NCMD(4)) cp(
 .clk(clk),.rst_n(por),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_data),
 .db_v(issuer_v),.db_rdy(cp_ready),.db_token(17'h1ffff),.db_pos(pos),.db_job(job),.db_generation(gen),
 .cpl_job(heldjob),.cpl_generation(heldgen),.cpl_position(heldpos),
 .sm_done(sm_done),.sm_fault(1'b0),.res_v(1'b0),.res_data(32'b0),
 .cpl_v(cpl_v),.cpl_rdy(cpl_r),.cpl_token(tok),.cpl_status(status),.cpl_cycles(cycles));
wire refready,refv;wire[31:0] refjob,refcycles;wire[3:0] refgen,refstatus;
wire[19:0] refpos;wire[16:0] reftok;
ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(1),.NCMD(4)) reference_cp(
 .clk(clk),.rst_n(por),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_data),
 .db_v(issuer_v),.db_rdy(refready),.db_token(17'h1ffff),.db_pos(pos),.db_job(job),.db_generation(gen),
 .cpl_job(refjob),.cpl_generation(refgen),.cpl_position(refpos),
 .sm_done(sm_done),.sm_fault(1'b0),.res_v(1'b0),.res_data(32'b0),
 .cpl_v(refv),.cpl_rdy(cpl_r),.cpl_token(reftok),.cpl_status(refstatus),.cpl_cycles(refcycles));
genvar s;
generate for(s=0;s<2;s=s+1)begin:st
 ot_ds_hbm_pcwb_owner_join #(.ENABLE(1),.DIE(95),.STACK(s)) j(
 .clk_sm(clk),.rst_sm_n(por),.service_clk(svc),.por_n(por),
 .db_v(issuer_v),.db_rdy(cp_ready),.issuer_done(cpl_v),.db_rdy_eff(permit[s]),
 .cpl_job(heldjob),.cpl_generation(heldgen),.cpl_position(heldpos),
 .owner_v(ov[s]),.owner_r(accept[s]),.owner_held(owned[s]),.owner_fenced(fenced[s]),
 .o_job(oj[s*32+:32]),.o_gen(og[s*4+:4]),.o_pos(op[s*20+:20]),
 .row_acc(rowacc[s]),.row_die(rowdie[s*7+:7]),.row_pos(rowpos[s*20+:20]),.assoc_fault(af[s]));
end endgenerate
integer accs=0,comps=0;
always @(posedge clk) if(por)begin
 if(issuer_v&&cp_ready) accs=accs+1;
 if(cpl_v&&cpl_r) comps=comps+1;
 #1;
 if({cpl_v,heldjob,heldgen,heldpos,tok,status,cycles} !== {refv,refjob,refgen,refpos,reftok,refstatus,refcycles})
  $fatal(1,"actual CP completion differs from original source");
end
// Independent immediate-ready probe checks the acc_q-to-toggle edge without CP busy masking it.
reg fastv=0;wire fready;integer fastacc=0;
ot_ds_hbm_pcwb_owner_join #(.ENABLE(1)) gap(
 .clk_sm(clk),.rst_sm_n(por),.service_clk(svc),.por_n(por),.db_v(fastv),.db_rdy(1'b1),.issuer_done(1'b0),.db_rdy_eff(fready),
 .cpl_job(heldjob),.cpl_generation(heldgen),.cpl_position(heldpos),
 .owner_r(1'b0),.owner_held(1'b0),.owner_fenced(1'b0),.row_acc(1'b0),.row_die(7'b0),.row_pos(20'b0));
always @(posedge clk)if(por&&fastv&&fready)fastacc=fastacc+1;
initial begin
 #2000;por=1;
 @(negedge clk);cmd_we=1;cmd_data=64'h1000100000000000;
 @(negedge clk);cmd_addr=1;cmd_data=64'h2000000000000000;
 @(negedge clk);cmd_we=0;db_v=1;fastv=1;
 wait(accs==1);@(negedge clk);db_v=0;
 wait(&ov);#1;
 if(oj!={job,job}||og!={gen,gen}||op!={pos,pos})$fatal(1,"native frame narrowed or sampled old");
 repeat(3)@(negedge svc);
 if(ov!==2'b11)$fatal(1,"owner valid not held under stall");
 if(fastacc!=1)$fatal(1,"accept-to-toggle gap accepted duplicate");
 accept=3;@(negedge svc);accept=0;owned=3;
 // Initial empty fence is not producer completion: hold all stacks fenced early.
 fenced=3;db_v=1;repeat(8)@(negedge clk);
 if(accs!=1 || (&permit))$fatal(1,"empty fence before actual CP completion released step");
 fenced=0;db_v=0;sm_done=1;
 wait(cpl_v);@(negedge clk);cpl_r=1;
 @(negedge clk);cpl_r=0;db_v=1;
 repeat(5)@(negedge clk);
 if(accs!=1)$fatal(1,"completion incorrectly released owner debt");
 fenced=1;repeat(8)@(negedge clk);
 if(accs!=1)$fatal(1,"one released stack admitted next doorbell");
 fenced=3;wait(accs==2);@(negedge clk);db_v=0;
 if(comps!=1)$fatal(1,"original completion missing");
 // Wrong position and wrong die are separately attributed and sticky; no further acceptance.
 rowdie={7'd94,7'd95};rowpos={20'hfffff,20'hffffe};
 @(negedge svc);rowacc=3;@(negedge svc);rowacc=0;
 if(af!==2'b11)$fatal(1,"wrong pos or wrong die not rejected");
 repeat(3)@(negedge clk);
 if((|permit)||(|ov))$fatal(1,"association fault did not fail closed");
 $display("PASS_DS20_ACTUAL_CP_OWNER_JOIN: fullwidth frame; early-empty fence; stalls; all-stack release; identical CP completion; wrongpos/wrongdie; immediate-gap");
 $finish;
end
endmodule
