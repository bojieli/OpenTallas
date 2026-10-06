`timescale 1ns/1ps
// Full storage/ports, minimum SOURCE1 producer/prompt/END lifecycle.
module wfc_source_lifecycle_case #(parameter PIPE=0)(output reg finished=0);
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,in_valid=0,in_last=1,out_ready=0,core_done=0,pr_qk=0;
 reg [511:0]in_data=0,vm_rq=0;
 reg [20:0]pr_q=0,core_next_token=0;
 reg [31:0]core_next_val=0;
 wire in_ready,out_valid,out_last,core_start,core_busy,tok_valid,proto_fault,vm_we,vm_re,pr_re;
 wire [511:0]out_data,vm_wdata;
 wire [20:0]core_token,core_pos,pr_pos,tok_pos,tok_id;
 wire [9:0]core_user,pr_user,tok_user,users_done;
 wire [29:0]kv_base;wire [14:0]vm_waddr,vm_raddr;wire [3:0]pr_blk;
 wire wf_issue,wf_reject,wf_squash;
 function automatic [20:0]gold(input integer pos);gold=21'(1000+17*pos);endfunction
 ot_rom_pkg_ctrl_wfc #(.NW(21),.AW(30),.VWA(15),.KVW(32768),.WAVE(1),.WIN(6),.USER_W(10),.MAXU(866),.SOURCE(1),.XWORDS(41),.RXWORDS(41),.DECODED_READ(PIPE),.CONTROL_PIPE(PIPE),.QUEUE_SHIFT(PIPE),.HEADER_LOCAL(PIPE),.PREFIX_INC(PIPE),.FWD_TOKEN(1)) c
 (.clk(clk),.rst_n(rst_n),.cfg_users(10'd1),.cfg_prompt_len(21'd2),.cfg_gen_len(21'd2),.*);
 integer cycle=0,delay=0,payload=0,commits=0,prompts=0,starts=0,packets=0,accepted=0;
 integer pending=0;
 reg [20:0]positions[0:7];integer pw=0,prd=0;
 reg held=0;reg [512:0]held_tuple;
 reg prompt_pending=0,prompt_known=0,done_held=0;
 reg [20:0]prompt_token=0,done_token=0;reg [31:0]done_val=0;
 integer prompt_checks=0,done_held_checks=0;
 always @(posedge clk)begin
   cycle<=cycle+1;
   if(!rst_n)begin
     core_done<=0;delay<=0;in_valid<=0;payload=0;pw=0;prd=0;
     commits=0;prompts=0;starts=0;packets=0;accepted=0;held=0;prompt_pending=0;done_held=0;prompt_checks=0;done_held_checks=0;
   end else begin
     if(prompt_pending)begin
       if(pr_q!==prompt_token||pr_qk!==prompt_known)$fatal(1,"prompt tagged next-edge response mismatch");
       prompt_checks=prompt_checks+1;
     end
     prompt_pending=pr_re;prompt_known=pr_pos<2;prompt_token=gold(pr_pos);
     if(done_held&&!core_start)begin
       if(!core_done||core_next_token!==done_token||core_next_val!==done_val)$fatal(1,"level completion lifetime changed before next launch");
       done_held_checks=done_held_checks+1;
     end
     done_held=core_done&&!core_start;done_token=core_next_token;done_val=core_next_val;
     out_ready<=cycle%7!=0;
     if(vm_re)vm_rq<=512'(vm_raddr+17);
     if(pr_re)begin
       pr_qk<=pr_pos<2;pr_q<=gold(pr_pos);prompts=prompts+1;
       if(pr_user!=0)$fatal(1,"prompt wrong transaction user");
     end
     if(core_start)begin
       if(core_user!=0||core_token!=gold(core_pos))$fatal(1,"SOURCE1 actual prompt/caller launch tuple");
       core_done<=0;delay<=6;core_next_token<=gold(core_pos+1);core_next_val<=32'h3f800000;starts=starts+1;
     end else if(delay>1)delay<=delay-1;
     else if(delay==1)begin delay<=0;core_done<=1;end
     if(held&&(!in_valid||{in_data,in_last}!==held_tuple))$fatal(1,"SOURCE1 RESULT held tuple lost");
     held=in_valid&&!in_ready;held_tuple={in_data,in_last};
     if(out_valid&&out_ready)begin
       if(payload==0)begin
         if(out_data[19:16]!=1||out_data[31:24]!=41)$fatal(1,"SOURCE1 unexpected packet type/length");
         positions[pw%8]=out_data[40+:21];pw=pw+1;payload=41;packets=packets+1;
       end else payload=payload-1;
     end
     if(in_valid&&in_ready)begin in_valid<=0;prd=prd+1;accepted=accepted+1;end
     else if(!in_valid&&prd<pw&&payload==0)begin
       in_valid<=1;in_data<=0;in_data[19:16]<=2;
       in_data[40+:21]<=positions[prd%8];in_data[61+:21]<=gold(positions[prd%8]+1);
       in_data[82+:32]<=32'h3f800000;
     end
     if(tok_valid)begin
       if(tok_user!=0||tok_pos!=commits||tok_id!=gold(commits+1))$fatal(1,"SOURCE1 independent committed-token gold got user%0d pos%0d id%0d expected pos%0d id%0d",tok_user,tok_pos,tok_id,commits,gold(commits+1));
       commits=commits+1;
     end
     if(proto_fault)$fatal(1,"SOURCE1 lifecycle proto_fault");
   end
 end
 initial begin
   repeat(5)@(negedge clk);rst_n=1;
   wait(starts==1);
   if(PIPE)wait(c.g_control_completion.v===1);
   else wait(core_done===1);
   @(negedge clk);rst_n=0;
   repeat(3)@(negedge clk);
   if(c.job_done||out_valid||core_busy||tok_valid||users_done)$fatal(1,"SOURCE1 warm reset retained old debt");
   rst_n=1;
   wait(users_done==1);repeat(80)@(negedge clk);
   if(commits!=3||core_busy||out_valid||in_valid||tok_valid||users_done!=1||prompts<2||accepted<3)
     $fatal(1,"SOURCE1 END lifecycle failed commits%0d packets%0d accepted%0d",commits,packets,accepted);
   $display("SOURCE1_LIFECYCLE MAXU866 PIPE=%0d warm_reset_cancel=PASS prompt_reads=%0d launches=%0d packets=%0d accepted_results=%0d committed=%0d END_users_done=1 post_END_edges=80 prompt_tag_checks=%0d held_done_checks=%0d fault=0 PASS",PIPE,prompts,starts,packets,accepted,commits,prompt_checks,done_held_checks);
   finished=1;
 end
endmodule
module tb_wfc_source_lifecycle;
 wire a,b;
 wfc_source_lifecycle_case #(.PIPE(0))original(a);
 wfc_source_lifecycle_case #(.PIPE(1))changed(b);
 initial begin wait(a&&b);$display("SOURCE1_LIFECYCLE_ALL PASS");$finish;end
endmodule
