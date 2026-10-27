(* keep_hierarchy, keep *)
module ot_dp_rrelay (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule

(* keep_hierarchy, keep *)
module ot_dp_rgate (input wire clk, input wire d, input wire run, output reg q);
    always @(posedge clk) q <= d & run;
endmodule

(* keep_hierarchy *)
module ot_dp_rsync_s2 (input wire clk, input wire async_rst_n, output wire sync_rst_n);
    // Intentional reset CDC shift register; only this async_reg declaration
    // mixes asynchronous assertion with synchronous release/feedback.
    /* verilator lint_off SYNCASYNCNET */
    (* async_reg = "true" *) reg [1:0] p;
    /* verilator lint_on SYNCASYNCNET */
    always @(posedge clk or negedge async_rst_n)
        if (!async_rst_n) p <= 2'b0; else p <= {p[0], 1'b1};
    assign sync_rst_n = p[1];
endmodule

(* keep_hierarchy *)
module ot_dp_rsync_s3 (input wire clk, input wire async_rst_n, output wire sync_rst_n);
    // Intentional reset CDC shift register; only this async_reg declaration
    // mixes asynchronous assertion with synchronous release/feedback.
    /* verilator lint_off SYNCASYNCNET */
    (* async_reg = "true" *) reg [2:0] p;
    /* verilator lint_on SYNCASYNCNET */
    always @(posedge clk or negedge async_rst_n)
        if (!async_rst_n) p <= 3'b0; else p <= {p[1:0], 1'b1};
    assign sync_rst_n = p[2];
endmodule

(* keep_hierarchy, keep *)
module ot_dp_lockq #(parameter integer STABLE = 16) (input wire clk, input wire d, input wire locked, output reg q);
    localparam integer CW = $clog2(STABLE + 1);
    (* async_reg = "true" *) reg [1:0] ls;
    reg [CW-1:0] cnt;
    wire stable = (cnt == STABLE);
    always @(posedge clk) begin
        if (!d) begin
            ls <= 2'b00;
            cnt <= {CW{1'b0}};
            q <= 1'b0;
        end else begin
            ls <= {ls[0], locked};
            if (!ls[1]) cnt <= {CW{1'b0}};
            else if (!stable) cnt <= cnt + 1'b1;
            q <= q | stable;
        end
    end
endmodule
