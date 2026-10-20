"""Source-only contract and weighted fanout checks; physical proof is separate."""
import copy
import json
import ctlm6_bound_macro as B


def fixture():
    ports = {'ck': {'direction': 'input', 'bits': [2]},
             'd': {'direction': 'input', 'bits': [3]},
             'rst_n': {'direction': 'input', 'bits': [22]},
             'q': {'direction': 'output', 'bits': [20]},
             'unused_abi_input': {'direction': 'input', 'bits': [21]}}
    fp = {'C': 'input', 'D': 'input', 'R': 'input', 'Q': 'output'}
    cells = {'producer': {'type': '$_DFF_PN0_',
                         'connections': {'C': [2], 'D': [5], 'R': [4], 'Q': [10]},
                         'port_directions': fp},
             'u_gi.u_mem': {'type': 'real_memory', 'parameters': {'DW': '1000010'},
                            'connections': {'CLK': [2], 'D': [10]*66, 'Q': [20]},
                            'port_directions': {'CLK': 'input', 'D': 'input', 'Q': 'output'}},
             'data_root': {'type': '$_DFF_P_', 'connections': {'C': [2], 'D': [3], 'Q': [5]},
                           'port_directions': {'C': 'input', 'D': 'input', 'Q': 'output'}},
             'reset_root': {'type': '$_DFF_P_', 'connections': {'C': [2], 'D': [22], 'Q': [4]},
                            'port_directions': {'C': 'input', 'D': 'input', 'Q': 'output'}}}
    mp = {'CLK': {'direction': 'input', 'bits': [1]},
          'D': {'direction': 'input', 'bits': list(range(2, 68))},
          'Q': {'direction': 'output', 'bits': [68]}}
    design = {'modules': {'top': {'ports': ports, 'cells': cells, 'netnames': {}},
                          'real_memory': {'attributes': {'blackbox': '1'}, 'ports': mp}}}
    contract = {'real_memory': {'kind': 'physical_macro', 'ports': {
        name: dict(direction=row['direction'], width=len(row['bits']), clock=name == 'CLK')
        for name, row in mp.items()}}}
    return design, contract


def run(design, contracts):
    return B.build(json.dumps(design).encode(), 'top', 'bounded', load_cap=16,
                   transparent_inverters=True, retain_mux=True, shared_helpers=True,
                   retain_all_comb=True, macro_contracts=contracts)


def rejects(design, contracts, phrase):
    try:
        run(design, contracts)
    except (ValueError, AssertionError) as error:
        assert phrase in str(error), (phrase, error)
    else:
        raise AssertionError('accepted invalid macro contract: '+phrase)


def main():
    design, contracts = fixture()
    rtl, helpers, record = run(design, contracts)
    assert rtl.count('real_memory #(') == 1
    assert '\\u_gi.u_mem ' in rtl
    assert ".DW(7'b1000010)" in rtl
    assert 'unused_abi_input' in rtl
    assert record['added_by_type']['$_DFF_PN0_'] == 4
    terminal = record['retained_macro_terminals'][0]
    assert terminal['original_connections']['CLK'] == terminal['emitted_connections']['CLK']
    assert terminal['original_connections']['Q'] == terminal['emitted_connections']['Q']
    assert len(set(terminal['emitted_connections']['D'])) == 5
    # A child input connected to16 actual FFs consumes16 terminal loads,
    # even though it is one pin in the abstract. Never count it as one.
    soft = copy.deepcopy(contracts)
    soft['real_memory'].update(kind='soft_child', load_source_sha256='0'*64,
                               input_loads={'D': [16]*66})
    _, _, weighted = run(design, soft)
    assert weighted['added_by_type']['$_DFF_PN0_'] == 65
    for mutate, phrase in [
        ('missing_direction', 'ports differ'), ('wrong_width', 'direction/width mismatch'),
        ('no_clock_role', 'boolean clock'), ('not_blackbox', 'not an actual declared blackbox'),
        ('unknown_module', 'not-an-allowed-macro'), ('output_overload', 'macro output overload'),
        ('soft_missing_weights', 'terminal loads'), ('soft_missing_hash', 'source-pinned'),
    ]:
        d, c = copy.deepcopy(design), copy.deepcopy(contracts)
        if mutate == 'missing_direction':
            del d['modules']['top']['cells']['u_gi.u_mem']['port_directions']['D']
        if mutate == 'wrong_width': c['real_memory']['ports']['D']['width'] = 65
        if mutate == 'no_clock_role': del c['real_memory']['ports']['CLK']['clock']
        if mutate == 'not_blackbox': d['modules']['real_memory']['attributes']['blackbox'] = '0'
        if mutate == 'unknown_module':
            d['modules']['top']['cells']['unknown'] = {
                'type': 'not-an-allowed-macro', 'connections': {}, 'port_directions': {}}
        if mutate == 'output_overload':
            for k in range(17):
                d['modules']['top']['ports'][f'out{k}'] = {'direction': 'output', 'bits': [20]}
        if mutate.startswith('soft_'):
            c['real_memory'].update(kind='soft_child')
            if mutate == 'soft_missing_weights': c['real_memory']['load_source_sha256'] = '0'*64
        rejects(d, c, phrase)
    print('MACRO_EXACT_ABI_PARAMS_CLOCKS_WEIGHTED_TERMINALS_FAILCLOSED PASS')


if __name__ == '__main__':
    main()
