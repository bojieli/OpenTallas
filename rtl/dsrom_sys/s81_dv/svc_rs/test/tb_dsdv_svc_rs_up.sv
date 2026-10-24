`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// RTL-BUILD-S81 (10-18): unit bench of the service-slice up tree (dsdv_svc_rs_up x16 on the p4j 2 x 8 grid, the role ROM
// of dsdv_svc_rs_roles.svh, the neighbour face wiring of tb_dsdv_svc_rs).  Random per-slice {done, fault, hcr, hack,
// hs = {ctrl fault, ctrl live}} held for HOLD cycles per epoch; after the tree latency each entry's uc must equal the
// reference fold over its half (half = the slices whose parent chain reaches that entry):
//   [15] rg fault = OR hs[1], [14] rg live = AND hs[0], [13] done = AND, [12] fault = OR, [11:6] / [5:0] sums.
// Epochs include all-live, one controller down, one controller fault.  MUT (bench only, dsdv_svc_rs_up UPMUT): 1 = live
// folded as OR.  PASS / FAIL line + counts.
// ---------------------------------------------------------------------------------------------------------------------
module tb_dsdv_svc_rs_up #(parameter integer MUT = 0, parameter integer EPOCHS = 400, parameter integer HOLD = 40);
`include "dsdv_svc_rs_roles.svh"
`ifdef UP_FMASK
`include "dsdv_svc_rs_faces.svh"
`endif
    localparam integer UW = 16;
    reg ck = 0, rst = 0;
    always #0.5 ck = ~ck;
    reg rn = 0;
    wire [4*UW-1:0] up_i [0:15], up_o [0:15];
    wire [UW-1:0] uc [0:15];
    reg done [0:15], fl [0:15]; reg [1:0] hcr [0:15], hack [0:15], hs [0:15];
    function automatic integer nb(input integer sd, input integer fc);
        integer r, c;
        r = sd % 2; c = sd / 2;
        case (fc)
            0: nb = (r == 0) ? 2*c + 1 : -1;
            1: nb = (c < 7) ? 2*(c+1) + r : -1;
            2: nb = (r == 1) ? 2*c : -1;
            default: nb = (c > 0) ? 2*(c-1) + r : -1;
        endcase
    endfunction
    genvar gs, gf;
    generate for (gs = 0; gs < 16; gs = gs + 1) begin : g_s
        localparam [21:0] RL = rs_role(gs);
        for (gf = 0; gf < 4; gf = gf + 1) begin : g_f
            localparam integer NBS = nb(gs, gf), OF = (gf + 2) % 4;
            if (NBS >= 0) begin : g_c
                assign up_i[gs][UW*gf +: UW] = up_o[NBS][UW*OF +: UW];
            end else begin : g_e
                assign up_i[gs][UW*gf +: UW] = '0;
            end
        end
`ifdef UP_FMASK
        // S81-P9-FACE: each slice's up node built with its variant's role face masks (rs_fmask: UI = [11:8], UO = [15:12])
        localparam logic [39:0] FMS = rs_fmask(4'(gs));
        dsdv_svc_rs_up #(.UW(UW), .UPMUT(MUT), .FM_UI(FMS[11:8]), .FM_UO(FMS[15:12])) u (.ck(ck), .rn(rn), .chm(RL[7:4]),
            .par(RL[10:8]), .done(done[gs]),
`else
        dsdv_svc_rs_up #(.UW(UW), .UPMUT(MUT)) u (.ck(ck), .rn(rn), .chm(RL[7:4]), .par(RL[10:8]), .done(done[gs]),
`endif
            .fl(fl[gs]), .hcr(hcr[gs]), .hack(hack[gs]), .hs_s(hs[gs]), .up_i(up_i[gs]), .up_o(up_o[gs]), .uc(uc[gs]));
    end endgenerate
    // half membership: follow the parent faces to an entry
    function automatic integer entry_of(input integer sd);
        integer s, p, k;
        s = sd;
        for (k = 0; k < 16; k++) begin
            p = rs_role(4'(s))[10:8];
            if (p == 0) return s;
            s = nb(s, p - 1);
        end
        return -1;
    endfunction
    integer e, i, h, bad = 0, chk = 0, nlive0 = 0, nflt = 0;
    integer ent [0:1];
    reg [UW-1:0] ref_ [0:1];
    initial begin
        ent[0] = RS_ENTRY_W; ent[1] = RS_ENTRY_E;
        for (i = 0; i < 16; i++) if (entry_of(i) != RS_ENTRY_W && entry_of(i) != RS_ENTRY_E) begin
            $display("FAIL slice %0d reaches no entry", i); $finish;
        end
        for (i = 0; i < 16; i++) begin done[i] = 0; fl[i] = 0; hcr[i] = 0; hack[i] = 0; hs[i] = 0; end
        repeat (4) @(negedge ck); rn = 1;
        for (e = 0; e < EPOCHS; e++) begin
            @(negedge ck);
            for (i = 0; i < 16; i++) begin
                done[i] = ($urandom % 8) != 0; fl[i] = ($urandom % 16) == 0; hcr[i] = $urandom; hack[i] = $urandom;
                hs[i] = 2'b01;
            end
            case (e % 4)          // epoch kinds: all live / one controller down / one fault / random
                1: hs[$urandom % 16] = 2'b00;
                2: hs[$urandom % 16] = 2'b11;
                3: for (i = 0; i < 16; i++) hs[i] = $urandom;
                default: ;
            endcase
            for (h = 0; h < 2; h++) begin
                reg rgf, rgl, dn, f; reg [5:0] c, a;
                rgf = 0; rgl = 1; dn = 1; f = 0; c = 0; a = 0;
                for (i = 0; i < 16; i++) if (entry_of(i) == ent[h]) begin
                    rgf |= hs[i][1]; rgl &= hs[i][0]; dn &= done[i]; f |= fl[i]; c += 6'(hcr[i]); a += 6'(hack[i]);
                end
                ref_[h] = {rgf, rgl, dn, f, c, a};
                if (!rgl) nlive0++;
                if (rgf) nflt++;
            end
            repeat (HOLD) @(negedge ck);
            for (h = 0; h < 2; h++) begin
                chk++;
                if (uc[ent[h]] !== ref_[h]) begin
                    bad++;
                    if (bad <= 5) $display("BAD epoch %0d entry %0d: uc %h ref %h", e, ent[h], uc[ent[h]], ref_[h]);
                end
            end
        end
        if (MUT != 0) begin
            if (bad == 0) begin $display("FAIL MUTANT %0d NOT DETECTED (%0d checks)", MUT, chk); $finish; end
            $display("FAIL MUTANT %0d REJECTED mismatches=%0d/%0d", MUT, bad, chk); $finish;
        end
        if (bad == 0 && nlive0 > 0 && nflt > 0)
            $display("PASS dsdv_svc_rs_up 16-slice tree: %0d entry checks (%0d live-down, %0d fault halves) bit exact", chk, nlive0, nflt);
        else $display("FAIL dsdv_svc_rs_up mismatches=%0d/%0d live-down %0d fault %0d", bad, chk, nlive0, nflt);
        $finish;
    end
endmodule
