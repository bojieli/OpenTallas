#!/usr/bin/env python3
"""KV-AHUB-RH1 equivalence bench inputs: REF = the signed-lineage h1 kit wrapper (constant AP_OFS/FR_OFS) re-parameterised
to table T; DUT = the strap wrapper with strap_ofs_* tied to encode(T) (optionally a wrong tie for the negative control).
usage: mk.py H1_WRAP STRAP_WRAP OUTDIR NAME AP_OFS FR_OFS [TIE_AP TIE_FR]"""
import re, sys, json
from pathlib import Path
sys.path.insert(0, sys.argv[9] if len(sys.argv) > 9 else ".")
import ahub_strap_ofs as A
h1, st, out, name, ap, fr = sys.argv[1:7]
fr = int(fr)
tie_ap, tie_fr = (sys.argv[7], int(sys.argv[8])) if len(sys.argv) > 8 and sys.argv[7] != "x" else (ap, fr)
sap, sfr = A.encode(tie_ap, tie_fr)
out = Path(out); out.mkdir(parents=True, exist_ok=True)
ref = Path(h1).read_text()
n = len(re.findall(r"\.AP_OFS\(64'h[0-9a-f]+\), \.FR_OFS\(-?\d+\)", ref))
assert n == 1, n
ref = re.sub(r"\.AP_OFS\(64'h[0-9a-f]+\), \.FR_OFS\(-?\d+\)", f".AP_OFS({ap}), .FR_OFS({fr})", ref)
ref = ref.replace("module qkd_ahub (", f"module refcore_{name} (", 1)
# tie top: same ports as REF, DUT inside with straps tied
hdr = ref[ref.index(f"module refcore_{name} ("):ref.index(");", ref.index(f"module refcore_{name} ("))]
ports = re.findall(r"(input|output) wire \[(\d+):0\] (\w+)", hdr)
lines = [f"module dut_{name} ("] + [f"    {d} wire [{h}:0] {p}," for d, h, p in ports]
lines[-1] = lines[-1].rstrip(",")
lines += [");", "    qkd_ahub u_dut ("]
conn = [f"        .{p}({p})," for _, _, p in ports] + [f"        .strap_ofs_ap(32'h{sap:08x}),", f"        .strap_ofs_fr(8'h{sfr:02x})"]
lines += conn + ["    );", "endmodule", ""]
(out / f"dut_{name}.sv").write_text("\n".join(lines))
# REF top: same instance name u_dut so both flattened sides share internal names (equiv_make matches by name)
rl = [f"module ref_{name} ("] + [f"    {d} wire [{h}:0] {p}," for d, h, p in ports]
rl[-1] = rl[-1].rstrip(",")
rl += [");", f"    refcore_{name} u_dut ("] + [f"        .{p}({p})," for _, _, p in ports]
rl[-1] = rl[-1].rstrip(",")
rl += ["    );", "endmodule", ""]
(out / f"ref_{name}.sv").write_text(ref + "\n" + "\n".join(rl))
print(json.dumps(dict(name=name, ap=ap, fr=fr, tie=[f"32'h{sap:08x}", f"8'h{sfr:02x}"], ports=len(ports))))
