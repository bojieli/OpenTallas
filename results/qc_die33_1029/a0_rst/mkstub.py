import re
src=open("rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_45.sv").read().split("\n")
hdr="\n".join(src[19:117])
outs=[m.group(2) for l in src[19:117] for m in re.finditer(r"output\s+wire\s*(\[[^\]]+\])?\s*(\w+)",l)]
body=hdr+"\n"+"\n".join(f"    assign {o} = {'1' if o=='me_idle' else '0'};" for o in outs)+"\nendmodule\n"
open("tools/qwen_romleaf/a0core/icg/rrst_body_stub_nk.sv","w").write("// DIE-QC-33 reset-relay bench vehicle ONLY: port-identical stub of qfd_tile_nk_rp2_45 (outputs 0, me_idle 1 = idle).\n"+body)
print(outs)
