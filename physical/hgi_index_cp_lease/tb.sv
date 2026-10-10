`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,owner_valid=1,owner_fault=0;reg[72:0]owner_frame;
 reg cmd_v=0;wire cmd_r;reg[1818:0]cmd_rec;
 reg grant_v=0;wire grant_r;reg[72:0]grant_frame;reg[5:0]grant_layer;
 reg[6:0]grant_rank;reg[19:0]grant_pos;reg[14:0]grant_key_row0;
 reg[15:0]grant_row_end;reg[8:0]grant_blocks;
 reg key_visible=0,query_ACK=0,prefetch_accepted=0;
 reg[72:0]key_visible_frame,query_ACK_frame,prefetch_frame;
 wire prefetch_v,native_v,native_r;wire[1818:0]native_rec;
 wire[72:0]held_frame;wire[5:0]held_layer;wire[6:0]held_rank;
 wire[14:0]held_key_row0;wire[8:0]held_blocks;
 reg reads_drained=0,consumer_done=0,VM_ACKs_drained=0;reg[72:0]drain_frame;
 reg source_idle=1,selector_idle=1,release_r=0;wire release_v,retained,fault;
 ot_hgi_index_cp_lease #(.ENABLE(1)) dut(.*);
 // Real native controller acceptance: actor owns the record/lease until its
 // native consumer and independently framed service/VM drains finish.
 wire[89:0]fs;wire[344:0]kin;wire start_v,ctl_done,ctl_fault,ctl_retained;
 reg start_r=1,src_done=0;reg[1:0]event_idx=0;
 ot_hbm_native_index_control #(.ENABLE(1)) native(
  .clk(clk),.por_n(por_n),.owner_valid(owner_valid),.owner_fault(owner_fault),
  .allocation_granted(retained),.owner_frame(owner_frame),.allocation_frame(held_frame),
  .producer_published(1'b1),.producer_drained(1'b1),.selector_idle(1'b1),
  .command_v(native_v),.command_r(native_r),.command_frame(held_frame),
  .command_rank(held_rank),.command_ndie(native_rec[46:33]),.command_k(10'd4),
  .command_cand(1'b0),.command_keep(1'b0),.command_layer(held_layer),.command_key_row0(held_key_row0),
  .key_visible(1'b0),.key_visibility_frame(73'b0),.prefetch_v(),.prefetch_accepted(1'b0),
  .prefetch_accepted_frame(73'b0),.held_layer(),.held_key_row0(),.held_ndie(),
  .keep_v(1'b0),.keep_r(),.keep_frame(73'b0),.keep_quarter(2'b0),.keep_bitmap(342'b0),
  .fs(fs),.kin(kin),.source_start_v(start_v),.source_start_r(start_r),
  .held_frame(),.held_rank(),.source_done(src_done),.index_event(event_idx),
  .returns_drained(1'b1),.source_idle(1'b1),.retained(ctl_retained),.done(ctl_done),.fault(ctl_fault));
 integer cases=0,waits,i;
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task check(input bit ok,input[255:0]msg);begin if(!ok)begin $display("CP_INDEX_LEASE FAIL case=%0d %0s",cases,msg);$fatal(1);end end endtask
 task reset_case;begin
  por_n=0;cmd_v=0;grant_v=0;key_visible=0;query_ACK=0;prefetch_accepted=0;
  reads_drained=0;consumer_done=0;VM_ACKs_drained=0;release_r=0;source_idle=1;selector_idle=1;
  owner_valid=1;owner_fault=0;src_done=0;event_idx=0;
  owner_frame=(73'd9<<53)|73'h12345678;cmd_rec=0;cmd_rec[0]=1;
  cmd_rec[32:1]=20;cmd_rec[64:33]=64;cmd_rec[1810:1791]=9;cmd_rec[1818:1811]=103;
  grant_frame=owner_frame;grant_layer=20;grant_rank=7;grant_pos=9;
  grant_key_row0=100;grant_row_end=500;grant_blocks=2;
  key_visible_frame=owner_frame;query_ACK_frame=owner_frame;prefetch_frame=owner_frame;drain_frame=owner_frame;
  tick;por_n=1;tick;cases=cases+1;
 end endtask
 task command;begin check(cmd_r,"command ready");cmd_v=1;tick;cmd_v=0;check(retained&&!native_v,"retained before grant");end endtask
 task grant;begin grant_v=1;tick;grant_v=0;end endtask
 task visible;begin key_visible=1;query_ACK=1;tick;key_visible=0;query_ACK=0;end endtask
 task accepted;begin prefetch_accepted=1;tick;prefetch_accepted=0;check(native_v,"native launch after receipt");tick;check(!native_v,"single native acceptance");end endtask
 task expect_fault;begin tick;check(fault&&retained&&!native_v&&!release_v,"fault retains and blocks");end endtask
 initial begin
  reset_case;command;
  repeat(20)begin tick;check(grant_r&&!native_v&&!prefetch_v&&!release_v,"missing grant stalls");end
  grant;check(!fault&&held_layer==20&&held_rank==7&&held_key_row0==100,"grant metadata");
  repeat(8)begin tick;check(!native_v&&!prefetch_v,"missing visibility stalls");end
  visible;check(prefetch_v,"visible permits prefetch");
  repeat(8)begin tick;check(prefetch_v&&!native_v,"missing acceptance stalls");end
  accepted;
  waits=0;while(!start_v&&waits<40)begin tick;waits=waits+1;end check(start_v&&!ctl_fault,"native source start");tick;
  src_done=1;event_idx=1;tick;src_done=0;event_idx=0;
  waits=0;while(!ctl_done&&waits<40)begin tick;waits=waits+1;end check(ctl_done,"native consumer done");
  consumer_done=1;tick;consumer_done=0;check(!release_v,"done alone is not drain");
  reads_drained=1;tick;reads_drained=0;check(!release_v,"read drain lacks VM ACK");
  source_idle=0;VM_ACKs_drained=1;tick;VM_ACKs_drained=0;check(!release_v,"source busy holds");
  source_idle=1;selector_idle=0;tick;check(!release_v,"selector busy holds");
  selector_idle=1;tick;check(release_v,"all real drains release");
  repeat(8)begin tick;check(release_v&&retained&&!cmd_r,"release backpressure retains");end
  release_r=1;tick;check(!retained&&cmd_r&&!fault,"release accepted");
  reset_case;command;grant_frame=owner_frame^1;grant;expect_fault;
  reset_case;command;grant_layer=21;grant;expect_fault;
  reset_case;command;grant_pos=10;grant;expect_fault;
  reset_case;command;grant_rank=8;grant;expect_fault;
  reset_case;command;grant_blocks=1;grant;expect_fault;
  reset_case;command;grant_row_end=100;grant;expect_fault;
  reset_case;command;grant;grant;expect_fault;
  reset_case;command;key_visible=1;tick;key_visible=0;expect_fault;
  reset_case;command;grant;key_visible_frame=owner_frame^1;key_visible=1;tick;key_visible=0;expect_fault;
  reset_case;command;grant;query_ACK_frame=owner_frame^1;query_ACK=1;tick;query_ACK=0;expect_fault;
  reset_case;command;grant;visible;prefetch_frame=owner_frame^1;prefetch_accepted=1;tick;prefetch_accepted=0;expect_fault;
  reset_case;command;grant;visible;accepted;drain_frame=owner_frame^1;reads_drained=1;tick;reads_drained=0;expect_fault;
  reset_case;command;reads_drained=1;tick;reads_drained=0;expect_fault;
  reset_case;command;VM_ACKs_drained=1;tick;VM_ACKs_drained=0;expect_fault;
  reset_case;command;consumer_done=1;tick;consumer_done=0;expect_fault;
  reset_case;command;grant;key_visible=1;tick;key_visible=0;key_visible=1;tick;key_visible=0;expect_fault;
  reset_case;command;owner_valid=0;expect_fault;
  reset_case;command;dut.record_bar[1]=dut.record[1];expect_fault;
  $display("CP_INDEX_LEASE PASS cases=%0d real_native_control=1",cases);$finish;
 end
endmodule
