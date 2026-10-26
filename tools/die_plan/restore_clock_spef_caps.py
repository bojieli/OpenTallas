#!/usr/bin/env python3
"""Restore pin-access wire caps omitted by OpenROAD rsz::SpefWriter.

Scope: the explicitly checked ASAP7 RVT clock buffers (M1 terminals) and M9 top ports.
The native exporter records the pin-access resistors but excludes terminal-node
ground caps. Infer each missing half-cap from its native resistor and the SAME cap-profile estimate, retaining the
native via resistance. STANDARD layer R is used: native NDR width credit is
already applied and must not be divided a second time. Fail on other masters,
missing/disconnected resistors, or a restored CAP sum inconsistent with D_NET.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from mix_clock_spef import header,sections

# Checked A/Y pin geometry in ORFS asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef:
# every listed buffer has only M1 terminals, so the same M2 attachment + V1 wire-cap reconstruction applies.
# Cell input capacitance is supplied by Liberty, not inferred here. Other masters remain rejected.
M1_CLOCK_BUFFERS = {f"BUFx{s}_ASAP7_75t_R" for s in
                    ("2", "3", "4", "4f", "5", "6f", "8", "10", "12", "12f", "16f", "24")}


def restore(lines,width):
    total=float(lines[0].split()[2]);pininfo={};caps={};res=[];mode=None
    for line in lines[1:]:
        f=line.split()
        if not f:continue
        if f[0] in ['*CONN','*CAP','*RES','*END']:mode=f[0];continue
        if mode=='*CONN':
            if f[0]=='*I':
                if len(f)<5 or f[3]!='*D' or f[4] not in M1_CLOCK_BUFFERS or f[1].rsplit(':',1)[-1] not in ('A','Y'):
                    raise ValueError('pinCAP model requires a checked native RVT clock-buffer M1 A/Y pin')
                pininfo[f[1]]='cell'
            elif f[0]=='*P':pininfo[f[1]]='port'
        elif mode=='*CAP':
            if len(f)!=3:raise ValueError('coupled capacitance outside global-route clock scope')
            caps[f[1]]=float(f[2])
        elif mode=='*RES':
            if len(f)!=4:raise ValueError('invalid native resistor')
            res.append((f[1],f[2],float(f[3])))
    adj=defaultdict(list)
    for a,b,r in res:adj[a].append((b,r));adj[b].append((a,r))
    allnodes=set(adj)|set(pininfo)|set(caps)
    seen=set();todo=[next(iter(allnodes))]
    while todo:
        p=todo.pop()
        if p not in seen:seen.add(p);todo.extend(n for n,r in adj[p] if n not in seen)
    if seen!=allnodes:raise ValueError('disconnected native SPEF graph (missing segment/resistor)')
    tolerance=max(.0005,total*2e-5)
    original=sum(caps.values())
    if abs(total-original)<=tolerance:return lines,dict(added_caps=0,cap_ff=0.,checksum_error_ff=abs(total-original))
    new={};ports=[]
    for pin,kind in pininfo.items():
        if pin in caps:continue
        if len(adj[pin])!=1:raise ValueError('terminal must have exactly one native pin-access resistor')
        if kind=='port':ports.append(pin);continue
        # All checked native clock buffers have M1 terminals. The M2 attachment
        # resistor includes one V1, which must never receive NDR scaling.
        r=adj[pin][0][1];length=(r-.0172)/.0297127
        if length < -1e-3:raise ValueError('pin-access resistor inconsistent with clock-buffer M1/M2/V1 model')
        new[pin]=max(0.,length)*.174942/2
    if len(ports)>1:raise ValueError('clock native net has more than one public port; cap budget ambiguous')
    if ports:
        remaining=total-original-sum(new.values())
        if remaining < -tolerance:raise ValueError('cell pin caps exceed native D_NET cap budget')
        # Native D_NET includes terminal wire caps. A generated clock net
        # has at most one M9 port, so its missing cap is uniquely determined.
        new[ports[0]]=max(0.,remaining)
    error=abs(total-original-sum(new.values()))
    if error>tolerance:raise ValueError(f'pin-cap reconstruction differs from D_NET by {error:.6f}fF (allowed {tolerance:.6f})')
    out=[];in_cap=False;index=0;inserted=False
    def append_caps():
        nonlocal index,inserted
        if inserted:return
        for pin,cap in sorted(new.items()):index+=1;out.append(f'{index} {pin} {cap:.10f}\n')
        inserted=True
    for line in lines:
        if line.startswith('*CAP'):in_cap=True
        elif line.startswith('*RES'):
            if not in_cap:out.append('*CAP\n')
            append_caps();in_cap=False
        elif line.startswith('*') and not line.startswith(('*I ','*P ')):
            if in_cap:append_caps();in_cap=False
        elif in_cap and line.split():index=max(index,int(line.split()[0]))
        out.append(line)
    if not inserted:raise ValueError('native SPEF lacks resistor block')
    return out,dict(added_caps=len(new),cap_ff=sum(new.values()),checksum_error_ff=error)


def repair(source,out,width,clock=None,prefix="ck_"):
    expected=None
    if clock is not None:
        data=json.loads((Path(clock)/'nets.json').read_text());ports={p for _,p in data['ports']}
        expected={n['name'] if n['name'] in ports else prefix+n['name'] for n in data['nets']}
    seen=set()
    stats=dict(nets=0,clock_nets=0,passthrough_nets=0,added_caps=0,added_cap_ff=0.,max_checksum_error_ff=0.,width=width)
    with open(source) as src,open(out,'w') as dst:
        h,names,first=header(src)
        if names:raise ValueError('clock native exporter uses explicit names; unexpected NAME_MAP')
        dst.writelines(h)
        for name,lines in sections(src,first,names):
            stats['nets']+=1
            if expected is not None and name not in expected:
                dst.writelines(lines);stats['passthrough_nets']+=1;continue
            seen.add(name);stats['clock_nets']+=1
            fixed,s=restore(lines,width);dst.writelines(fixed);stats['added_caps']+=s['added_caps'];stats['added_cap_ff']+=s['cap_ff'];stats['max_checksum_error_ff']=max(stats['max_checksum_error_ff'],s['checksum_error_ff'])
    if expected is not None and seen!=expected:raise ValueError(f'native SPEF missing expected clock nets: {sorted(expected-seen)[:8]}')
    return stats

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--width',type=int,choices=[4,8],required=True);p.add_argument('--clock',type=Path);p.add_argument('--prefix',default='ck_')
    a=p.parse_args();print(json.dumps(repair(a.source,a.out,a.width,a.clock,a.prefix),indent=2))
