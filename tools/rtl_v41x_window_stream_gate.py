"""Matched WINDOW replay with actual producer writes; no numeric attention claim."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHIP = ROOT / 'rtl/chip'
NAMES = ['attn_desc_lifecycle', 'attn_row_merge', 'window_attn_source',
         'window_kv_prefetch', 'window_refill_schedule', 'window_row_codec',
         'window_stage4', 'window_stream']
SOURCES = [CHIP / ('ot_chip_v41x_' + n + '.sv') for n in NAMES]
BENCH = ROOT / 'rtl/test/tb_ds_layer_write_compose.sv'
EDGE = ROOT / 'rtl/test/tb_window_stream_edges.sv'
OUT = ROOT / 'results/rtl/v41x_window_stream.json'

def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*SOURCES, BENCH, EDGE, Path(__file__)]}

def run():
    arms = []
    with tempfile.TemporaryDirectory(prefix='window-stream-') as tmp:
        exe = str(Path(tmp) / 'gate.vvp')
        for ii1 in (0, 1):
            subprocess.run(['iverilog', '-g2012', '-s', 'tb_ds_layer_write_compose',
                            f'-Ptb_ds_layer_write_compose.STREAM_II1={ii1}',
                            '-o', exe, *map(str, SOURCES), str(BENCH)], check=True,
                           capture_output=True, text=True)
            scenarios = []
            for period, delay in [(1, 2), (11, 2), (3, 15)]:
                result = subprocess.run(['vvp', exe, f'+SINK_PERIOD={period}',
                                         f'+LATENCY={delay}'], check=True,
                                        capture_output=True, text=True, timeout=120)
                assert 'WINDOW_PRODUCER_COMPOSE_PASS' in result.stdout
                def fields(line):
                    return {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}
                scenarios.append({'metrics': fields(next(line for line in result.stdout.splitlines()
                                                        if line.startswith('EDGE_CONTRACT'))),
                                  'replays': [fields(line) for line in result.stdout.splitlines()
                                              if line.startswith('REPLAY')]})
            bad = subprocess.run(['vvp', exe, '+CORRUPT_WRITE'], capture_output=True,
                                 text=True, timeout=120)
            assert bad.returncode != 0 and 'packed row mismatch' in bad.stdout
            arms.append(scenarios)
        subprocess.run(['iverilog', '-g2012', '-s', 'tb_window_stream_edges', '-o', exe,
                        str(CHIP/'ot_chip_v41x_window_stage4.sv'), str(SOURCES[-1]), str(EDGE)],
                       check=True, capture_output=True, text=True)
        edge = subprocess.run(['vvp', exe], check=True, capture_output=True, text=True, timeout=120)
        assert 'STREAM_EDGES_PASS jobs=7 accepted=101 max_reserved=4' in edge.stdout
    assert arms[0][0]['replays'][0]['min_gap'] == 4
    assert arms[1][0]['replays'][0]['min_gap'] == 1
    for arm in arms:
        for case in arm:
            assert case['metrics']['max_outstanding'] == 1
            assert case['metrics']['accepted'] == 64
            assert case['metrics']['descriptors'] == 2
    rec = {'status': 'pass', 'sources': hashes(), 'baseline': arms[0], 'ii1': arms[1],
           'edges': edge.stdout.strip(), 'fifo_data_bytes': 8448, 'credit_slots': 4,
           'scope': 'Same synthetic producer, actual delayed-completion HBM write/refill/replay; '
                    'no numeric attention, shared-client arbitration, physical timing or full-token claim.',
           'unchanged': 'Selected CKV merger and default WINDOW implementation; serial full refill.'}
    OUT.write_text(json.dumps(rec, indent=2) + '\n')
    return rec

if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
