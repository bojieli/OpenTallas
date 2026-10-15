`timescale 1ns/1ps
// qwen-1010/a 2026-10-10: the TP sequencer's all-reduce VM read through the die master's pin stations.
// The vector memory answers at ITS pins one edge after vm_re (registered read); between the sequencer and the memory sit
// the master's output station (OS), RLY die relays each way and the input station (IS): round trip OS + RLY + 1 + RLY + IS.
// The collective records every word the sequencer sends and loops them back.  PASS = every sent word equals the memory
// word it names (order kept).  VRL = 0: the base ot_qwen_tp_seq_w12 (assumes 1 edge); VRL > 0: ot_qwen_tp_seq_w12_vrl
// with that read latency.  Expected: base FAILS at any station; VRL = round trip PASSES; VRL = round trip - 1 FAILS.
module tb_qwen_seq_row_transport;
    parameter integer VARIABLE = 0, MUT = 0, VRL = 19, OS = 1, IS = 1, RLY = 2, NWORDS = 256, VW0 = 256, CRDY = 1, CST = 0, CRED = 128, IB = 512, TRUNC = 0, FENCE = 0;
    // CRED > 0: credit-mode collective port: the receiver buffers IB words, drains them at random and returns one credit
    // pulse per drained word through the stations (c_ready = credit); an overflow of its buffer is a FAIL
    // CST 1: the collective handshake also crosses the stations (c_valid / c_data through OS, c_ready back through IS)
    localparam integer FW = 512, NW = 18;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    reg start = 0;
    wire core_start, done, fault, coll_busy; wire [NW-1:0] core_tok, core_pos, ntok; wire [31:0] nval;
    wire [11:0] prog_base; wire desc_re; wire [5:0] desc_addr; reg [63:0] desc_q;
    wire vm_rvalid; 
    wire vm_re, vm_we; wire [19:0] vm_raddr, vm_waddr; wire [FW-1:0] vm_wdata, vm_rq;
    wire c_valid, c_last, c_mode; wire [FW-1:0] c_data; wire [31:0] c_tag;
    reg c_ready; reg r_valid = 0; reg [FW-1:0] r_data; reg r_last = 0;
    // descriptors: seg 0 = AR of NWORDS words at VW0, seg 1 = END
    always @(posedge clk) if (desc_re) desc_q <= (desc_addr == 0) ? {16'd0, 16'd0, 12'(VW0 >> 8), 2'd0, 8'(NWORDS), 8'(VW0), 2'd1} : 64'd0;
    // the core: done two edges after start
    reg [1:0] cs; always @(posedge clk) cs <= {cs[0], core_start};
    wire core_done = cs[1];
    // memory at its pins, stations between
    function automatic [511:0] expected(input integer row);
        expected = {16{32'(row * 32'h9E3779B1 + 7)}};
    endfunction
    wire m_re, pin_pending; wire [19:0] m_a;
    wire local_ready = VARIABLE ? !pin_pending : 1'b1;
    reg m_ready=1, m_valid0=0; reg [511:0] m_q;
    integer cyc=0, delay_left=0; reg busy=0; reg [19:0] held_a;
    generate if (VARIABLE) begin : g_elastic
        ot_qfd_row_request_pin #(.AW(20), .OS(OS+RLY)) station (
            .clk(clk), .rst_n(rst_n), .request(vm_re), .addr(vm_raddr), .ready(m_ready),
            .valid(m_re), .pin_addr(m_a), .pending(pin_pending));
        always @(negedge clk) m_ready <= (cyc%7 >= 3) && !busy;
        always @(posedge clk) begin
            cyc <= cyc+1; m_valid0 <= 0;
            if (m_re && m_ready) begin busy <= 1; delay_left <= 13+(cyc%11); held_a <= m_a; end
            if (busy) begin
                delay_left <= delay_left-1;
                if (delay_left==1) begin busy<=0; m_valid0<=1; m_q<=expected(held_a); end
            end
        end
    end else begin : g_static
        wire accepted; wire [19:0] response_addr;
        ot_hdc_delay #(.W(21), .D(OS+RLY), .RESET(1)) req_pipe (.clk(clk), .rst_n(rst_n), .d({vm_re,vm_raddr}), .q({m_re,m_a}));
        ot_hdc_delay #(.W(21), .D(13), .RESET(1)) mem_pipe (.clk(clk), .rst_n(rst_n), .d({m_re,m_a}), .q({accepted,response_addr}));
        always @(*) begin m_valid0=accepted; m_q=expected(MUT==3 ? (response_addr^20'd1) : response_addr); end
        assign pin_pending=0;
    end endgenerate
    wire response_v;
    ot_hdc_delay #(.W(FW+1), .D(RLY+IS), .RESET(1)) resp_pipe (.clk(clk), .rst_n(rst_n), .d({m_valid0,m_q}), .q({response_v,vm_rq}));
    assign vm_rvalid = MUT==1 ? vm_re : MUT==2 ? 1'b0 : response_v;
    integer read_count = 0, write_count = 0;
    always @(posedge clk) if (rst_n) begin
        if (vm_re) begin
            if (vm_raddr !== 20'(VW0 + read_count)) $fatal(1, "read row truncation expected=%0d got=%0d", VW0+read_count,vm_raddr);
            read_count = read_count + 1;
        end
        if (vm_we) begin
            if (vm_waddr !== 20'(VW0 + write_count) || vm_wdata !== expected(VW0 + write_count)) $fatal(1, "write row/data mismatch");
            write_count = write_count + 1;
        end
    end
    // collective: c_ready always (CRDY 0) or random; loops the words back after all are sent
    integer sent = 0, bad = 0, back = 0;
    integer issue_cycle=0, issue_n=0, response_n=0;
    always @(posedge clk) if (rst_n) begin
        issue_cycle=issue_cycle+1;
        if(vm_re) begin $display("TIMELINE issue=%0d row=%0d cycle=%0d",issue_n,vm_raddr,issue_cycle); issue_n=issue_n+1; end
        if(vm_rvalid) begin $display("TIMELINE response=%0d cycle=%0d",response_n,issue_cycle); response_n=response_n+1; end
    end
    reg x_ready = 0; wire x_valid; wire [FW-1:0] x_data; wire q_ready;
    // credit receiver: IB-word buffer; drains a word on a random cycle and returns its credit
    integer occ = 0, ovf = 0; reg drain;
    always @(posedge clk) begin
        drain = (CRDY == 0) ? 1'b1 : $random;
        if (CRED != 0 && !rst_n) x_ready <= 1'b0;
        else if (CRED != 0) begin
            x_ready <= (occ > 0) && drain;
            occ = occ + ((x_valid) ? 1 : 0) - (((occ > 0) && drain) ? 1 : 0);
            if (occ > IB) ovf = ovf + 1;
        end else x_ready <= (CRDY == 0) ? 1'b1 : $random;
    end
    ot_hdc_delay #(.W(1 + FW), .D(CST ? OS : 0), .RESET(1)) u_cv (.clk(clk), .rst_n(rst_n), .d({c_valid, c_data}), .q({x_valid, x_data}));
    ot_hdc_delay #(.W(1), .D(CST ? IS : 0), .RESET(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(x_ready), .q(q_ready));
    always @(*) c_ready = q_ready;   // (unused by the DUT: it reads q_ready)
    always @(posedge clk) if (rst_n && x_valid) begin
        if (x_data !== expected(VW0 + sent)) begin bad = bad + 1; if (bad < 4) $display("word %0d: got %h want %h", sent, x_data[31:0], 32'( (VW0+sent)*32'h9E3779B1+7)); end
        sent = sent + 1;
    end
    always @(posedge clk) begin
        r_valid <= 1'b0; r_last <= 1'b0;
        if (sent == NWORDS && back < NWORDS) begin r_valid <= 1'b1; r_data <= expected(VW0 + back); r_last <= (back == NWORDS - 1); back = back + 1; end
    end
    generate begin : g_vrl
        ot_qwen_tp_seq_w12_vrl #(.VRL(VRL), .VARIABLE(VARIABLE), .STATIC(1), .VWA(20), .VM_ADDR_EXT(!TRUNC), .CRED(CRED), .ENABLE_AR256(1), .N(8), .NW(NW), .QWEN_FULLSHAPE(1)) u (
            .clk(clk), .rst_n(rst_n), .rst_nw(rst_n), .start(start), .token(18'd5), .pos(18'd9), .done(done), .next_token(ntok), .next_val(nval),
            .fault(fault), .coll_busy(coll_busy), .core_start(core_start), .core_token(core_tok), .core_pos(core_pos),
            .core_done(core_done), .core_next_token(18'd0), .core_next_val(32'd0), .core_fault(1'b0), .prog_base(prog_base),
            .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q), .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq), .vm_rvalid(vm_rvalid),
            .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .c_valid(c_valid), .c_ready(q_ready), .c_data(c_data),
            .c_last(c_last), .c_mode(c_mode), .c_tag(c_tag), .r_valid(r_valid), .r_data(r_data), .r_last(r_last), .r_rank(3'd0), .r_err(1'b0));
    end endgenerate
    integer t0;
    initial begin
        repeat (3) @(negedge clk); rst_n = 1; @(negedge clk); start = 1; @(negedge clk); start = 0; t0 = $time;
        repeat (20000) begin @(posedge clk); if (done) begin
            if (FENCE ? (fault && read_count == 0 && write_count == 0) : (bad == 0 && sent == NWORDS && !fault && ovf == 0 && write_count == NWORDS)) $display("PASS row_transport variable=%0d VRL=%0d OS=%0d IS=%0d RLY=%0d words=%0d coll_cycles=%0d", VARIABLE, VRL, OS, IS, RLY, sent, $time - t0);
            else $fatal(1, "FAIL tp_seq_vrl VRL=%0d OS=%0d IS=%0d RLY=%0d bad=%0d sent=%0d fault=%0d ovf=%0d", VRL, OS, IS, RLY, bad, sent, fault, ovf);
            $finish; end end
        $fatal(1, "FAIL tp_seq_vrl timeout sent=%0d bad=%0d", sent, bad); $finish;
    end
endmodule
