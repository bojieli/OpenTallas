`timescale 1ns/1ps
`default_nettype none
// Bench (H-SM svc helper 2026-10-16): the HARDENED xcal wrapper ot_hbm_svc_sm_xcal_t (ot_static_cmd_target MODE 0 folded
// in, TGT_PIN 1, strap 192) driven ONLY through the real host ingress (ot_hbm_host_static_ingress AXI-lite F20..F30), in
// LOCKSTEP with the actual svg go path behind its OWN collar (ot_static_cmd_target MODE 0, strap 64 -> ot_hbm_svc_sm_issuer
// FIXED_GO=1 -> ot_smh_calendar_static W135, as in ot_hbm_svc_sm_group).  The host writes each calendar's programme to its
// own window A, the SAME descriptor rows to both windows B, one descriptor per target, then one global launch (F30).
// Every output cycle {cmd_ext, sm_command} and kv_desc must belong to the same programme word (checks of
// tb_hbm_svc_sm_xcal).  -DMUT=0 PASS; 1 (late calendar), 2 (wrong field), 3 (reset never released), 4 (collar ignores the
// target id) FAIL.
module tb_hbm_svc_sm_xcal_t;
`ifndef MUT
`define MUT 0
`endif
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    // ---- host ingress
    reg awv = 0, wv = 0, arv = 0, rr = 1, br = 1; reg [11:0] awa = 0, ara = 0; reg [31:0] wd = 0;
    wire awr, wr, bv, arr, rv; wire [1:0] bresp; wire [31:0] rdata;
    wire cfg_v, desc_v, launch_v, ing_fault; wire [7:0] cfg_target; wire [11:0] cfg_addr, desc_base; wire [255:0] cfg_data;
    wire [12:0] desc_limit; wire [15:0] desc_loops;
    wire s_act, x_act;
    ot_hbm_host_static_ingress #(.TARGET_MASK((256'd1<<64)|(256'd1<<192))) ing(
        .clk(clk), .rst_n(rst_n), .s_awvalid(awv), .s_awready(awr), .s_awaddr(awa), .s_wvalid(wv), .s_wready(wr),
        .s_wdata(wd), .s_wstrb(4'hf), .s_bvalid(bv), .s_bready(br), .s_bresp(bresp), .s_arvalid(arv), .s_arready(arr),
        .s_araddr(ara), .s_rvalid(rv), .s_rready(rr), .s_rdata(rdata), .block_ready(1'b1), .program_active(s_act | x_act),
        .program_fault(1'b0), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .fault(ing_fault));
    // ---- svg collar + go path (issuer + programme calendar, as in the svg)
    wire cfg_we, desc_we, run_v, s_cfgd, s_flt; wire [9:0] cfg_addr_s; wire [255:0] cfg_data_s, desc_data;
    wire [6:0] desc_addr, run_base; wire [7:0] run_count;
    wire running, run_done, ifault, reserve_v, start_v, pstart_v;
    wire [31:0] rb; wire [14:0] rrb; wire [11:0] rt; wire [1:0] rbank, sbank; wire [15:0] re, se, ploops;
    wire [6:0] rrows; wire [9:0] rtag, pbase; wire [10:0] plimit;
    wire [134:0] programme; wire programme_v, p_active, p_done, p_fault; wire [31:0] ordinal;
    ot_static_cmd_target #(.TARGET(8'hff), .TGT_PIN(1), .MODE(0), .AWA(10), .AWB(7), .RBW(7), .RCW(8), .NA(2), .NF(1)) t_svg(
        .clk(clk), .tgt(8'd64), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .tgt_active({p_active, running}), .tgt_fault(ifault | p_fault),
        .a_we(cfg_we), .a_addr(cfg_addr_s), .a_data(cfg_data_s), .b_we(desc_we), .b_addr(desc_addr), .b_data(desc_data),
        .run_v(run_v), .run_base(run_base), .run_count(run_count), .cmd_v(), .cmd(), .cycle(),
        .configured(s_cfgd), .fault(s_flt), .active(s_act));
    ot_hbm_svc_sm_issuer #(.LBANKS(4), .FIXED_GO(1)) issuer (.clk(clk), .rst_n(rst_n), .desc_we(desc_we),
        .desc_addr(desc_addr), .desc_data(desc_data), .run_v(run_v), .run_base(run_base), .run_count(run_count),
        .running(running), .run_done(run_done), .fault(ifault), .reserve_v(reserve_v), .reserve_ready(1'b1),
        .reserve_base(rb), .reserve_row_base(rrb), .reserve_total(rt), .reserve_bank(rbank), .reserve_epoch(re),
        .reserve_rows(rrows), .reserve_tag_base(rtag), .block_ready(4'hf), .cache_ready(2'b11), .cache_owned(2'b00),
        .start_v(start_v), .start_bank(sbank), .start_epoch(se), .program_start_v(pstart_v),
        .program_start_base(pbase), .program_start_limit(plimit), .program_start_loops(ploops), .program_done(p_done));
    ot_smh_calendar_static #(.W(135)) svg_cal (.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr_s),
        .cfg_data(cfg_data_s), .start_v(pstart_v), .start_base(pbase), .start_limit(plimit), .start_loops(ploops),
        .calendar(programme), .calendar_v(programme_v), .ordinal(ordinal), .active(p_active), .done(p_done),
        .fault(p_fault));
    wire [82:0] sm_command = programme_v ? programme[82:0] : 83'd0;
    // ---- DUT: the hardened wrapper, strap 192
    wire [108:0] cmd_ext; wire [63:0] kv_desc; wire x_done, x_fault, x_cfgd;
    ot_hbm_svc_sm_xcal_t #(.MUT(`MUT)) dut (.clk(clk), .rst_n(rst_n), .tgt(8'd192), .cfg_v(cfg_v), .cfg_target(cfg_target),
        .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit),
        .desc_loops(desc_loops), .launch_v(launch_v), .cmd_ext(cmd_ext), .kv_desc(kv_desc), .done(x_done),
        .configured(x_cfgd), .fault(x_fault), .active(x_act));
    wire [191:0] command = {cmd_ext, sm_command};
    function automatic [255:0] sw(input [9:0] pc);
        sw = 0; sw[255:240] = 16'hc7a1; sw[233:224] = pc; sw[82] = 1'b1; sw[49:40] = pc; sw[2:0] = 3'b101;
    endfunction
    function automatic [255:0] xw(input [9:0] pc);
        reg [172:0] w;
        begin
            w = 0;
            w[108:101] = 8'ha2;                 // command[191:184]
            w[32] = 1'b1;                        // command[115] = kv load
            w[11:2] = pc;                        // pc identity in command[94:85] (BE control field, bench marker)
            w[172:109] = {16'd0, 16'(pc + 1), 32'h1000 + 32'(pc)};
            xw = 0; xw[255:240] = 16'hc7a1; xw[233:224] = pc; xw[172:0] = w;
        end
    endfunction
    function automatic [255:0] dw(input [6:0] row, input [9:0] b, input [10:0] l, input [15:0] lp, input [23:0] at,
                                  input [1:0] land);
        dw = 0; dw[255:240] = 16'h5d15; dw[239:233] = row; dw[31:0] = 32'h100 * row; dw[48:47] = land;
        dw[64:49] = 16'(row); dw[71:65] = 7'd1; dw[81:72] = 10'(row); dw[91:82] = b; dw[102:92] = l;
        dw[118:103] = lp; dw[142:119] = at;
    endfunction
    integer i, matched = 0, errors = 0, expect_words = 0, cyc = 0;
    reg [9:0] pcs, pcx;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if ((sm_command != 0) != (cmd_ext != 0)) begin
            errors = errors + 1;
            if (errors < 5) $display("MISALIGN cyc %0d svg %0d ext %0d", cyc, sm_command != 0, cmd_ext != 0);
        end else if (sm_command != 0) begin
            pcs = sm_command[49:40]; pcx = cmd_ext[11:2];
            if (command[191:184] != 8'ha2 || pcs != pcx || kv_desc != {16'd0, 16'(pcs + 1), 32'h1000 + 32'(pcs)} ||
                !command[115]) begin
                errors = errors + 1;
                if (errors < 5) $display("FIELD cyc %0d pc svg %0d ext %0d kv %h", cyc, pcs, pcx, kv_desc);
            end else matched = matched + 1;
        end
    end
    // ---- AXI write (as tb_static_cmd_target)
    task automatic axw(input [11:0] a, input [31:0] d);
        reg ad, dd;
        begin
            ad = 0; dd = 0; @(negedge clk); awv = 1; awa = a; wv = 1; wd = d;
            while (!(ad && dd)) begin
                begin : HS reg ha, hw; ha = awv && awr; hw = wv && wr;
                @(posedge clk); #0.01; if (ha) begin ad = 1; awv = 0; end if (hw) begin dd = 1; wv = 0; end end
                @(negedge clk);
            end
            while (!bv) @(posedge clk);
            if (bresp != 0) begin $display("ERROR bresp %0d at %h data %h", bresp, a, d); errors = errors + 1; end
            @(posedge clk);
        end
    endtask
    task automatic row(input [7:0] t, input [11:0] addr, input [255:0] data);
        begin
            axw(12'hf20, {12'd0, addr, t});
            for (integer p = 0; p < 8; p = p + 1) axw(12'hf24, data[p*32 +: 32]);
        end
    endtask
    task automatic desc(input [7:0] t, input [11:0] base, input [12:0] lim, input [15:0] loops);
        begin axw(12'hf20, {12'd0, 12'd0, t}); axw(12'hf28, {7'd0, lim, base}); axw(12'hf2c, {16'd0, loops}); end
    endtask
    task automatic idle_wait;
        begin repeat (8) @(posedge clk); while (s_act || x_act) @(posedge clk); repeat (8) @(posedge clk); end
    endtask
    initial begin : TMO #4000000; $display("XCAL_T_LOCKSTEP FAIL timeout"); $finish; end
    initial begin
        repeat (5) @(posedge clk); rst_n = 1; repeat (5) @(posedge clk);
        for (i = 0; i < 64; i = i + 1) begin row(8'd192, 12'(i), xw(i)); row(8'd64, 12'(i), sw(i)); end   // svg rows LAST: MUT 4 (id ignored) must end with them
        // descriptor table rows 0..4 (same rows to both windows B)
        row(8'd64, 12'h400, dw(0, 0, 5, 2, 40, 0));   row(8'd192, 12'h400, dw(0, 0, 5, 2, 40, 0));
        row(8'd64, 12'h401, dw(1, 10, 13, 1, 80, 1)); row(8'd192, 12'h401, dw(1, 10, 13, 1, 80, 1));
        row(8'd64, 12'h402, dw(2, 20, 24, 3, 120, 2)); row(8'd192, 12'h402, dw(2, 20, 24, 3, 120, 2));
        row(8'd64, 12'h403, dw(3, 30, 38, 1, 30, 3)); row(8'd192, 12'h403, dw(3, 30, 38, 1, 30, 3));
        row(8'd64, 12'h404, dw(4, 40, 41, 5, 47, 0)); row(8'd192, 12'h404, dw(4, 40, 41, 5, 47, 0));
        // run A: rows [0,3) on one global launch
        desc(8'd64, 12'd0, 13'd3, 16'd1); desc(8'd192, 12'd0, 13'd3, 16'd1);
        if (s_flt || x_fault || ing_fault) begin errors = errors + 1; $display("ERROR fault before launch"); end
        repeat (10) @(posedge clk); axw(12'hf30, 32'd1); expect_words = expect_words + 5 * 2 + 3 + 4 * 3;
        idle_wait;
        // run B: rows [3,5)
        desc(8'd64, 12'd3, 13'd5, 16'd1); desc(8'd192, 12'd3, 13'd5, 16'd1);
        repeat (10) @(posedge clk); axw(12'hf30, 32'd1); expect_words = expect_words + 8 + 5;
        idle_wait;
        $display("words matched %0d / expected %0d, errors %0d, faults svg collar %0d issuer %0d cal %0d xcal_t %0d ingress %0d",
                 matched, expect_words, errors, s_flt, ifault, p_fault, x_fault, ing_fault);
        if (errors == 0 && matched == expect_words && !s_flt && !ifault && !p_fault && !x_fault && !ing_fault)
            $display("XCAL_T_LOCKSTEP PASS mut=%0d", `MUT);
        else $display("XCAL_T_LOCKSTEP FAIL mut=%0d", `MUT);
        $finish;
    end
endmodule
`default_nettype wire
