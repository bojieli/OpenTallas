`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_hop_tx (stream ds-control, 2026-10-08): the 'hop' engine port of the S81 stage program: it frames a stage's
// hand-off messages from the job descriptors of ot_s81_stage_seq.  It replaces ot_rom_pkg_ctrl_x's outbound side
// (which framed after a core-done handshake): a hand-off is a job like any other, queued at this port while the stage
// runs and started on its input (dataflow): `go` pulses once per hop job, in program order, when the job's input is
// in the vector memory (the producer's write-done strobe, e.g. hc_post's last word) or, for a RESULT, when the head
// sampler's {token, logit, stop} is valid (res_v).
//
// Descriptor (ot_s81_stage_seq command, CMDW bits): {slot, user, pos, tok, arg, op}; arg[3:0] message type
// (1 HIDDEN, 2 RESULT, 3 SIDE), arg[15:4] destination fabric id (a die or a multicast group), arg[23:16] SIDE payload
// flits (SIDE) / unused.  Payloads: HIDDEN = XW flits read from VM words TXB + slot * XW ..; SIDE = arg[23:16] flits
// from SIDE_TXB + slot * 256 .., staged by the receivers at header ADDR = SIDE_RXB.  Every header carries the job's
// user / position / token and the run's stop configuration (run_*), so the next stage (and the head die's sampler)
// sees them.  A completion {slot, op} is returned when the message's last flit has been taken by the link (out_ready).
// The VM read port is synchronous (vm_re / vm_raddr registered here, the memory's registered read: data on vm_rq
// two edges after the issue); reads run ahead of the link by at most the 4-flit
// output queue.  Faults: 1 descriptor queue overflow (credits violated), 2 go without a queued descriptor, 3 unknown
// message type, 4 RESULT go without res_v.
// ---------------------------------------------------------------------------
module ot_s81_hop_tx #(
    parameter integer MY_ID    = 0,
    parameter integer FLIT     = 512,
    parameter integer NW       = 21,
    parameter integer USER_W   = 12,
    parameter integer VWA      = 14,
    parameter integer XW       = 640,
    parameter integer TXB      = 0,
    parameter integer SIDE_TXB = 0,
    parameter integer SIDE_RXB = 0,
    parameter integer CMDW     = 0,
    parameter integer OPW      = 7,
    parameter integer ARGW     = 24,
    parameter integer SUW      = 10,     // the sequencer's descriptor user width
    parameter integer QD       = 8
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               cmd_v,
    input  wire [CMDW-1:0]    cmd_d,
    output reg                dn_v,
    output reg  [OPW:0]       dn_tag,
    input  wire               go,
    input  wire               res_v,
    input  wire [NW-1:0]      res_tok,
    input  wire [31:0]        res_val,
    input  wire               res_stop,
    input  wire               run_eosen,
    input  wire [NW-1:0]      run_eos,
    input  wire [NW:0]        run_maxl,
    output reg                vm_re,
    output reg  [VWA-1:0]     vm_raddr,
    input  wire [FLIT-1:0]    vm_rq,
    output wire               out_valid,
    input  wire               out_ready,
    output wire [FLIT-1:0]    out_data,
    output wire               out_last,
    output reg                fault,
    output reg  [3:0]         fault_code,
    output reg  [31:0]        st_msgs
);
`include "ot_s81_hdr.svh"
    localparam integer QB = $clog2(QD);
    // ---- descriptor queue (the engine-side command queue: QD credits) ----
    reg [CMDW-1:0] dq [0:QD-1];
    reg [QB-1:0]   dq_w, dq_r;
    reg [QB:0]     dq_n;
    reg [QB:0]     go_n;                     // go pulses received and not yet consumed
    wire [CMDW-1:0] hd = dq[dq_r];
    wire            h_slot = hd[CMDW-1];
    wire [SUW-1:0]  h_user = hd[CMDW-2 -: SUW];
    wire [NW-1:0]   h_pos  = hd[CMDW-2-SUW -: NW];
    wire [NW-1:0]   h_tok  = hd[CMDW-2-SUW-NW -: NW];
    wire [ARGW-1:0] h_arg  = hd[OPW +: ARGW];
    wire [OPW-1:0]  h_op   = hd[OPW-1:0];
    wire [3:0]      h_typ  = h_arg[3:0];
    wire [11:0]     h_dst  = h_arg[15:4];
    wire [7:0]      h_sl   = h_arg[23:16];

    // ---- output queue (4 flits) ----
    reg [FLIT-1:0] oq_d [0:3];
    reg            oq_l [0:3];
    reg [1:0]      oq_w, oq_r;
    reg [2:0]      oq_n;
    assign out_valid = oq_n != 0;
    assign out_data  = oq_d[oq_r];
    assign out_last  = oq_l[oq_r];
    wire pop = out_valid && out_ready;

    localparam [1:0] S_IDLE = 0, S_DATA = 1, S_DRAIN = 2;
    reg [1:0]   st;
    reg [11:0]  k, nw;                      // payload flits read / to read
    reg         rd_v, rd_l;                 // VM read data arrives this cycle (2nd stage), its last flag
    reg         r1_v, r1_l;                 // 1st stage: vm_re is on the port this cycle
    reg         cur_slot;
    reg [OPW-1:0] cur_op;
    reg [11:0]  pend_flits;                 // flits of the current message not yet popped
    wire [2:0]  room = 3'd4 - oq_n - (rd_v ? 3'd1 : 3'd0) - (r1_v ? 3'd1 : 3'd0);

    function automatic [FLIT-1:0] hdr(input [3:0] typ, input [11:0] dst, input [11:0] len, input [SUW-1:0] usr,
                                      input [NW-1:0] pos, input [NW-1:0] idx, input [31:0] val, input [NW-1:0] tok,
                                      input [15:0] addr, input stop);
        begin
            hdr = {FLIT{1'b0}};
            hdr[SH_DEST +: 12] = dst; hdr[SH_SRC +: 12] = 12'(MY_ID); hdr[SH_TYPE +: 4] = typ; hdr[SH_LEN +: 12] = len;
            hdr[SH_USER +: SH_UW] = SH_UW'(usr); hdr[SH_POS +: NW] = pos; hdr[SH_IDX +: NW] = idx; hdr[SH_VAL +: 32] = val;
            hdr[SH_TOK +: NW] = tok; hdr[SH_ADDR +: 16] = addr; hdr[SH_STOP] = stop;
            hdr[SH_EOSEN] = run_eosen; hdr[SH_EOS +: NW] = run_eos; hdr[SH_MAXL +: SH_MLW] = SH_MLW'(run_maxl);
        end
    endfunction

    wire start = (st == S_IDLE) && dq_n != 0 && (go_n != 0 || go) && oq_n < 3'd4 && !rd_v && !r1_v;
    reg  [3:0]  cur_typ;
    reg         push; reg [FLIT-1:0] push_d; reg push_l;
    reg  [11:0] pf_n;                          // pend_flits after this cycle
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dq_w <= 0; dq_r <= 0; dq_n <= 0; go_n <= 0;
            oq_w <= 0; oq_r <= 0; oq_n <= 0; cur_typ <= 0;
            st <= S_IDLE; k <= 0; nw <= 0; rd_v <= 1'b0; rd_l <= 1'b0; r1_v <= 1'b0; r1_l <= 1'b0; cur_slot <= 1'b0; cur_op <= 0; pend_flits <= 0;
            vm_re <= 1'b0; vm_raddr <= 0; dn_v <= 1'b0; dn_tag <= 0;
            fault <= 1'b0; fault_code <= 0; st_msgs <= 0;
        end else begin
            dn_v <= 1'b0;
            vm_re <= 1'b0;
            push = 1'b0; push_d = 0; push_l = 1'b0;
            pf_n = pend_flits;
            // descriptors (the engine-side queue of QD entries)
            if (cmd_v) begin
                if (dq_n == QD) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd1; end
                else begin dq[dq_w] <= cmd_d; dq_w <= dq_w + 1'b1; end
            end
            if (go && dq_n == 0 && !cmd_v) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd2; end
            go_n <= go_n + (go ? 1'b1 : 1'b0) - (start ? 1'b1 : 1'b0);
            dq_n <= dq_n + ((cmd_v && dq_n != QD) ? 1'b1 : 1'b0) - (start ? 1'b1 : 1'b0);
            // VM read: vm_re (registered port) -> the memory's registered read -> data two edges after the issue
            rd_v <= r1_v; rd_l <= r1_l; r1_v <= 1'b0;
            if (rd_v) begin push = 1'b1; push_d = vm_rq; push_l = rd_l; end
            case (st)
                S_IDLE: if (start) begin
                    dq_r <= dq_r + 1'b1; cur_slot <= h_slot; cur_op <= h_op; cur_typ <= h_typ; k <= 0;
                    st_msgs <= st_msgs + 1;
                    push = 1'b1;
                    case (h_typ)
                        MT_HIDDEN: begin
                            push_d = hdr(MT_HIDDEN, h_dst, 12'(XW), h_user, h_pos, 0, 0, h_tok, 0, 1'b0);
                            nw <= 12'(XW); st <= S_DATA; pf_n = 12'(XW) + 1'b1;
                        end
                        MT_SIDE: begin
                            push_d = hdr(MT_SIDE, h_dst, 12'(h_sl), h_user, h_pos, 0, 0, h_tok, 16'(SIDE_RXB), 1'b0);
                            push_l = (h_sl == 0);
                            nw <= 12'(h_sl); st <= (h_sl == 0) ? S_DRAIN : S_DATA; pf_n = 12'(h_sl) + 1'b1;
                        end
                        MT_RESULT: begin
                            if (!res_v) begin fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd4; end
                            push_d = hdr(MT_RESULT, h_dst, 12'd0, h_user, h_pos, res_tok, res_val, h_tok, 0, res_stop);
                            push_l = 1'b1; st <= S_DRAIN; pf_n = 12'd1;
                        end
                        default: begin
                            fault <= 1'b1; if (fault_code == 0) fault_code <= 4'd3;
                            push = 1'b0; st <= S_DRAIN; pf_n = 12'd0;
                        end
                    endcase
                end
                S_DATA: if (room > (push ? 3'd1 : 3'd0)) begin
                    vm_re <= 1'b1;
                    vm_raddr <= ((cur_typ == MT_HIDDEN) ? VWA'(TXB) + (cur_slot ? VWA'(XW) : {VWA{1'b0}})
                                                        : VWA'(SIDE_TXB) + (cur_slot ? VWA'(256) : {VWA{1'b0}})) + VWA'(k);
                    r1_v <= 1'b1; r1_l <= (k == nw - 1'b1);
                    k <= k + 1'b1;
                    if (k == nw - 1'b1) st <= S_DRAIN;
                end
                default: ;
            endcase
            if (push) begin oq_d[oq_w] <= push_d; oq_l[oq_w] <= push_l; oq_w <= oq_w + 1'b1; end
            if (pop) begin oq_r <= oq_r + 1'b1; pf_n = pf_n - 1'b1; end
            oq_n <= oq_n + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            pend_flits <= pf_n;
            // completion: every flit of the message has been taken by the link
            if (st == S_DRAIN && pf_n == 0) begin
                dn_v <= 1'b1; dn_tag <= {cur_slot, cur_op}; st <= S_IDLE;
            end
        end
    end
endmodule
