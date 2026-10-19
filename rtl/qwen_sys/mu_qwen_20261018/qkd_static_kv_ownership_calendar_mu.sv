`timescale 1ns/1ps
// MU-KV-PROG 10-19 (Qwen ROM 4 users): multi-user successor of qkd_static_kv_ownership_calendar (same ports + MU; the
// original file is untouched).  The ownership calendar is the one consumer of the KV layer programme in qkd_kvs_ctl that
// holds per-TOKEN state: go (qkd_kv_ownership_obs: stage_start of stage 1) opens a window of compiled length (enter /
// leave / deadline roots = a whole token) and a go while that window is active is a fault (bad[2]).  Under
// qkd_static_kv_layer_programme_mu the 4 users' tokens overlap on the KV die, so the second user's stage-1 start would
// fault the die (audit: results/rtl/mu_qwen_1018/kvprog/README.md).
//   MU 0: instantiates the unchanged original (behaviour-identical by construction).
//   MU 1: the window is RE-ARMED by every go (cycle restarts at 0; native_reserved stays 1; native_mode keeps its value),
//         so the KV die stays natively owned from the first token start until leave / deadline after the LAST start.
//         enter checks host / upstream quiet and the drains only on the host -> native transition (native_mode 0);
//         leave checks them on the native -> host transition, which is reached only leave_root after the last go.
//         The compiler boots leave_root / deadline_root as the maximum over users of the user's go -> stage-36 quiet + 1
//         and go -> token end (its GAP bubbles included), so every user that started before the last go is covered.
//         With one user (gos never inside an active window, as the original requires) every edge equals the original.
//   No ready / credit / stall: a go never waits; a go while unconfigured or during a boot write is a fault as before.
// MUT (bench negative controls, MU 1): 5 = shared single window (a go while active faults = the original, bad[2]);
//   6 = enter re-checks quiet / drains on every re-armed window (not only on the transition); 7 = no re-arm (the window
//   runs from the first go only; later gos are ignored).  1-3 as the original.
// PIPE (MU-KV-CTL3 10-19, = KV-CTL mu2 PIPE of the original; 0 = unchanged): the 32-group drain AND gets its own register
//   (drained_all_q, guards see the drain 1 edge earlier vs the compiled roots: compiler QUIET / drain window +1 ck before
//   enter / leave) and the root - k compare offsets are captured with the root words (roots are static once sealed).
module qkd_static_kv_ownership_calendar_mu #(parameter integer MUT = 0, parameter integer MU = 0, parameter integer PIPE = 0, parameter integer SAFE = 0) (
    input wire ck, rst_n,
    input wire cfg_we, input wire [1:0] cfg_addr, input wire [31:0] cfg_data,
    input wire go,
    input wire host_quiet, upstream_quiet,
    input wire [31:0] group_drained, group_fault,
    output wire native_mode, ownership_valid, native_reserved,
    output wire active, done, configured,
    output wire [31:0] cycle,
    output wire fault, output wire [7:0] fault_code
);
generate if (MU == 0) begin : g_plain
    qkd_static_kv_ownership_calendar #(.MUT(MUT), .PIPE(PIPE)) u_plain (.ck(ck), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .go(go), .host_quiet(host_quiet), .upstream_quiet(upstream_quiet),
        .group_drained(group_drained), .group_fault(group_fault), .native_mode(native_mode),
        .ownership_valid(ownership_valid), .native_reserved(native_reserved), .active(active), .done(done),
        .configured(configured), .cycle(cycle), .fault(fault), .fault_code(fault_code));
end else begin : g_mu
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    reg we_q, go_q, host_q, upstream_q;
    reg [1:0] addr_q; reg [31:0] data_q, drained_q, fault_q;
    always @(posedge ck) begin
        addr_q <= cfg_addr; data_q <= cfg_data;
        drained_q <= group_drained; fault_q <= group_fault;
    end
    always @(posedge ck or negedge rn) begin
        if (!rn) begin we_q <= 0; go_q <= 0; host_q <= 0; upstream_q <= 0; end
        else begin we_q <= cfg_we; go_q <= go; host_q <= host_quiet; upstream_q <= upstream_quiet; end
    end
    reg nm, ov, nr, ac, dn, cf, ft; reg [31:0] cy; reg [7:0] fc;
    reg [31:0] enter_root, leave_root, deadline_root;
    reg [2:0] written;
    reg [31:0] enter_m, leave_m, deadline_m;                   // PIPE: root - k, captured with the root word
    reg drained_all_q;                                         // PIPE: &drained_q, one edge later
    always @(posedge ck) drained_all_q <= &drained_q;
    wire drained_ok = (PIPE != 0) ? drained_all_q : (&drained_q);
    wire rearm = go_q && ac && MUT != 7;                       // a later user's token start re-arms the window
    wire enter_now = ac && !rearm && cy == ((PIPE != 0) ? enter_m : enter_root - ((MUT == 1) ? 32'd2 : 32'd1));
    wire enter_tr = enter_now && (!nm || MUT == 6);            // host -> native transition only
    wire leave_now = ac && !rearm && cy == ((PIPE != 0) ? leave_m : leave_root - 32'd1);
    wire deadline_now = cy == ((PIPE != 0) ? deadline_m : deadline_root - 32'd1);
    // SAFE guard forecast is sampled one edge before the ownership boundary.
    // Four KEPT registered stop copies isolate root banks and control enables.
    reg [31:0] enter_guard, leave_guard;
    wire guard_enter = SAFE ? (ac && !rearm && !nm && cy == enter_guard) : enter_tr;
    wire guard_leave = SAFE ? (ac && !rearm && cy == leave_guard) : leave_now;
    (* keep = 1 *) reg [7:0] bad_q;
    (* keep = 1, dont_touch = 1 *) reg [3:0] halt_q;
    wire [7:0] bad_use = SAFE ? bad_q : bad;
    wire stop_ctl = SAFE ? halt_q[3] : (ft || (|bad));
    wire [3:0] stop_bank = SAFE ? halt_q : {4{ft || (|bad)}};
    always @(posedge ck or negedge rn) begin
        if (!rn) begin bad_q <= 0; halt_q <= 0; end
        else begin
            bad_q <= bad;
            halt_q[0] <= ft || (|bad);
            halt_q[1] <= ft || (|bad);
            halt_q[2] <= ft || (|bad);
            halt_q[3] <= ft || (|bad);
        end
    end
    reg [7:0] bad;
    always @* begin
        bad = 0;
        if (we_q && (cf || ac || go_q)) bad[0] = 1;
        if (we_q && addr_q == 3 &&
            (written != 3'b111 || data_q != 32'h514b564d || enter_root < 3 ||
             leave_root <= enter_root || deadline_root <= leave_root)) bad[1] = 1;
        if (go_q && (!cf || we_q || (ac && MUT == 5))) bad[2] = 1;
        if (guard_enter && (!host_q || !upstream_q || !drained_ok)) bad[3] = 1;
        if (guard_leave && MUT != 2 && (!upstream_q || !drained_ok)) bad[4] = 1;
        if ((|fault_q) && MUT != 3) bad[5] = 1;
    end
    always @(posedge ck or negedge rn) begin
        if (!rn) begin
            nm <= 0; ov <= 0; nr <= 0; ac <= 0;
            dn <= 0; cf <= 0; cy <= 0; ft <= 0; fc <= 0;
            written <= 0;
        end else if (stop_ctl) begin
            ft <= 1; fc <= fc | bad_use;
            ov <= 0; nr <= 1; ac <= 0; dn <= 0;
        end else begin
            dn <= 0;
            if (we_q) case (addr_q)
                0: written[0] <= 1;
                1: written[1] <= 1;
                2: written[2] <= 1;
                3: begin cf <= 1; ov <= 1; end
            endcase
            if (ac) begin
                cy <= cy + 1;
                if (enter_now) nm <= 1;
                if (leave_now) nm <= 0;
                if (!rearm && deadline_now) begin ac <= 0; dn <= 1; nr <= 0; end
            end
            if (go_q && !(ac && MUT == 7)) begin
                cy <= 0; ac <= 1; nr <= 1;
                if (!ac) nm <= 0;                              // a fresh window starts in host mode (the original)
            end
        end
    end
    always @(posedge ck or negedge rn) begin
        if (!rn) begin enter_root <= 0; enter_m <= 0; enter_guard <= 0; end
        else if (!stop_bank[0] && we_q && addr_q == 0) begin
            enter_root <= data_q;
            enter_m <= data_q - ((MUT == 1) ? 32'd2 : 32'd1);
            enter_guard <= data_q - 32'd2;
        end
    end
    always @(posedge ck or negedge rn) begin
        if (!rn) begin leave_root <= 0; leave_m <= 0; leave_guard <= 0; end
        else if (!stop_bank[1] && we_q && addr_q == 1) begin
            leave_root <= data_q; leave_m <= data_q - 32'd1;
            leave_guard <= data_q - 32'd2;
        end
    end
    always @(posedge ck or negedge rn) begin
        if (!rn) begin deadline_root <= 0; deadline_m <= 0; end
        else if (!stop_bank[2] && we_q && addr_q == 2) begin
            deadline_root <= data_q; deadline_m <= data_q - 32'd1;
        end
    end
    assign native_mode = nm; assign ownership_valid = ov; assign native_reserved = nr;
    assign active = ac; assign done = dn; assign configured = cf; assign cycle = cy;
    assign fault = ft; assign fault_code = fc;
end endgenerate
endmodule
