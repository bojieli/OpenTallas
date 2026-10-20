#!/usr/bin/env python3
from pathlib import Path
import subprocess
cmd=['read_liberty -ignore_miss_func '+str(p) for p in sorted(Path('libs').glob('*.lib'))]
cmd += ['read_verilog -overwrite canonical_ASR_normalized.v',
        'read_verilog -overwrite canonical_DFF_normalized.v',
        'write_verilog -noattr cell_models.v']
Path('models.ys').write_text('\n'.join(cmd)+'\n')
with Path('models.log').open('w') as out:
    subprocess.run(['yosys','-s','models.ys'],stdout=out,stderr=subprocess.STDOUT,check=True)
