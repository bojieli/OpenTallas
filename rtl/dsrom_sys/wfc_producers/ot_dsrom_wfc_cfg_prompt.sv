`timescale 1ns/1ps
// Finite source-owned producer. No generated tokens, golden oracle or ROM ECC.
// Mutable prompt/draft SRAM retains SECDED; tags travel inside the codeword.
module ot_dsrom_wfc_cfg_prompt #(
 parameter integer ENABLE=0, MAXU=866, PREFIX=8, POSITIONS=8,
 parameter integer SLOTS=MAXU*(PREFIX+POSITIONS), ROWS=(SLOTS+1)/2, BANKS=(ROWS+511)/512
)(
 input wire clk,rst_n,cold_fenced,
 input wire cmd_v, input wire [1:0] cmd_op, // 0 prompt, 1 draft, 2 launch, 3 end
 input wire [9:0] cmd_user, input wire [20:0] cmd_pos,cmd_token,
 input wire [3:0] cmd_block, input wire [15:0] cmd_epoch, input wire [13:0] cmd_entry,
 output wire cmd_ready,
 output wire [9:0] cfg_users, output wire [20:0] cfg_prompt_len,cfg_gen_len,
 output wire [15:0] stage_epoch, output wire [13:0] stage_entry,
 input wire pr_re, input wire [9:0] pr_user, input wire [20:0] pr_pos,
 input wire [3:0] pr_blk, output wire [20:0] pr_q, output wire pr_qk,
 output wire active,initializing,fault
);
 initial if(MAXU!=866 || PREFIX!=8 || POSITIONS!=8 || BANKS!=14)
  $fatal(1,"WFC producer must match the full866 priced finite extent");
 generate if(ENABLE) begin:g_live
  reg poison=0,running=0,ready_mem=0,scanning=0;
  reg [12:0] clear_row=0,clear_check=13'h1fff;
  reg [81:0] config_q=0,config_check={82{1'b1}},pending_q=0,pending_check={82{1'b1}};
  reg [9:0] scan_user=0,scan_user_check=10'h3ff;reg [3:0] scan_pos=0,scan_pos_check=4'hf;
  reg scan_sent_all=0,read_pending=0,read_scan=0,read_last=0,read_prompt=0;
  reg [3:0] read_bank=0,read_block=0;reg read_slot=0;reg [9:0] read_user_q=0;reg [20:0] read_pos_q=0;
  wire config_bad=config_q!=~config_check || pending_q!=~pending_check || clear_row!=~clear_check || scan_user!=~scan_user_check || scan_pos!=~scan_pos_check;
  assign {stage_entry,stage_epoch,cfg_gen_len,cfg_prompt_len,cfg_users}=config_q;
  assign active=running;assign initializing=!ready_mem;assign fault=poison||config_bad;
  assign cmd_ready=rst_n&&ready_mem&&!scanning&&!fault;
  wire take=cmd_v&&cmd_ready;
  wire write_prompt=take&&cmd_op==0&&!running&&cmd_user<MAXU&&cmd_pos<PREFIX;
  wire write_draft=take&&cmd_op==1&&cmd_user<MAXU&&(!running||cmd_epoch==stage_epoch);
  wire write_word=write_prompt||write_draft;
  wire [15:0] write_index=16'(cmd_user)*(PREFIX+POSITIONS)+16'(write_prompt?cmd_pos:21'(PREFIX)+21'(cmd_pos[2:0]));
  wire [12:0] write_row=write_index[13:1];
  wire [56:0] payload={cmd_user,cmd_pos,write_prompt?4'd0:cmd_block,1'b1,cmd_token};
  function automatic [63:0] encode(input [56:0] d);
   integer j,k,p,n;reg [5:0] parity;
   begin parity=0;p=3;n=0;
    while(n<57)begin
     if((p&(p-1))!=0)begin for(k=0;k<6;k=k+1)if((p>>k)&1)parity[k]=parity[k]^d[n];n=n+1;end
     p=p+1;
    end
    encode={^( {parity,d} ),parity,d};
   end
  endfunction
  wire [127:0] wd=128'(encode(payload)) << (64*write_index[0]);
  wire [127:0] wm=128'hffffffffffffffff << (64*write_index[0]);
  wire scan_issue=scanning&&!scan_sent_all;
  wire port_read=rst_n&&!fault&&(scan_issue||(running&&pr_re&&pr_user<cfg_users));
  wire [9:0] read_user=scan_issue?scan_user:pr_user;
  wire [20:0] read_pos=scan_issue?21'(scan_pos):pr_pos;
  wire is_prompt=scan_issue||read_pos<cfg_prompt_len;
  wire [15:0] read_index=16'(read_user)*(PREFIX+POSITIONS)+16'(is_prompt?read_pos:21'(PREFIX)+21'(read_pos[2:0]));
  wire [12:0] read_row=read_index[13:1];
  wire [127:0] bank_q[0:BANKS-1];
  for(genvar b=0;b<BANKS;b=b+1)begin:g_bank
   (* keep=1,dont_touch=1 *) ot_sram_1r1w_512x128_m4_r2c2 u_prompt (
    .clk(clk),.r_ce_in(port_read&&read_row[12:9]==b),.r_addr_in(read_row[8:0]),.rd_out(bank_q[b]),
    .w_ce_in(rst_n&&!fault&&((!ready_mem&&clear_row[12:9]==b)||(write_word&&write_row[12:9]==b))),
    .w_addr_in(!ready_mem?clear_row[8:0]:write_row[8:0]),.wd_in(!ready_mem?128'd0:wd),
    .w_mask_in(!ready_mem?{128{1'b1}}:wm),.rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(14'd0));
  end
  wire [63:0] cw=64'(bank_q[read_bank]>>(64*read_slot));
  wire [56:0] data;wire corrected,uncorrectable;
  ot_rom_secded_dec #(.K(57),.R(6),.N(64)) u_mutable_decode(.cw(cw),.data(data),.corrected(corrected),.uncorrectable(uncorrectable));
  assign pr_q=data[20:0];
  assign pr_qk=rst_n&&running&&!fault&&read_pending&&!read_scan&&!uncorrectable&&data[21]&&data[56:47]==read_user_q&&data[46:26]==read_pos_q&&(read_prompt||data[25:22]==read_block);
  always @(posedge clk)begin
   if(!rst_n)begin
    // Warm reset poisons accepted work; it does not reset a live run or SRAM.
    if(running||scanning)poison<=1;
   end else begin
    if(config_bad)poison<=1;
    if(!ready_mem&&!poison)begin
     if(clear_row==ROWS-1)begin ready_mem<=1;clear_row<=0;clear_check<=13'h1fff;end
     else begin clear_row<=clear_row+1;clear_check<=~(clear_row+13'd1);end
    end
    read_pending<=port_read;read_scan<=scan_issue;
    if(port_read)begin
     read_bank<=read_row[12:9];read_slot<=read_index[0];read_user_q<=read_user;read_pos_q<=read_pos;read_prompt<=is_prompt;read_block<=pr_blk;
     read_last<=scan_issue&&scan_user==pending_q[9:0]-1&&scan_pos==pending_q[30:10]-1;
    end
    if(scan_issue)begin
     if(scan_pos==pending_q[30:10]-1)begin scan_pos<=0;scan_pos_check<=4'hf;if(scan_user==pending_q[9:0]-1)scan_sent_all<=1;else begin scan_user<=scan_user+1;scan_user_check<=~(scan_user+10'd1);end end
     else begin scan_pos<=scan_pos+1;scan_pos_check<=~(scan_pos+4'd1);end
    end
    if(read_pending&&uncorrectable)poison<=1;
    if(read_pending&&read_scan)begin
     if(uncorrectable||!data[21]||data[25:22]!=0||data[56:47]!=read_user_q||data[46:26]!=read_pos_q)begin poison<=1;scanning<=0;end
     else if(read_last)begin config_q<=pending_q;config_check<=~pending_q;running<=1;scanning<=0;end
    end
    if(running&&pr_re&&pr_user>=cfg_users)poison<=1;
    if(take)begin
     case(cmd_op)
      0:if(!write_prompt)poison<=1;
      1:if(!write_draft)poison<=1;
      2:begin
       if(running||cmd_user==0||cmd_user>MAXU||cmd_pos==0||cmd_pos>PREFIX||cmd_token==0||cmd_entry!=14'd12||{1'b0,cmd_pos}+{1'b0,cmd_token}-1>=22'h200000)poison<=1;
       else begin pending_q<={cmd_entry,cmd_epoch,cmd_token,cmd_pos,cmd_user};pending_check<=~{cmd_entry,cmd_epoch,cmd_token,cmd_pos,cmd_user};scanning<=1;scan_user<=0;scan_user_check<=10'h3ff;scan_pos<=0;scan_pos_check<=4'hf;scan_sent_all<=0;end
      end
      3:begin
       // Existing real all-copy fence is required to retire/clear a run.
       if(!cold_fenced)poison<=1;
       else begin running<=0;scanning<=0;ready_mem<=0;clear_row<=0;clear_check<=13'h1fff;config_q<=0;config_check<={82{1'b1}};read_pending<=0;poison<=0;end
      end
     endcase
    end
   end
  end
 end else begin:g_off
  assign cmd_ready=0;assign cfg_users=0;assign cfg_prompt_len=0;assign cfg_gen_len=0;
  assign stage_epoch=0;assign stage_entry=0;assign pr_q=0;assign pr_qk=0;
  assign active=0;assign initializing=0;assign fault=0;
 end endgenerate
endmodule
