`timescale 1ns/1ps
module wfc_enclosing_case #(parameter STRUCTURAL=0,NEGATIVE=0)(output reg finished=0);
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,in_valid=0,in_last=0,out_ready=0;
 reg [511:0]in_data=0;
 wire in_ready,out_valid,out_last;wire [511:0]out_data;
 wire pr_re;wire[9:0]pr_user;wire[20:0]pr_pos;wire[3:0]pr_blk;
 wire bl_rx_ready,bl_tx_valid,bl_tx_last;wire[511:0]bl_tx_data;
 wire tok_valid;wire[9:0]tok_user,users_done;wire[20:0]tok_pos,tok_id;
 reg rcfg_we=0;reg[7:0]rcfg_dest=0;reg[2:0]rcfg_mask=0;
 reg [15:0]stage_epoch=9;reg[13:0]stage_entry=5;
 wire stage_request_v;reg stage_request_ready=0;
 wire [46:0]stage_request_identity;wire[20:0]stage_request_token;wire[13:0]stage_request_entry;
 reg whole_stage_v=0;reg[46:0]whole_stage_identity=0;
 reg[20:0]whole_stage_token=17;reg[31:0]whole_stage_value=32'h3f800000;
 wire whole_stage_accepted;
 reg context_restored=0,native_idle=1,native_fragment_done=0;
 reg c8_write_quiet=0;
 reg[3:0]xb_we4=0;reg[59:0]xb_waddr4=0;reg[2047:0]xb_wdata4=0;
 reg xb_re=0;reg[14:0]xb_raddr=0;wire[511:0]xb_rq;
 wire context_v;wire[46:0]context_identity;wire[20:0]context_token;wire[13:0]context_entry;
 wire native_start;wire[20:0]native_token,native_pos;wire[13:0]native_entry;wire[9:0]native_user;
 wire[46:0]native_identity;wire[20:0]captured_token,captured_pos;wire[13:0]captured_pc;
 wire c8_retire_v;wire[46:0]c8_retire_identity;wire busy,fault;
 ot_dsrom_wfc_enclosing_stage #(.ENABLE(1),.STRUCTURAL(STRUCTURAL))dut(
 .clk(clk),.rst_n(rst_n),.cfg_users(10'd866),.cfg_prompt_len(21'd3),.cfg_gen_len(21'd30),
 .pr_q(21'd0),.pr_qk(1'b0),.c8_write_quarantine(1'b0),.c8_write_fault(1'b0),.coll_busy(1'b0),
 .bl_rx_valid(1'b0),.bl_rx_last(1'b0),.bl_rx_data(512'd0),.bl_tx_ready(1'b1),.*);
 integer cycle=0,reqs=0,acks=0,starts=0,retired=0,flits=0,writes=0;
 integer wfc_start_edge=-1,request_edge=-1,capture_edge=-1;
 reg holding=0;reg[81:0]held_request;reg[46:0]saved_owner=0;
 always @(posedge clk)begin
   cycle=cycle+1;out_ready<=cycle%7!=0;
   if(dut.g_stage.core_start)wfc_start_edge=cycle;
   if(stage_request_v&&!stage_request_ready)begin
     if(holding&&{stage_request_identity,stage_request_token,stage_request_entry}!==held_request)$fatal(1,"held stage offer changed");
     holding=1;held_request={stage_request_identity,stage_request_token,stage_request_entry};
   end
   if(stage_request_v&&stage_request_ready)begin
     reqs=reqs+1;holding=0;saved_owner=stage_request_identity;request_edge=cycle;
     if(stage_request_identity!=={stage_epoch,10'd865,21'(reqs-1)}||stage_request_entry!=stage_entry)
       $fatal(1,"actual request owner mismatch mode%0d",STRUCTURAL);
   end
   if(native_start)begin
     starts=starts+1;capture_edge=cycle;
     if(!native_idle||native_user!=865||native_token!=(starts==1?3:5)||native_pos!=starts-1||native_entry!=stage_entry)
       $fatal(1,"actual C8/core capture wrong current user/tuple");
     if(capture_edge-wfc_start_edge<3)$fatal(1,"enclosing minimum launch calendar violated");
     $display("ENCLOSING_CAPTURE mode=%0d job=%0d actual_user=%0d WFC_to_native_edges=%0d request_wait_edges=%0d",STRUCTURAL,starts,native_user,capture_edge-wfc_start_edge,request_edge-wfc_start_edge);
   end
   if(c8_retire_v)begin retired=retired+1;if(c8_retire_identity!=saved_owner)$fatal(1,"C8 wrong retirement identity");end
   if(whole_stage_accepted)begin
     acks=acks+1;
     if(!whole_stage_v||whole_stage_identity!=saved_owner)$fatal(1,"whole producer ACK without actual held job");
     whole_stage_v<=0;
   end
   if(rst_n&&dut.g_stage.vm_we)begin
     if(dut.g_stage.vm_waddr!=writes||dut.g_stage.vm_wdata!=={16{32'(writes+1)}})$fatal(1,"native VM write wrong fullword");
     writes=writes+1;
   end
   if(out_valid&&out_ready)begin
     if(flits==0)begin
       if(out_data[19:16]!=1||out_data[31:24]!=46||out_data[39:32]!=97||out_data[151+:2]!=3||out_data[61+:21]!=17||out_data[82+:32]!=32'h3f800000||out_last)$fatal(1,"held whole-stage header mismatch");
     end else if(out_data!=={16{32'(flits<=41?flits:1000+flits-1)}}||out_last!=(flits==46))
       $fatal(1,"full VM payload mismatch word%0d got%h",flits,out_data);
     flits=flits+1;
   end
 end
 task automatic beat(input[511:0]data,input last);
   begin
     @(negedge clk);in_valid=1;in_data=data;in_last=last;
     @(posedge clk);while(!in_ready)@(posedge clk);
     @(negedge clk);in_valid=0;
   end
 endtask
 task automatic send_job(input integer pos,input integer token);
   reg[511:0]header;
   begin
     header=0;header[19:16]=1;header[31:24]=41;header[39:32]=97;header[151+:2]=3;
     header[40+:21]=pos;header[114+:21]=token;
     beat(header,0);
     for(integer w=1;w<=41;w=w+1)beat({16{32'(w)}},w==41);
   end
 endtask
 initial begin
   // Preload only actual source words required by the46-word TX path, plus
   // highest full-depth word. No zero-fill or reduced memory depth.
   for(integer w=0;w<46;w=w+1)begin
     @(negedge clk);xb_we4=1;xb_waddr4[14:0]=w;xb_wdata4[511:0]={16{32'(1000+w)}};
   end
   @(negedge clk);xb_waddr4[14:0]=32767;xb_wdata4[511:0]={16{32'habcddcba}};
   @(negedge clk);xb_we4=0;xb_re=1;xb_raddr=32767;
   @(negedge clk);if(xb_rq!=={16{32'habcddcba}})$fatal(1,"full-depth VM highword/lane mismatch");xb_re=0;
   rst_n=1;repeat(6)@(negedge clk);
   rcfg_we=1;rcfg_dest=0;rcfg_mask=1;
   @(negedge clk);rcfg_dest=1;rcfg_mask=2;
   @(negedge clk);rcfg_we=0;c8_write_quiet=1;
   send_job(0,3);
   wait(stage_request_v);repeat(8)@(negedge clk);
   if(reqs!=0||starts!=0||acks!=0)$fatal(1,"producer stall lost finite request");
   stage_request_ready=1;wait(reqs==1);repeat(6)@(negedge clk);
   if(starts!=0||!context_v)$fatal(1,"actual C8 restore fence bypassed");context_restored=1;
   wait(starts==1);@(negedge clk);
   if(captured_token!=3||captured_pos!=0||captured_pc!=5)$fatal(1,"literal native accepted-start capture failed");
   native_idle=0;repeat(4)@(negedge clk);native_fragment_done=1;native_idle=1;c8_write_quiet=0;
   repeat(7)@(negedge clk);if(retired||acks||flits)$fatal(1,"C8/write quiet/whole stage authority bypass");
   c8_write_quiet=1;wait(retired==1);repeat(5)@(negedge clk);
   if(acks||flits||!busy)$fatal(1,"fragment/C8 retirement substituted for whole-stage completion");
   whole_stage_identity=saved_owner;whole_stage_v=1;
   if(NEGATIVE)begin
     wait(dut.g_stage.u_boundary.u_ctrl.g_control_completion.v===1);
     @(negedge clk);whole_stage_identity=saved_owner^47'd1;
     #0.01;if(whole_stage_accepted)$fatal(1,"wrong identity received same-edge retirement ACK");
     repeat(3)@(negedge clk);
     if(!fault||!busy||acks||whole_stage_accepted||stage_request_identity!=saved_owner)
       $fatal(1,"wrong identity after qualified capture erased owner/retired job");
     $display("ENCLOSING_WRONG_OWNER full866 after_actual_completion_capture false_ACK=0 owned_job_retained=1 quarantine=1 PASS");
     finished=1;
   end else begin
   wait(acks==1);wait(flits==47);repeat(8)@(negedge clk);
   if(fault||busy||writes!=41)$fatal(1,"real enclosing nominal transfer failed");
   $display("ENCLOSING_NOMINAL mode=%0d MAXU866 fullVM32768x512 user865 request_stall8 restore_stall6 actual_C8_retire1 whole_ACK1 exact_writes41 exact_flits47 PASS",STRUCTURAL);
   // A second accepted owned job must survive warm reset as poisoned debt.
   stage_epoch=10;stage_entry=6;native_fragment_done=0;writes=0;
   send_job(1,5);wait(reqs==2);wait(starts==2);@(negedge clk);rst_n=0;
   repeat(3)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
   if(!fault||!busy||acks!=1||whole_stage_accepted||stage_request_identity!=saved_owner)
     $fatal(1,"accepted whole job erased/reused on warm reset");
   xb_re=1;xb_raddr=32767;@(negedge clk);
   if(xb_rq!=={16{32'habcddcba}})$fatal(1,"warm reset erased finite mutable VM");xb_re=0;
   $display("ENCLOSING_WARM mode=%0d second_owned_job_retained=1 quarantine=1 false_ACK=0 fullVM_highword_preserved=1 PASS",STRUCTURAL);
   finished=1;
   end
 end
endmodule
module tb_wfc_enclosing_stage;
 wire a,b;
 wfc_enclosing_case #(.STRUCTURAL(0))original(a);
 wfc_enclosing_case #(.STRUCTURAL(1))changed(b);
 initial begin wait(a&&b);$display("ENCLOSING_MINIMUM_MECHANISM PASS no_canonical_producer_or_SSFF_claim");$finish;end
endmodule

module tb_wfc_enclosing_wrong_owner;
 wire a;wfc_enclosing_case #(.STRUCTURAL(1),.NEGATIVE(1))bad_owner(a);
 initial begin wait(a);$display("ENCLOSING_WRONG_OWNER_ALL PASS");$finish;end
endmodule
