#!/usr/bin/env python3
"""Small boundary gate. Does not qualify native59 or a die composition."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/arch/qwen_split_1014/kvsys_v1_3_candidate/native_command'
TEMPLATE = OUT / 'native380_template.json'
RTL = ROOT / 'rtl/qwen_sys/split_20261014/qkd_native59_command_guard.sv'
TB = ROOT / 'rtl/test/qwen_split/tb_native59_command_guard.sv'

def main():
    data = json.loads(TEMPLATE.read_text())
    value = int(data['command_hex'], 16)
    assert (value >> 152) & 0xffffff == 13696
    assert (value >> 280) & 0xffffff == 3167
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (RTL, TB, TEMPLATE)}
    receipt = {'scope': 'component only; no native provider or physical qualification', 'sources': sources, 'cases': []}
    with tempfile.TemporaryDirectory(prefix='native-command-') as temp:
        tmp = Path(temp)
        (tmp/'native380-test.svh').write_text(f"localparam [379:0] COMMAND=380'h{value:095x};\n")
        for mutant in range(4):
            exe = tmp/f'm{mutant}.vvp'
            subprocess.run(['iverilog', '-g2012', '-I', temp, '-s', 'tb_native59_command_guard',
                            f'-Ptb_native59_command_guard.MUT={mutant}', '-o', str(exe), str(RTL), str(TB)], check=True)
            result = subprocess.run(['vvp', str(exe)], capture_output=True, text=True)
            (OUT/f'm{mutant}.log').write_text(result.stdout+result.stderr)
            assert (result.returncode == 0) == (mutant == 0), result.stdout+result.stderr
            receipt['cases'].append({'mutant': mutant, 'exit_code': result.returncode,
                                     'observed': 'PASS' if mutant == 0 else 'FAIL'})
    (OUT/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('PASS actual descriptor/context boundary; all three bypass mutants observed FAIL')

if __name__ == '__main__':
    main()
