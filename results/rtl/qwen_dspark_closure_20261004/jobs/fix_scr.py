p = "gen_dsc/ot_qwen_rom_core_scr.sv"
t = open(p).read()
a = """    genvar vpt;
    generate if (VPOS != 0) begin : g_vpos_tiles
        for (vpt = 0; vpt < 8; vpt = vpt + 1) begin : g_t
            ot_hdc_dyn_ttiles #(.W(W),.G(G),.NW(NW)) u_t (
                .pos(pos_r + vpt),.split_log2(4'd0),.rounds(dynp_tiles_zero[vpt]),.invalid_split());
        end
    end endgenerate
"""
b = """    // SCREEN COPY (VPOS = 1 only): the eight per-position round counters, unconditional
    genvar vpt;
    generate for (vpt = 0; vpt < 8; vpt = vpt + 1) begin : g_vpos_t
        ot_hdc_dyn_ttiles #(.W(W),.G(G),.NW(NW)) u_t (
            .pos(pos_r + vpt),.split_log2(4'd0),.rounds(dynp_tiles_zero[vpt]),.invalid_split());
    end endgenerate
"""
assert a in t
open(p, "w").write(t.replace(a, b))
print("ok")
