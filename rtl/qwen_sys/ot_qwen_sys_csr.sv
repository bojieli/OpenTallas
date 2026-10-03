`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_sys_csr: system status, fault aggregation and the host register
// split of the Qwen ROM system top.  NEW.
//
// Host register space (AXI4-Lite, 13-bit byte address, one transaction at a
// time, the ot_host_if handshake): [12] = 0 -> ot_host_if (its 4 KB BAR,
// unchanged); [12] = 1 -> these registers:
//   1000 SYS_ID "QSYS"
//   1004 SYS_STATUS  [0] sys_ready [1] boot_fault [7:4] boot_state [11:8] boot_err
//   1008 SYS_CTRL    [0] soft reset (self-clearing pulse to the reset sequencer)
//   1010 FAULT_STATUS sticky per source, write 1 to clear
//   1014 FAULT_MASK  interrupt enable per source
//   1018 FAULT_FIRST [31] valid [4:0] the first source to fault since FAULT_STATUS was last all clear
//   101C FAULT_RAW   the sources' current levels
//   1020 + 4 i       NCNT counters (cnt[32 i +: 32]), read-only
// Fault sources: see ot_qwen_rom_sys_top (FS_* bit map).  irq = host_if irq
// OR any (FAULT_STATUS & FAULT_MASK): a fault reaches the host as an interrupt
// with a register that names the failing block.
// ---------------------------------------------------------------------------
module ot_qwen_sys_csr #(
    parameter integer NCNT = 16
) (
    input  wire               clk,
    input  wire               rst_n,
    // host AXI4-Lite (13-bit address)
    input  wire               s_awvalid,
    output wire               s_awready,
    input  wire [12:0]        s_awaddr,
    input  wire               s_wvalid,
    output wire               s_wready,
    input  wire [31:0]        s_wdata,
    input  wire [3:0]         s_wstrb,
    output wire               s_bvalid,
    input  wire               s_bready,
    output wire [1:0]         s_bresp,
    input  wire               s_arvalid,
    output wire               s_arready,
    input  wire [12:0]        s_araddr,
    output wire               s_rvalid,
    input  wire               s_rready,
    output wire [31:0]        s_rdata,
    output wire [1:0]         s_rresp,
    // to / from ot_host_if (12-bit BAR)
    output wire               h_awvalid,
    input  wire               h_awready,
    output wire [11:0]        h_awaddr,
    output wire               h_wvalid,
    input  wire               h_wready,
    output wire [31:0]        h_wdata,
    output wire [3:0]         h_wstrb,
    input  wire               h_bvalid,
    output wire               h_bready,
    output wire               h_arvalid,
    input  wire               h_arready,
    output wire [11:0]        h_araddr,
    input  wire               h_rvalid,
    output wire               h_rready,
    input  wire [31:0]        h_rdata,
    input  wire               h_irq,
    // system state
    input  wire               sys_ready,
    input  wire               boot_fault,
    input  wire [3:0]         boot_state,
    input  wire [3:0]         boot_err,
    output reg                soft_rst,
    input  wire [31:0]        fault_src,
    input  wire [NCNT*32-1:0] cnt,
    output wire               irq
);
    // ---- split
    wire aw_hi = s_awaddr[12];
    wire ar_hi = s_araddr[12];
    reg  c_bvalid, c_rvalid;
    reg  alive;                         // AXI: no handshake while in reset
    always @(posedge clk or negedge rst_n) if (!rst_n) alive <= 1'b0; else alive <= 1'b1;
    reg  [31:0] c_rdata;
    wire c_wr_go = alive && s_awvalid && s_wvalid && aw_hi && !c_bvalid && !h_bvalid;
    wire c_rd_go = alive && s_arvalid && ar_hi && !c_rvalid && !h_rvalid;
    assign h_awvalid = alive && s_awvalid && !aw_hi;
    assign h_wvalid  = alive && s_wvalid && !aw_hi;
    assign h_awaddr  = s_awaddr[11:0];
    assign h_wdata   = s_wdata;
    assign h_wstrb   = s_wstrb;
    assign h_bready  = s_bready;
    assign h_arvalid = alive && s_arvalid && !ar_hi;
    assign h_araddr  = s_araddr[11:0];
    assign h_rready  = s_rready;
    assign s_awready = aw_hi ? c_wr_go : (alive && h_awready);
    assign s_wready  = aw_hi ? c_wr_go : (alive && h_wready);
    assign s_bvalid  = c_bvalid | h_bvalid;
    assign s_bresp   = 2'b00;
    assign s_arready = ar_hi ? c_rd_go : (alive && h_arready);
    assign s_rvalid  = c_rvalid | h_rvalid;
    assign s_rdata   = c_rvalid ? c_rdata : h_rdata;
    assign s_rresp   = 2'b00;

    // ---- registers
    reg [31:0] f_status, f_mask;
    reg        f_first_v;
    reg [4:0]  f_first;
    assign irq = h_irq | (|(f_status & f_mask));
    reg [4:0] lowest;
    reg       any_new;
    integer i;
    wire [31:0] new_f = fault_src & ~f_status;
    always @(*) begin
        lowest = 0; any_new = 1'b0;
        for (i = 31; i >= 0; i = i - 1) if (new_f[i]) begin lowest = i[4:0]; any_new = 1'b1; end
    end
    reg [31:0] rmux;
    always @(*) begin
        case (s_araddr[11:2])
            10'h000: rmux = 32'h5153_5953;   // "QSYS"
            10'h001: rmux = {20'd0, boot_err, boot_state, 2'd0, boot_fault, sys_ready};
            10'h002: rmux = 32'd0;
            10'h004: rmux = f_status;
            10'h005: rmux = f_mask;
            10'h006: rmux = {f_first_v, 26'd0, f_first};
            10'h007: rmux = fault_src;
            default: rmux = (s_araddr[11:2] >= 10'h008 && s_araddr[11:2] < 10'h008 + NCNT)
                            ? cnt[32*(s_araddr[11:2] - 10'h008) +: 32] : 32'd0;
        endcase
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            c_bvalid <= 1'b0; c_rvalid <= 1'b0; c_rdata <= 0;
            f_status <= 0; f_mask <= 0; f_first_v <= 1'b0; f_first <= 0; soft_rst <= 1'b0;
        end else begin
            soft_rst <= 1'b0;
            if (c_bvalid && s_bready) c_bvalid <= 1'b0;
            if (c_rvalid && s_rready) c_rvalid <= 1'b0;
            if (c_rd_go) begin c_rvalid <= 1'b1; c_rdata <= rmux; end
            // sticky capture first, then W1C (a source still faulting re-latches next cycle)
            f_status <= f_status | fault_src;
            if (any_new && !f_first_v) begin f_first_v <= 1'b1; f_first <= lowest; end
            if (c_wr_go) begin
                c_bvalid <= 1'b1;
                case (s_awaddr[11:2])
                    10'h002: soft_rst <= s_wdata[0];
                    10'h004: begin
                        f_status <= (f_status | fault_src) & ~s_wdata;
                        if (((f_status | fault_src) & ~s_wdata) == 0) f_first_v <= 1'b0;
                    end
                    10'h005: f_mask <= s_wdata;
                    default: ;
                endcase
            end
        end
    end
endmodule
