#!/usr/bin/env python3
"""Audit source-bit connectivity and unchanged physical pins after issuer aliasing.

This compares generated local master rectangles, independently of instance homes.
It establishes graph/pin identity only, never timing or physical qualification.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

SOURCE = 'tt_ctlm'
ISSUER = 'res_train_issue'
TAPS = {'me_go':('ib',0,0), 'me_tiles':('ib',19,36), 'me_ts':('ib',80,103),
        'me_split':('ib',251,254), 'me_oen':('ib',353,353),
        'tag_v':('c1',26,26), 'tag_last':('c1',139,139)}
COMMAND = {'train_start':1,'train_count':4,'capture_stride':32,'payload_write':1,'slot_count':4}


class View:
    def __init__(self, data):
        self.data=data
        self.insts={i['n']:i for i in data['insts']}
        self.aliases=data.get('port_join',{})
        self.errors=[]
        self.cache={}

    def resolve(self, inst, port, width):
        master=self.insts[inst]['m']
        real,bits=self.aliases.get(master,{}).get(port,(port,list(range(width))))
        if len(bits)!=width or len(set(bits))!=width:
            self.errors.append(f'malformed alias {inst}.{port}: width {width}')
        return [(inst,real,b) for b in bits]

    def pins(self, inst):
        master=self.insts[inst]['m']
        if master in self.cache:return self.cache[master]
        result={}
        for pin in self.data['masters'][master]['pins']:
            match=re.fullmatch(r'(.+?)(?:\[(\d+)\])?',pin['name'])
            port,index=match.groups()
            index=int(index or 0)
            real,bits=self.aliases.get(master,{}).get(port,(port,None))
            if bits is not None:
                if index>=len(bits):
                    self.errors.append(f'pin alias index out of range: {master}.{pin["name"]}')
                    continue
                index=bits[index]
            key=real,index
            if key in result:self.errors.append(f'duplicate numeric pin: {master}.{real}[{index}]')
            result[key]=(pin['layer'],pin['rect'])
        self.cache[master]=result
        return result

    def source_nets(self):
        result={}
        counts=Counter()
        for bus in self.data['buses']:
            if bus['c'] in ('clock_trunk','reset'):continue
            width=bus['n']
            endpoints=[self.resolve(i,p,width) for i,p in bus['e']]
            for ep in endpoints:
                if not ep or ep[0][0]!=SOURCE or ep[0][1] not in ('ib','c1'):continue
                for k,source in enumerate(ep):
                    counts[source]+=1
                    result[source]=set(e[k] for e in endpoints if len(e)==width)
        return result,counts


def audit(before,after):
    old,new=View(before),View(after)
    failures=[]
    nets0,counts0=old.source_nets()
    nets1,counts1=new.source_nets()
    affected=set()
    expected_issuer={}
    for sink,(real,lo,hi) in TAPS.items():
        for b in range(lo,hi+1):expected_issuer[SOURCE,real,b]=(ISSUER,sink,b-lo)
    for source in sorted(set(nets0)|set(nets1)):
        old_peers=nets0.get(source,set())
        current=nets1.get(source,set())
        expected=old_peers|({expected_issuer[source]} if source in expected_issuer else set())
        if current!=expected:
            failures.append(dict(kind='numeric_connectivity',source=source,
                                 missing=sorted(expected-current),unexpected=sorted(current-expected)))
        if counts0[source]!=1 or counts1[source]!=1:
            failures.append(dict(kind='source_multiconnection',source=source,
                                 before=counts0[source],after=counts1[source]))
        affected.update((i,p) for i,p,b in old_peers)
    # All expected TT bits must appear, independent of aliases in either input.
    for real,width in [('ib',380),('c1',341)]:
        for bit in range(width):
            source=SOURCE,real,bit
            if source not in nets0 or source not in nets1:
                failures.append(dict(kind='missing_source_bit',source=source))
    # A physical master may be reused by another instance outside these nets.
    # Audit every instance whose representation of a real port changed.
    for inst in set(old.insts)&set(new.insts):
        a0=old.aliases.get(old.insts[inst]['m'],{})
        a1=new.aliases.get(new.insts[inst]['m'],{})
        for port in {r for r,bits in list(a0.values())+list(a1.values())}:
            x0={a:rb for a,rb in a0.items() if rb[0]==port}
            x1={a:rb for a,rb in a1.items() if rb[0]==port}
            if x0!=x1:affected.add((inst,port))
    pin_count=0
    for inst,port in sorted(affected):
        p0,p1=old.pins(inst),new.pins(inst)
        keys={key for key in p0 if key[0]==port}
        current={key for key in p1 if key[0]==port}
        if keys!=current:
            failures.append(dict(kind='missing_or_extra_numeric_pin',instance=inst,port=port,
                                 missing=sorted(keys-current),unexpected=sorted(current-keys)))
        for key in sorted(keys&current):
            pin_count+=1
            layer0,r0=p0[key];layer1,r1=p1[key]
            if layer0!=layer1 or len(r0)!=4 or len(r1)!=4 or any(abs(a-b)>1e-8 for a,b in zip(r0,r1)):
                failures.append(dict(kind='pin_moved',instance=inst,port=port,bit=key[1],before=p0[key],after=p1[key]))
    # Validate every connected affected endpoint has exactly the physical bit it names.
    for view in (old,new):
        for bus in view.data['buses']:
            if bus['c'] in ('clock_trunk','reset'):continue
            for inst,port in bus['e']:
                bits=view.resolve(inst,port,bus['n'])
                if not bits or ((inst,bits[0][1]) not in affected and inst!=ISSUER):continue
                pins=view.pins(inst)
                for i,p,b in bits:
                    if (p,b) not in pins:
                        failures.append(dict(kind='unknown_endpoint_pin',instance=i,port=p,bit=b))
    command_count=0
    for port,width in COMMAND.items():
        buses=[b for b in after['buses'] if [ISSUER,port] in [list(e) for e in b['e']]]
        expect={(ISSUER,port)}|{(f'sp_res_ser_{b}',port) for b in range(3)}
        if len(buses)!=1 or buses[0]['n']!=width or {tuple(e) for e in buses[0]['e']}!=expect:
            failures.append(dict(kind='issuer_command_fanout',port=port))
        else:command_count+=width
    for error in old.errors+new.errors:failures.append(dict(kind='malformed_alias_or_pin',detail=error))
    mismatches=after.get('generated_plan_audit',{}).get('nonclock_reset_endpoint_bit_mismatches',[])
    if mismatches:failures.append(dict(kind='generated_endpoint_mismatches',count=len(mismatches),examples=mismatches[:5]))
    return dict(schema='opentallas.qwen.res-train-alias-audit.v1',
                scope='numeric source/sink identity and unchanged local physical rectangles for TT ib/c1 nets; no route qualification',
                verdict='PASS' if not failures else 'FAIL',
                baseline_source_commit=before.get('source_commit'),current_source_commit=after.get('source_commit'),
                source_bits=len(nets0),affected_ports=[dict(instance=i,port=p) for i,p in sorted(affected)],
                numeric_physical_pins_checked=pin_count,command_bits=command_count,
                failure_count=len(failures),failure_counts=dict(Counter(f['kind'] for f in failures)),
                failures=failures[:20])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('before',type=Path);ap.add_argument('after',type=Path)
    ap.add_argument('--output',type=Path)
    a=ap.parse_args()
    raw0,raw1=a.before.read_bytes(),a.after.read_bytes()
    result=audit(json.loads(raw0),json.loads(raw1))
    result['input_sha256']={'before':hashlib.sha256(raw0).hexdigest(),'after':hashlib.sha256(raw1).hexdigest()}
    result['input_files']={'before':str(a.before.resolve()),'after':str(a.after.resolve())}
    result['audit_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output=json.dumps(result,indent=2)+'\n'
    if a.output:a.output.write_text(output)
    print(output,end='')
    raise SystemExit(0 if result['verdict']=='PASS' else 1)


if __name__=='__main__':main()
