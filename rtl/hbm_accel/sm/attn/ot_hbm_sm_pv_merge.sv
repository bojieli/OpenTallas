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
//
// RDREG (HBM-CORES-B 11-12, DIE-HBM-100 pv_merge event form; default 0 = unchanged): 1 registers the u_stack read
// data at the macro output (st_q), so no logic hangs off the macro rd_out pins.  +1 edge on the stack read path:
//   merge   the barrel issues each entry's read two turns ahead (bp+2 instead of bp+1); an entry's state changes
//           only at its own turn, so the address is the same and every merge turn, pv_v / pv_y / pv_tag are
//           cycle-identical to RDREG 0;
//   publish request timing and every request rule are unchanged; pub_v / pub_data / pub_word / pub_out_slot /
//           pub_tag are the RDREG 0 stream delayed by exactly one edge (first scalar 3 edges after the request);
//   fold    the add issues at F+3 (was F+2) and the sum is written at F+3+ALAT; the folded entry stays pending one
//           edge longer, so the first ev / publication / fold that touches it may come one edge later.
// RDMUT (bench negative controls only, needs RDREG 1): 1 = merge read issued one turn ahead (stale stack data);
// 2 = publication data word taken from an off-by-one word index; 3 = fold add issued at F+2 (operand not there).
//
// TREG (HBM-CORES-B 11-12, DIE-HBM-100 pv_merge event form F2 + RDREG + TREG; default 0 = unchanged): registered,
// replicated turn decode.  The turn logic indexes the barrel entry r = bp (8:1 of e_busy / e_fl / e_k / e_c / e_n) and
// drives 512-bit operand, write-data and pv_y selects; pvm_F2R (F2 + RDREG) failed TT setup -87 ps on 553 endpoints, every
// one starting at bp.  An entry's state changes only at its own turn, so entry bp+1's decode taken one cycle early equals
// entry bp's decode at its turn.  TREG 1 registers that decode (reset to the reset-state decode) in NG copies, one per
// 512/NG-bit lane group next to the muxes it selects (keep), plus one control copy.  Only ev / tag_d (inputs of this cycle)
// combine with the copies.  Cycle-identical: no pin-cycle change.  TRMUT 1 (negative control only): the copies take the
// decode of entry bp (the current turn) instead of bp+1.
module ot_hbm_sm_pv_merge #(
    parameter integer L=16, IL=8, TAGW=16, ALAT=7, LV=4, MUT=0, PUBLISH=0, RDREG=0, RDMUT=0, TREG=0, TRMUT=0
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
    initial if((RDREG!=0 && RDREG!=1) || (RDMUT!=0 && RDREG!=1))$fatal(1,"RDREG 0/1; RDMUT needs RDREG 1");
    initial if((TREG!=0 && TREG!=1) || (TRMUT!=0 && TREG!=1))$fatal(1,"TREG 0/1; TRMUT needs TREG 1");
    initial if(PUBLISH && LV>7)$fatal(1,"publication reserves unused stack level7");
    genvar l;
    wire publish_request=PUBLISH ? pub_start : 1'b0;
    wire fold_request=PUBLISH ? fold_start : 1'b0;
    reg fd0,fd1,fd2;                                   // fold read of b, add issue (RDREG 1: fd2 issues)
    reg [2:0] fa0,fb0,fa1,fa2;
    reg [511:0] fold_a_data;
    reg [ALAT:0] fw_v;                                 // fold sum in flight (bit k: issued k cycles ago)
    reg [2:0] fw_a [0:ALAT];
    wire fold_write=fw_v[ALAT-1];                      // the add issued ALAT cycles ago: my holds its sum this cycle
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
    // RDREG 1: the read is issued two turns ahead (entry bp+2) and lands in st_q at the entry's turn
    wire [2:0]  na = (RDREG == 1 && RDMUT != 1) ? bp + 3'd2 : nb;
    wire [KW:0] rk = e_busy[na] ? e_k[na] : {(KW+1){1'b0}};
    wire [5:0]  sr_a = {na, rk[2:0] + ((MUT == 1) ? 3'd1 : 3'd0)};
    wire [L*32-1:0] st_rd;                            // macro rd_out
    wire [L*32-1:0] st_q;                             // stack read data as used by the merge / fold / publication
    reg         sw_ce;
    reg  [5:0]  sw_a;
    reg  [L*32-1:0] sw_d;
    ot_sram_1r1w_64x512_m1_r2c2 u_stack (.clk(clk), .r_ce_in(1'b1), .r_addr_in(stack_read_addr), .rd_out(st_rd),
        .w_ce_in(stack_write_en), .w_addr_in(stack_write_addr), .wd_in(stack_write_data), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    generate if (RDREG == 1) begin : g_rdreg
        reg [L*32-1:0] rq;                            // macro-output register: the only load on rd_out
        always @(posedge clk) rq <= st_rd;
        assign st_q = rq;
    end else begin : g_rdnone
        assign st_q = st_rd;
    end endgenerate
    wire fold_issue = (RDREG == 1 && RDMUT != 3) ? fd2 : fd1;  // fold add: both operands present
    // merge adder operands of this turn
    reg  [L*32-1:0] ma, mb;
    reg             mv;
    wire [L*32-1:0] my;
    wire [L-1:0]    mf;
    reg  [L*32-1:0] vreg;                             // adder result, back at the entry's next turn
    generate for (l = 0; l < L; l = l + 1) begin : g_madd
        ot_gpu_fadd #(.LAT(ALAT)) u_m (.clk(clk), .rst_n(rst_n), .v(mv), .a(ma[32*l +: 32]), .b(mb[32*l +: 32]),
                                       .y(my[32*l +: 32]), .fault(mf[l]));
    end endgenerate
    always @(posedge clk) vreg <= my;
    // turn logic (combinational) for entry r = bp
    wire [2:0] r = bp;
    assign finish=td[NG][10] && td[NG][9] && !td[NG][8] && !ev;
    assign finish_slot=e_tag[r][2:0];
    assign stack_read_addr=publish_request ? {pub_slot,3'd7} : fold_request ? {((MUT==4) ? fold_b : fold_a),3'd7} : fd0 ? {fb0,3'd7} : sr_a;
    assign stack_write_en=sw_ce || (PUBLISH && finish) || fold_write;
    assign stack_write_addr=fold_write ? {fw_a[ALAT-1],3'd7} : (PUBLISH && finish) ? {finish_slot,3'd7} : sw_a;
    assign stack_write_data=fold_write ? my : (PUBLISH && finish) ? vreg : sw_d;

    wire       ev_first = tag_d[TAGW-2], ev_last = tag_d[TAGW-3];
    wire [7:0] ev_c = ev_first ? 8'd0 : e_n[r][7:0];
    reg        m_fault;
    // ---- turn decode of entry r = bp: live (TREG 0) or registered one cycle early from entry bp+1 (TREG 1) ----
    // d = {busy, fl, k<LV, c[k], n[k], k==0, k==0||(MUT2 && k==LV-1), n[0], k[2:0]}
    localparam integer NG = 4, GW = L*32/NG, DW = 11;
    function automatic [DW-1:0] tdec(input integer x);
        reg [KW:0] k;
        begin
            k = e_k[x];
            tdec = {e_busy[x], e_fl[x], (k < LV), e_c[x][k[2:0]], e_n[x][k[2:0]], (k == 0),
                    (k == 0 || (MUT == 2 && k == LV - 1)), e_n[x][0], k[2:0]};
        end
    endfunction
    localparam [DW-1:0] TDEC_RST = {1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b1, 1'b1, 1'b0, 3'd0};  // every entry in reset
    wire [DW-1:0] td_live = tdec(r);
    wire [DW-1:0] td_next = tdec((TRMUT == 1) ? bp : nb);
    wire [DW-1:0] td [0:NG];                          // [0..NG-1] lane-group copies, [NG] control copy
    genvar gq;
    generate for (gq = 0; gq <= NG; gq = gq + 1) begin : g_td
        if (TREG == 1) begin : g_q
            (* keep *) reg [DW-1:0] q;
            always @(posedge clk or negedge rst_n) if (!rst_n) q <= TDEC_RST; else q <= td_next;
            assign td[gq] = q;
`ifdef FORMAL
            always @(posedge clk) if (rst_n) assert (q == td_live);
`endif
        end else begin : g_l
            assign td[gq] = td_live;
        end
    end endgenerate
    // control copy
    wire c_busy = td[NG][10], c_fl = td[NG][9], c_klt = td[NG][8], c_cb = td[NG][7], c_n0 = td[NG][3];
    wire [2:0] c_k3 = td[NG][2:0];
    always @(*) begin
        mv = 1'b0; sw_ce = 1'b0; sw_a = {r, 3'd0};
        if (fold_issue) mv = 1'b1;
        else if (ev) begin
            if (!ev_first && c_n0) mv = 1'b1;
            else begin sw_ce = 1'b1; sw_a = {r, 3'd0}; end
        end else if (c_busy && !c_fl) begin
            if (c_cb) mv = 1'b1;
            else begin sw_ce = 1'b1; sw_a = {r, c_k3}; end
        end else if (c_busy && c_fl && c_klt) mv = 1'b1;
    end
    // lane-group data selects, each from its own copy
    generate for (gq = 0; gq < NG; gq = gq + 1) begin : g_sel
        wire g_busy = td[gq][10], g_fl = td[gq][9], g_klt = td[gq][8], g_cb = td[gq][7], g_nb = td[gq][6],
             g_k0 = td[gq][5], g_kz = td[gq][4], g_n0 = td[gq][3];
        reg [GW-1:0] a_g, b_g, d_g;
        always @(*) begin
            a_g = {GW{1'b0}}; b_g = {GW{1'b0}}; d_g = sum[gq*GW +: GW];
            if (fold_issue) begin a_g = fold_a_data[gq*GW +: GW]; b_g = st_q[gq*GW +: GW]; end
            else if (ev) begin
                if (!ev_first && g_n0) begin a_g = st_q[gq*GW +: GW]; b_g = sum[gq*GW +: GW]; end
            end else if (g_busy && !g_fl) begin
                if (g_cb) begin a_g = st_q[gq*GW +: GW]; b_g = vreg[gq*GW +: GW]; end
                else d_g = vreg[gq*GW +: GW];
            end else if (g_busy && g_fl && g_klt) begin
                if (g_nb) begin a_g = st_q[gq*GW +: GW]; b_g = g_k0 ? {GW{1'b0}} : vreg[gq*GW +: GW]; end
                else begin a_g = g_kz ? {GW{1'b0}} : vreg[gq*GW +: GW]; b_g = {GW{1'b0}}; end
            end
        end
        always @(*) begin ma[gq*GW +: GW] = a_g; mb[gq*GW +: GW] = b_g; sw_d[gq*GW +: GW] = d_g; end
    end endgenerate
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
    generate for (gq = 0; gq < NG; gq = gq + 1) begin : g_pvy
        always @(posedge clk) if (td[gq][10] && td[gq][9] && !td[gq][8] && !ev) pv_y[gq*GW +: GW] <= vreg[gq*GW +: GW];
    end endgenerate
    always @(posedge clk) if (finish) pv_tag <= e_tag[r];
    // The unused level7 stores one final512bit node for each logical slot.
    // Publication shares the existing1R1W macro after the merge is quiescent.
    // Macro read -> buffer capture -> first scalar is exactly2edges. Requests
    // at word14 prefetch the next node without a gap or another memory macro.
    reg [7:0] node_valid;
    reg [7:0] node_pending;                           // fold sum not yet written back
    reg fold_fault;
    integer fk;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin fd0<=0;fd1<=0;fd2<=0;fw_v<=0;fold_fault<=0;node_pending<=0;end
        else begin
            fd0<=fold_request;fd1<=fd0;fd2<=fd1;
            fw_v<={fw_v[ALAT-1:0],fold_issue};
            if(fold_request)begin
                fa0<=fold_a;fb0<=fold_b;
                if(!node_valid[fold_a] || !node_valid[fold_b] || node_pending[fold_a] || node_pending[fold_b] ||
                   fold_a==fold_b || ev || (|e_busy) || publish_request || pub_d0 || pub_d1 || pub_active || fd0)fold_fault<=1;
                node_pending[fold_a]<=1'b1;
            end
            if(fd0)fa1<=fa0;
            if(fd1 && (ev || (|e_busy)))fold_fault<=1;
            if(fold_write)begin
                node_pending[fw_a[ALAT-1]]<=1'b0;
                if(sw_ce || (PUBLISH && finish))fold_fault<=1;
            end
            if(publish_request && node_pending[pub_slot])fold_fault<=1;
            if(ev && (|node_pending))fold_fault<=1;
        end
    always @(posedge clk)begin
        if((RDREG == 1) ? fd1 : fd0)fold_a_data<=st_q;
        if(fd1)fa2<=fa1;
        fw_a[0]<=(RDREG == 1) ? fa2 : fa1;
        for(fk=1;fk<=ALAT;fk=fk+1)fw_a[fk]<=fw_a[fk-1];
    end
    reg [TAGW-1:0] node_tag[0:7];
    reg pub_d0,pub_d1,pub_active,pub_fault;
    reg [2:0] slot0,slot1;
    reg [TAGW-1:0] tag0,tag1;
    reg [511:0] pub_buffer;
    reg [3:0] word_next;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            node_valid<=0;pub_d0<=0;pub_d1<=0;pub_active<=0;pub_fault<=0;
            word_next<=0;
        end else begin
            pub_d0<=publish_request;pub_d1<=pub_d0;
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
            if(pub_d0)begin slot1<=slot0;tag1<=tag0;end
            if(pub_d1)begin
                word_next<=1;pub_active<=1;
            end else if(pub_active)begin
                if(word_next==15)begin pub_active<=0;word_next<=0;end
                else word_next<=word_next+1;
            end
        end
    // publication output stage: o_* is the request-time state the scalar is emitted from
    wire o_d1,o_act;
    wire [3:0] o_wn;
    wire [2:0] o_slot;
    wire [TAGW-1:0] o_tag;
    generate if (RDREG == 1) begin : g_pubq
        reg q_d1,q_act;
        reg [3:0] q_wn;
        reg [2:0] q_slot;
        reg [TAGW-1:0] q_tag;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin q_d1<=0;q_act<=0;end
            else begin q_d1<=pub_d1;q_act<=pub_active;end
        always @(posedge clk)begin
            q_wn<=(RDMUT == 2) ? word_next + 4'd1 : word_next;q_slot<=slot1;q_tag<=tag1;
            if(pub_d1)pub_buffer<=st_q;
        end
        assign o_d1=q_d1; assign o_act=q_act; assign o_wn=q_wn; assign o_slot=q_slot; assign o_tag=q_tag;
    end else begin : g_pubd
        always @(posedge clk) if(pub_d0)pub_buffer<=st_q;
        assign o_d1=pub_d1; assign o_act=pub_active; assign o_wn=word_next; assign o_slot=slot1; assign o_tag=tag1;
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if(!rst_n)pub_v<=0;
        else begin
            pub_v<=o_d1 || o_act;
            if(o_d1)begin
                pub_data<=pub_buffer[((MUT==3)?32:0)+:32];pub_word<=0;pub_out_slot<=o_slot;pub_tag<=o_tag;
            end else if(o_act)begin
                pub_data<=pub_buffer[32*(o_wn ^ ((MUT==3)?4'd1:4'd0))+:32];pub_word<=o_wn;
            end
        end
    assign fault = m_fault | pub_fault | fold_fault;
endmodule
`default_nettype wire
