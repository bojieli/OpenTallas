"""unit test: l34 drops the middle stages of a 5-stage 8-bit lane (sites 300 um apart, hop 1000) and recomposes edges"""
import json, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent


def test_l34_chain():
    I = {'src': {'master': 'blk_a', 'note': ''}, 'dst': {'master': 'blk_b', 'note': ''}}
    E = []
    for s in range(5):
        I[f'rf0001_s{s:03d}_l0'] = {'master': 'hbfd_rly_48_WE', 'note': f'lane row; site ({100 + 300 * s}.0, 50.0) um'}
    E.append(dict(name='drv', bits=8, source=['src', 'q', 0, 8], sink=['rf0001_s000_l0', 'i', 0, 8]))
    for s in range(4):
        E.append(dict(name=f't{s}', bits=8, source=[f'rf0001_s{s:03d}_l0', 'o', 0, 8], sink=[f'rf0001_s{s + 1:03d}_l0', 'i', 0, 8]))
    E.append(dict(name='ld_lo', bits=4, source=['rf0001_s004_l0', 'o', 0, 4], sink=['dst', 'd', 4, 8]))
    E.append(dict(name='ld_hi', bits=4, source=['rf0001_s004_l0', 'o', 4, 8], sink=['dst', 'd', 0, 4]))
    E.append(dict(name='ck2', bits=1, source=['ckg', 'pll', 0, 1], sink=['rf0001_s002_l0', 'ck', 0, 1]))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); (td / 'in.json').write_text(json.dumps(dict(instances=I, edges=E, clock_resets=[], straps=[])))
        subprocess.run([sys.executable, HERE / 'l34_relay_hop.py', td / 'in.json', td / 'out.json', '--hop', '1000', '--report', td], check=True)
        c = json.loads((td / 'out.json').read_text()); rep = json.loads((td / 'l34_report.json').read_text())
    kept = sorted(n for n in c['instances'] if n.startswith('rf'))
    assert kept == ['rf0001_s000_l0', 'rf0001_s003_l0', 'rf0001_s004_l0'], kept
    assert rep['undriven_bits'] == 0 and rep['stages_now'] == 5 and rep['stages_kept'] == 3
    srcs = {(e['source'][0], e['sink'][0]) for e in c['edges']}
    assert ('rf0001_s000_l0', 'rf0001_s003_l0') in srcs and not any('s001' in a or 's002' in b for a, b in srcs)
    ld = sorted((e['source'][2:], e['sink'][2:]) for e in c['edges'] if e['sink'][0] == 'dst')
    assert ld == [([0, 4], [4, 8]), ([4, 8], [0, 4])], ld
    assert all(e['sink'][0] != 'rf0001_s002_l0' for e in c['edges'])


if __name__ == '__main__':
    test_l34_chain(); print('PASS')
