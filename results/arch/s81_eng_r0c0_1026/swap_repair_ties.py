"""PATH-S81/ENG-R0C0: swap every repair-tied r2c2 SRAM instance of dsdv_eng_rr_e to its no-repair r0c0_pc master
and delete the repair tie-offs.  usage: swap.py FILE..."""
import re, sys
TIE = re.compile(r",\s*\n(\s*)\.rr_en\(2'b00\), \.rr_addr\(\d+'d0\), \.cr_en\(2'b00\), \.cr_sel\(\d+'d0\)\);")
for f in sys.argv[1:]:
    s = open(f).read(); n0 = s.count("_r2c2 u_")
    out = []; pos = 0; n = 0
    for m in re.finditer(r"ot_sram_1r1w_(64x512_m1|512x128_m4|128x256_m1)_r2c2 (u_\w+) \(", s):
        end = s.index(");", m.end()) + 2
        inst = s[m.start():end]
        new, k = TIE.subn(");", inst)
        assert k == 1, (f, m.group(2), inst)
        new = new.replace(f"ot_sram_1r1w_{m.group(1)}_r2c2 ", f"ot_sram_1r1w_{m.group(1)}_r0c0_pc ", 1)
        out.append(s[pos:m.start()]); out.append(new); pos = end; n += 1
    out.append(s[pos:]); s2 = "".join(out)
    assert "rr_en" not in s2 and "cr_sel" not in s2, f
    open(f, "w").write(s2); print(f, "swapped", n, "of", n0)
