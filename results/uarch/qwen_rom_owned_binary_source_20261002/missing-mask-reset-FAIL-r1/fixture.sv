`timescale 1ns/1ps
module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN);
 always @(posedge CLK or negedge RESETN or negedge SETN)
 if(!RESETN) QN<=1'b1;else if(!SETN) QN<=1'b0;else QN<=!D;endmodule
 module INVx1_ASAP7_75t_R(input A,output Y);assign Y=~A;endmodule
 module BUFx4_ASAP7_75t_R(input A,output Y);assign Y=A;endmodule
 module AND3x1_ASAP7_75t_R(input A,B,C,output Y);assign Y=A&B&C;endmodule
 module metadata #(parameter ROM_REPLICA_CELL_RETENTION=0)(input clk,rst_n,wrom_re,input[23:0]wrom_addr,input[2659:0]rom_rd,output[511:0]wrom_q);
 localparam CODE_BANKS=5,TG=4,W=16,MEM_EXTRA=1,AW=24,ROM_CONTROL_DISTRIBUTION=1,ROM_BANK5_CONTROL=1,ROM_HOLD_DIRECT_CAPTURE=1;
 wire[4:0]rom_ce;wire[11:0]rom_addr;wire[119:0]rom_distributed_addr;
     wire [CODE_BANKS-1:0] code_rd_bank; // Explicit before primitive-port expression.
    reg  [CODE_BANKS-1:0] code_sel_q;
    genvar b, p;
    generate
        for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_ce
            assign rom_ce[b] = wrom_re && (wrom_addr[AW-1:12] == b);
        end
    endgenerate
    assign rom_addr = wrom_addr[11:0];
    wire [84:0] distributed_strobe_n;
    wire [79:0] distributed_hold_term;
    wire [89:0] distributed_metadata_reset_n;
    wire [4:0] bank_hold_term;
    generate if (ROM_CONTROL_DISTRIBUTION != 0) begin : g_distribution
        genvar db;
        for (db=0; db<5; db=db+1) begin : g_term
            assign bank_hold_term[db] = code_sel_q[db] & ~distributed_strobe_n[17*db];
        end
        ot_qwen_rom_bank5_control_distribution u_tree (
            .bank_read_n(~code_rd_bank), .bank_hold_term(bank_hold_term),
            .low_address(rom_addr), .reset_n(rst_n),
            .strobe_sink_n(distributed_strobe_n), .hold_term_sink(distributed_hold_term),
            .macro_address(rom_distributed_addr), .metadata_reset_n(distributed_metadata_reset_n));
        for (db=0;db<5;db=db+1) begin : g_early_select
            always @(posedge clk or negedge distributed_metadata_reset_n[db])
                if (!distributed_metadata_reset_n[db]) code_sel_q[db] <= 1'b0;
                else if (wrom_re) code_sel_q[db] <= rom_ce[db];
        end
    end else begin : g_undistributed
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) code_sel_q <= {CODE_BANKS{1'b0}};
            else if (wrom_re) code_sel_q <= rom_ce;
        end
        assign rom_distributed_addr = {10{rom_addr}};
        assign distributed_strobe_n = 85'b0;
        assign distributed_hold_term = 80'b0;
        assign distributed_metadata_reset_n = {90{rst_n}};
        assign bank_hold_term = 5'b0;
    end endgenerate
    //: MEM_EXTRA: the read strobe and bank select one more cycle, for the captured banks' OR
    wire code_rd_q;
    reg [CODE_BANKS-1:0] code_sel_q2;
    generate if (ROM_CONTROL_DISTRIBUTION != 0 &&
        (ROM_BANK5_CONTROL == 0 || ROM_HOLD_DIRECT_CAPTURE == 0 || W != 16 || TG != 4 || CODE_BANKS != 5 || MEM_EXTRA != 1)) begin : g_unpriced_distribution
        initial $error("ROM_CONTROL_DISTRIBUTION requires priced bank5/direct W16/TG4/CB5/MEM_EXTRA1");
    end endgenerate
    generate if (ROM_BANK5_CONTROL != 0) begin : g_bank_control
        genvar rb;
        for (rb = 0; rb < CODE_BANKS; rb = rb + 1) begin : g_bank
            wire read_q;
            wire bank_reset_n = (ROM_CONTROL_DISTRIBUTION != 0) ? distributed_metadata_reset_n[5+rb] : rst_n;
            if (ROM_REPLICA_CELL_RETENTION != 0) begin : g_retained
                wire read_q_n;
                // Actual RVT Liberty: QN next_state=!D, RESETN presets QN=1.
                (* keep = 1, dont_touch = 1 *) DFFASRHQNx1_ASAP7_75t_R u_read_ff
                    (.CLK(clk), .D(wrom_re), .RESETN(bank_reset_n), .SETN(1'b1), .QN(read_q_n));
                assign read_q = ~read_q_n;
            end else begin : g_inferred
                reg read_state_q;
                always @(posedge clk or negedge bank_reset_n)
                    if (!bank_reset_n) read_state_q <= 1'b0;
                    else read_state_q <= wrom_re;
                assign read_q = read_state_q;
            end
            assign code_rd_bank[rb] = read_q;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) code_sel_q2[rb] <= 1'b0;
                else if (read_q) code_sel_q2[rb] <= code_sel_q[rb];
        end
        assign code_rd_q = code_rd_bank[0];
    end else begin : g_shared_control
        reg read_q;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin read_q <= 1'b0; code_sel_q2 <= {CODE_BANKS{1'b0}}; end
            else begin
                read_q <= wrom_re;
                if (read_q) code_sel_q2 <= code_sel_q;
            end
        end
        assign code_rd_q = read_q;
        assign code_rd_bank = {CODE_BANKS{read_q}};
    end endgenerate
    generate if (ROM_BANK5_CONTROL != 0 &&
        (ROM_HOLD_DIRECT_CAPTURE == 0 || W != 16 || TG != 4 || CODE_BANKS != 5 || MEM_EXTRA != 1)) begin : g_unpriced_bank5
        initial $error("ROM_BANK5_CONTROL requires priced directcapture W16/TG4/CB5/MEM_EXTRA1");
    end endgenerate
    generate if (ROM_HOLD_DIRECT_CAPTURE != 0 &&
        (W != 16 || TG != 4 || CODE_BANKS != 5 || MEM_EXTRA != 1)) begin : g_unpriced_shape
        initial $error("ROM_HOLD_DIRECT_CAPTURE requires Maxwell-priced W16/TG4/CB5/MEM_EXTRA1");
    end endgenerate
    localparam integer PWB = 2 * W * 8;      // a group pair's slice of the code word (256 of the macro's 266 bits)
    generate
        for (p = 0; p < TG / 2; p = p + 1) begin : g_pair
            wire [PWB-1:0] or_q [0:CODE_BANKS];
            assign or_q[0] = {PWB{1'b0}};
            for (b = 0; b < CODE_BANKS; b = b + 1) begin : g_bank
                wire [PWB-1:0] rd = rom_rd[(p*CODE_BANKS + b)*266 +: PWB];
                if (MEM_EXTRA != 0) begin : g_cap
                    if (ROM_HOLD_DIRECT_CAPTURE != 0) begin : g_direct
                        // CE-idle holds rd in the source ROM. Observability is
                        // still qualified by identical delayed bank metadata.
                        reg [PWB-1:0] cap;
                        always @(posedge clk) cap <= rd;
                        genvar chunk;
                        for (chunk = 0; chunk < PWB / 32; chunk = chunk + 1) begin : g_mask
                            // Eight32-bit chunks per column,16 per bank:
                            // exactly80 reset/hold selectorFFs. Keep replicas
                            // for physical locality; mapped preservation gates.
                            wire local_sel;
                            wire mask_reset_n = (ROM_CONTROL_DISTRIBUTION != 0) ?
                                distributed_metadata_reset_n[10+16*b+8*p+chunk] : rst_n;
                            if (ROM_REPLICA_CELL_RETENTION != 0) begin : g_retained
                                wire local_sel_n;
                                reg local_next;
                                always @* begin
                                    local_next = local_sel;
                                    if (ROM_CONTROL_DISTRIBUTION != 0) begin
                                        if (!distributed_strobe_n[17*b+1+8*p+chunk])
                                            local_next = distributed_hold_term[16*b+8*p+chunk];
                                    end else if (code_rd_bank[b]) local_next = code_sel_q[b];
                                end
                                (* keep = 1, dont_touch = 1 *) DFFASRHQNx1_ASAP7_75t_R u_mask_ff
                                    (.CLK(clk), .D(local_next), .RESETN(1'b1), .SETN(1'b1), .QN(local_sel_n));
                                assign local_sel = ~local_sel_n;
                            end else begin : g_inferred
                                reg local_state_q;
                                always @(posedge clk or negedge mask_reset_n) begin
                                    if (!mask_reset_n) local_state_q <= 1'b0;
                                    else if (ROM_CONTROL_DISTRIBUTION != 0) begin
                                        if (!distributed_strobe_n[17*b+1+8*p+chunk])
                                            local_state_q <= distributed_hold_term[16*b+8*p+chunk];
                                    end else if (code_rd_bank[b]) local_state_q <= code_sel_q[b];
                                end
                                assign local_sel = local_state_q;
                            end
                            assign or_q[b+1][32*chunk +: 32] = or_q[b][32*chunk +: 32] |
                                (cap[32*chunk +: 32] & {32{local_sel}});
                        end
                    end else begin : g_original
                        // Original source behavior, defaultoff.
                        reg [PWB-1:0] cap;
                        always @(posedge clk) if (code_sel_q[b] && code_rd_q) cap <= rd;
                        assign or_q[b+1] = or_q[b] | (cap & {PWB{code_sel_q2[b]}});
                    end
                end else begin : g_nocap
                    assign or_q[b+1] = or_q[b] | (rd & {PWB{code_sel_q[b]}});
                end
            end
            assign wrom_q[PWB*p +: PWB] = or_q[CODE_BANKS];
        end
    endgenerate

endmodule
 module tb;
 localparam W=16,IL=8,AW=24,NW=18,GT=6144,PRUNE=1,SMIN=6,KV_PREP=3,INT8_WEIGHT=1,INT8_SCALE_WCS_BASE=1;
 reg clk=0,external_reset_n=1,parent_domains_ready=0,ib_go=0;reg[378:0]ib=0,ib_q;reg go_q;
 wire rst_n,launch;wire go=go_q;reg wrom_re,kv_re;reg[23:0]wrom_addr;
 ot_qwen_rom_reset_parent_provider #(.RESET_CONTEXT(1)) provider(.clk_stream(clk),.external_reset_n(external_reset_n),.parent_domains_ready(parent_domains_ready),.ib_go(ib_go),.released_reset_n(rst_n),.launch_enable(launch));
 always @(posedge clk or negedge rst_n) if(!rst_n)go_q<=0;else go_q<=launch;
 always @(posedge clk)ib_q<=ib;
 wire [17:0] i_nout;
wire [17:0] i_tiles;
wire [17:0] i_k;
wire [0:0] i_wsrc;
wire [23:0] i_wbase;
wire [23:0] i_ts;
wire [23:0] i_ks;
wire [23:0] i_js;
wire [23:0] i_xbase;
wire [23:0] i_xks;
wire [23:0] i_xjs;
wire [23:0] i_xcs;
wire [2:0] i_jsh;
wire [3:0] i_split;
wire [23:0] i_wcs;
wire [0:0] i_round;
wire [23:0] i_obase;
wire [23:0] i_ots;
wire [23:0] i_ojs;
wire [0:0] i_mmode;
wire [0:0] i_oen;
wire [0:0] i_amax;
wire [0:0] i_rmax;
wire [23:0] i_mbase;
assign {i_nout,i_tiles,i_k,i_wsrc,i_wbase,i_ts,i_ks,i_js,i_xbase,i_xks,i_xjs,i_xcs,i_jsh,i_split,i_wcs,i_round,i_obase,i_ots,i_ojs,i_mmode,i_oen,i_amax,i_rmax,i_mbase}=ib_q;
    reg              active;
    assign active_o = active;
    reg [NW-1:0]     nout_r, tiles_r, k_r;
    reg              wsrc_r, round_r, oen_r, amax_r, mmode_r, rmax_r;
    reg [AW-1:0]     mbase_r;
    reg [AW-1:0]     scale_base_r;
    reg [3:0]        split_r;
    reg [AW-1:0]     tstep_r;          // weight step per round: ts, or (G/S)*ts for KV ops
    reg [AW-1:0]     wcs_r;
    reg [NW-1:0]     ktot_r;           // KV ops: the whole K (elements past it multiply +0)
    reg [AW-1:0]     ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r;
    reg [2:0]        jsh_r;
    reg [NW-1:0]     t, k;
    reg [$clog2(IL)-1:0] j;
    reg [AW-1:0]     cur, base_k, base_t, xk, xc, xk_base, oa, ot, ot_step;
    reg [NW:0]       nb, nb_t, nb_step;    // first row of the current slot / round (port 0)
    reg [NW:0]       lb, lb_step;          // first lane-vector index of the round (mmode 1)
    reg              t_last, k_last;
    wire             j_last = (j == IL - 1);
    //: pruning: an op below the smallest split the pruned tree supports
    reg              split_fault;
    //: KV_PREP > 0: a KV-sourced op waits KV_PREP cycles after its go (ready low) for its per-group KV
    //: offsets, which leave the issue path as a pipelined multiply (see g_kv_addr)
    reg              pend;
    reg [3:0]        pcnt;


generate begin:g_issue_fast

    //: FAST_ISSUE (1.2 GHz @ SS): the same schedule, cycle for cycle (plus KV_PREP on KV ops).
    //: (1) The per-op products (the round steps ts*(GT/S), ots*(GT/S), (GT/S)*W*IL, (GT/S)*W and the KV
    //:     K-step count ceil(K/S)) are first needed at the first K or round boundary, IL >= 3 cycles after
    //:     the go: they are two register stages computed from the latched fields, not an input-to-register
    //:     multiply; ts*(GT/S) is shifted adds of ts (GT's set bits), not a multiplier.
    //: (2) Every loop add is ot_qwen_w12_kadd: a Kogge-Stone prefix adder whose levels are kept netlist
    //:     boundaries (ABC re-maps a flattened `+` as a MAJ ripple: 22 cells, -656 ps at SS on `cur`).
    localparam integer PRW = $clog2(GT) + 1;
    //: x * (GT >> s), exactly, as the sum of x shifted to each set bit b >= s of the constant GT (two terms at
    //: 6,144): no multiplier
    function automatic [AW+PRW-1:0] mul_gt_shr(input [AW-1:0] x, input [3:0] sh);
        integer b;
        reg [AW+PRW-1:0] acc;
        begin
            acc = 0;
            for (b = 0; b < PRW; b = b + 1)
                if (((GT >> b) & 1) != 0 && b >= sh) acc = acc + ({{PRW{1'b0}}, x} << (b - sh));
            mul_gt_shr = acc;
        end
    endfunction
    reg [PRW-1:0]    pr_a;                 // GT >> split
    reg [AW+PRW-1:0] tsg_a, otsg_a;        // ts*(GT>>S), ots*(GT>>S)
    reg [NW-1:0]     kc_a;
    localparam [NW:0]   WNB = W;
    localparam [NW-1:0] ONE = 1, TWO = 2;
    //: three stages (the first use is IL >= 3 cycles after the go): the shifted terms, their kept sum, the result
    localparam integer NB_GT = PRW;
    reg [AW+PRW-1:0] tsh [0:NB_GT-1];
    reg [AW+PRW-1:0] osh [0:NB_GT-1];
    reg [NW:0]       kpad_a;
    always @(posedge clk) begin : p_terms
        integer b;
        for (b = 0; b < NB_GT; b = b + 1) begin
            tsh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ts_r} << (b - split_r)) : {(AW+PRW){1'b0}};
            osh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ots_r} << (b - split_r)) : {(AW+PRW){1'b0}};
        end
        pr_a <= GT >> split_r;
        kpad_a <= {1'b0, ktot_r} + ((1 << split_r) - 1);
    end
    wire [AW+PRW-1:0] tsum, osum;
    wire [NB_GT*(AW+PRW)-1:0] tsh_flat, osh_flat;
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_ts (.rows(tsh_flat), .s(tsum));
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_os (.rows(osh_flat), .s(osum));
    genvar tb;
    for (tb = 0; tb < NB_GT; tb = tb + 1) begin : g_fl
        assign tsh_flat[tb*(AW+PRW) +: AW+PRW] = tsh[tb];
        assign osh_flat[tb*(AW+PRW) +: AW+PRW] = osh[tb];
    end
    always @(posedge clk) begin
        tsg_a <= tsum; otsg_a <= osum;
        kc_a <= wsrc_r ? kpad_a[NW-1:0] >> split_r : ktot_r;       // ceil(K/S) (K + S - 1 < 2^NW)
        tstep_r <= !wsrc_r ? ts_r : tsg_a[AW-1:0];
        ot_step <= otsg_a[AW-1:0];
        nb_step <= pr_a * (W * IL);
        lb_step <= pr_a * W;
        k_r <= kc_a;
    end
    //: loop adds
    wire [AW-1:0] cur_js, oa_j, xc_j, bk_k, xk_k, bt_t, ot_t;
    wire [NW:0]   nb_j, nbt_t, lb_t;
    wire [NW-1:0] k_1, k_2, t_1, t_2;
    ot_qwen_w12_kadd #(.W(AW)) u_a0 (.a(cur), .b(js_r), .s(cur_js));
    ot_qwen_w12_kadd #(.W(AW)) u_a1 (.a(oa), .b(ojs_r), .s(oa_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a2 (.a(xc), .b(xjs_r), .s(xc_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a3 (.a(base_k), .b(ks_r), .s(bk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a4 (.a(xk), .b(xks_r), .s(xk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a5 (.a(base_t), .b(tstep_r), .s(bt_t));
    ot_qwen_w12_kadd #(.W(AW)) u_a6 (.a(ot), .b(ot_step), .s(ot_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a7 (.a(nb), .b(WNB), .s(nb_j));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a8 (.a(nb_t), .b(nb_step), .s(nbt_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a9 (.a(lb), .b(lb_step), .s(lb_t));
    ot_qwen_w12_kadd #(.W(NW)) u_a10 (.a(k), .b(ONE), .s(k_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a11 (.a(k), .b(TWO), .s(k_2));
    ot_qwen_w12_kadd #(.W(NW)) u_a12 (.a(t), .b(ONE), .s(t_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a13 (.a(t), .b(TWO), .s(t_2));
    //: the go's own first-boundary flags, without the K-step divide: ceil(K/S) == 1 <=> K <= S
    wire kc_is_1 = i_wsrc ? ({{(32-NW){1'b0}}, i_k} <= (32'd1 << i_split)) : (i_k == 1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
            split_fault <= 1'b0;
        end else if (pend) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (pcnt == 0) begin pend <= 1'b0; active <= 1'b1; end
            else pcnt <= pcnt - 1'b1;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                if (KV_PREP > 0 && i_wsrc) begin pend <= 1'b1; pcnt <= KV_PREP - 1; end
                else active <= 1'b1;
                if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; ktot_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                rmax_r <= i_rmax; mbase_r <= i_mbase;
                scale_base_r <= (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
                mmode_r <= i_mmode; split_r <= i_split; wcs_r <= i_wcs;
                ts_r <= i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= kc_is_1;
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase;
                nb <= 0; nb_t <= 0;
                lb <= 0;
            end
        end else begin
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa_j; nb <= nb_j; xc <= xc_j;
                if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur_js;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k_1; k_last <= (k_2 == k_r);
                    base_k <= bk_k; cur <= bk_k;
                    xk <= xk_k; xc <= xk_k;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk_base; xc <= xk_base;
                    if (!t_last) begin
                        t <= t_1; t_last <= (t_2 == tiles_r);
                        base_t <= bt_t; base_k <= bt_t; cur <= bt_t;
                        ot <= ot_t; oa <= ot_t;
                        nb_t <= nbt_t; nb <= nbt_t; lb <= lb_t;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end
end endgenerate
 reg[2659:0]rom_rd;
 wire[511:0]a,b;
 metadata #(.ROM_REPLICA_CELL_RETENTION(0)) inferred(clk,rst_n,wrom_re,wrom_addr,rom_rd,a);
 metadata #(.ROM_REPLICA_CELL_RETENTION(1)) retained(clk,rst_n,wrom_re,wrom_addr,rom_rd,b);
 genvar pair,bank,chunk;
 generate for(pair=0;pair<2;pair=pair+1)begin:rp for(bank=0;bank<5;bank=bank+1)begin:rb
 localparam[31:0]PAYLOAD=32'h12340000+pair*5+bank;
 always @(posedge clk)if(retained.rom_ce[bank])rom_rd[(pair*5+bank)*266+:266]<={10'd0,{8{PAYLOAD}}};
 for(chunk=0;chunk<8;chunk=chunk+1)begin:rc
 always @(negedge clk)if(rst_n)begin
 if(retained.g_pair[pair].g_bank[bank].g_cap.g_direct.g_mask[chunk].local_sel !== inferred.g_pair[pair].g_bank[bank].g_cap.g_direct.g_mask[chunk].local_sel)$fatal(1,"mask equivalence");
 if(retained.g_pair[pair].g_bank[bank].g_cap.g_direct.g_mask[chunk].local_sel !== 0 && retained.g_pair[pair].g_bank[bank].g_cap.g_direct.g_mask[chunk].local_sel !== 1)$fatal(1,"mask not initialized binary");
 end end end end endgenerate
 integer ticks=0;
 task tick;begin #1;clk=1;#1;
 if(launch && (!parent_domains_ready || !rst_n))$fatal(1,"launch before owned readiness");
 if(launch && $isunknown(ib))$fatal(1,"accepted instruction not binary");
 if(rst_n)begin
 if($isunknown(retained.code_sel_q) || $isunknown(retained.code_rd_bank) || $isunknown(retained.code_sel_q2))$fatal(1,"metadata not initialized binary");
 if(retained.code_sel_q !== inferred.code_sel_q || retained.code_rd_bank !== inferred.code_rd_bank || retained.code_sel_q2 !== inferred.code_sel_q2)$fatal(1,"metadata equivalence");
 if(a !== b || $isunknown(b))$fatal(1,"unqualified payload observation");
 end clk=0;#1;ticks=ticks+1;end endtask
 initial begin
 external_reset_n=0;tick;tick;external_reset_n=1;
 ib=379'h1000000800020000000000400000200000010000000000000000000000000c0000000000000000000000000000000;
parent_domains_ready=0;ib_go=1;tick;tick;ib_go=0;tick;parent_domains_ready=1;tick;ib_go=1;tick;ib_go=0;
repeat(28)tick;
ib=379'h1000000800020010000000400000200000010000000000000000000000000c0000000000000000000000000000000;
parent_domains_ready=0;ib_go=1;tick;tick;ib_go=0;tick;parent_domains_ready=1;tick;ib_go=1;tick;ib_go=0;
repeat(28)tick;
ib=379'h1000000800020020000000400000200000010000000000000000000000000c0000000000000000000000000000000;
parent_domains_ready=0;ib_go=1;tick;tick;ib_go=0;tick;parent_domains_ready=1;tick;ib_go=1;tick;ib_go=0;
repeat(28)tick;
ib=379'h1000000800020030000000400000200000010000000000000000000000000c0000000000000000000000000000000;
parent_domains_ready=0;ib_go=1;tick;tick;ib_go=0;tick;parent_domains_ready=1;tick;ib_go=1;tick;ib_go=0;
repeat(28)tick;
external_reset_n=0;#1;if(retained.code_sel_q!==0 || retained.code_rd_bank!==0)$fatal(1,"async reset");tick;tick;external_reset_n=1;tick;tick;
ib=379'h1000000800020040000000400000200000010000000000000000000000000c0000000000000000000000000000000;
parent_domains_ready=0;ib_go=1;tick;tick;ib_go=0;tick;parent_domains_ready=1;tick;ib_go=1;tick;ib_go=0;
repeat(28)tick;
ib=379'h1000000800020000000000400000200000010000000000000000000000000c0000000000000000000000000000000;
parent_domains_ready=0;ib_go=1;tick;tick;ib_go=0;tick;parent_domains_ready=1;tick;ib_go=1;tick;ib_go=0;
repeat(28)tick;
ib=379'h1000000800810000000000400000200000010000000000000000000000000c0000000000000000000000000000000;
parent_domains_ready=0;ib_go=1;tick;tick;ib_go=0;tick;parent_domains_ready=1;tick;ib_go=1;tick;ib_go=0;
repeat(28)tick;
$display("PASS_LITERAL_BINARY_INIT_METADATA_CONTROL ticks=%0d",ticks);$finish;end endmodule
