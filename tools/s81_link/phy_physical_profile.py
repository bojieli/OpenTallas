#!/usr/bin/env python3
"""Model actual legacy KP4 pin stages; keep functional models separate from P&R.

The renamed physical masters refer to the actual legacy digital views. They are
not newly qualified views. Analog placement/orientation remains a separate issue.
"""
from pathlib import Path
import argparse
import json
import re
import sys

LEAVES = ('dsyn', 'ddly', 'dchn', 'dout', 'enc')


def prepare(root, out):
    root, out = Path(root), Path(out)
    (out / 'rtl').mkdir(parents=True, exist_ok=True)
    (out / 'sim').mkdir(exist_ok=True)
    sys.path.insert(0, str(root / 'tools/landed_parent'))
    import lp
    aliases, wrappers, contracts = {}, [], {}
    for leaf in LEAVES:
        name = 'ot_s81_kp4_' + leaf
        alias = name + '_physical_pinmodel'
        view = root / 'physical/ref_tile' / ('s81lk_kp4_' + leaf) / 'views' / name
        ports = json.loads((view / 'port_latency.json').read_text())['ports']
        mod = lp.parse_module(lp.preprocess((root / f'rtl/dsrom_sys/s81_link/{name}.sv').read_text(), []), name)
        decl, body, con = [], [], []
        for p in mod['ports']:
            n, rng = p['name'], p['range'] or ''
            direction = {'in': 'input', 'out': 'output'}[p['dir']]
            decl.append(f'{direction} wire {rng} {n}')
            expected = 0 if n in ('clk', 'rst_n') else 1
            if ports[n]['register_edges'] != expected:
                raise ValueError(f'{name}.{n}: legacy physical register count changed')
            if expected == 0:
                con.append(f'.{n}({n})')
                continue
            body.append(f'wire {rng} pin_{n};')
            d, q = (n, 'pin_' + n) if p['dir'] == 'in' else ('pin_' + n, n)
            body.append(f'ot_pl_pad #(.W({lp.width_text(p["range"])}),.N(1)) u_pin_{n} (.ck(clk),.d({d}),.q({q}));')
            con.append(f'.{n}(pin_{n})')
        body.append(name + ' u_real (' + ', '.join(con) + ');')
        wrappers.append('module ' + alias + '(\n' + ',\n'.join(decl) + '\n);\n' + '\n'.join(body) + '\nendmodule\n')
        aliases[name] = alias
        contracts[name] = {n: p['register_edges'] for n, p in ports.items()}
    rm = json.loads((root / 'physical/ref_tile/s81lk_rate_match/pin_regs.json').read_text())
    if rm['enable']:
        raise ValueError('rate-match extra pin stages need an explicit dual-clock model')
    parent = (root / 'rtl/dsrom_sys/s81_link/lp/ot_s81_kp4_dec_native_flat_lp.sv').read_text()
    parent = parent.replace('module ot_s81_kp4_dec_native_flat_lp #', 'module ot_s81_kp4_dec_native_flat_lp_physical #')
    for name, alias in aliases.items():
        if not name.endswith('_enc'):
            parent = re.sub(r'\b' + name + r'\b', alias, parent)
    col = (root / 'rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv').read_text()
    col = col[:col.index('endmodule') + len('endmodule')] + '\n'
    col = col.replace('module ot_pdie_serdes_col #', 'module ot_pdie_serdes_col_physical_profile #')
    col = col.replace('ot_s81_kp4_enc u_enc', aliases['ot_s81_kp4_enc'] + ' u_enc')
    col = col.replace('ot_s81_kp4_dec_native_flat_lp #', 'ot_s81_kp4_dec_native_flat_lp_physical #')
    (out / 'rtl/ot_pdie_serdes_col.sv').write_text(col)
    (out / 'rtl/ot_s81_kp4_dec_native_flat_lp.sv').write_text(parent)
    (out / 'sim/physical_pinmodels.sv').write_text('// SIMULATION ONLY: P&R uses actual renamed digital hard views.\n' + '\n'.join(wrappers))
    record = dict(top='ot_pdie_serdes_col_physical_profile', aliases=aliases, port_register_edges=contracts,
                  rate_match_added_edges=0, decoder_added_edges=dict(q=6, lock=2, n_relock=2, n_corr=4, n_unc=4),
                  encoder_contract='input+1/output+1; simulate actual frame phase, not a global raw-PMA shift',
                  physical_qualified=False, claim='actual legacy digital view aliases; current sign-off still required')
    (out / 'physical_profile.json').write_text(json.dumps(record, indent=1) + '\n')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    prepare(Path(__file__).resolve().parents[2], a.out)
