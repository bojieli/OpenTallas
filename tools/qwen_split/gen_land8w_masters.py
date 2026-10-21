# writes physical/qwen_fwd_lane/qfd_land8w_masters.sv (QW-LANDW 10-19: wide D8 landh0 class masters)
#   FLOP: 107 / 116 b = ot_qfd_land8 D8 flop ring (8 slots x W < 2 kb per slot set)
#   SRAM: slice tiles of the 453 / 520 / 548-b records = ot_qfd_land8s (3 x 64-b dual-clock SRAM banks per tile);
#         a lane of width WL is ceil(WL / 192) = 3 slice tiles side by side, same strap K, same calendar
import sys
FLOP = {107: (44.28, 44.28), 116: (46.44, 46.44)}
SRAM_TILE = (98.28, 170.64)
SRAM = (151, 173, 174, 182, 183)
LANES = {453: (151, 151, 151), 520: (174, 173, 173), 548: (183, 183, 182)}
MACRO_AT = ((43.2, 43.2), (43.2, 86.4), (43.2, 129.6))


def masters():
    out = []
    for w, (fw, fh) in FLOP.items():
        for tag, icg in (("d8", 1), ("d8n", 0)):
            out.append((f"qfd_landh0{tag}_{w}_EW_{round(fw)}x{round(fh)}", w, icg, "ot_qfd_land8", fw, fh))
    for w in SRAM:
        fw, fh = SRAM_TILE
        for tag, icg in (("d8s", 1), ("d8sn", 0)):
            out.append((f"qfd_landh0{tag}_{w}_EW_{round(fw)}x{round(fh)}", w, icg, "ot_qfd_land8s", fw, fh))
    return out


def main():
    out = ["`timescale 1ns/1ps",
           "// QW-LANDW 10-19: wide D8 hop-0 landing class masters.  Written by tools/qwen_split/gen_land8w_masters.py.",
           "// qfd_landh0d8_* / d8n_*  : D8 flop ring (rtl/qwen_split/qfd_land8.sv ot_qfd_land8), ICG main / no-ICG fallback.",
           "// qfd_landh0d8s_* / d8sn_*: D8 SRAM record slice (rtl/qwen_split/qfd_land8s.sv ot_qfd_land8s), ICG / no ICG.",
           "// Ports = qfd_landh0d8 (ck_s en a ck rs k0..k3 tie_hi tie_lo b fault)."]
    for name, w, icg, core, _, _ in masters():
        out.append(f"module {name} (input wire ck_s, input wire en, input wire [{w-1}:0] a, input wire ck, input wire rs, "
                   f"input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, "
                   f"output wire [{w-1}:0] b, output wire fault);")
        out.append("    (* keep = \"true\" *) wire tie_hi_w = 1'b1;")
        out.append("    (* keep = \"true\" *) wire tie_lo_w = 1'b0;")
        out.append("    assign tie_hi = tie_hi_w;")
        out.append("    assign tie_lo = tie_lo_w;")
        out.append(f"    {core} #(.W({w}), .ICG({icg})) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), "
                   f".k({{k3, k2, k1, k0}}), .o(b), .fault(fault));")
        out.append("endmodule")
    open(sys.argv[1], "w").write("\n".join(out) + "\n")


if __name__ == '__main__':
    main()
