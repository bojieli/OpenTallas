"""Compare exact published intervals and latency for the full reference corpus."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools import run_a3_hc_transcendental_rtl_campaign as campaign


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    build = ROOT/'build/transcendental_tail_fold'
    build.mkdir(parents=True, exist_ok=True)
    original = (ROOT/campaign.RTL_SOURCES[-1]).read_text()
    marker = '            hold_cycles = (index % 17 == 0) ? 3 :'
    trace = '''            $display("TAIL_CASE index=%0d cycles=%0d result=%h error=%h exact=%b lower=%h upper=%h",
                index, guard, result_code, result_error, dut.interval_exact,
                dut.interval_lower_out, dut.interval_upper_out);
'''
    assert original.count(marker) == 1
    bench = build/'tb.sv'
    bench.write_text(original.replace(marker, trace+marker))
    inventories = {}
    rows = {}
    for variant in ('baseline', 'candidate'):
        sources = [*campaign.RTL_SOURCES[:-2],
                   campaign.RTL_SOURCES[-2] if variant == 'baseline' else
                   str((HERE/'candidate.sv').relative_to(ROOT)), str(bench.relative_to(ROOT))]
        inventory = {name: digest(ROOT/name) for name in sources}
        inventory.update({str((campaign.VECTOR_DIR/name).relative_to(ROOT)):
                          digest(campaign.VECTOR_DIR/name) for name in campaign.VECTOR_FILES})
        inventories[variant] = inventory
        cmd = [str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),
               '--binary', '--timing', '-j', '2', '-Wno-fatal', '--top-module',
               'tb_a3_hc_transcendental', '--Mdir', str(build/variant), *sources]
        with (HERE/(variant+'_compile.log')).open('w') as log:
            subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        with (HERE/(variant+'.log')).open('w') as log:
            subprocess.run([str(build/variant/'Vtb_a3_hc_transcendental')], cwd=ROOT,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        log = (HERE/(variant+'.log')).read_text()
        summary, checks = campaign.parse_log(log)
        assert 'FAIL' not in log
        if variant == 'baseline':
            campaign.validate_observed(summary, checks,
                                       json.loads((campaign.VECTOR_DIR/'index.json').read_text()))
        rows[variant] = [dict(re.findall(r'(\w+)=(\w+)', line)) for line in log.splitlines()
                         if line.startswith('TAIL_CASE ')]
        assert len(rows[variant]) == 4200
        for name, expected in inventory.items():
            assert digest(ROOT/name) == expected, name
    saved = []
    for before, after in zip(rows['baseline'], rows['candidate']):
        for key in ('index', 'result', 'error', 'exact'):
            assert before[key] == after[key], (key, before, after)
        if before['exact'] == '1':
            for key in ('lower', 'upper'):
                assert before[key] == after[key], (key, before, after)
        delta = int(before['cycles']) - int(after['cycles'])
        assert delta >= 0, (before, after)
        saved.append(delta)
    base_cycles = sum(int(r['cycles']) for r in rows['baseline'])
    candidate_cycles = sum(int(r['cycles']) for r in rows['candidate'])
    result = {'scope': 'Full 4200-case exp/sigmoid reference corpus, exact published interval comparison; active service cycles, not clock or model latency.',
              'cases': len(saved), 'faster_cases': sum(x > 0 for x in saved),
              'baseline_cycles': base_cycles, 'candidate_cycles': candidate_cycles,
              'saved_cycles': sum(saved), 'cycle_reduction_percent': 100*sum(saved)/base_cycles,
              'max_saved_cycles_per_case': max(saved),
              'exact_interval_endpoints_match': True, 'production_integrated': False}
    (HERE/'sources.json').write_text(json.dumps(inventories, indent=2)+'\n')
    (HERE/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
