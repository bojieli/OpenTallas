"""Native scheduled row transport; applied after legacy controller generation."""

def apply(text):
    old = "                S_COLL: begin\n                    // queue: vector-memory words read one cycle earlier; pop on send\n                    if (rd_go) rd_k <= rd_k + 1'b1;\n"
    new = "                S_COLL: begin\n                    // Queue actual completed rows; outstanding slot reserves capacity.\n                    if (rd_go) rd_k <= rd_k + 1'b1;\n"
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '            rd_p <= (VRL > 1) ? {rd_p, rd_go} : rd_go;\n            case (st)\n'
    new = "            rd_p <= (VRL > 1) ? {rd_p, rd_go} : rd_go;\n            if (rd_go) rd_pending <= 1'b1;\n            if (rd_v) rd_pending <= 1'b0;\n            if ((VARIABLE == 0 && vm_rvalid != rd_expected) ||\n                (vm_rvalid && (!rd_expected || st != S_COLL || kind != K_AR))) fault <= 1'b1;\n            case (st)\n"
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = "            vm_we <= 1'b0; vm_waddr <= 0;\n            q_w <= 0; q_r <= 0; q_n <= 0; rd_k <= 0; tx_k <= 0; rx_k <= 0; rd_p <= {VRL{1'b0}};\n            best_i <= 0; best_v <= 0;\n"
    new = "            vm_we <= 1'b0; vm_waddr <= 0;\n            q_w <= 0; q_r <= 0; q_n <= 0; rd_k <= 0; tx_k <= 0; rx_k <= 0; rd_pending <= 1'b0; rd_p <= 0;\n            best_i <= 0; best_v <= 0;\n"
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = "        else if (CRED != 0) c_cred <= c_cred - (c_fire ? 8'd1 : 8'd0) + (c_ready ? 8'd1 : 8'd0);\n    wire   rd_go   = (st == S_COLL) && kind == K_AR && rd_k < nw && (q_n + rd_n) < QD;\n\n"
    new = "        else if (CRED != 0) c_cred <= c_cred - (c_fire ? 8'd1 : 8'd0) + (c_ready ? 8'd1 : 8'd0);\n    wire   rd_go   = (st == S_COLL) && kind == K_AR && rd_k < nw && ((VARIABLE != 0) ? (!rd_pending && q_n < QD) : ((q_n + rd_n) < QD));\n\n"
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = "    assign c_last  = (tx_k == ((kind == K_ARGMAX) ? 9'd0 : nw - 1'b1));\n    wire   c_fire  = c_valid && ((CRED == 0) ? c_ready : 1'b1);\n    always @(posedge clk or negedge rst_n)\n"
    new = "    assign c_last  = (tx_k == ((kind == K_ARGMAX) ? 9'd0 : nw - 1'b1));\n    wire   c_fire  = c_valid && ((STATIC != 0 || CRED != 0) ? 1'b1 : c_ready);\n    always @(posedge clk or negedge rst_n)\n"
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = "    reg [7:0] c_cred;   // credit mode: a word leaves only with a credit (valid = send)\n    assign c_valid = (st == S_COLL) && (q_n != 0) && (CRED == 0 || c_cred != 8'd0);\n    assign c_data  = q_d[q_r];\n"
    new = "    reg [7:0] c_cred;   // credit mode: a word leaves only with a credit (valid = send)\n    assign c_valid = (st == S_COLL) && (q_n != 0) && (STATIC != 0 || CRED == 0 || c_cred != 8'd0);\n    assign c_data  = q_d[q_r];\n"
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '    reg [8:0]    rd_k, tx_k, rx_k;\n    reg [VRL-1:0] rd_p;                 // reads in flight, oldest at VRL-1\n    wire          rd_v = rd_p[VRL-1];\n    integer       rd_i, rd_n;\n    always @(*) begin rd_n = 0; for (rd_i = 0; rd_i < VRL; rd_i = rd_i + 1) rd_n = rd_n + rd_p[rd_i]; end\n    reg [7:0] c_cred;   // credit mode: a word leaves only with a credit (valid = send)\n'
    new = '    reg [8:0]    rd_k, tx_k, rx_k;\n    reg [VRL-1:0] rd_p;\n    integer rd_i, rd_n;\n    always @(*) begin rd_n = 0; for (rd_i=0; rd_i<VRL; rd_i=rd_i+1) rd_n=rd_n+rd_p[rd_i]; end\n    reg rd_pending;\n    wire rd_expected = (VARIABLE != 0) ? rd_pending : rd_p[VRL-1];\n    wire rd_v = vm_rvalid && rd_expected;\n    reg [7:0] c_cred;   // credit mode: a word leaves only with a credit (valid = send)\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '    input  wire [FW-1:0]     vm_rq,\n    output reg               vm_we,\n'
    new = '    input  wire [FW-1:0]     vm_rq,\n    input  wire              vm_rvalid,\n    output reg               vm_we,\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = 'module ot_qwen_tp_seq_w12_vrl #(\n    parameter integer VRL = 1,     // vre -> vrq edges\n    parameter integer RMUT = 0,    // el1011-q-seq negative control: vm_wdata bit 0 flipped on the AR write\n'
    new = 'module ot_qwen_tp_seq_w12_vrl #(\n    parameter integer VRL = 1,     // scheduled request -> actual response edges\n    parameter integer VARIABLE = 0, // diagnostic only; absent from production hierarchy\n    parameter integer STATIC = 1, // fixed collective send slots, no runtime credit or readiness\n    parameter integer RMUT = 0,    // el1011-q-seq negative control: vm_wdata bit 0 flipped on the AR write\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '        .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q), .vm_re(b_vm_re), .vm_raddr(b_vm_raddr),\n        .vm_rq(q_vm_rq), .vm_we(b_vm_we), .vm_waddr(b_vm_waddr), .vm_wdata(b_vm_wdata), .c_valid(b_c_valid),\n        .c_ready(q_c_ready), .c_data(b_c_data), .c_last(b_c_last), .c_mode(b_c_mode), .c_tag(b_c_tag),\n'
    new = '        .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q), .vm_re(b_vm_re), .vm_raddr(b_vm_raddr),\n        .vm_rq(q_vm_rq), .vm_rvalid(q_vm_rvalid), .vm_we(b_vm_we), .vm_waddr(b_vm_waddr), .vm_wdata(b_vm_wdata), .c_valid(b_c_valid),\n        .c_ready(q_c_ready), .c_data(b_c_data), .c_last(b_c_last), .c_mode(b_c_mode), .c_tag(b_c_tag),\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '    ot_hdc_delay #(.W(6 + 1 + NW), .D(OS)) u_o_cb (.clk(clk), .rst_n(rsv[6]), .d({sg_stage, sg_tok, q_tp_pos}), .q({cb_stage, cb_tok_start, cb_tpos}));\n    ot_qwen_tp_seq_w12_vrl #(.VRL(IS + OS + 1 + 2 * RLY), .CRED(CRED), .N(D), .NW(NW), .PAW(PAW), .VWA(VWA), .VM_ADDR_EXT(VWA > 8), .DAW(6), .FW(512), .TAGW(32),\n        .QWEN_FULLSHAPE(1), .ENABLE_AR256(1), .RMUT(RRG >= 2 ? 1 : 0)) u_seq (\n'
    new = '    ot_hdc_delay #(.W(6 + 1 + NW), .D(OS)) u_o_cb (.clk(clk), .rst_n(rsv[6]), .d({sg_stage, sg_tok, q_tp_pos}), .q({cb_stage, cb_tok_start, cb_tpos}));\n    ot_qwen_tp_seq_w12_vrl #(.VRL(IS + OS + ROW_LAT + 2 * RLY), .VARIABLE(0), .STATIC(1), .CRED(CRED), .N(D), .NW(NW), .PAW(PAW), .VWA(VWA), .VM_ADDR_EXT(VWA > 8), .DAW(6), .FW(512), .TAGW(32),\n        .QWEN_FULLSHAPE(1), .ENABLE_AR256(1), .RMUT(RRG >= 2 ? 1 : 0)) u_seq (\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_vm_re (.clk(clk), .rst_n(rsv[6]), .d(b_vm_re), .q(vm_re));\n    wire [VWA-1:0] b_vm_raddr;\n    ot_hdc_delay #(.W(VWA), .D(OS)) u_o_vm_raddr (.clk(clk), .rst_n(rsv[6]), .d(b_vm_raddr), .q(vm_raddr));\n'
    new = '    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_vm_re (.clk(clk), .rst_n(rsv[6]), .d(b_vm_re), .q(vm_re));\n    ot_hdc_delay #(.W(VWA), .D(OS)) u_o_vm_raddr (.clk(clk), .rst_n(rsv[6]), .d(b_vm_raddr), .q(vm_raddr));\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '    wire [1-1:0] b_vm_re;\n    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_vm_re (.clk(clk), .rst_n(rsv[6]), .d(b_vm_re), .q(vm_re));\n'
    new = '    wire [1-1:0] b_vm_re;\n    wire [VWA-1:0] b_vm_raddr;\n    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_o_vm_re (.clk(clk), .rst_n(rsv[6]), .d(b_vm_re), .q(vm_re));\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '    ot_hdc_delay #(.W(512), .D(IS)) u_i_vm_rq (.clk(clk), .rst_n(rsv[5]), .d(vm_rq), .q(q_vm_rq));\n    wire [1-1:0] q_c_ready;\n'
    new = '    ot_hdc_delay #(.W(512), .D(IS)) u_i_vm_rq (.clk(clk), .rst_n(rsv[5]), .d(vm_rq), .q(q_vm_rq));\n    wire q_vm_rvalid;\n    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_vm_rvalid (.clk(clk), .rst_n(rsv[5]), .d(vm_rvalid), .q(q_vm_rvalid));\n    wire [1-1:0] q_c_ready;\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '    input  wire [512-1:0] vm_rq,\n    input  wire [1-1:0] c_ready,\n'
    new = '    input  wire [512-1:0] vm_rq,\n    input  wire vm_rvalid, // actual completed row, aligned with vm_rq\n    input  wire [1-1:0] c_ready,\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    old = '    parameter integer RLY = 0, parameter integer CRED = 0,\n    parameter integer VWA = 20,\n'
    new = '    parameter integer RLY = 0, parameter integer CRED = 0,\n    parameter integer ROW_LAT = 13, // measured NOX native row response latency\n    parameter integer VWA = 20,\n'
    if text.count(old) != 1:
        raise ValueError("row transport generator anchor missing: " + old[:100])
    text = text.replace(old, new, 1)
    text = text.replace("else if (CRED != 0) c_cred <=", "else if (STATIC == 0 && CRED != 0) c_cred <=", 1)
    text = text.replace("localparam integer QB = (VRL > 1) ? $clog2(VRL + 4) : 2;", "localparam integer QB = (STATIC != 0) ? 2 : ((VRL > 1) ? $clog2(VRL + 4) : 2);", 1)
    text = text.replace(": ((q_n + rd_n) < QD));", ": (STATIC != 0 || (q_n + rd_n) < QD));", 1)
    return text + "\n// Hardened controller-owned row request station. Register at the actual pin;\n// preserve valid/address until external admission, never infer it upstream.\nmodule ot_qfd_row_request_pin #(parameter integer AW=20, OS=1)(\n    input wire clk, rst_n, request, input wire [AW-1:0] addr,\n    input wire ready, output reg valid, output reg [AW-1:0] pin_addr,\n    output wire pending);\n    wire request_d; wire [AW-1:0] addr_d;\n    ot_hdc_delay #(.W(1), .D(OS), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(request), .q(request_d));\n    ot_hdc_delay #(.W(AW), .D(OS)) u_a (.clk(clk), .rst_n(rst_n), .d(addr), .q(addr_d));\n    assign pending = valid;\n    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin valid <= 1'b0; pin_addr <= 0; end\n        else begin\n            if (valid && ready) valid <= 1'b0;\n            if (request_d) begin valid <= 1'b1; pin_addr <= addr_d; end\n        end\n    end\nendmodule\n"
