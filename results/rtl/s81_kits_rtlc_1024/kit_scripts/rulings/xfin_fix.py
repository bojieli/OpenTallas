p="rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv"; s=open(p).read()
pairs=[
("    output reg  [31:0]        e_hh, e_kk, e_dd,\n    output wire               fault",
 "    output reg  [31:0]        e_hh, e_kk, e_dd,\n    output reg                fault         // RTLC 10-24: pin flop = the kept sticky flt next state (0 edges)"),
("""        for (d2 = 0; d2 < 4; d2 = d2 + 1) if (eoh[d2]) begin
            e_c <= d2; e_hh <= cr_v[d2] ? chh[d2] : ehh[d2]; e_kk <= cr_v[d2] ? ckk[d2] : ekk[d2];
            e_dd <= cr_v[d2] ? cdd[d2] : edd[d2];
        end""",
"""        // S81-KITS-RTLC 10-24 (raw face_guard: no output pin flop reads itself): the ENG result registers are ZERO when no
        // copy is emitted (were: hold), so e_* change only where e_v = 0 (the collection reads them under e_v).
        e_c <= 2'd0; e_hh <= 32'd0; e_kk <= 32'd0; e_dd <= 32'd0;
`ifdef OT_RTLC_MUT_XFIN   // RTLC bench mutant: e_kk carries e_hh
        for (d2 = 0; d2 < 4; d2 = d2 + 1) if (eoh[d2]) begin
            e_c <= d2; e_hh <= cr_v[d2] ? chh[d2] : ehh[d2]; e_kk <= cr_v[d2] ? chh[d2] : ehh[d2];
            e_dd <= cr_v[d2] ? cdd[d2] : edd[d2];
        end
`else
        for (d2 = 0; d2 < 4; d2 = d2 + 1) if (eoh[d2]) begin
            e_c <= d2; e_hh <= cr_v[d2] ? chh[d2] : ehh[d2]; e_kk <= cr_v[d2] ? ckk[d2] : ekk[d2];
            e_dd <= cr_v[d2] ? cdd[d2] : edd[d2];
        end
`endif"""),
("""    reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt <= 1'b0; else if (go_c) flt <= 1'b0; else if (xf || rf || eflt || (|tbad) || (|cf)) flt <= 1'b1;
    assign fault = flt;""",
"""    (* keep = "true" *) reg flt;                        // sticky state (kept); the fault pin flop loads its next value
    wire flt_set = xf || rf || eflt || (|tbad) || (|cf);
    always @(posedge clk or negedge rstn)
        if (!rstn) begin flt <= 1'b0; fault <= 1'b0; end
        else if (go_c) begin flt <= 1'b0; fault <= 1'b0; end
        else begin flt <= flt | flt_set; fault <= flt | flt_set; end"""),
]
for o,n in pairs:
    assert s.count(o)==1,o[:60]; s=s.replace(o,n)
open(p,"w").write(s); print("ok")
