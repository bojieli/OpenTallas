`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_hbm_partition: the shoreline HBM memory partition behind one L2
// slice (clk_mem): an MREQ controller front end around the timing-faithful
// behavioural HBM model rtl/hdc/kv/ot_hdc_hbm_model.sv (reused unmodified,
// NPC pseudo-channels, CLK_PS).
//
// Address: the MREQ byte address is die-global; the partition removes the
// slice-select bits [7 +: LNS] (local = {a[31:7+LNS], a[6:0]}) and addresses
// the model with the 32-byte sector local >> 5 (SECW = 27 - LNS bits).  The
// model stores sector s in u_model.mem[s % MEM_WORDS], byte b of the sector
// in bits [8b +: 8] (tools/gpu_sys/mem_image.py builds the load images).
//
// Front end (in order, one request per cycle into a registered backend slot):
//   * read: one-sector model read; the response is returned by tag;
//   * write with all 32 strobes: one model write;
//   * write with a partial strobe: exact ordered read-modify-write; the front
//     end stops accepting, reads the sector (ordered after every earlier
//     access to it by the model's same-sector rule), merges the strobed bytes
//     and writes the whole sector, then resumes;
//   * write acknowledge: the model has no write response.  A write is ordered
//     before every later read of its sector once the model has ACCEPTED it
//     (a sector maps to one pseudo-channel queue and the model's scheduler
//     never lets a burst pass an older same-sector burst when either is a
//     write), so the adapter queues the ack at model acceptance;
//   * the NPC read response ports are merged round-robin; reads and write acks
//     share the MREQ response port (alternating priority).
//
// USE_W2 = 1 inserts Codex's W2 exact tag/generation completion matcher
// rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv
// (unmodified, OPT_EXACT=1, its locked NC6/MAX16/CTAG32/GEN4/AW34 geometry)
// between the front end (client 0; clients 1..5 idle; generation 0; tag
// zero-extended) and the model adapter (provider; the adapter's acceptance-
// time write ack is the provider's write-done).  Its byte-strobe-less request
// is why the read-modify-write stays in front of it.
//
// Memory image: at time 0 the model array is zeroed, then loaded with
// $readmemh from "<prefix>_p<PART_IDX>.hex" (DIE_IDX < 0, default) or
// "<prefix>_d<DIE_IDX>_p<PART_IDX>.hex" (DIE_IDX >= 0, one image set per die
// under one plusarg), where <prefix> is the plusarg
// +gpu_sys_mem_prefix=<prefix> if present, else IMAGE_PREFIX (empty: none).
// ENABLE = 0 (default): inert, every output 0, no model instance.
// ---------------------------------------------------------------------------
module ot_gpu_hbm_partition #(
    parameter integer ENABLE    = 0,
    parameter integer NS        = 2,
    parameter integer LNS       = (NS > 1) ? $clog2(NS) : 0,
    parameter integer TW        = 6,
    parameter integer NPC       = 2,
    parameter integer MEM_WORDS = 16384,
    parameter integer CLK_PS    = 1000,
    parameter integer USE_W2    = 0,
    parameter integer PART_IDX  = 0,
    parameter integer DIE_IDX   = -1,
    parameter         IMAGE_PREFIX = ""
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          req_v,
    output reg           req_rdy,
    input  wire          req_we,
    input  wire [31:0]   req_addr,
    input  wire [255:0]  req_wdata,
    input  wire [31:0]   req_wstrb,
    input  wire [TW-1:0] req_tag,
    output reg           rsp_v,
    input  wire          rsp_rdy,
    output reg  [TW-1:0] rsp_tag,
    output reg           rsp_we,
    output reg  [255:0]  rsp_data,
    output reg           fault
);
    generate if (ENABLE != 0) begin : g_on
        localparam integer SECW = 27 - LNS;
        localparam integer BTW  = TW + 1;                    // front-end tag: {rmw, tag}
        localparam integer ATW  = (USE_W2 != 0) ? 35 : BTW;  // model tag
        localparam integer LPC  = (NPC > 1) ? $clog2(NPC) : 1;
        initial if (USE_W2 != 0 && BTW > 32) $fatal(1, "ot_gpu_hbm_partition: TW+1 must fit the W2 32-bit tag");

        // ---------------- front end ----------------
        reg            bv, bwe;
        reg [SECW-1:0] bsec;
        reg [BTW-1:0]  btag;
        reg [255:0]    bdata;
        reg            rmw;                   // waiting for the RMW read
        reg [TW-1:0]   rmw_tag;
        reg [255:0]    rmw_wdata;
        reg [31:0]     rmw_wstrb;
        reg            pri;
        // backend view (front end <-> [W2] <-> adapter)
        wire           be_req_rdy;
        wire           be_rsp_v, be_wd_v;
        wire [BTW-1:0] be_rsp_tag;
        /* verilator lint_off UNUSEDSIGNAL */
        wire [BTW-1:0] be_wd_tag;           // [TW] is always 0 for an ack
        /* verilator lint_on UNUSEDSIGNAL */
        wire [255:0]   be_rsp_data;
        reg            be_rsp_rdy, be_wd_rdy;
        wire           w2_fault;

        reg            sel_rd, b_free, rmw_rsp;
        reg [255:0]    merged;
        always @(*) begin : p_fe
            integer b;
            b_free  = !bv || be_req_rdy;
            rmw_rsp = be_rsp_v && be_rsp_tag[TW];
            req_rdy = !rmw && b_free && !fault;
            sel_rd  = be_rsp_v && !be_rsp_tag[TW] && (!be_wd_v || !pri);
            rsp_v   = (be_rsp_v && !be_rsp_tag[TW]) || be_wd_v;
            rsp_we  = rsp_v && !sel_rd;
            rsp_tag = sel_rd ? be_rsp_tag[TW-1:0] : (be_wd_v ? be_wd_tag[TW-1:0] : '0);
            rsp_data = sel_rd ? be_rsp_data : 256'd0;
            for (b = 0; b < 32; b = b + 1)
                merged[b*8 +: 8] = rmw_wstrb[b] ? rmw_wdata[b*8 +: 8] : be_rsp_data[b*8 +: 8];
        end
        always @(*) begin : p_berdy
            be_rsp_rdy = rmw_rsp ? (rmw && b_free) : (sel_rd && rsp_rdy);
            be_wd_rdy  = !sel_rd && be_wd_v && rsp_rdy;
        end

        function automatic [SECW-1:0] lsec(input [31:0] a);
            reg [31:0] la;
            begin
                la = (NS > 1) ? (((a >> (7 + LNS)) << 7) | (a & 32'h7f)) : a;
                lsec = SECW'(la >> 5);
            end
        endfunction

        always @(posedge clk) begin
            if (!rst_n) begin
                bv <= 1'b0; bwe <= 1'b0; bsec <= '0; btag <= '0; bdata <= '0;
                rmw <= 1'b0; rmw_tag <= '0; rmw_wdata <= '0; rmw_wstrb <= '0; pri <= 1'b0; fault <= 1'b0;
            end else begin
                if (bv && be_req_rdy) bv <= 1'b0;
                if (req_v && req_rdy) begin
                    bv <= 1'b1; bsec <= lsec(req_addr);
                    if (req_we && req_wstrb != 32'hffff_ffff) begin
                        bwe <= 1'b0; btag <= {1'b1, req_tag}; bdata <= 256'd0;
                        rmw <= 1'b1; rmw_tag <= req_tag; rmw_wdata <= req_wdata; rmw_wstrb <= req_wstrb;
                    end else begin
                        bwe <= req_we; btag <= {1'b0, req_tag}; bdata <= req_we ? req_wdata : 256'd0;
                    end
                end
                if (rmw_rsp && be_rsp_rdy) begin
                    if (be_rsp_tag[TW-1:0] != rmw_tag) fault <= 1'b1;
                    bv <= 1'b1; bwe <= 1'b1; btag <= {1'b0, rmw_tag}; bdata <= merged; rmw <= 1'b0;
                end
                if (rmw_rsp && !rmw) fault <= 1'b1;
                if (w2_fault) fault <= 1'b1;
                if (rsp_v && rsp_rdy) pri <= !pri;
            end
        end

        // ---------------- model adapter ----------------
        wire            a_req_v, a_req_we;
        wire            a_req_rdy;
        wire [SECW-1:0] a_req_sec;
        wire [ATW-1:0]  a_req_tag;
        wire [255:0]    a_req_data;
        reg             a_rsp_v;
        wire            a_rsp_rdy;
        reg  [ATW-1:0]  a_rsp_tag;
        reg  [255:0]    a_rsp_data;
        wire            a_wd_v;
        wire            a_wd_rdy;
        wire [ATW-1:0]  a_wd_tag;

        wire            m_req_rdy;
        /* verilator lint_off UNUSEDSIGNAL */
        wire [NPC-1:0]  m_pc_room;          // model outputs not used by a one-sector front end
        wire [NPC*4-1:0]   m_rsp_beat;
        /* verilator lint_on UNUSEDSIGNAL */
        reg  [NPC-1:0]  m_rsp_rdy;
        wire [NPC-1:0]  m_rsp_v;
        wire [NPC*ATW-1:0] m_rsp_tag;
        wire [NPC*256-1:0] m_rsp_data;

        // write-ack queue (acknowledge at model acceptance)
        localparam integer WQD = 4;
        reg  [ATW-1:0] wq [0:WQD-1];
        reg  [1:0]     wq_rp, wq_wp;
        reg  [2:0]     wq_n;
        wire           wq_room = (wq_n < 3'(WQD));
        wire           m_take  = a_req_v && m_req_rdy && (!a_req_we || wq_room);
        assign a_req_rdy = m_req_rdy && (!a_req_we || wq_room);
        assign a_wd_v   = (wq_n != 0);
        assign a_wd_tag = wq[wq_rp];
        always @(posedge clk) begin
            if (!rst_n) begin
                wq_rp <= '0; wq_wp <= '0; wq_n <= '0;
            end else begin
                if (m_take && a_req_we) begin wq[wq_wp] <= a_req_tag; wq_wp <= wq_wp + 1'b1; end
                if (a_wd_v && a_wd_rdy) wq_rp <= wq_rp + 1'b1;
                wq_n <= wq_n + ((m_take && a_req_we) ? 3'd1 : 3'd0) - ((a_wd_v && a_wd_rdy) ? 3'd1 : 3'd0);
            end
        end
        // read response merge (round-robin over pseudo-channels)
        reg [LPC-1:0] rr;
        reg [LPC-1:0] gsel;
        always @(*) begin : p_merge
            integer k;
            /* verilator lint_off UNUSEDSIGNAL */
            integer pc;
            /* verilator lint_on UNUSEDSIGNAL */
            a_rsp_v = 1'b0; gsel = '0;
            for (k = NPC - 1; k >= 0; k = k - 1) begin
                pc = (integer'(rr) + k) % NPC;
                if (m_rsp_v[pc]) begin a_rsp_v = 1'b1; gsel = LPC'(pc); end
            end
            a_rsp_tag  = m_rsp_tag[integer'(gsel)*ATW +: ATW];
            a_rsp_data = m_rsp_data[integer'(gsel)*256 +: 256];
        end
        always @(*) begin : p_mrdy
            m_rsp_rdy  = '0;
            if (a_rsp_v && a_rsp_rdy) m_rsp_rdy[gsel] = 1'b1;
        end
        always @(posedge clk) begin
            if (!rst_n) rr <= '0;
            else if (a_rsp_v && a_rsp_rdy) rr <= (integer'(gsel) == NPC - 1) ? '0 : gsel + 1'b1;
        end

        ot_hdc_hbm_model #(.NPC(NPC), .AW(SECW), .DW(256), .MEM_WORDS(MEM_WORDS), .TAGW(ATW), .CLK_PS(CLK_PS))
        u_model (
            .clk(clk), .rst_n(rst_n), .req_v(a_req_v && (!a_req_we || wq_room)), .req_rdy(m_req_rdy),
            .pc_room(m_pc_room), .req_we(a_req_we), .req_addr(a_req_sec), .req_len(5'd1), .req_tag(a_req_tag),
            .req_wdata(a_req_data), .rsp_v(m_rsp_v), .rsp_rdy(m_rsp_rdy), .rsp_tag(m_rsp_tag),
            .rsp_beat(m_rsp_beat), .rsp_data(m_rsp_data));

        // ---------------- front end <-> adapter: direct or through W2 ----------------
        if (USE_W2 == 0) begin : g_direct
            assign a_req_v    = bv;
            assign a_req_we   = bwe;
            assign a_req_sec  = bsec;
            assign a_req_tag  = btag;
            assign a_req_data = bdata;
            assign be_req_rdy = a_req_rdy;
            assign be_rsp_v   = a_rsp_v;
            assign be_rsp_tag = a_rsp_tag;
            assign be_rsp_data = a_rsp_data;
            assign a_rsp_rdy  = be_rsp_rdy;
            assign be_wd_v    = a_wd_v;
            assign be_wd_tag  = a_wd_tag;
            assign a_wd_rdy   = be_wd_rdy;
            assign w2_fault   = 1'b0;
        end else begin : g_w2
            /* verilator lint_off UNUSEDSIGNAL */   // W2 outputs of the idle clients 1..5 and status
            wire          w_rearm_rdy, w_idle;
            wire [5:0]    w_c_req_rdy, w_c_rsp_v, w_c_wd_v;
            wire [6*32-1:0]  w_c_rsp_tag, w_c_wd_tag;
            wire [6*4-1:0]   w_c_rsp_gen, w_c_wd_gen;
            wire [6*256-1:0] w_c_rsp_data;
            wire          w_p_req_v, w_p_req_we, w_p_rsp_rdy, w_p_wd_rdy;
            wire [33:0]   w_p_req_addr;
            wire [34:0]   w_p_req_tag;
            wire [3:0]    w_p_req_gen;
            wire [255:0]  w_p_req_data;
            /* verilator lint_on UNUSEDSIGNAL */
            ot_hdc_qwen_pc_exact_completion #(.OPT_EXACT(1)) u_w2 (
                .clk(clk), .rst_n(rst_n), .admission_stop(1'b0), .rearm_v(1'b0), .provider_fenced(1'b1),
                .reset_fenced(1'b1), .rearm_rdy(w_rearm_rdy), .idle(w_idle),
                .c_req_v({5'd0, bv}), .c_req_we({5'd0, bwe}), .c_req_rdy(w_c_req_rdy),
                .c_req_addr({170'd0, 34'(bsec)}), .c_req_tag({160'd0, 32'(btag)}), .c_req_gen(24'd0),
                .c_req_data({1280'd0, bdata}),
                .c_rsp_v(w_c_rsp_v), .c_wr_done_v(w_c_wd_v), .c_rsp_rdy({5'd0, be_rsp_rdy}),
                .c_wr_done_rdy({5'd0, be_wd_rdy}), .c_rsp_tag(w_c_rsp_tag), .c_wr_done_tag(w_c_wd_tag),
                .c_rsp_gen(w_c_rsp_gen), .c_wr_done_gen(w_c_wd_gen), .c_rsp_data(w_c_rsp_data),
                .p_req_v(w_p_req_v), .p_req_we(w_p_req_we), .p_req_rdy(a_req_rdy), .p_req_addr(w_p_req_addr),
                .p_req_tag(w_p_req_tag), .p_req_gen(w_p_req_gen), .p_req_data(w_p_req_data),
                .p_rsp_v(a_rsp_v), .p_wr_done_v(a_wd_v), .p_rsp_rdy(w_p_rsp_rdy), .p_wr_done_ready(w_p_wd_rdy),
                .p_rsp_tag(a_rsp_tag), .p_wr_done_tag(a_wd_tag), .p_rsp_gen(4'd0), .p_wr_done_gen(4'd0),
                .p_rsp_data(a_rsp_data), .fault(w2_fault));
            assign a_req_v    = w_p_req_v;
            assign a_req_we   = w_p_req_we;
            assign a_req_sec  = w_p_req_addr[SECW-1:0];
            assign a_req_tag  = w_p_req_tag;
            assign a_req_data = w_p_req_data;
            assign be_req_rdy = w_c_req_rdy[0];
            assign be_rsp_v   = w_c_rsp_v[0];
            assign be_rsp_tag = w_c_rsp_tag[BTW-1:0];
            assign be_rsp_data = w_c_rsp_data[255:0];
            assign a_rsp_rdy  = w_p_rsp_rdy;
            assign be_wd_v    = w_c_wd_v[0];
            assign be_wd_tag  = w_c_wd_tag[BTW-1:0];
            assign a_wd_rdy   = w_p_wd_rdy;
        end

        // ---------------- memory image ----------------
        initial begin : init_mem
            string pfx, fn;
            integer w;
            for (w = 0; w < MEM_WORDS; w = w + 1) u_model.mem[w] = 256'd0;
            pfx = IMAGE_PREFIX;
            if (!$value$plusargs("gpu_sys_mem_prefix=%s", pfx)) pfx = IMAGE_PREFIX;
            if (pfx != "") begin
                if (DIE_IDX < 0) fn = $sformatf("%s_p%0d.hex", pfx, PART_IDX);
                else fn = $sformatf("%s_d%0d_p%0d.hex", pfx, DIE_IDX, PART_IDX);
                $readmemh(fn, u_model.mem);
            end
        end
    end else begin : g_off
        assign req_rdy = 1'b0;
        assign rsp_v = 1'b0;
        assign rsp_tag = '0;
        assign rsp_we = 1'b0;
        assign rsp_data = '0;
        assign fault = 1'b0;
    end endgenerate
endmodule
