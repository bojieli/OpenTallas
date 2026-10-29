`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg  rst_n='0;
reg [1:0] cfg_stack='0;
reg [779:0] di='0;
reg [260:0] land_er='0;
wire [779:0] g_dout;
wire [287:0] g_land_es;
wire [287:0] g_wes;
wire [317:0] g_es_context;
wire  g_es_expected_valid;
wire [60:0] g_es_expected_identity;
wire [28:0] g_es_expected_address;
wire [4:0] g_es_expected_pc;
wire [1:0] g_es_expected_stack;
wire  g_emb_issue_v;
wire [17:0] g_emb_token;
wire [5:0] g_emb_word_index;
wire  g_emb_half;
wire  g_emb_scale;
wire [15:0] g_emb_epoch;
wire  g_emb_return_slot;
wire  g_capture_slot;
wire  g_transfer_slot;
wire  g_fault;
wire [779:0] p_dout;
wire [287:0] p_land_es;
wire [287:0] p_wes;
wire [317:0] p_es_context;
wire  p_es_expected_valid;
wire [60:0] p_es_expected_identity;
wire [28:0] p_es_expected_address;
wire [4:0] p_es_expected_pc;
wire [1:0] p_es_expected_stack;
wire  p_emb_issue_v;
wire [17:0] p_emb_token;
wire [5:0] p_emb_word_index;
wire  p_emb_half;
wire  p_emb_scale;
wire [15:0] p_emb_epoch;
wire  p_emb_return_slot;
wire  p_capture_slot;
wire  p_transfer_slot;
wire  p_fault;
wire [779:0] b_dout;
wire [287:0] b_land_es;
wire [287:0] b_wes;
wire [317:0] b_es_context;
wire  b_es_expected_valid;
wire [60:0] b_es_expected_identity;
wire [28:0] b_es_expected_address;
wire [4:0] b_es_expected_pc;
wire [1:0] b_es_expected_stack;
wire  b_emb_issue_v;
wire [17:0] b_emb_token;
wire [5:0] b_emb_word_index;
wire  b_emb_half;
wire  b_emb_scale;
wire [15:0] b_emb_epoch;
wire  b_emb_return_slot;
wire  b_capture_slot;
wire  b_transfer_slot;
wire  b_fault;
wire [779:0] r_dout;
wire [287:0] r_land_es;
wire [287:0] r_wes;
wire [317:0] r_es_context;
wire  r_es_expected_valid;
wire [60:0] r_es_expected_identity;
wire [28:0] r_es_expected_address;
wire [4:0] r_es_expected_pc;
wire [1:0] r_es_expected_stack;
wire  r_emb_issue_v;
wire [17:0] r_emb_token;
wire [5:0] r_emb_word_index;
wire  r_emb_half;
wire  r_emb_scale;
wire [15:0] r_emb_epoch;
wire  r_emb_return_slot;
wire  r_capture_slot;
wire  r_transfer_slot;
wire  r_fault;
qkd_kv_pc_chain_station_b_p u_g (.ck(clk), .rst_n(rst_n), .cfg_stack(cfg_stack), .di(di), .dout(g_dout), .land_es(g_land_es), .land_er(land_er), .wes(g_wes), .es_context(g_es_context), .es_expected_valid(g_es_expected_valid), .es_expected_identity(g_es_expected_identity), .es_expected_address(g_es_expected_address), .es_expected_pc(g_es_expected_pc), .es_expected_stack(g_es_expected_stack), .emb_issue_v(g_emb_issue_v), .emb_token(g_emb_token), .emb_word_index(g_emb_word_index), .emb_half(g_emb_half), .emb_scale(g_emb_scale), .emb_epoch(g_emb_epoch), .emb_return_slot(g_emb_return_slot), .capture_slot(g_capture_slot), .transfer_slot(g_transfer_slot), .fault(g_fault));
pc_chain_collar_good u_p (.ck(clk), .rst_n(rst_n), .cfg_stack(cfg_stack), .di(di), .dout(p_dout), .land_es(p_land_es), .land_er(land_er), .wes(p_wes), .es_context(p_es_context), .es_expected_valid(p_es_expected_valid), .es_expected_identity(p_es_expected_identity), .es_expected_address(p_es_expected_address), .es_expected_pc(p_es_expected_pc), .es_expected_stack(p_es_expected_stack), .emb_issue_v(p_emb_issue_v), .emb_token(p_emb_token), .emb_word_index(p_emb_word_index), .emb_half(p_emb_half), .emb_scale(p_emb_scale), .emb_epoch(p_emb_epoch), .emb_return_slot(p_emb_return_slot), .capture_slot(p_capture_slot), .transfer_slot(p_transfer_slot), .fault(p_fault));
pc_chain_collar_badbit u_b (.ck(clk), .rst_n(rst_n), .cfg_stack(cfg_stack), .di(di), .dout(b_dout), .land_es(b_land_es), .land_er(land_er), .wes(b_wes), .es_context(b_es_context), .es_expected_valid(b_es_expected_valid), .es_expected_identity(b_es_expected_identity), .es_expected_address(b_es_expected_address), .es_expected_pc(b_es_expected_pc), .es_expected_stack(b_es_expected_stack), .emb_issue_v(b_emb_issue_v), .emb_token(b_emb_token), .emb_word_index(b_emb_word_index), .emb_half(b_emb_half), .emb_scale(b_emb_scale), .emb_epoch(b_emb_epoch), .emb_return_slot(b_emb_return_slot), .capture_slot(b_capture_slot), .transfer_slot(b_transfer_slot), .fault(b_fault));
pc_chain_collar_badreset u_r (.ck(clk), .rst_n(rst_n), .cfg_stack(cfg_stack), .di(di), .dout(r_dout), .land_es(r_land_es), .land_er(land_er), .wes(r_wes), .es_context(r_es_context), .es_expected_valid(r_es_expected_valid), .es_expected_identity(r_es_expected_identity), .es_expected_address(r_es_expected_address), .es_expected_pc(r_es_expected_pc), .es_expected_stack(r_es_expected_stack), .emb_issue_v(r_emb_issue_v), .emb_token(r_emb_token), .emb_word_index(r_emb_word_index), .emb_half(r_emb_half), .emb_scale(r_emb_scale), .emb_epoch(r_emb_epoch), .emb_return_slot(r_emb_return_slot), .capture_slot(r_capture_slot), .transfer_slot(r_transfer_slot), .fault(r_fault));
reg [1818:0] prior;always @(posedge clk) prior<={g_dout,g_land_es,g_wes,g_es_context,g_es_expected_valid,g_es_expected_identity,g_es_expected_address,g_es_expected_pc,g_es_expected_stack,g_emb_issue_v,g_emb_token,g_emb_word_index,g_emb_half,g_emb_scale,g_emb_epoch,g_emb_return_slot,g_capture_slot,g_transfer_slot,g_fault};
integer cyc,bad=0,bitcaught=0,resetcaught=0,bootbeats=0,writerbeats=0,issues=0;
integer j;
initial begin
cfg_stack=2'd1;
for(cyc=0;cyc<4096;cyc=cyc+1)begin
 @(negedge clk);
 if(cyc>12)begin
  if({p_dout,p_land_es,p_wes,p_es_context,p_es_expected_valid,p_es_expected_identity,p_es_expected_address,p_es_expected_pc,p_es_expected_stack,p_emb_issue_v,p_emb_token,p_emb_word_index,p_emb_half,p_emb_scale,p_emb_epoch,p_emb_return_slot,p_capture_slot,p_transfer_slot,p_fault} !== prior)begin bad=bad+1;if(bad<5)$display("BAD cyc=%0d",cyc);end
  if({b_dout,b_land_es,b_wes,b_es_context,b_es_expected_valid,b_es_expected_identity,b_es_expected_address,b_es_expected_pc,b_es_expected_stack,b_emb_issue_v,b_emb_token,b_emb_word_index,b_emb_half,b_emb_scale,b_emb_epoch,b_emb_return_slot,b_capture_slot,b_transfer_slot,b_fault} !== prior)bitcaught=bitcaught+1;
  if({r_dout,r_land_es,r_wes,r_es_context,r_es_expected_valid,r_es_expected_identity,r_es_expected_address,r_es_expected_pc,r_es_expected_stack,r_emb_issue_v,r_emb_token,r_emb_word_index,r_emb_half,r_emb_scale,r_emb_epoch,r_emb_return_slot,r_capture_slot,r_transfer_slot,r_fault} !== prior)resetcaught=resetcaught+1;
 end
 if(p_land_es[0])bootbeats=bootbeats+1; if(p_wes[0])writerbeats=writerbeats+1;if(p_emb_issue_v)issues=issues+1;
 rst_n=(cyc%512>=8);di='0;land_er='0;
 for(j=0;j<780;j=j+32)di={di,32'($urandom)};
 di[0]=0;di[1]=0;di[615]=0;di[616]=0;di[719]=0;di[754]=0;di[779]=0;
 di[6:2]=5'd0;di[11:7]=5'd0;
 case(cyc%8)
 0:di[779]=1'b1;
 1:begin di[0]=1'b1;di[553]=1'b1;end
 2:begin di[615]=1'b1;di[621:617]=5'd0;end
 3:begin di[754]=1'b1;di[759:755]=5'd0;di[762:760]=3'd0;di[778:763]=16'd3;end
 4:begin di[719]=1'b1;di[737:720]=18'd5;end
 default:begin end
 endcase
end
$display("COLLAR cycles=%0d bad=%0d bitcaught=%0d resetcaught=%0d boot=%0d writer=%0d issue=%0d",cyc,bad,bitcaught,resetcaught,bootbeats,writerbeats,issues);
if(bad!=0 || bitcaught==0 || resetcaught==0 || bootbeats<100 || writerbeats<100 || issues==0)$fatal(1,"COLLAR FAIL");
$finish;end
endmodule
