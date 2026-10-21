`timescale 1ns/1ps
`default_nettype none
// Six fixed launches of REAL KS descriptors. This is an opt-in adapter on the
// existing HOST_EN=1 path, not a token generator or a completion-driven issuer.
// SYNC CSR 0x19 first supplies graph tag d[39:8] and global capture-edge
// timestamp d[87:40]. A real local counter then advances that explicit epoch;
// ARM's epoch must match it exactly. No global-zero assumption is made.
// ARM CSR 0x17 (class 0, d=f_host[512:1]):
// d[39:8] graph tag; [87:40] absolute epoch AT THIS CSR CAPTURE EDGE;
// [135:88] first KS capture edge at the original seqhost input;
// [183:136] first issuer-command edge from the actual stage programme;
// [193:184] owner; [195:194] actual issuer phase at the epoch edge.
// The actual PW row-0 issue age and seal phase are observed on the same host
// path. No default global epoch, descriptor token, or position is synthesized.
// The host must account for its real transport latency when constructing ARM.
// Six KS descriptors arriving AFTER ARM are retained unchanged and emitted at
// first_ks + n*SPAN. Missing/late data faults; it never moves a deadline.
module dsdv_static_ks6 #(
    parameter integer SPAN = 1259408,
    parameter [31:0] GRAPH_TAG = 32'h218d375d,
    parameter integer NOPS = 128
) (
    input wire ck, rst_n,
    input wire [514:0] f_host,
    input wire [52:0] f_ks,
    input wire upstream_fault,
    output reg [52:0] timed_ks,
    output reg selected,
    output reg armed,
    output reg done,
    output reg [3:0] fault
);
    wire hv = f_host[0];
    wire [511:0] hd = f_host[512:1];
    wire csr = hv && f_host[514:513] == 2'd0;
    wire arm = csr && hd[7:0] == 8'h17;
    wire disarm = csr && hd[7:0] == 8'h18;
    wire sync_epoch = csr && hd[7:0] == 8'h19;
    wire pw = csr && hd[7:0] == 8'h10;
    wire [6:0] pa = hd[102:96];
    wire [27:0] pd = hd[59:32];
    wire prog_write = csr && (hd[7:0] == 8'h10 || hd[7:0] == 8'h11 ||
                                      hd[7:0] == 8'h13 || hd[7:0] == 8'h14);
    reg [23:0] first_issue;
    reg first_seen, sealed;
    reg [7:0] prog_len, settle;
    reg [1:0] seal_phase;
    reg epoch_valid;
    reg [47:0] global_edge;
    reg [9:0] owner;
    // 312 payload bits: below the 2-kbit SRAM threshold. Data is unreset.
    reg [6*52-1:0] descriptors;
    reg [5:0] valid;
    reg [2:0] wr, rd;
    reg [23:0] wait_edges;
    wire [47:0] epoch = hd[87:40];
    wire [47:0] first_ks = hd[135:88];
    wire [47:0] first_cmd = hd[183:136];
    wire [47:0] delta = first_ks - epoch;
    // Issuer samples KS at +3 and accepts only when phase_q+1 equals
    // the sealed start phase: +4 is zero modulo the four-phase cycle.
    wire [1:0] expected_phase = hd[195:194] + delta[1:0];
    wire bad_arm = hd[39:8] != GRAPH_TAG || !epoch_valid || epoch != global_edge || first_ks <= epoch ||
                   delta[47:24] != 0 || delta < 3 || !first_seen || !sealed || settle != 0 ||
                   first_cmd != first_ks + 48'd4 + {24'd0, first_issue} ||
                   expected_phase != seal_phase || (selected && !done) || f_ks[52];
    wire bad_desc = selected && f_ks[52] &&
                    (!armed || wr >= 6 || f_ks[51:42] != owner);
    wire config_race = selected && armed && (prog_write || sync_epoch);
    wire immediate_bad = upstream_fault || bad_desc || config_race || (arm && bad_arm);
    initial begin
        if (SPAN < 4 || SPAN >= (1<<24) || (SPAN % 4) != 0 || NOPS > 239)
            $fatal(1, "static KS: invalid immutable schedule parameters");
    end
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            timed_ks <= 0; selected <= 0; armed <= 0; done <= 0; fault <= 0;
            valid <= 0; wr <= 0; rd <= 0; wait_edges <= 0; owner <= 0;
            first_issue <= 0; first_seen <= 0; sealed <= 0; prog_len <= 0;
            settle <= 0; seal_phase <= 0;
            epoch_valid <= 0; global_edge <= 0;
        end else begin
            timed_ks <= 0;
            if (epoch_valid) global_edge <= global_edge + 1'b1;
            if (sync_epoch && !(selected && armed)) begin
                if (hd[39:8] != GRAPH_TAG) begin fault[1] <= 1; epoch_valid <= 0; end
                else begin
                    epoch_valid <= 1;
                    // global_edge represents the NEXT capture edge after
                    // SYNC, hence the +1 on the synchronizing edge itself.
                    global_edge <= hd[87:40] + 1'b1;
                end
            end
            if (settle != 0) settle <= settle - 1'b1;
            if (csr && hd[7:0] == 8'h11) prog_len <= hd[39:32];
            if (pw && pd[27:26] == 3 && !pd[25]) begin
                first_seen <= 0; sealed <= 0; settle <= 0;
            end
            if (pw && pa == 0 && pd[27:26] == 1) begin
                first_issue <= pd[25:2]; first_seen <= 1;
            end
            if (pw && pd[27:26] == 3 && pd[25]) begin
                sealed <= first_seen && prog_len != 0 && prog_len == pd[16:9];
                seal_phase <= pd[8:7];
                // The real walker performs a one-row/edge seal scan. This
                // conservative fixed BOOT guard covers its staging; it does
                // not delay a token or wait for a completion.
                settle <= NOPS + 16;
            end
            if (upstream_fault && selected) fault[3] <= 1;
            if (bad_desc) fault[0] <= 1;
            if (config_race) fault[1] <= 1;
            if (arm) begin
                selected <= 1;
                if (bad_arm || fault != 0 || upstream_fault) begin
                    fault[1] <= 1; armed <= 0;
                end else begin
                    owner <= hd[193:184]; valid <= 0; wr <= 0; rd <= 0;
                    wait_edges <= delta[23:0] - 1'b1;
                    armed <= 1; done <= 0;
                end
            end else if (fault != 0 || immediate_bad) begin
                armed <= 0;
            end else if (selected && armed) begin
                if (f_ks[52]) begin
                    descriptors[52*wr +: 52] <= f_ks[51:0];
                    valid[wr] <= 1; wr <= wr + 1'b1;
                end
                if (wait_edges > 1) wait_edges <= wait_edges - 1'b1;
                else if (wait_edges == 1) begin
                    // Registered output is sampled by the original seqhost
                    // on the following edge: exactly the declared KS edge.
                    if (rd >= 6 || !valid[rd]) begin
                        fault[0] <= 1; armed <= 0;
                    end else begin
                        timed_ks <= {1'b1, descriptors[52*rd +: 52]};
                        valid[rd] <= 0;
                        if (rd == 5) begin armed <= 0; done <= 1; end
                        else begin rd <= rd + 1'b1; wait_edges <= SPAN; end
                    end
                end
            end
            if (disarm) begin
                if (done && !armed && fault == 0) begin selected <= 0; done <= 0; end
                else begin fault[2] <= 1; armed <= 0; end
            end
        end
    end
endmodule
`default_nettype wire
