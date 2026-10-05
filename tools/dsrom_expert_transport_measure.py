#!/usr/bin/env python3
"""Exact native/conditional expert payload sizes on the existing recovery-hop endpoint."""
from __future__ import annotations
import argparse
import json
import math
import subprocess
from pathlib import Path
import dsrom_1m_links as L

ROOT = Path(__file__).resolve().parents[1]
CASES = {2304: ("packed_gu_conditional", "Conditional BF16-packed GU return; pack/unpack unbound"),
         4608: ("native_gu_or_packed_w2", "Native raw32 GU return; also conditional packed W2 input"),
         9216: ("native_w2_input", "Native raw32 W2 input"),
         20480: ("native_field_input", "Native raw32 field input")}
SHAPE_CONTRACT = "results/rtl/dsrom_recovery_20261004/expert_placement_sweep/HANDOFF.txt"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--payload-bytes', required=True, help='Comma-separated exact sizes; select only missing cases')
    a = p.parse_args()
    sizes = [int(x) for x in a.payload_bytes.split(',')]
    if len(set(sizes))!=len(sizes) or any(x not in CASES for x in sizes):
        raise SystemExit('Only distinct source-bound 2304/4608/9216/20480 byte cases supported')
    if a.out.exists() or a.work.exists():
        raise SystemExit('Existing results/work: reuse; do not overwrite or duplicate')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise SystemExit('Requires clean pinned source')
    base_path = ROOT/'results/rtl/dsrom_recovery_20261004/draft/rlinks.json'
    base = json.loads(base_path.read_text())
    pins = {s:L.sha(ROOT/s) for s in L.HOP_RTL}
    if pins != base['sources']:
        raise SystemExit('Endpoint sources differ from retained RECOVERY_HOPS; obtain owner binding')
    defines = dict(FB=64, CH=L.CH_LFEC, CHU=L.CH_UCIE, CRED=512, SEQW=10, CREDU=64, SEQWU=8)
    phy = L.phy_Bps()
    model = dict(clock_domain='streaming', clock_hz=L.CLK, defines=defines,
        cases={CASES[b][0]:dict(payload_B=b, payload_bits=8*b, payload_flits=math.ceil(b/64), role=CASES[b][1]) for b in sizes},
        source_shape_contract=SHAPE_CONTRACT, source_shape_sha256=L.sha(ROOT/SHAPE_CONTRACT),
        source_shape_commit="7095e772abb58b1ff3b0fec2e82a1fcfaca90cdb",
        endpoint_bytes_per_cycle=64, board_vendor_ns=L.LFEC_NS, ucie_vendor_ns=L.UCIE_NS,
        wire_cycles=2*L.SERDES_STAGES, phy_Bps=phy,
        rule='Measured last_flit includes vendor delay lines. Add only PHY serialization beyond endpoint plus '
             '90 wire cycles, once. No interpolation; no collective or concurrent-group measurement.',
        model_basis='Existing RECOVERY_HOPS endpoint/calendar and Arendt GU2304B/W2input4608B boundary',
        baseline_record=str(base_path.relative_to(ROOT)), baseline_sha256=L.sha(base_path),
        endpoint_source_sha256=pins)
    a.work.mkdir(parents=True)
    (a.work/'model_before_measurement.json').write_text(json.dumps(model,indent=2)+'\n')
    hops = {}
    for size in sizes:
        name, role = CASES[size]
        r = L.run_hop_case(a.work, (name, defines, size, role))
        f = r['fields']
        (a.work/(name+'.summary.log')).write_text(r['summary']+'\n')
        expected = math.ceil(size/64)
        exact = r['exact'] and f['sent']==expected and f['rcvd']==expected and all(
            f[k]==0 for k in ('mism','extra','fault1','fault2'))
        phy_cycles = size/phy*L.CLK
        extra = max(0, math.ceil(phy_cycles-f['flits']-1e-9)) if phy_cycles>f['flits'] else 0
        vendor = L.CH_LFEC+L.CH_UCIE
        endpoint = f['last_flit']-vendor
        total = f['last_flit']+extra+2*L.SERDES_STAGES
        hops[name] = dict(payload_B=size, role=role, exact=exact, fields=f, summary=r['summary'],
            measured_rtl_cycles_including_vendor=f['last_flit'], measured_endpoint_cycles=endpoint,
            vendor_cycles=dict(board=L.CH_LFEC, ucie=L.CH_UCIE), vendor_budget_ns=dict(board=L.LFEC_NS, ucie=L.UCIE_NS),
            phy_serialization_cycles=phy_cycles, phy_serialization_extra_cycles=extra,
            wire_cycles=2*L.SERDES_STAGES, total_cycles=total, total_us=total/L.CLK*1e6,
            components_us=dict(endpoint=endpoint/L.CLK*1e6, vendor=vendor/L.CLK*1e6,
                               phy_extra=extra/L.CLK*1e6, wire=2*L.SERDES_STAGES/L.CLK*1e6))
        assert total==endpoint+vendor+extra+2*L.SERDES_STAGES
        print(name, r['summary'], 'total_cycles', total, flush=True)
    record = dict(schema='opentallas.dsrom.expert-transport.v1',
        verdict='PASS_ENDPOINT_PAYLOAD_ONLY' if all(h['exact'] for h in hops.values()) else 'FAIL',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        model=model, hops=hops, tool_sha256=L.sha(Path(__file__)),
        helper_sha256=L.sha(ROOT/'tools/dsrom_1m_links.py'),
        scope='Hash-pattern payload order/data/last checks on one idle endpoint message. Not actual GU provider '
              'or six-group fanout, mutable context/visibility/consumer calendar, SS60/FF25 or token qualification.',
        physical_qualified=False, adoption=False)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(record,indent=2)+'\n')
    return 0 if record['verdict']=='PASS_ENDPOINT_PAYLOAD_ONLY' else 1


if __name__=='__main__':
    raise SystemExit(main())
