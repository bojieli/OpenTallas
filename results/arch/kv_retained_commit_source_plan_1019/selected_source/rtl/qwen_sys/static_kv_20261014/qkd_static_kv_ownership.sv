`timescale 1ns/1ps
// Local observation leaf, four actual PC paths. These outputs never issue,
// hold, retry or move a production slot. The parent must separately account
// every outstanding upstream command/data/landing pipeline in upstream_quiet;
// absence of activity at one pin, writer.active=0 or a single domain's idle
// observation is insufficient. Physical crossing/clock/path proof is required.
module qkd_static_kv_drain_guard4 #(parameter integer MUT = 0) (
    input wire ck, rst_n,
    input wire [3:0] ctrl_idle_core, ring_idle_core,
    input wire [3:0] ctrl_idle_hbm, front_idle_hbm, ring_idle_hbm,
    input wire [3:0] ctrl_fault_core, ctrl_completion_fault_core, ctrl_intake_fault_core, ring_fault_core,
    input wire [3:0] ctrl_fault_hbm, ctrl_output_fault_hbm, ctrl_calendar_fault_hbm, ring_fault_hbm,
    input wire [3:0] front_fault_overflow_hbm, front_fault_go_hbm, front_hold_hbm,
    input wire upstream_quiet, upstream_fault,
    output reg drained, fault
);
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    // Every asynchronous observation crosses independently. Synchronizing a
    // combinational reduction in the HBM domain would create an unregistered
    // boundary cone and would not establish a real source-domain observation.
    (* async_reg = "true" *) reg [11:0] idle_meta, idle_sync;
    (* async_reg = "true" *) reg [27:0] fault_meta, fault_sync;
    reg [7:0] idle_core_q; reg [15:0] fault_core_q;
    reg quiet_q, upstream_fault_q, quiet_prev;
    always @(posedge ck or negedge rn) begin
        if (!rn) begin
            idle_meta <= 0; idle_sync <= 0;
            fault_meta <= 0; fault_sync <= 0;
            idle_core_q <= 0; fault_core_q <= 0;
            quiet_q <= 0; upstream_fault_q <= 0;
            quiet_prev <= 0; drained <= 0; fault <= 0;
        end else begin
            idle_meta <= {ctrl_idle_hbm, front_idle_hbm, ring_idle_hbm};
            idle_sync <= idle_meta;
            fault_meta <= {ctrl_fault_hbm, ctrl_output_fault_hbm, ctrl_calendar_fault_hbm, ring_fault_hbm,
                           front_fault_overflow_hbm, front_fault_go_hbm, front_hold_hbm};
            fault_sync <= fault_meta;
            idle_core_q <= {ctrl_idle_core, ring_idle_core};
            fault_core_q <= {ctrl_fault_core, ctrl_completion_fault_core, ctrl_intake_fault_core, ring_fault_core};
            quiet_q <= upstream_quiet; upstream_fault_q <= upstream_fault;
            quiet_prev <= ((MUT == 1) || (&idle_sync)) && (&idle_core_q) && quiet_q &&
                          !(|fault_sync) && !(|fault_core_q) && !upstream_fault_q && !fault;
            drained <= quiet_prev && ((MUT == 1) || (&idle_sync)) && (&idle_core_q) && quiet_q &&
                       !(|fault_sync) && !(|fault_core_q) && !upstream_fault_q && !fault;
            if (MUT != 2 && ((|fault_sync) || (|fault_core_q) || upstream_fault_q)) fault <= 1;
        end
    end
endmodule

// Fixed-cycle native/HOST ownership producer. This is a real source component,
// not a production schedule by itself. Boot roots must come from the actual
// compiled programme through the real loader; go/quiet/drain/fault must be
// connected to actual on-chip producers. No input can postpone either switch.
// A bad boundary fault-stops ownership_valid instead of granting another owner.
//
// Boot writes addresses 0 enter, 1 leave, 2 deadline; address3 seals 0x514b564d
// (QKVM). Roots are output PIN edge ages from the internal accepted go. Input
// go is first captured at its pin; internal accepted go is the following edge.
// Thus output edge = external go capture edge + 1 + root. The controller-face
// ownership mux's capture/output edges and all physical relays are additional
// explicit compiler ages. Native mode must already be present for the first
// reserved transaction and remain through actual read/write/return debt.
//
// native_reserved asserts at internal accepted go, before native_mode, and
// clears only at the successful deadline. HOST intake must be blocked while
// reserved or ownership_valid=0. It stays reserved on fault until reset. The
// compiler prices this admission-isolation path before the native enter root.
// Guards are observations only. Normal production never waits for idle/ready.
// A failing guard makes this execution invalid/aborted, with both ownership
// paths disabled; it cannot extend or resume the compiled timeline. Reset is
// required to clear the fault or replace the sealed exceptional boot image.
module qkd_static_kv_ownership_calendar #(parameter integer MUT = 0) (
    input wire ck, rst_n,
    input wire cfg_we, input wire [1:0] cfg_addr, input wire [31:0] cfg_data,
    input wire go,
    input wire host_quiet, upstream_quiet,
    input wire [31:0] group_drained, group_fault,
    output reg native_mode, ownership_valid, native_reserved,
    output reg active, done, configured,
    output reg [31:0] cycle,
    output reg fault, output reg [7:0] fault_code
);
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
    reg [31:0] enter_root, leave_root, deadline_root;
    reg [2:0] written;
    wire enter_now = active && cycle == enter_root - ((MUT == 1) ? 32'd2 : 32'd1);
    wire leave_now = active && cycle == leave_root - 32'd1;
    reg [7:0] bad;
    always @* begin
        bad = 0;
        if (we_q && (configured || active || go_q)) bad[0] = 1;
        if (we_q && addr_q == 3 &&
            (written != 3'b111 || data_q != 32'h514b564d || enter_root < 3 ||
             leave_root <= enter_root || deadline_root <= leave_root)) bad[1] = 1;
        if (go_q && (!configured || active || we_q)) bad[2] = 1;
        if (enter_now && (!host_q || !upstream_q || !(&drained_q))) bad[3] = 1;
        if (leave_now && MUT != 2 && (!upstream_q || !(&drained_q))) bad[4] = 1;
        if ((|fault_q) && MUT != 3) bad[5] = 1;
    end
    always @(posedge ck or negedge rn) begin
        if (!rn) begin
            native_mode <= 0; ownership_valid <= 0; native_reserved <= 0; active <= 0;
            done <= 0; configured <= 0; cycle <= 0; fault <= 0; fault_code <= 0;
            enter_root <= 0; leave_root <= 0; deadline_root <= 0; written <= 0;
        end else if (fault || (|bad)) begin
            fault <= 1; fault_code <= fault_code | bad;
            ownership_valid <= 0; native_reserved <= 1; active <= 0; done <= 0;
        end else begin
            done <= 0;
            if (we_q) case (addr_q)
                0: begin enter_root <= data_q; written[0] <= 1; end
                1: begin leave_root <= data_q; written[1] <= 1; end
                2: begin deadline_root <= data_q; written[2] <= 1; end
                3: begin configured <= 1; ownership_valid <= 1; end
            endcase
            if (go_q) begin cycle <= 0; active <= 1; native_mode <= 0; native_reserved <= 1; end
            if (active) begin
                cycle <= cycle + 1;
                if (enter_now) native_mode <= 1;
                if (leave_now) native_mode <= 0;
                if (cycle == deadline_root - 1) begin active <= 0; done <= 1; native_reserved <= 0; end
            end
        end
    end
endmodule
