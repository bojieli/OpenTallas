"""Reproduce the minimum XR write/read scheduling mechanism proof, no die simulation."""
from pathlib import Path
import gzip
import importlib.util
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TOOL = ROOT / 'tools/die_plan/s81_vp_xr_overlay.py'
spec = importlib.util.spec_from_file_location('xr_overlay', TOOL)
xr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xr)
base = gzip.decompress((TOOL.parent / 'fixtures/s81_vp_xr/ot_s81sl_vp.sv.gz').read_bytes()).decode()
candidate = xr.patch_vp(base)
with tempfile.TemporaryDirectory(prefix='s81_xr_raw_') as tmp:
    work = Path(tmp)
    (work / 'base.sv').write_text(base[base.index('module ot_s81sl_vpw'):].replace('module ot_s81sl_vpw', 'module ot_s81sl_vpw_base', 1))
    (work / 'xr.sv').write_text(candidate[candidate.index('module ot_s81sl_vpw'):])
    for name, defines in [('positive', []), ('negative_missing_read_stage', ['-DRAW_MUTANT'])]:
        exe = work / (name + '.vvp')
        subprocess.run(['iverilog', '-g2012', *defines, '-o', str(exe), str(HERE / 'tb.sv'), str(work / 'base.sv'), str(work / 'xr.sv')], check=True)
        result = subprocess.run(['vvp', '-n', str(exe)], capture_output=True, text=True)
        print(name, result.stdout, result.stderr)
        if name == 'positive':
            assert result.returncode == 0 and 'RAW_scheduler_checks=9995' in result.stdout
        else:
            assert result.returncode != 0 and 'RAW scheduler mismatch cycle 36' in result.stdout
