`timescale 1ns/1ps
`default_nettype none
// Reusable attention merge leaf. Its inputs are canonical FP32 lane chunk sums
// from the existing SM arithmetic, with the caller's exact last/tag alignment.
// No multipliers or accumulator lanes are instantiated here. Every merge uses
// the same modulo8 barrel, RNE adders and real64x512 stack as the proven tcpv.
// The production hierarchical caller reuses CLOSED tcl halves and provides ev
// at closed tct's LL=16 boundary. The flat component caller retains LL=12.
//
// FOLD (H-SM-ATT r2 2026-10-15, in-SM PV stream merge for head dim 128): a compiler-fixed fold request (fold_start, fold_a,
// fold_b) adds the finished level-7 node of entry fold_b into entry fold_a's (a <- a + b, one RNE add a lane on the SAME
// 16 merge adders).  Request cycle F reads {a,7}, F+1 reads {b,7}, the add issues at F+2 and the sum is written to {a,7}
// at F+2+ALAT.  Qwen: entries 2u+h hold token stream u's node of dim half h; folds (0,2)(4,6)(1,3)(5,7) then (0,4)(1,5)
// give ((s0+s1)+(s2+s3)) = the pairwise node of the 16 chunks of the 128-token block, exactly the golden order.
// Every illegal request (entry not finished, pending write, merge or publication active, port collision) is a sticky
// fault; nothing waits.  MUT 4 = the fold reads entry b in place of a (b + b: bench negative control).
module ot_hbm_sm_pv_merge #(
    parameter integer L=16, IL=8, TAGW=16, ALAT=7, LV=4, MUT=0, PUBLISH=0,
    // TURNREG 1 (HH-12 2026-10-19, smh_pvm gate: setup -341 ps at 770 ps on bp -> 8:1 entry-state mux -> operand select ->
    // 1,024-bit operand mux -> adder decode): the turn entry's state is registered one cycle ahead (entry nb = bp+1 is
    // only written at its own turn, 8 cycles earlier, so the copy equals e_*[r] exactly).  Cycle-identical; 0 = old form.
    parameter integer TURNREG=0,
    // SAFE 1 (HBM-PVM-SAFE 2026-10-19, smh_pvm route r3 NEEDS_RTL TT -125 / FF -18: macro rd_out -> operand mux -> adder
    // A1 decode/compare in one cycle; fd1 -> 3-way write mux -> macro wd_in; flop delay line fw_a/fw_v): structural form.
    //  (a) OPERAND REGISTERS: the operand mux lands in oa/ob/ov and the adders start from registers; the result register
    //      vreg is dropped (the adder's own y is read at the entry's next turn), so a merge turn stays exactly 8 cycles
    //      (1 operand + ALAT 7) and the merge stream is cycle-identical.
    //  (b) adders without datapath reset (ot_hdc_fp32_add_lat DRST 0: only valid bits reset; ~7k reset loads removed).
    //  (c) stack write data = ev ? sum : y (2:1 on one registered select; the other sources are all y).  Equal to the
    //      3-way priority mux on every non-faulting schedule (ev never coincides with a fold write-back, a finish or a
    //      chain write: each is a sticky fault or excluded by the turn logic).
    //  (d) fold write-back tracker = 8-slot ring indexed by a free-running counter (written at the add issue, read 8
    //      cycles later at the same slot) instead of the fw_a / fw_v flop delay lines.
    //  Schedule cost: a fold's sum is written ALAT + 3 cycles after its request (was ALAT + 2).  A fold may name as b a
    //  node whose write-back lands in the request cycle (b is read one cycle later); a and publication must follow the
    //  write-back by >= 1 cycle.  Qwen h128 calendar: publication of node 0 moves from F0 + 22 to F0 + 23 (+1 cycle a block).
    parameter integer SAFE=0
)(
    input wire clk, rst_n,
    input wire ev,
    input wire [L*32-1:0] sum,
    input wire [TAGW-1:0] tag_d,
    output reg pv_v,
    output reg [L*32-1:0] pv_y,
    output reg [TAGW-1:0] pv_tag,
    output wire fault,
    // Compiler-fixed publication requests; next request may prefetch while
    // word14 of the preceding node is emitted. No ready or retry port.
    input wire pub_start,
    input wire [2:0] pub_slot,
    output reg pub_v,
    output reg [31:0] pub_data,
    output reg [3:0] pub_word,
    output reg [2:0] pub_out_slot,
    output reg [TAGW-1:0] pub_tag,
    input wire fold_start,
    input wire [2:0] fold_a,
    input wire [2:0] fold_b
);
    initial if (L!=16 || IL!=8 || ALAT!=7 || LV<1 || LV>8 || TAGW<6)
        $fatal(1,"PV merge requires16lanes,8slots,LAT7,LV1..8,TAGW>=6");
    initial if(PUBLISH && LV>7)$fatal(1,"publication reserves unused stack level7");
    initial if(SAFE!=0 && (SAFE!=1 || TURNREG!=1))$fatal(1,"PV merge SAFE 1 requires TURNREG 1");
    genvar l;
    wire publish_request=PUBLISH ? pub_start : 1'b0;
    wire fold_request=PUBLISH ? fold_start : 1'b0;
    reg fd0,fd1;                                       // fold read of b, add issue
    reg [2:0] fa0,fb0,fa1;
    reg [511:0] fold_a_data;
    reg [ALAT:0] fw_v;                                 // fold sum in flight (bit k: issued k cycles ago)
    reg [2:0] fw_a [0:ALAT];
    // SAFE 1: the ring slot read this cycle holds the add issued ALAT + 1 cycles ago (operand register + ALAT)
    reg [2:0] fr_c;                                    // free-running ring index
    reg [7:0] fr_v;                                    // ring: fold add issued at this slot
    reg [2:0] fr_a [0:7];                              // ring: its entry
    wire fold_write=SAFE ? fr_v[fr_c] : fw_v[ALAT-1];  // the add issued ALAT (+1) cycles ago: my holds its sum this cycle
    wire [2:0] fold_waddr=SAFE ? fr_a[fr_c] : fw_a[ALAT-1];
    wire finish;
    wire [2:0] finish_slot;
    wire [5:0] stack_read_addr;
    wire [5:0] stack_write_addr;
    wire stack_write_en;
    wire [511:0] stack_write_data;

    // ---------------- PV: barrel binary-counter merge ----------------
    localparam integer KW = 3;
    reg  [2:0]  bp;                                   // entry whose turn it is
    always @(posedge clk or negedge rst_n) if (!rst_n) bp <= 3'd0; else bp <= bp + 3'd1;
    wire [2:0]  nb = bp + 3'd1;
    reg  [7:0]  e_busy, e_fl, e_fin;                  // busy / flushing / flush after chain
    reg  [KW:0] e_k   [0:7];                          // level of the next turn (chain: carry level; flush: fold level)
    reg  [7:0]  e_c   [0:7];                          // chunk index being merged (chain)
    reg  [8:0]  e_n   [0:7];                          // chunks of the run so far
    reg  [TAGW-1:0] e_tag [0:7];
    // events of this cycle (lane chunk sums of a PV beat)
    // stack read for entry nb, landing at its turn (next cycle)
    wire [KW:0] rk = e_busy[nb] ? e_k[nb] : {(KW+1){1'b0}};
    wire [5:0]  sr_a = {nb, rk[2:0] + ((MUT == 1) ? 3'd1 : 3'd0)};
    wire [L*32-1:0] st_rd;
    reg         sw_ce;
    reg  [5:0]  sw_a;
    reg  [L*32-1:0] sw_d;
    ot_sram_1r1w_64x512_m1_r2c2 u_stack (.clk(clk), .r_ce_in(1'b1), .r_addr_in(stack_read_addr), .rd_out(st_rd),
        .w_ce_in(stack_write_en), .w_addr_in(stack_write_addr), .wd_in(stack_write_data), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // merge adder operands of this turn
    reg  [L*32-1:0] ma, mb;
    reg             mv;
    wire [L*32-1:0] my;
    wire [L-1:0]    mf;
    reg  [L*32-1:0] vreg;                             // adder result, back at the entry's next turn (SAFE 0)
    wire [L*32-1:0] vres;                             // the result read at the entry's next turn
    generate if (SAFE) begin : g_safe
        // (a) operand registers: the adders start from flops; y is the result at the entry's next turn
        reg [L*32-1:0] oa, ob;
        reg            ov;
        always @(posedge clk) begin oa <= ma; ob <= mb; end
        always @(posedge clk or negedge rst_n) if (!rst_n) ov <= 1'b0; else ov <= mv;
        for (l = 0; l < L; l = l + 1) begin : g_madd
            wire [1:0] er;
            wire       vo;
            // (b) DRST 0: no reset on the adder datapath (valid bits only)
            ot_hdc_fp32_add_lat #(.LAT(ALAT), .DRST(0)) u_m (.clk(clk), .rst_n(rst_n), .valid_in(ov), .a(oa[32*l +: 32]),
                .b(ob[32*l +: 32]), .y(my[32*l +: 32]), .err(er), .valid_out(vo));
            assign mf[l] = vo && (er != 2'd0);
        end
        assign vres = my;
    end else begin : g_base
        for (l = 0; l < L; l = l + 1) begin : g_madd
            ot_gpu_fadd #(.LAT(ALAT)) u_m (.clk(clk), .rst_n(rst_n), .v(mv), .a(ma[32*l +: 32]), .b(mb[32*l +: 32]),
                                           .y(my[32*l +: 32]), .fault(mf[l]));
        end
        always @(posedge clk) vreg <= my;
        assign vres = vreg;
    end endgenerate
    // turn logic (combinational) for entry r = bp
    wire [2:0] r = bp;
    // turn state of entry r (TURNREG 1: registered at nb one cycle earlier; 0: read through the 8:1 entry mux)
    wire [2:0] qe = (MUT == 5) ? bp : nb;             // MUT 5: copy sampled one entry late (negative control)
    reg        q_busy, q_fl, q_klt, q_k0, q_kl1, q_ck, q_nk;
    reg  [7:0] q_n8;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin q_busy<=1'b0;q_fl<=1'b0;q_klt<=1'b1;q_k0<=1'b1;q_kl1<=(LV==1);q_ck<=1'b0;q_nk<=1'b0;q_n8<=8'd0; end
        else begin
            q_busy<=e_busy[qe]; q_fl<=e_fl[qe]; q_klt<=(e_k[qe]<LV); q_k0<=(e_k[qe]==0); q_kl1<=(e_k[qe]==LV-1);
            q_ck<=e_c[qe][e_k[qe][2:0]]; q_nk<=e_n[qe][e_k[qe][2:0]]; q_n8<=e_n[qe][7:0];
        end
    wire       t_busy = TURNREG ? q_busy : e_busy[r];
    wire       t_fl   = TURNREG ? q_fl   : e_fl[r];
    wire       t_klt  = TURNREG ? q_klt  : (e_k[r] < LV);
    wire       t_k0   = TURNREG ? q_k0   : (e_k[r] == 0);
    wire       t_kl1  = TURNREG ? q_kl1  : (e_k[r] == LV - 1);
    wire       t_ck   = TURNREG ? q_ck   : e_c[r][e_k[r][2:0]];
    wire       t_nk   = TURNREG ? q_nk   : e_n[r][e_k[r][2:0]];
    wire [7:0] t_n8   = TURNREG ? q_n8   : e_n[r][7:0];
`ifndef SYNTHESIS
    always @(posedge clk) if (TURNREG && rst_n &&
        ({q_busy,q_fl,q_klt,q_k0,q_kl1,q_ck,q_nk,q_n8} !== {e_busy[r],e_fl[r],(e_k[r]<LV),(e_k[r]==0),(e_k[r]==LV-1),
          e_c[r][e_k[r][2:0]],e_n[r][e_k[r][2:0]],e_n[r][7:0]}))
        $fatal(1, "pv_merge TURNREG copy differs from entry %0d state", r);
`endif
    assign finish=t_busy && t_fl && !t_klt && !ev;
    assign finish_slot=e_tag[r][2:0];
    assign stack_read_addr=publish_request ? {pub_slot,3'd7} : fold_request ? {((MUT==4) ? fold_b : fold_a),3'd7} : fd0 ? {fb0,3'd7} : sr_a;
    assign stack_write_en=sw_ce || (PUBLISH && finish) || fold_write;
    assign stack_write_addr=fold_write ? {fold_waddr,3'd7} : (PUBLISH && finish) ? {finish_slot,3'd7} : sw_a;
    // (c) SAFE: ev ? sum : y (the fold, finish and chain writes all store y); base: the 3-way priority mux
    assign stack_write_data=SAFE ? (ev ? sum : my) : fold_write ? my : (PUBLISH && finish) ? vreg : sw_d;

    wire       ev_first = tag_d[TAGW-2], ev_last = tag_d[TAGW-3];
    wire [7:0] ev_c = ev_first ? 8'd0 : t_n8;
    reg        m_fault;
    always @(*) begin
        mv = 1'b0; ma = {L*32{1'b0}}; mb = {L*32{1'b0}};
        sw_ce = 1'b0; sw_a = {r, 3'd0}; sw_d = sum;
        if (fd1) begin mv = 1'b1; ma = fold_a_data; mb = st_rd; end
        else if (ev) begin
            if (ev_c[0]) begin mv = 1'b1; ma = st_rd; mb = sum; end
            else begin sw_ce = 1'b1; sw_a = {r, 3'd0}; sw_d = sum; end
        end else if (t_busy && !t_fl) begin
            if (t_ck) begin mv = 1'b1; ma = st_rd; mb = vres; end
            else begin sw_ce = 1'b1; sw_a = {r, e_k[r][2:0]}; sw_d = vres; end
        end else if (t_busy && t_fl && t_klt) begin
            mv = 1'b1;
            if (t_nk) begin ma = st_rd; mb = t_k0 ? {L*32{1'b0}} : vres; end
            else begin ma = (t_k0 || (MUT == 2 && t_kl1)) ? {L*32{1'b0}} : vres; mb = {L*32{1'b0}}; end
        end
    end
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            e_busy <= 8'd0; e_fl <= 8'd0; e_fin <= 8'd0; pv_v <= 1'b0; m_fault <= 1'b0;
            for (i = 0; i < 8; i = i + 1) begin e_k[i] <= 0; e_c[i] <= 8'd0; e_n[i] <= 9'd0; end
        end else begin
            pv_v <= 1'b0;
            if (|mf) m_fault <= 1'b1;
            if (ev) begin
                if (e_busy[r]) m_fault <= 1'b1;                       // chunk arrived while the entry still merges
                if (ev_c >= (8'd1 << (LV - 1))) m_fault <= 1'b1;      // run longer than the stack
                e_tag[r] <= tag_d;
                e_n[r] <= {1'b0, ev_c} + 9'd1;
                e_c[r] <= ev_c;
                if (ev_c[0]) begin e_busy[r] <= 1'b1; e_fl[r] <= 1'b0; e_k[r] <= 1; e_fin[r] <= ev_last; end
                else if (ev_last) begin e_busy[r] <= 1'b1; e_fl[r] <= 1'b1; e_k[r] <= 0; end
            end else if (e_busy[r] && !e_fl[r]) begin
                if (e_c[r][e_k[r][2:0]]) e_k[r] <= e_k[r] + 1;
                else if (e_fin[r]) begin e_fl[r] <= 1'b1; e_k[r] <= 0; end
                else e_busy[r] <= 1'b0;
            end else if (e_busy[r] && e_fl[r]) begin
                if (e_k[r] < LV) e_k[r] <= e_k[r] + 1;
                else begin e_busy[r] <= 1'b0; e_fl[r] <= 1'b0; pv_v <= 1'b1; end
            end
        end
    end
    always @(posedge clk) if (finish) begin pv_y <= vres; pv_tag <= e_tag[r]; end
    // The unused level7 stores one final512bit node for each logical slot.
    // Publication shares the existing1R1W macro after the merge is quiescent.
    // Macro read -> buffer capture -> first scalar is exactly2edges. Requests
    // at word14 prefetch the next node without a gap or another memory macro.
    reg [7:0] node_valid;
    reg [7:0] node_pending;                           // fold sum not yet written back
    reg fold_fault;
    integer fk;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin fd0<=0;fd1<=0;fw_v<=0;fold_fault<=0;node_pending<=0;end
        else begin
            fd0<=fold_request;fd1<=fd0;
            fw_v<={fw_v[ALAT-1:0],fd1};
            if(fold_request)begin
                fa0<=fold_a;fb0<=fold_b;
                if(!node_valid[fold_a] || !node_valid[fold_b] || node_pending[fold_a] ||
                   (node_pending[fold_b] && !(SAFE && fold_write && fold_waddr==fold_b)) ||
                   fold_a==fold_b || ev || (|e_busy) || publish_request || pub_d0 || pub_d1 || pub_active || fd0)fold_fault<=1;
                node_pending[fold_a]<=1'b1;
            end
            if(fd0)fa1<=fa0;
            if(fd1 && (ev || (|e_busy)))fold_fault<=1;
            if(fold_write)begin
                node_pending[fold_waddr]<=1'b0;
                if(sw_ce || (PUBLISH && finish))fold_fault<=1;
            end
            if(publish_request && node_pending[pub_slot])fold_fault<=1;
            if(ev && (|node_pending))fold_fault<=1;
        end
    always @(posedge clk)begin
        if(fd0)fold_a_data<=st_rd;
        fw_a[0]<=fa1;
        for(fk=1;fk<=ALAT;fk=fk+1)fw_a[fk]<=fw_a[fk-1];
    end
    // (d) SAFE fold ring: slot fr_c is read (write-back of the add issued 8 cycles ago) and rewritten (this cycle's issue)
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin fr_c<=3'd0;fr_v<=8'd0;end
        else begin fr_c<=fr_c+3'd1;fr_v[fr_c]<=fd1;end
    always @(posedge clk) if(fd1)fr_a[fr_c]<=fa1;
    reg [TAGW-1:0] node_tag[0:7];
    reg pub_d0,pub_d1,pub_active,pub_fault;
    reg [2:0] slot0,slot1;
    reg [TAGW-1:0] tag0,tag1;
    reg [511:0] pub_buffer;
    reg [3:0] word_next;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            node_valid<=0;pub_d0<=0;pub_d1<=0;pub_active<=0;pub_fault<=0;
            pub_v<=0;word_next<=0;
        end else begin
            pub_d0<=publish_request;pub_d1<=pub_d0;
            pub_v<=pub_d1 || pub_active;
            if(PUBLISH && ev && ev_first)node_valid[tag_d[2:0]]<=0;
            if(fold_request)node_valid[fold_b]<=0;      // b is consumed by the fold
            if(PUBLISH && finish)begin
                node_valid[finish_slot]<=1;node_tag[finish_slot]<=e_tag[r];
                if(sw_ce)pub_fault<=1;
            end
            if(publish_request)begin
                slot0<=pub_slot;tag0<=node_tag[pub_slot];
                if(!node_valid[pub_slot] || ev || (|e_busy) || pub_d0 || pub_d1 ||
                   (pub_active && word_next!=14))pub_fault<=1;
            end
            if(ev && (pub_active || pub_d0 || pub_d1))pub_fault<=1;
            if(pub_d0)begin pub_buffer<=st_rd;slot1<=slot0;tag1<=tag0;end
            if(pub_d1)begin
                pub_data<=pub_buffer[((MUT==3)?32:0)+:32];pub_word<=0;pub_out_slot<=slot1;pub_tag<=tag1;
                word_next<=1;pub_active<=1;
            end else if(pub_active)begin
                pub_data<=pub_buffer[32*(word_next ^ ((MUT==3)?4'd1:4'd0))+:32];pub_word<=word_next;
                if(word_next==15)begin pub_active<=0;word_next<=0;end
                else word_next<=word_next+1;
            end
        end
    assign fault = m_fault | pub_fault | fold_fault;
endmodule
`default_nettype wire
