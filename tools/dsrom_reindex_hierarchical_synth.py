#!/usr/bin/env python3
"""Prepare attribute-preserving literal-quarter/shared-parent synthesis cuts.

Preparation and interface checks are cheap. Execute frontends/mapping only on
an admitted host. This does not alter/restart R9, map a flat64 scorer, fabricate
macro abstracts, allocate a floorplan, or confer timing/numerical qualification.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

from dsrom_reindex_parent_model import hierarchical_parent_join_model
from dsrom_reindex_native_quarter_gate import RTL, FROZEN_SCORER

ROOT = Path(__file__).resolve().parents[1]
PARENT = 'rtl/dsrom_sys/reindex_parent/ot_dsrom_reindex_hierarchical_parent.sv'
QUARTER = RTL[0]
SHARED = 'rtl/dsrom_sys/integration/ot_dsrom_reindex_chain.sv'
QTOP = 'ot_dsrom_reindex_native_quarter'
STOP = 'ot_dsrom_reindex_chain'
PTOP = 'ot_dsrom_reindex_hierarchical_parent'
QMAP = 'ot_dsrom_reindex_quarter_mapped'
SMAP = 'ot_dsrom_reindex_shared_mapped'


def interface(path):
    text = path.read_text()
    start = re.search(r'^module\s+', text, re.M).start()
    end = re.search(r'^\s*\);', text[start:], re.M).end() + start
    # Ubuntu's old Yosys treats parameter bit as a reg declaration. This
    # interface-only normalization changes neither width nor default value.
    return text[start:end].replace('parameter bit ', 'parameter integer ') + '\nendmodule\n'


def prepare(out):
    out.mkdir(parents=True, exist_ok=False)
    native = [s for s in RTL if '/tb_' not in s]
    old = json.loads((ROOT / 'results/rtl/dsrom_reindex_parent_20261005/'
                     'integration_r9_PASS/record.json').read_text())['sha256']
    shared = [s for s in old if s.endswith('.sv') and '/tb_' not in s
              and '/wavefront/' not in s]
    shared += ['physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/'
               'ot_sram_1r1w_512x128_m4_r2c2_bb.v']
    source = sorted(set(native + shared + [PARENT, 'tools/run_abi3_physical.py',
                     'tools/orfs_allcorner_spef.py',
                     'tools/dsrom_reindex_hierarchical_synth.py',
                     'tools/dsrom_reindex_parent_model.py']))
    pins = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in source}
    assert pins['rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv'] == FROZEN_SCORER
    for s in shared:
        if s in old:
            assert pins[s] == old[s], 'Changed accepted shared source: ' + s
    for name, paths, top, mapped, parameters in (
            ('quarter', native, QTOP, QMAP, '-chparam ENABLE 1'),
            ('shared', shared, STOP, SMAP, '-chparam OPT_REINDEX_PARENT 1')):
        # These are frontends, not standalone mapped/P&R verdicts. Mapping
        # must use actual corner libraries and the existing admitted flow.
        commands = [f'read_verilog -sv {ROOT / s}' for s in paths]
        commands += [f'hierarchy -check -top {top} {parameters}', 'proc',
                     'opt_clean', f'rename {top} {mapped}',
                     f'write_rtlil {out / (name + "_frontend.il")}',
                     f'write_verilog {out / (name + "_frontend.v")}']
        (out / (name + '_frontend.ys')).write_text('\n'.join(commands) + '\n')
    # Resolve only the two synthesis partition names in the NEW wrapper.
    # All original quarter/scorer/chain RTL stays byte-identical.
    link = (ROOT / PARENT).read_text()
    link, n = re.subn(r'ot_dsrom_reindex_chain\s*#\(.*?\)\s*u_shared',
                     SMAP + ' u_shared', link, flags=re.S)
    assert n == 1
    link, n = re.subn(r'ot_dsrom_reindex_native_quarter\s*#\(\.ENABLE\(1\)\)\s*u_native',
                     QMAP + ' u_native', link)
    assert n == 1
    (out / 'parent_link.sv').write_text(link)
    (out / 'link_mapped.ys').write_text('\n'.join([
        f'read_verilog {out / "quarter_mapped.v"}',
        f'read_verilog {out / "shared_mapped.v"}',
        f'read_verilog -sv {out / "parent_link.sv"}',
        f'hierarchy -check -top {PTOP} -chparam ENABLE 1',
        'proc', 'opt_clean', 'check -assert', 'stat',
        f'write_json {out / "linked_mapped.json"}',
        f'write_verilog {out / "linked_mapped.v"}']) + '\n')
    # Only source-extracted interface stubs are used in the local wire audit.
    # They never enter a mapped export or a timing/P&R command.
    (out / 'interface_only.sv').write_text(interface(ROOT / QUARTER) + interface(ROOT / SHARED))
    record = dict(model=hierarchical_parent_join_model(), source_sha256=pins,
                  synthesis_partitions=dict(literal_quarter_instances=4,
                      literal_quarter_unique_builds=1, shared_winner_retention_instances=1),
                  mapped_export_rule='Preserve attributes through intermediate exports; no write_verilog -noattr.',
                  shared_retention='All existing u_sel/lm/rep_pend/ks_out/sc_in/empty_due/j_slot retained in original chain. No perquarter winner clones or retention blackboxes.',
                  mutable_selector_memory='Original chain lm retained; protection/macro qualification still open, no parity waiver.',
                  R9_reused=True, passing_native_gate_replayed=False,
                  admitted_frontend_launched=False, mapped=False, parent_qualified=False)
    (out / 'preparation.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def verify_connections(path, mapped=False):
    modules = json.loads(path.read_text())['modules']
    top = modules[PTOP]
    cells = top['cells']
    qtype, stype = (QMAP, SMAP) if mapped else (QTOP, STOP)
    qs = sorted((n, c) for n, c in cells.items() if qtype in c['type'])
    ss = [(n, c) for n, c in cells.items() if stype in c['type']]
    assert len(qs) == 4 and len(ss) == 1 and len(cells) == 5
    shared = ss[0][1]['connections']
    topports = {n: p['bits'] for n, p in top['ports'].items()}
    for q, (name, cell) in enumerate(qs):
        assert f'g_quarter[{q}]' in name
        c = cell['connections']
        for port, width in [('ks_valid', 1), ('ks_ready', 1), ('ks_last', 1),
                            ('ks_lv', 16), ('ks_key', 8704), ('ks_idx', 320),
                            ('sc_valid', 1), ('sc_ready', 1), ('sc_last', 1),
                            ('sc_lv', 16), ('sc_val', 256), ('sc_idx', 320)]:
            assert c[port] == shared[port][q*width:(q+1)*width], (q, port)
        for port, width in [('ql_v', 1), ('ql_ready', 1), ('ql_head', 8),
                            ('ql_codes', 512), ('ql_sc', 32), ('ql_w', 16), ('ks_ref', 16)]:
            assert c[port] == topports[port][q*width:(q+1)*width], (q, port)
        for port, public, width in [('sc_fault', 'score_fault', 16),
                                    ('protocol_fault', 'scorer_protocol_fault', 1)]:
            assert c[port] == topports[public][q*width:(q+1)*width]
        assert c['clk'] == shared['clk'] == topports['clk']
        assert c['rst_n'] == shared['rst_n'] == topports['rst_n']
    # Source timing/protection bodies are checked only for a REAL mapped link.
    if mapped:
        for typ in {c['type'] for c in cells.values()}:
            assert not int(str(modules[typ].get('attributes', {}).get('blackbox', '0')), 2)
            assert modules[typ]['cells'], 'Empty mapped partition body: ' + typ
    return dict(quarters=4, keys=64, IW=20, shared_winner_retention_bodies=1,
                all_key_score_ID_query_ref_ready_clock_bits_connected=True,
                top_added_state=0, interface_only=not mapped, physical_qualified=False)


def wire_check(out):
    log = out / 'interface_yosys.log'
    script = '\n'.join([
        f'read_verilog -lib -sv {out / "interface_only.sv"}',
        f'read_verilog -sv {ROOT / PARENT}',
        f'hierarchy -check -top {PTOP} -chparam ENABLE 1',
        'proc', 'opt_clean', 'check -assert', f'write_json {out / "interface.json"}'])
    with log.open('w') as f:
        subprocess.run(['yosys', '-Q', '-T', '-p', script], stdout=f,
                       stderr=subprocess.STDOUT, check=True)
    result = verify_connections(out / 'interface.json')
    # Changed integration only: reject a crossed full-ID lane and a borrowed
    # neighboring quarter credit. This never invokes the accepted native gate.
    original = json.loads((out / 'interface.json').read_text())
    negatives = []
    for port in ('ks_idx', 'ks_ready'):
        bad = copy.deepcopy(original)
        cells = bad['modules'][PTOP]['cells']
        quarters = sorted((n, c) for n, c in cells.items() if QTOP in c['type'])
        quarters[0][1]['connections'][port][0] = quarters[1][1]['connections'][port][0]
        path = out / ('negative_cross_quarter_' + port + '.json')
        path.write_text(json.dumps(bad) + '\n')
        try:
            verify_connections(path)
        except AssertionError:
            negatives.append(dict(port=port, refused=True))
        else:
            raise AssertionError('Crossed quarter binding accepted: ' + port)
    result['crossed_ID_and_credit_negatives'] = negatives
    offscript = '\n'.join([
        f'read_verilog -sv {ROOT / PARENT}', f'hierarchy -check -top {PTOP}',
        'proc', 'opt_clean', 'check -assert', f'write_json {out / "default_off.json"}'])
    with (out / 'default_off.log').open('w') as f:
        subprocess.run(['yosys', '-Q', '-T', '-p', offscript], stdout=f,
                       stderr=subprocess.STDOUT, check=True)
    off = json.loads((out / 'default_off.json').read_text())['modules'][PTOP]
    assert not off['cells']
    assert all(set(p['bits']) <= {'0'} for p in off['ports'].values() if p['direction'] == 'output')
    result['default_off_cells'] = 0
    result['default_off_outputs_and_ready_zero'] = True
    (out / 'wire_check.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--wire-check', action='store_true')
    p.add_argument('--verify-mapped', type=Path)
    a = p.parse_args()
    if a.verify_mapped:
        print(json.dumps(verify_connections(a.verify_mapped, mapped=True), indent=2))
        return
    out = a.out.resolve()
    prepare(out)
    if a.wire_check:
        print(json.dumps(wire_check(out), indent=2))


if __name__ == '__main__':
    main()
