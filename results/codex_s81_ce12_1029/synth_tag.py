import json
import pathlib
import subprocess

root = pathlib.Path.cwd()
source = (root / 'rtl/ot_v41_bf16_lanes3.sv').read_text()
(root / 'tag_helper.sv').write_text(source[source.index('module ot_v41_bf_tag_delay #('):])
for groups in (4, 16):
    output = root / f'tag{groups}.json'
    command = (f'read_verilog -sv rtl/ot_hdc_delay.sv rtl/ot_v41_kreg.sv tag_helper.sv; '
               f'chparam -set W 13 -set D 8 -set GROUPS {groups} ot_v41_bf_tag_delay; '
               'hierarchy -top ot_v41_bf_tag_delay; proc; flatten; opt; '
               f'write_json {output}')
    subprocess.run(['yosys', '-Q', '-p', command], check=True,
                   stdout=(root / f'synth{groups}.log').open('w'), stderr=subprocess.STDOUT)
    modules = json.loads(output.read_text())['modules']
    module = modules['ot_v41_bf_tag_delay']
    def count_bits(name):
        total = 0
        for cell in modules[name]['cells'].values():
            if 'dff' in cell['type'].lower():
                total += len(cell['connections']['Q'])
            elif cell['type'] in modules:
                total += count_bits(cell['type'])
        return total
    bits = count_bits('ot_v41_bf_tag_delay')
    expected = 13 * (7 + groups)
    assert bits == expected, (groups, bits, expected)
    kept = [n for n,c in module['cells'].items() if 'g_group[' in n and n.endswith('u_copy')]
    assert len(kept) == groups, (groups, kept)
    print(f'PASS groups={groups} register_bits={bits} kept_final_copies={len(kept)} added_vs_original={bits-104}')
