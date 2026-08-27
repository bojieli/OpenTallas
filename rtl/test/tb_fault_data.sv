`timescale 1ns/1ps
// Directed integrity/fault campaign for route records, immutable ROM repair/ECC,
// and the tagged HBM abstraction.  Every check emits a stable site identifier
// consumed by tools/rtl_fault_campaign.py; an overall PASS alone is insufficient.
module tb_fault_data;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    integer failures = 0;

    task automatic check_site;
        input [8*64-1:0] site_id;
        input condition;
        begin
            if (condition)
                $display("FAULT_SITE %0s PASS", site_id);
            else begin
                $display("FAULT_SITE %0s FAIL", site_id);
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

    // ------------------------------------------------------------------
    // Route-record integrity and deterministic duplicate handling.
    reg route_valid = 1'b0;
    reg [223:0] route_record = 224'b0;
    reg route_ctx_ready = 1'b0;
    wire route_ready;
    wire route_ctx_valid;
    wire [7:0] route_ctx_mask;
    wire [15:0] route_ctx_transaction;
    wire [7:0] route_ctx_epoch;
    wire [6:0] route_ctx_layer;
    wire [4:0] route_ctx_topk;
    wire route_ctx_poison;
    wire [15:0] route_ctx_duplicates;
    wire route_bad_crc;
    wire route_bad_field;

    ot_route_mask #(
        .NUM_EXPERTS(8), .TOP_K(4), .EXPERT_ID_W(10), .FIFO_DEPTH(2)
    ) route_dut (
        .clk(clk), .rst_n(rst_n), .route_valid(route_valid),
        .route_ready(route_ready), .route_record(route_record),
        .ctx_valid(route_ctx_valid), .ctx_ready(route_ctx_ready),
        .ctx_mask(route_ctx_mask), .ctx_transaction_id(route_ctx_transaction),
        .ctx_epoch_id(route_ctx_epoch), .ctx_layer_id(route_ctx_layer),
        .ctx_top_k_count(route_ctx_topk), .ctx_poison(route_ctx_poison),
        .ctx_duplicate_slots(route_ctx_duplicates),
        .bad_crc_seen(route_bad_crc), .bad_field_seen(route_bad_field)
    );

    function automatic [15:0] crc16_208;
        input [207:0] d;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg feedback;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 26; byte_i = byte_i + 1)
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    feedback = c[15] ^ d[byte_i*8+bit_i];
                    c = {c[14:0],1'b0};
                    if (feedback)
                        c = c ^ 16'h1021;
                end
            crc16_208 = c;
        end
    endfunction

    task automatic send_route;
        input [207:0] body;
        input corrupt_crc;
        reg [15:0] crc;
        begin
            crc = crc16_208(body);
            if (corrupt_crc)
                crc = crc ^ 16'h0001;
            @(negedge clk);
            route_record = {crc,body};
            route_valid = 1'b1;
            while (!route_ready)
                @(negedge clk);
            @(negedge clk);
            route_valid = 1'b0;
            while (!route_ctx_valid)
                @(negedge clk);
        end
    endtask

    task automatic pop_route;
        begin
            @(negedge clk);
            route_ctx_ready = 1'b1;
            @(negedge clk);
            route_ctx_ready = 1'b0;
        end
    endtask

    // ------------------------------------------------------------------
    // Immutable ROM with a non-power-of-two physical range so bad logical
    // addresses and bad repair targets are both representable.
    reg rom_req_valid = 1'b0;
    reg [1:0] rom_logical_addr = 2'b0;
    reg [7:0] rom_transaction = 8'b0;
    reg [3:0] rom_sequence = 4'b0;
    reg [2:0] rom_repair_valid = 3'b0;
    reg [5:0] rom_repair_map = 6'b0;
    reg rom_inject_fault = 1'b0;
    reg [1:0] rom_inject_addr = 2'b0;
    reg [15:0] rom_inject_mask = 16'b0;
    wire rom_req_ready;
    wire rom_rsp_valid;
    wire [15:0] rom_rsp_data;
    wire [7:0] rom_rsp_transaction;
    wire [3:0] rom_rsp_sequence;
    wire [1:0] rom_rsp_syndrome;
    wire rom_rsp_poison;

    ot_rom_wrapper #(
        .LOGICAL_DEPTH(3), .PHYS_DEPTH(3), .DATA_W(16), .READ_LATENCY(1),
        .TAG_W(8), .SEQ_W(4), .ADDR_W(2), .PHYS_ADDR_W(2)
    ) rom_dut (
        .clk(clk), .rst_n(rst_n), .req_valid(rom_req_valid),
        .req_ready(rom_req_ready), .logical_addr(rom_logical_addr),
        .transaction_id(rom_transaction), .seq_id(rom_sequence),
        .repair_valid(rom_repair_valid), .repair_map(rom_repair_map),
        .inject_fault(rom_inject_fault), .inject_fault_addr(rom_inject_addr),
        .inject_fault_mask(rom_inject_mask), .rsp_valid(rom_rsp_valid),
        .rsp_data(rom_rsp_data), .rsp_transaction_id(rom_rsp_transaction),
        .rsp_sequence(rom_rsp_sequence), .rsp_syndrome(rom_rsp_syndrome),
        .rsp_poison(rom_rsp_poison)
    );

    task automatic rom_read;
        input [1:0] logical_address;
        input [7:0] transaction;
        input [3:0] seq_value;
        begin
            @(negedge clk);
            rom_logical_addr = logical_address;
            rom_transaction = transaction;
            rom_sequence = seq_value;
            rom_req_valid = 1'b1;
            @(negedge clk);
            rom_req_valid = 1'b0;
            while (!rom_rsp_valid)
                @(negedge clk);
        end
    endtask

    // ------------------------------------------------------------------
    // Tagged HBM protocol/integrity checker.
    reg hbm_req_valid = 1'b0;
    wire hbm_req_ready;
    reg [63:0] hbm_req_address = 64'b0;
    reg [23:0] hbm_req_session = 24'b0;
    reg [11:0] hbm_req_tag = 12'b0;
    reg [15:0] hbm_req_beats_minus_one = 16'b0;
    reg [1:0] hbm_req_operation = 2'b0;
    wire hbm_req_accepted;
    reg hbm_rsp_valid = 1'b0;
    wire hbm_rsp_ready;
    reg [511:0] hbm_rsp_data = 512'b0;
    reg [63:0] hbm_rsp_byte_valid = 64'b0;
    reg [11:0] hbm_rsp_tag = 12'b0;
    reg hbm_rsp_last = 1'b0;
    reg [2:0] hbm_rsp_error = 3'b0;
    reg [15:0] hbm_rsp_crc = 16'b0;
    wire hbm_complete_valid;
    wire [11:0] hbm_complete_tag;
    wire [23:0] hbm_complete_session;
    wire hbm_complete_poison;
    wire [2:0] hbm_complete_error;
    wire hbm_protocol_error;
    wire [2:0] hbm_outstanding;
    reg captured_complete;
    reg captured_poison;
    reg [2:0] captured_error;
    reg [11:0] captured_tag;
    reg [23:0] captured_session;
    reg recycle_conserved;

    ot_hbm_frontend #(
        .TAGS(3), .MAX_OUTSTANDING(2), .TAG_W(2), .COUNT_W(17), .CHECK_CRC(1)
    ) hbm_dut (
        .clk(clk), .rst_n(rst_n), .req_valid(hbm_req_valid),
        .req_ready(hbm_req_ready), .req_byte_address(hbm_req_address),
        .req_session_id(hbm_req_session), .req_tag(hbm_req_tag),
        .req_burst_beats_minus_one(hbm_req_beats_minus_one),
        .req_operation(hbm_req_operation), .req_size_log2_bytes(6'd6),
        .req_stage_id(4'd0), .req_accepted(hbm_req_accepted),
        .rsp_valid(hbm_rsp_valid), .rsp_ready(hbm_rsp_ready),
        .rsp_data(hbm_rsp_data), .rsp_byte_valid(hbm_rsp_byte_valid),
        .rsp_tag(hbm_rsp_tag), .rsp_last(hbm_rsp_last),
        .rsp_error(hbm_rsp_error), .rsp_crc(hbm_rsp_crc),
        .complete_valid(hbm_complete_valid), .complete_tag(hbm_complete_tag),
        .complete_session_id(hbm_complete_session),
        .complete_poison(hbm_complete_poison),
        .complete_error(hbm_complete_error), .protocol_error(hbm_protocol_error),
        .outstanding_count(hbm_outstanding)
    );

    function automatic [15:0] crc16_592;
        input [591:0] d;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg feedback;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 74; byte_i = byte_i + 1)
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    feedback = c[15] ^ d[byte_i*8+bit_i];
                    c = {c[14:0],1'b0};
                    if (feedback)
                        c = c ^ 16'h1021;
                end
            crc16_592 = c;
        end
    endfunction

    task automatic hbm_issue;
        input [11:0] tag;
        input [15:0] beats_minus_one;
        input [23:0] session;
        begin
            @(negedge clk);
            hbm_req_tag = tag;
            hbm_req_beats_minus_one = beats_minus_one;
            hbm_req_session = session;
            hbm_req_address = {48'b0,tag,4'b0};
            hbm_req_valid = 1'b1;
            if (!hbm_req_ready) begin
                $display("HBM request unexpectedly blocked tag=%0d", tag);
                failures = failures + 1;
            end
            @(negedge clk);
            hbm_req_valid = 1'b0;
        end
    endtask

    task automatic hbm_response;
        input [11:0] tag;
        input last;
        input [2:0] response_error;
        input corrupt_crc;
        reg [591:0] body;
        reg [15:0] crc;
        begin
            @(negedge clk);
            hbm_rsp_data = {16{32'h1357_9bdf}} ^ {{500{1'b0}},tag};
            hbm_rsp_byte_valid = 64'hffff_ffff_ffff_ffff;
            hbm_rsp_tag = tag;
            hbm_rsp_last = last;
            hbm_rsp_error = response_error;
            body = {response_error,last,tag,hbm_rsp_byte_valid,hbm_rsp_data};
            crc = crc16_592(body);
            if (corrupt_crc)
                crc = crc ^ 16'h0080;
            hbm_rsp_crc = crc;
            hbm_rsp_valid = 1'b1;
            @(posedge clk);
            #1;
            captured_complete = hbm_complete_valid;
            captured_poison = hbm_complete_poison;
            captured_error = hbm_complete_error;
            captured_tag = hbm_complete_tag;
            captured_session = hbm_complete_session;
            @(negedge clk);
            hbm_rsp_valid = 1'b0;
        end
    endtask

    reg [207:0] route_body;
    initial begin
        // Initialize immutable model contents as a macro-load fixture, never
        // through a functional or test write interface.
        rom_dut.mem[0] = 16'h1234;
        rom_dut.mem[1] = 16'h5678;
        rom_dut.mem[2] = 16'h9abc;

        reset_duts();

        route_body = 208'b0;
        route_body[0 +: 10] = 10'd2;
        route_body[160 +: 16] = 16'h1001;
        route_body[176 +: 8] = 8'h2a;
        route_body[184 +: 7] = 7'd4;
        route_body[191 +: 5] = 5'd1;
        send_route(route_body,1'b1);
        check_site("FC-ROUTE-CRC", route_ctx_poison && route_bad_crc &&
                   route_ctx_mask == 8'h04);
        pop_route();

        route_body = 208'b0;
        route_body[0 +: 10] = 10'd8;
        route_body[191 +: 5] = 5'd1;
        send_route(route_body,1'b0);
        check_site("FC-ROUTE-RANGE", route_ctx_poison && route_bad_field &&
                   route_ctx_mask == 8'b0);
        pop_route();

        reset_duts();
        route_body = 208'b0;
        route_body[0 +: 10] = 10'd3;
        route_body[10 +: 10] = 10'd3;
        route_body[191 +: 5] = 5'd2;
        send_route(route_body,1'b0);
        check_site("FC-ROUTE-DUPLICATE", !route_ctx_poison &&
                   route_ctx_mask == 8'h08 && route_ctx_duplicates[1]);
        pop_route();

        route_body = 208'b0;
        route_body[0 +: 10] = 10'd1;
        route_body[191 +: 5] = 5'd1;
        route_body[200] = 1'b1;
        send_route(route_body,1'b0);
        check_site("FC-ROUTE-RESERVED", route_ctx_poison && route_bad_field);
        pop_route();

        route_body = 208'b0;
        route_body[0 +: 10] = 10'd1;
        route_body[191 +: 5] = 5'd0;
        send_route(route_body,1'b0);
        check_site("FC-ROUTE-TOPK", route_ctx_poison && route_bad_field);
        pop_route();

        // Correctable injection must never expose a corrupt architectural word.
        reset_duts();
        rom_inject_fault = 1'b1;
        rom_inject_addr = 2'd0;
        rom_inject_mask = 16'h0001;
        rom_read(2'd0,8'ha1,4'h3);
        check_site("FC-ROM-SINGLE-BIT", rom_rsp_syndrome == 2'b01 &&
                   !rom_rsp_poison && rom_rsp_data == 16'h1234 &&
                   rom_rsp_transaction == 8'ha1 && rom_rsp_sequence == 4'h3);

        rom_inject_mask = 16'h0003;
        rom_read(2'd0,8'ha2,4'h4);
        check_site("FC-ROM-MULTI-BIT", rom_rsp_syndrome == 2'b10 &&
                   rom_rsp_poison);

        rom_inject_fault = 1'b0;
        rom_inject_mask = 16'b0;
        rom_repair_valid = 3'b001;
        rom_repair_map = 6'b0;
        rom_repair_map[0 +: 2] = 2'd2;
        rom_read(2'd0,8'ha3,4'h5);
        check_site("FC-ROM-REPAIR-VALID", !rom_rsp_poison &&
                   rom_rsp_data == 16'h9abc);

        rom_repair_valid = 3'b010;
        rom_repair_map = 6'b0;
        rom_repair_map[2 +: 2] = 2'd3;
        rom_read(2'd1,8'ha4,4'h6);
        check_site("FC-ROM-REPAIR-RANGE", rom_rsp_poison &&
                   rom_rsp_syndrome == 2'b00);

        rom_repair_valid = 3'b0;
        rom_read(2'd3,8'ha5,4'h7);
        check_site("FC-ROM-ADDRESS-RANGE", rom_rsp_poison &&
                   rom_rsp_data == 16'b0);

        // HBM CRC corruption is terminal for that tag and cannot contaminate
        // a later, unrelated request.
        reset_duts();
        hbm_issue(12'd0,16'd0,24'h101001);
        hbm_response(12'd0,1'b1,3'b000,1'b1);
        check_site("FC-HBM-CRC", captured_complete && captured_poison &&
                   captured_error == 3'b110 && captured_session == 24'h101001 &&
                   hbm_outstanding == 0);

        hbm_issue(12'd1,16'd0,24'h101002);
        hbm_response(12'd1,1'b1,3'b000,1'b0);
        check_site("FC-HBM-RECOVERY", captured_complete && !captured_poison &&
                   captured_error == 3'b000 && captured_session == 24'h101002 &&
                   hbm_outstanding == 0);

        reset_duts();
        hbm_response(12'd2,1'b1,3'b000,1'b0);
        check_site("FC-HBM-WRONG-TAG", captured_complete && captured_poison &&
                   captured_error == 3'b111 && captured_tag == 12'd2 &&
                   hbm_outstanding == 0);

        reset_duts();
        hbm_issue(12'd0,16'd1,24'h202001);
        hbm_response(12'd0,1'b1,3'b000,1'b0);
        check_site("FC-HBM-EARLY-LAST", captured_complete && captured_poison &&
                   hbm_protocol_error && hbm_outstanding == 0);

        reset_duts();
        hbm_issue(12'd0,16'd0,24'h202002);
        hbm_response(12'd0,1'b0,3'b000,1'b0);
        check_site("FC-HBM-LATE-LAST", captured_complete && captured_poison &&
                   hbm_protocol_error && hbm_outstanding == 0);

        reset_duts();
        hbm_issue(12'd0,16'd0,24'h202003);
        hbm_response(12'd0,1'b1,3'b101,1'b0);
        check_site("FC-HBM-ERROR-STATUS", captured_complete && captured_poison &&
                   captured_error == 3'b101 && hbm_outstanding == 0);

        // The minus-one field's all-ones encoding is 65,536, not zero.
        reset_duts();
        hbm_issue(12'd0,16'hffff,24'h303001);
        check_site("FC-HBM-MAX-BURST", hbm_outstanding == 1 &&
                   hbm_dut.expected_beats[0] == 17'h1_0000);

        // A completion and a different-tag admission can share a cycle.  The
        // outstanding reservation must remain one and the new tag must own it.
        reset_duts();
        hbm_issue(12'd0,16'd0,24'h303002);
        @(negedge clk);
        hbm_req_tag = 12'd1;
        hbm_req_beats_minus_one = 16'd0;
        hbm_req_session = 24'h303003;
        hbm_req_address = 64'h40;
        hbm_req_valid = 1'b1;
        hbm_rsp_data = {16{32'h1357_9bdf}};
        hbm_rsp_byte_valid = 64'hffff_ffff_ffff_ffff;
        hbm_rsp_tag = 12'd0;
        hbm_rsp_last = 1'b1;
        hbm_rsp_error = 3'b000;
        hbm_rsp_crc = crc16_592({3'b000,1'b1,12'd0,
                                 64'hffff_ffff_ffff_ffff,
                                 {16{32'h1357_9bdf}}});
        hbm_rsp_valid = 1'b1;
        @(posedge clk);
        #1;
        recycle_conserved = hbm_req_accepted && hbm_complete_valid &&
                             !hbm_complete_poison &&
                             hbm_complete_session == 24'h303002 &&
                             hbm_outstanding == 1 && hbm_dut.active[1] &&
                             !hbm_dut.active[0];
        @(negedge clk);
        hbm_req_valid = 1'b0;
        hbm_rsp_valid = 1'b0;
        hbm_response(12'd1,1'b1,3'b000,1'b0);
        check_site("FC-HBM-SAME-CYCLE-RECYCLE", recycle_conserved &&
                   captured_complete && !captured_poison &&
                   captured_session == 24'h303003 && hbm_outstanding == 0);

        if (failures == 0) begin
            $display("PASS: directed route ROM and HBM fault sites");
            $finish;
        end else begin
            $fatal(1,"%0d directed data fault sites failed",failures);
        end
    end
endmodule
