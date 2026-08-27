`timescale 1ns/1ps
// Directed cross-stage logical-link fault campaign.  The PHY is outside the
// public model; this bench closes packet CRC, sequence, replay, retry, timeout,
// credit, and abort containment at the architectural packet boundary.
module tb_fault_link;
    // Canonical coverage-merge stimulus identifier: 0x464c4e4b ("FLNK").
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;
    integer failures = 0;

    task automatic check_site;
        input [8*64-1:0] site_id;
        input condition;
        begin
            if (condition)
                $display("FAULT_SITE %0s PASS",site_id);
            else begin
                $display("FAULT_SITE %0s FAIL",site_id);
                failures = failures + 1;
            end
        end
    endtask

    task automatic reset_duts;
        begin
            @(negedge clk);
            rst_n = 1'b0;
            repeat (3) @(negedge clk);
            rst_n = 1'b1;
            @(negedge clk);
        end
    endtask

    function automatic [31:0] crc32c_flit;
        input [31:0] data;
        integer byte_i;
        integer bit_i;
        reg [31:0] c;
        reg feedback;
        begin
            c = 32'hffff_ffff;
            for (byte_i = 0; byte_i < 4; byte_i = byte_i + 1)
                for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                    feedback = c[0] ^ data[byte_i*8+bit_i];
                    c = c >> 1;
                    if (feedback)
                        c = c ^ 32'h82f6_3b78;
                end
            crc32c_flit = c ^ 32'hffff_ffff;
        end
    endfunction

    function automatic [31:0] crc32c_extend;
        input [31:0] state_in;
        input [31:0] data;
        integer byte_i;
        integer bit_i;
        reg [31:0] c;
        reg feedback;
        begin
            c = state_in;
            for (byte_i = 0; byte_i < 4; byte_i = byte_i + 1)
                for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                    feedback = c[0] ^ data[byte_i*8+bit_i];
                    c = c >> 1;
                    if (feedback)
                        c = c ^ 32'h82f6_3b78;
                end
            crc32c_extend = c;
        end
    endfunction

    function automatic [31:0] packet_crc_one;
        input [31:0] data;
        begin
            packet_crc_one = crc32c_extend(32'hffff_ffff,data) ^ 32'hffff_ffff;
        end
    endfunction

    function automatic [31:0] packet_crc_two;
        input [31:0] data0;
        input [31:0] data1;
        reg [31:0] state;
        begin
            state = crc32c_extend(32'hffff_ffff,data0);
            packet_crc_two = crc32c_extend(state,data1) ^ 32'hffff_ffff;
        end
    endfunction

    // ------------------------------------------------------------------
    // Receiver.
    reg rx_link_valid = 1'b0;
    wire rx_link_ready;
    reg [31:0] rx_link_flit = 32'b0;
    reg [31:0] rx_link_flit_crc = 32'b0;
    reg [31:0] rx_link_packet_crc = 32'b0;
    reg rx_link_last = 1'b0;
    reg [3:0] rx_link_seq = 4'b0;
    wire rx_out_valid;
    reg rx_out_ready = 1'b1;
    wire [31:0] rx_out_flit;
    wire rx_out_last;
    wire [3:0] rx_out_seq;
    wire rx_out_poison;
    wire rx_ack_valid;
    wire [3:0] rx_ack_seq;
    wire rx_ack_ok;
    wire rx_protocol_error;
    wire rx_duplicate;
    integer rx_deliveries = 0;
    integer rx_good_acks = 0;
    integer rx_bad_acks = 0;

    ot_stage_link_rx #(.FLIT_W(32),.MAX_FLITS(4),.SEQ_W(4)) rx_dut (
        .clk(clk), .rst_n(rst_n), .link_valid(rx_link_valid),
        .link_ready(rx_link_ready), .link_flit(rx_link_flit),
        .link_flit_crc(rx_link_flit_crc),
        .link_packet_crc(rx_link_packet_crc), .link_last(rx_link_last),
        .link_packet_seq(rx_link_seq), .out_valid(rx_out_valid),
        .out_ready(rx_out_ready), .out_flit(rx_out_flit),
        .out_last(rx_out_last), .out_packet_seq(rx_out_seq),
        .out_poison(rx_out_poison), .ack_valid(rx_ack_valid),
        .ack_seq(rx_ack_seq), .ack_ok(rx_ack_ok),
        .protocol_error(rx_protocol_error), .duplicate_packet(rx_duplicate)
    );

    always @(posedge clk) begin
        if (rx_out_valid && rx_out_ready)
            rx_deliveries <= rx_deliveries + 1;
        if (rx_ack_valid) begin
            if (rx_ack_ok)
                rx_good_acks <= rx_good_acks + 1;
            else
                rx_bad_acks <= rx_bad_acks + 1;
        end
    end

    task automatic rx_send_flit;
        input [31:0] data;
        input last;
        input [3:0] seq;
        input [31:0] packet_crc;
        input corrupt_flit_crc;
        begin
            @(negedge clk);
            rx_link_flit = data;
            rx_link_flit_crc = crc32c_flit(data) ^
                               (corrupt_flit_crc ? 32'h0000_0001 : 32'b0);
            rx_link_packet_crc = packet_crc;
            rx_link_last = last;
            rx_link_seq = seq;
            rx_link_valid = 1'b1;
            while (!rx_link_ready)
                @(negedge clk);
            @(negedge clk);
            rx_link_valid = 1'b0;
        end
    endtask

    // ------------------------------------------------------------------
    // Transmitter.
    reg tx_in_valid = 1'b0;
    wire tx_in_ready;
    reg [31:0] tx_in_flit = 32'b0;
    reg tx_in_last = 1'b0;
    reg [3:0] tx_in_seq = 4'b0;
    reg tx_remote_credit = 1'b1;
    wire tx_credit_consumed;
    wire tx_link_valid;
    reg tx_link_ready = 1'b1;
    wire [31:0] tx_link_flit;
    wire [31:0] tx_link_flit_crc;
    wire [31:0] tx_link_packet_crc;
    wire tx_link_last;
    wire [3:0] tx_link_seq;
    reg tx_ack_valid = 1'b0;
    reg [3:0] tx_ack_seq = 4'b0;
    reg tx_ack_ok = 1'b0;
    reg tx_abort = 1'b0;
    wire tx_busy;
    wire [1:0] tx_retry_count;
    wire tx_timeout;
    wire tx_error;
    integer tx_sends = 0;
    integer tx_credit_pulses = 0;
    integer tx_timeout_pulses = 0;

    ot_stage_link_tx #(
        .FLIT_W(32), .MAX_FLITS(4), .SEQ_W(4), .RETRY_MAX(1), .ACK_TIMEOUT(3)
    ) tx_dut (
        .clk(clk), .rst_n(rst_n), .in_valid(tx_in_valid),
        .in_ready(tx_in_ready), .in_flit(tx_in_flit), .in_last(tx_in_last),
        .in_packet_seq(tx_in_seq), .remote_credit(tx_remote_credit),
        .credit_consumed(tx_credit_consumed), .link_valid(tx_link_valid),
        .link_ready(tx_link_ready), .link_flit(tx_link_flit),
        .link_flit_crc(tx_link_flit_crc),
        .link_packet_crc(tx_link_packet_crc), .link_last(tx_link_last),
        .link_packet_seq(tx_link_seq), .ack_valid(tx_ack_valid),
        .ack_seq(tx_ack_seq), .ack_ok(tx_ack_ok), .abort(tx_abort),
        .busy(tx_busy), .retry_count(tx_retry_count), .timeout(tx_timeout),
        .error(tx_error)
    );

    always @(posedge clk) begin
        if (tx_link_valid && tx_link_ready)
            tx_sends <= tx_sends + 1;
        if (tx_credit_consumed)
            tx_credit_pulses <= tx_credit_pulses + 1;
        if (tx_timeout)
            tx_timeout_pulses <= tx_timeout_pulses + 1;
    end

    task automatic tx_launch_single;
        input [31:0] data;
        input [3:0] seq;
        begin
            @(negedge clk);
            tx_in_flit = data;
            tx_in_seq = seq;
            tx_in_last = 1'b1;
            tx_in_valid = 1'b1;
            while (!tx_in_ready)
                @(negedge clk);
            @(negedge clk);
            tx_in_valid = 1'b0;
            while (!tx_link_valid)
                @(negedge clk);
            @(negedge clk);
        end
    endtask

    task automatic tx_ack;
        input [3:0] seq;
        input ok;
        begin
            @(negedge clk);
            tx_ack_seq = seq;
            tx_ack_ok = ok;
            tx_ack_valid = 1'b1;
            @(negedge clk);
            tx_ack_valid = 1'b0;
        end
    endtask

    integer before_deliver;
    integer before_good_ack;
    integer before_bad_ack;
    integer before_sends;
    integer before_credit;
    integer before_timeout;
    integer wait_cycles;
    reg [31:0] two_crc;

    initial begin
        reset_duts();

        before_deliver = rx_deliveries;
        before_bad_ack = rx_bad_acks;
        rx_send_flit(32'h1111_0001,1'b1,4'd0,
                     packet_crc_one(32'h1111_0001),1'b1);
        repeat (3) @(negedge clk);
        check_site("FC-LINK-RX-FLIT-CRC", rx_bad_acks == before_bad_ack + 1 &&
                   rx_deliveries == before_deliver && rx_protocol_error);

        reset_duts();
        before_deliver = rx_deliveries;
        before_bad_ack = rx_bad_acks;
        rx_send_flit(32'h2222_0002,1'b1,4'd0,
                     packet_crc_one(32'h2222_0002) ^ 32'h10,1'b0);
        repeat (3) @(negedge clk);
        check_site("FC-LINK-RX-PACKET-CRC", rx_bad_acks == before_bad_ack + 1 &&
                   rx_deliveries == before_deliver && rx_protocol_error);

        reset_duts();
        before_deliver = rx_deliveries;
        before_bad_ack = rx_bad_acks;
        two_crc = packet_crc_two(32'h3333_0003,32'h3333_0004);
        rx_send_flit(32'h3333_0003,1'b0,4'd0,two_crc,1'b0);
        rx_send_flit(32'h3333_0004,1'b1,4'd0,two_crc,1'b1);
        repeat (3) @(negedge clk);
        check_site("FC-LINK-RX-NO-PARTIAL", rx_bad_acks == before_bad_ack + 1 &&
                   rx_deliveries == before_deliver);

        // Establish sequence zero, then prove replay is acknowledged without
        // redelivery and a clean next sequence remains usable.
        reset_duts();
        before_deliver = rx_deliveries;
        before_good_ack = rx_good_acks;
        rx_send_flit(32'h4444_0004,1'b1,4'd0,
                     packet_crc_one(32'h4444_0004),1'b0);
        repeat (3) @(negedge clk);
        check_site("FC-LINK-RX-GOOD", rx_good_acks == before_good_ack + 1 &&
                   rx_deliveries == before_deliver + 1 && !rx_out_poison);

        before_deliver = rx_deliveries;
        before_good_ack = rx_good_acks;
        rx_send_flit(32'h4444_0004,1'b1,4'd0,
                     packet_crc_one(32'h4444_0004),1'b0);
        repeat (2) @(negedge clk);
        check_site("FC-LINK-RX-DUPLICATE", rx_good_acks == before_good_ack + 1 &&
                   rx_deliveries == before_deliver && rx_duplicate);

        before_deliver = rx_deliveries;
        before_bad_ack = rx_bad_acks;
        rx_send_flit(32'h5555_0005,1'b1,4'd2,
                     packet_crc_one(32'h5555_0005),1'b0);
        repeat (3) @(negedge clk);
        check_site("FC-LINK-RX-OUT-OF-ORDER", rx_bad_acks == before_bad_ack + 1 &&
                   rx_deliveries == before_deliver && rx_protocol_error);

        before_deliver = rx_deliveries;
        before_bad_ack = rx_bad_acks;
        two_crc = packet_crc_two(32'h6666_0006,32'h6666_0007);
        rx_send_flit(32'h6666_0006,1'b0,4'd1,two_crc,1'b0);
        rx_send_flit(32'h6666_0007,1'b1,4'd2,two_crc,1'b0);
        repeat (3) @(negedge clk);
        check_site("FC-LINK-RX-MIXED-SEQUENCE", rx_bad_acks == before_bad_ack + 1 &&
                   rx_deliveries == before_deliver);

        before_deliver = rx_deliveries;
        before_good_ack = rx_good_acks;
        rx_send_flit(32'h7777_0007,1'b1,4'd1,
                     packet_crc_one(32'h7777_0007),1'b0);
        repeat (3) @(negedge clk);
        check_site("FC-LINK-RX-RECOVERY", rx_good_acks == before_good_ack + 1 &&
                   rx_deliveries == before_deliver + 1);

        // Credit is consumed once per original packet, never once per retry.
        reset_duts();
        before_sends = tx_sends;
        before_credit = tx_credit_pulses;
        tx_launch_single(32'haaaa_0001,4'd3);
        tx_ack(4'd3,1'b0);
        wait_cycles = 0;
        while (tx_sends < before_sends + 2 && wait_cycles < 20) begin
            @(negedge clk);
            wait_cycles = wait_cycles + 1;
        end
        check_site("FC-LINK-TX-NAK-RETRY", tx_sends == before_sends + 2 &&
                   tx_retry_count == 1 && tx_busy);
        check_site("FC-LINK-TX-CREDIT-ONCE", tx_credit_pulses == before_credit + 1);
        tx_ack(4'd3,1'b1);
        repeat (2) @(negedge clk);

        reset_duts();
        before_sends = tx_sends;
        before_timeout = tx_timeout_pulses;
        tx_launch_single(32'hbbbb_0002,4'd4);
        wait_cycles = 0;
        while ((tx_timeout_pulses == before_timeout || tx_sends < before_sends + 2) &&
               wait_cycles < 30) begin
            @(negedge clk);
            wait_cycles = wait_cycles + 1;
        end
        check_site("FC-LINK-TX-TIMEOUT-RETRY", tx_timeout_pulses > before_timeout &&
                   tx_sends == before_sends + 2 && tx_retry_count == 1);
        tx_ack(4'd4,1'b1);
        repeat (2) @(negedge clk);

        reset_duts();
        before_sends = tx_sends;
        tx_launch_single(32'hcccc_0003,4'd5);
        tx_ack(4'd5,1'b0);
        while (tx_sends < before_sends + 2)
            @(negedge clk);
        tx_ack(4'd5,1'b0);
        repeat (3) @(negedge clk);
        check_site("FC-LINK-TX-RETRY-EXHAUST", tx_error && !tx_busy &&
                   tx_retry_count == 1);

        reset_duts();
        before_sends = tx_sends;
        tx_launch_single(32'hdddd_0004,4'd6);
        tx_ack(4'd7,1'b1);
        repeat (1) @(negedge clk);
        check_site("FC-LINK-TX-WRONG-ACK", tx_busy && tx_retry_count == 0 &&
                   tx_sends == before_sends + 1);
        tx_ack(4'd6,1'b1);
        repeat (2) @(negedge clk);

        reset_duts();
        tx_remote_credit = 1'b0;
        @(negedge clk);
        tx_in_valid = 1'b1;
        tx_in_last = 1'b1;
        tx_in_seq = 4'd7;
        tx_in_flit = 32'heeee_0005;
        repeat (3) @(negedge clk);
        check_site("FC-LINK-TX-CREDIT-GUARD", !tx_in_ready && !tx_busy);
        tx_in_valid = 1'b0;
        tx_remote_credit = 1'b1;

        reset_duts();
        tx_launch_single(32'hffff_0006,4'd8);
        @(negedge clk);
        tx_abort = 1'b1;
        @(negedge clk);
        tx_abort = 1'b0;
        repeat (3) @(negedge clk);
        check_site("FC-LINK-TX-ACK-WAIT-ABORT", tx_error && !tx_busy);

        if (failures == 0) begin
            $display("PASS: directed stage-link fault sites");
            $finish;
        end else begin
            $fatal(1,"%0d directed link fault sites failed",failures);
        end
    end
endmodule
