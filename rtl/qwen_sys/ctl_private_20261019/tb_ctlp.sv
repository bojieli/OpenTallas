`timescale 1ns/1ps
module tb_ctlp #(parameter integer WS=1);
reg ck=0; always #5 ck=~ck; reg rst_n=0; integer edges=0; integer checked=0; integer scenario=0;
reg  w_cfg_we=0;
reg [7:0] w_cfg_addr=0;
reg [63:0] w_cfg_data=0;
reg  w_start=0;
reg [5:0] w_stage=0;
reg [15:0] w_epoch=0;
reg [17:0] w_token=0;
reg [12:0] w_position=0;
reg [1:0] w_generation=0;
wire  w_compiled_word_slot[0:2];
wire [1:0] w_compiled_word_index[0:2];
wire [58:0] w_compiled_identity[0:2];
wire [1:0] w_compiled_generation[0:2];
wire  w_kvn_word_slot[0:2];
wire  w_configured[0:2];
wire  w_active[0:2];
wire  w_done[0:2];
wire  w_fault[0:2];
wire [31:0] w_cycle[0:2];
wire [3:0] w_expected_valid[0:2];
wire [19:0] w_expected_pc[0:2];
wire [1:0] w_expected_stack[0:2];
wire [58:0] w_expected_identity[0:2];
wire [1:0] w_expected_generation[0:2];
wire [28:0] w_expected_address[0:2];
qkd_kv_native_programme #(.SRAM(WS),.VMAP(1)) w0(.ck(ck),.rst_n(rst_n),.cfg_we(w_cfg_we),.cfg_addr(w_cfg_addr),.cfg_data(w_cfg_data),.start(w_start),.stage(w_stage),.epoch(w_epoch),.token(w_token),.position(w_position),.generation(w_generation),.compiled_word_slot(w_compiled_word_slot[0]),.compiled_word_index(w_compiled_word_index[0]),.compiled_identity(w_compiled_identity[0]),.compiled_generation(w_compiled_generation[0]),.kvn_word_slot(w_kvn_word_slot[0]),.configured(w_configured[0]),.active(w_active[0]),.done(w_done[0]),.fault(w_fault[0]),.cycle(w_cycle[0]),.expected_valid(w_expected_valid[0]),.expected_pc(w_expected_pc[0]),.expected_stack(w_expected_stack[0]),.expected_identity(w_expected_identity[0]),.expected_generation(w_expected_generation[0]),.expected_address(w_expected_address[0]));
qkd_kv_native_programme_ctlp #(.SRAM(WS),.VMAP(1),.ENABLE(0)) w1(.ck(ck),.rst_n(rst_n),.cfg_we(w_cfg_we),.cfg_addr(w_cfg_addr),.cfg_data(w_cfg_data),.start(w_start),.stage(w_stage),.epoch(w_epoch),.token(w_token),.position(w_position),.generation(w_generation),.compiled_word_slot(w_compiled_word_slot[1]),.compiled_word_index(w_compiled_word_index[1]),.compiled_identity(w_compiled_identity[1]),.compiled_generation(w_compiled_generation[1]),.kvn_word_slot(w_kvn_word_slot[1]),.configured(w_configured[1]),.active(w_active[1]),.done(w_done[1]),.fault(w_fault[1]),.cycle(w_cycle[1]),.expected_valid(w_expected_valid[1]),.expected_pc(w_expected_pc[1]),.expected_stack(w_expected_stack[1]),.expected_identity(w_expected_identity[1]),.expected_generation(w_expected_generation[1]),.expected_address(w_expected_address[1]));
qkd_kv_native_programme_ctlp #(.SRAM(WS),.VMAP(1),.ENABLE(1)) w2(.ck(ck),.rst_n(rst_n),.cfg_we(w_cfg_we),.cfg_addr(w_cfg_addr),.cfg_data(w_cfg_data),.start(w_start),.stage(w_stage),.epoch(w_epoch),.token(w_token),.position(w_position),.generation(w_generation),.compiled_word_slot(w_compiled_word_slot[2]),.compiled_word_index(w_compiled_word_index[2]),.compiled_identity(w_compiled_identity[2]),.compiled_generation(w_compiled_generation[2]),.kvn_word_slot(w_kvn_word_slot[2]),.configured(w_configured[2]),.active(w_active[2]),.done(w_done[2]),.fault(w_fault[2]),.cycle(w_cycle[2]),.expected_valid(w_expected_valid[2]),.expected_pc(w_expected_pc[2]),.expected_stack(w_expected_stack[2]),.expected_identity(w_expected_identity[2]),.expected_generation(w_expected_generation[2]),.expected_address(w_expected_address[2]));
always @(negedge ck) begin if({w_compiled_word_slot[0],w_compiled_word_index[0],w_compiled_identity[0],w_compiled_generation[0],w_kvn_word_slot[0],w_configured[0],w_active[0],w_done[0],w_fault[0],w_cycle[0],w_expected_valid[0],w_expected_pc[0],w_expected_stack[0],w_expected_identity[0],w_expected_generation[0],w_expected_address[0]} !== {w_compiled_word_slot[1],w_compiled_word_index[1],w_compiled_identity[1],w_compiled_generation[1],w_kvn_word_slot[1],w_configured[1],w_active[1],w_done[1],w_fault[1],w_cycle[1],w_expected_valid[1],w_expected_pc[1],w_expected_stack[1],w_expected_identity[1],w_expected_generation[1],w_expected_address[1]}) $fatal(1,"CTLP_MISMATCH family=w enable=0 scenario=%0d edge=%0d",scenario,edges); end
always @(negedge ck) begin if({w_compiled_word_slot[0],w_compiled_word_index[0],w_compiled_identity[0],w_compiled_generation[0],w_kvn_word_slot[0],w_configured[0],w_active[0],w_done[0],w_fault[0],w_cycle[0],w_expected_valid[0],w_expected_pc[0],w_expected_stack[0],w_expected_identity[0],w_expected_generation[0],w_expected_address[0]} !== {w_compiled_word_slot[2],w_compiled_word_index[2],w_compiled_identity[2],w_compiled_generation[2],w_kvn_word_slot[2],w_configured[2],w_active[2],w_done[2],w_fault[2],w_cycle[2],w_expected_valid[2],w_expected_pc[2],w_expected_stack[2],w_expected_identity[2],w_expected_generation[2],w_expected_address[2]}) $fatal(1,"CTLP_MISMATCH family=w enable=1 scenario=%0d edge=%0d",scenario,edges); end
reg  p_cfg_we=0;
reg [8:0] p_cfg_addr=0;
reg [63:0] p_cfg_data=0;
reg  p_start=0;
reg  p_authority_valid=0;
reg  p_programme_authorized=0;
reg [15:0] p_programme_epoch=0;
reg [63:0] p_programme_digest=0;
reg [15:0] p_authority_epoch=0;
reg [17:0] p_authority_token=0;
reg [17:0] p_authority_position=0;
reg [1:0] p_authority_generation=0;
wire  p_ctrl_go[0:2];
wire  p_kgo[0:2];
wire  p_vgo[0:2];
wire  p_attention_issue[0:2];
wire  p_attention_run[0:2];
wire  p_writer_start[0:2];
wire  p_link_start[0:2];
wire  p_stage_start[0:2];
wire  p_stage_done[0:2];
wire  p_expected_upstream_quiet[0:2];
wire [5:0] p_completed_stage[0:2];
wire [5:0] p_stage[0:2];
wire [5:0] p_layer[0:2];
wire [15:0] p_epoch[0:2];
wire [17:0] p_token[0:2];
wire [17:0] p_position[0:2];
wire [13:0] p_ctx_t[0:2];
wire [1:0] p_generation[0:2];
wire  p_configured[0:2];
wire  p_active[0:2];
wire  p_done[0:2];
wire  p_fault[0:2];
wire [7:0] p_fault_code[0:2];
wire [31:0] p_age[0:2];
wire [31:0] p_token_cycles[0:2];
qkd_static_kv_layer_programme_mus #(.MU(1)) p0(.ck(ck),.rst_n(rst_n),.cfg_we(p_cfg_we),.cfg_addr(p_cfg_addr),.cfg_data(p_cfg_data),.start(p_start),.authority_valid(p_authority_valid),.programme_authorized(p_programme_authorized),.programme_epoch(p_programme_epoch),.programme_digest(p_programme_digest),.authority_epoch(p_authority_epoch),.authority_token(p_authority_token),.authority_position(p_authority_position),.authority_generation(p_authority_generation),.ctrl_go(p_ctrl_go[0]),.kgo(p_kgo[0]),.vgo(p_vgo[0]),.attention_issue(p_attention_issue[0]),.attention_run(p_attention_run[0]),.writer_start(p_writer_start[0]),.link_start(p_link_start[0]),.stage_start(p_stage_start[0]),.stage_done(p_stage_done[0]),.expected_upstream_quiet(p_expected_upstream_quiet[0]),.completed_stage(p_completed_stage[0]),.stage(p_stage[0]),.layer(p_layer[0]),.epoch(p_epoch[0]),.token(p_token[0]),.position(p_position[0]),.ctx_t(p_ctx_t[0]),.generation(p_generation[0]),.configured(p_configured[0]),.active(p_active[0]),.done(p_done[0]),.fault(p_fault[0]),.fault_code(p_fault_code[0]),.age(p_age[0]),.token_cycles(p_token_cycles[0]));
qkd_static_kv_layer_programme_ctlp #(.MU(1),.ENABLE(0)) p1(.ck(ck),.rst_n(rst_n),.cfg_we(p_cfg_we),.cfg_addr(p_cfg_addr),.cfg_data(p_cfg_data),.start(p_start),.authority_valid(p_authority_valid),.programme_authorized(p_programme_authorized),.programme_epoch(p_programme_epoch),.programme_digest(p_programme_digest),.authority_epoch(p_authority_epoch),.authority_token(p_authority_token),.authority_position(p_authority_position),.authority_generation(p_authority_generation),.ctrl_go(p_ctrl_go[1]),.kgo(p_kgo[1]),.vgo(p_vgo[1]),.attention_issue(p_attention_issue[1]),.attention_run(p_attention_run[1]),.writer_start(p_writer_start[1]),.link_start(p_link_start[1]),.stage_start(p_stage_start[1]),.stage_done(p_stage_done[1]),.expected_upstream_quiet(p_expected_upstream_quiet[1]),.completed_stage(p_completed_stage[1]),.stage(p_stage[1]),.layer(p_layer[1]),.epoch(p_epoch[1]),.token(p_token[1]),.position(p_position[1]),.ctx_t(p_ctx_t[1]),.generation(p_generation[1]),.configured(p_configured[1]),.active(p_active[1]),.done(p_done[1]),.fault(p_fault[1]),.fault_code(p_fault_code[1]),.age(p_age[1]),.token_cycles(p_token_cycles[1]));
qkd_static_kv_layer_programme_ctlp #(.MU(1),.ENABLE(1)) p2(.ck(ck),.rst_n(rst_n),.cfg_we(p_cfg_we),.cfg_addr(p_cfg_addr),.cfg_data(p_cfg_data),.start(p_start),.authority_valid(p_authority_valid),.programme_authorized(p_programme_authorized),.programme_epoch(p_programme_epoch),.programme_digest(p_programme_digest),.authority_epoch(p_authority_epoch),.authority_token(p_authority_token),.authority_position(p_authority_position),.authority_generation(p_authority_generation),.ctrl_go(p_ctrl_go[2]),.kgo(p_kgo[2]),.vgo(p_vgo[2]),.attention_issue(p_attention_issue[2]),.attention_run(p_attention_run[2]),.writer_start(p_writer_start[2]),.link_start(p_link_start[2]),.stage_start(p_stage_start[2]),.stage_done(p_stage_done[2]),.expected_upstream_quiet(p_expected_upstream_quiet[2]),.completed_stage(p_completed_stage[2]),.stage(p_stage[2]),.layer(p_layer[2]),.epoch(p_epoch[2]),.token(p_token[2]),.position(p_position[2]),.ctx_t(p_ctx_t[2]),.generation(p_generation[2]),.configured(p_configured[2]),.active(p_active[2]),.done(p_done[2]),.fault(p_fault[2]),.fault_code(p_fault_code[2]),.age(p_age[2]),.token_cycles(p_token_cycles[2]));
always @(negedge ck) begin if({p_ctrl_go[0],p_kgo[0],p_vgo[0],p_attention_issue[0],p_attention_run[0],p_writer_start[0],p_link_start[0],p_stage_start[0],p_stage_done[0],p_expected_upstream_quiet[0],p_completed_stage[0],p_stage[0],p_layer[0],p_epoch[0],p_token[0],p_position[0],p_ctx_t[0],p_generation[0],p_configured[0],p_active[0],p_done[0],p_fault[0],p_fault_code[0],p_age[0],p_token_cycles[0]} !== {p_ctrl_go[1],p_kgo[1],p_vgo[1],p_attention_issue[1],p_attention_run[1],p_writer_start[1],p_link_start[1],p_stage_start[1],p_stage_done[1],p_expected_upstream_quiet[1],p_completed_stage[1],p_stage[1],p_layer[1],p_epoch[1],p_token[1],p_position[1],p_ctx_t[1],p_generation[1],p_configured[1],p_active[1],p_done[1],p_fault[1],p_fault_code[1],p_age[1],p_token_cycles[1]}) $fatal(1,"CTLP_MISMATCH family=p enable=0 scenario=%0d edge=%0d",scenario,edges); end
always @(negedge ck) begin if({p_ctrl_go[0],p_kgo[0],p_vgo[0],p_attention_issue[0],p_attention_run[0],p_writer_start[0],p_link_start[0],p_stage_start[0],p_stage_done[0],p_expected_upstream_quiet[0],p_completed_stage[0],p_stage[0],p_layer[0],p_epoch[0],p_token[0],p_position[0],p_ctx_t[0],p_generation[0],p_configured[0],p_active[0],p_done[0],p_fault[0],p_fault_code[0],p_age[0],p_token_cycles[0]} !== {p_ctrl_go[2],p_kgo[2],p_vgo[2],p_attention_issue[2],p_attention_run[2],p_writer_start[2],p_link_start[2],p_stage_start[2],p_stage_done[2],p_expected_upstream_quiet[2],p_completed_stage[2],p_stage[2],p_layer[2],p_epoch[2],p_token[2],p_position[2],p_ctx_t[2],p_generation[2],p_configured[2],p_active[2],p_done[2],p_fault[2],p_fault_code[2],p_age[2],p_token_cycles[2]}) $fatal(1,"CTLP_MISMATCH family=p enable=1 scenario=%0d edge=%0d",scenario,edges); end
// Deliberately independent pre-boot memory/Q values; original remains X.
// These are adversarial simulation states, not an initialization contract.
generate if(WS==1) begin:g_poison
 initial begin #1;
  for(integer a=0;a<130;a=a+1)begin
   w1.g_sr.u_rows.arr[a]={258{1'b1}};w2.g_sr.u_rows.arr[a]={129{2'b10}};
  end
  w1.g_sr.u_rows.rd_out={256{1'b1}};w2.g_sr.u_rows.rd_out={128{2'b10}};
 end
end endgenerate
initial begin #1;
 for(integer a=0;a<130;a=a+1)begin
  p1.u_rowa.arr[a]={258{1'b1}};p1.u_rowb.arr[a]={129{2'b10}};
  p2.u_rowa.arr[a]={129{2'b01}};p2.u_rowb.arr[a]={258{1'b1}};
 end
 p1.u_rowa.rd_out=~256'd0;p1.u_rowb.rd_out={128{2'b10}};
 p2.u_rowa.rd_out={128{2'b01}};p2.u_rowb.rd_out=~256'd0;
end
always @(posedge ck) edges<=edges+1;
always @(negedge ck) if(edges>4) checked=checked+1;
task tick; begin @(posedge ck); #1; @(negedge ck); #1; end endtask
task idle(input integer n); begin repeat(n)tick(); end endtask
task reset_all; begin rst_n=0; w_cfg_we=0;p_cfg_we=0;w_start=0;p_start=0;idle(5);rst_n=1;idle(5);end endtask
task wc(input integer a,input reg[63:0] d);begin w_cfg_we=1;w_cfg_addr=a;w_cfg_data=d;tick();w_cfg_we=0;tick();end endtask
task pc(input integer a,input reg[63:0] d);begin p_cfg_we=1;p_cfg_addr=a;p_cfg_data=d;tick();p_cfg_we=0;tick();end endtask
function automatic integer wr(input integer s,input integer f);begin
 case(f) 0:wr=4+s%3;1:wr=8+s%3;2:wr=12+s%3;3:wr=16+s%3;default:wr=22+s%3;endcase
end endfunction
function automatic integer pr(input integer s,input integer f);begin
 case(f)0:pr=3;1:pr=4;2:pr=5;3:pr=6;4:pr=10;5:pr=11;6:pr=12;7:pr=13;default:pr=18+s%3;endcase
end endfunction
task boot_w;begin for(integer s=0;s<36;s=s+1)for(integer f=0;f<5;f=f+1)wc(s*5+f,wr(s,f));wc(180,64'h514b565052473336);idle(4);if(!w_configured[0]||w_fault[0])$fatal(1,"WRITER_BOOT_FAIL");end endtask
task boot_p;begin
 for(integer s=0;s<36;s=s+1)for(integer f=0;f<9;f=f+1)pc(s*9+f,pr(s,f));
 pc(324,64'hc15aee1097de2341);pc(325,16'h20);
 for(integer u=0;u<4;u=u+1)for(integer j=0;j<36;j=j+1)pc(326+u*36+j,(j+u)%3);
 pc(470,64'h514b564c59523336);idle(4);if(!p_configured[0]||p_fault[0])$fatal(1,"PROGRAMME_BOOT_FAIL");
end endtask
integer wd=0,ws=0,we=0,pd=0,ps=0,pb=0;
always @(negedge ck) begin if(w_done[0])wd=wd+1; if(w_compiled_word_slot[0])ws=ws+1; if(|w_expected_valid[0])we=we+1; if(p_done[0])pd=pd+1; if(p_stage_done[0])ps=ps+1; if(p_stage_start[0])pb=pb+1; end
task start_w(input integer s,input integer tok);integer d0,s0,e0;begin
 d0=wd;s0=ws;e0=we;
 w_stage=s;w_epoch=16'h20;w_token=tok;w_position=tok*17;w_generation=tok%4;w_start=1;tick();w_start=0;idle(40);
 if(w_fault[0]||w_active[0]||wd-d0!=1||ws-s0!=4||we-e0!=2)$fatal(1,"WRITER_RUNTIME_FAIL done=%0d slots=%0d descriptors=%0d",wd-d0,ws-s0,we-e0);end endtask
task start_p(input integer tok);integer d0,s0,b0;begin
 d0=pd;s0=ps;b0=pb;
 p_authority_epoch=16'h20;p_authority_token=tok;p_authority_position=tok*19;p_authority_generation=tok%4;
 p_authority_valid=1;p_programme_authorized=1;p_programme_epoch=16'h20;p_programme_digest=64'hc15aee1097de2341;
 idle(3);p_start=1;tick();p_start=0;idle(1000);if(p_fault[0]||p_active[0]||pd-d0!=1||ps-s0!=36||pb-b0!=36)$fatal(1,"PROGRAMME_RUNTIME_FAIL done=%0d ends=%0d begins=%0d",pd-d0,ps-s0,pb-b0);end endtask
initial begin
 reset_all(); scenario=1;boot_w();boot_p();
 for(integer t=0;t<2;t=t+1)begin for(integer s=1;s<=36;s=s+1)start_w(s,t+1);start_p(t+1);end
 // Rejected start during pending boot write: memory Q remains arbitrary, never consumed.
 scenario=2;reset_all();w_cfg_we=1;w_cfg_addr=0;w_cfg_data=4;tick();w_cfg_we=0;w_start=1;w_stage=1;tick();w_start=0;idle(5);if(!w_fault[0])$fatal(1,"INVALID_START_NOT_REJECTED");
 // Exact final pending boot write overlaps rejected start; seal is absent.
 scenario=14;reset_all();
 for(integer s=0;s<36;s=s+1)for(integer f=0;f<5;f=f+1)if(s*5+f<179)wc(s*5+f,wr(s,f));
 w_cfg_we=1;w_cfg_addr=179;w_cfg_data=wr(35,4);tick();w_cfg_we=0;w_start=1;w_stage=36;tick();w_start=0;
 if(!w0.wq_v||!w0.start_p||w0.wq_stage!=(36'd1<<35)||w0.wq_word!=5'b10000||w0.wq_data!=wr(35,4))$fatal(1,"FINAL_WRITE_WITNESS_MISSING");
 $display("CTLP_FINAL_PENDING_WRITE edge=%0d next_cfg_stage=%0d final_row=35 final_word=4 raw_read=%b write=%b",edges,w0.cfg_stage,w0.start_p,w0.wq_v);
 idle(5);if(!w_fault[0])$fatal(1,"FINAL_PENDING_START_NOT_REJECTED");
 // Reset interrupts an accepted write before its delayed memory commit.
 scenario=12;reset_all();w_cfg_we=1;w_cfg_addr=0;w_cfg_data=4;tick();w_cfg_we=0;rst_n=0;idle(4);rst_n=1;idle(5);boot_w();start_w(2,3);
 // Reset independently interrupts first read and row landing.
 for(integer r=0;r<3;r=r+1)begin scenario=3+r;reset_all();boot_w();w_start=1;w_stage=36;tick();w_start=0;idle(r);reset_all();boot_w();start_w(1,4);end
 // Programme exact write/read/landing reset interruption and complete re-boot.
 scenario=15;reset_all();p_cfg_we=1;p_cfg_addr=0;p_cfg_data=3;tick();p_cfg_we=0;rst_n=0;idle(4);rst_n=1;idle(5);boot_p();start_p(5);
 for(integer r=0;r<3;r=r+1)begin
  scenario=16+r;reset_all();boot_p();p_start=1;tick();p_start=0;idle(r);reset_all();boot_p();start_p(6);
 end
 scenario=13;reset_all();boot_w();w_stage=1;w_start=1;tick();w_stage=2;tick();w_start=0;idle(40);if(!w_fault[0])$fatal(1,"ACTIVE_START_NOT_REJECTED");
 scenario=6;reset_all();wc(1,4);idle(3);if(!w_fault[0])$fatal(1,"WRITER_BAD_ADDR_NOT_REJECTED");
 scenario=7;reset_all();wc(0,8);wc(1,4);wc(2,12);wc(3,16);wc(4,22);idle(3);if(!w_fault[0])$fatal(1,"WRITER_BAD_ORDER_NOT_REJECTED");
 scenario=8;reset_all();pc(1,3);idle(3);if(!p_fault[0])$fatal(1,"PROGRAMME_BAD_ADDR_NOT_REJECTED");
 scenario=9;reset_all();boot_p();p_programme_digest=0;p_programme_epoch=16'h20;p_authority_epoch=16'h20;p_authority_valid=1;p_programme_authorized=1;idle(3);p_start=1;tick();p_start=0;idle(4);if(!p_fault[0])$fatal(1,"BAD_DIGEST_NOT_REJECTED");
 scenario=10;reset_all();boot_p();p_programme_digest=64'hc15aee1097de2341;p_programme_epoch=16'h21;idle(3);p_start=1;tick();p_start=0;idle(4);if(!p_fault[0])$fatal(1,"BAD_EPOCH_NOT_REJECTED");
 scenario=11;reset_all();boot_w();w_cfg_we=1;w_cfg_addr=180;w_start=1;w_stage=1;tick();w_cfg_we=0;w_start=0;idle(5);if(!w_fault[0])$fatal(1,"CFG_START_NOT_REJECTED");
 $display("CTLP_PASS checked_edges=%0d scenarios=18 original_enable0_enable1_all_outputs",checked);$finish;
end
endmodule
