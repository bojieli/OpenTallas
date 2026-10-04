module wf_abi #(parameter integer PKG_WAVE=0);
localparam integer PKG_ID=0;
localparam integer MAXU=866;
localparam integer SOURCE=1;
localparam integer RESULT_PARTS=1;
localparam integer SEND_HIDDEN=0;
localparam integer HID_DEST=0;
localparam integer SEND_RESULT=0;
localparam integer RES_DEST=0;
localparam integer COMBINE_IN=0;
localparam integer ROW0=0;
localparam integer FWD_TOKEN=1;
localparam integer FULL_SHAPE=1;
localparam integer NW=21;
localparam integer AW=30;
localparam integer VWA=15;
localparam integer FLIT=512;
localparam integer USER_W=10;
localparam integer KVW=32768;
localparam integer XWORDS=1;
localparam integer RXWORDS=1;
localparam integer RXB=0;
localparam integer TXB=0;
localparam integer PKG_WAVE_WIN=6;
wire  clk;
wire  rn;
wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] cfg_users;
wire [NW-1:0] cfg_prompt_len;
wire [NW-1:0] cfg_gen_len;
wire  pc_in_valid;
wire  pc_in_ready;
wire [FLIT-1:0] pc_in_data;
wire  pc_in_last;
wire  pc_out_valid;
wire  pc_out_ready;
wire [FLIT-1:0] pc_out_data;
wire  pc_out_last;
wire  c_start;
wire [NW-1:0] c_token;
wire [NW-1:0] c_pos;
wire [USER_W-1:0] c_user;
wire [AW-1:0] kv_base;
wire  xa_we;
wire [VWA-1:0] xa_waddr;
wire [FLIT-1:0] xa_wdata;
wire  xa_re;
wire [VWA-1:0] xa_raddr;
wire [FLIT-1:0] xa_rq;
wire  pr_re;
wire [USER_W-1:0] pr_user;
wire [NW-1:0] pr_pos;
wire [NW-1:0] pr_q;
wire  ctrl_busy;
wire  tok_valid;
wire [USER_W-1:0] tok_user;
wire [NW-1:0] tok_pos;
wire [NW-1:0] tok_id;
wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] users_done;
wire  proto_fault;
wire wf_stage_done;
wire wf_stage_accepted;
wire [20:0] wf_stage_next_token;
wire [31:0] wf_stage_next_val;
wire wf_request;
wire [20:0] wf_token,wf_pos;
wire [9:0] wf_user;
wire wf_busy;
wire [3:0] wf_pr_blk;
wire wf_pr_qk;
wire wf_issue,wf_reject,wf_squash;
wire host_mode,core_done,c8_write_quiet,c8_write_quarantine,c8_write_fault,coll_busy;
wire [NW-1:0] core_next_token;
wire [31:0] core_next_val;
    assign wf_request = PKG_WAVE && c_start;
    assign wf_token = c_token;
    assign wf_pos = c_pos;
    assign wf_user = c_user;
    assign wf_busy = PKG_WAVE && ctrl_busy;
    // Local mutable-state visibility comes from the actual selected journals.
    // Arch must additionally provide the full-stage/index-visible completion.
    wire wf_result_visible = c8_write_quiet && !c8_write_quarantine &&
                             !c8_write_fault && !coll_busy;
    ot_rom_pkg_ctrl_wf_s81 #(.WAVE(PKG_WAVE), .WIN(PKG_WAVE_WIN), .PKG_ID(PKG_ID), .FLIT(FLIT), .NW(NW), .AW(AW), .VWA(VWA),
                        .USER_W(FULL_SHAPE ? 10 : 8), .MAXU(MAXU), .KVW(KVW),
                        .XWORDS(XWORDS), .RXWORDS(RXWORDS), .RXB(RXB), .TXB(TXB), .SOURCE(SOURCE),
                        .RESULT_PARTS(RESULT_PARTS), .SEND_HIDDEN(SEND_HIDDEN), .HID_DEST(HID_DEST),
                        .SEND_RESULT(SEND_RESULT), .RES_DEST(RES_DEST), .COMBINE_IN(COMBINE_IN), .ROW0(ROW0),
                        .FWD_TOKEN(FWD_TOKEN)) u_ctrl (
        .clk(clk), .rst_n(rn),
        .cfg_users(cfg_users), .cfg_prompt_len(cfg_prompt_len), .cfg_gen_len(cfg_gen_len),
        .in_valid(pc_in_valid), .in_ready(pc_in_ready), .in_data(pc_in_data), .in_last(pc_in_last),
        .out_valid(pc_out_valid), .out_ready(pc_out_ready), .out_data(pc_out_data), .out_last(pc_out_last),
        .core_start(c_start), .core_token(c_token), .core_pos(c_pos), .core_user(c_user),
        .core_done(PKG_WAVE ? (wf_stage_done && wf_result_visible) : (host_mode ? 1'b0 : core_done)),
        .core_next_token(PKG_WAVE ? wf_stage_next_token : core_next_token), .core_next_val(PKG_WAVE ? wf_stage_next_val : core_next_val), .kv_base(kv_base),
        .vm_we(xa_we), .vm_waddr(xa_waddr), .vm_wdata(xa_wdata), .vm_re(xa_re), .vm_raddr(xa_raddr), .vm_rq(xa_rq),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
        .core_done_accepted(wf_stage_accepted),
        .pr_blk(wf_pr_blk), .pr_qk(PKG_WAVE && wf_pr_qk),
        .wf_issue(wf_issue), .wf_reject(wf_reject), .wf_squash(wf_squash),
        .core_busy(ctrl_busy), .tok_valid(tok_valid), .tok_user(tok_user), .tok_pos(tok_pos), .tok_id(tok_id),
        .users_done(users_done), .proto_fault(proto_fault));
endmodule
