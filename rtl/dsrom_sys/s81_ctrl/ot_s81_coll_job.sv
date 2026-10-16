`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_coll_job (s81-ctl-1011, 2026-10-11): the coll engine endpoint (ADAPTER_CONTRACT_1011, engine 3) of the S81
// collective slab.  It sits on the slab's VM input f_vm, in the slab clock (pll_stream), and makes the collective a
// command-driven engine of dsfd_sp_ctrl (ot_s81_stage_seq): a collective job is ONE message of engine records (VM
// f_vm type 1, the run of records ending with last), and
//   start = the job's descriptor is queued: the job's records are held in the record queue HQ until the descriptor
//           that names them is at the issue head; then they are released to the core's engine queue q0 in order.
//           Records never reach the engine without a command (a dropped command holds them: no result, no done).
//   done  = the job's LAST result has left the slab on t_vm (engine beat, type 1, with the job's last word: a reduce
//           beat packs up to 4 words and may carry the lasts of several messages: one done per last, in order).
// Descriptor arg (cmd[30:7], compiler-owned schema "coll_message" in tools/s81_ctrl/native_registry.json):
//   arg[15:0] = records of the message (1..65535), arg[16] = mode (the f_vm mode bit of every record of the
//   message: 1 all-gather, 0 all-reduce), arg[23:17] = 0.  A released record whose mode differs, a last before
//   arg[15:0] records, no last at arg[15:0] records, a reserved bit set or a count of 0 is a WRONG DESCRIPTOR: sticky
//   fault on the slab status (c_st[0]), and the record is still released (the engine's own checks see the data).
// Pass-through flits (type 2) bypass HQ unchanged (independent core queues q1..q5); a config word (type 3) while
// engine records are held or a message is open is a protocol fault (config is a boot-time word).
// Credits: the VM sends type-1 records only against the core's q0 credits (QD0 16), returned on q0 pops; a held
// record has not been popped, so HQ (16 deep) + q0 never hold more than the VM's 16 credits: a push into a full HQ
// is a fault, never a drop.  Latency: no register of its own on f_vm (the output is a mux of flops); a record released the cycle
// its job is at the head, cut through when HQ is empty (+0 here; the caller's pin flop is the only added cycle).
// MUT (negative controls): 5 early done (a done on the job's first result beat instead of its last).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_coll_job #(parameter integer HQD = 16, JQ = 8, MUT = 0, EPMUT = 0) (
    // controller side (dsfd_sp_ctrl clock): die pins of engine 3
    input  wire          c_clk, c_rst_n,
    input  wire [84:0]   c_cmd,                 // {cv[3], cd[3*84 +: 84]}
    output wire [8:0]    c_done,                // {dv[3], dt[3*8 +: 8]}
    output wire [1:0]    c_st,                  // {online, fault}
    // slab side (pll_stream)
    input  wire          ck, rs_n,               // synchronised slab reset
    input  wire [591:0]  vm_f,                   // the VM's f_vm word (pin-registered by the caller)
    output wire [591:0]  core_f,                 // to the slab core's f_vm (from flops through the release mux: the core pin-registers it)
    input  wire [13:0]   core_h,                 // header [13:0] of the slab's t_vm word (results leaving the slab)
    output wire          fault
);
    // ---- the pinned endpoint (adapter + in-order job queue of JQ descriptors)
    wire j_v, j_new; wire [83:0] j_d, j_new_d; wire ep_fault;
    reg  j_done;
    reg  jf;
    ot_s81_slab_ep #(.QD(8), .JQ(JQ), .MUT(EPMUT)) u_ep (.c_clk(c_clk), .c_rst_n(c_rst_n), .c_cmd(c_cmd), .c_done(c_done),
        .c_st(c_st), .e_clk(ck), .e_rst_n(rs_n), .j_v(j_v), .j_d(j_d), .j_new(j_new), .j_new_d(j_new_d),
        .j_present(1'b1), .j_done(j_done), .slab_fault(jf), .ep_fault(ep_fault));
    assign fault = jf | ep_fault;
    // ---- issue queue: copies of the queued descriptors' args (the release side runs ahead of the done side)
    localparam integer IAW = (JQ <= 2) ? 1 : $clog2(JQ);
    reg [16:0] iq [0:JQ-1]; reg [IAW-1:0] iw, ir; reg [IAW:0] in_;
    reg        ibad [0:JQ-1];
    // ---- record queue HQ: {data 552, tag 32, mode, last}
    localparam integer HW = 552 + 32 + 2;
    localparam integer HAW = $clog2(HQD);
    reg [HW-1:0] hq [0:HQD-1]; reg [HAW-1:0] hw, hr; reg [HAW:0] hn;
    wire in_v   = vm_f[0];
    wire [1:0] in_t = vm_f[2:1];
    wire in_rec = in_v && in_t == 2'd1;
    wire in_byp = in_v && in_t != 2'd1;
    // message state
    reg        act;                               // a message is open (its descriptor at the issue head)
    reg [15:0] cnt, need; reg md, abad;
    wire       head_ok = act || (in_ != 0);
    wire [HW-1:0] hd = hq[hr];
    // a record arriving with HQ empty and its descriptor present goes straight out (cut-through: +1 cycle, the output
    // register); otherwise HQ releases its head (bypass words take the output slot first)
    wire       cut = in_rec && (hn == 0) && head_ok;
    wire       rel = ((hn != 0) && head_ok && !in_byp) || cut;
    wire [HW-1:0] hsel = cut ? {vm_f[591:40], vm_f[39:8], vm_f[7], vm_f[6]} : hd;
    wire       h_last = hsel[0], h_mode = hsel[1];
    // output word, same cycle (no added register: the caller's pin flop on vm_f is the endpoint's only cycle)
    assign core_f = in_byp ? vm_f : rel ? {hsel[HW-1 -: 552], hsel[33:2], h_mode, h_last, 3'd0, 2'd1, 1'b1} : 592'd0;
    // ---- done side: lasts leaving the slab
    wire       ob = core_h[0] && core_h[2:1] == 2'd1;
    wire [3:0] ol = core_h[13:10] & core_h[9:6];
    wire [2:0] nl = ob ? ({2'b0, ol[0]} + ol[1] + ol[2] + ol[3]) : 3'd0;
    reg  [4:0] pend;                              // lasts seen whose done is not yet pulsed
    reg        first_seen;                        // MUT 5: a result beat seen for the head job
    wire [2:0] nd = (MUT == 5) ? ((ob && !first_seen && j_v) ? 3'd1 : 3'd0) : nl;
    integer i;
    always @(posedge ck or negedge rs_n)
        if (!rs_n) begin
            iw <= 0; ir <= 0; in_ <= 0; hw <= 0; hr <= 0; hn <= 0; act <= 1'b0; cnt <= 0; need <= 0; md <= 1'b0; abad <= 1'b0;
            pend <= 0; first_seen <= 1'b0; j_done <= 1'b0; jf <= 1'b0;
        end else begin
            // descriptor copies
            if (j_new) begin iq[iw] <= {j_new_d[23], j_new_d[22:7]}; ibad[iw] <= (j_new_d[30:24] != 0) || (j_new_d[22:7] == 0);
                             iw <= (iw == JQ - 1) ? 0 : iw + 1'b1; end
            // record queue push
            if (in_rec && !cut) begin hq[hw] <= {vm_f[591:40], vm_f[39:8], vm_f[7], vm_f[6]}; hw <= hw + 1'b1;
                                      if (hn == HQD && !rel) jf <= 1'b1; end
            case ({in_rec && !cut, rel && !cut}) 2'b10: hn <= hn + 1'b1; 2'b01: hn <= hn - 1'b1; default: hn <= hn; endcase
            if (in_v && in_t == 2'd3 && (hn != 0 || act)) jf <= 1'b1;
            // released record: queue pointer and message bookkeeping
            if (rel && !in_byp) begin
                if (!cut) hr <= hr + 1'b1;
                // message bookkeeping: open at the first record (descriptor from the issue head), close at last
                begin : msg
                    reg [15:0] c_; reg [15:0] n_; reg m_; reg b_;
                    if (act) begin c_ = cnt; n_ = need; m_ = md; b_ = abad; end
                    else begin c_ = 0; n_ = iq[ir][15:0]; m_ = iq[ir][16]; b_ = ibad[ir]; end
                    if (b_ || h_mode != m_ || (h_last != (c_ + 1'b1 == n_)) || c_ + 1'b1 > n_) jf <= 1'b1;
                    if (h_last) begin
                        act <= 1'b0;
                        ir <= (ir == JQ - 1) ? 0 : ir + 1'b1;
                    end else begin
                        act <= 1'b1; cnt <= c_ + 1'b1; need <= n_; md <= m_; abad <= b_;
                    end
                end
            end
            case ({j_new, rel && h_last}) 2'b10: in_ <= in_ + 1'b1; 2'b01: in_ <= in_ - 1'b1; default: in_ <= in_; endcase
            // done side: one done a cycle, in order (the slab_ep returns the head's tag)
            j_done <= 1'b0;
            if (pend + nd != 0) begin j_done <= 1'b1; pend <= pend + nd - 1'b1; end
            if (MUT == 5) begin if (j_done) first_seen <= 1'b0; else if (ob && j_v) first_seen <= 1'b1; end
            if (pend + nd > 5'd16) jf <= 1'b1;
        end
endmodule
