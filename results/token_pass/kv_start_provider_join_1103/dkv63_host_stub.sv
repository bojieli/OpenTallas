`timescale 1ns/1ps
// DIE-KV-63/start: HOST stand-in for the START-skeleton vehicle. The real C45 ordered D2D boot event bridge with the C45
// 'installed' predicate. mode 0 = main (f4fc168ee): setup && program_installed_local && mission_start. mode 1 = the
// pre-f4fc168ee text compiled into veh60: setup && program_ready && mission_start, where program_ready = local install &&
// peer witness commit, and the witness arrives only after this event starts the d2d epoch (closed loop).
module dkv63_host_stub (input wire ck_ctl, input wire por_n, input wire mission_start, input wire static_setup_ready,
                        output wire d2d_boot_begin);
    wire request = $root.tb.req, local_inst = $root.tb.local_inst;
    reg running = 1'b0, committed = 1'b0;
    wire program_ready = local_inst && committed;
    wire installed = static_setup_ready && (($root.tb.mode == 1) ? program_ready : local_inst) && mission_start;
    qkd_d2d_boot_event_bridge #(.ENABLE(1)) u_d2d_boot_event (.ck(ck_ctl), .rst_n(por_n), .request(request),
        .installed(installed), .boot_begin(d2d_boot_begin));
    always @(posedge ck_ctl) begin
        if (d2d_boot_begin) running <= 1'b1;
        if (running && local_inst) committed <= 1'b1;
    end
endmodule
