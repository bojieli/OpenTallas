#!/usr/bin/env python3
"""Check exact K32 and K128 runtime key encoding for replicated stacks."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / 'rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv'
TB = ROOT / 'rtl/test/tb_hdc_v41x_idx_pool_kwr.sv'
OUT = ROOT / 'results/rtl/hdc_v41x_idx_pool_kwr_campaign.json'
VVP = Path('/tmp/claude-1000/idx_pool_kwr.vvp')


def main() -> None:
    VVP.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['iverilog', '-g2012', '-s', 'tb_hdc_v41x_idx_pool_kwr',
                    '-o', str(VVP), str(RTL), str(TB)], check=True)
    run = subprocess.run(['vvp', str(VVP)], capture_output=True, text=True, check=True)
    m = re.search(r'V41XPOOLKWR checked=(\d+) errors=(\d+) keys=(\d+)', run.stdout)
    if not m:
        raise RuntimeError(run.stdout + run.stderr)
    checked, errors, keys = map(int, m.groups())
    assert checked == 2 and errors == 0 and keys == 2
    src = [RTL, TB, Path(__file__).resolve()]
    rec = dict(schema='opentallas-hdc-v41x-idx-pool-kwr-v1', status='pass',
               kdim=[32, 128], checked=checked, errors=errors,
               stack_replication=4, encoded_bytes_per_key=68,
               logical_storage_bytes_per_key=272,
               sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in src})
    OUT.write_text(json.dumps(rec, indent=1) + '\n')
    print(run.stdout.strip())


if __name__ == '__main__':
    main()
