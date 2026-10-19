#!/usr/bin/env python3
"""Self-test of dv_layer_record.py on the committed L0 smoke replay (fails: die gap G1) and a synthetic PASS run."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import dv_layer_record as R  # noqa: E402

S = ROOT / 'results/rtl/s81_layer_tput_1018/slice_bench'
PRICE = ROOT / 'results/rtl/s81_layer_tput_1018/layer_price_p4l.json'


def main():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        rp, run = S / 'replay/replay_3S', S / 'runs/replay_L0_s3S'
        muts = ['--mutant', str(S / 'runs/replay_mut_shift1'), '--mutant', str(S / 'runs/replay_mut_hops')]
        R.main(['collect', '--layer', 'L0', '--cut', 'cut_3S_ctl', '--run', str(run), '--replay', str(rp), '--full-layer',
                *muts, '--out', str(t / 'f.json')])
        assert not json.loads((t / 'f.json').read_text())['valid'], 'a failing run must not count'
        (t / 'p').mkdir()
        for f in ('verilator.version', 'sources.sha256'):
            shutil.copy(run / f, t / 'p' / f)
        (t / 'p/status').write_text('run rc 0\nDV_SLICE cycles=255 in_events=64 out_checks=32 mismatches=0 '
                                    'fault_cycles=0 first_fault=0\nTB_DV_SLICE PASS\n')
        R.main(['collect', '--layer', 'L0', '--cut', 'cut_0S', '--run', str(t / 'p'), '--replay', str(rp), *muts,
                '--out', str(t / 's.json')])
        assert not json.loads((t / 's.json').read_text())['valid'], 'a smoke program must not count'
        ms = []
        for i, c in enumerate(json.loads((S / 'layer_slices.json').read_text())['layers']['L0']['cuts']):
            R.main(['collect', '--layer', 'L0', '--cut', c, '--run', str(t / 'p'), '--replay', str(rp), '--full-layer',
                    *muts, '--out', str(t / f'm{i}.json')])
            ms.append(str(t / f'm{i}.json'))
        R.main(['compose', '--slices', str(S / 'layer_slices.json'), '--price', str(PRICE), '--meas', *ms[:-1],
                '--out', str(t / 'c1.json')])
        assert json.loads((t / 'c1.json').read_text())['layers']['L0']['grade'] == 'NOT_MEASURED', 'missing cut'
        R.main(['compose', '--slices', str(S / 'layer_slices.json'), '--price', str(PRICE), '--meas', *ms,
                '--out', str(t / 'c2.json')])
        c = json.loads((t / 'c2.json').read_text())
        assert c['layers']['L0']['grade'] == 'MEASURED' and c['layers']['L0']['cycles'] == 105
        terms = {x['layer']: x for x in c['workloads']['ar']['terms']}
        assert terms['L0']['grade'] == 'MEASURED' and terms['L1']['grade'] == 'MEASURED_REP'
        assert terms['L2']['grade'] == 'PRICED' and terms['head']['grade'] == 'PRICED'
    print('test_dv_layer_record: ALL PASS')


if __name__ == '__main__':
    main()
