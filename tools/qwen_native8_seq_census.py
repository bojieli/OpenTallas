#!/usr/bin/env python3
"""Source-bound native8 retained-state census; run synthesis only via ot-run.

This counts generic retained FF bits and clock roots before cell mapping/CTS.
It does not provide sink characterization, timing, placement, or physical slots.
"""
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

TOP = 'ot_qfd_seq_su_bi_native8_candidate'
SOURCES = [
    'rtl/physical/ot_qfd_seq_su_bi_native8_candidate.sv',
    'rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv',
    'rtl/rom/ot_qwen_tp_seq_w12.sv',
    'rtl/rom/ot_rom_pkg_link.sv',
    'rtl/rom/ot_rom_pkg_ctrl.sv',
    'rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv',
    'rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv',
    'rtl/hdc/ot_hdc_delay.sv',
    'rtl/hdc/ot_hdc_dyn_ttiles.sv',
    'rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv',
    'rtl/hdc/ot_hdc_cg.sv',
]
MACRO = ('physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/'
         'ot_sram_1r1w_64x512_m1_r2c2.v')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value):
    return int(value, 2) if isinstance(value, str) else int(value)


def census(path):
    mods = json.loads(path.read_text())['modules']
    roots = collections.Counter()
    rows, macros, unsupported = [], [], []

    def walk(name, scope, incoming):
        m = mods[name]
        resolve = lambda b: incoming.get(b, scope + ':' + str(b)) if isinstance(b, int) else str(b)
        row = {'instance': scope, 'module': name, 'local_ff_bits': 0,
               'local_memories': [], 'clock_ff_bits': collections.Counter()}
        for cname, c in m.get('cells', {}).items():
            typ, conn = c['type'], c.get('connections', {})
            if typ in mods and not number(mods[typ].get('attributes', {}).get('blackbox', 0)):
                imap = {}
                for pname, port in mods[typ].get('ports', {}).items():
                    for cb, pb in zip(port['bits'], conn.get(pname, [])):
                        if isinstance(cb, int):
                            imap[cb] = resolve(pb)
                walk(typ, scope + '/' + cname, imap)
            elif typ in mods:
                macros.append({'instance': scope + '/' + cname, 'type': typ,
                               'clock': [resolve(b) for b in conn.get('clk', [])]})
            elif typ.startswith('$mem'):
                p = c['parameters']
                if typ == '$mem_v2':
                    row['local_memories'].append({'name': cname, 'bits': number(p['WIDTH']) * number(p['SIZE']),
                                                 'width': number(p['WIDTH']), 'words': number(p['SIZE']),
                                                 'write_clocks': [resolve(b) for b in conn.get('WR_CLK', [])]})
            elif ('ff' in typ.lower() or typ.startswith('$_DFF')) and 'Q' in conn:
                clk = conn.get('CLK', conn.get('C', []))
                if len(clk) != 1:
                    unsupported.append({'instance': scope + '/' + cname, 'type': typ, 'clock_bits': clk})
                    continue
                width = len(conn['Q'])
                key = resolve(clk[0])
                row['local_ff_bits'] += width
                row['clock_ff_bits'][key] += width
                roots[key] += width
            elif 'latch' in typ.lower():
                unsupported.append({'instance': scope + '/' + cname, 'type': typ})
        row['clock_ff_bits'] = dict(row['clock_ff_bits'])
        rows.append(row)

    walk(TOP, TOP, {b: pname for pname, p in mods[TOP]['ports'].items() for b in p['bits']})
    return {'total_generic_ff_bits': sum(roots.values()), 'clock_ff_bits': dict(roots),
            'instances': rows, 'blackbox_macros': macros, 'unsupported_state': unsupported}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--psram', type=int, choices=[0, 1], required=True)
    ap.add_argument('--yosys', default=str(Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    params = {'G': 3072, 'D': 8, 'NW': 18, 'SW': 64, 'CRED': 32, 'RB': 3,
              'IS': 1, 'OS': 1, 'RT': 4, 'PSRAM': a.psram, 'RRG': 0,
              'PCUT': 0, 'OLAG': 0, 'HQ2': 0, 'PMUT': 0, 'RLY': 0}
    # Defer elaboration: eager processing plus top parameter overrides causes
    # Yosys to rederive the controller before its shared helper is available.
    script = 'read_verilog -defer -sv -D SYNTHESIS ' + ' '.join(SOURCES) + '\n'
    script += 'read_verilog -lib -sv ' + MACRO + '\n'
    script += 'hierarchy -check -top ' + TOP + ' ' + ' '.join('-chparam %s %d' % p for p in params.items()) + '\n'
    script += 'proc\nopt\nmemory_dff\nmemory_collect\nopt_clean\n'
    script += 'write_json ' + str(a.out / 'retained.json') + '\n'
    script += 'memory_map\nopt\nstat\nwrite_json ' + str(a.out / 'mapped.json') + '\n'
    yp = a.out / 'census.ys'
    yp.write_text(script)
    with (a.out / 'yosys.log').open('w') as log:
        run = subprocess.run([a.yosys, '-s', str(yp)], stdout=log, stderr=subprocess.STDOUT)
    if run.returncode:
        raise SystemExit(run.returncode)
    result = {'schema': 'opentallas.native8.sequencer-retained-census.v1',
              'source_commit': '4fb280f39', 'top': TOP, 'parameters': params,
              'source_sha256': {p: sha(p) for p in [*SOURCES, MACRO]},
              'census_script_sha256': sha(__file__), 'yosys_script_sha256': sha(yp),
              'retained': census(a.out / 'retained.json'),
              'mapped': census(a.out / 'mapped.json'),
              'physical_qualified': False, 'slots_assigned': False,
              'clock_sink_rule': 'Generic FF bit counts are a source census, not cell-mapped clock sinks. New roots require <=15000 actual sinks or measured CTS insertion<=300ps/spread<=80ps.',
              'legacy_closed_alias_used': False, 'CROM_latency_or_VL_adoption': False}
    (a.out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'psram': a.psram, 'mapped_generic_ff_bits': result['mapped']['total_generic_ff_bits'],
                      'mapped_clock_ff_bits': result['mapped']['clock_ff_bits'],
                      'macros': len(result['mapped']['blackbox_macros']), 'physical_qualified': False}))


if __name__ == '__main__':
    main()
