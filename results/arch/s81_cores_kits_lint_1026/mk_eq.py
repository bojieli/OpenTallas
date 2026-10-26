import importlib.util, shutil, sys, re
from pathlib import Path
K = Path('/srv/opentallas-scratch2/claude/cores-kits/s81/kits')
ORIG = Path('/srv/opentallas-scratch2/claude/cores-kits/s81/lintA')
E = Path('/srv/opentallas-scratch2/claude/cores-kits/s81/lintA/eq')
CHG = ['ot_s81sl_xrt.sv', 'dsdv_gunit_l1c.sv', 'dsdv_gunit_pass.sv', 'ot_s81_su_rw.sv', 'dsdv_bk_v.sv']
MUT = {  # kit -> (file, old, new) or ('define', NAME)
 'dsdv_gunit_l0': ('dsdv_gunit_pass.sv', 's[k] <= s[k - 1];', 's[k] <= ~s[k - 1];'),
 'dsdv_gunit_l1': ('dsdv_gunit_pass.sv', 's[k] <= s[k - 1];', 's[k] <= ~s[k - 1];'),
 'dsdv_gunit_l4': ('dsdv_gunit_pass.sv', 's[k] <= s[k - 1];', 's[k] <= ~s[k - 1];'),
 'dsdv_gunit_l3': ('ot_s81_su_rw.sv', 'id[i] <= i_x[32 * i +: 9];', 'id[i] <= ~i_x[32 * i +: 9];'),
 'ot_s81sl_xrt1': ('ot_s81sl_xrt.sv', 'lov_c[k] <= lo_v_i[k / 16];', 'lov_c[k] <= !lo_v_i[k / 16];'),
 'dsdv_gunit_l1c': ('define', 'OT_RTLC_MUT_L1C'),
 'dsdv_bk_g': ('define', 'OT_RTLC_MUT_BKLN'),
}
for m, mut in MUT.items():
    kit = K / f'{m}_k26b'
    spec = importlib.util.spec_from_file_location('rl_' + m, kit / 'rtl_lint.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    lines = mod.script(kit).splitlines()
    d = E / m; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    shutil.copytree(kit / 'rtl', d / 'gold'); shutil.copytree(kit / 'rtl', d / 'mut')
    changed = [f for f in CHG if (kit / 'rtl' / f).exists()]
    for f in changed: shutil.copy(ORIG / f, d / 'gold' / f)
    pre = [l for l in lines if l.startswith('read_liberty')]
    defs = [l for l in lines if l.startswith('verilog_defines')]
    reads = [l for l in lines if l.startswith('read_verilog')]
    hier = [l for l in lines if l.startswith('hierarchy')][0]
    def elab(root, name):
        return [l.replace('/work/rtl', root) for l in reads] + [hier, 'proc', 'memory', 'flatten', 'opt_clean', f'rename -top {name}', f'design -stash {name}']
    tail = ['design -copy-from gold -as gold gold', 'design -copy-from gate -as gate gate', 'equiv_make gold gate equiv',
            'hierarchy -top equiv', 'equiv_simple -seq 2', 'equiv_induct -seq 2', 'equiv_status -assert']
    (d / 'lint.ys').write_text('\n'.join(lines) + '\n')
    (d / 'eq.ys').write_text('\n'.join(pre + defs + elab('/eq/gold', 'gold') + pre + elab('/work/rtl', 'gate') + tail) + '\n')
    if mut[0] == 'define':
        mdefs = [f'verilog_defines -D{mut[1]}']
    else:
        f, old, new = mut; p = d / 'mut' / f; s = p.read_text(); assert s.count(old) >= 1, (m, old); p.write_text(s.replace(old, new, 1)); mdefs = []
    (d / 'mut.ys').write_text('\n'.join(pre + defs + elab('/eq/gold', 'gold') + pre + mdefs + elab('/eq/mut', 'gate') + tail) + '\n')
    (d / 'run.sh').write_text(f'''cd {d}
for s in lint eq mut; do q=""; [ $s = lint ] && q=-q
docker run --rm -m 14g -v {kit}:/work:ro -v {d}:/eq openroad/orfs:asap7lock bash -lc "export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:\\$PATH; yosys $q -l /eq/$s.log -s /eq/$s.ys" > {d}/$s.out 2>&1; echo "$s rc=$?" >> {d}/rc.txt
done
''')
    print(m, 'changed', changed, 'mut', mut)
