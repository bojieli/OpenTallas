// KVJ-SMALL (c) 2026-10-17: OR of the 128 KV controller completion faults as a REGISTERED NEIGHBOUR TREE into the
// HOST root status input (qkd_host_root_admission.ctrl_completion_fault, consumed there only as |ctrl_completion_fault
// into observed_physical_faults, sampled by qkd_host_service_guard as a sticky asynchronous single bit).
//
// Source: each pc_path's completion_fault = qkd_ctrl_static_commit.fault = fs[1], a core-domain (ck) flop that is
// sticky until the controller's core reset (hf sticky in hclk, two-flop synchronised into ck).  The tree therefore runs
// in the same core ck, is a pure level OR (no events, no handshake, no credits) and is sticky by construction because
// its inputs are; it adds no state of its own beyond pipeline registers.
//
// qkd_kv_cfault_node: one registered node.  It sits beside its children (group node beside the group's grp_ctl, the
// upper nodes beside the middle child), so every input hop is a neighbour hop.  STAGES >= 1 registers: the first is the
// OR register, the rest are relay flops on the hop to the parent, priced by the floorplan (die reach 405 um); the
// compiler/model takes the latency  L = sum over levels of STAGES.
// qkd_kv_cfault_tree: the same nodes composed for N leaves, radix R (bench vehicle and a one-instance option); leaf i is
// controller i = 32*cfg_stack + pc (pc already in physical slot order), so node j of level 1 covers 4 abutted PCs = one
// controller group, level 2 four adjacent groups, and so on.  Latency LEVELS*STAGES (128 / R 4: 4 levels).
module qkd_kv_cfault_node #(parameter integer R = 4, parameter integer STAGES = 1, parameter integer MUT = 0)(
    input  wire         ck,
    input  wire         rst_n,
    input  wire [R-1:0] fault_in,
    output wire         fault
);
    // MUT 1: leaf 0 dropped (the OR ignores input 0)
    wire [R-1:0] m = (MUT == 1) ? {fault_in[R-1:1], 1'b0} : fault_in;
    wire [STAGES:0] q;                                   // q[0] is the OR (combinational); q[1..STAGES] are flops
    assign q[0] = |m;
    genvar s;
    for (s = 1; s <= STAGES; s = s + 1) begin : st
        reg r;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) r <= 1'b0;
            else        r <= q[s-1];
        assign q[s] = r;
    end
    assign fault = q[STAGES];
endmodule

module qkd_kv_cfault_tree #(parameter integer N = 128, parameter integer R = 4, parameter integer STAGES = 1,
                            parameter integer MUT = 0)(
    input  wire         ck,
    input  wire         rst_n,
    input  wire [N-1:0] fault_in,
    output wire         fault
);
    function integer nlev(input integer n);
        integer k; begin nlev = 0; k = n; while (k > 1) begin k = (k + R - 1) / R; nlev = nlev + 1; end end
    endfunction
    localparam integer LEVELS = nlev(N);
    localparam integer LATENCY = LEVELS * STAGES;       // reported to the compiler (ck edges, fault -> host input)
    function integer width_at(input integer l);
        integer k, j; begin k = N; for (j = 0; j < l; j = j + 1) k = (k + R - 1) / R; width_at = k; end
    endfunction
    genvar l, j;
    generate
        for (l = 0; l <= LEVELS; l = l + 1) begin : lv
            wire [width_at(l)-1:0] v;
            if (l == 0) begin : leaf
                assign v = fault_in;
            end else begin : nodes
                for (j = 0; j < width_at(l); j = j + 1) begin : n
                    localparam integer LO = j * R;
                    localparam integer CNT = (width_at(l-1) - LO < R) ? (width_at(l-1) - LO) : R;
                    // MUT 2: the root node drops its register stage (combinational OR into the host)
                    if (MUT == 2 && l == LEVELS) begin : comb
                        assign v[j] = |lv[l-1].v[LO +: CNT];
                    end else begin : reg_n
                        qkd_kv_cfault_node #(.R(CNT), .STAGES(STAGES), .MUT((MUT == 1 && l == 1 && j == 5) ? 1 : 0)) u (
                            .ck(ck), .rst_n(rst_n), .fault_in(lv[l-1].v[LO +: CNT]), .fault(v[j]));
                    end
                end
            end
        end
    endgenerate
    assign fault = lv[LEVELS].v[0];
endmodule
