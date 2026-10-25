# PATH-QC-SRAMIF keep check: every per-SRAM MIF=1 landing register copy survives Yosys as its own kept module instance
# with W flops (memory 10-18: keep on parameterised modules is renamed; check the netlist, not the RTL).
import glob, re, sys
k = sys.argv[1]
top = re.search(r'^export DESIGN_NAME = (\S+)', open(k + '/config.mk').read(), re.M).group(1)
v = open(sorted(glob.glob(k + '/run/results/asap7/*/base/1_2_yosys.v'))[-1]).read()
mods = {}
for m in re.finditer(r'^module (\S+)\s*\(.*?^endmodule', v, re.M | re.S):
    mods[m.group(1)] = len(re.findall(r'^\s*DFF\w+\s', m.group(0), re.M))
inst = {}
for m in re.finditer(r'^\s*(\\\$paramod\S+qfd_dv_s8x_kff)\s+(\\\S+|\S+)\s*\(', v, re.M):
    inst[m.group(2).lstrip('\\')] = mods.get(m.group(1).lstrip('\\'), mods.get(m.group(1), -1))
if top == 'qfd_dv_s8x_btab':
    exp = {'g_cb1.u_rbk': 2}
    for b in range(4):
        exp.update({f'g_btb[{b}].g_r.u_rce': 1, f'g_btb[{b}].g_r.u_ra': 7, f'g_btb[{b}].g_r.u_we': 1,
                    f'g_btb[{b}].g_r.u_wa': 7, f'g_btb[{b}].g_r.u_wd': 256})
else:
    exp = {'g_cb1.u_rbk': 1}
    for b in range(2):
        for h in ('lo', 'hi'):
            exp.update({f'g_prog[{b}].g_r.u_{h}_rce': 1, f'g_prog[{b}].g_r.u_{h}_ra': 8, f'g_prog[{b}].g_r.u_{h}_we': 1,
                        f'g_prog[{b}].g_r.u_{h}_wa': 8, f'g_prog[{b}].g_r.u_{h}_wd': 256 if h == 'lo' else 201})
bad = 0
for n, w in exp.items():
    got = inst.get(n)
    ok = got == w
    bad += not ok
    print('KEEP %-28s want %3d flops got %s %s' % (n, w, got, 'OK' if ok else 'FAIL'))
print('KEEP_CHECK %s %s copies %d/%d (kept kff instances in netlist: %d)' % (top, 'PASS' if not bad else 'FAIL', len(exp) - bad, len(exp), len(inst)))
sys.exit(1 if bad else 0)
