# PATH-QC-RP1-F59 keep check (SRAMIF form): every per-bank MIF=1 landing register copy survives Yosys as its own kept
# kff module instance with W flops (memory 10-18: keep on parameterised modules is renamed; check the netlist, not RTL).
import glob, re, sys
k = sys.argv[1]
v = open(sorted(glob.glob(k + '/run/results/asap7/*/base/1_2_yosys.v'))[-1]).read()
mods = {}
for m in re.finditer(r'^module (\S+)\s*\(.*?^endmodule', v, re.M | re.S):
    mods[m.group(1)] = len(re.findall(r'^\s*DFF\w+\s', m.group(0), re.M))
inst = {}
for m in re.finditer(r'^\s*(\\\$paramod\S+qfd_dv_s8x_kff)\s+(\\\S+|\S+)\s*\(', v, re.M):
    inst[m.group(2).lstrip('\\')] = mods.get(m.group(1).lstrip('\\'), mods.get(m.group(1), -1))
exp = {'g_rs1.u_rs': 25, 'g_rs1.u_c1w': 1, 'u_c1': 1}
for b in range(2):
    exp.update({f'g_crb[{b}].g_r.u_rce': 1, f'g_crb[{b}].g_r.u_ra': 10, f'g_crb[{b}].g_r.u_we': 1,
                f'g_crb[{b}].g_r.u_wa': 10, f'g_crb[{b}].g_r.u_wd': 256})
bad = 0
for n, w in exp.items():
    got = inst.get(n); ok = got == w; bad += not ok
    print('KEEP %-24s want %3d flops got %s %s' % (n, w, got, 'OK' if ok else 'FAIL'))
print('KEEP_CHECK qfd_dv_s8_crh_rp1 %s copies %d/%d (kept kff instances in netlist: %d)' % ('PASS' if not bad else 'FAIL', len(exp) - bad, len(exp), len(inst)))
sys.exit(1 if bad else 0)
