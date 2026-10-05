#!/usr/bin/env python3
"""Pin the literal P0 receiver closure without changing RTL or launching tools."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def enroll(inventory, job, out):
    authority = json.loads(inventory.read_text())
    selection = json.loads((job / 'selection.json').read_text())
    args = job / 'top.args.f'
    sources = []
    for line in args.read_text().splitlines():
        if line.startswith('--top-module'):
            break
        path = Path(line.strip())
        if not path.is_absolute():
            path = job / 'die' / path
        if not path.is_file():
            raise FileNotFoundError(path)
        sources.append(path)
    expected = authority['source_pins']
    by_name = {path.name: path for path in sources}
    verified = {}
    for name, pin in expected.items():
        if name == 'host':
            path = Path(pin['path'])
        elif Path(pin['path']).is_absolute():
            path = Path(pin['path'])
        else:
            path = by_name[Path(pin['path']).name]
        actual = sha(path)
        if actual != pin['sha256']:
            raise ValueError(f'{name}: source differs from P0 inventory: {path}')
        verified[name] = dict(path=str(path), sha256=actual)
    if sha(job / 'selection.json') != authority['selection_sha256']:
        raise ValueError('selection differs from retained P0 authority')
    core = Path(verified['compiled_generated_core']['path']).read_text()
    parent = Path(verified['selected_top']['path']).read_text()
    matvec = Path(verified['matvec']['path']).read_text()
    assert 'DEC_LA' not in core, 'candidate cannot be enrolled as P0'
    for name, value in [('ACC_LAT', 5), ('TREE_LAT', 3), ('MUL_LAT', 5),
                        ('FAST_ISSUE', 0), ('KV_PREP', 0)]:
        assert re.search(r'parameter integer\s+' + name + r'\s*=\s*' + str(value) + r'\b', core), name
    assert '.clk(me_clk), .rst_n(rst_n), .go(me_go)' in core
    assert '.clk(clk), .rt_active(su_active)' in core
    assert 'assign me_mem_ok_svc = !rst_n || scale_ready;' in parent
    assert re.search(r'\bu_kv\s*\(', parent)
    assert '.kv_write_drained(kv_write_drained)' in parent
    out.mkdir(parents=True, exist_ok=False)
    snapshot = out / 'source'
    snapshot.mkdir()
    closure = []
    for index, path in enumerate(sources):
        copy = snapshot / f'{index:02d}_{path.name}'
        copy.write_bytes(path.read_bytes())
        closure.append(dict(path=str(path), snapshot=str(copy), sha256=sha(copy),
                            runtime_hierarchical_leaf=path.parts[-2].startswith('Vot_')))
    for path in [args, job / 'selection.json']:
        (out / path.name).write_bytes(path.read_bytes())
    bank = by_name['ot_qwen_rt_rom_bank.sv']
    cg = by_name['ot_hdc_cg.sv']
    macro = by_name['ot_rom_4096x266_m8.v']
    macro_json = macro.with_suffix('.json')
    if macro_json.is_file():
        (out / macro_json.name).write_bytes(macro_json.read_bytes())
    boundary = {
        'prog_q': dict(bits=1024, driver='parent.prog_mem synchronous read on clk',
                       source='selected_top', min_arrival_ps=None, max_arrival_ps=None),
        'crom_q': dict(bits=4096, driver='64 parent.crom_mem synchronous reads on clk',
                       source='selected_top', min_arrival_ps=None, max_arrival_ps=None),
        'scale_q': dict(bits=12288, driver='parent.g_sc[0:47].u_bank, 13 macros per port, DW256',
                        source=str(bank), min_arrival_ps=None, max_arrival_ps=None),
        't_lvl': dict(bits=24576, driver='selected parent input, 48 x16 x32',
                      min_arrival_ps=None, max_arrival_ps=None),
        'fab_fault': dict(bits=1, driver='selected parent input', min_arrival_ps=None, max_arrival_ps=None),
        'kv_ok': dict(bits=1, driver='selected STREAM4 service u_kv',
                      source='stream4_service', min_arrival_ps=None, max_arrival_ps=None),
        'kv_write_drained': dict(bits=1, driver='selected STREAM4 service u_kv; retained drain/retirement dependency',
                                source='stream4_service', min_arrival_ps=None, max_arrival_ps=None),
        'w_ok': dict(bits=1, driver='scale_ready=rom_ready && !(|sc_fault[47:0])',
                     source='selected_top', min_arrival_ps=None, max_arrival_ps=None),
        'me_mem_ok': dict(bits=1, driver='!rst_n || scale_ready',
                          source='selected_top', min_arrival_ps=None, max_arrival_ps=None),
        'emb_ok': dict(bits=1, driver='rom_ready && !emb_fault',
                       source='selected_top', min_arrival_ps=None, max_arrival_ps=None),
    }
    for contract in boundary.values():
        contract['receiver_load_ff'] = None
    macro_model = json.loads(macro_json.read_text()) if macro_json.is_file() else {}
    macro_views = {}
    for name, expected_hash in macro_model.get('views', {}).items():
        view = macro.parent / name
        actual_hash = sha(view) if view.is_file() else None
        if actual_hash is not None and actual_hash != expected_hash:
            raise ValueError(f'macro view differs from retained model: {view}')
        macro_views[name] = dict(path=str(view), expected_sha256=expected_hash,
                                actual_sha256=actual_hash, present=view.is_file())
    record = dict(
        status='P0_LITERAL_SOURCE_ENROLLED_CLOCK_BOUND_MISSING',
        authority=authority['functional_authority'], inventory_pin='e86ed320f',
        core_sha256=verified['compiled_generated_core']['sha256'],
        core_parameters=dict(W=16, G=6144, AW=24, NW=18, PAW=12, SU_VEC=1, SW=64,
                             LV=7, SMIN=7, SMAX=11, TCUT=7, BD=41, NWS=5, TWS=38,
                             ORD=7, MEM_EXTRA=1, ME_STALL=1, ME_IDLE_GATE=1,
                             ACC_LAT=5, TREE_LAT=3, MUL_LAT=5, FAST_ISSUE=0, KV_PREP=0),
        DEC_LA_present=False, baseline_RTL_modified=False, candidate_fault_fix_applied=False,
        source_pins=verified, compiled_SV_closure=closure,
        native_top_args_sha256=sha(args), selection_sha256=sha(job / 'selection.json'),
        actual_receivers={
            'ME': 'core.u_me.u_top: original ot_qwen_w12_matvec_part PART2 capture and loop feedback',
            'SU': 'core.g_vsu.u_su: original ot_hdc_vstream_rt accept and descriptor/loop FFs',
            'ME_clock': 'core.g_me_cg.u_me_cg.u_icg.GCLK -> me_clk -> u_me.u_top.clk',
            'SU_clock': 'clk (same literal source clock as core and sequencer)'},
        icg=dict(source=str(cg), sha256=sha(cg), cell='ICGx1_ASAP7_75t_R',
                 CLK='clk', ENA='me_en', SE=0, GCLK='me_clk',
                 enable='!rst_n || (me_mem_ok && (!me_idle || me_wake))',
                 reset='rst_n asynchronously resets ME/SU; !rst_n forces gate enabled',
                 reset_driver='parent.rt_rst_n starts low, deasserts after cyc==5 posedge clk',
                 reset_recovery_removal_bounds_ps=None,
                 propagated_CLK_GCLK_SS_FF_min_max_ps=None,
                 ENA_launch_load_setup_hold_bounds_ps=None),
        boundaries=boundary, source_physical_slot=None,
        core_output_loads=dict(go_accept_feedback='retain actual ME/SU receivers and active/ready feedback',
                               loaded_pin_capacitances_ff=None, ideal_receiver_allowed=False),
        enrollment_tool_sha256=sha(Path(__file__)),
        scale_macros=dict(type='ot_rom_4096x266_m8', count=48 * 13, payload_bits=256,
                          source_sha256=sha(macro), content_independent_model=str(macro_json),
                          read_latency_source_edges=1, bank_select='registered sel_q, 13-way gated output OR',
                          CE='scale_gre[port] && me_clk_en && bank_index_match',
                          ROM_ECC=False, macro_loaded_SS_FF_clockq=None),
        macro_views=macro_views,
        macro_model_claim_boundary=macro_model.get('claim_boundary'),
        macro_analytical_clockq_ps={corner: macro_model.get('timing', {}).get(corner, {}).get('clk_to_q_ps')
                                   for corner in ['ss', 'ff']},
        smallest_clock_bound_missing={
            'path': 'core.clk -> actual ICG CLK/GCLK -> core.u_me.u_top capture FF clock pins',
            'data_gate_launch': '48 sc_fault FFs + rom_ready -> scale_ready -> me_mem_ok -> me_en -> ICG.ENA',
            'need': 'source-matched SS/FF launch/capture insertion, actual ENA/capture loads, gating checks and reset recovery/removal',
            'owner': 'Goodall physical context + Beauvoir source enrollment'},
        serial_clock_join=dict(source_clock='clk', source_serial_clock_port=None,
                               source_ratio_CDC_installed=False,
                               historical_serial_period_ps=1111,
                               async_group_exceptions_valid_for_selected_SU=False,
                               disposition='Retain literal common-clock arcs; source/domain enrollment or owner clock-plan decision required before serial-domain credit'),
        retained_part2_fault_base=dict(
            source_uses_LV0_only_assignment="assign tfault[LV0] = 1'b0;" in matvec,
            candidate276_applied=False, qualification=False),
        cycles=authority['cycles'], cycles_are_logical=True, new_hardware=False,
        added_state_bits=0, added_latency_cycles=0, new_heavy_job=False,
        clock_policy_ps=[833, 60, 25], physical_cut_ready=False,
        source_matches_candidate8170=False, physical_qualified=False)
    (out / 'enrollment.json').write_text(json.dumps(record, indent=2) + '\n')
    return dict(status=record['status'], core_sha256=record['core_sha256'],
                SV_sources=len(closure), scale_macros=48 * 13,
                DEC_LA_present=False, physical_cut_ready=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', required=True, type=Path)
    p.add_argument('--job', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(enroll(args.inventory, args.job, args.out), indent=2))
