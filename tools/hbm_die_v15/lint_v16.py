#!/usr/bin/env python3
"""Verilator lint of the v16 full HBM die (H-NETLIST 2026-10-15).

    lint_v16.py DIE_DIR [--top hbm_v16_die] [--remote ot-epyc1tb]

RTL closure per die master with H-DIE's tools/hbm_die_v15/master_filelist.py resolver (the file choice the per-master
synthesis reads), unioned over every master of DIE_DIR/contract.json; mapped memory / PHY / PLL models enter as their
black-box views.  Module-name COLLISIONS (two masters whose closures need different bodies under one module name) cannot
elaborate in one flat die: they are reported (a die-level finding for the owners: uniquify), and the die is linted in
partitions -- the main partition is die.v + every master closure except the colliding minority, which enters by its
port declaration only (lint harness, never part of the die netlist); each colliding master is then linted alone with its
own closure.  Every %Error fails.  Writes DIE_DIR/lint/{lint.json, closure.json, *.log}.
"""
import argparse, collections, functools, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import master_filelist as mf  # noqa: E402

mf.index = functools.lru_cache(maxsize=None)(mf.index)
WNO = ['TIMESCALEMOD', 'WIDTH', 'UNUSED', 'PINCONNECTEMPTY', 'DECLFILENAME', 'UNDRIVEN', 'UNOPTFLAT', 'CASEINCOMPLETE',
       'PINMISSING', 'MULTIDRIVEN', 'COMBDLY', 'STMTDLY', 'INITIALDLY', 'BLKANDNBLK', 'MODDUP', 'LITENDIAN', 'SELRANGE',
       'IMPLICIT', 'CASEOVERLAP', 'SYMRSVDWORD', 'REALCVT', 'ASSIGNDLY', 'GENUNNAMED', 'VARHIDDEN']
# masters whose owner elaborates a pinned source set (several modules share a name across generations): prefer it
PREFER = {
    'ot_hgi_sfu_scheduled_engine': [l.strip() for l in (ROOT / 'results/arch/hbm_native_1013/sfu_native_quarter/r2_sources.txt')
                                    .read_text().splitlines() if l.strip() and '/test/' not in l],
    'hfd_ckgen': ['rtl/hbm_accel/control/ot_hbm_pll_bb.sv'],
    'ot_hbm_lk_ep': ['rtl/hbm_accel/tu/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv'],
}
RD = '/srv/opentallas-scratch/claude/hnetlist-lint'
# elaboration defines of the die build: the static SM front instantiates the hardened front_c sub-elements (die_case.py
# synthesises the SM with -DOT_SMH_FC_HIER; without it ot_smh_static_front has no fc_* definitions)
DEFINES = ['OT_SMH_FC_HIER']


# RTL the resolver's SKIP list hides but die masters instantiate (the PC controller's r14 sequencer; synth_master.sh
# passes it as EXTRA the same way)
EXTRA_DIRS = ['rtl/model_ready_hbm_r14']


def closure(c):
    per, amb, unres = {}, {}, {}
    for d in EXTRA_DIRS:
        for f in sorted((ROOT / d).glob('*.sv')):
            if f.name.startswith('tb_'):
                continue
            rel = str(f.relative_to(ROOT))
            for _, name in mf.DEF.findall(mf.strip(f.read_text(errors='replace'))):
                if rel not in mf.index(ROOT).setdefault(name, []):
                    mf.index(ROOT)[name].append(rel)
    for m in sorted(c['masters']):
        src = next(i['source'] for i in c['instances'].values() if i['master'] == m)
        if src.endswith('_bb.v'):
            per[m] = dict(files=[], macros=[src]); continue
        deps = next((i.get('rtl_deps', []) for i in c['instances'].values() if i['master'] == m), [])
        kits = ([src] if src not in mf.index(ROOT).get(m, []) else []) + list(deps)
        for kit in kits:   # a master (or a child, rtl_deps) defined outside the resolver's roots (physical/<kit>/):
            for f in sorted((ROOT / kit).parent.glob('*.sv')):   # index its kit directory (sibling leaves)
                rel = str(f.relative_to(ROOT))
                if f.name.startswith('tb_'):
                    continue
                for _, name in mf.DEF.findall(mf.strip(f.read_text(errors='replace'))):
                    if rel not in mf.index(ROOT).setdefault(name, []):
                        mf.index(ROOT)[name].append(rel)
        r = mf.resolve(ROOT, m, (), [src] + PREFER.get(m, []))
        per[m] = dict(files=r['files'], macros=[x['file'] for x in r['macros']])
        amb.update(r['ambiguous'])
        if r['unresolved']:
            unres[m] = r['unresolved']
    return per, amb, unres


def collisions(per):
    defs = collections.defaultdict(lambda: collections.defaultdict(set))
    for m, v in per.items():
        for f in v['files']:
            for _, name in mf.DEF.findall(mf.strip((ROOT / f).read_text(errors='replace'))):
                defs[name][f].add(m)
    out = {}
    for name, fs in defs.items():
        if len(fs) > 1 and len({mf.body(ROOT, f, name) for f in fs}) > 1:
            out[name] = {f: sorted(ms) for f, ms in fs.items()}
    return out


def port_decl(c, m):
    ii = [x for x in c['instances'].values() if x['master'] == m]
    i = ii[0]
    prm = sorted({k for x in ii for k in x['params']})
    pd = ('#(' + ', '.join(f'parameter {k} = 0' for k in prm) + ') ') if prm else ''
    ps = ', '.join(f"{d['direction']} wire [{d['bits'] - 1}:0] {p}" for p, d in i['ports'].items())
    return f'// LINT HARNESS ONLY (not die RTL): port declaration of {m}, linted alone with its own closure\n' \
           f'(* blackbox *) module {m} {pd}({ps}); endmodule\n'


def run(cmd_files, top, extra, od, tag, remote, die_v=None):
    files = []
    for f in cmd_files:
        if f not in files:
            files.append(f)
    inc = sorted({str(Path(f).parent) for f in files})
    fl = od / f'{tag}.f'
    fl.write_text('\n'.join([f'+define+{d}' for d in DEFINES] + [f'+incdir+{d}' for d in inc] + files) + '\n')
    tail = [str(x.name) for x in extra] + ([die_v.name] if die_v else [])
    cmd = ['verilator', '--lint-only', '-Wall', '-Wno-fatal'] + [f'-Wno-{w}' for w in WNO] + ['--top-module', top, '-f', fl.name] + tail
    if remote:
        rd = f'{RD}/{tag}'
        lst = od / f'{tag}.rsync'
        lst.write_text('\n'.join(sorted(set(files + [str(Path(d) / x.name) for d in inc for x in (ROOT / d).glob('*.svh')]
                                            + [str(Path(d) / x.name) for d in inc for x in (ROOT / d).glob('*.vh')]))) + '\n')
        subprocess.run(['ssh', remote, f'rm -rf {rd} && mkdir -p {rd}'], check=True)
        subprocess.run(['rsync', '-a', '--files-from', str(lst), str(ROOT) + '/', f'{remote}:{rd}/'], check=True)
        subprocess.run(['rsync', '-a', str(fl)] + [str(x) for x in extra] + ([str(die_v)] if die_v else []) + [f'{remote}:{rd}/'], check=True)
        r = subprocess.run(['ssh', remote, f'cd {rd} && ' + ' '.join(cmd)], capture_output=True, text=True)
    else:
        fl.write_text('\n'.join([f'+define+{d}' for d in DEFINES] + [f'+incdir+{ROOT / d}' for d in inc] + [str(ROOT / f) for f in files]) + '\n')
        cmd = cmd[:-len(tail)] + [str(x) for x in extra] + ([str(die_v)] if die_v else []) if tail else cmd
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=od)
    log = r.stdout + r.stderr
    (od / f'{tag}.log').write_text(' '.join(cmd) + '\n' + log)
    errs = [l for l in log.splitlines() if l.startswith('%Error')]
    warns = collections.Counter(re.match(r'%Warning-(\w+)', l).group(1) for l in log.splitlines() if re.match(r'%Warning-\w+', l))
    return dict(tag=tag, top=top, files=len(files), returncode=r.returncode, errors=len(errs), error_lines=errs[:40],
                warnings=dict(warns), verdict='PASS' if r.returncode == 0 and not errs else 'FAIL')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('die_dir', type=Path)
    ap.add_argument('--top', default='hbm_v16_die')
    ap.add_argument('--remote', help='ssh host with Verilator 5.x (the SU lanes carry /*verilator hier_block*/)')
    a = ap.parse_args()
    a.die_dir = a.die_dir.resolve()
    c = json.loads((a.die_dir / 'contract.json').read_text())
    per, amb, unres = closure(c)
    col = collisions(per)
    alone = set()                      # colliding minority, per collided module: masters on the smaller side
    for name, fs in col.items():
        for g in sorted(fs.values(), key=len)[:-1]:
            alone |= set(g)
    od = a.die_dir / 'lint'
    od.mkdir(exist_ok=True)
    harness = od / 'harness_portdecl.v'
    harness.write_text(''.join(port_decl(c, m) for m in sorted(alone)))
    main_files = [f for m, v in per.items() if m not in alone for f in v['macros'] + v['files']]
    ver = subprocess.run((['ssh', a.remote] if a.remote else []) + ['verilator', '--version'], capture_output=True, text=True).stdout.strip()
    parts = [run(main_files, a.top, [harness] if alone else [], od, 'die_main', a.remote, a.die_dir / 'die.v')]
    for m in sorted(alone):
        parts.append(run(per[m]['macros'] + per[m]['files'], m, [], od, f'alone_{m}', a.remote))
    rec = dict(schema='opentallas.hbm_v16.lint.v2', tool=ver, host=a.remote or 'local', top=a.top, masters=len(per),
               files=len({f for v in per.values() for f in v['files']}), module_name_collisions=col,
               linted_alone=sorted(alone), defines=DEFINES, ambiguous_definitions_resolved=amb, unresolved_modules=unres, partitions=parts,
               verdict='PASS' if all(p['verdict'] == 'PASS' for p in parts) and not unres else 'FAIL',
               full_flat_elaboration='BLOCKED by module-name collisions (owners must uniquify)' if col else 'one partition')
    (od / 'closure.json').write_text(json.dumps(per, indent=1) + '\n')
    (od / 'lint.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f"LINT {rec['verdict']} masters={len(per)} collisions={len(col)} alone={sorted(alone)} unresolved={len(unres)}")
    for p in parts:
        print(f"  {p['tag']}: {p['verdict']} files={p['files']} errors={p['errors']} warnings={p['warnings']}")
        for e in p['error_lines'][:10]:
            print('   ', e[:240])
    return 0 if rec['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
