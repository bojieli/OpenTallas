`timescale 1ns/1ps
// Distinct seq40/canonical-mode candidate, disabled by default.
// Historical9110 seq16 source is preserved.
// Candidate transport adapter. No region ABI or physical master adoption.
// commit_v must be the ACTUAL native write-commit event, not loader intent.
// commit_pending includes all accepted writes not yet committed. Writes remain
// reserved through GLOBAL release: one result is not a whole-operation snapshot.
module ot_qfd_vm_producer_lease_seq40 #(
    parameter integer ENABLE = 0, parameter integer MUT = 0
)(
    input wire clk, rst_n,
    input wire acquire_v, output wire acquire_ready,
    input wire [378:0] held_ib, input wire held_mode,
    input wire [15:0] held_context, input wire [3:0] request_phase,
    input wire [95:0] request_address, input wire [4:0] request_root,
    input wire [15:0] request_recipient,
    input wire query_v, output wire query_ready,
    input wire [15:0] query_context, input wire [31:0] query_version,
    input wire [39:0] query_seq40, input wire query_mode,
    input wire commit_v, commit_pending,
    output wire native_write_allowed,
    output wire [31:0] acquire_version,
    output wire read_v, input wire read_ready,
    output wire [378:0] read_ib, output wire read_mode,
    output wire [3:0] read_phase, output wire [95:0] read_address,
    output wire [4:0] read_root, output wire [15:0] read_recipient,
    output wire [39:0] read_seq40,
    input wire response_v, output wire response_ready,
    input wire [511:0] response_data,
    output wire q_v, input wire q_ready, output wire [511:0] q_data,
    output wire [15:0] q_context, output wire [31:0] q_version,
    output wire q_mode, output wire [3:0] q_phase,
    output wire [95:0] q_address, output wire [4:0] q_root,
    output wire [15:0] q_recipient, output wire [39:0] q_seq40,
    input wire release_v, output wire release_ready,
    input wire [15:0] release_context, input wire [31:0] release_version,
    input wire recipients_quiescent,
    output wire source_output_drained,
    input wire transport_flush_req, output wire transport_flush_ack,
    output reg fault,
    output reg [31:0] blocked_write_cycles, output reg [31:0] leased_cycles
);
    localparam IDLE=0, REQUEST=1, RESPONSE=2, OUTPUT=3, RETAIN=4;
    reg [2:0] state;
    reg armed;
    reg [31:0] version, snapshot_version;
    reg [378:0] descriptor;
    reg mode; reg [15:0] context_id;
    reg [3:0] phase; reg [95:0] address;
    reg [4:0] root; reg [15:0] recipient; reg [39:0] seq; reg seen_query;
    reg [511:0] payload;
    // Canonical native NW18/AW24 IB379 xjs slice (tile decoder line263).
    wire descriptor_mode = (held_ib[179:156] == 24'd0);
    wire match_release = release_context == context_id && release_version == snapshot_version;
    assign acquire_version = version;
    assign acquire_ready = ENABLE && armed && state==IDLE && !transport_flush_req &&
                            ((MUT==1) || (!commit_pending && !commit_v)) && ((MUT==10) || held_mode==descriptor_mode);
    // Pending acquisition stops new writes; drain already accepted writes first.
    assign native_write_allowed = !ENABLE || (!transport_flush_req &&
                    (state==IDLE && !acquire_v));
    assign read_v = ENABLE && state==REQUEST;
    assign read_ib = MUT==2 ? held_ib : descriptor;
    assign read_mode = MUT==8 ? (held_ib[179:156]==24'd0) : mode;
    assign read_phase=phase; assign read_address=address;
    assign read_root=root; assign read_recipient=recipient; assign read_seq40=seq;
    assign response_ready = ENABLE && state==RESPONSE;
    assign q_v = ENABLE && (state==OUTPUT || (MUT==3 && state==RETAIN));
    assign q_data = payload;
    assign q_context = context_id; assign q_version = snapshot_version;
    assign q_mode=mode; assign q_phase=phase; assign q_address=address;
    assign q_root=root; assign q_recipient=recipient; assign q_seq40=seq;
    assign query_ready = ENABLE && state==RETAIN && !release_v && !transport_flush_req &&
                         query_context==context_id && query_version==snapshot_version &&
                         ((MUT==7) || query_mode==mode);
    assign source_output_drained = !ENABLE || (state==RETAIN && !query_v);
    assign release_ready = ENABLE && state==RETAIN && !query_v && match_release &&
                           (recipients_quiescent || MUT==4);
    assign transport_flush_ack = ENABLE && transport_flush_req && state==IDLE &&
                                 !commit_pending && recipients_quiescent;
    always @(posedge clk) begin
        if (!rst_n) begin
            state<=IDLE; armed<=0; version<=0; snapshot_version<=0;
            descriptor<=0; mode<=0; context_id<=0; phase<=0; address<=0;
            root<=0; recipient<=0; seq<=0; seen_query<=0; payload<=0; fault<=0;
            blocked_write_cycles<=0; leased_cycles<=0;
        end else begin
            if (commit_v) version<=version+1;
            if (transport_flush_req) armed<=0;
            if (transport_flush_ack) armed<=1;
            if (ENABLE && !native_write_allowed) blocked_write_cycles<=blocked_write_cycles+1;
            if (ENABLE && state!=IDLE) leased_cycles<=leased_cycles+1;
            if (ENABLE && release_v && state!=RETAIN) fault<=1;
            if (ENABLE && release_v && state==RETAIN && !match_release) fault<=1;
            if (ENABLE && commit_v && state!=IDLE) fault<=1;
            case (state)
                IDLE: if (acquire_v && acquire_ready) begin
                    descriptor<=held_ib; mode<=descriptor_mode; context_id<=held_context;
                    snapshot_version<=version; seen_query<=0; state<=RETAIN;
                end
                REQUEST: if (read_v && read_ready) state<=RESPONSE;
                RESPONSE: if (response_v && response_ready) begin payload<=response_data; state<=OUTPUT; end
                OUTPUT: if (q_v && q_ready) state<=RETAIN;
                RETAIN: begin
                    if (MUT==5 && response_v) payload<=response_data;
                    if (release_v && release_ready) state<=IDLE;
                    else if (query_v && query_ready) begin
                        phase<=request_phase; address<=request_address; root<=request_root;
                        recipient<=request_recipient;
                        if (!(MUT==6 && seen_query)) seq<=MUT==9 ? {8'd0,query_seq40[31:0]} : query_seq40;
                        seen_query<=1; state<=REQUEST;
                    end
                end
                default: state<=IDLE;
            endcase
        end
    end
endmodule

// Native ROW binding: accepted decoded bank/address is independent of opaque IB.
// Drives actual re/ra/rq/rqb ports. RO is updated at edge +8; sampling at +9
// avoids reading the old value at the same NBA edge. No ENGINE/ME gating.
module ot_qfd_vm_producer_row_binding_seq40 #(
    parameter integer LAW=8, parameter integer MUT=0
)(
    input wire clk,rst_n, request_v, output wire request_ready,
    input wire [2:0] decoded_bank, input wire [LAW-1:0] decoded_row,
    output reg [7:0] re, output reg [8*LAW-1:0] ra,
    output reg rq, output reg [2:0] rqb,
    input wire [511:0] native_ro,
    output reg response_v, input wire response_ready,
    output reg [511:0] response_data,
    input wire accepted_write, output wire commit_v, output wire commit_pending
);
    reg [2:0] write_pipe;
    reg [3:0] age;
    reg busy;
    assign request_ready=!busy && !response_v;
    assign commit_v=write_pipe[2];
    assign commit_pending=|write_pipe;
    always @(posedge clk) begin
        if (!rst_n) begin
            re<=0; ra<=0; rq<=0; rqb<=0; busy<=0; age<=0;
            response_v<=0; response_data<=0; write_pipe<=0;
        end else begin
            write_pipe<={write_pipe[1:0],accepted_write};
            re<=0; rq<=0;
            if (response_v && response_ready) response_v<=0;
            if (request_v && request_ready) begin
                re<=8'b1<<decoded_bank;
                ra[decoded_bank*LAW+:LAW]<=decoded_row;
                rq<=1; rqb<=decoded_bank; busy<=1; age<=0;
            end else if (busy) begin
                age<=age+1;
                // Registered request reaches native ports one edge after accept.
                if (age==(MUT==1 ? 8 : 9)) begin
                    response_data<=native_ro; response_v<=1; busy<=0;
                end
            end
        end
    end
endmodule
