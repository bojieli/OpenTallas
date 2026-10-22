#!/usr/bin/env python3
"""Expose the real Col8 columns at the accepted, fixed reticle placements.

This creates source connections and placement requests, not qualified hard
views. Long payload and reset transport and propagated clocks remain separate
construction steps. Original quarter connections stay on the real controller.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTROL = 'rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_col8_control.sv'
COLUMN = 'rtl/hdc/v41x/ot_hbm_idx_col8_sram_face.sv'
MODELS = 'results/arch/hbm_col8_parent_1021/native_cells.v'
Q = ('SW', 'SE', 'NW', 'NE')
CUT = {'cut_rst_n': ('output',32), 'cut_qv': ('output',32),
       'cut_q': ('output',18176), 'cut_key': ('output',17408),
       'cut_hid': ('output',2048), 'cut_cs': ('input',1024),
       'cut_cf': ('input',32), 'cut_prdy': ('input',128)}
PORTS = {'ctl': ('input',1), 'cp': ('input',4), 'rst_n': ('input',1),
         'qv_b': ('input',1), 'q_b': ('input',568), 'key': ('input',544),
         'hid': ('input',64), 'cs_out': ('output',32),
         'cf_out': ('output',1), 'prdy': ('output',4)}


def apply(graph, split, geometry, dependencies):
    c = copy.deepcopy(graph)
    assert len(split['instances']) == 132
    assert split['active_clocks_per_quarter'] == 143
    assert geometry['placed_columns'] == geometry['required_columns'] == 128
    assert geometry['required_pairs'] == 512
    assert geometry['required_raw_seam_srams'] == 1536
    assert not geometry['unplaced'] and not geometry['repair_failures']
    assert hashlib.sha256((ROOT/MODELS).read_bytes()).hexdigest() == '3606964bc33b09214c19c32b6d6bbab6cbf09f26d28d3aa9f9aec1571f657048'
    deps = dependencies['production_RTL'] + [dependencies['pair_source_for_simulation_only'], MODELS]
    for f in deps:
        want = dependencies['sha256'].get(f)
        if want:
            assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest() == want, f
    changed = []; added = []; reset = []; clocks = []; placements = {}; hard_children = []
    for q in Q:
        n = 'hb_idx__s_' + q
        i = c['instances'][n]
        assert i['master'] == 'ot_hbm_idx_score_quarter_static', (n,i['master'])
        assert i['params']['TP'] == 192 and i['params'].get('RANK_W',8) == 8
        i['params']['RANK_W'] = 8
        old = i['master']
        i.update(master='ot_hbm_idx_score_quarter_col8_control', source=CONTROL,
                 rtl_deps=[f for f in deps if f != CONTROL], force_synth=True,
                 placement_key=q+'.residual_control',
                 note='Real residual controller; old quarter reserve is not a qualified hard footprint')
        i.pop('physical_view',None); i.pop('closed_record',None)
        i['ports'].update({p:dict(direction=d,bits=b) for p,(d,b) in CUT.items()})
        for s in c['straps']:
            if s.get('inst') == n and s.get('master') == old:
                s['master'] = i['master']
        declared = next(x for x in split['instances'] if x['placement_key']==q+'.residual_control')
        i['hard_children'] = []
        for child in declared.get('hard_children',[]):
            child = copy.deepcopy(child)
            assert child['master']=='ot_hidx_meta_sram146' and child['params']=={'D':146}
            assert hashlib.sha256((ROOT/child['source']).read_bytes()).hexdigest()==child['source_sha256']
            assert (ROOT/child['view']/(child['master']+'.lef')).is_file()
            child['instance'] = child['instance'].replace(n+'.u_control.',n+'.',1)
            child['clock_terminal_compensation_open'] = True
            i['hard_children'].append(child);hard_children.append(child)
        changed.append(n)
    for item in split['instances']:
        if item['kind'] != 'hierarchical_column':
            continue
        key = item['placement_key']; q = key.split('.')[0]; ctrl = 'hb_idx__s_'+q
        k = item['column_index']; name = 'col8_'+key.replace('.','_')
        assert name not in c['instances']
        c['instances'][name] = dict(master=item['master'], source=COLUMN,
            rtl_deps=[f for f in deps if f != COLUMN], params={},
            ports={p:dict(direction=d,bits=b) for p,(d,b) in PORTS.items()},
            slot=name, placement_key=key, force_synth=True,
            region='d4g_l35_col8', owner='CODEX-HBM-CHAIN-2000',
            note='Real column with four pair masters and twelve raw SRAMs; R3 and physical timing remain diagnostic')
        added.append(name)
        placements[name] = dict(geometry['placed_service_envelopes'][key],
            orientation='R0', kind='hierarchical_column', opaque_hard_view=False,
            source_rectangles={p.split('/',1)[1]:v for p,v in geometry['individual_source_rectangles'].items()
                               if p.startswith(key+'/')})
        assert len([v for v in placements[name]['source_rectangles'].values() if v['kind']=='pair']) == 4
        for physical_path, part in placements[name]['source_rectangles'].items():
            rtl_path = physical_path
            if rtl_path.startswith(('l0.','l1.','l2.','l3.')):
                rtl_path = rtl_path[:3]+'u_ring.'+rtl_path[3:]
            part['rtl_path'] = name+'.'+rtl_path
        for p, conn in item['connections'].items():
            direction,bits = PORTS[p]
            if p in ('ctl','cp'):
                original = 'clk_chunk' if p == 'ctl' else 'clk_hslice'
                old = [r for r in c['clock_resets'] if r['instance']==ctrl and r['port']==original]
                assert len(old)==1,(ctrl,original)
                entry = copy.deepcopy(old[0]); entry.update(instance=name,port=p,bits=bits)
                # Preserve the exact 143-clock graph identity even while the
                # initial source contract still uses its root-domain source.
                entry['source_port_bits'] = conn
                entry['physical_root_assignment_open'] = True
                c['clock_resets'].append(entry)
                clocks.append(dict(instance=name,port=p,source_port_bits=conn))
                continue
            assert conn['width'] == bits
            source_port = conn['net'].split('.')[-1]; lo = conn['lsb']
            a = [ctrl,source_port,lo,lo+bits]; b = [name,p,0,bits]
            if direction == 'output': a,b=b,a
            edge = dict(name=f'l35_{name}_{p}',bits=bits,source=a,sink=b,
                clock='stream',ready_or_credit=False,allowed_exception=None,
                basis='Exact cut/rejoin source connection; actual transport and calendar pending',region='d4g_l35_col8')
            if p == 'rst_n':
                edge.update(kind='reset', transport='separate_source_bound_reset_delivery',
                            boot_edges_open=True, payload_relay_allowed=False)
                reset.append(dict(source=a,sink=b,source_release='three local clk_chunk edges after leaf input reset',
                                  column_release='four local ctl edges before local reset leaves',
                                  transport_release_edges=None,asynchronous_assertion=True))
            c['edges'].append(edge)
    assert len(added)==128 and len(reset)==128
    c['masters'] = dict(sorted(collections.Counter(i['master'] for i in c['instances'].values()).items()))
    c['summary']['clock_reset_ports'] = len(c['clock_resets'])
    return c, dict(status='DIAGNOSTIC_SOURCE_COMPOSED',release_ready=False,
        controllers=changed,columns=added,active_clocks_per_quarter=143,
        column_clock_connections=clocks,controller_unused_clock_port='clk_hslice',
        placements=placements,existing_bodies_moved=geometry['existing_bodies_moved'],
        enlarged_hc_root=geometry['placed_service_envelopes']['hc_eng'],
        baseline_roots_within_existing_bodies=geometry['baseline_roots_within_existing_bodies'],
        reset_delivery=reset,automatic_relays_requiring_regeneration=geometry['automatic_relays_requiring_regeneration'],
        local_calendar=split['calendar'],hard_children=hard_children,
        placement_input_manifest_sha256=geometry['input_manifest_sha256'],
        obligations=['real legal clock construction for all active terminals',
            'source-bound reset delivery with measured additional boot ages',
            'regenerate routes for all displaced bodies',
            'equal-age payload and return transport, including long NW column move',
            'exact pair/meta hard-view binding and residual native/physical qualification',
            'actual programme and native producer retention calendar'])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('input','split','geometry','dependencies','output','report'):p.add_argument(n,type=Path)
    a=p.parse_args()
    c,r=apply(*[json.loads(getattr(a,n).read_text()) for n in ('input','split','geometry','dependencies')])
    for path,value in ((a.output,c),(a.report,r)):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=1)+'\n')
    print('COL8_SOURCE_ATTACHED',len(r['columns']),'columns; reset, clocks and routed calendar OPEN')
