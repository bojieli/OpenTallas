# writes physical/qwen_fwd_lane/qfd_land8_masters.sv (QW-LAND8 D8 landh0 class masters)
import sys
SIZES = {1: (15.12, 15.12), 3: (15.12, 15.12), 10: (19.44, 19.44), 32: (25.92, 23.76)}
def main():
  out = ["`timescale 1ns/1ps",
         "// QW-LAND8 10-19: D8 hop-0 landing class masters (rtl/qwen_split/qfd_land8.sv ot_qfd_land8).  Written by",
         "// tools/qwen_split/gen_land8_masters.py; ports = qfd_landh0 + the fourth K strap pin k3.",
         "// qfd_landh0d8_*  : hop-0 ICG on ck_s with the REGISTERED enable (main);  qfd_landh0d8n_*: no clock gate (fallback)."]
  for w, (fw, fh) in SIZES.items():
      for tag, icg in (("d8", 1), ("d8n", 0)):
          name = f"qfd_landh0{tag}_{w}_EW_{round(fw)}x{round(fh)}"
          out.append(f"module {name} (input wire ck_s, input wire en, input wire [{w-1}:0] a, input wire ck, input wire rs, "
                     f"input wire k0, input wire k1, input wire k2, input wire k3, output wire tie_hi, output wire tie_lo, "
                     f"output wire [{w-1}:0] b, output wire fault);")
          out.append("    (* keep = \"true\" *) wire tie_hi_w = 1'b1;")
          out.append("    (* keep = \"true\" *) wire tie_lo_w = 1'b0;")
          out.append("    assign tie_hi = tie_hi_w;")
          out.append("    assign tie_lo = tie_lo_w;")
          out.append(f"    ot_qfd_land8 #(.W({w}), .ICG({icg})) u_land (.ck_s(ck_s), .en(en), .i(a), .ck(ck), .rs(rs), "
                     f".k({{k3, k2, k1, k0}}), .o(b), .fault(fault));")
          out.append("endmodule")
  open(sys.argv[1], "w").write("\n".join(out) + "\n")


if __name__ == '__main__':
    main()
