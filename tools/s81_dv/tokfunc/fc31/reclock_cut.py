#!/usr/bin/env python3
"""TOK-DS-GAPS 10-24: re-class the slice region clock ports of an EXISTING cut (made before dv_slice_cut CLOCK_PORT_RE
learned ck_<REGION>) and regenerate its replay bench.  slice_top.sv is untouched (byte-identical); only slice_ports.json
kinds (die_input -> clock for every cut input whose net drives an instance pin .ck_<REGION>(...)) and the tb change, so
port indices (and every replay in.txt / out.txt) stay valid.  The new kit = the old kit with tb/tb_slice_top.sv replaced.
  reclock_cut.py --cut CUTDIR --kit KITDIR --out-cut NEWCUT --out-kit NEWKIT
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
TB = HERE.parents[2] / 'dv_slice_tb.py'
PIN = re.compile(r'\.(ck_[A-Z][A-Z0-9_]*)\(\s*(\w+)\s*\)')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ('--cut', '--kit', '--out-cut', '--out-kit'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    cut, kit, oc, ok = map(Path, (a.cut, a.kit, a.out_cut, a.out_kit))
    if oc.exists() or ok.exists():
        sys.exit('reclock: output exists (fresh dirs only)')
    shutil.copytree(cut, oc)
    shutil.copytree(kit, ok, symlinks=True)
    nets = {m.group(2): m.group(1) for m in PIN.finditer((cut / 'slice_top.sv').read_text())}
    D = json.loads((cut / 'slice_ports.json').read_text())
    P = D['ports']
    changed = []
    for name, p in P.items():
        if p['dir'] == 'input' and p['kind'] != 'clock' and p.get('net') in nets:
            p['kind'], p['clock_from'] = 'clock', [p['net']]
            changed.append(dict(port=name, pin=nets[p['net']]))
    (oc / 'slice_ports.json').write_text(json.dumps(D, indent=1) + '\n')
    subprocess.run([sys.executable, str(TB), '--ports', str(oc / 'slice_ports.json'), '--top', 'slice_top',
                    '--out', str(oc)], check=True)
    old = json.loads((cut / 'tb_ports.json').read_text())
    new = json.loads((oc / 'tb_ports.json').read_text())
    if [(p['index'], p['port']) for p in old] != [(p['index'], p['port']) for p in new]:
        sys.exit('reclock: port indices changed')
    shutil.copy(oc / 'tb_slice_top.sv', ok / 'tb' / 'tb_slice_top.sv')
    rec = dict(schema='opentallas.s81_dv.reclock_cut.v1', cut=str(cut), kit=str(kit), reclocked=changed,
               slice_top_unchanged=(cut / 'slice_top.sv').read_bytes() == (oc / 'slice_top.sv').read_bytes())
    (oc / 'reclock.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f'RECLOCK {len(changed)} ports: ' + ' '.join(c['port'] for c in changed))


if __name__ == '__main__':
    main()
