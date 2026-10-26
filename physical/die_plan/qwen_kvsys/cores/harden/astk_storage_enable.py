#!/usr/bin/env python3
"""ASTK6 opt-in kit transform: per-row 32-bit storage enables, zero cycles.

Apply after astk_path4. Enables capture zl/tl with zq/tq, using the next
drain-counter value. Original put remains for sv/f logic. Production RTL
stays unchanged until this transform is explicitly applied to a new kit.
"""
from pathlib import Path

WE_MODULE = r"""
(* keep_hierarchy *) module qkd_astk_sd_we #(
    parameter integer ROW = 0,
    parameter [3:0] ZC = 0
) (
    input wire ck, input wire rst_n,
    input wire [14:0] tl,
    input wire [9:0] zl,
    input wire [5:0] stl,
    input wire start,
    output wire [3:0] we
);
    wire [3:0] slot_n = zl[9:6];
    wire [3:0] sib_n = {slot_n[3:1],1'b1};
    wire [3:0] sgam_n = (ZC[3:2] == 2'd0) ? sib_n :
                       (ZC[3:2] == 2'd1) ? {sib_n[2:0],1'b0} :
                       (ZC[3:2] == 2'd2) ? {sib_n[1:0],2'b00} : {sib_n[0],3'b000};
    wire [8:0] lo_bound = {ZC[1:0],sgam_n,3'b000};
    wire pb_n = (5'(ROW) < tl[14:10]) ||
                ((5'(ROW) == tl[14:10]) && (lo_bound < tl[9:1]));
    // zq/tq next contain zl/tl. Drain next is zero iff no restart
    // occurs now and the present counter is zero or one.
    wire ready_n = !start && (stl <= 6'd1);
    wire eligible = zl[0] && !zl[6] && (zl[5:2] == 4'(ROW)) && pb_n && ready_n && (`KVD_AKMUT != 3);
    (* keep *) reg [3:0] en;
    assign we = en;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) en <= 4'd0;
        else en <= {4{eligible}};
endmodule
"""


def transform(text):
    assert "(* keep *) reg [137:0] zl;" in text, "requires ASTK4 landing stage"
    assert text.count("        if (put) sd[k] <= d;\n") == 1
    text = text.replace("        if (put) sd[k] <= d;\n", "")
    anchor = "    always @(posedge ck) begin\n        ot <= {1'b0, slot[3:1], k, g};\n"
    assert text.count(anchor) == 1
    rows = r"""    // ASTK6:64 local enables; each Q drives 32 storage flops.
    genvar wr, wg;
    generate for(wr=0;wr<16;wr=wr+1) begin:g_sd_row
        wire [3:0] we;
        (* keep, keep_hierarchy *) qkd_astk_sd_we #(.ROW(wr),.ZC(ZC)) u_we
            (.ck(ck),.rst_n(rn_q),.tl(tl),.zl(zl[9:0]),.stl(stl),.start(start),.we(we));
        for(wg=0;wg<4;wg=wg+1) begin:g_word
            always @(posedge ck) if(we[wg]) sd[wr][32*wg+:32] <= d[32*wg+:32];
        end
    end endgenerate
"""
    return text.replace(anchor, rows + anchor) + WE_MODULE


def apply_kit(rtl_dir):
    p = Path(rtl_dir) / "qkd_astk_zn_head_p.sv"
    p.write_text(transform(p.read_text()))


def replica_expect(exp):
    exp["rules"].append(dict(name="zn0 storage row write-enable copies",
        inst_re=r"g_zn_0_u_zn[./]g_sd_row\\?\[(\d+)\\?\][./]u_we$",
        groups=[str(i) for i in range(16)], ff_per_inst=4))
    return exp


if __name__ == "__main__":
    import sys
    apply_kit(sys.argv[1])
