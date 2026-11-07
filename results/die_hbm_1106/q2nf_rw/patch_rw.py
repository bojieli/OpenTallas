#!/usr/bin/env python3
"""DIE-HBM-83-Q2R d44v part 58: opt-in (`ifdef OT_Q2NF_RW) right-width SRAM masters in ot_q2nf_rest.

Old masters carry mostly unused pins (measured on the vA 3_place.odb: 18,761 macro signal pins, 6,161 real, 9,341 tied,
3,259 outputs with no sink; GRT overflow 469,484 over the macro walls):
  8 x ot_sram_1r1w_64x512_m1_r2c2  w_mask_in = 141 ones, wd_in[511:141] = 0, rd_out[511:141] read by nothing, repair tied 0
      -> ot_sram_1r1w_64x141_m1_r0c0_g141  (rd_out[140:0], wd_in[140:0], w_mask_in = 1)
  6 x ot_sram_1r1w_256x256_m2_r2c2 w_mask_in = all ones, repair tied 0
      -> ot_sram_1r1w_256x256_m2_r0c0_g256 (w_mask_in = 1)
Instance names and every other connection are unchanged; the script asserts each of those facts on the text and stops if
one does not hold.  The default (no define) text is byte-identical to the input with the ifdef lines and the new
branches removed (proved at the end of this script).        patch_rw.py RTL.sv [--check]
"""
import hashlib, re, sys
p = sys.argv[1]; s = open(p).read()
assert "OT_Q2NF_RW" not in s, "already patched"
INST = re.compile(r"^  (ot_sram_1r1w_64x512_m1_r2c2|ot_sram_1r1w_256x256_m2_r2c2) (\\\S+)\s+\(\n(.*?)^  \);\n", re.M | re.S)
NEW = {"ot_sram_1r1w_64x512_m1_r2c2": ("ot_sram_1r1w_64x141_m1_r0c0_g141", 141, 512, 6),
       "ot_sram_1r1w_256x256_m2_r2c2": ("ot_sram_1r1w_256x256_m2_r0c0_g256", 256, 256, 8)}
REPAIR = {"cr_en", "cr_sel", "rr_addr", "rr_en"}
PORTS = re.compile(r"^\s*\.(\w+)\((.*)\),?\s*$", re.M)


def nets(concat):
    """{ a , b , c } -> [a, b, c], msb first; each entry an escaped identifier or a sized constant"""
    t = concat.strip(); assert t[0] == "{" and t[-1] == "}", t[:60]
    return [x.strip() for x in t[1:-1].split(",")]


out, n, count = [], 0, {}
last = 0
for m in INST.finditer(s):
    old_m, name, body = m.groups(); new_m, bits, oldbits, ra = NEW[old_m]
    pr = dict(PORTS.findall(body))
    assert set(pr) == {"clk", "cr_en", "cr_sel", "r_addr_in", "r_ce_in", "rd_out", "rr_addr", "rr_en", "w_addr_in", "w_ce_in", "w_mask_in", "wd_in"}, name
    for k in REPAIR:
        assert re.fullmatch(r"\d+'h0+", pr[k]), (name, k, pr[k])
    mask = re.fullmatch(rf"{oldbits}'h([0-9a-f]+)", pr["w_mask_in"]); assert mask, (name, pr["w_mask_in"][:40])
    assert int(mask.group(1), 16) == (1 << bits) - 1, (name, "mask not low ones")
    rd = nets(pr["rd_out"]); assert len(rd) == oldbits, (name, len(rd))
    if bits != oldbits:
        for q in rd[:oldbits - bits]:                       # read by nothing: declaration + this rd_out only
            assert re.fullmatch(r"\\\S+", q), q
            assert len(re.findall(re.escape(q) + r"(?=\s)", s)) == 2, (name, q, "has a reader")
        wd = nets(pr["wd_in"]); assert wd[0] == f"{oldbits - bits}'h" + "0" * ((oldbits - bits + 3) // 4), (name, wd[0])
        assert len(wd) == bits + 1, (name, len(wd))
        rd_new, wd_new = rd[oldbits - bits:], wd[1:]
        rdt, wdt = "{ " + " , ".join(rd_new) + " }", "{ " + " , ".join(wd_new) + " }"
    else:
        rdt, wdt = pr["rd_out"], pr["wd_in"]
    new = (f"  {new_m} {name}  (\n    .clk({pr['clk']}),\n    .r_addr_in({pr['r_addr_in']}),\n    .r_ce_in({pr['r_ce_in']}),\n"
           f"    .rd_out({rdt}),\n    .w_addr_in({pr['w_addr_in']}),\n    .w_ce_in({pr['w_ce_in']}),\n"
           f"    .w_mask_in(1'h1),\n    .wd_in({wdt})\n  );\n")
    out.append(s[last:m.start()]); out.append("`ifdef OT_Q2NF_RW\n" + new + "`else\n" + m.group(0) + "`endif\n"); last = m.end()
    count[old_m] = count.get(old_m, 0) + 1; n += 1
out.append(s[last:])
assert count == {"ot_sram_1r1w_64x512_m1_r2c2": 8, "ot_sram_1r1w_256x256_m2_r2c2": 6}, count
r = "".join(out)
back = re.sub(r"`ifdef OT_Q2NF_RW\n.*?`else\n(.*?)`endif\n", r"\1", r, flags=re.S)
assert back == s, "default text changed"
print("instances", count, "default text sha256 identical", hashlib.sha256(s.encode()).hexdigest()[:16])
if "--check" not in sys.argv:
    open(p, "w").write(r); print("written", p)
