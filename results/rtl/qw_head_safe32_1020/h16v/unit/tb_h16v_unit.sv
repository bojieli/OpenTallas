`timescale 1ns/1ps
// QW-H16V unit exactness: ot_hdc_dyn_ttiles_tab vs 16 x ot_hdc_dyn_ttiles (exhaustive pos, several G), ot_hdc_inc_ks /
// ot_hdc_gt_ks (random + corners), ot_qwen_tp8_rom_relocate_pb + _base vs ot_qwen_tp8_rom_relocate (all stages, random cmd).
module tab_chk #(parameter integer W=16, G=6144, NW=18) (input wire [NW-1:0] pos, output wire bad);
    wire [16*NW-1:0] r; wire [15:0] iv; wire [NW-1:0] qq;
    ot_hdc_dyn_ttiles_q #(.W(W),.G(G),.NW(NW)) uq (.pos(pos),.quot(qq));
    ot_hdc_dyn_ttiles_tab #(.W(W),.G(G),.NW(NW)) u (.quot(qq),.rounds(r),.invalid(iv));
    wire [15:0] b;
    genvar d;
    for (d = 0; d < 16; d = d + 1) begin : g
        wire [NW-1:0] rr; wire ii;
        ot_hdc_dyn_ttiles #(.W(W),.G(G),.NW(NW)) o (.pos(pos),.split_log2(4'(d)),.rounds(rr),.invalid_split(ii));
        assign b[d] = (rr !== r[d*NW +: NW]) || (ii !== iv[d]);
    end
    assign bad = |b;
endmodule
module tb_h16v_unit;
    reg [17:0] pos; reg [11:0] p12;
    wire b0, b1, b2, b3, b4, b5, b6;
    tab_chk #(.W(16),.G(6144),.NW(18)) c0 (.pos(pos),.bad(b0));
    tab_chk #(.W(16),.G(768),.NW(18))  c1 (.pos(pos),.bad(b1));
    tab_chk #(.W(16),.G(4),.NW(18))    c2 (.pos(pos),.bad(b2));
    tab_chk #(.W(16),.G(5),.NW(18))    c3 (.pos(pos),.bad(b3));
    tab_chk #(.W(8),.G(24),.NW(18))    c4 (.pos(pos),.bad(b4));
    tab_chk #(.W(1),.G(3),.NW(18))     c5 (.pos(pos),.bad(b5));
    tab_chk #(.W(16),.G(6144),.NW(12)) c6 (.pos(p12),.bad(b6));
    reg [31:0] a, bb; wire [31:0] y; wire gt;
    ot_hdc_inc_ks #(.W(32)) ui (.a(a),.y(y));
    ot_hdc_gt_ks #(.W(32)) ug (.a(a),.b(bb),.gt(gt));
    reg [17:0] a18; wire [17:0] y18; ot_hdc_inc_ks #(.W(18)) ui18 (.a(a18),.y(y18));
    reg [379:0] cmd; reg [5:0] st; wire [379:0] o1, o2; wire f1, f2, vs, hd; wire [23:0] cb, sb;
    ot_qwen_tp8_rom_relocate r0 (.in_cmd(cmd),.in_stage(st),.out_cmd(o1),.fault(f1));
    ot_qwen_tp8_rom_relocate_base rb (.in_stage(st),.valid_stage(vs),.head(hd),.code_base(cb),.scale_base(sb));
    ot_qwen_tp8_rom_relocate_pb r1 (.in_cmd(cmd),.valid_stage(vs),.head(hd),.code_base(cb),.scale_base(sb),.out_cmd(o2),.fault(f2));
    integer i, j, err;
    initial begin
        err = 0;
        for (i = 0; i < (1 << 18); i = i + 1) begin
            pos = i; p12 = i[11:0]; #1;
            if (b0|b1|b2|b3|b4|b5|b6) begin err = err + 1; if (err < 10) $display("TAB MISMATCH pos=%0d %b%b%b%b%b%b%b", i, b0,b1,b2,b3,b4,b5,b6); end
        end
        for (i = 0; i < 200000; i = i + 1) begin
            a = (i < 64) ? ((i & 1) ? 32'hFFFFFFFF : 32'h0) ^ (32'h1 << (i >> 1)) : $random; bb = (i % 3 == 0) ? a ^ (32'h1 << (i % 32)) : (i % 7 == 0) ? a : $random;
            a18 = $random; #1;
            if (y !== a + 1'b1 || gt !== (a > bb) || y18 !== a18 + 1'b1) begin err = err + 1; if (err < 10) $display("KS MISMATCH a=%h b=%h", a, bb); end
        end
        for (j = 0; j < 64; j = j + 1) for (i = 0; i < 400; i = i + 1) begin
            st = j; cmd = {12{$random}}; if (i & 1) cmd[55] = 0; if (i & 2) cmd[0] = 1;
            if (i & 4) cmd[79:56] = $random % 1700; if (i & 8) cmd[278:255] = $random % 1300; #1;
            if (o1 !== o2 || f1 !== f2) begin err = err + 1; if (err < 10) $display("RELOC MISMATCH st=%0d", j); end
        end
        if (err == 0) $display("H16V_UNIT PASS"); else $display("H16V_UNIT FAIL %0d", err);
        $finish;
    end
endmodule
