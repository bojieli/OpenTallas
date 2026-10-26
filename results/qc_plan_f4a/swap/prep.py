# QC-PLAN-F4A narrowed swap (COORD RULING (2)): build old (origin/main, modules suffixed _o) and mutant sources.
import re, subprocess, sys, os
W = sys.argv[1]; D = os.path.join(W, "results/qc_plan_f4a/swap")
F = ["rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv", "rtl/qwen_dv/s5/s8/qfd_dv_s8_crh_rp1.sv"]
old = "".join(subprocess.check_output(["git", "-C", W, "show", "origin/main:" + f]).decode() for f in F)
new = "".join(open(os.path.join(W, f)).read() for f in F)
mods = set(re.findall(r"^(?:\(\*[^*]*\*\)\s*)?\s*module\s+(\w+)", old, re.M))
for m in sorted(mods, key=len, reverse=True):
    old = re.sub(r"\b%s\b" % m, m + "_o", old)
open(f"{D}/old_suffixed.sv", "w").write(old)
open(f"{D}/new.sv", "w").write(new)
# mutants: flip r_addr bit 0 on the swapped SRAM of the module under test only
a = "ot_sram_1r1w_1024x256_m1b2_r2c2_ns u_m (.clk(ck),\n            .r_ce_in(m_rce),\n            .r_addr_in(m_ra),"
assert new.count(a) == 1
open(f"{D}/mut_vmr.sv", "w").write(new.replace(a, a.replace("(m_ra)", "(m_ra ^ 10'd1)")))
b = "ot_sram_1r1w_1024x256_m1b2_r2c2_ns u_m (.clk(ck), .r_ce_in(m_rce), .r_addr_in(m_ra),"
assert new.count(b) == 1
open(f"{D}/mut_rp1.sv", "w").write(new.replace(b, b.replace("(m_ra)", "(m_ra ^ 10'd1)")))
print("modules suffixed", len(mods))
