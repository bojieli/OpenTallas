"""Read-only actual-Lib virtual cut at the core side of the shipped pin wrapper.

This is structural evidence only. It cannot admit a different kit or replace a
fresh mapped census, actual placement, pin anchoring or native capture audit.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

INPUTS = dict(c_in=4,row_in=64,e_in=16,lt_in=12,hid=2,bsel=2,
              q_valid_in=1,q_beat_in=6,q_data_in=128)
OUTPUTS = dict(kp=32,kpv=1,nb=64,gf=1)


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--source',required=True);ap.add_argument('--netlist',required=True)
    ap.add_argument('--native-report',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();src=Path(a.source)
    sys.path.insert(0,str(src/'tools/ref_tile'));sys.path.insert(0,str(src/'tools'))
    import native_census as N
    from dft import liberty as L
    from dft.scan_insert import sequential_role
    receipt=json.loads(Path(a.native_report).read_text());paths=[r['path'] for r in receipt['liberty']]
    roles,libs=N.liberty_roles(paths)
    if libs!=receipt['liberty']:raise ValueError('actual loaded Liberty bytes changed')
    cells=L.load_cells(paths,Path(a.out).parent/'cache')
    raw=Path(a.netlist).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=receipt['netlist']['sha256']:raise ValueError('mapped identity changed')
    mods=N.TL.parse_verilog(raw.decode());mods={k:v for k,v in mods.items() if k==receipt['top'] or k not in roles}
    g,_=N.TL.flatten(mods,receipt['top'])
    drivers={};loads={};unary={};seq={};errors=[]
    for i,(master,name,pins) in enumerate(g.cells):
        if master not in roles:raise ValueError('missing actual Liberty role '+master)
        r=roles[master];ins=[];outs=[]
        for p,nets in pins.items():
            if p not in r['pins'] or len(nets)!=1:raise ValueError('unsupported actual pin shape '+master+'/'+p)
            n=nets[0];pr=r['pins'][p]
            if pr['direction']=='input':
                loads.setdefault(n,[]).append((i,p));ins.append((p,n))
            elif pr['direction']=='output':
                if n in drivers:raise ValueError('multiple drivers')
                drivers[n]=(i,p);outs.append((p,n))
            else:raise ValueError('unsupported pin direction')
        if r['sequential']:
            sr=sequential_role(cells[master])
            if not sr:raise ValueError('not an actual edge-triggered flop '+master)
            seq[i]=sr
        elif len(ins)==len(outs)==1:
            f=re.sub(r'[\s()]','',r['pins'][outs[0][0]]['function'] or '')
            if f in (ins[0][0],'!'+ins[0][0],'~'+ins[0][0],ins[0][0]+"'"):
                unary[i]=(ins[0][1],outs[0][1])
    def net(port,bit,kind):
        key=f'{port}__ot_{kind}[{bit}]'
        if key not in g.net_id:raise ValueError('missing virtual cut net '+key)
        return g.find(g.net_id[key])
    report={}
    for port,width in INPUTS.items():
        rows=[]
        for bit in range(width):
            start=net(port,bit,'q');todo=[(start,0)];seen=set();ends=[];bad=[]
            while todo:
                n,h=todo.pop()
                if n in seen:continue
                seen.add(n)
                if not loads.get(n):bad.append('unloaded virtual input')
                for ci,pin in loads.get(n,[]):
                    master,name,pins=g.cells[ci]
                    if ci in unary:todo.append((unary[ci][1],h+1))
                    elif ci in seq and pin in seq[ci]['data_pins']:
                        if not name.startswith('u_ot_pr_core.'):
                            bad.append('capture outside core '+name)
                        ends.append(dict(instance=name,master=master,pin=pin,unary_hops=h))
                    else:bad.append('unregistered/nondata endpoint '+name+'/'+pin)
            if bad or not ends:errors.append(dict(port=port,bit=bit,errors=bad))
            rows.append(dict(bit=bit,captures=ends,errors=bad))
        report[port]=dict(direction='input',width=width,bits=rows)
    for port,width in OUTPUTS.items():
        rows=[]
        for bit in range(width):
            n=net(port,bit,'pr');seen=set();h=0;bad=[];end=None
            while True:
                if n in seen:bad.append('driver cycle');break
                seen.add(n)
                if n not in drivers:bad.append('missing driver');break
                ci,pin=drivers[n];master,name,_=g.cells[ci]
                if ci in unary:n=unary[ci][0];h+=1;continue
                if ci in seq and pin in seq[ci]['outputs'] and name.startswith('u_ot_pr_core.'):
                    end=dict(instance=name,master=master,pin=pin,unary_hops=h)
                else:bad.append('unregistered/noncore output driver '+name+'/'+pin)
                break
            if bad or end is None:errors.append(dict(port=port,bit=bit,errors=bad))
            rows.append(dict(bit=bit,launch=end,errors=bad))
        report[port]=dict(direction='output',width=width,bits=rows)
    out=dict(scope='READ_ONLY_VIRTUAL_CORE_CUT_NOT_NEW_KIT_QUALIFICATION',
             status='PASS' if not errors else 'FAIL',netlist_sha256=receipt['netlist']['sha256'],
             input_bits=sum(INPUTS.values()),output_bits=sum(OUTPUTS.values()),liberty=libs,
             ports=report,errors=errors,
             still_required=['new exact mapped core census and complete physical top boundary audit',
                             'explicit source-registered kit approval','all pin flops anchored at full faces',
                             'TT/FF native capture/launch and clock spread','complete cold/LK schedule proof'])
    Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ('scope','status','input_bits','output_bits','errors')}))


if __name__=='__main__':main()
