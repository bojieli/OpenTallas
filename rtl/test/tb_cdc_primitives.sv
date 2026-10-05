`timescale 1ns/1ps
module tb_cdc_primitives;
    reg src_clk = 1'b0;
    reg dst_clk = 1'b0;
    reg qual_clk = 1'b0;
    always #5 src_clk = ~src_clk;
    always #7 dst_clk = ~dst_clk;
    always #4 qual_clk = ~qual_clk;

    integer failures = 0;
    integer timeout_count;

    // Acknowledged mailbox.
    reg src_rst_n = 1'b0;
    reg dst_rst_n = 1'b0;
    reg mail_src_valid = 1'b0;
    wire mail_src_ready;
    reg [15:0] mail_src_data = 16'b0;
    wire mail_src_done;
    wire [3:0] mail_src_response;
    wire mail_dst_valid;
    reg mail_dst_ready = 1'b0;
    wire [15:0] mail_dst_data;
    reg [3:0] mail_dst_response = 4'b0;
    integer mail_transfers = 0;
    integer mail_completions = 0;

    ot_cdc_mailbox #(.WIDTH(16),.RESPONSE_W(4)) mailbox (
        .src_clk(src_clk), .src_rst_n(src_rst_n),
        .src_valid(mail_src_valid), .src_ready(mail_src_ready),
        .src_data(mail_src_data), .src_done(mail_src_done),
        .src_response(mail_src_response), .dst_clk(dst_clk),
        .dst_rst_n(dst_rst_n), .dst_valid(mail_dst_valid),
        .dst_ready(mail_dst_ready), .dst_data(mail_dst_data),
        .dst_response(mail_dst_response));

    always @(posedge dst_clk)
        if (mail_dst_valid && mail_dst_ready)
            mail_transfers = mail_transfers + 1;
    always @(posedge src_clk)
        if (mail_src_done)
            mail_completions = mail_completions + 1;

    task automatic wait_mail_ready;
        begin
            timeout_count = 0;
            while (!mail_src_ready && timeout_count < 80) begin
                @(negedge src_clk);
                timeout_count = timeout_count + 1;
            end
            if (!mail_src_ready) begin
                $display("FAIL mailbox source ready timeout");
                failures = failures + 1;
            end
        end
    endtask

    task automatic launch_mail;
        input [15:0] payload;
        begin
            wait_mail_ready();
            @(negedge src_clk);
            mail_src_data = payload;
            mail_src_valid = 1'b1;
            while (!mail_src_ready)
                @(negedge src_clk);
            @(negedge src_clk);
            mail_src_valid = 1'b0;
            // Once accepted, the producer may present unrelated next data;
            // the mailbox-owned hold register must preserve the transfer.
            mail_src_data = ~payload;
        end
    endtask

    task automatic wait_mail_dst;
        input [15:0] expected;
        begin
            timeout_count = 0;
            while (!mail_dst_valid && timeout_count < 80) begin
                @(negedge dst_clk);
                timeout_count = timeout_count + 1;
            end
            if (!mail_dst_valid) begin
                $display("FAIL mailbox destination valid timeout");
                failures = failures + 1;
            end else if (mail_dst_data !== expected) begin
                $display("FAIL mailbox payload got=%h expected=%h",mail_dst_data,expected);
                failures = failures + 1;
            end
        end
    endtask

    task automatic finish_mail;
        input [15:0] expected;
        input [3:0] response;
        input integer stalls;
        integer before_done;
        integer stall_i;
        begin
            wait_mail_dst(expected);
            for (stall_i = 0; stall_i < stalls; stall_i = stall_i + 1) begin
                @(negedge dst_clk);
                if (!mail_dst_valid || mail_dst_data !== expected) begin
                    $display("FAIL mailbox changed while backpressured");
                    failures = failures + 1;
                end
            end
            before_done = mail_completions;
            mail_dst_response = response;
            mail_dst_ready = 1'b1;
            @(negedge dst_clk);
            mail_dst_ready = 1'b0;
            timeout_count = 0;
            while (mail_completions == before_done && timeout_count < 80) begin
                @(negedge src_clk);
                timeout_count = timeout_count + 1;
            end
            if (mail_completions != before_done + 1) begin
                $display("FAIL mailbox completion timeout/duplication");
                failures = failures + 1;
            end else if (mail_src_response !== response) begin
                $display("FAIL mailbox response got=%h expected=%h",mail_src_response,response);
                failures = failures + 1;
            end
        end
    endtask

    // Qualified level synchronizer.
    reg qual_rst_n = 1'b0;
    reg qual_async = 1'b0;
    wire qual_sync;
    ot_sync_level #(.WIDTH(1),.QUAL_CYCLES(3)) qualified_level (
        .clk(qual_clk), .rst_n(qual_rst_n), .async_in(qual_async),
        .sync_out(qual_sync));

    task automatic wait_qual_value;
        input expected;
        input integer minimum_cycles;
        integer cycles;
        begin
            cycles = 0;
            while (qual_sync !== expected && cycles < 24) begin
                @(negedge qual_clk);
                cycles = cycles + 1;
            end
            if (qual_sync !== expected) begin
                $display("FAIL qualified level timeout expected=%b",expected);
                failures = failures + 1;
            end else if (cycles < minimum_cycles) begin
                $display("FAIL qualified level changed too early cycles=%0d min=%0d",cycles,minimum_cycles);
                failures = failures + 1;
            end
        end
    endtask

    // Reset-rendezvous asynchronous FIFO.
    reg fifo_wr_rst_n = 1'b0;
    reg fifo_rd_rst_n = 1'b0;
    reg fifo_wr_valid = 1'b0;
    wire fifo_wr_ready;
    reg [7:0] fifo_wr_data = 8'b0;
    wire fifo_wr_overflow;
    wire fifo_rd_valid;
    reg fifo_rd_ready = 1'b0;
    wire [7:0] fifo_rd_data;
    wire fifo_rd_underflow;

    ot_async_fifo #(.WIDTH(8),.DEPTH(4)) reset_fifo (
        .wr_clk(src_clk), .wr_rst_n(fifo_wr_rst_n),
        .wr_valid(fifo_wr_valid), .wr_ready(fifo_wr_ready),
        .wr_data(fifo_wr_data), .wr_overflow(fifo_wr_overflow),
        .rd_clk(dst_clk), .rd_rst_n(fifo_rd_rst_n),
        .rd_valid(fifo_rd_valid), .rd_ready(fifo_rd_ready),
        .rd_data(fifo_rd_data), .rd_underflow(fifo_rd_underflow));

    task automatic fifo_write;
        input [7:0] value;
        begin
            timeout_count = 0;
            while (!fifo_wr_ready && timeout_count < 80) begin
                @(negedge src_clk);
                timeout_count = timeout_count + 1;
            end
            if (!fifo_wr_ready) begin
                $display("FAIL FIFO write ready timeout");
                failures = failures + 1;
            end
            @(negedge src_clk);
            fifo_wr_data = value;
            fifo_wr_valid = 1'b1;
            @(negedge src_clk);
            fifo_wr_valid = 1'b0;
        end
    endtask

    task automatic fifo_read;
        input [7:0] expected;
        begin
            timeout_count = 0;
            while (!fifo_rd_valid && timeout_count < 80) begin
                @(negedge dst_clk);
                timeout_count = timeout_count + 1;
            end
            if (!fifo_rd_valid) begin
                $display("FAIL FIFO read valid timeout");
                failures = failures + 1;
            end else if (fifo_rd_data !== expected) begin
                $display("FAIL FIFO data got=%h expected=%h",fifo_rd_data,expected);
                failures = failures + 1;
            end
            fifo_rd_ready = 1'b1;
            @(negedge dst_clk);
            fifo_rd_ready = 1'b0;
        end
    endtask

    initial begin
        // Deliberately stagger initial reset release across all three clocks.
        repeat (3) @(negedge dst_clk);
        dst_rst_n = 1'b1;
        fifo_rd_rst_n = 1'b1;
        repeat (4) @(negedge src_clk);
        src_rst_n = 1'b1;
        fifo_wr_rst_n = 1'b1;
        repeat (2) @(negedge qual_clk);
        qual_rst_n = 1'b1;

        // Mailbox backpressure, payload stability, typed response, and reuse.
        launch_mail(16'ha55a);
        finish_mail(16'ha55a,4'h5,4);
        launch_mail(16'h0123);
        finish_mail(16'h0123,4'h9,0);

        // Destination reset while a request is backpressured: the operation is
        // replayed after reset, with no completion or payload corruption.
        launch_mail(16'hcafe);
        wait_mail_dst(16'hcafe);
        @(negedge dst_clk);
        dst_rst_n = 1'b0;
        repeat (3) @(negedge dst_clk);
        if (mail_dst_valid) begin
            $display("FAIL mailbox valid asserted in destination reset");
            failures = failures + 1;
        end
        dst_rst_n = 1'b1;
        finish_mail(16'hcafe,4'ha,2);

        // Source reset cancels an unconsumed operation.  Keep destination
        // backpressured so cancellation has no external side effect.
        launch_mail(16'hdead);
        wait_mail_dst(16'hdead);
        timeout_count = mail_completions;
        @(negedge src_clk);
        src_rst_n = 1'b0;
        repeat (3) @(negedge src_clk);
        src_rst_n = 1'b1;
        repeat (8) @(negedge dst_clk);
        if (mail_dst_valid || mail_completions != timeout_count) begin
            $display("FAIL mailbox source-reset cancellation");
            failures = failures + 1;
        end
        launch_mail(16'hbeef);
        finish_mail(16'hbeef,4'h3,1);

        // Short synchronized glitches do not become qualified output levels.
        @(negedge qual_clk);
        qual_async = 1'b1;
        @(negedge qual_clk);
        qual_async = 1'b0;
        repeat (8) @(negedge qual_clk);
        if (qual_sync !== 1'b0) begin
            $display("FAIL qualified level passed short high pulse");
            failures = failures + 1;
        end
        qual_async = 1'b1;
        wait_qual_value(1'b1,4);
        qual_async = 1'b0;
        @(negedge qual_clk);
        qual_async = 1'b1;
        repeat (8) @(negedge qual_clk);
        if (qual_sync !== 1'b1) begin
            $display("FAIL qualified level passed short low pulse");
            failures = failures + 1;
        end
        qual_async = 1'b0;
        wait_qual_value(1'b0,4);

        // FIFO ordering before reset.
        fifo_write(8'h11);
        fifo_write(8'h22);
        fifo_write(8'h33);
        fifo_read(8'h11);
        fifo_read(8'h22);
        fifo_read(8'h33);

        // Either-side reset flushes both pointer domains and closes ready/valid.
        fifo_write(8'haa);
        fifo_write(8'hbb);
        @(negedge dst_clk);
        fifo_rd_rst_n = 1'b0;
        #1;
        if (fifo_wr_ready || fifo_rd_valid) begin
            $display("FAIL FIFO did not close on read-side reset");
            failures = failures + 1;
        end
        repeat (3) @(negedge dst_clk);
        fifo_rd_rst_n = 1'b1;
        repeat (10) @(negedge dst_clk);
        if (fifo_rd_valid) begin
            $display("FAIL FIFO retained pre-reset payload");
            failures = failures + 1;
        end
        fifo_write(8'h44);
        fifo_read(8'h44);

        fifo_write(8'h55);
        @(negedge src_clk);
        fifo_wr_rst_n = 1'b0;
        #1;
        if (fifo_wr_ready || fifo_rd_valid) begin
            $display("FAIL FIFO did not close on write-side reset");
            failures = failures + 1;
        end
        repeat (2) @(negedge src_clk);
        fifo_wr_rst_n = 1'b1;
        repeat (10) @(negedge dst_clk);
        if (fifo_rd_valid) begin
            $display("FAIL FIFO retained payload after write-side reset");
            failures = failures + 1;
        end
        fifo_write(8'h66);
        fifo_read(8'h66);

        if (fifo_wr_overflow || fifo_rd_underflow) begin
            $display("FAIL FIFO diagnostic flag asserted on legal traffic");
            failures = failures + 1;
        end
        if (mail_transfers != mail_completions) begin
            $display("FAIL mailbox transfer/completion mismatch transfers=%0d completions=%0d",
                     mail_transfers,mail_completions);
            failures = failures + 1;
        end

        if (failures == 0) begin
            $display("PASS: CDC mailbox, qualified level, and reset-rendezvous FIFO");
            $finish;
        end else begin
            $fatal(1,"%0d CDC primitive failures",failures);
        end
    end
endmodule
