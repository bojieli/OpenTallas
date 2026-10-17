#!/usr/bin/env python3
"""Enumerate actual Q3H register owners; no common clock fallback, no native claim.

The ABI lists a separate planned external entry for each real child clock port and
for each fabric register bank/stage. The physical clock owner must supply measured
phi-R and neighbour pairs before the ABI may be used for binding. Run-pad clocks
are enumerated by actual constant stages, not by the 5.2-mm run's parent clock.
"""
import argparse, hashlib, json, re
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--fabric',required=True);ap.add_argument('--contract',required=True)
    ap.add_argument('--nk',required=True);ap.add_argument('--nl',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();fabric=Path(a.fabric).read_text();contract=json.loads(Path(a.contract).read_text())
    entries=[]
    def add(name,owner,role,sinks=None,location=None):
        entries.append(dict(port=name,owner=owner,role=role,sinks=sinks,centre_um=location,
                            native='UNMEASURED',clock='related 1.2GHz, regional forwarded neighbour clocks',required_phi_minus_R=True))
    for child in contract['children']['tiles']:
        c,r=child['slot']; kind='nl' if 'nl_' in child['master'] else 'nk'
        text=Path(getattr(a,kind)).read_text()
        ports=re.findall(r'input\s+wire\s+(ck\w*)\s*[,\n]',text)
        assert ports and len(set(ports))==len(ports)
        for port in ports:
            add(f'ck_t{c}_{r}_{port}',f"{child['inst']}.{port}",'hard_tile_clock',None,
                None)
    # Every actual fabric clocked instance is a sink owner. A run of D stages is
    # D owners: no 5-mm run is treated as a local root merely because it has one clk.
    consumed=set()
    for line in fabric.splitlines():
        m=re.search(r'qfd_q3h_stn #\(\.W\((\d+)\), \.N\((\d+)\)\) (\w+) \(\.ck\(ck\)',line)
        if m:
            w,n,inst=m.groups();loc=re.search(r'// \(([\d.]+), ([\d.]+)\)',line)
            add('ck_f_'+inst,'u_fab.'+inst+'.q_r','fabric_register_bank',int(w),
                list(map(float,loc.groups())) if loc else None);consumed.add(inst);continue
        m=re.search(r'qfd_xcst_n (\w+) \(\.ck\(ck\)',line)
        if m:
            inst=m.group(1);add('ck_f_'+inst,'u_fab.'+inst,'corridor_station',None);consumed.add(inst);continue
        m=re.search(r'qfd_q3h_run #\(\.W\((\d+)\), \.D\((.*?)\)\) (\w+) \(\.ck\(ck\)',line)
        if m:
            w,depth,inst=m.groups()
            dm=re.fullmatch(r'MUT == \d+ \? \d+ : (\d+)',depth.strip('()'))
            if dm: depth=dm.group(1)
            if not depth.isdigit():raise ValueError('nonconstant unrecognized run '+line)
            for stage in range(int(depth)):
                add(f'ck_f_{inst}_s{stage}',f'u_fab.{inst}.g_run.g_s[{stage}].u_s.q_r','fabric_run_stage',int(w))
            consumed.add(inst)
    expected=len(re.findall(r'\.ck\(ck\)',fabric))
    if len(consumed)!=expected:raise ValueError(f'unclassified clocks: {len(consumed)} vs {expected}')
    doc=dict(schema='opentallas.qwen.q3h.regional_clock_abi.plan.v1',qualification=False,adopted=False,
       contract_outline_um=contract['outline_um'],status='PLAN: physical entries, sites and measured native clock delivery pending',
       added_data_stages=0,added_clocked_flops_from_rewire=0,
       entries=entries,total_entries=len(entries),
       tile_entries=sum(x['role']=='hard_tile_clock' for x in entries),
       fabric_entries=sum(x['role']!='hard_tile_clock' for x in entries),
       known_fabric_flops=sum(x['sinks'] or 0 for x in entries if x['role']!='hard_tile_clock'),
       unknown_station_sinks=sum(x['role']=='corridor_station' for x in entries),
       physical_obligations=['Literal port per real region, never tie all to one global ck',
          'Actual clock pins owned by their own hard leaf or bank; all entry ports must be timed',
          'Regional reset follows existing fixed-stage tree; actual-neighbour clock pairs<=80ps required',
          'Source-bounded run-stage coordinates/reach and native views before ABI binding',
          'Current single-ck diagnostic RTL is preserved, not replaced by this unmeasured plan'],
       source_sha256={k:hashlib.sha256(Path(getattr(a,k)).read_bytes()).hexdigest() for k in ['fabric','contract','nk','nl']})
    Path(a.out).write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps({k:doc[k] for k in ['total_entries','tile_entries','fabric_entries','known_fabric_flops','unknown_station_sinks']}))
if __name__=='__main__':main()
