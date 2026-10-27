"""Audit native FUSED/VM buddy transport in a materialized MU hub candidate.
This is a structural contract check, not timing/throughput or native RTL equivalence.
"""
import argparse,json,re
from pathlib import Path


def audit(cores,stations,expected_lanes=16):
    names={c['inst'] for c in cores}
    banks={n for n in names if n.startswith('u_vmb_')}
    lanes={n for n in names if re.fullmatch(r'u_mu_fused_\d+',n)}
    def owner(label):
        matches=[n for n in names if label==n or label.startswith(n+'.')]
        return max(matches,key=len) if matches else None
    errors=[];rows=[];pairs={};other_serial=[]
    for i,s in enumerate(stations):
        a=owner(str(s.get('launch','')));b=owner(str(s.get('capture','')))
        serial=int(s.get('serial_k',1))
        if (a in banks or b in banks) and serial>1:other_serial.append(i)
        if a in banks and b in lanes: bank,lane,kind,expected=a,b,'rd',257
        elif a in lanes and b in banks:
            bank,lane=b,a;kind='rq' if int(s['bits'])==18 else 'wr';expected=18 if kind=='rq' else 282
        else:continue
        row=dict(station=i,bank=bank,lane=lane,kind=kind,bits=s['bits'],serial_k=serial,relay_stations=len(s.get('regs_um',[])),conn=s.get('conn'))
        rows.append(row);pairs.setdefault((bank,lane),[]).append(row)
        if serial!=1 or s.get('r11_cc_serial'):errors.append(f'station {i}: native buddy link serialized')
        if int(s['bits'])!=expected:errors.append(f'station {i}: {kind} width {s["bits"]} != {expected}')
    if len(banks)!=expected_lanes or len(lanes)!=expected_lanes:
        errors.append(f'bank/lane count {len(banks)}/{len(lanes)} != {expected_lanes}/{expected_lanes}')
    if len(pairs)!=expected_lanes:errors.append(f'buddy pair count {len(pairs)} != {expected_lanes}')
    for (bank,lane),rs in pairs.items():
        if sorted(r['kind'] for r in rs)!=['rd','rq','wr']:errors.append(f'{bank}/{lane}: expected one rd/rq/wr')
    for bank in banks:
        if sum(b==bank for b,l in pairs)!=1:errors.append(f'{bank}: not exactly one FUSED buddy')
    for lane in lanes:
        if sum(l==lane for b,l in pairs)!=1:errors.append(f'{lane}: not exactly one VM buddy')
    return dict(schema='opentallas.hbm_fused_vm_census.v1',verdict='PASS' if not errors else 'FAIL',
        scope='model native buddy identity/width/serialization only; no physical or throughput signoff',
        banks=len(banks),lanes=len(lanes),buddy_records=len(rows),pairs=len(pairs),errors=errors,
        buddy_relay_stations_total=sum(r['relay_stations'] for r in rows),
        serialized_vm_station_indices=other_serial,buddy_rows=rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('candidate');ap.add_argument('--out',required=True)
    ap.add_argument('--expected-lanes',type=int,default=16);a=ap.parse_args();d=json.loads(Path(a.candidate).read_text())
    r=audit(d.get('cores',d.get('hard_cores',[])),d.get('stations',d.get('internal_stations',[])),a.expected_lanes)
    Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='buddy_rows'},indent=1))
    return r['verdict']!='PASS'
if __name__=='__main__':raise SystemExit(main())
