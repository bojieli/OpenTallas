#!/usr/bin/env python3
"""Verify analytical-only refinement leaves every proven CTL and gold byte intact."""
from pathlib import Path
import hashlib
import subprocess
import sys

subprocess.run([sys.executable, 'tools/s81_dv/layer_prog/qf_producer/compile_headers.py',
                '--out', 'model_final'],check=True)
for tag in (0,1,53,127,128,213,254,255):
    for name in (f'ctl_{tag}.hex',f'gold_{tag}.hex'):
        assert (Path('model_final')/name).read_bytes() == (Path('out_v5/input')/name).read_bytes(),name
src=Path('tools/s81_dv/layer_prog/qf_producer/compile_headers.py')
print(hashlib.sha256(src.read_bytes()).hexdigest(),src)
print('FINAL_MODEL_REFINEMENT_CONTROL_GOLD_BYTEIDENTICAL')
