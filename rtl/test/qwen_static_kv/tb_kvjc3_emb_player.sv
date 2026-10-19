`timescale 1ns/1ps
// KVJ-C3 2026-10-17: embedding slot player bench against the plan's join model (tools/qwen_kv_die/kvjc3_pc_chain.py).
// Full shape: root -> 4 x 32 chain stations (players) -> 128 x qkd_static_kv_pc_es_merge (real strap endpoints) ->
// 128 bench controller models (fixed es -> er latency LAT, data = a hash of {stack, pc, address}: the HBM controller
// path itself is pc_path's, outside this bench) -> 4 real return trains (head + 31 hops) -> qkd_embedding_static_join4_cal.
// Boot: the tool's boot words on the shared boot bus.  Per token: one start pulse; checks every join word (index,
// scale, token, epoch, exact data from the independent map below) at the tool's exact edge, 65 words, and no fault
// anywhere (root, stations, es merges, trains, join).  MUT: 3 / 4 station, 6 join4_cal; a mutant must FAIL.
// KVJ-SMALL b2 10-17: with OT_KVJC3_DISP defined the shared boot bus comes from the actual boot dispatcher
// (qkd_static_kv_boot_dispatch ESCFG=1, MUT = OT_KVJC3_DMUT) fed targets 1..9, 12, 13, 0 (OT_KVJC3_DISP_DIR/target12.hex,
// target13.hex = kv_static_programme.es_cfg_words); its stream must equal boot.memh and setup_ready must rise.
`ifndef OT_KVJC3_MUT
`define OT_KVJC3_MUT 0
`endif
`ifndef OT_KVJC3_DIR
`define OT_KVJC3_DIR "."
`endif
module tb_kvjc3_emb_player;
    localparam integer MUT = `OT_KVJC3_MUT, LAT = 92, ROW0 = 24427;
    localparam integer SMUT = (MUT == 3 || MUT == 4) ? MUT : 0;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    reg start = 0; reg [17:0] tok = 0; reg [15:0] epo = 0;
`ifdef OT_KVJC3_DISP
`ifndef OT_KVJC3_DMUT
`define OT_KVJC3_DMUT 0
`endif
    wire cfg_we; wire [7:0] cfg_addr; wire [63:0] cfg_data;
    reg [142:0] pr = 0; reg [3:0] target = 1; reg ready = 0; reg [63:0] digest = 0; reg [159:0] applied = 0; reg [2:0] configured = 0;
    wire setup, dfault; wire [7:0] code;
    qkd_static_kv_boot_dispatch #(.MUT(`OT_KVJC3_DMUT), .DIECFG(0), .LINKCFG(0), .ESCFG(1)) u_disp (.ck(ck), .rst_n(rst_n),
        .boot_pr(pr), .boot_image_target(target), .boot_image_ready(ready), .boot_image_fault(1'b0), .boot_image_epoch(16'd77),
        .boot_image_digest(digest), .execution_active(1'b0), .sink_applied(applied), .local_configured(configured),
        .sink_fault(1'b0), .diecfg_sealed(1'b0), .diecfg_fault(1'b0),
        .layer_we(), .layer_addr(), .layer_data(), .writer_we(), .writer_addr(), .writer_data(), .ownership_we(),
        .ownership_addr(), .ownership_data(), .landing_we(), .front_we(), .group_addr(), .group_data(),
        .controller_we(), .controller_addr(), .controller_data(), .controller_last(), .front_last(),
        .diecfg_we(), .diecfg_addr(), .diecfg_data(), .link_cfg_tx_we(), .link_cfg_rx_we(), .link_cfg_addr(), .link_cfg_data(),
        .es_cfg_we(cfg_we), .es_cfg_addr(cfg_addr), .es_cfg_data(cfg_data),
        .setup_ready(setup), .fault(dfault), .fault_code(code), .installed_epoch(), .installed_isa_digest());
`else
    reg cfg_we = 0; reg [7:0] cfg_addr = 0; reg [63:0] cfg_data = 0;
`endif
    wire [778:0] head [0:3];
    wire root_fault;
    qkd_kv_es_fan_root u_root (.ck(ck), .rst_n(rst_n), .es(1152'd0), .dest_pc(20'd0), .dest_stack(2'd0), .identity(59'd0),
        .generation(2'd0), .expected_valid(4'd0), .expected_pc(20'd0), .expected_stack(2'd0), .expected_identity(59'd0),
        .expected_generation(2'd0), .expected_address(29'd0), .emb_start(start), .emb_token(tok), .emb_epoch(epo),
        .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .d0(head[0]), .d1(head[1]), .d2(head[2]), .d3(head[3]), .fault(root_fault));
    wire [778:0] ch [0:3][0:32];
    wire [298:0] up [0:3][0:31];
    wire [127:0] sf, mf, hf;
    function automatic [255:0] hdat(input integer st, input integer p, input [28:0] ad);
        integer j; reg [31:0] h;
        begin
            for (j = 0; j < 8; j = j + 1) begin
                h = (32'(st) * 32'h9e3779b1) ^ (32'(p) * 32'h85ebca77) ^ (32'(ad) * 32'hc2b2ae3d) ^ (32'(j) * 32'h27d4eb2f);
                hdat[32*j +: 32] = h ^ (h >> 15);
            end
        end
    endfunction
    genvar s, p;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        assign ch[s][32] = head[s];                         // chain order: root -> slot 31 -> ... -> slot 0
        for (p = 0; p < 32; p = p + 1) begin : g_p
            wire [287:0] wes, es; wire [317:0] ctx; wire ev; wire [60:0] eid; wire [28:0] ead; wire [4:0] epc; wire [1:0] est;
            wire iv, ih, isc, rs, cs, ts; wire [17:0] it; wire [5:0] iw; wire [15:0] ie;
            qkd_kv_pc_chain_station #(.MUT(SMUT)) u_st (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)),
                .di(ch[s][p + 1]), .dout(ch[s][p]), .wes(wes), .es_context(ctx), .es_expected_valid(ev),
                .es_expected_identity(eid), .es_expected_address(ead), .es_expected_pc(epc), .es_expected_stack(est),
                .emb_issue_v(iv), .emb_token(it), .emb_word_index(iw), .emb_half(ih), .emb_scale(isc), .emb_epoch(ie),
                .emb_return_slot(rs), .capture_slot(cs), .transfer_slot(ts), .fault(sf[32*s + p]));
            // bench controller model: es -> er after LAT edges (er[0] = the read, er[256:1] = data)
            reg [29:0] dl [0:LAT-1];
            integer k;
            always @(posedge ck) begin
                dl[0] <= {es[285:257], es[0]};
                for (k = 1; k < LAT; k = k + 1) dl[k] <= dl[k - 1];
            end
            wire [260:0] er = {4'd0, dl[LAT-1][0] ? hdat(s, p, dl[LAT-1][29:1]) : 256'd0, dl[LAT-1][0]};
            wire bv, bh, bs; wire [255:0] bd; wire [17:0] bt; wire [5:0] bw; wire [15:0] be;
            qkd_static_kv_pc_es_merge u_m (.ck(ck), .rst_n(rst_n), .pc(5'(p)), .cfg_stack(2'(s)), .wes(wes),
                .emb_boot_ready(1'b1), .emb_issue_v(iv), .emb_token(it), .emb_word_index(iw), .emb_half(ih),
                .emb_scale(isc), .emb_epoch(ie), .emb_return_slot(rs), .es(es), .er(er), .beat_v(bv), .beat_data(bd),
                .beat_token(bt), .beat_word(bw), .beat_half(bh), .beat_scale(bs), .beat_epoch(be), .corrected(),
                .emb_outstanding(), .fault(mf[32*s + p]));
            wire [297:0] rec = {be, bs, bh, bw, bt, bd};
            if (p == 0) begin : g_head
                qkd_embedding_static_return_head u_h (.ck(ck), .rst_n(rst_n), .capture_slot(cs), .capture_v(bv),
                    .capture_record(rec), .transfer_slot(ts), .upo(up[s][0]), .fault(hf[32*s]));
            end else begin : g_hop
                qkd_embedding_static_return_hop u_h (.ck(ck), .rst_n(rst_n), .capture_slot(cs), .capture_v(bv),
                    .capture_record(rec), .transfer_slot(ts), .upi(up[s][p - 1]), .upo(up[s][p]), .fault(hf[32*s + p]));
            end
        end
    end endgenerate
    wire wv, wsc, jfault; wire [511:0] wd; wire [17:0] wt; wire [5:0] wi; wire [15:0] we;
    qkd_embedding_static_join4_cal #(.MUT(MUT == 6 ? 1 : 0)) u_j (.ck(ck), .rst_n(rst_n), .up0(up[0][31]), .up1(up[1][31]),
        .up2(up[2][31]), .up3(up[3][31]), .start(start), .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .word_v(wv), .word_data(wd), .word_token(wt), .word_index(wi), .word_scale(wsc), .word_epoch(we), .fault(jfault));
    // ---- the model: boot words and expected join word edges ----
    reg [71:0] boot [0:1100];
    reg [27:0] wexp [0:64];
    reg [255:0] sd;
    integer nboot, errors = 0, nw, r0, i, t;
    // independent embedding map (qkd_embedding_static_map ABI): {bank5, col5, row19}
    function automatic [28:0] code_ad(input [17:0] tk);
        reg [9:0] q; begin q = tk[9:0]; code_ad = {q[9:7], q[1:0], q[6:2], 19'(ROW0 + tk[17:10])}; end
    endfunction
    function automatic [28:0] scale_ad(input [17:0] tk);
        reg [9:0] q; begin q = 10'd384 + {3'd0, tk[17:11]}; scale_ad = {q[9:7], q[1:0], q[6:2], 19'(ROW0 + 148)}; end
    endfunction
    reg [17:0] toks [0:4];
    always @(negedge ck) if (rst_n && wv) begin
        if (nw > 64) begin errors = errors + 1; $display("FAIL extra word"); end
        else begin
            if (cyc - r0 != wexp[nw][27:12] || wsc != wexp[nw][8] || wi != (wsc ? wi : wexp[nw][5:0]) || wt != tok || we != epo)
                begin errors = errors + 1; if (errors < 10) $display("FAIL word %0d edge %0d (exp %0d) idx %0d scale %0d", nw, cyc - r0, wexp[nw][27:12], wi, wsc); end
            if (!wsc && wd != {hdat(wi[5:4], {wi[3:0], 1'b1}, code_ad(tok)), hdat(wi[5:4], {wi[3:0], 1'b0}, code_ad(tok))})
                begin errors = errors + 1; if (errors < 10) $display("FAIL word %0d data", wi); end
            sd = hdat(tok[10:9], tok[8:4], scale_ad(tok));
            if (wsc && wd != {496'd0, sd[tok[3:0]*16 +: 16]})
                begin errors = errors + 1; $display("FAIL scale data"); end
        end
        nw = nw + 1;
    end
`ifdef OT_KVJC3_DISP
    reg [63:0] t12 [0:1023]; reg [63:0] t13 [0:7]; integer nbus = 0, dt, da, dn;
    always @(posedge ck) if (cfg_we) begin
        if (nbus < 1026 && {cfg_addr, cfg_data} !== boot[nbus]) begin
            errors = errors + 1; if (errors < 10) $display("FAIL dispatcher bus word %0d %h (boot.memh %h)", nbus, {cfg_addr, cfg_data}, boot[nbus]); end
        nbus = nbus + 1;
    end
    task dword(input [3:0] tg, input integer a, input [63:0] d);
        begin target = tg; pr = 0; pr[74] = 1; pr[73:64] = 10'(a); pr[63:0] = d; @(negedge ck); pr = 0; end endtask
    task dimage(input [3:0] tg); begin pr = 0; @(negedge ck); ready = 1; target = tg; @(negedge ck); @(negedge ck); ready = 0; @(negedge ck); end endtask
`endif
    initial begin
        $readmemh({`OT_KVJC3_DIR, "/boot.memh"}, boot);
        $readmemh({`OT_KVJC3_DIR, "/words.memh"}, wexp);
        nboot = 32 * 4 * 8 + 2;
        // scale homes {stack, pc} = token[10:4]: EN/31, WS/0, WS/23 (the last token id), WN/5, and a mid token
        toks[0] = 18'd2037; toks[1] = 18'd102407; toks[2] = 18'd151935; toks[3] = 18'(1024 * 3 + (1 << 9) + (5 << 4) + 9);
        toks[4] = 18'd77777;
        repeat (4) @(negedge ck); rst_n = 1; repeat (4) @(negedge ck);
`ifdef OT_KVJC3_DISP
        $readmemh({`OT_KVJC3_DISP_DIR, "/target12.hex"}, t12); $readmemh({`OT_KVJC3_DISP_DIR, "/target13.hex"}, t13);
        for (dt = 1; dt <= 9; dt = dt + 1) begin
            case (dt) 1: dn = 327; 2: dn = 181; 3: dn = 4; 4, 5: dn = 192; default: dn = 1024; endcase
            for (da = 0; da < dn; da = da + 1) dword(4'(dt), da, (dt == 3) ? 64'(da) : 64'(dt * 4096 + da));
            dimage(4'(dt));
        end
        for (da = 0; da < 1024; da = da + 1) dword(12, da, t12[da]); dimage(12);
        for (da = 0; da < 8; da = da + 1) dword(13, da, t13[da]); dimage(13);
        target = 0; @(negedge ck); ready = 1; digest = 64'h0fedcba987654321; configured = 7; applied = {160{1'b1}};
        repeat (3) @(negedge ck);
        if (!setup || dfault || nbus != 1032) begin
            errors = errors + 1; $display("FAIL dispatcher setup %0d fault %0d code %h bus words %0d (1032)", setup, dfault, code, nbus); end
`else
        for (i = 0; i < nboot; i = i + 1) begin
            cfg_we = 1; cfg_addr = boot[i][71:64]; cfg_data = boot[i][63:0]; @(negedge ck);
        end
        cfg_we = 0; cfg_addr = 0; cfg_data = 0;
`endif
        repeat (40) @(negedge ck);
        for (t = 0; t < 5; t = t + 1) begin
            tok = toks[t]; epo = 16'(16'h1234 + t * 77); nw = 0;
            start = 1; @(posedge ck); r0 = cyc; @(negedge ck); start = 0;    // start present after edge r0
            repeat (wexp[64][27:12] + 40) @(negedge ck);
            if (nw != 65) begin errors = errors + 1; $display("FAIL token %0d words %0d", tok, nw); end
            repeat (200) @(negedge ck);
        end
        if (root_fault || |sf || |mf || |hf || jfault) begin
            errors = errors + 1;
            $display("FAIL faults root %0d station %h merge %h train %h join %0d", root_fault, sf, mf, hf, jfault);
        end
        if (errors) $display("FAIL MUT %0d errors %0d", MUT, errors);
`ifdef OT_KVJC3_DISP
        else $display("PASS KVJC3_EMB_PLAYER 5 tokens x 65 words exact edges/data, LAT %0d, no fault; boot bus from the dispatcher ESCFG targets 12/13 (%0d words == boot.memh + 6 empty segments), setup_ready", LAT, nbus);
`else
        else $display("PASS KVJC3_EMB_PLAYER 5 tokens x 65 words exact edges/data, LAT %0d, no fault", LAT);
`endif
        $finish;
    end
endmodule
