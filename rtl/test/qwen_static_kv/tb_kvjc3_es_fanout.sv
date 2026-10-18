`timescale 1ns/1ps
// KVJ-C3 2026-10-17: writer lane -> 128-PC fan-out bench against the plan's join model (kvjc3_pc_chain.py
// writer_ages).  Full shape: the real native writer (qkd_kv_static_writer_native, production compiled-slot cadence: four
// word slots on consecutive edges, high halves 2 edges apart) -> qkd_kv_es_fan_root -> 4 x 32 chain stations ->
// 128 x qkd_static_kv_pc_es_merge -> 128 copies of the controller's native intake check (qkd_ctrl_pc_host_static_core
// es_context / es_expected_* compare, verbatim terms) on the merged es.  Scoreboard: every writer lane word reaches
// exactly the PC named by the writer's actual {dest_stack, dest_pc} lane, bit-exact (sv, sv, address, data, v), on the
// model's edge  w + 5 + (31 - slot) (+1 for lanes 2/3), and no other PC; zero intake faults (so the independent
// expected descriptor and the context met every word at the controller); no root / station / merge / writer fault.
// Stimulus: layers {0, 1, 35} x positions 0..511 (every stack, group, quarter, K and V, both VMAP layouts' fields).
// MUT: 1 station pc alias, 2 root drops lanes 2/3, 5 context not lagged; a mutant must FAIL.
`ifndef OT_KVJC3_MUT
`define OT_KVJC3_MUT 0
`endif
module tb_kvjc3_es_fanout;
    localparam integer MUT = `OT_KVJC3_MUT;
    localparam integer SMUT = (MUT == 1 || MUT == 5) ? MUT : 0, RMUT = (MUT == 2) ? 2 : 0;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    // ---- writer ----
    reg v = 0, slot = 0; reg [10:0] tag = 0; reg [511:0] data = 0; reg [58:0] id = 0, cid = 0; reg [1:0] gen = 0, cgen = 0, ix = 0;
    wire [1151:0] es; wire [19:0] dpc, epc; wire [1:0] dst, est, og, eg; wire [58:0] oi, ei; wire [3:0] ev; wire [28:0] ea;
    wire wfault; wire [7:0] wfc;
    qkd_kv_static_writer_native #(.VMAP(1)) u_w (.ck(ck), .rst_n(rst_n), .word_valid(v), .word_tag(tag), .word_data(data),
        .word_identity(id), .word_generation(gen), .compiled_word_slot(slot), .compiled_word_index(ix),
        .compiled_identity(cid), .compiled_generation(cgen), .es(es), .dest_pc(dpc), .dest_stack(dst), .identity(oi),
        .generation(og), .expected_valid(ev), .expected_pc(epc), .expected_stack(est), .expected_identity(ei),
        .expected_generation(eg), .expected_address(ea), .fault(wfault), .fault_code(wfc));
    wire [778:0] head [0:3];
    wire root_fault;
    qkd_kv_es_fan_root #(.MUT(RMUT)) u_root (.ck(ck), .rst_n(rst_n), .es(es), .dest_pc(dpc), .dest_stack(dst), .identity(oi),
        .generation(og), .expected_valid(ev), .expected_pc(epc), .expected_stack(est), .expected_identity(ei),
        .expected_generation(eg), .expected_address(ea), .emb_start(1'b0), .emb_token(18'd0), .emb_epoch(16'd0),
        .cfg_we(1'b0), .cfg_addr(8'd0), .cfg_data(64'd0), .d0(head[0]), .d1(head[1]), .d2(head[2]), .d3(head[3]),
        .fault(root_fault));
    wire [778:0] ch [0:3][0:32];
    wire [127:0] sf, mf, inf;
    wire [287:0] mes [0:127];
    genvar s, p;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        assign ch[s][32] = head[s];
        for (p = 0; p < 32; p = p + 1) begin : g_p
            wire [287:0] wes, es_m; wire [317:0] ctx; wire xv; wire [60:0] eid; wire [28:0] ead; wire [4:0] xpc; wire [1:0] xst;
            wire iv, ih, isc, rs; wire [17:0] it; wire [5:0] iw; wire [15:0] ie;
            qkd_kv_pc_chain_station #(.MUT(SMUT)) u_st (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)),
                .di(ch[s][p + 1]), .dout(ch[s][p]), .wes(wes), .es_context(ctx), .es_expected_valid(xv),
                .es_expected_identity(eid), .es_expected_address(ead), .es_expected_pc(xpc), .es_expected_stack(xst),
                .emb_issue_v(iv), .emb_token(it), .emb_word_index(iw), .emb_half(ih), .emb_scale(isc), .emb_epoch(ie),
                .emb_return_slot(rs), .capture_slot(), .transfer_slot(), .fault(sf[32*s + p]));
            qkd_static_kv_pc_es_merge u_m (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)), .wes(wes),
                .emb_boot_ready(1'b1), .emb_issue_v(iv), .emb_token(it), .emb_word_index(iw), .emb_half(ih),
                .emb_scale(isc), .emb_epoch(ie), .emb_return_slot(rs), .es(es_m), .er(261'd0), .beat_v(), .beat_data(),
                .beat_token(), .beat_word(), .beat_half(), .beat_scale(), .beat_epoch(), .corrected(),
                .emb_outstanding(), .fault(mf[32*s + p]));
            assign mes[32*s + p] = es_m;
            // controller native intake check (qkd_ctrl_pc_host_static_core, PROFILE 0), verbatim terms
            reg [317:0] es_context_q; reg es_expected_q, es_v_q, nif; reg [60:0] es_expected_identity_q;
            reg [28:0] es_expected_address_q; reg [4:0] es_expected_pc_q, pc_core_q; reg [1:0] stack_q, es_expected_stack_q;
            reg [286:0] es_d_q;                 // the core: es_d_q <= es[287:1]
            always @(posedge ck) begin
                es_context_q <= ctx; es_expected_identity_q <= eid; es_expected_address_q <= ead; es_expected_pc_q <= xpc;
                es_expected_stack_q <= xst; stack_q <= 2'(s); pc_core_q <= 5'(p); es_d_q <= es_m[287:1];
            end
            always @(posedge ck or negedge rst_n)
                if (!rst_n) begin es_expected_q <= 0; es_v_q <= 0; nif <= 0; end
                else begin
                    es_expected_q <= xv; es_v_q <= es_m[0];
                    if ((es_v_q && es_context_q[317]) != es_expected_q) nif <= 1;
`ifdef OT_KVJC3_DEBUG
                    if (!nif && es_v_q && es_context_q[317]) $display("DBG pc %0d cyc %0d exq %0d id %0d ones %0d sv %0d%0d ad %h/%h pc %0d/%0d st %0d/%0d", 32*s+p, cyc, es_expected_q,
                        es_context_q[316:256] == es_expected_identity_q, es_context_q[255:0] == {256{1'b1}}, es_d_q[286], es_d_q[285],
                        {es_d_q[274:256], es_d_q[284:280], es_d_q[279:275]}, es_expected_address_q, pc_core_q, es_expected_pc_q, stack_q, es_expected_stack_q);
`endif
                    if (es_v_q && es_context_q[317] && (es_context_q[316:256] != es_expected_identity_q ||
                        es_context_q[255:0] != {256{1'b1}} || !es_d_q[286] || !es_d_q[285] ||
                        {es_d_q[274:256], es_d_q[284:280], es_d_q[279:275]} != es_expected_address_q ||
                        pc_core_q != es_expected_pc_q || stack_q != es_expected_stack_q)) nif <= 1;
                end
            assign inf[32*s + p] = nif;
        end
    end endgenerate
    // ---- scoreboard: the model's writer age ----
    typedef struct packed { int unsigned at; logic [287:0] w; } ent_t;
    ent_t sb [0:127][$];
    integer errors = 0, writes = 0, arrivals = 0, q, k, n;
    always @(negedge ck) if (rst_n) begin
        for (q = 0; q < 4; q = q + 1) if (es[288*q]) begin
            n = 32 * dst + dpc[5*q +: 5];
            sb[n].push_back('{at: cyc + 5 + (31 - dpc[5*q +: 5]) + (q >= 2 ? 1 : 0), w: es[288*q +: 288]});
            writes = writes + 1;
        end
        for (k = 0; k < 128; k = k + 1) if (mes[k][0]) begin
            arrivals = arrivals + 1;
            if (sb[k].size() == 0) begin errors = errors + 1; if (errors < 10) $display("FAIL PC %0d: unexpected word at %0d", k, cyc); end
            else begin
                if (sb[k][0].at != cyc || sb[k][0].w != mes[k]) begin
                    errors = errors + 1;
                    if (errors < 10) $display("FAIL PC %0d: word at %0d expected %0d data_ok %0d", k, cyc, sb[k][0].at, sb[k][0].w == mes[k]);
                end
                void'(sb[k].pop_front());
            end
        end
    end
    function automatic [7:0] bytecode(input integer l, t, kk, d);
        bytecode = 8'((l * 37 + t * 13 + kk * 91 + d * 17 + (t >> 8)) % 256);
    endfunction
    integer li, layer, pos, i, e;
    integer layers [0:2];
    initial begin
        layers[0] = 0; layers[1] = 1; layers[2] = 35;
        repeat (3) @(negedge ck); rst_n = 1; repeat (6) @(negedge ck);
        for (li = 0; li < 3; li = li + 1) for (pos = 0; pos < 512; pos = pos + 1) begin
            layer = layers[li];
            cid = {16'(layer + 9), 6'(layer + 1), 18'(pos + 13), 13'(pos), 6'd0}; cgen = 2'((pos + layer) % 4);
            for (i = 0; i < 4; i = i + 1) begin
                ix = 2'(i); slot = 1; v = 1; id = cid; gen = cgen;
                tag = {3'b010, 5'd0, 1'(i / 2), 1'b0, 1'(i % 2)};
                for (e = 0; e < 64; e = e + 1) data[e*8 +: 8] = bytecode(layer, pos, i / 2, (i % 2) * 64 + e);
                @(negedge ck);
            end
            slot = 0; v = 0; repeat (3) @(negedge ck);
        end
        repeat (60) @(negedge ck);
        for (k = 0; k < 128; k = k + 1) if (sb[k].size() != 0) begin
            errors = errors + 1; if (errors < 20) $display("FAIL PC %0d: %0d words never arrived", k, sb[k].size());
        end
        if (writes != 3 * 512 * 2 * 4) begin errors = errors + 1; $display("FAIL writer lane words %0d", writes); end
        if (wfault || root_fault || |sf || |mf || |inf) begin
            errors = errors + 1;
            $display("FAIL faults writer %0d root %0d station %h merge %h intake %h", wfault, root_fault, sf, mf, inf);
        end
        if (errors) $display("FAIL MUT %0d errors %0d (writes %0d arrivals %0d)", MUT, errors, writes, arrivals);
        else $display("PASS KVJC3_ES_FANOUT %0d lane words -> 128 PCs exact (edge, PC, bits), intake check clean", writes);
        $finish;
    end
endmodule
