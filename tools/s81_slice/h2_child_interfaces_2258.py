#!/usr/bin/env python3
"""Read current emitted LP child ABIs; no elaboration, RTL or geometry changes."""
import argparse, hashlib, json, re, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--repo', required=True)
ap.add_argument('--kits', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()
repo = Path(a.repo)
sys.path.insert(0, str(repo / 'tools'))
from die_port_bind import parse_modules

masters = {'dsfd_coll_lane_w_safe8_ntf', 'dsfd_coll_lane_e_safe8_ntf',
           'ot_s81_mu72_lnland', 'ot_s81_mu72_lnland_nst'}
records = {}
instances = []
for outer in sorted(Path(a.kits).glob('dsdv_slice_*_LP__t*')):
    kit = outer / outer.name
    if not (kit / 'config.mk').exists():
        continue
    config = (kit / 'config.mk').read_text()
    defines = re.search(r'^export VERILOG_DEFINES = (.*)$', config, re.M).group(1).split()
    sources = {}
    for src in (kit / 'rtl').glob('*.sv'):
        text = src.read_text()
        if not any(re.search(r'\bmodule\s+' + re.escape(m) + r'\b', text) for m in masters):
            continue
        for mod in parse_modules(text, str(src)):
            if mod.name not in masters:
                continue
            assert not mod.port_parse_errors, mod.port_parse_errors
            ports = {n: dict(direction=mod.ports[n][0], bits=mod.width(n, mod.env())) for n in mod.order}
            source_sha = hashlib.sha256(src.read_bytes()).hexdigest()
            if mod.name in records:
                assert records[mod.name]['ports'] == ports, (mod.name, 'ABI differs')
                assert records[mod.name]['source_sha256'] == source_sha, (mod.name, 'source differs')
            else:
                ln = mod.name.startswith('ot_s81_mu72_lnland')
                records[mod.name] = dict(ports=ports, source_sha256=source_sha, source=str(src),
                    parameter_values={'MUT': 0} if ln else {'CORE_CRED': 12},
                    clock_pins=['ck_k', 'ck_n'] if ln else ['ck[0]'],
                    reset_pins=['rs_k', 'rs_n'] if ln else ['rs[0]'], defines=defines)
            sources[mod.name] = source_sha
    bound = next((kit / 'rtl').glob('*_bound.sv'))
    text = bound.read_text()
    for match in re.finditer(r'\b(' + '|'.join(sorted(masters)) + r')\s*#\((.*?)\)\s+(\w+)\s*\((.*?)\n\s*\);', text, re.S):
        master, params, inst, conn = match.groups()
        conns = dict(re.findall(r'\.(\w+)\(([^()]*)\)', conn))
        if master.startswith('ot_s81_mu72_lnland'):
            assert conns['ck_k'] == conns['ck_n'] == 'clk', (kit, inst, conns)
            assert conns['rs_k'] != conns['rs_n'], (kit, inst, 'independent resets unexpectedly collapsed')
        instances.append(dict(type=outer.name, master=master, instance=inst,
                              parameter_text=params, connections=conns))
assert set(records) == masters, (set(records), masters)
assert len(instances) == 28, len(instances)

domains = {
    'K': dict(ports=['ck_k'], inputs=['rs_k','k_lo_v','k_lo_d','k_li_r','k_rxv'],
              outputs=['k_lo_r','k_li_v','k_li_d','k_flt']),
    'N': dict(ports=['ck_n'], inputs=['rs_n','n_lo_r','n_li_v','n_li_d','n_flt'],
              outputs=['n_lo_v','n_lo_d','n_li_r','n_rxv'])}
for master, record in records.items():
    if not master.startswith('ot_s81_mu72_lnland'):
        continue
    dd = json.loads(json.dumps(domains))
    if master == 'ot_s81_mu72_lnland':
        dd['K']['outputs'].append('k_st')
        dd['N']['inputs'].append('n_st')
    buses = [b for d in dd.values() for k in ('inputs','outputs') for b in d[k]]
    assert len(buses) == len(set(buses))
    assert set(buses) == set(record['ports']) - {'ck_k','ck_n'}
    record['spec_clock_contract'] = dict(clock_port='ck_k', clock_ports=['ck_k','ck_n'],
        clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[1,1],phase_ps=0),
        clock_data_paths='related_same_frequency',clock_entry_domains=dd)
    record['recipe_required'] = dict(multi_root=True, insertion_balance=True)
    record['physical_entry_obligation'] = 'Two distinct plan clock-pin sites, one per root; both parent nets are clk. Preserve independent rs_k/rs_n.'

out = dict(scope='CURRENT_EMITTED_SOURCE_ONLY; geometry and timing not assigned',
           source_event='1dfae74037a', masters=records, instances=instances,
           added_data_cycles=0, generated_rtl_wrapper=False,
           limits=['No new elaboration or physical qualification', 'No merged clock or reset pins',
                   'Define sets retained from actual emitted kits; generator recipe must preserve them'])
Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(dict(masters=len(records), instances=len(instances), clocks='all LN ck_k=ck_n=parent clk',
                      resets='independent', verdict='PASS source ABI')))
