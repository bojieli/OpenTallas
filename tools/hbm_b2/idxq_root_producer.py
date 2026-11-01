#!/usr/bin/env python3
"""Emit an opt-in source graft from the observed C11E root, never edit that root."""
import argparse
import hashlib
import json
from pathlib import Path

from idxq_named_overlay import instance, render


def make(root_path, graph_path, out):
    if out.exists():
        raise ValueError('Fresh output required')
    root = root_path.read_text()
    graph = json.loads(graph_path.read_text())
    cells = {c['canonical']: c for c in graph['cells']}
    master, params, ctl = instance(root, 'u_u_hb_idx_ctl')
    smaster, sparams, selector = instance(root, 'u_u_hb_idx_selector')
    lmaster, lparams, link = instance(root, 'u_u_hb_idx_link')
    assert master == cells['hb_idx__ctl']['module'] == 'ot_hbm_idx_rootctl_static_am'
    assert smaster == cells['hb_idx__selector']['module'] == 'ot_hbm_idx_selector_static_sel_eightwide'
    assert set(ctl) == set(cells['hb_idx__ctl']['ports'])
    assert set(selector) == set(cells['hb_idx__selector']['ports'])
    assert lmaster == 'ot_hbm_idx_topk_link_static' and not lparams
    assert cells['hb_idx__ctl']['explicit_parameters'] == dict(CR_RT='36', FAN32='1', RSTL='1', SEL_LAT='40', VM_RT='75')
    original_ctl = dict(ctl)
    ctl.update(n_rows='idxq_prm818_prospective[773:769]', row_pitch='idxq_prm818_prospective[785:774]',
               sel_op='idxq_sel_op', sel_pass='idxq_sel_pass', sel_addr='idxq_sel_addr',
               selected_v='idxq_selected_v', sf='idxq_selector_fault', ingest_v='idxq_ingest_v',
               lin_clear='idxq_lin_clear', lin_row='idxq_lin_row', lout_row='idxq_lout_row')
    text = '''// SOURCE-ONLY C11E instance replacements; no current top/route/clock model adoption.
// Join with root_collar_818.svfrag. Existing real TOPK/share/clock/reset expressions stay exact.
wire[15:0] idxq_sel_op,idxq_selected_v;
wire[7:0] idxq_sel_pass;
wire[31:0] idxq_sel_addr;
wire[3:0] idxq_selector_fault,idxq_ingest_v;
wire[9471:0] idxq_selected_line;
wire idxq_lin_clear;
wire[4:0] idxq_lin_row,idxq_lout_row;
'''
    text += render('ot_hnx_idxq_rootctl_static_am', '.K(8),.S(4),.CW(2),'+params, 'u_u_hb_idx_ctl', ctl)
    for s in range(4):
        ports = dict(selector)
        ports.update(op=f'idxq_sel_op[{s*4}+:4]', pass_=f'idxq_sel_pass[{s*2}+:2]')
        ports['pass'] = ports.pop('pass_')
        ports.update(addr=f'idxq_sel_addr[{s*8}+:8]', fault=f'idxq_selector_fault[{s}]',
                     selected_v=f'idxq_selected_v[{s*4}+:4]', selected_line=f'idxq_selected_line[{s*2368}+:2368]')
        # Same real tree input is presented to all four independent selector stores.
        text += render(smaster, sparams, f'u_u_hb_idx_selector_idxq{s}', ports)
    lp = {p: link[p] for p in ['clk', 'clk_mem', 'rst_n', 'clear', 'flush', 'emit_v', 'emit_group',
                               'rank', 'gbase', 'tx_v', 'tx', 'fault', 'selected_count']}
    lp.update(row_clear='idxq_lin_clear', in_slot='idxq_lin_row[2:0]', emit_slot='idxq_lout_row[2:0]',
              sel_v_w='idxq_selected_v[7:0]', sel_v_e='idxq_selected_v[15:8]',
              sel_line_w='idxq_selected_line[4735:0]', sel_line_e='idxq_selected_line[9471:4736]')
    text += '// Donor row-slot ABI is row modulo8; actual selected N6 rows are0..5.\n'
    text += render('ot_hnx_idxq_link', '', 'u_u_hb_idx_link', lp)
    out.mkdir(parents=True)
    (out/'root_calendar_selectors_link.svfrag').write_text(text)
    changed = sorted(k for k, v in original_ctl.items() if ctl[k] != v)
    report = dict(status='SOURCE_ONLY_PARTIAL_ROOT_GRAFT_NOT_ADOPTED', current_graph_changed=False,
        may_generate_physical=False, inputs={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [root_path, graph_path]},
        root=dict(old_master=master, prospective_master='ot_hnx_idxq_rootctl_static_am', retained_parameters=cells['hb_idx__ctl']['explicit_parameters'],
                  prospective_parameters=dict(K=8,S=4,CW=2), changed_existing_ports=changed,
                  retained_service_ports={p:v for p,v in original_ctl.items() if p not in changed}),
        selectors=dict(count=4, old_count=1, additional_count=3, additional_SRAM_256x256_banks=36,
                       controls_bits=dict(op=16,pass_bits=8,addr=32), real_input=selector['in_line'],
                       clocks={p:selector[p] for p in ['clk_ctl','clk_q','clk_mem']}, reset=selector['rst_n'],
                       selected_line_bits=9472, selected_valid_bits=16, faults='All4 actual selector fault outputs'),
        link=dict(old_master=lmaster, prospective_master='ot_hnx_idxq_link', donor='859b27b6b', row_slots=8,
                  row_mapping='modulo8; source-selected8INDEX allN6', retained_clock=link['clk'], retained_reset=link['rst_n'],
                  real_fault=link['fault'], selected_count=link['selected_count']),
        holds=['Four selector instances add clock/reset fanout and36SRAM banks; no physical slot/route credit',
               'New root calendar and9472b selector→row-slot link need current functional composition and delivered reset qualification',
               'Root/qctl programme tables and new49b ingress need actual HOST loading/global cohort dates',
               'Join qctl/keybuf/reader/query-clear source packet and qualify new local routes; no152native retirement',
               'Current3286pin reader/source unchanged; prospective3319 remains physical HOLD'])
    report['port_abi']={'scope': 'RTL port-bit counts, not physical pin placement or route credit', 'root': {'old': 5877, 'prospective': 5965, 'delta': 88, 'details': {'new_N_pitch': 17, 'new_row_events': 11, 'wider_selector_control': 42, 'wider_selected_v': 12, 'wider_selector_fault': 3, 'wider_ingest_v': 3}}, 'qctl_each': {'old': 337, 'prospective': 371, 'delta': 34}, 'reader_each': {'old': 3286, 'prospective': 3319, 'delta': 33}, 'selector_each': {'old': 3599, 'prospective': 3599, 'old_count': 1, 'prospective_count': 4}, 'link': {'old': 4597, 'prospective': 11723, 'delta': 7126, 'details': {'extra_selector_data': 7104, 'extra_selector_valid': 15, 'new_row_slot_controls': 7}}, 'collar_prm': {'old': 769, 'prospective': 818, 'delta': 49}}
    (out/'cycle_ledger.json').write_text(json.dumps({'scope': 'Source contracts only; no routed/global calendar adoption', 'clock_ps': 833, 'reader_capture_added_edges': 0, 'reader_profiles': [171, 173], 'reader_reset': 'Existing local SYNC2+TREE1 relay; consumer release edge4 retained', 'qctl_reset': 'DELIVERED_RESET0 retains observed old local SYNC2+TREE1 relay; earlier candidate1 was incorrect', 'qctl_row_clear_delay_edges': {'RT171': 169, 'RT173': 171}, 'query_clear': 'Own delayed qctl.row_start; actual old query instance retains all other ports', 'reader_frame': 'Own qctl.frame_start once per record; never row_start', 'source_example_frame_to_first_weight_edges': 3, 'source_example_frame_to_first_query_edges': 20, 'new_frame_route_minus_existing_weight_route_max_edges': 2, 'root_parameters_retained': {'CR_RT': 36, 'VM_RT': 75, 'SEL_LAT': 40, 'RSTL': 1, 'FAN32': 1}, 'link_pin_pipeline': 'Donor retains old input/output pin registers and2edge reset synchronizer; new4selector merge is combinational and physically unqualified', 'global_cohort_dates': None, 'new_route_latency_adopted': False, 'local_composition_qualified': False},indent=2)+'\n')
    (out/'root_producer.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--graph',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();make(a.root,a.graph,a.out)
