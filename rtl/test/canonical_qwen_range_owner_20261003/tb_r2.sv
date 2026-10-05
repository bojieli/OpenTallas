`timescale 1ps/1ps
module tb;
reg clk;
reg por_n;
reg warm_reset;
reg session_begin_valid;
reg [63:0] session_begin_id;
reg allcopies_fenced;
reg reverse_fenced;
reg ingress_quiet;
wire session_begin_ready;
reg claim_valid;
reg claim_initial;
reg [238:0] claim_tuple;
reg [54:0] claim_owner;
wire claim_ready;
wire [2:0] claim_row;
reg bind_valid;
reg [238:0] bind_tuple;
reg [6:0] bind_mask;
wire bind_ready;
wire issued_input_live;
wire issued_input_started;
wire inputs_bound_valid;
wire [238:0] inputs_bound_tuple;
wire [6:0] inputs_bound_mask;
reg inputs_bound_ready;
reg go_accepted;
reg [238:0] go_tuple;
reg [10:0] next_source_PC;
wire row_barrier_ready;
wire [31:0] expected_output_page_mask;
reg page_ack_valid;
reg [54:0] page_ack_owner;
wire page_ack_ready;
wire rf_range_ack_valid;
wire [238:0] rf_range_ack_tuple;
wire [54:0] rf_range_ack_owner;
wire [31:0] rf_range_ack_page_mask;
reg rf_range_ack_ready;
reg producer_visible_valid;
reg [238:0] producer_visible_tuple;
wire producer_visible_ready;
reg publish_valid;
reg [238:0] publish_tuple;
reg [54:0] publish_owner;
reg [31:0] publish_page_mask;
wire publish_ready;
reg input_terminal_valid;
reg [238:0] input_terminal_tuple;
reg [6:0] input_terminal_mask;
wire input_terminal_ready;
reg input_reverse_valid;
reg [238:0] input_reverse_tuple;
reg [6:0] input_reverse_mask;
wire input_reverse_ready;
reg frame_retire_valid;
reg [238:0] frame_retire_tuple;
reg [54:0] frame_retire_owner;
wire frame_retire_ready;
reg source_native_retire_valid;
reg [63:0] source_native_retire_session;
reg [10:0] source_native_retire_version;
reg [54:0] source_native_retire_owner;
wire source_native_retire_ready;
reg query_valid;
reg query_write;
reg [238:0] query_tuple;
reg [10:0] query_version;
reg [8:0] query_slot;
wire query_ready;
wire query_result_valid;
reg query_result_ready;
wire [238:0] query_result_tuple;
wire [45:0] query_result_owner;
wire [8:0] query_result_slot;
wire source_owner_retained;
wire fault;
wire [6:0] live_rows;
wire [6:0] published_rows;
wire [6:0] consumer_rows;
wire [63:0] held_session;
ot_gpu_qwen_native_range_owner #(.ENABLE(1),.SM_INDEX(0)) dut(.*);
always #500 clk=~clk;
integer cycles=0;always @(posedge clk)cycles<=cycles+1;
task step;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
task must(input bit value,input [511:0] label);begin if(!value)$fatal(1,"FAIL %0s cycle%0d",label,cycles);end endtask
reg [238:0] A,B,L;reg [54:0] OA,OB,OL;reg [71:0] held_bad_word;
task reserve(input [238:0] id,input [54:0] own);begin
 claim_tuple=id;claim_owner=own;claim_valid=1;#1;must(claim_ready,"legal claim");step;claim_valid=0;#1;end endtask
task launch(input [238:0] id,input [6:0] mask);begin
 next_source_PC=id[174:164];bind_tuple=id;bind_mask=mask;bind_valid=1;#1;must(bind_ready,"captured canonical inputs");step;bind_valid=0;#1;
 must(inputs_bound_valid&&inputs_bound_tuple==id&&inputs_bound_mask==mask,"held inputs before GO");
 go_tuple=id;go_accepted=1;inputs_bound_ready=1;step;go_accepted=0;inputs_bound_ready=0;#1;end endtask
task finish_frame(input [238:0] id,input [54:0] own,input [6:0] mask);begin
 input_terminal_tuple=id;input_terminal_mask=mask;input_terminal_valid=1;#1;must(input_terminal_ready,"actual terminal");step;input_terminal_valid=0;
 frame_retire_valid=1;frame_retire_tuple=id;frame_retire_owner=own;#1;must(!frame_retire_ready,"reverse needed");frame_retire_valid=0;
 input_reverse_tuple=id;input_reverse_mask=mask;input_reverse_valid=1;#1;must(input_reverse_ready,"actual reverse");step;input_reverse_valid=0;
 frame_retire_valid=1;#1;must(frame_retire_ready,"frame retirement");step;frame_retire_valid=0;#1;end endtask
task pages_and_publish(input [238:0] id,input [54:0] own);integer k,n;begin
 n=id[9:0]-id[18:10];
 producer_visible_tuple=id;producer_visible_valid=1;#1;must(producer_visible_ready,"fullengine visible");step;producer_visible_valid=0;
 publish_tuple=id;publish_owner=own;publish_page_mask=32'hffffffff>>(32-n);publish_valid=1;#1;must(!publish_ready,"visible alone no publication");publish_valid=0;
 for(k=0;k<n;k=k+1)begin
  page_ack_owner={own[54:9],9'(id[18:10]+k)};page_ack_valid=1;#1;must(page_ack_ready,"page common-mirror ACK");step;page_ack_valid=0;#1;
  if(k<n-1)must(!rf_range_ack_valid,"no first-page shortcut");
 end
 must(rf_range_ack_valid&&rf_range_ack_tuple==id&&rf_range_ack_owner==own&&rf_range_ack_page_mask==publish_page_mask,"complete range aggregate");
 repeat(3)begin step;must(rf_range_ack_valid&&rf_range_ack_tuple==id,"range ACK held");end
 rf_range_ack_ready=1;step;rf_range_ack_ready=0;#1;
 publish_valid=1;#1;must(publish_ready,"real pages plus visibility");step;publish_valid=0;#1;end endtask
task read_source(input [238:0] id,input [10:0] ver,input [8:0] slot,input [45:0] own);begin
 query_tuple=id;query_version=ver;query_slot=slot;query_write=0;query_valid=1;#1;must(query_ready,"saved source input association");step;query_valid=0;
 repeat(4)step;#1;must(query_result_valid&&query_result_tuple==id&&query_result_owner==own&&source_owner_retained,"physical held query");
 repeat(2)step;must(query_result_valid,"held read result");query_result_ready=1;step;query_result_ready=0;#1;end endtask
initial begin
 clk=0;
 por_n=0;
 warm_reset=0;
 session_begin_valid=0;
 session_begin_id=0;
 allcopies_fenced=0;
 reverse_fenced=0;
 ingress_quiet=0;
 claim_valid=0;
 claim_initial=0;
 claim_tuple=0;
 claim_owner=0;
 bind_valid=0;
 bind_tuple=0;
 bind_mask=0;
 inputs_bound_ready=0;
 go_accepted=0;
 go_tuple=0;
 next_source_PC=0;
 page_ack_valid=0;
 page_ack_owner=0;
 rf_range_ack_ready=0;
 producer_visible_valid=0;
 producer_visible_tuple=0;
 publish_valid=0;
 publish_tuple=0;
 publish_owner=0;
 publish_page_mask=0;
 input_terminal_valid=0;
 input_terminal_tuple=0;
 input_terminal_mask=0;
 input_reverse_valid=0;
 input_reverse_tuple=0;
 input_reverse_mask=0;
 frame_retire_valid=0;
 frame_retire_tuple=0;
 frame_retire_owner=0;
 source_native_retire_valid=0;
 source_native_retire_session=0;
 source_native_retire_version=0;
 source_native_retire_owner=0;
 query_valid=0;
 query_write=0;
 query_tuple=0;
 query_version=0;
 query_slot=0;
 query_result_ready=0;
 A=239'h000000000000000080d0000000000000064000000000000000100c50a048;B=239'h000000000000000080e00000000000000650000000000000001010589025;L=239'h000000000000000080d0000000000000066000000000000000100c50a048;
 OA={46'd19,A[18:10]};OB={46'd20,B[18:10]};OL={46'd21,L[18:10]};
 por_n=1;#2;por_n=0;#5;por_n=1;step;
 session_begin_id=1;session_begin_valid=1;#1;must(!session_begin_ready,"positive fences needed");
 allcopies_fenced=1;reverse_fenced=1;ingress_quiet=1;#1;must(session_begin_ready,"cold source fences");step;session_begin_valid=0;
 reserve(A,OA);launch(A,0);pages_and_publish(A,OA);finish_frame(A,OA,0);
 must(live_rows[0]&&published_rows[0],"producer frame never clears lease");
 source_native_retire_session=1;source_native_retire_version=A[29:19];source_native_retire_owner=OA;source_native_retire_valid=1;#1;must(!source_native_retire_ready,"declared consumer still owed");source_native_retire_valid=0;
 next_source_PC=A[174:164]+2;#1;must(!row_barrier_ready,"expired lease blocks PC advance");next_source_PC=A[174:164]+1;
 reserve(B,OB);launch(B,7'b1);
 read_source(B,A[29:19],A[18:10],OA[54:9]);
 pages_and_publish(B,OB);finish_frame(B,OB,7'b1);
 source_native_retire_valid=1;#1;must(source_native_retire_ready,"last consumer actual terminal plus reverse");step;source_native_retire_valid=0;
 must(!live_rows[0]&&live_rows[1],"only named source lease retired");
 must(published_rows[1]&&!live_rows[0],"32 page source retained through consumer");
 // Single codeword CE stalls release until actual scrub; no repaired-data bypass.
 @(negedge clk);dut.rows[1].record.coded[0]=~dut.rows[1].record.coded[0];#10;
 must(!dut.all_clean&&!query_ready&&!claim_ready,"CE blocks all source actions");step;#1;must(dut.all_clean&&!fault,"verified next-edge scrub");
 // Double error preserves debt and refuses irreversible publication/retirement.
 @(negedge clk);dut.rows[1].record.coded[0]=~dut.rows[1].record.coded[0];dut.rows[1].record.coded[1]=~dut.rows[1].record.coded[1];#10;
 must(fault&&!source_native_retire_ready&&!frame_retire_ready,"double error fail closed");held_bad_word=dut.rows[1].record.coded[0 +:72];step;
 warm_reset=1;step;warm_reset=0;#1;must(fault&&!session_begin_ready&&dut.rows[1].record.coded[0 +:72]==held_bad_word,"warm reset retains actual coded debt");
 $display("PASS_RANGE_OWNER full239 source_input_rows frame_vs_lease bitmap32 held_query CE DUE reset cycles=%0d",cycles);$finish;
end
endmodule
