"""Compile only the new PC; reuse Herschel's terminal connected fixture and records."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

J = Path(__file__).resolve().parent
OLD = Path('/srv/opentallas-scratch/jobs/herschel-pcwb-dram-enrollment-r2')
REPO = Path('/srv/opentallas/repos/herschel-pcwb-dram-enrollment-20261005')
sys.path.insert(0, str(REPO / 'tools'))
import hbm_accel_dskv_wb as donor

prior = json.loads((OLD / 'verdict.json').read_text())
assert prior['verdict'] == 'PASS'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
for name, expected in prior['packed_input_sha256'].items():
    assert sha(OLD / 'work/inputs' / name) == expected
for source in [donor.SOURCES[0], donor.SOURCES[2], 'tools/hbm_accel_dskv_wb.py']:
    assert sha(REPO / source) == prior['input_sha256'][source]
old_bench = (OLD / 'work/candidate.sv').read_text()
assert sha(OLD / 'work/candidate.sv') == prior['records']['candidate']['generated_bench_sha256']
a, b = 'ot_hbm_accel_stream_pc_wb_digest #(', 'ot_hbm_accel_stream_pc_wb_command_match #('
x, y = '.DIGEST_CUT(1)', '.DIGEST_CUT(1), .CMD_MATCH_CUT(1)'
assert old_bench.count(a) == old_bench.count(x) == 1
new_bench = old_bench.replace(a, b).replace(x, y)
assert new_bench.replace(b, a).replace(y, x) == old_bench
bench = J / 'connected.sv'
bench.write_text(new_bench)
source = J / 'ot_hbm_accel_stream_pc_wb_command_match.sv'
V = Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd = [str(V), '--binary', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-j', '16', '-O2',
       '--top-module', donor.TOP, '--Mdir', str(J / 'connected_obj'), '-GSTACK=1',
       str(REPO / donor.SOURCES[0]), str(source), str(REPO / donor.SOURCES[2]), str(bench)]
with (J / 'connected_build.log').open('w') as log:
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=None)
runs = []
for mut in range(5):
    run = donor.run(J / 'connected_obj' / ('V' + donor.TOP), OLD / 'work/inputs', 31,
                    donor.T_BG, nbg=0 if mut in (2, 4) else donor.NBG, mut=mut)
    runs.append(run)
    (J / f'connected_mut{mut}.json').write_text(json.dumps(run, indent=2) + '\n')
mismatches = [dict(mut=i,field=k,base=base.get(k),candidate=cand.get(k))
              for i,(base,cand) in enumerate(zip(prior['records']['candidate']['runs'],runs))
              for k in sorted(base.keys() | cand.keys()) if base.get(k) != cand.get(k)]
passed = not mismatches and runs[0]['verdict'] == 'PASS' and all(r['verdict']=='FAIL' for r in runs[1:])
record = dict(verdict='PASS' if passed else 'FAIL', source_sha256=sha(source),
              reference_source_sha256=prior['input_sha256']['rtl/hbm_accel/service/ot_hbm_accel_stream_pc_wb_digest.sv'],
              generated_bench_sha256=sha(bench), retained_record_sha256=sha(OLD/'verdict.json'),
              packed_input_sha256=prior['packed_input_sha256'], selection=dict(WA_LATE=1,DIGEST_CUT=1,CMD_MATCH_CUT=1),
              inputs=prior['inputs'], fixture_selection=prior['selection'], runs=runs, mismatches=mismatches,
              scope='same connected fixture, unchanged checker/stimulus/bytes; no 833ps physical or fulltoken rate claim')
(J/'connected_result.json').write_text(json.dumps(record,indent=2)+'\n')
print(record['verdict'], 'mismatches', len(mismatches))
raise SystemExit(0 if passed else 1)
