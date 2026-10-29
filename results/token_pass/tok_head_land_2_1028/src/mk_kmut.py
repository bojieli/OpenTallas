#!/usr/bin/env python3
"""TOK-HEAD-LAND-2 K mutants on ctl -> sp0 (x/GO crossing): sp0 .strap_ca_k_x_i 8 -> 7 (km1) and 8 -> 9 (kp1),
exactly one strap literal changed in land/gen/s81_head_top.sv.  Run in the run dir R; then die_TT<m>.f = die_TT.f
with the top path swapped (sed)."""
from pathlib import Path
top = Path("land/gen/s81_head_top.sv").read_text().split("\n")
i = next(n for n, l in enumerate(top) if l.startswith("    ot_s81hd_spn sp0 ("))
j = next(n for n in range(i, len(top)) if "strap_ca_k_x_i(" in top[n])
k_end = next(n for n in range(i + 1, len(top)) if top[n].startswith("    ot_s81hd_"))
assert j < k_end and top[j].strip() == ".strap_ca_k_x_i(6\x27b001000),", top[j]
for tag, v in (("km1", 7), ("kp1", 9)):
    t = list(top); t[j] = t[j].replace("6\x27b001000", "6\x27b%s" % format(v, "06b"))
    Path(tag).mkdir(exist_ok=True); Path(tag, "s81_head_top.sv").write_text("\n".join(t))
    print(tag, "line", j + 1, t[j].strip())
