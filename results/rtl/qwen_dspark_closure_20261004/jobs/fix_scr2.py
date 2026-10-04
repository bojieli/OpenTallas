p = "gen_dsc/ot_qwen_rom_core_scr.sv"
t = open(p).read()
for a, b in [("    wire [NW-1:0] dynp_tiles_zero [0:7];\n", "    wire [8*NW-1:0] dynp_tiles_zero_f;   // SCREEN COPY: packed (Yosys 0.68 re-derive assert on an unpacked port array)\n"),
             (".rounds(dynp_tiles_zero[vpt])", ".rounds(dynp_tiles_zero_f[vpt*NW +: NW])"),
             ("<= dynp_tiles_zero[vpo];", "<= dynp_tiles_zero_f[vpo*NW +: NW];")]:
    assert t.count(a) == 1, a
    t = t.replace(a, b)
open(p, "w").write(t)
print("ok")
