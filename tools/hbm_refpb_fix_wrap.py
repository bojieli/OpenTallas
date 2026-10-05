"""Run an unchanged expert bench driver with the bound DRAM checker added to its sources.
usage: tools/hbm_refpb_fix_wrap.py <tool module> <chk 0|1> -- tool args...
Tallies DRAMCHK_PC lines of every simulation run into <out>.dramchk.json."""
import sys, importlib, json, re, subprocess, threading
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
mod = importlib.import_module(sys.argv[1]); chk = sys.argv[2] == '1'
args = sys.argv[sys.argv.index('--') + 1:]
if chk:
    mod.SOURCES = mod.SOURCES + ['rtl/test/ot_hbm_pc_dram_check.sv']
tally = dict(runs=0, pc_lines=0, viol=0, ref=0, act=0, rd=0, viol_texts=[], runs_with_viol=0)
lock = threading.Lock(); real = subprocess.run
def run(cmd, *a, **k):
    r = real(cmd, *a, **k)
    if k.get('capture_output') and isinstance(r.stdout, str) and 'DRAMCHK' in r.stdout:
        with lock:
            tally['runs'] += 1; v0 = tally['viol']
            for m in re.finditer(r'DRAMCHK_PC \S+ viol=(\d+) act=(\d+) pre=\d+ ref=(\d+) rd=(\d+)', r.stdout):
                tally['pc_lines'] += 1; tally['viol'] += int(m[1]); tally['act'] += int(m[2]); tally['ref'] += int(m[3]); tally['rd'] += int(m[4])
            if tally['viol'] > v0:
                tally['runs_with_viol'] += 1
                tally['viol_texts'] += [l for l in r.stdout.splitlines() if l.startswith('DRAMCHK_VIOLATION')][:3]
                tally['viol_texts'] = tally['viol_texts'][:30]
    return r
mod.subprocess.run = run
mod.main(args)
out = Path(args[args.index('--out') + 1])
out.with_suffix('.dramchk.json').write_text(json.dumps(tally, indent=1) + '\n')
print('DRAMCHK_TALLY', json.dumps({k: v for k, v in tally.items() if k != 'viol_texts'}))
