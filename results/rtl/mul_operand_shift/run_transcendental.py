"""Qualify candidate multiplier in the complete exp/sigmoid consumer."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools import run_a3_hc_transcendental_rtl_campaign as campaign

OUT = Path(__file__).resolve().parent
BUILD = ROOT/'build/mul_shift_full_trans'
SOURCES = ['results/rtl/mul_operand_shift/candidate.sv',
           *campaign.RTL_SOURCES[1:]]


def main():
    inventory = json.loads((OUT/'consumer_sources.json').read_text())
    def verify():
        for name, expected in inventory.items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name
    verify()
    verilator = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    command = [str(verilator), '--binary', '--timing', '-j', '2', '-Wno-fatal',
               '--top-module', 'tb_a3_hc_transcendental', '--Mdir', str(BUILD), *SOURCES]
    with (OUT/'transcendental_compile.log').open('w') as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = subprocess.run([str(BUILD/'Vtb_a3_hc_transcendental'),
                             '+CASES=testdata/rtl/a3_hc_transcendental/cases.hex'],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    (OUT/'transcendental.log').write_text(result.stdout+result.stderr)
    summary, checks = campaign.parse_log(result.stdout+result.stderr)
    manifest = json.loads((campaign.VECTOR_DIR/'index.json').read_text())
    campaign.validate_observed(summary, checks, manifest)
    verify()
    print(summary, checks)


if __name__ == '__main__':
    main()
