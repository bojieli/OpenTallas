#!/usr/bin/env python3
"""Prepare the minimum real-F20 SU installation/command-execution vehicle.

Use an actual emitted su_prog*/cols/config.mem and its sibling quarter.mem.
The bench drives AXI F20/F24/F28/F2c/F30 through the real ingress and collar,
then checks the real root and SRAM-backed producer's executed command stream.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import re


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--rev', required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--programme', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    c = json.loads(a.contract.read_text())['instances']
    assert c['col_su']['params'].get('SPARSE_SU') == 1, 'actual source contract must enable SPARSE_SU'
    assert c['col_su']['master'] == 'ot_hbm_static_cfg_collar'
    assert c['pgp_SW']['master'] == 'ot_hbm_su_programme_pslice_c5'
    assert c['pgp_SW']['params']['SB'] == 2470
    assert c['su_prog']['master'] == 'ot_hbm_su_programme_root_h5'
    rows = (a.programme / 'cols/config.mem').read_text().split()
    lines = (a.programme / 'quarter.mem').read_text().split()
    assert rows and lines and all(int(s, 16) < 1 << 2470 for s in lines)
    a.out.mkdir(parents=True, exist_ok=True)
    sources = dict(ingress=c['host_cp_ingress']['source'], collar_sparse_final=c['col_su']['source'],
                   root=c['su_prog']['source'], pgcol=c['pgp_SW']['source'],
                   programme='rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv',
                   rst='rtl/lib/ot_rst_relay.sv',
                   sram='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v')
    identities = {}
    for name, source in sources.items():
        assert not Path(source).is_absolute(), 'source must be pinned in the release revision'
        content = subprocess.check_output(['git', '-C', str(a.repo), 'show', f'{a.rev}:{source}'])
        (a.out / (name + ('.v' if name == 'sram' else '.sv'))).write_bytes(content)
        identities[name] = dict(path=source, sha256=hashlib.sha256(content).hexdigest())
    tb = a.repo / 'rtl/test/tb_hbm_host_su_sparse_install.sv'
    bench = tb.read_text()
    cap = c['col_su']['params'].get('SU_DICT_CAP')
    assert isinstance(cap, (str, int)), 'actual SU aperture must be explicit'
    if isinstance(cap, int):
        cap = f"320'h{cap:x}"
    assert re.fullmatch(r"[0-9a-fA-F_'dhb{},\s]+", cap), 'unexpected aperture expression'
    bench = bench.replace('.SPARSE_SU(1),', f'.SU_DICT_CAP({cap}),.SPARSE_SU(1),')
    mask = c['host_cp_ingress']['params']['TARGET_MASK']
    assert re.fullmatch(r"256'h[0-9a-fA-F]+", mask), 'unexpected target mask'
    bench = bench.replace(".TARGET_MASK(256'd1<<112)", f'.TARGET_MASK({mask})')
    (a.out / 'tb_sparse_final.sv').write_text(bench)
    (a.out / 'image.mem').write_text(''.join(f'{int(r[:4],16)*128+int(r[4:6],16):06x}{int(r[6:],16):064x}\n' for r in rows))
    (a.out / 'quarter.mem').write_text('\n'.join(lines) + '\n')
    (a.out / 'identity.json').write_text(json.dumps(dict(
        schema='opentallas.hbm.host-su-install.v1', source_revision=a.rev,
        contract_sha256=hashlib.sha256(a.contract.read_bytes()).hexdigest(),
        programme_sha256=hashlib.sha256((a.programme/'cols/config.mem').read_bytes()).hexdigest(),
        words=len(rows), commands=len(lines), sources=identities,
        params={n:c[n]['params'] for n in ('col_su','pgp_SW')},
        scope='F20 ingress to executed SU commands; no link-PMA or die timing claim'), indent=1) + '\n')
    source_args = 'tb_sparse_final.sv ingress.sv collar_sparse_final.sv root.sv rst.sv pgcol.sv programme.sv sram.v'
    (a.out / 'run.sh').write_text(f'''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for c in 0 2 3 4 5 6 7;do
  iverilog -g2012 -s tb_hostprog -P tb_hostprog.N={len(rows)} -P tb_hostprog.LINES={len(lines)} -P tb_hostprog.CASE=$c -o final$c.vvp {source_args} > final_compile$c.log 2>&1
  vvp -n final$c.vvp | tee final$c.log
done
''')
    print(f'HOST_SU_INSTALL_PREPARED words={len(rows)} commands={len(lines)} source={a.rev}')


if __name__ == '__main__':
    main()
