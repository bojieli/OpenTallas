`timescale 1ns/1ps
`default_nettype none
// HBM-KITS-C/VMGLUE 2026-10-18: physical successors of the VM hub-glue logic for the hardened glue tiles
// (hfd_hgi_vms_glue_{sw,e,nw}_t, gen_vms_glue_tiles.py).
// g3 (HOURLY-HBM/HH-3 10-19, AD-HBM-VMSGLUE "STRUCTURAL FIX = g3"): the g2 --cts gates failed setup structurally
// (E WNS -1979 ps, ~25k endpoints): single-cycle broadcast / gather across the 648 x 1555 um lane-banded tile.  g3
// pipelines exactly those edges; every change is a whole-edge shift the contract reference states
// (hfd_hgi_vms_glue_tiles_ref.sv, built from the UNCHANGED historical children):
//   ot_vms_rstop_lt  every input except xq_done lands on a plain stage A; stage B = the historical stop registers, with
//                    the tx control (enable / source) and the header decode (own / kind) replicated per lane band and
//                    every flit / eject bit computed in its band (ring transit +1, eject +1, tx control 1 edge earlier,
//                    mirror egress / hub injection / replay return / WACK +1); rce lane-OR = registered 2-level tree
//                    (band pairs -> centre): rce +1 more.  == historical stop with D1 on its inputs and D1 on rce.
//   ot_vms_rcl_lt    replay select replicated per 36-b slice of the rce mux (no edge change).
//   ot_vms_hub_lt    request scatter registered per bank face group (E 0-3 / N 4,5 / S 6,7): pq +1; bank responses
//                    land plain, the per-group hit decode + AND-OR + popcount + checks are registered beside the face,
//                    final OR / bookkeeping next edge: pr -> cr +1; response_enable / response_seq +1 (slot reuse
//                    after a response +1).  == historical hub with D1 on pr / response_enable / response_seq, D1 on pq.
//   hfd_vms_glue_core_lt  7 reset regions (hub, CW, CCW, replay + status, hub face groups E / N / S).
// g4 (HBM-SAFE-VMGLUE 10-19, owner SAFE-DESIGN checklist): the g3 --cts gates sat > 6 h in GRT repair; their real TT
// setup was -0.94..-1.11 ns, all LONG WIRE (hub / replay anchored at corner control pins, 1.1-2.6 mm single-cycle paths;
// placed reach census: 21-33k reg->reg paths > 405 um).  g4 = reach stages, registered one-hot schedule selects, no
// runtime arbitration (a schedule collision stays a status fault):
//   ot_vms_rstop_lt  second landing (stop inputs +2 vs historical): header band copy + per-ring-face-half relay copies of
//                    the one-hot tx select / header decode / injection + replay payloads; per-band valid relays to the
//                    header band; every band select a kept copy per 35-b slice; cco built in band 0; rce 3-level tree
//                    (pairs -> halves -> header band, +1 vs g3); commit delay line = ring buffer.
//   ot_vms_rcl_lt    one-hot registered replay select (sa / sb) per 36-b slice.
//   ot_vms_hub_lt    bank request = AND-OR of client requests under a registered one-hot select decoded a stage ahead
//                    from bank_enable / bank_client (qualified: valid, local, bank match), kept per 36-b slice; slot
//                    clears as kept per-(client, slot, 32-b) registers.
//   hfd_vms_glue_core_lt  hub island <-> ring-stop relays (pi, ri, cco, rce, faults -> status: +1 each), 11 reset
//                    regions; the tile ports carry pin flop + relays (gen_vms_glue_tiles.py DB / DD / DC).
//   Contract: hfd_vms_glue_core_g4_ref (historical children + plain delays), lockstep bench vms_glue_tile_equiv.py.
// g2 notes (still true): only valid / control state is reset; payload registers are plain flops; the hub response
// demultiplex is a parallel tag decode + AND-OR + popcount (no 10-deep slot-mux chain).
// Reset-light equivalence: every payload register without a reset is either overwritten on every edge from reset-held
// logic or read only under a reset valid bit; after >= 5 edges of reset the port behaviour equals the fully reset
// reference (tools/hbm_die_v16/vms_glue_tile_equiv.py checks it in lockstep with periodic resets).
// g6 (L2H-PGVM/VMG6 10-19): lane / rce select copies per 24-b slice (g5 35 / 36-b slices: 35-37 loads), the commit
// delay ring addressed by a one-hot pointer (cptr 128 loads) with the commit valid in the ring (no 13-deep valid shift
// chain), reset leaves <= 24 async loads. Same edges as g5.
module ot_vms_rstop_lt #(
    parameter integer PHYSICAL_RING=1,
    parameter integer COMMIT_DELAY=5,
    parameter integer MUT=0,
    parameter [7:0] UPPER=8'b00111100,   // g4: lane bands in the upper half of the ring face (the rest: lower half)
    parameter integer NLS=36             // g6 reset leaves: 0 header band, 1 control, 2 commit pointers,
                                         // 3+4b+r band b slices 3r..3r+2 (+ eg_v on r 0), 35 outstanding
) (
    input wire clk,
    input wire [NLS-1:0] rl,
    input wire [1:0] sid,
    input wire dir,
    input wire tx_enable,
    input wire [2:0] tx_source,
    input wire [2223:0] l_in,
    output wire [2223:0] l_out,
    input wire [289:0] pi,
    input wire [8*276-1:0] eg,
    output wire [8*276-1:0] xq,
    input wire [7:0] xq_done,
    output reg [287:0] rce,
    input wire [265:0] ri,
    output reg [2:0] wko,
    input wire [2:0] wki,
    output wire [263:0] cco,
    output reg ack_o,
    input wire ack_i,
    output reg mirror_busy,
    output reg fault
);
    // ---- stage A: plain landing of every input except xq_done (lane bits in their band, header / controls / pi / ri /
    //      wki / ack in the header band at the middle of the ring face) ----
    reg [2223:0] a_l; reg [289:0] a_pi; reg [2207:0] a_eg; reg [265:0] a_ri;
    reg [2:0] a_wki, a_src; reg a_en, a_dr, a_ack; reg [1:0] a_me;
    always @(posedge clk) begin
        a_l<=l_in; a_pi<=pi; a_eg<=eg; a_ri<=ri; a_wki<=wki; a_src<=tx_source; a_en<=tx_enable;
        a_dr<=dir; a_ack<=ack_i; a_me<=sid;
    end
    // ---- g4 stage M (plain): the second landing.  Header band: a plain copy of the header-band inputs.  Header band ->
    //      lane bands: one relay copy per ring-face half (<= ~390 um from the middle and <= ~390 um from its farthest
    //      band) carrying the REGISTERED ONE-HOT tx select (decoded from the static schedule's tx_enable / tx_source),
    //      the header decode (own / kind) and the hub-injection / replay payloads.  Lane bands -> header band: one relay
    //      per band for the lane / egress valid bits. ----
    reg [14:0] m_h; reg m_hv; reg [289:0] m_pi; reg [265:0] m_ri; reg [2:0] m_wki, m_src; reg m_en, m_dr, m_ack; reg [1:0] m_me;
    always @(posedge clk) begin
        m_h<=a_l[2222:2208]; m_hv<=a_l[2223]; m_pi<=a_pi; m_ri<=a_ri; m_wki<=a_wki; m_src<=a_src; m_en<=a_en;
        m_dr<=a_dr; m_ack<=a_ack; m_me<=a_me;
    end
    wire own_a=a_l[2223] && a_l[2217+int'(a_me)];
    wire [4:0] oh_a;                          // one-hot tx select: source k with tx_enable (5..7 / disabled: none)
    for(genvar k=0;k<5;k=k+1) begin : g_oha
        assign oh_a[k]=a_en && a_src==3'(k);
    end
    wire [277:0] hm_pi [0:1];
    wire [255:0] hm_ri [0:1]; wire [6:0] hm_h7 [0:1];
    for(genvar h=0;h<2;h=h+1) begin : half
        (* keep = "true", dont_touch = "true" *) reg [277:0] pi_m;
        always @(posedge clk) pi_m<=a_pi[277:0];
        assign hm_pi[h]=pi_m;
        if(h==int'(UPPER[0])) begin : g_b0  // band 0 also takes the replay payload and the cco header bits
            (* keep = "true", dont_touch = "true" *) reg [255:0] ri_m;
            (* keep = "true", dont_touch = "true" *) reg [6:0] h7_m;
            always @(posedge clk) begin ri_m<=a_ri[255:0]; h7_m<=a_l[2214:2208]; end
            assign hm_ri[h]=ri_m; assign hm_h7[h]=h7_m;
        end else begin : g_nb0
            assign hm_ri[h]='0; assign hm_h7[h]='0;
        end
    end
    // ---- stage B, header band: the historical stop registers (same reset set) ----
    reg [14:0] h_d; reg h_v;
    reg [288:0] pi_d; reg pi_v;
    reg [264:0] ri_d; reg ri_v;
    reg [7:0] ev;
    reg [2:0] wki_q, source_q;
    reg enable_q, dr, ack_q;
    reg [1:0] me;
    reg [7:0] lanes;
    wire [7:0] lv_m, ev_m;                    // band -> header band valid relays
    always @(posedge clk) begin
        h_d<=m_h; pi_d<=m_pi[288:0]; ri_d<=m_ri[264:0]; lanes<=lv_m;
    end
    always @(posedge clk or negedge rl[0])
        if(!rl[0]) begin h_v<=0;pi_v<=0;ri_v<=0;ev<=0;wki_q<=0;source_q<=0;enable_q<=0;dr<=0;ack_q<=0;me<=0; end
        else begin
            h_v<=m_hv;pi_v<=m_pi[289];ri_v<=m_ri[265];wki_q<=m_wki;source_q<=m_src;enable_q<=m_en;
            dr<=m_dr;ack_q<=m_ack;me<=m_me;ev<=ev_m;
        end
    wire [1:0] kind=h_d[14:13];
    wire own=h_v && h_d[9+int'(me)];
    wire [3:0] rest=h_d[12:9] & ~(4'b1 << me);
    wire transit=h_v && (|rest);
    wire [1:0] rank={me[1],me[1]^me[0]};
    wire [1:0] r1=rank+2'd1, r2=rank+2'd2, r3=rank+2'd3;
    wire [1:0] d1=(PHYSICAL_RING!=0) ? {r1[1],r1[1]^r1[0]} : me+2'd1;
    wire [1:0] d2=(PHYSICAL_RING!=0) ? {r2[1],r2[1]^r2[0]} : me+2'd2;
    wire [1:0] d3=(PHYSICAL_RING!=0) ? {r3[1],r3[1]^r3[0]} : me+2'd3;
    wire [3:0] dest=dr ? (4'b1 << d3) : ((4'b1 << d1)|(4'b1 << d2));
    reg [15:0] fh;                            // flit header [2223:2208]
    always @* begin
        fh='0;
        if(enable_q) case(source_q)
            0: fh={transit,h_d[14:13],rest,h_d[8:0]};
            1: fh={pi_v,2'd0,pi_d[288:285],me,pi_d[284:281],pi_d[280:279],pi_d[278]};
            2: fh={|ev,2'd1,dest,me,7'd0};
            3: fh={ri_v,2'd2,4'b1<<ri_d[264:263],me,ri_d[262:259],ri_d[258:257],ri_d[256]};
            4: fh={wki_q[2],2'd3,4'b1<<wki_q[1:0],me,7'd0};
            default: fh='0;
        endcase
    end
    wire mut_hit=(MUT==1) && fh[15] && fh[14:13]==2'd1;
    // ---- lane bands: second plain landing in the band, then stage B with the band's copies of the one-hot tx select and
    //      the header decode (from its half relay); every flit / eject bit is band-local ----
    wire [7:0] lv;
    wire [7:0] own_kind0;
    wire [275:0] lane_q [0:7];
    for(genvar b=0;b<8;b=b+1) begin : band
        localparam integer H=UPPER[b] ? 1 : 0;
        // g6 r2: the stage-M relay of the one-hot tx select / header decode is a kept copy PER BAND (was per half:
        // 48 slice loads per bit); same edge, placed between the header band and its band like the half copy
        (* keep = "true", dont_touch = "true" *) reg [4:0] oh_m;
        (* keep = "true", dont_touch = "true" *) reg own_m;
        (* keep = "true", dont_touch = "true" *) reg [1:0] kind_m;
        always @(posedge clk) begin oh_m<=oh_a; own_m<=own_a; kind_m<=a_l[2222:2221]; end
        reg [275:0] ln_m; reg [275:0] eg_m;
        (* keep = "true", dont_touch = "true" *) reg lv_r;
        (* keep = "true", dont_touch = "true" *) reg ev_r;
        always @(posedge clk) begin ln_m<=a_l[b*276+:276]; eg_m<=a_eg[b*276+:276]; lv_r<=a_l[b*276+275]; ev_r<=a_eg[b*276+275]; end
        assign lv_m[b]=lv_r; assign ev_m[b]=ev_r;
        reg [275:0] ln;
        reg [274:0] eg_d; reg eg_v;
        (* keep = "true", dont_touch = "true" *) reg [277:0] pi_b;
        always @(posedge clk) begin ln<=ln_m; eg_d<=eg_m[274:0]; pi_b<=hm_pi[H]; end
        always @(posedge clk or negedge rl[3+4*b]) if(!rl[3+4*b]) eg_v<=0; else eg_v<=eg_m[275];
        // REGISTERED ONE-HOT selects per 24-b slice of the lane (kept copies, g6; g4/g5 35-b): flit source 0 transit /
        // 1 hub injection for THIS band (bank match folded in) / 2 mirror egress / 3 replay return (band 0); eject (own &
        // kind 1), rce (own & kind 0), cco (own & kind 2, band 0); the lane valid bit for the rce pair OR
        wire [275:0] m0, m1, m2, m3, mx, mk0, mcc, mlv;
        for(genvar j=0;j<12;j=j+1) begin : sl
            localparam integer LO=j*24, WD=(j==11)?12:24;     // 11 x 24 + 12 = 276
            localparam integer RL=3+4*b+j/3;
            (* keep = "true", dont_touch = "true" *) reg [3:0] sel_q;
            (* keep = "true", dont_touch = "true" *) reg xo_q, k0_q, cc_q;
            (* keep = "true", dont_touch = "true" *) reg lv_q;
            always @(posedge clk or negedge rl[RL])
                if(!rl[RL]) begin sel_q<=0; xo_q<=0; k0_q<=0; cc_q<=0; end
                else begin
                    sel_q<={oh_m[3] && b==0, oh_m[2], oh_m[1] && hm_pi[H][277:275]==3'(b), oh_m[0]};
                    xo_q<=own_m && kind_m==2'd1; k0_q<=own_m && kind_m==2'd0; cc_q<=own_m && kind_m==2'd2;
                end
            always @(posedge clk) lv_q<=ln_m[275];
            assign m0[LO+:WD]={WD{sel_q[0]}}; assign m1[LO+:WD]={WD{sel_q[1]}}; assign m2[LO+:WD]={WD{sel_q[2]}};
            assign m3[LO+:WD]={WD{sel_q[3]}}; assign mx[LO+:WD]={WD{xo_q}}; assign mk0[LO+:WD]={WD{k0_q}};
            assign mcc[LO+:WD]={WD{cc_q}}; assign mlv[LO+:WD]={WD{lv_q}};
        end
        wire [275:0] s1={1'b1,pi_b[274:264],pi_b[255:0],pi_b[263:256]};
        wire [275:0] s2={eg_v,eg_d};
        wire [275:0] s3;
        if(b==0) begin : g_ri
            reg [255:0] ri_b; reg [6:0] h7_b; reg [263:0] cco_b;
            always @(posedge clk) begin ri_b<=hm_ri[H]; h7_b<=hm_h7[H]; end
            assign s3={12'd0,ri_b,8'd0};
            // cco built in band 0 (lane 0 payload + header bits relayed with the header decode)
            always @(posedge clk) cco_b<=mcc[263:0] & {1'b1,h7_b,ln[263:8]};
            assign cco=cco_b;
        end else begin : g_nri
            assign s3='0;
        end
        reg [275:0] fl;
        always @* begin
            fl=(m0&ln)|(m1&s1)|(m2&s2)|(m3&s3);
            if(b==0 && mut_hit) fl[8]=~fl[8];
        end
        reg [275:0] lo, xo;
        always @(posedge clk) begin
            lo<=fl;
            xo<=mx & ln;
        end
        assign l_out[b*276+:276]=lo;
        assign xq[b*276+:276]=xo;
        assign lv[b]=ln[275];
        assign own_kind0[b]=mk0[0];
        assign lane_q[b]=ln & mk0 & mlv;     // rce pair term: the lane while own & kind 0 and the lane is valid
    end
    // ---- rce: registered 3-level lane-OR tree (band pairs -> ring-face halves -> header band): +1 edge vs g3 ----
    reg [274:0] pl [0:3]; reg [1:0] pv [0:3]; reg [9:0] ph, ph2;
    always @(posedge clk) begin
        for(integer p=0;p<4;p=p+1) begin
            pl[p]<=lane_q[2*p][274:0] | lane_q[2*p+1][274:0];   // both bands of a pair sit in one half: same decode
            pv[p]<=own_kind0[2*p] ? {lv[2*p+1],lv[2*p]} : 2'd0;
        end
        ph<=(own && kind==2'd0) ? {1'b1,h_d[8:0]} : 10'd0;
        ph2<=ph;
    end
    // rce valid gate as kept copies per 24-b slice (g6; g4/g5 36-b: 36-37 loads)
    (* keep = "true", dont_touch = "true" *) reg [11:0] ph2v;
    always @(posedge clk) ph2v<={12{ph[9]}};
    // half h: OR of its pairs + the highest pair with a valid lane (the historical bank pick: the last valid pair wins)
    reg [274:0] hl_n [0:1]; reg [3:0] hb_n [0:1];   // hb = {any, pair[1:0], lane-in-pair}
    always @* begin
        for(integer h=0;h<2;h=h+1) begin
            hl_n[h]='0; hb_n[h]='0;
            for(integer p=0;p<4;p=p+1) if(int'(UPPER[2*p])==h) begin
                hl_n[h]=hl_n[h]|pl[p];
                if(pv[p]!=0) hb_n[h]={1'b1,2'(p),pv[p][1]};
            end
        end
    end
    reg [274:0] hl [0:1]; reg [3:0] hb [0:1];
    always @(posedge clk) begin hl[0]<=hl_n[0]; hl[1]<=hl_n[1]; hb[0]<=hb_n[0]; hb[1]<=hb_n[1]; end
    wire pick1=hb[1][3] && (!hb[0][3] || hb[1][2:1]>hb[0][2:1]);
    wire [2:0] bnk=pick1 ? hb[1][2:0] : (hb[0][3] ? hb[0][2:0] : 3'd0);
    wire [274:0] lor=hl[0]|hl[1];
    wire [287:0] rce_n={ph2,bnk,lor[274:264],lor[7:0],lor[263:8]};
    always @(posedge clk) for(integer j=0;j<12;j=j+1) rce[j*24+:24]<=ph2v[j] ? rce_n[j*24+:24] : 24'd0;
    reg [15:0] lo_h;
    assign l_out[2223:2208]=lo_h;
    always @(posedge clk) lo_h<=fh;
    // ---- control: commit / WACK / mirror accounting / faults (the historical logic on the header band) ----
    reg [15:0] outstanding;
    // g4: the commit mask / source delay line is a COMMIT_DELAY-slot ring buffer: the slot under the pointer was written
    // COMMIT_DELAY - 1 edges ago (= the historical shift chain's last stage); no flop -> flop hold chain.
    // g6: one-hot pointer (kept, rotates; reset slot 0) and the commit valid stored in the ring (reset 0: = the g5 valid
    // shift chain's reset), so the read is an AND-OR and no pointer bit fans out to the 13 x 11 slot bits.
    // g6 r2: two identical kept rings, cp (writes) and cq_r (reads): one ring measured 34 loads per bit
    (* keep = "true", dont_touch = "true" *) reg [COMMIT_DELAY-1:0] cp, cq_r;
    always @(posedge clk or negedge rl[2])
        if(!rl[2]) begin cp<={{(COMMIT_DELAY-1){1'b0}},1'b1}; cq_r<={{(COMMIT_DELAY-1){1'b0}},1'b1}; end
        else begin cp<={cp[COMMIT_DELAY-2:0],cp[COMMIT_DELAY-1]}; cq_r<={cq_r[COMMIT_DELAY-2:0],cq_r[COMMIT_DELAY-1]}; end
    reg [9:0] cring [0:COMMIT_DELAY-1];
    reg [COMMIT_DELAY-1:0] cvr;
    always @(posedge clk) for(integer k=0;k<COMMIT_DELAY;k=k+1) if(cp[k]) cring[k]<={lanes,h_d[8:7]};
    always @(posedge clk or negedge rl[1]) if(!rl[1]) cvr<='0; else for(integer k=0;k<COMMIT_DELAY;k=k+1) if(cp[k]) cvr[k]<=own && kind==1;
    reg [9:0] cr_rd; reg cv_rd;
    always @* begin
        cr_rd='0; cv_rd=1'b0;
        for(integer k=0;k<COMMIT_DELAY;k=k+1) if(cq_r[k]) begin cr_rd=cr_rd|cring[k]; cv_rd=cv_rd|cvr[k]; end
    end
    wire [7:0] commit_mask_o=cr_rd[9:2]; wire [1:0] commit_src_o=cr_rd[1:0];
    always @(posedge clk or negedge rl[35]) if(!rl[35]) outstanding<=0;
        else outstanding<=outstanding + ((fh[15] && source_q==2)?(dr?16'd1:16'd2):16'd0) - (ack_q?16'd1:16'd0);
    always @(posedge clk or negedge rl[1]) begin
        if(!rl[1]) begin
            ack_o<=0;wko<='0;mirror_busy<=0;fault<=0;
        end else begin
            ack_o<=own && kind==3;
            if(own && kind==0 && $countones(lanes)!=1) fault<=1;
            if((transit && (!enable_q || source_q!=0)) ||
               (pi_v && (!enable_q || source_q!=1)) ||
               ((|ev) && (!enable_q || source_q!=2)) ||
               (ri_v && (!enable_q || source_q!=3)) ||
               (wki_q[2] && (!enable_q || source_q!=4)) ||
               (enable_q && source_q>4) ||
               (h_v && h_d[12:9]==0)) fault<=1;
            wko<=0;
            if(cv_rd) begin
                if((xq_done & commit_mask_o) != commit_mask_o) fault<=1;
                else wko<={1'b1,commit_src_o};
            end
            mirror_busy<=outstanding!=0;
            if(ack_q && outstanding==0) fault<=1;
        end
    end
endmodule

// g6: replay select copies per 24-b slice (g4/g5 36-b: 36-39 loads); reset leaves rl[0] control, rl[1] / rl[2] selects
module ot_vms_rcl_lt #(parameter integer MUT=0) (
    input wire clk,
    input wire [2:0] rl,
    input wire [1:0] sid,
    input wire rx_enable,rx_source,
    input wire [287:0] rce0,rce1,
    output wire [337:0] hq,
    input wire [273:0] hr,
    output wire [265:0] ri0,ri1,
    output reg fault
);
    reg [286:0] a_d,b_d; reg a_v,b_v;
    reg [272:0] r_d; reg r_v;
    wire [287:0] a={a_v,a_d}, b={b_v,b_d};
    wire [273:0] response={r_v,r_d};
    reg [1:0] me;
    reg select_q,enable_q;
    reg [336:0] hq_d; reg hq_v;
    reg [264:0] ri0_d,ri1_d; reg ri0_v,ri1_v;
    assign hq={hq_v,hq_d}; assign ri0={ri0_v,ri0_d}; assign ri1={ri1_v,ri1_d};
    // g3: the replay select is replicated per 36-b slice of the 288-b rce mux (one copy beside each slice)
    wire [287:0] e;
    // g4: registered one-hot replay select (static schedule replay_source), replicated per 36-b slice: AND-OR, no mux
    for(genvar i=0;i<12;i=i+1) begin : sel
        (* keep = "true", dont_touch = "true" *) reg sa_q, sb_q;
        always @(posedge clk or negedge rl[1+i/6]) if(!rl[1+i/6]) begin sa_q<=1; sb_q<=0; end else begin sa_q<=!rx_source; sb_q<=rx_source; end
        assign e[i*24+:24]=({24{sa_q}}&a[i*24+:24])|({24{sb_q}}&b[i*24+:24]);
    end
    wire [14:0] sec={e[274]?2'b00:me,e[273:264],e[277:275]};
    wire [31:0] addr={11'b0,e[274],sec,5'b0};
    wire [15:0] tag={6'b0,~select_q,e[286:285],e[284:281],e[280:279],e[278]};
    wire return_port=response[266] ^ (MUT==1);
    reg [31:0] mask;
    always @* for(integer k=0;k<8;k=k+1) mask[k*4+:4]={4{e[256+k]}};
    wire [264:0] rpay={response[265:264],response[263:260],response[259:258],response[256],response[255:0]};
    always @(posedge clk) begin
        a_d<=rce0[286:0]; b_d<=rce1[286:0]; r_d<=hr[272:0];
        hq_d<={e[278],addr,e[255:0],mask,tag};
        ri0_d<=rpay; ri1_d<=rpay;
    end
    always @(posedge clk or negedge rl[0])
        if(!rl[0]) begin
            a_v<=0;b_v<=0;r_v<=0;me<=0;select_q<=0;enable_q<=0;
            hq_v<=0;ri0_v<=0;ri1_v<=0;fault<=0;
        end else begin
            a_v<=rce0[287];b_v<=rce1[287];r_v<=hr[273];me<=sid;
            select_q<=rx_source;enable_q<=rx_enable;
            hq_v<=enable_q && e[287];
            ri0_v<=response[273] && !return_port;
            ri1_v<=response[273] && return_port;
            if((a[287] && (!enable_q || select_q)) ||
               (b[287] && (!enable_q || !select_q))) fault<=1;
            if(response[273] && response[272:267]!=0) fault<=1;
        end
endmodule


// ot_vms_hub_static with the response demultiplex as parallel logic (same function, same edges, same reset set).
// g6 (L2H-PGVM/VMG6 10-19, Codex g5 census ea05ef46a: SW/E/NW 971/742/743 mapped roots > 32): every broadcast of the g5
// hub is now a KEPT per-slice copy registered on the SAME edge as the register it replaces (same reset class), so every
// edge, priority and fault of g5 is unchanged:
//   * cw / ccw injection: cs / ccs (840 / 575 / 563 loads) no longer select the 290-b payload; a QUALIFIED one-hot per
//     (direction, client, 24-b slice) is registered from the inputs on the cs / ce edge (cw_enable & client == c & cq valid
//     & needed, me static); cs / ccs only feed the fault checks.
//   * cr: re (280) gates the 274-b response through kept copies per (client, 23-b slice); the slot tag / write flag is an
//     AND-OR under a kept one-hot of rseq per (client, slot) (rseq 108).
//   * writes (260): folded into the registered one-hot response slot select (rsel <= re_a & rseq_a == k & !writes_next).
//   * ring returns: the hit decode of the two ring sources is registered per (client-slot, 32-b slice) from cco on the rr0
//     edge (plain: its only consumers are gated by reset-class rsel / store-enable copies), no 256-b combinational fan-out.
//   * store enable (arr != 0, 266-load OR trees): registered per (client-slot, 32-b slice) on the a_q / rr0 edge from the
//     group pre-sums a_n and the cco decode (exact 3-bit wrap preserved), reset class of a_q / rvalid.
//   * group hit copies hs1 per 16-b slice (was 32: 37-38 loads); bank request selects per 24-b slice (was 36).
//   * reset: a leaf vector rl (<= 24 async loads per leaf) from the core forest replaces rst_n / rst_f (same release edge).
// Storage (checklist 5, decision): the slot store stays flop registers per client (1,024 b per client: <= the ~2 kb rule;
// SW = 3 clients): it is written by up to 10 sources on one edge (8 banks + 2 ring returns, static schedule, no
// backpressure) and read by a registered one-hot; a 1R1W/1RW SRAM macro cannot take 10 same-edge writes without
// serialising returns in the compiler schedule (an owner-level contract change), and the 1024x256 macro would be 256x
// oversized. Recorded in lanes/L2H-PGVM.md.
module ot_vms_hub_lt #(
    parameter integer NC=4,
    parameter integer PHYSICAL_RING=1,
    parameter integer CW=(NC<1)?1:$clog2(NC+1),
    parameter integer MUT=0,            // bench only: 4 = pq from the hub centre without the face-group edge, 7 = g6 br
    parameter integer NLH=3+14*(NC+1)   // reset leaves (layout: see L_* below)
)(
    input wire clk,
    input wire [NLH-1:0] rl,
    input wire [1:0] sid,
    input wire [(NC+1)*338-1:0] cq,
    input wire [(NC+1)*2-1:0] client_seq,
    input wire [7:0] bank_enable,
    input wire [8*CW-1:0] bank_client,
    input wire cw_enable,
    input wire [CW-1:0] cw_client,
    input wire ccw_enable,
    input wire [CW-1:0] ccw_client,
    output wire [(NC+1)*274-1:0] cr,
    output wire [8*285-1:0] pq,
    input wire [8*266-1:0] pr,
    output wire [289:0] cwi, cci,
    input wire [263:0] cco0, cco1,
    input wire [NC:0] response_enable,
    input wire [(NC+1)*2-1:0] response_seq,
    output reg [2:0] status
);
    localparam integer N=NC+1;
    localparam integer NS=10;          // response sources: 8 banks + CW / CCW ring returns
    // reset leaves: 0 landing/valid regs, 1 output valids + status, per client c (base 2+11c): +0/+1 slot state (slots
    // 0-1 / 2-3), +2/+3 rsel, +4/+5 clr, +6/+7 store enable, +8 re copies, +9 cw one-hot, +10 ccw one-hot; per face
    // group g and client c: 2+11N+3c+g (h/w1/w0/a of the client's 4 slots, + bad on c 0); bank request valids 2+14N.
    localparam integer L_A=0, L_B=1, L_PV=2+14*N;
    function automatic integer lc(input integer c, input integer o); lc=2+11*c+o; endfunction
    function automatic integer lg(input integer g, input integer c); lg=2+11*N+3*c+g; endfunction
    reg [N*338-1:0] qr;
    reg [N*2-1:0] sq;
    reg [7:0] be;
    reg [8*CW-1:0] bc;
    reg ce, cce;
    reg [CW-1:0] cs, ccs;
    reg [1:0] me;
    // g7 (L2H-PGVM-G7 10-19): no hub landing br on the bank returns -- the tile pr chain's last relay feeds the group
    // stage 1 directly (br was a pure in-place flop -> flop hop: 2,128 hold-critical endpoints); bank returns -1 edge
    // MUT 7 (bench only): the g6 landing kept (contract break)
    wire [8*266-1:0] br;
    if(MUT==7) begin : g_br6
        reg [8*266-1:0] br_q; always @(posedge clk) br_q<=pr; assign br=br_q;
    end else begin : g_br7
        assign br=pr;
    end
    reg [263:0] rr0,rr1;
    reg [N-1:0] re;
    reg [N*2-1:0] rseq;
    reg [255:0] response_data[0:N-1][0:3];
    reg [15:0] tags[0:N-1][0:3];
    reg active[0:N-1][0:3], writes[0:N-1][0:3];
    reg [2:0] expected[0:N-1][0:3], seen[0:N-1][0:3];
    reg [N*274-1:0] cr_next;
    reg [8*285-1:0] pq_next;
    reg [2:0] fault;
    reg [N*274-1:0] cr_payload;
    wire [8*285-1:0] pq_payload;   // g3: built per face group (req_grp)
    reg [288:0] cw_payload,ccw_payload;
    reg [N-1:0] cr_valid;
    wire [7:0] pq_valid;
    reg cw_valid,ccw_valid;
    wire [289:0] cw_next, ccw_next;    // g6: AND-OR of the qualified one-hot slice copies
    for(genvar g=0;g<N;g=g+1) begin : client_output
        assign cr[g*274+:274]={cr_valid[g],cr_payload[g*274+:273]};
    end
    for(genvar g=0;g<8;g=g+1) begin : bank_output
        assign pq[g*285+:285]={pq_valid[g],pq_payload[g*285+:284]};
    end
    assign cwi={cw_valid,cw_payload};
    assign cci={ccw_valid,ccw_payload};
    always @(posedge clk) begin
        cr_payload<=cr_next;
        cw_payload<=cw_next[288:0]; ccw_payload<=ccw_next[288:0];
    end
    reg [N-1:0] issued_local,issued_cw,issued_ccw;
    wire [1:0] rank={me[1],me[1]^me[0]};
    wire [1:0] nr=rank+2'd1, orank=rank+2'd2, pvr=rank+2'd3;
    wire [1:0] next_sid=(PHYSICAL_RING!=0)?{nr[1],nr[1]^nr[0]}:me+2'd1;
    wire [1:0] opposite_sid=(PHYSICAL_RING!=0)?{orank[1],orank[1]^orank[0]}:me+2'd2;
    wire [1:0] previous_sid=(PHYSICAL_RING!=0)?{pvr[1],pvr[1]^pvr[0]}:me+2'd3;
    wire [3:0] cw_dest=(4'b1<<next_sid)|(4'b1<<opposite_sid);
    wire [3:0] ccw_dest=4'b1<<previous_sid;
    function automatic [2:0] bank_of(input [337:0] q);
        bank_of=q[311:309];
    endfunction
    function automatic [7:0] wordmask(input [337:0] q);
        for(integer w=0;w<8;w=w+1) wordmask[w]=&q[16+4*w+:4];
    endfunction
    function automatic local_needed(input [337:0] q,input integer c);
        local_needed=(c==NC)||q[324]||(q[323:322]==me);
    endfunction
    function automatic cw_needed(input [337:0] q,input integer c);
        cw_needed=(c!=NC)&&((q[324]&&q[336])||(!q[324]&&((4'b1<<q[323:322])&cw_dest)!=0));
    endfunction
    function automatic ccw_needed(input [337:0] q,input integer c);
        ccw_needed=(c!=NC)&&((q[324]&&q[336])||(!q[324]&&q[323:322]==previous_sid));
    endfunction
    // g3: bank responses and the response enables land on a plain stage first (pr -> cr +1, re / rseq +1)
    reg [N-1:0] re_a; reg [N*2-1:0] rseq_a;
    always @(posedge clk) begin
        qr<=cq; sq<=client_seq; bc<=bank_client; cs<=cw_client;
        ccs<=ccw_client; me<=sid; rr0<=cco0; rr1<=cco1; re_a<=response_enable; rseq_a<=response_seq; rseq<=rseq_a;
    end
    reg [N-1:0] qvalid;
    reg [7:0] bvalid;   // g3: = br valid bits (plain landing; the face-group partial registers carry the reset)
    reg rvalid0,rvalid1;
    always @(posedge clk or negedge rl[L_A]) begin
        if(!rl[L_A]) begin
            qvalid<='0; rvalid0<=0; rvalid1<=0;
            be<=0; ce<=0; cce<=0; re<=0;
        end else begin
            for(integer c=0;c<N;c=c+1) qvalid[c]<=cq[c*338+337];
            rvalid0<=cco0[263]; rvalid1<=cco1[263];
            be<=bank_enable; ce<=cw_enable; cce<=ccw_enable; re<=re_a;
        end
    end
    // ---- g6: qualified one-hot ring-injection selects per (direction, client, 24-b slice), registered on the ce / cs edge
    localparam integer NIS=13;          // 290 = 12 x 24 + 2
    for(genvar d=0;d<2;d=d+1) begin : inj
        wire [NIS*N-1:0] oh;
        for(genvar c=0;c<N;c=c+1) begin : g_c
            wire en_c=(d==0) ? (cw_enable && int'(cw_client)==c && cq[c*338+337] && cw_needed(cq[c*338+:338],c))
                             : (ccw_enable && int'(ccw_client)==c && cq[c*338+337] && ccw_needed(cq[c*338+:338],c));
            (* keep = "true", dont_touch = "true" *) reg [NIS-1:0] ohc;
            always @(posedge clk or negedge rl[lc(c,9+d)]) if(!rl[lc(c,9+d)]) ohc<='0; else ohc<={NIS{en_c}};
            assign oh[c*NIS+:NIS]=ohc;
        end
        reg [289:0] nx;
        always @* begin
            nx='0;
            for(integer c=0;c<N;c=c+1) begin : orc
                reg [337:0] q; reg [3:0] mask; reg [289:0] f;
                q=qr[c*338+:338];
                mask=q[324]?((d==0)?cw_dest:ccw_dest):(4'b1<<q[323:322]);
                f={1'b1,mask,4'(c),sq[c*2+:2],q[336],bank_of(q),q[324],q[321:312],wordmask(q),q[303:48]};
                for(integer s=0;s<NIS;s=s+1) if(oh[c*NIS+s])
                    for(integer i=s*24;i<s*24+24 && i<290;i=i+1) nx[i]=nx[i]|f[i];
            end
        end
        if(d==0) begin : g_cw assign cw_next=nx; end else begin : g_ccw assign ccw_next=nx; end
    end
    // ---- response demultiplex, g3: per bank face group the hit decode + AND-OR + popcount + source checks are
    //      registered beside the face (from the plain landing br), the ring returns (cco) decode at the hub; the
    //      final OR / sum / slot checks run on the next edge.  Source s = {valid, client4, seq2, we, data256}.
    always @* for(integer b=0;b<8;b=b+1) bvalid[b]=br[b*266+265];
    wire [NS*264-1:0] rpf;
    for(genvar s=0;s<8;s=s+1) begin : rsp_bank
        assign rpf[s*264+:264]={bvalid[s],br[s*266+260+:4],br[s*266+256+:2],br[s*266+264],br[s*266+:256]};
    end
    assign rpf[8*264+:264]={rvalid0,rr0[262:0]};
    assign rpf[9*264+:264]={rvalid1,rr1[262:0]};
    // hit[(s*N+c)*4+k]: source s returns client c slot k (a tag client >= N hits nothing: it faults)
    wire [NS*N*4-1:0] hit;
    for(genvar s=0;s<NS;s=s+1) begin : rsp_hit
        for(genvar c=0;c<N;c=c+1) begin : rsp_hit_c
            for(genvar k=0;k<4;k=k+1) begin : rsp_hit_k
                assign hit[(s*N+c)*4+k]=rpf[s*264+263] && rpf[s*264+259+:4]==4'(c) && rpf[s*264+257+:2]==2'(k);
            end
        end
    end
    wire [NS-1:0] src_bad;      // a valid return for a client >= N, or bank tag bits 3:2 non-zero
    for(genvar s=0;s<NS;s=s+1) begin : rsp_bad
        if(s<8) begin : g_b
            assign src_bad[s]=(rpf[s*264+263] && int'(rpf[s*264+259+:4])>=N) || (bvalid[s] && br[s*266+258+:2]!=0);
        end else begin : g_r
            assign src_bad[s]=rpf[s*264+263] && int'(rpf[s*264+259+:4])>=N;
        end
    end
    // face group g: banks [GL(g) .. GH(g)]
    wire [3*N*4-1:0] g_h, g_w1, g_w0;
    wire [3*N*4*3-1:0] g_a, g_an;
    wire [3*N*4*256-1:0] g_d;
    wire [2:0] g_bad;
    for(genvar g=0;g<3;g=g+1) begin : rsp_grp
        localparam integer GL=(g==0)?0:(g==1)?4:6, GH=(g==0)?3:(g==1)?5:7, GS=GH-GL+1;
        reg [N*4-1:0] h_q, w1_q, w0_q; reg [N*4*3-1:0] a_q; reg bad_q;
        reg [N*4*256-1:0] d_q;
        reg [N*4-1:0] h_n, w1_n, w0_n; reg [N*4*3-1:0] a_n; reg [N*4*256-1:0] d_n; reg bad_n;
        // g5: stage 1 registers the group's source data / write flags and the hit decode as a registered one-hot per
        // (source, client-slot, slice); g6: 16-b slices (32-b slices measured 37-38 loads).
        reg [GS*256-1:0] d1; reg [GS-1:0] we1; reg [GS*N*4-1:0] h1; reg bad1;
        (* keep = "true", dont_touch = "true" *) reg [GS*N*4*16-1:0] hs1;
        always @(posedge clk) begin
            bad1<=|src_bad[GH:GL];
            for(integer s=GL;s<=GH;s=s+1) begin
                d1[(s-GL)*256+:256]<=rpf[s*264+:256]; we1[s-GL]<=rpf[s*264+256];
                for(integer ck=0;ck<N*4;ck=ck+1) begin
                    h1[(s-GL)*N*4+ck]<=hit[s*N*4+ck];
                    for(integer j=0;j<16;j=j+1) hs1[((s-GL)*N*4+ck)*16+j]<=hit[s*N*4+ck];
                end
            end
        end
        always @* begin
            h_n='0; w1_n='0; w0_n='0; a_n='0; d_n='0; bad_n=bad1;
            for(integer s=0;s<GS;s=s+1) begin
                for(integer ck=0;ck<N*4;ck=ck+1) begin
                    if(h1[s*N*4+ck]) begin
                        h_n[ck]=1'b1;
                        if(we1[s]) w1_n[ck]=1'b1; else w0_n[ck]=1'b1;
                        a_n[ck*3+:3]=a_n[ck*3+:3]+3'd1;
                    end
                    for(integer j=0;j<16;j=j+1) if(hs1[(s*N*4+ck)*16+j])
                        d_n[ck*256+j*16+:16]=d_n[ck*256+j*16+:16]|d1[s*256+j*16+:16];
                end
            end
        end
        always @(posedge clk) d_q<=d_n;
        for(genvar c=0;c<N;c=c+1) begin : g_rc
            always @(posedge clk or negedge rl[lg(g,c)])
                if(!rl[lg(g,c)]) begin h_q[c*4+:4]<='0; w1_q[c*4+:4]<='0; w0_q[c*4+:4]<='0; a_q[c*12+:12]<='0; end
                else begin h_q[c*4+:4]<=h_n[c*4+:4]; w1_q[c*4+:4]<=w1_n[c*4+:4]; w0_q[c*4+:4]<=w0_n[c*4+:4]; a_q[c*12+:12]<=a_n[c*12+:12]; end
        end
        always @(posedge clk or negedge rl[lg(g,0)]) if(!rl[lg(g,0)]) bad_q<=0; else bad_q<=bad_n;
        assign g_h[g*N*4+:N*4]=h_q; assign g_w1[g*N*4+:N*4]=w1_q; assign g_w0[g*N*4+:N*4]=w0_q;
        assign g_a[g*N*4*3+:N*4*3]=a_q; assign g_an[g*N*4*3+:N*4*3]=a_n;
        assign g_d[g*N*4*256+:N*4*256]=d_q; assign g_bad[g]=bad_q;
    end
    wire [N*4*256-1:0] ret_f;   // returned_data[c][k]
    wire [N*4*3-1:0] arr_f;     // arrivals[c][k] (3-bit wrap, as the historical counter)
    wire [N*4-1:0] hit_any, hit_w1, hit_w0;
    wire [N*4*8-1:0] sen;       // g6: store enables per (client-slot, 32-b slice)
    // g6: per (client-slot, 32-b slice) registered ring hit copies (rr0 / rr1 edge, from cco) and store enables (a_q /
    // rvalid edge: arr != 0 from the group pre-sums and the same cco decode)
    for(genvar c=0;c<N;c=c+1) begin : rsp_cpy
        for(genvar k=0;k<4;k=k+1) begin : g_k
            localparam integer CK=c*4+k;
            wire c8=cco0[263] && cco0[262:259]==4'(c) && cco0[258:257]==2'(k);
            wire c9=cco1[263] && cco1[262:259]==4'(c) && cco1[258:257]==2'(k);
            wire [2:0] an=(g_an[CK*3+:3]+g_an[(N*4+CK)*3+:3])+(g_an[(2*N*4+CK)*3+:3]+(3'(c8)+3'(c9)));
            (* keep = "true", dont_touch = "true" *) reg [7:0] hs8, hs9;
            (* keep = "true", dont_touch = "true" *) reg [7:0] en;
            always @(posedge clk) begin hs8<={8{c8}}; hs9<={8{c9}}; end
            always @(posedge clk or negedge rl[lc(c,6+k/2)]) if(!rl[lc(c,6+k/2)]) en<='0; else en<={8{an!=3'd0}};
            assign sen[CK*8+:8]=en;
            for(genvar j=0;j<8;j=j+1) begin : g_j
                wire [31:0] rd=(g_d[CK*256+j*32+:32]|g_d[(N*4+CK)*256+j*32+:32])|(g_d[(2*N*4+CK)*256+j*32+:32]|
                    (({32{hs8[j]}}&rr0[j*32+:32])|({32{hs9[j]}}&rr1[j*32+:32])));
                assign ret_f[CK*256+j*32+:32]=rd;
            end
        end
    end
    for(genvar ck=0;ck<N*4;ck=ck+1) begin : rsp_fin
        wire h8=hit[(8*N*4)+ck], h9=hit[(9*N*4)+ck];
        assign arr_f[ck*3+:3]=(g_a[ck*3+:3]+g_a[(N*4+ck)*3+:3])+(g_a[(2*N*4+ck)*3+:3]+(3'(h8)+3'(h9)));
        assign hit_any[ck]=g_h[ck]|g_h[N*4+ck]|g_h[2*N*4+ck]|h8|h9;
        assign hit_w1[ck]=g_w1[ck]|g_w1[N*4+ck]|g_w1[2*N*4+ck]|(h8&rpf[8*264+256])|(h9&rpf[9*264+256]);
        assign hit_w0[ck]=g_w0[ck]|g_w0[N*4+ck]|g_w0[2*N*4+ck]|(h8&!rpf[8*264+256])|(h9&!rpf[9*264+256]);
    end
    // ---- request scatter, g3: per bank face group a registered copy of the hub request state; the bank request
    //      is built beside the face (+1 edge on pq vs the historical hub)
    for(genvar g=0;g<3;g=g+1) begin : req_grp
        localparam integer GL=(g==0)?0:(g==1)?4:6, GH=(g==0)?3:(g==1)?5:7;
        // g5: the one-hot select is registered AT THE HUB (sel_h, one per bank and client), then copied per slice one
        // edge later; the request copies get the matching second stage (qr_g1 -> qr_g).  pq +1 edge (contract: pq_d2).
        (* keep = "true", dont_touch = "true" *) reg [N*338-1:0] qr_g1, qr_g;
        (* keep = "true", dont_touch = "true" *) reg [N*2-1:0] sq_g1, sq_g;
        always @(posedge clk) begin qr_g1<=qr; sq_g1<=sq; qr_g<=qr_g1; sq_g<=sq_g1; end
        for(genvar b=GL;b<=GH;b=b+1) begin : bank
            wire [N-1:0] sel_n;
            for(genvar c=0;c<N;c=c+1) begin : g_seln
                assign sel_n[c]=be[b] && int'(bc[b*CW+:CW])==c && qvalid[c] &&
                                ((c==NC)||qr[c*338+324]||(qr[c*338+322+:2]==me)) && qr[c*338+309+:3]==3'(b);
            end
            (* keep = "true", dont_touch = "true" *) reg [N-1:0] sel_h;   // g5: hub-side registered one-hot
            always @(posedge clk) sel_h<=sel_n;
            wire [284:0] nx;
            // g6: kept copy per 24-b slice of the 285-b request (g5: 36-b slices, 33-36 loads)
            for(genvar j=0;j<12;j=j+1) begin : sl
                localparam integer LO=j*24, WD=(j==11)?21:24;    // 11 x 24 + 21 = 285
                (* keep = "true", dont_touch = "true" *) reg [N-1:0] sel;
                always @(posedge clk) sel<=(MUT==6) ? sel_n : sel_h;   // MUT 6 (bench only): g5 select stage missing
                reg [WD-1:0] nxs;
                always @* begin
                    nxs='0;
                    for(integer c=0;c<N;c=c+1) if(sel[c]) begin : orc
                        reg [284:0] f;
                        f={1'b1,qr_g[c*338+336],qr_g[c*338+324],qr_g[c*338+312+:10],qr_g[c*338+48+:256],
                           wordmask(qr_g[c*338+:338]),4'(c),2'b00,sq_g[c*2+:2]};
                        nxs=nxs|f[LO+:WD];
                    end
                end
                assign nx[LO+:WD]=nxs;
            end
            reg [283:0] pp; reg pv;
            wire [284:0] nq=(MUT==4) ? pq_next[b*285+:285] : nx;
            always @(posedge clk) pp<=nq[283:0];
            always @(posedge clk or negedge rl[L_PV]) if(!rl[L_PV]) pv<=1'b0; else pv<=nq[284];
            assign pq_payload[b*285+:285]={1'b0,pp}; assign pq_valid[b]=pv;
        end
    end
    // g4: response slot select = REGISTERED ONE-HOT of the static schedule's response_seq (decoded a stage ahead from the
    // g3 landing re_a / rseq_a), kept per (client, slot, 32-b slice); g6: the write flag of the slot on the response edge
    // (writes' next state) is folded in, so writes no longer gates the 256-b data
    // g6 r2: admission one-hot (qvalid & sq == k) as kept registers per (client, slot) on the qvalid edge / reset class:
    // adm_t for the tag write, adm_s for the slot state and wr_n (the shared decode measured 36-39 loads)
    (* keep = "true", dont_touch = "true" *) reg [N*4-1:0] adm_t, adm_s;
    for(genvar c=0;c<N;c=c+1) begin : g_adm
        always @(posedge clk or negedge rl[lc(c,8)])
            if(!rl[lc(c,8)]) begin adm_t[c*4+:4]<='0; adm_s[c*4+:4]<='0; end
            else for(integer k=0;k<4;k=k+1) begin
                adm_t[c*4+k]<=cq[c*338+337] && client_seq[c*2+:2]==2'(k);
                adm_s[c*4+k]<=cq[c*338+337] && client_seq[c*2+:2]==2'(k);
            end
    end
    reg wr_n [0:N-1][0:3];
    always @* for(integer c=0;c<N;c=c+1) for(integer k=0;k<4;k=k+1)
        wr_n[c][k]=adm_s[c*4+k] ? qr[c*338+336] : writes[c][k];
    (* keep = "true", dont_touch = "true" *) reg [N*4*8-1:0] rsel;
    for(genvar c=0;c<N;c=c+1) for(genvar k=0;k<4;k=k+1) begin : g_rsel
        always @(posedge clk or negedge rl[lc(c,2+k/2)])
            if(!rl[lc(c,2+k/2)]) rsel[(c*4+k)*8+:8]<='0;
            else rsel[(c*4+k)*8+:8]<={8{re_a[c] && rseq_a[c*2+:2]==2'(k) && !wr_n[c][k]}};
    end
    reg [N*256-1:0] rdat;
    always @* begin
        rdat='0;
        for(integer c=0;c<N;c=c+1) for(integer k=0;k<4;k=k+1) for(integer j=0;j<8;j=j+1)
            if(rsel[(c*4+k)*8+j])
                rdat[c*256+j*32+:32]=rdat[c*256+j*32+:32]|response_data[c][k][j*32+:32]|ret_f[(c*4+k)*256+j*32+:32];
    end
    // g6: kept one-hot of rseq per (client, slot) (rseq_a edge, plain like rseq): t = tag / write mux, k = checks
    (* keep = "true", dont_touch = "true" *) reg [N*4-1:0] roh_t, roh_k;
    always @(posedge clk) for(integer c=0;c<N;c=c+1) for(integer k=0;k<4;k=k+1) begin
        roh_t[c*4+k]<=rseq_a[c*2+:2]==2'(k); roh_k[c*4+k]<=rseq_a[c*2+:2]==2'(k);
    end
    // g6: kept copies of re per (client, 23-b slice of the 274-b response), same edge / reset class as re
    localparam integer NRS=12;          // 274 = 11 x 23 + 21
    wire [N*NRS-1:0] rec;
    for(genvar c=0;c<N;c=c+1) begin : g_rec
        (* keep = "true", dont_touch = "true" *) reg [NRS-1:0] r;
        always @(posedge clk or negedge rl[lc(c,8)]) if(!rl[lc(c,8)]) r<='0; else r<={NRS{re_a[c]}};
        assign rec[c*NRS+:NRS]=r;
    end
    always @* begin : crn
        cr_next='0;
        for(integer c=0;c<N;c=c+1) begin : crc
            reg [15:0] tg; reg wt; reg [273:0] f;
            tg='0; wt=1'b0;
            for(integer k=0;k<4;k=k+1) if(roh_t[c*4+k]) begin tg=tg|tags[c][k]; wt=wt|writes[c][k]; end
            f={1'b1,tg,wt,rdat[c*256+:256]};
            for(integer s=0;s<NRS;s=s+1) if(rec[c*NRS+s])
                for(integer i=s*23;i<s*23+23 && i<274;i=i+1) cr_next[c*274+i]=f[i];
        end
    end
    always @* begin : route
        integer c,k,b;
        reg [337:0] q;
        reg [7:0] wm;
        fault=0; pq_next=0;
        issued_local=0; issued_cw=0; issued_ccw=0;
        q=0; wm=0; c=0; k=0;
        for(b=0;b<8;b=b+1) if(be[b]) begin
            c=int'(bc[b*CW+:CW]);
            if(c>=N) fault[0]=1;
            else begin
                q=qr[c*338+:338];
                if(!qvalid[c]||!local_needed(q,c)||bank_of(q)!=3'(b)) fault[0]=1;
                else begin
                    pq_next[b*285+:285]={1'b1,q[336],q[324],q[321:312],q[303:48],wordmask(q),4'(c),2'b00,sq[c*2+:2]};
                    if(issued_local[c]) fault[0]=1;
                    issued_local[c]=1;
                end
            end
        end
        for(integer dir=0;dir<2;dir=dir+1) if(dir==0?ce:cce) begin
            c=dir==0?int'(cs):int'(ccs);
            if(c>=N) fault[0]=1;
            else begin
                q=qr[c*338+:338];
                if(!qvalid[c]||!(dir==0?cw_needed(q,c):ccw_needed(q,c))) fault[0]=1;
                else if(dir==0) issued_cw[c]=1;
                else issued_ccw[c]=1;
            end
        end
        for(c=0;c<N;c=c+1) if(qvalid[c]) begin
            q=qr[c*338+:338]; k=int'(sq[c*2+:2]); wm=wordmask(q);
            if(active[c][k]) fault[0]=1;
            if(issued_local[c]!=local_needed(q,c)||issued_cw[c]!=cw_needed(q,c)||issued_ccw[c]!=ccw_needed(q,c)) fault[0]=1;
            if(q[335:325]!=0||q[308:304]!=0||(q[324]&&q[323:322]!=0)||(c==NC&&!q[324]&&q[323:322]!=me)) fault[2]=1;
            for(integer w=0;w<8;w=w+1) if(q[336]&&q[16+4*w+:4]!={4{wm[w]}}) fault[1]=1;
        end
        if((|g_bad)||src_bad[8]||src_bad[9]) fault[0]=1;
        for(c=0;c<N;c=c+1) for(k=0;k<4;k=k+1)
            if((hit_any[c*4+k] && !active[c][k]) || (hit_w1[c*4+k] && !writes[c][k]) || (hit_w0[c*4+k] && writes[c][k])) fault[0]=1;
        for(c=0;c<N;c=c+1) begin
            for(k=0;k<4;k=k+1) if(arr_f[(c*4+k)*3+:3]!=0)
                if({1'b0,seen[c][k]}+{1'b0,arr_f[(c*4+k)*3+:3]}>{1'b0,expected[c][k]}) fault[0]=1;
            if(re[c]) for(k=0;k<4;k=k+1) if(roh_k[c*4+k]) begin
                if(!active[c][k]||{1'b0,seen[c][k]}+{1'b0,arr_f[(c*4+k)*3+:3]}!={1'b0,expected[c][k]}) fault[0]=1;
            end
        end
    end
    always @(posedge clk or negedge rl[L_B]) begin : outv
        if(!rl[L_B]) begin
            cr_valid<=0; cw_valid<=0; ccw_valid<=0; status<=0;
        end else begin
            for(integer c=0;c<N;c=c+1) cr_valid[c]<=cr_next[c*274+273];
            cw_valid<=cw_next[289]; ccw_valid<=ccw_next[289];
            status<=status|fault;
        end
    end
    // slot state per (client, slot pair) on its own reset leaf (same priorities as g5: admission after retirement)
    for(genvar c=0;c<N;c=c+1) for(genvar k=0;k<4;k=k+1) begin : g_slot
        always @(posedge clk or negedge rl[lc(c,k/2)]) begin
            if(!rl[lc(c,k/2)]) begin
                active[c][k]<=0; seen[c][k]<=0; expected[c][k]<=0; writes[c][k]<=0;
            end else begin
                if(arr_f[(c*4+k)*3+:3]!=0) seen[c][k]<=seen[c][k]+arr_f[(c*4+k)*3+:3];
                if(re[c] && roh_k[c*4+k]) active[c][k]<=0;
                if(adm_s[c*4+k]) begin
                    active[c][k]<=1;
                    seen[c][k]<=0;
                    expected[c][k]<=(qr[c*338+324]&&qr[c*338+336]&&c!=NC)?3'd4:3'd1;
                    writes[c][k]<=qr[c*338+336];
                end
            end
        end
    end
    // g4: the slot clear (qvalid & seq == k) as kept per-(client, slot, 32-b slice) registers beside the slot data
    (* keep = "true", dont_touch = "true" *) reg [N*4*8-1:0] clr;
    for(genvar c=0;c<N;c=c+1) for(genvar k=0;k<4;k=k+1) begin : g_clr
        always @(posedge clk or negedge rl[lc(c,4+k/2)])
            if(!rl[lc(c,4+k/2)]) clr[(c*4+k)*8+:8]<='0;
            else clr[(c*4+k)*8+:8]<={8{cq[c*338+337] && client_seq[c*2+:2]==2'(k)}};
    end
    // g6: store enable per 32-b slice (rsp_cpy.en); clear has priority over arrival (as g5)
    always @(posedge clk) for(integer c=0;c<N;c=c+1) begin
        for(integer k=0;k<4;k=k+1) for(integer j=0;j<8;j=j+1) begin
            if(sen[(c*4+k)*8+j])
                response_data[c][k][j*32+:32]<=response_data[c][k][j*32+:32]|ret_f[(c*4+k)*256+j*32+:32];
            if(clr[(c*4+k)*8+j]) response_data[c][k][j*32+:32]<=32'd0;
        end
        for(integer k=0;k<4;k=k+1) if(adm_t[c*4+k]) tags[c][k]<=qr[c*338+:16];
    end
endmodule


// g6 reset forest (L2H-PGVM/VMG6 10-19; g5 census: relay leaves 298 / 204 / 196 / 77 / 63 / 58 / 51 async loads): the tile
// lands rst_n in ONE face flop (rst_l0); ot_vms_rst_forest replicates the second landing stage per group of <= 24 leaves
// (l1[g], plain), runs the 2-stage synchroniser per group (s0[g] / s1[g], async clear from l1[g]) and drives <= 24 kept
// leaves per group (async clear from l1[g], D = s1[g]).  Assertion 2 edges after the port, release 5 edges after the
// port: exactly the g5 timing (rst_l0 -> rst_l1 -> ot_rst_relay SYNC 2 + TREE 1).  Every net <= 26 loads.
module ot_vms_rst_forest #(parameter integer NL=24, parameter integer GL=24) (
    input wire clk,
    input wire rst_l0,
    output wire [NL-1:0] rl
);
    localparam integer NG=(NL+GL-1)/GL;
    for(genvar g=0;g<NG;g=g+1) begin : grp
        (* keep = "true", dont_touch = "true" *) reg l1;
        (* keep = "true", dont_touch = "true" *) reg s0, s1;
        always @(posedge clk) l1<=rst_l0;
        always @(posedge clk or negedge l1) if(!l1) begin s0<=1'b0; s1<=1'b0; end else begin s0<=1'b1; s1<=s0; end
        for(genvar i=g*GL;i<(g+1)*GL && i<NL;i=i+1) begin : lf
            (* keep = "true", dont_touch = "true" *) reg q;
            always @(posedge clk or negedge l1) if(!l1) q<=1'b0; else q<=s1;
            assign rl[i]=q;
        end
    end
endmodule

// ot_vms_slice_static_glue (gen_vms_hoist.py) wiring with the _lt children, ONE tile clock; g6: reset leaves from the
// forest (hub NLH, CW / CCW stop 36 each, replay 3, status 1).
module hfd_vms_glue_core_lt #(
    parameter integer NC=0,
    parameter integer CW=((NC+1)>1)?$clog2(NC+1):1,
    parameter integer COMMIT_DELAY=6,
    parameter integer RMUT=0,
    parameter [7:0] UPPER=8'b00111100     // g4: lane bands in the upper half of the ring face
)(
    input wire clk,
    input wire rst_l0,                    // g6: the tile's face reset landing (one plain flop); the forest is below
    input wire [1:0] sid,
    input wire [((NC>0)?NC:1)*338-1:0] cq,
    output wire [((NC>0)?NC:1)*274-1:0] cr,
    input wire [(NC+1)*2-1:0] client_seq,
    input wire [(NC+1)-1:0] response_enable,
    input wire [(NC+1)*2-1:0] response_seq,
    input wire [7:0] bank_enable,
    input wire [8*CW-1:0] bank_client,
    input wire [1:0] hub_ring_enable,
    input wire [2*CW-1:0] hub_ring_client,
    input wire [2223:0] cw_in,ccw_in,
    output wire [2223:0] cw_out,ccw_out,
    input wire [1:0] ring_tx_enable,
    input wire [5:0] ring_tx_source,
    input wire replay_enable,replay_source,
    input wire [143:0] bank_status,
    output wire [2207:0] bk_xq,bk_xq2,
    input wire [7:0] bk_xq_done,bk_xq2_done,
    input wire [2207:0] bk_eg,
    output wire [8*285-1:0] bk_pq,
    input wire [8*266-1:0] bk_pr,
    output wire [2:0] hub_status,
    output wire [1:0] mirror_busy,
    output wire [18:0] vmstat,
    output wire [2:0] ring_fault
);
    localparam integer NLH=3+14*(NC+1), NLS=36;
    localparam integer OH=0, OC=NLH, OCC=NLH+NLS, OR_=NLH+2*NLS, OS=NLH+2*NLS+3, NL=NLH+2*NLS+4;
    wire [NL-1:0] rl;
    ot_vms_rst_forest #(.NL(NL)) u_rst(.clk(clk),.rst_l0(rst_l0),.rl(rl));
    wire [(NC+1)*338-1:0] hcq;
    wire [(NC+1)*274-1:0] hcr;
    wire [337:0] hq;
    wire [273:0] hr=hcr[NC*274+:274];
    generate if(NC>0)begin:g_local
        assign hcq={hq,cq};assign cr=hcr[NC*274-1:0];
    end else begin:g_no_local
        assign hcq=hq;assign cr='0;
    end endgenerate
    wire [289:0] pi0,pi1;
    wire [263:0] cco0,cco1;
    wire [287:0] rce0,rce1;
    wire [265:0] ri0,ri1;
    wire [2:0] wk01,wk10;
    wire ack01,ack10;
    // g4 reach relays between the hub island and the ring-stop header bands (~400-700 um apart): one plain edge each way
    // (hub -> stop injection pi, replay -> stop return ri, stop -> hub cco, stop -> replay rce) and on the ring faults
    // into the status block; RMUT 5 (bench only) drops the pi and rce relays (contract break)
    reg [289:0] pi0_r,pi1_r; reg [265:0] ri0_r,ri1_r; reg [263:0] cco0_r,cco1_r; reg [287:0] rce0_r,rce1_r; reg [2:0] rf_r;
    wire [2:0] rfault;
    always @(posedge clk) begin
        pi0_r<=pi0; pi1_r<=pi1; ri0_r<=ri0; ri1_r<=ri1; cco0_r<=cco0; cco1_r<=cco1; rce0_r<=rce0; rce1_r<=rce1; rf_r<=rfault;
    end
    wire [289:0] pi0_s=(RMUT==5) ? pi0 : pi0_r, pi1_s=(RMUT==5) ? pi1 : pi1_r;
    wire [287:0] rce0_s=(RMUT==5) ? rce0 : rce0_r, rce1_s=(RMUT==5) ? rce1 : rce1_r;
    assign ring_fault=rfault;
    ot_vms_hub_lt #(.NC(NC),.CW(CW),.MUT(RMUT),.NLH(NLH)) u_hub(
        .clk(clk),.rl(rl[OH+:NLH]),.sid(sid),.cq(hcq),.cr(hcr),
        .client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),
        .bank_enable(bank_enable),.bank_client(bank_client),
        .cw_enable(hub_ring_enable[0]),.cw_client(hub_ring_client[0+:CW]),
        .ccw_enable(hub_ring_enable[1]),.ccw_client(hub_ring_client[CW+:CW]),
        .pq(bk_pq),.pr(bk_pr),.cwi(pi0),.cci(pi1),.cco0(cco0_r),.cco1(cco1_r),.status(hub_status));
    ot_vms_rstop_lt #(.COMMIT_DELAY(COMMIT_DELAY),.MUT(RMUT),.UPPER(UPPER),.NLS(NLS)) u_cw(
        .clk(clk),.rl(rl[OC+:NLS]),.sid(sid),.dir(1'b0),
        .tx_enable(ring_tx_enable[0]),.tx_source(ring_tx_source[0+:3]),
        .l_in(cw_in),.l_out(cw_out),.pi(pi0_s),.eg(bk_eg),.xq(bk_xq),.xq_done(bk_xq_done),
        .rce(rce0),.ri(ri0_r),.wko(wk01),.wki(wk10),.cco(cco0),
        .ack_o(ack01),.ack_i(ack10),.mirror_busy(mirror_busy[0]),.fault(rfault[0]));
    ot_vms_rstop_lt #(.COMMIT_DELAY(COMMIT_DELAY),.MUT(RMUT),.UPPER(UPPER),.NLS(NLS)) u_ccw(
        .clk(clk),.rl(rl[OCC+:NLS]),.sid(sid),.dir(1'b1),
        .tx_enable(ring_tx_enable[1]),.tx_source(ring_tx_source[3+:3]),
        .l_in(ccw_in),.l_out(ccw_out),.pi(pi1_s),.eg(bk_eg),.xq(bk_xq2),.xq_done(bk_xq2_done),
        .rce(rce1),.ri(ri1_r),.wko(wk10),.wki(wk01),.cco(cco1),
        .ack_o(ack10),.ack_i(ack01),.mirror_busy(mirror_busy[1]),.fault(rfault[1]));
    ot_vms_rcl_lt u_replay(.clk(clk),.rl(rl[OR_+:3]),.sid(sid),
        .rx_enable(replay_enable),.rx_source(replay_source),.rce0(rce0_s),.rce1(rce1_s),
        .hq(hq),.hr(hr),.ri0(ri0),.ri1(ri1),.fault(rfault[2]));
    ot_vms_status_static u_status(.clk(clk),.rst_n(rl[OS]),
        .bank_status(bank_status),.hub_status(hub_status),.ring_fault(|rf_r),.vmstat(vmstat));
endmodule
`default_nettype wire
