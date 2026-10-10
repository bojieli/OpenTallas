#!/usr/bin/env python3
"""Check the elaborated NW21 MTP ports against the generated die bus chains.

This is a wiring/inventory audit, not an identity-composition or physical gate.
The sequencer's component closure never closes the complete native-binding row.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S

GROUPS = {
    ('capture', 'mtp'): ('f_rv', 'f_rd', 't_rg'),
    ('mtp', 'collective'): ('t_tv', 't_td', 'f_tg', 't_sv', 't_sd', 'f_sg', 't_acc'),
    ('vm', 'mtp'): ('f_wv', 'f_wd', 't_wg', 'f_qv', 'f_qd', 't_qg'),
    ('mtp', 'vm'): ('t_hv', 't_hd', 'f_hg'),
}
SRCS = ['rtl/dsrom_sys/mtp/' + p for p in
        ('dsfd_mtp_tops.sv', 'ot_dsrom_mtp_seq.sv', 'ot_dsrom_mtp_link_pair.sv', 'ot_dsrom_mtp_skid.sv')]


def audit(floorplan):
    ports = list(dict.fromkeys(p for group in GROUPS.values() for p in group)) + ['f_cfg']
    tb = 'module audit; dsfd_mtp_seq dut(); initial begin\n' + ''.join(
        f'$display("PORT {p} %0d", $bits(dut.{p}));\n' for p in ports) + '$finish; end endmodule\n'
    with tempfile.TemporaryDirectory(prefix='mtp-port-audit-') as d:
        d = Path(d)
        (d / 'audit.sv').write_text(tb)
        subprocess.run(['iverilog', '-g2012', '-s', 'audit', '-o', str(d / 'audit.vvp'),
                        *[str(ROOT / s) for s in SRCS], str(d / 'audit.sv')], check=True, capture_output=True)
        log = subprocess.run(['vvp', str(d / 'audit.vvp')], check=True, capture_output=True, text=True).stdout
    widths = {a: int(b) for _, a, b in (l.split() for l in log.splitlines() if l.startswith('PORT '))}
    assert set(widths) == set(ports), 'missing elaborated ports'
    fp = json.loads(floorplan.read_text())
    chains = {c['chain']: c for c in fp['chains']}
    buses = []
    for a, b, bits, src_port, dst_port in S.MTP_SEQ_BUSES:
        parts = GROUPS[(a, b)]
        actual = sum(widths[p] for p in parts)
        chain = chains[f'hb_{a}_{b}']
        assert actual == bits == sum(chain['lanes']), (a, b, actual, bits, chain['lanes'])
        buses.append(dict(source=a, destination=b, bits=actual, ports={p: widths[p] for p in parts},
                          chain=chain))
    assert len(buses) == len(GROUPS), 'missing bus class'
    assert fp['variant']['mtp_seq'] is not None, 'head die does not carry sequencer'
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
              SRCS + ['tools/dsrom_s81_fulldie.py', 'tools/mtp_native_binding_audit.py']}
    return dict(schema='opentallas.mtp.native_bus_binding.v1',
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                source_sha256=hashes, floorplan=str(floorplan.relative_to(ROOT)),
                floorplan_sha256=hashlib.sha256(floorplan.read_bytes()).hexdigest(),
                port_elaboration_log=log, static_config_bits=widths['f_cfg'], buses=buses,
                aggregate_bits=sum(b['bits'] for b in buses), bus_binding_passed=True,
                identity_composition_qualified=False, physical_qualified=False,
                remaining=['seed/draft native endpoint identity join', 'verify causal path',
                           'rollback committed-state join', 'full production head inventory',
                           'routed die timing and DRC'],
                scope='Elaborated wrapper ports and generated head631 bus chains only; historical storage recipe.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--floorplan', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    receipt = audit(a.floorplan.resolve())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x') as f:
        json.dump(receipt, f, indent=2)
        f.write('\n')
    print(f"MTP BUS BINDING PASS {receipt['aggregate_bits']} bits across {len(receipt['buses'])} chains; integration OPEN")
