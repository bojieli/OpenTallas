`timescale 1ns/1ps
module ot_qwen_d2d_list_play_f5_shared #(parameter integer AW = 11, parameter integer MIN_DT = 4, parameter integer MUT_HALT_REWIND = 0, parameter [AW-1:0] WRAP_ADDR = '0, parameter integer FRESH_WARM_OWNER = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          go,            // anchor: entry 0's dt counts from this edge
    input  wire          halt,
    output wire [AW-1:0] rom_addr,
    input  wire [31:0]   rom_q,
    output reg           start,
    output reg           seg,
    output reg  [1:0]    user,
    output reg           running,
    output reg           fault
);
    reg [AW-1:0] addr;
    reg [31:0]   nxt;
    reg          nv;
    reg [1:0]    age;
    reg [19:0]   cnt;
    reg [31:0]   cur;
    assign rom_addr = addr;
    wire owner_ready;
    generate if (FRESH_WARM_OWNER != 0) begin : g_fresh_warm_owner
        // The initial frame can contain a warm tail from before this epoch.
        // Publish a warm start only after this owner has had a cold start.
        reg [3:0] seen_cold;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) seen_cold <= 4'd0;
            else if (halt || go) seen_cold <= 4'd0;
            else if (running && cnt == 20'd1 && cur[11] && cur[10])
                seen_cold[cur[9:8]] <= 1'b1;
        assign owner_ready = cur[10] || seen_cold[cur[9:8]];
    end else begin : g_all_warm
        assign owner_ready = 1'b1;
    end endgenerate
    wire bad_n = (nxt[31:12] < MIN_DT) || (|nxt[6:0]);
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            addr <= '0; nxt <= 32'd0; nv <= 1'b0; age <= 2'd0; cnt <= 20'd0; cur <= 32'd0;
            start <= 1'b0; seg <= 1'b0; user <= 2'd0; running <= 1'b0; fault <= 1'b0;
        end else begin
            start <= 1'b0;
            // prefetch: the ROM word of addr is stable two edges after addr moved
            if (!nv) begin
                if (age == 2'd2) begin nxt <= rom_q; nv <= 1'b1; end
                else age <= age + 2'd1;
            end
            if (halt) begin
                running <= 1'b0;
                // Epoch recovery restarts the compiled frame at word0. A prefetched mid-frame word must not
                // survive an abort; prefetch begins again after halt/reload is released, before the next anchor.
                if (!MUT_HALT_REWIND) begin
                    addr <= '0; nxt <= 32'd0; nv <= 1'b0; age <= 2'd0;
                    cnt <= 20'd0; cur <= 32'd0; seg <= 1'b0; user <= 2'd0;
                end
            end
            else if (go || (running && cnt == 20'd1)) begin
                if (go && running) fault <= 1'b1;
                if (!go && cur[11] && owner_ready) begin start <= 1'b1; seg <= cur[10]; user <= cur[9:8]; end
                if (!nv || bad_n) fault <= 1'b1;
                running <= 1'b1;
                cur <= nxt; cnt <= nxt[31:12]; nv <= 1'b0; age <= 2'd0;
                addr <= nxt[7] ? WRAP_ADDR : addr + 1'b1;
            end else if (running) cnt <= cnt - 20'd1;
        end
    end
endmodule
