`timescale 1ns/1ps
`default_nettype none
// Opt-in composition only. Model583e28c64/4196c9628 precedes RTL.
// Host/descriptor/collar physical qualification remains OPEN; no gate claim.
module ot_hbm_svc_sm_xcal_rel_banked #(parameter integer MUT = 0, parameter integer PAW = 11, parameter integer PREL = 1,
    parameter integer DD = 256, parameter integer DAW = (DD > 128) ? 8 : 7,
    parameter integer CLASS_ENABLE=0,CLASS_MUT=0,MIRROR_MUT=0,CALMUT=0,BANKMUT=0) (
    input  wire          clk_core,clk_bank0,clk_bank1,
    input  wire          rst_n,
    input  wire          cfg_we,
    input  wire [PAW-1:0] cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_we,
    input  wire [DAW-1:0] desc_addr,
    input  wire [255:0]  desc_data,
    input  wire          run_v,
    input  wire [DAW-1:0] run_base,
    input  wire [DAW:0]  run_count,
    output wire [108:0]  cmd_ext,
    output wire [63:0]   kv_desc,
    output wire          active,
    output wire          done,
    output wire          fault,
    output wire [174:0] command_envelope,
    output wire command_class_observe,command_context_valid_observe
);
    wire clk=clk_core;
    initial if(PAW!=11 || (DD!=128&&DD!=256))$fatal(1,"banked public XC production shape requires PAW11/DD128or256");
    reg active_pre,done_pre,host_fault;
    // ---------------- local reset release at the rst_n pin (H-SM native capture repair, 2026-10-16): r1 measured
    // rst_n capture 254.0 ps > 190 (the pin fanned out to every async-clear flop here and in u_cal).  rst_n now lands
    // on ONE async-clear flop at the pin face (assert async, release synchronous, one edge later); every other flop
    // clears from rst_q, a reg->recovery path inside the leaf.  No operation edge changes (the host collar issues
    // descriptor/programme writes only after reset; release precedes them).  MUT 3: rst_q never releases.
    reg rst_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_q <= 1'b0;
        else        rst_q <= (MUT == 3) ? 1'b0 : 1'b1;
    // ---------------- pin flops
    reg desc_we_q, run_q;
    reg [DAW-1:0] desc_addr_q, run_base_q;
    reg [255:0] desc_data_q;
    reg [DAW:0] run_count_q;
    always @(posedge clk) begin desc_addr_q <= desc_addr; desc_data_q <= desc_data; run_base_q <= run_base; run_count_q <= run_count; end
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin desc_we_q <= 1'b0; run_q <= 1'b0; end
        else begin desc_we_q <= desc_we; run_q <= run_v; end
    // ---------------- go table (copy of the svg issuer's descriptor table)
    reg running, rd_q, ent_v;
    reg [DAW-1:0] rp, rp_q;
    reg [DAW:0] n_rd, n_go, n_done;
    reg [23:0] rc;
    reg [23:0] e_at; reg [PAW-1:0] e_base; reg [PAW:0] e_limit; reg [15:0] e_loops; reg [4:0] e_ctx;   // {mode3, mrel, fl}
    wire [255:0] rd;
    wire rd_go = running && n_rd != 0 && !ent_v && !rd_q;
    generate if (DD == 128) begin : g_t1
        ot_sram_1r1w_128x256_m1_r2c2 u_tab (.clk(clk), .r_ce_in(rd_go), .r_addr_in(rp[6:0]), .rd_out(rd),
            .w_ce_in(desc_we_q && !running), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end else begin : g_t2
        wire [255:0] rd_lo, rd_hi;
        ot_sram_1r1w_128x256_m1_r2c2 u_tab_lo (.clk(clk), .r_ce_in(rd_go && !rp[7]), .r_addr_in(rp[6:0]), .rd_out(rd_lo),
            .w_ce_in(desc_we_q && !running && !desc_addr_q[7]), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q),
            .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        ot_sram_1r1w_128x256_m1_r2c2 u_tab_hi (.clk(clk), .r_ce_in(rd_go && rp[7]), .r_addr_in(rp[6:0]), .rd_out(rd_hi),
            .w_ce_in(desc_we_q && !running && desc_addr_q[7]), .w_addr_in(desc_addr_q[6:0]), .wd_in(desc_data_q),
            .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        assign rd = rp_q[7] ? rd_hi : rd_lo;
    end endgenerate
    wire go = ent_v && rc == e_at;
    // Full native bank/core composition. Separate physical roots are explicit.
    wire cfg0_we,cfg1_we;wire [9:0] bank_cfg_addr;wire [255:0] bank_cfg_data;
    wire [66:0] request0,request1,token0,token1;wire [172:0] row0,row1;wire [10:0] ok0,ok1;
    wire [174:0] app_envelope;
    wire cal_active,cal_done,cal_fault;
    ot_smh_calendar_bank_leaf #(.W(173),.XW(5),.BANK(0),.MUT(BANKMUT)) u_bank0(
      .clk(clk_bank0),.rst_n(rst_q),.cfg_we(cfg0_we),.cfg_addr(bank_cfg_addr),.cfg_data(bank_cfg_data),
      .read_token(request0),.row(row0),.word_ok(ok0),.row_token(token0));
    ot_smh_calendar_bank_leaf #(.W(173),.XW(5),.BANK(1),.MUT(BANKMUT)) u_bank1(
      .clk(clk_bank1),.rst_n(rst_q),.cfg_we(cfg1_we),.cfg_addr(bank_cfg_addr),.cfg_data(bank_cfg_data),
      .read_token(request1),.row(row1),.word_ok(ok1),.row_token(token1));
    ot_smh_banked_xc_central #(.PREL(PREL),.CALMUT(CALMUT),.COMMANDALIGN(0),
      .CLASS_ENABLE(CLASS_ENABLE),.CLASS_MUT(CLASS_MUT)) u_app(
      .clk(clk),.rst_n(rst_q),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
      .start_v(go),.start_base(e_base),.start_limit(e_limit),.start_loops(e_loops),.start_ctx(e_ctx),
      .cfg0_we(cfg0_we),.cfg1_we(cfg1_we),.bank_cfg_addr(bank_cfg_addr),.bank_cfg_data(bank_cfg_data),
      .request0(request0),.request1(request1),.row0(row0),.row1(row1),.ok0(ok0),.ok1(ok1),.token0(token0),.token1(token1),
      .cmd_ext(),.kv_desc(),.command_envelope(app_envelope),.command_class_observe(),.command_context_valid_observe(),
      .active(cal_active),.done(cal_done),.fault(cal_fault));
    wire [174:0] envelope_to_mirror;
    generate if(MUT==4)begin:g_bypass_rc
      // Diagnostic-only raw calendar observer shares the two real bank outputs.
      // Its requests are identical to u_app.u_core; no extra programme SRAM.
      wire [172:0] raw_word;wire [66:0] raw_request0,raw_request1;
      ot_smh_calendar_banked_central #(.W(173),.AW(11),.XW(5)) u_raw(
        .clk(clk),.rst_n(rst_q),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(go),.start_base(e_base),.start_limit(e_limit),.start_loops(e_loops),.start_ctx(e_ctx),
        .cfg0_we(),.cfg1_we(),.bank_cfg_addr(),.bank_cfg_data(),.request0(raw_request0),.request1(raw_request1),
        .row0(row0),.row1(row1),.ok0(ok0),.ok1(ok1),.token0(token0),.token1(token1),
        .calendar(raw_word),.calendar_ctx(),.calendar_iter(),.calendar_lastit(),.calendar_v(),.ordinal(),
        .active(),.done(),.fault(),.app_reset_n(),.app_next_fault());
      assign envelope_to_mirror={app_envelope[174:173],raw_word};
    end else begin:g_normal_rc
      assign envelope_to_mirror=app_envelope;
    end endgenerate
    // Full175: preserve all64 KV bits, context valid/class, and all109 command bits.
    reg [174:0] mirror1,mirror2;
    always @(posedge clk)begin mirror1[173:0]<=envelope_to_mirror[173:0];mirror2[173:0]<=mirror1[173:0];end
    always @(posedge clk or negedge rst_q)
      if(!rst_q)begin mirror1[174]<=0;mirror2[174]<=0;end
      else begin mirror1[174]<=envelope_to_mirror[174];mirror2[174]<=mirror1[174];end
    wire [174:0] mirrored=MIRROR_MUT==1?mirror1:mirror2;
    wire [172:0] word=mirrored[172:0];
    assign cmd_ext=MUT==2?word[172:64]:word[108:0];
    assign kv_desc=MUT==2?word[63:0]:word[172:109];
    assign command_envelope={mirrored[174:173],kv_desc,cmd_ext};
    assign command_context_valid_observe=mirrored[174];
    assign command_class_observe=mirrored[173];
    // Align descriptor-origin status with calendar+2 before mirror tail+2.
    reg running1,running2,host_fault1,host_fault2,app_fault_q;
    reg active1,active2,done1,done2,fault1,fault2;
    wire fault_pre=host_fault2||app_fault_q;
    always @(posedge clk or negedge rst_q)begin
      if(!rst_q)begin
        running1<=0;running2<=0;host_fault1<=0;host_fault2<=0;app_fault_q<=0;
        active1<=0;active2<=0;done1<=0;done2<=0;fault1<=0;fault2<=0;
      end else begin
        running1<=running;running2<=running1;host_fault1<=host_fault;host_fault2<=host_fault1;
        app_fault_q<=app_fault_q||cal_fault;
        active1<=active_pre;active2<=active1;done1<=done_pre;done2<=done1;fault1<=fault_pre;fault2<=fault1;
      end
    end
    assign active=active2;assign done=done2;assign fault=fault2;
    always @(posedge clk or negedge rst_q) begin
        if (!rst_q) begin
            running <= 1'b0; rd_q <= 1'b0; ent_v <= 1'b0; rp <= 0; rp_q <= 0; n_rd <= 0; n_go <= 0; n_done<=0;
            rc <= 24'd0; e_at <= 24'd0; e_base <= 0; e_limit <= 0; e_loops <= 16'd0; e_ctx <= 5'd0;
            active_pre <= 1'b0; done_pre <= 1'b0; host_fault <= 1'b0;
        end else begin
            done_pre <= 1'b0;
            active_pre <= running2 || cal_active || n_done!=0;
            if (run_q) begin
                if (running || n_done!=0 || run_count_q == 0 || {1'b0, run_base_q} + run_count_q > DD) host_fault <= 1'b1;
                else begin
                    running <= 1'b1; rp <= run_base_q; n_rd <= run_count_q; n_go <= run_count_q; n_done<=0;
                    rc <= (MUT == 1) ? 24'd0 : 24'd1;
                end
            end else if (running) rc <= rc + 24'd1;
            rd_q <= rd_go; rp_q <= rp;
            if (rd_go) begin rp <= rp + 1'b1; n_rd <= n_rd - 1'b1; end
            if (rd_q) begin
                ent_v <= 1'b1;
                e_at <= rd[142:119]; e_base <= PAW'({rd[189], rd[91:82]}); e_limit <= (PAW+1)'({rd[190], rd[102:92]}); e_loops <= rd[118:103];
                e_ctx <= {rd[197:195], rd[198], rd[199]};
                if (rd[255:240] != 16'h5d15 || rd[232 +: DAW] != rp_q || (DAW == 7 && rd[239]) || rd[231:200] != 0) host_fault <= 1'b1;
            end
            if (go) begin
                ent_v <= 1'b0; n_go <= n_go - 1'b1;
                if (n_go == 1) running <= 1'b0;
            end
            if (ent_v && rc > e_at) host_fault <= 1'b1;            // missed compiler slot: never a late start
            case({go,cal_done})
              2'b10:n_done<=n_done+1'b1;
              2'b01:if(n_done!=0)n_done<=n_done-1'b1;
              default:begin end
            endcase
            // Unlike canonical cal_done&&!running, do not finish an earlier
            // programme after the final GO while later work remains outstanding.
            if(cal_done&&n_go==0&&n_done==1)done_pre<=1'b1;          // the run's last programme has issued its last word
        end
    end
endmodule
`default_nettype wire
