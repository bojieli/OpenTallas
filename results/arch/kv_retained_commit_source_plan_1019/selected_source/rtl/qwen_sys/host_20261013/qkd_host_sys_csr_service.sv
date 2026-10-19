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
module qkd_host_sys_csr_service #(
    parameter integer ENABLE_SERVICE=0,MUT_EPOCH=0,
    parameter integer NCNT = 16,
    parameter integer MUT_DIAG = 0
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
    input wire [31:0] die_fault_vec,
    input wire [79:0] die_kst,
    input  wire [NCNT*32-1:0] cnt,
    output wire               irq,
 input wire  por_n,
 input wire  begin_tx_cr,
 input wire  begin_tx_available,
 input wire [7:0] service_ready8,
 input wire [7:0] pending_ack8,
 input wire [127:0] service_epoch8,
 input wire  service_fault,
 input wire  ingest_permission,
 output reg  begin_v,
 output reg [15:0] begin_epoch,
 output reg  begin_available,
 output reg  begin_fault,
 input wire decode_request,decode_start,decode_done,
 output reg epoch_busy,startup_allowed
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

    reg[15:0]allocated_epoch;
    reg broadcast_complete,decode_busy,decode_armed;
    wire begin_write=c_wr_go&&s_awaddr[11:2]==10'h028&&s_wstrb[0]&&s_wdata[0];
    wire allocate=ENABLE_SERVICE&&begin_write&&begin_available&&!epoch_busy&&!begin_fault&&!decode_busy&&!decode_request&&!decode_start&&(MUT_EPOCH==1||allocated_epoch!=16'hffff);
    reg match_epochs;integer ei;
    always @*begin
      match_epochs=1;
      for(ei=0;ei<8;ei=ei+1)if(service_epoch8[16*ei+:16]!=begin_epoch)match_epochs=0;
    end
    // Epoch allocation survives host soft reset. POR remains the cold boundary;
    // cold reset requires actual link/FIFO flush before reused cold epoch data.
    always @(posedge clk or negedge por_n)if(!por_n)allocated_epoch<=0;
      else if(rst_n&&allocate)allocated_epoch<=allocated_epoch+1'b1;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin
      begin_v<=0;begin_epoch<=0;begin_available<=0;begin_fault<=0;epoch_busy<=0;broadcast_complete<=0;decode_busy<=0;decode_armed<=0;startup_allowed<=0;
    end else begin
      begin_v<=0;startup_allowed<=allocated_epoch==0;
      if(!decode_done)decode_armed<=1;
      if(decode_busy&&decode_armed&&decode_done)decode_busy<=0;
      if(decode_request||decode_start)begin decode_busy<=1;decode_armed<=0;end
      begin_available<=ENABLE_SERVICE&&!epoch_busy&&!decode_busy&&!decode_request&&!decode_start&&!begin_fault&&begin_tx_available&&(MUT_EPOCH==1||allocated_epoch!=16'hffff);
      if(ENABLE_SERVICE&&service_fault)begin_fault<=1;
      if(ENABLE_SERVICE&&begin_write)begin
        if(!allocate)begin_fault<=1;
        else begin begin_v<=1;begin_epoch<=allocated_epoch+1'b1;epoch_busy<=1;broadcast_complete<=0;begin_available<=0;end
      end
      if(begin_tx_cr&&epoch_busy)broadcast_complete<=1;
      if(epoch_busy&&broadcast_complete&&(&service_ready8)&&(&pending_ack8)&&match_epochs&&!service_fault)epoch_busy<=0;
    end
    // ---- registers
    reg [31:0] f_status, f_mask;
    reg [31:0] diag_status, diag_mask;
    reg        f_first_v;
    reg [4:0]  f_first;
    assign irq = h_irq | (|(f_status & f_mask)) | (|(diag_status & diag_mask));
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
            10'h028: rmux = ENABLE_SERVICE?{10'b0,begin_fault,broadcast_complete,epoch_busy,begin_available,2'b0,begin_epoch}:32'b0; //10a0 BEGIN/status
            10'h029: rmux = ENABLE_SERVICE?{15'b0,ingest_permission,pending_ack8,service_ready8}:32'b0; //10a4
            10'h02a: rmux = ENABLE_SERVICE?service_epoch8[31:0]:32'b0;
            10'h02b: rmux = ENABLE_SERVICE?service_epoch8[63:32]:32'b0;
            10'h02c: rmux = ENABLE_SERVICE?service_epoch8[95:64]:32'b0;
            10'h02d: rmux = ENABLE_SERVICE?service_epoch8[127:96]:32'b0;
            10'h020: rmux = diag_status; // 1080: all eight dies, 4 bits each
            10'h021: rmux = diag_mask;
            10'h022: rmux = die_fault_vec;
            10'h023: rmux = 32'h0008_0004; // eight dies, four mapped causes each
            10'h024: rmux = die_kst[31:0]; //1090: raw merged KV cause10 per die
            10'h025: rmux = die_kst[63:32];
            10'h026: rmux = {16'b0,die_kst[79:64]};
            default: rmux = (s_araddr[11:2] >= 10'h008 && s_araddr[11:2] < 10'h008 + NCNT)
                            ? cnt[32*(s_araddr[11:2] - 10'h008) +: 32] : 32'd0;
        endcase
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            c_bvalid <= 1'b0; c_rvalid <= 1'b0; c_rdata <= 0;
            diag_status <= 0; diag_mask <= 0;
            f_status <= 0; f_mask <= 0; f_first_v <= 1'b0; f_first <= 0; soft_rst <= 1'b0;
        end else begin
            soft_rst <= 1'b0;
            if (c_bvalid && s_bready) c_bvalid <= 1'b0;
            if (c_rvalid && s_rready) c_rvalid <= 1'b0;
            if (c_rd_go) begin c_rvalid <= 1'b1; c_rdata <= rmux; end
            // sticky capture first, then W1C (a source still faulting re-latches next cycle)
            f_status <= f_status | fault_src;
            diag_status <= diag_status | ((MUT_DIAG!=0)?{16'b0,die_fault_vec[15:0]}:die_fault_vec);
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
                    10'h020: diag_status <= (diag_status | die_fault_vec) & ~s_wdata;
                    10'h021: diag_mask <= s_wdata;
                    default: ;
                endcase
            end
        end
    end
endmodule
