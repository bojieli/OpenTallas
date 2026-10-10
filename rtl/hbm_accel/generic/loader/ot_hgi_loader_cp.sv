`timescale 1ns/1ps
`default_nettype none
// HGI-1 host <-> command processor registers in the loader (hgi-takeover 2026-10-09; die gap 4a).
//
// The host reaches the die over the loader's AXI-lite slave (s_*, 12-bit byte address).  This block claims the window
// 0xC00-0xDFF in front of the loader core (every other address passes through unchanged):
//   0xC00 W  doorbell token [17:0]          0xC04 W  doorbell pos [19:0]       0xC08 W  doorbell job [31:0]
//   0xC0C W  {ncol [11:8], entry [5:4], gen [3:0]}       0xC10 W  RING: the staged doorbell goes to the CP (refused while one is
//                                                     pending: read 0xC20 bit 0)
//   0xC14 W  die id (rank) [7:0]
//   0xC20 R  {cpl_count [10:8], db_pending [0]}   0xC24 R {cfg_err [3:1], cfg_loaded [0]}   0xC28 / 0xC2C R cfg_cp_act lo / hi
//   0xC40 R  cpl token  0xC44 R cpl pos  0xC48 R cpl job  0xC4C R {tokx [8], status [7:4], gen [3:0]}
//            (tokx = 1: a CTL.TOKX committed-token beat {token, pos + i - 1, status 0}; END's completion follows)
//   0xC50 R  cpl cycles; READING 0xC50 POPS the completion (read the other fields first)
//   0xD00 + 8a / +4  W  CFG window pair a (0..31): low word, then high word; the high-word write sends
//                      {window, a, {hi, lo}} to the CP host port (a = 31: CFG_COMMIT)
// Command-processor link (die buses, relay-tolerant: pulses + one-entry stations on both sides):
//   lcp (loader -> CP, 419 b, bit 0 first) = cfg_we [0], cfg_addr [6:1], cfg_wdata [70:7], db_v [71], db_token [89:72],
//       db_pos [109:90], db_job [141:110], db_gen [145:142], db_entry [147:146], cpl_ack [148], f_rsp_v [149],
//       f_rsp_data [405:150], f_req_ack [406], rank [414:407] (die id, host-written at 0xC14),
//       db_ncol [418:415]
//   cpl (CP -> loader, 222 b) = db_taken [0], cpl_v [1], cpl_token [19:2], cpl_pos [39:20], cpl_job [71:40], cpl_gen [75:72],
//       cpl_status [79:76], cpl_cycles [111:80], cpl_tokx [112], f_req_v [113], f_req_addr [153:114],
//       cfg_loaded [154], cfg_err [157:155], cfg_cp_act [221:158] (CF-0 read-back)
// The record-ring fetch (f_req / f_rsp) rides the loader's memory lane 1 (ot_hfd_loader_kport), read only.
module ot_hgi_loader_cp #(
    parameter integer CPL_DEPTH = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    // host AXI-lite from the die host link
    input  wire          s_awvalid, output wire s_awready, input wire [11:0] s_awaddr,
    input  wire          s_wvalid,  output wire s_wready,  input wire [31:0] s_wdata, input wire [3:0] s_wstrb,
    output wire          s_bvalid,  input  wire s_bready,
    input  wire          s_arvalid, output wire s_arready, input wire [11:0] s_araddr,
    output wire          s_rvalid,  input  wire s_rready,  output wire [31:0] s_rdata,
    // to the loader core's AXI-lite slave
    output wire          c_awvalid, input  wire c_awready, output wire [11:0] c_awaddr,
    output wire          c_wvalid,  input  wire c_wready,  output wire [31:0] c_wdata, output wire [3:0] c_wstrb,
    input  wire          c_bvalid,  output wire c_bready,
    output wire          c_arvalid, input  wire c_arready, output wire [11:0] c_araddr,
    input  wire          c_rvalid,  output wire c_rready,  input  wire [31:0] c_rdata,
    // command-processor link
    output reg  [418:0]  lcp,
    input  wire [221:0]  cpl,
    // record-ring fetch on memory lane 1 (to ot_hfd_loader_kport)
    output reg           m_req_v, input wire m_req_rdy, output reg [36:0] m_req_addr,
    input  wire          m_rsp_v, input wire [255:0] m_rsp_data,
    output reg           fault
);
    // ---------------------------------------------------------------- AXI-lite window split
    wire w_loc = s_awaddr[11:9] == 3'b110;               // 0xC00-0xDFF
    wire r_loc = s_araddr[11:9] == 3'b110;
    reg  lb_v; reg lr_v; reg [31:0] lr_d;
    wire lw_take = s_awvalid && s_wvalid && w_loc && !lb_v;  // local write: address and data together
    assign s_awready = w_loc ? lw_take : c_awready;
    assign s_wready  = w_loc ? lw_take : c_wready;
    assign c_awvalid = s_awvalid && !w_loc; assign c_awaddr = s_awaddr;
    assign c_wvalid  = s_wvalid && !w_loc;  assign c_wdata = s_wdata; assign c_wstrb = s_wstrb;
    assign s_bvalid  = lb_v | c_bvalid;
    assign c_bready  = s_bready && !lb_v;
    wire lr_take = s_arvalid && r_loc && !lr_v;
    assign s_arready = r_loc ? lr_take : c_arready;
    assign c_arvalid = s_arvalid && !r_loc; assign c_araddr = s_araddr;
    assign s_rvalid  = lr_v | c_rvalid;
    assign s_rdata   = lr_v ? lr_d : c_rdata;
    assign c_rready  = s_rready && !lr_v;
    // ---------------------------------------------------------------- doorbell / CFG staging, completion FIFO
    reg [17:0] d_tok; reg [19:0] d_pos; reg [31:0] d_job; reg [3:0] d_gen; reg [1:0] d_ent; reg [3:0] d_ncol; reg db_pend;
    reg [31:0] cfg_lo [0:31];
    localparam integer CW = 18 + 20 + 32 + 4 + 4 + 32 + 1;   // 111
    reg [CW-1:0] cq [0:CPL_DEPTH-1];
    reg [2:0] cq_n; reg [1:0] cq_h, cq_t;
    wire [CW-1:0] head = cq[cq_h];
    // completion fields of the head entry: {tokx 1, cycles 32, status 4, gen 4, job 32, pos 20, token 18}
    wire [17:0] h_tok = head[17:0];    wire [19:0] h_pos = head[37:18]; wire [31:0] h_job = head[69:38];
    wire [3:0] h_gen = head[73:70];    wire [3:0] h_st = head[77:74];   wire [31:0] h_cyc = head[109:78];
    wire h_tokx = head[110];
    // CP link fields
    wire c_db_taken = cpl[0], c_cpl_v = cpl[1];
    wire c_freq_v = cpl[113]; wire [39:0] c_freq_a = cpl[153:114];
    // F5 (hgi-e2e): the record-ring fetch is a 4-entry request queue (the CP holds 4 credits; f_req_ack = a request
    // accepted by the memory lane returns one) feeding lane 1 back to back; responses return in order, any number in
    // flight (the sequencer bounds them: NOS 48).  Was: one request until its data, a second request faulted.
    localparam integer FQD = 4;
    reg [36:0] fq [0:FQD-1]; reg [1:0] fq_h, fq_t; reg [2:0] fq_n;
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lb_v <= 1'b0; lr_v <= 1'b0; db_pend <= 1'b0; cq_n <= 3'd0; cq_h <= 2'd0; cq_t <= 2'd0; lcp <= 419'd0;
            m_req_v <= 1'b0; fq_h <= 2'd0; fq_t <= 2'd0; fq_n <= 3'd0; fault <= 1'b0;
            d_tok <= 18'd0; d_pos <= 20'd0; d_job <= 32'd0; d_gen <= 4'd0; d_ent <= 2'd0; d_ncol <= 4'd0;
        end else begin
            lcp[0] <= 1'b0; lcp[71] <= 1'b0; lcp[148] <= 1'b0; lcp[406] <= 1'b0;   // pulses
            // local write
            if (lb_v && s_bready) lb_v <= 1'b0;
            if (lw_take) begin
                lb_v <= 1'b1;
                case (s_awaddr[8:0])
                    9'h000: d_tok <= s_wdata[17:0];
                    9'h004: d_pos <= s_wdata[19:0];
                    9'h008: d_job <= s_wdata;
                    9'h00C: begin d_gen <= s_wdata[3:0]; d_ent <= s_wdata[5:4]; d_ncol <= s_wdata[11:8]; end
                    9'h014: lcp[414:407] <= s_wdata[7:0];
                    9'h010: if (!db_pend) begin
                        db_pend <= 1'b1;
                        lcp[147:71] <= {d_ent, d_gen, d_job, d_pos, d_tok, 1'b1}; lcp[418:415] <= d_ncol;
                    end
                    default: if (s_awaddr[8]) begin                      // 0xD00-0xDFF CFG window
                        if (!s_awaddr[2]) cfg_lo[s_awaddr[7:3]] <= s_wdata;
                        else lcp[70:0] <= {s_wdata, cfg_lo[s_awaddr[7:3]], 1'b1, s_awaddr[7:3], 1'b1};
                    end
                endcase
            end
            if (c_db_taken) db_pend <= 1'b0;
            // completions from the CP: always accepted (the CP sends the next only after cpl_ack)
            if (c_cpl_v) begin
                if (cq_n == CPL_DEPTH) fault <= 1'b1;
                else begin cq[cq_t] <= cpl[112:2]; cq_t <= cq_t + 2'd1; end
            end
            // local read
            if (lr_v && s_rready) lr_v <= 1'b0;
            if (lr_take) begin
                lr_v <= 1'b1;
                if (s_araddr[8]) lr_d <= 32'd0;
                else case (s_araddr[7:0])
                    8'h20: lr_d <= {21'd0, cq_n, 7'd0, db_pend};
                    8'h24: lr_d <= {28'd0, cpl[157:154]};
                    8'h28: lr_d <= cpl[189:158];
                    8'h2C: lr_d <= cpl[221:190];
                    8'h40: lr_d <= {14'd0, h_tok};
                    8'h44: lr_d <= {12'd0, h_pos};
                    8'h48: lr_d <= h_job;
                    8'h4C: lr_d <= {23'd0, h_tokx, h_st, h_gen};
                    8'h50: lr_d <= h_cyc;
                    default: lr_d <= 32'd0;
                endcase
            end
            begin : occ
                reg push, pop;
                push = c_cpl_v && cq_n != CPL_DEPTH;
                pop  = lr_take && !s_araddr[8] && s_araddr[7:0] == 8'h50 && cq_n != 0;
                if (pop) begin cq_h <= cq_h + 2'd1; lcp[148] <= 1'b1; end      // cpl_ack: the CP may send the next
                cq_n <= cq_n + push - pop;
            end
            // record-ring fetch: request queue -> memory lane 1 (one request register, refilled the cycle it is taken)
            begin : fetch
                reg take, pop_; take = m_req_v && m_req_rdy; pop_ = 1'b0;
                if (take) lcp[406] <= 1'b1;                                      // f_req_ack: a credit back to the CP
                if ((!m_req_v || take) && fq_n != 3'd0) begin
                    m_req_v <= 1'b1; m_req_addr <= fq[fq_h]; fq_h <= fq_h + 2'd1; pop_ = 1'b1;
                end else if (take) m_req_v <= 1'b0;
                if (c_freq_v) begin
                    if ((fq_n == FQD && !pop_) || |c_freq_a[39:37]) fault <= 1'b1;   // credit overrun / address
                    fq[fq_t] <= c_freq_a[36:0]; fq_t <= fq_t + 2'd1;
                end
                fq_n <= fq_n + {2'd0, c_freq_v} - {2'd0, pop_};
            end
            if (m_rsp_v) begin lcp[149] <= 1'b1; lcp[405:150] <= m_rsp_data; end
            else lcp[149] <= 1'b0;
        end
    end
endmodule
`default_nettype wire
