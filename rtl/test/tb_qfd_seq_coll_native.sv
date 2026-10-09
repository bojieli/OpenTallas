`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// sys-takeover 2026-10-09: the Qwen ROM native collective END TO END (registry qfd_native_collective_binding).  Four dies,
// each:  generated sequencer master ot_qfd_sp_constants_sequencer_nc (IS / OS stations, ot_qwen_rom_core_ctrl +
// ot_qwen_tp_seq_w12_nc, descriptor store) on the stream clock ckd
//   <-> the vector memory master ot_qfd_sp_vector_memory (row read port: request -> r_qv 3 edges later; row write port)
//   <-> ot_qwen_die_io_xfifo NCOLL = 1 (ot_qwen_die_coll_xfifo: 546-b forward with credits, 516-b return with credits)
//   <-> ot_rom_oneshot_die_m (ck) on a ot_rom_ucie_link ring to the other three dies.
// The program store holds END words only (the core finishes each segment at once; the matrix engine's argmax result is
// presented on pi_me_am_*: each die's record differs).  Descriptors: seg 0 ALL-REDUCE vm rows [VW, VW + NWD) (NWD 0 =
// 256 rows), seg 1 ARGMAX (row0 = ROW0 * die).  The bench preloads every die's partial rows into its VM through the row
// write port, runs NSTEP steps (each step re-reduces the rows the previous one wrote: the VM write-back is read back),
// and checks: every write-back row (address, once each, data == the golden fold of tools/hdc_golden.fold), every die's
// next token / value == the golden rank-order argmax, no fault anywhere (sequencer, core, xfifo, engine, VM request
// while r_rdy low).  +VEC = directory of part.hex (die-major rows), sum<s>.hex (step s rows), am.hex / exp.hex (per
// step: die records, expected {val, token}).  Prints SEQ_COLL_NATIVE PASS / FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module tb_qfd_seq_coll_native #(parameter integer CR = 8, parameter integer ENG_IB = 8, parameter integer LCR = 8,
                                parameter integer CQ_AD = 64, parameter integer QD = 8)
                               (input wire ck, input wire ckd);
    localparam integer N = 4, LANES = 16, FW = 512, TAGW = 32, RB = 2, PW = FW + 2 + TAGW;
    localparam integer WSQ = 546, WCQ = 516, NW = 18, AW = 24;
    reg [FW-1:0] part [0:4*256-1];
    reg [FW-1:0] sumv [0:8*256-1];
    reg [63:0]   amr  [0:8*N-1];          // per step, die: {val32, idx(NW, zero-extended to 32)}
    reg [63:0]   expv [0:7];              // per step: {val32, token32}
    integer NSTEP, VW, NWD, ROW0;
    string dir;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    reg [4:0] rcnt = 0;
    wire rst_n = (rcnt == 5'd20);
    always @(posedge ckd) if (!rst_n) rcnt <= rcnt + 1'b1;

    wire [N-1:0] txv;
    wire [N*PW-1:0] txr;
    wire [N*N-1:0] txrdy, crin, crout, rxv;
    wire [N*N*PW-1:0] rxr;
    wire [N-1:0] fck, fckd, fdie, sdone, sfault, cfault, vmbad;
    integer bad = 0, writes = 0;

    // bench phases (ckd): 0 preload VM + descriptors, 1.. steps
    integer ph = 0, pre = 0, step = 0, waitc = 0;
    reg start_p = 0;
    reg pre_v = 0; reg [7:0] pre_row = 0; reg [1:0] pre_die = 0;
    reg dwv = 0; reg [2:0] dwa = 0;
    integer NWEFF;

    genvar g, t;
    generate for (g = 0; g < N; g = g + 1) begin : g_die
        // ---------------- sequencer master (ckd) ----------------
        wire vm_re, vm_we, c_valid, c_last, c_mode, r_cr, s_done, s_fault, core_fault;
        wire [7:0] vm_raddr, vm_waddr;
        wire [FW-1:0] vm_wdata, c_data;
        wire [TAGW-1:0] c_tag;
        wire [NW-1:0] ntok; wire [31:0] nval;
        wire vm_qv; wire [FW-1:0] vm_rq;
        wire c_cr, r_valid, r_last, r_err; wire [FW-1:0] r_data; wire [1:0] r_rank;
        wire [31:0] r0 = ROW0 * g;
        wire [63:0] desc_w = (dwa == 0) ? {16'd0, 4'd0, 12'd0, 14'd0, NWD[7:0], VW[7:0], 2'd1} :
                                          {r0[15:0], 12'd0, 4'd0, 12'd0, r0[17:16], 16'd0, 2'd2};
        wire [63:0] am = amr[(step > 0 ? step - 1 : 0) * N + g];
        ot_qfd_sp_constants_sequencer_nc #(.CR(CR), .QD(QD)) u_seq (
            .clk(ckd), .rst_n(rst_n), .po_me_clk(),
            .h_start(start_p), .tp_token(18'(100 + step)), .tp_pos(18'(7 * step + 3)),
            .kv_write_drained(1'b1), .kv_ok(1'b1), .me_mem_ok(1'b1),
            .vm_qv(vm_qv), .vm_rq(vm_rq), .c_cr(c_cr), .r_valid(r_valid), .r_data(r_data), .r_last(r_last),
            .r_rank(r_rank), .r_err(r_err),
            .pw_v(1'b0), .pw_addr(10'd0), .pw_data(64'd0), .dw_v(dwv), .dw_addr(dwa), .dw_data(desc_w),
            .pi_me_ready(1'b1), .pi_me_idle(1'b1), .pi_me_wrom_re(1'b0), .pi_me_wrom_addr(24'd0),
            .pi_me_am_idx(am[NW-1:0]), .pi_me_am_val(am[63:32]), .pi_me_am_any(1'b1), .pi_me_progress(16'd0),
            .pi_me_fault(1'b0), .pi_su_rt_active(1'b0), .pi_su_rt_inflight(8'd0), .pi_su_ready(1'b1), .pi_su_idle(1'b1),
            .pi_su_wrom_re(1'b0), .pi_su_wrom_addr(24'd0), .pi_su_kv_we(64'd0), .pi_su_progress(16'd0),
            .pi_su_progress_rows(16'd0), .pi_su_fault(1'b0),
            .s_done(s_done), .seq_ntok(ntok), .seq_nval(nval), .s_fault(s_fault), .core_fault(core_fault),
            .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
            .c_valid(c_valid), .c_data(c_data), .c_last(c_last), .c_mode(c_mode), .c_tag(c_tag), .r_cr(r_cr));
        assign sdone[g] = s_done; assign sfault[g] = s_fault; assign cfault[g] = core_fault;
        // ---------------- vector memory master (ckd) ----------------
        wire pre_me = pre_v && pre_die == g;
        wire r_rdy;
        ot_qfd_sp_vector_memory #(.USE_MACRO(0)) u_vm (
            .clk(ckd), .rst_n(rst_n), .me_en(1'b0), .x_dv(1'b0), .x_dc(24'd0), .x_dcs(24'd0), .x_dsp(4'd0), .x_q(),
            .w_v(vm_we || pre_me), .w_row(20'(pre_me ? pre_row : vm_waddr)), .w_mask(16'hffff),
            .w_data(pre_me ? part[g * 256 + pre_row] : vm_wdata),
            .r_v(vm_re), .r_rdy(r_rdy), .r_row(20'(vm_raddr)), .r_qv(vm_qv), .r_q(vm_rq),
            .x_rdy(), .x_fault(), .x_hazard());
        reg vb = 0;
        always @(posedge ckd) if (vm_re && !r_rdy) vb <= 1'b1;
        assign vmbad[g] = vb;
        // write-back checker
        reg [255:0] seen;
        always @(posedge ckd) begin
            if (start_p) seen <= 256'd0;
            if (vm_we && ph >= 1) begin
                writes = writes + 1;
                if (((vm_waddr - VW[7:0]) & 8'hff) >= NWEFF) begin
                    bad = bad + 1; if (bad < 6) $display("WB OUT OF RANGE die=%0d row=%0d", g, vm_waddr);
                end else begin
                    if (seen[vm_waddr]) begin bad = bad + 1; if (bad < 6) $display("WB TWICE die=%0d row=%0d", g, vm_waddr); end
                    seen[vm_waddr] <= 1'b1;
                    if (vm_wdata !== sumv[(step - 1) * 256 + vm_waddr]) begin
                        bad = bad + 1;
                        if (bad < 6) $display("WB MISMATCH die=%0d step=%0d row=%0d got=%h exp=%h", g, step, vm_waddr,
                                              vm_wdata[63:0], sumv[(step - 1) * 256 + vm_waddr][63:0]);
                    end
                end
            end
        end
        // ---------------- io_xfifo NCOLL (ckd <-> ck) ----------------
        wire e_v, e_cr, o_v, o_last, o_err;
        wire [WSQ-1:0] e_d;
        wire [FW-1:0] o_data;
        wire [RB-1:0] o_rank;
        wire [2:0] fcode;
        wire [WCQ-1:0] rq;
        ot_qwen_die_io_xfifo #(.WSQ(WSQ), .NCOLL(1), .WCQ(WCQ), .N(N), .MB(FW + 1), .CQ_AD(CQ_AD), .CR(CR), .ENG_IB(ENG_IB), .LCR(LCR)) u_x (
            .ck(ck), .cku(ck), .cks(ck), .ckd(ckd), .rst_n(rst_n),
            .i_ucie_tx_v(1'b0), .i_ucie_tx(1024'b0), .i_ucie_tx_cr(), .o_ucie_tx_v(), .o_ucie_tx(), .o_ucie_tx_cr(1'b0),
            .i_ucie_rx_v(1'b0), .i_ucie_rx(1024'b0), .i_ucie_rx_cr(), .o_ucie_rx_v(), .o_ucie_rx(), .o_ucie_rx_cr(1'b0),
            .i_serdes_tx_v(1'b0), .i_serdes_tx(1024'b0), .i_serdes_tx_cr(), .o_serdes_tx_v(), .o_serdes_tx(), .o_serdes_tx_cr(1'b0),
            .i_serdes_rx_v(1'b0), .i_serdes_rx(1024'b0), .i_serdes_rx_cr(), .o_serdes_rx_v(), .o_serdes_rx(), .o_serdes_rx_cr(1'b0),
            .i_seq_coll_v(c_valid), .i_seq_coll({c_tag, c_mode, c_last, c_data}), .i_seq_coll_cr(c_cr),
            .o_seq_coll_v(e_v), .o_seq_coll(e_d), .o_seq_coll_cr(e_cr),
            .i_coll_seq_v(o_v), .i_coll_seq({o_err, o_rank, o_last, o_data}),
            .o_coll_seq_v(r_valid), .o_coll_seq(rq), .o_coll_seq_cr(r_cr),
            .fault_ck(fck[g]), .fault_cku(), .fault_cks(), .fault_ckd(fckd[g]));
        assign {r_err, r_rank, r_last, r_data} = rq;
        // ---------------- collective engine (ck) ----------------
        ot_rom_oneshot_die_m #(.N(N), .RANK(g), .LANES(LANES), .TAGW(TAGW), .DEPTH(32), .IB(ENG_IB)) u_die (
            .clk(ck), .rst_n(rst_n),
            .in_valid(e_v), .in_cr(e_cr), .in_data(e_d[FW-1:0]), .in_last(e_d[FW]), .in_mode(e_d[FW+1]),
            .in_tag(e_d[FW+2 +: TAGW]),
            .tx_valid(txv[g]), .tx_rec(txr[g*PW +: PW]), .tx_ready(txrdy[g*N +: N]), .cr_in(crin[g*N +: N]),
            .rx_valid(rxv[g*N +: N]), .rx_rec(rxr[g*N*PW +: N*PW]), .cr_out(crout[g*N +: N]),
            .out_valid(o_v), .out_data(o_data), .out_last(o_last), .out_rank(o_rank), .out_err(o_err),
            .fault(fdie[g]), .fault_code(fcode));
        for (t = 0; t < N; t = t + 1) begin : g_to
            if (t == g) begin : g_self
                assign txrdy[g*N + t] = 1'b1; assign crin[g*N + t] = 1'b0;
                assign rxv[g*N + t] = 1'b0; assign rxr[(g*N + t)*PW +: PW] = {PW{1'b0}};
            end else begin : g_link
                ot_rom_ucie_link #(.PW(PW), .LAT(12), .FLIT_BYTES(FW / 8), .BPC_NUM(3600), .BPC_DEN(1)) u_link (
                    .clk(ck), .rst_n(rst_n), .in_valid(txv[g]), .in_rec(txr[g*PW +: PW]), .in_ready(txrdy[g*N + t]),
                    .out_valid(rxv[t*N + g]), .out_rec(rxr[(t*N + g)*PW +: PW]),
                    .cr_in(crout[t*N + g]), .cr_out(crin[g*N + t]));
            end
        end
    end endgenerate

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("NSTEP=%d", NSTEP)) NSTEP = 2;
        if (!$value$plusargs("VW=%d", VW)) VW = 0;
        if (!$value$plusargs("NWD=%d", NWD)) NWD = 0;
        if (!$value$plusargs("ROW0=%d", ROW0)) ROW0 = 37984;
        NWEFF = (NWD == 0) ? 256 : NWD;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/sum.hex"}, sumv);
        $readmemh({dir, "/am.hex"}, amr);
        $readmemh({dir, "/exp.hex"}, expv);
    end

    // ---------------- bench sequencing (ckd) ----------------
    integer s0 = 0, s1 = 0;
    reg armed = 0;
    always @(posedge ckd) begin
        start_p <= 1'b0; dwv <= 1'b0;
        if (rst_n && ph == 0) begin
            waitc <= waitc + 1;
            if (waitc >= 24) begin
                // preload: 4 dies x 256 rows, then 2 descriptors per die (all dies share the dw bus: the row0 term
                // uses the die index inside desc_w)
                if (pre < 4 * 256) begin
                    pre_v <= 1'b1; pre_die <= pre / 256; pre_row <= pre % 256; pre <= pre + 1;
                end else if (pre < 4 * 256 + 2) begin
                    pre_v <= 1'b0; dwv <= 1'b1; dwa <= pre - 4 * 256; pre <= pre + 1;
                end else if (pre < 4 * 256 + 40) begin
                    pre_v <= 1'b0; pre <= pre + 1;               // let the stations drain
                end else begin
                    ph <= 1; step <= 1; start_p <= 1'b1; s0 = cyc;
                end
            end
        end else if (ph == 1) begin
            if (start_p) armed <= 1'b0;
            else if (sdone == {N{1'b0}}) armed <= 1'b1;          // the new step has cleared every die's done
            if (armed && sdone == {N{1'b1}} && !start_p) begin
                armed <= 1'b0;
                // the step's result: every die must hold the golden argmax
                for (integer d = 0; d < N; d = d + 1) begin
                    if (g_die_val(d) !== expv[step - 1][63:32] || g_die_tok(d) !== expv[step - 1][NW-1:0]) begin
                        bad = bad + 1;
                        if (bad < 6) $display("ARGMAX die=%0d step=%0d got tok=%0d val=%h exp tok=%0d val=%h", d, step,
                                              g_die_tok(d), g_die_val(d), expv[step - 1][NW-1:0], expv[step - 1][63:32]);
                    end
                end
                $display("step %0d done ck=%0d", step, cyc - s0);
                if (step == NSTEP) begin ph <= 2; s1 = cyc; end
                else begin step <= step + 1; start_p <= 1'b1; s0 = cyc; end
            end
        end
    end
    function automatic [NW-1:0] g_die_tok(input integer d);
        case (d) 0: g_die_tok = g_die[0].ntok; 1: g_die_tok = g_die[1].ntok; 2: g_die_tok = g_die[2].ntok;
                 default: g_die_tok = g_die[3].ntok; endcase
    endfunction
    function automatic [31:0] g_die_val(input integer d);
        case (d) 0: g_die_val = g_die[0].nval; 1: g_die_val = g_die[1].nval; 2: g_die_val = g_die[2].nval;
                 default: g_die_val = g_die[3].nval; endcase
    endfunction

    always @(posedge ck) begin
        if (ph == 2 || cyc > 400000 * NSTEP) begin
            $display("SEQ_COLL_NATIVE steps=%0d vw=%0d nw=%0d mismatches=%0d writes=%0d (exp %0d) fault_seq=%b fault_core=%b fault_ck=%b fault_ckd=%b fault_die=%b vm_req_unready=%b",
                     step, VW, NWEFF, bad, writes, 4 * NWEFF * NSTEP, sfault, cfault, fck, fckd, fdie, vmbad);
            if (ph == 2 && bad == 0 && writes == 4 * NWEFF * NSTEP && sfault == 0 && cfault == 0 && fck == 0 && fckd == 0 &&
                fdie == 0 && vmbad == 0) $display("SEQ_COLL_NATIVE PASS");
            else $display("SEQ_COLL_NATIVE FAIL");
            $finish;
        end
    end
endmodule
