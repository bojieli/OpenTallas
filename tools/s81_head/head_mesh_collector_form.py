#!/usr/bin/env python3
"""Experimental MESH collector DSREP8/band-spread form; no plan adoption or P&R."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def source_complete(kit, typ, published, out):
    """Use the accepted HEAD constructors, retaining the exact published cohort."""
    sys.path[:0] = [str(ROOT / 'tools/s81_head'), str(ROOT / 'tools/die_plan')]
    from head_start_reset_aliases import patch_rtl as alias_patch
    from head_start_raw_private import patch_rtl as private_patch
    from head_wave_kit_rtl import tokens
    out.mkdir()
    wrapper_name = typ['module'] + '.sv'
    text = alias_patch((kit / 'rtl' / wrapper_name).read_text(), typ['reset_start_raw_exports'])
    if text.count(', .DSREP(8)') != 2 or text.count('#(.BQ(10), .RBL(1))') != 1:
        raise ValueError('expected exactly two DSREP8 rings and the RBL1/BQ10 parent')
    normalized = text.replace(', .DSREP(8)', '').replace('#(.BQ(10), .RBL(1))', '#(.BQ(2))')
    if tokens(normalized) != tokens(gzip.decompress(published.read_bytes()).decode()):
        raise ValueError('native source cohort changed beyond declared RBL/BQ/DSREP')
    text, private = private_patch(text, typ)
    cfg = (kit / 'config.mk').read_text().replace('\\\n', ' ')
    values = re.findall(r'^export VERILOG_FILES\s*=\s*(.*)$', cfg, re.M)
    if len(values) != 1 or '$' in values[0]:
        raise ValueError('source closure needs one literal VERILOG_FILES')
    files = []
    for value in values[0].split():
        src = kit / value.removeprefix('/work/') if value.startswith('/work/') else Path(value)
        dest = out / src.name
        if dest.exists():
            raise ValueError('duplicate source basename: ' + src.name)
        shutil.copy2(src, dest)
        files.append(dest.resolve())
    wrapper = out / wrapper_name
    if files.count(wrapper.resolve()) != 1:
        raise ValueError('partition wrapper absent from exact source closure')
    wrapper.write_text(text)
    files = [wrapper.resolve()] + [p for p in files if p != wrapper.resolve()]
    filelist = out / 'kit_rtl.f'
    filelist.write_text(''.join(str(p) + '\n' for p in files))
    (out / 'constructor.json').write_text(json.dumps(dict(
        normalized_published_tokens_equal=True, declared_changes=['RBL1', 'BQ10', 'DSREP8'],
        private_raw=private, added_pin_cycles=0), indent=2) + '\n')
    return filelist


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    por = ROOT / 'physical/die_plan/s81_head/plan_of_record/l48ve'
    plan = json.loads(gzip.decompress((por / 'source_plan.json.gz').read_bytes()))
    side = gzip.decompress((por / 'source_sidecar.json.gz').read_bytes())
    typ = plan['partition_types']['hd_mesh']
    typ['contents'][0]['params'].update(RBL='1', BQ='10')
    typ['clock']['landing_ring_dsrep'] = {'buses': ['coll_ia', 'coll_ib'], 'dsrep': 8}
    # Preserve the exact published census/assets while moving this private plan.
    def relocate(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and v.startswith(('native_domains/', 'assets/', 'core_pins/')):
                    obj[k] = str(por / v)
                else:
                    relocate(v)
        elif isinstance(obj, list):
            for v in obj:
                relocate(v)
    relocate(plan)
    pin = out / 'source_plan.json'
    pin.write_text(json.dumps(plan, indent=1))
    sidepath = out / 'source_sidecar.json'
    sidepath.write_bytes(side)
    def run(*args):
        name = ('band_spread.log' if str(args[0]).endswith('ring_band_spread.py') else
                'gen_phys_source_complete.log' if '--kit-rtl' in args else 'gen_phys.log')
        with (out / name).open('w') as log:
            subprocess.run([sys.executable, '-I', *map(str, args)], check=True, env=env,
                           stdout=log, stderr=subprocess.STDOUT)
    env = dict(os.environ, OT_CONS_KIT='1', OT_CONS_UTIL='0.35',
               OT_CONS_MAX_LAYER='M6', OT_SKIP_PRECTS_METRICS='1', OT_FSM_NONE_WIRES='hunt')
    run(ROOT / 'tools/die_plan/ring_band_spread.py', pin, sidepath,
        out / 'plan.json', out / 'spread_report.json', '--types', 'hd_mesh', '--spread', '7',
        '--bisect', '--tag', 'CODEX-HEAD-MESH-1113')
    # Official generator keeps all independent contracts, lint, LEC and physical gates.
    run(ROOT / 'tools/die_plan/gen.py', 'phys', out / 'plan.json', '--out', out / 'kits',
        '--rtl-root', ROOT, '--types', 'hd_mesh', '--clock-landing', sidepath,
        '--util', '0.35', '--max-wire-um', '80', '--hold-ff-margin', '15',
        '--cland-pinslot', 'hd_mesh', '--trial')
    readset = source_complete(out / 'kits/hd_mesh', typ,
        por / 'published/ot_s81hd_mesh_ep.sv.gz', out / 'source_complete')
    run(ROOT / 'tools/die_plan/gen.py', 'phys', out / 'plan.json', '--out', out / 'kits_source_complete',
        '--rtl-root', ROOT, '--types', 'hd_mesh', '--clock-landing', sidepath,
        '--kit-rtl', 'hd_mesh=' + str(readset), '--util', '0.35', '--max-wire-um', '80',
        '--hold-ff-margin', '15', '--cland-pinslot', 'hd_mesh', '--trial')
    kit = out / 'kits_source_complete/hd_mesh'
    for name in ('DO_NOT_COUNT', 'HOLD_ROUTE', 'HOLD_CTS'):
        (kit / name).write_text('Experimental collector form: inspect actual PLACE before any later stage.\n')
    (out / 'calendar.json').write_text(json.dumps({
        'compared_to': 'existing RBL1/BQ10 vA/vB', 'added_pin_cycles': 0,
        'existing_RBL_TX_pin_cycles': 1, 'RX_pin_cycles': 0,
        'adoption': 'NONE', 'release_eligible': False}, indent=2) + '\n')
    print(kit)


if __name__ == '__main__':
    main()
