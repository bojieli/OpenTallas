#!/usr/bin/env python3
"""Clone registered VM sector selectors into fanout-bounded, same-cycle copies.

Input is Yosys's one-bit generic-cell JSON for the extracted rest module.
No logic function, port, clock edge, reset or cycle changes. New FFs duplicate
an existing FF's entire cell connections except Q and carry keep attributes.
"""
import argparse, copy, json, pathlib

def transform(data, fanout=8, all_ff=False, local_reset=False):
    data=copy.deepcopy(data)
    mod=data['modules']['ot_hgi_sfu_split3_ctl_rest']
    assert '__p56_ctl' in mod['ports'], 'lower with OT_REST1C_SCALAR_OPIPE_JOINED enabled'
    selected=set()
    for name,net in mod['netnames'].items():
        if '.drain_sector_q[16]' in name:
            assert len(net['bits'])==1, name
            selected.update(net['bits'])
    assert len(selected)==4, sorted(selected)
    if local_reset:
        reset=mod['netnames']['u_core_u_rst_relay_q_0']['bits'];assert len(reset)==1
        selected.update(reset)
    cells=mod['cells']
    original=set(cells)
    qdrivers={c['connections']['Q'][0]:n for n,c in cells.items()if c['type'] in {'$_DFF_P_','$_DFF_PN0_'} and len(c['connections'].get('Q',[]))==1}
    targets={qdrivers[b]for b in selected if b in qdrivers}
    if local_reset:
        pending=list(targets)
        while pending:
            n=pending.pop()
            for port in ('D','R'):
                for bit in cells[n]['connections'].get(port,[]):
                    upstream=qdrivers.get(bit)
                    if upstream is not None and upstream not in targets:targets.add(upstream);pending.append(upstream)
    # Consumers must be expanded before their registered parents.
    deps={n:{qdrivers[bit]for port in ('D','R')for bit in cells[n]['connections'].get(port,[])if bit in qdrivers and qdrivers[bit] in targets}for n in targets}
    order=[];remaining=set(targets)
    while remaining:
        ready=sorted(n for n in remaining if not any(n in deps[k]for k in remaining))
        assert ready,'cyclic FF dependency requires a dedicated proof'
        order.extend(ready);remaining.difference_update(ready)
    maxbit=max((b for n in mod['netnames'].values() for b in n['bits'] if isinstance(b,int)),default=0)
    report=[]
    for name in order:
        cell=cells[name]
        if not cell['type'].startswith('$_DFF'):
            continue
        q=cell['connections'].get('Q',[])
        if len(q)!=1:continue
        consumers=[]
        for cn,cc in cells.items():
            for port,bits in cc['connections'].items():
                if cc['port_directions'].get(port)!='input':continue
                for ix,b in enumerate(bits):
                    if b==q[0]:consumers.append((cn,port,ix))
        if len(consumers)<=fanout:continue
        # Place independent copies by existing sink hierarchy where available.
        aliases={}
        for nn,nv in mod['netnames'].items():
            if not nn.startswith('$'):
                for bb in nv['bits']:aliases.setdefault(bb,nn)
        def sink_key(load):
            cc=cells[load[0]]
            outputs=[aliases.get(bb,'')for pp,bbs in cc['connections'].items()if cc['port_directions'].get(pp)=='output'for bb in bbs]
            return (0 if load[0] in targets else 1,min(outputs,default=''),load)
        consumers.sort(key=sink_key)
        clones=[]
        # Keep the original register's first bounded set of consumers. Clone
        # every later group, preserving the original register for LEC identity.
        cell.setdefault('attributes',{})['keep']='1'
        for group in range(1,(len(consumers)+fanout-1)//fanout):
            maxbit+=1;newname=f'ot_rest_selcopy_{len(report)}_{group}'
            c=copy.deepcopy(cell);c['connections']['Q']=[maxbit]
            cells[newname+'_ff']=c
            mod['netnames'][newname]={'hide_name':0,'bits':[maxbit],'attributes':{'keep':'1'}}
            loads=consumers[group*fanout:(group+1)*fanout]
            for cn,p,ix in loads:cells[cn]['connections'][p][ix]=maxbit
            clones.append({'cell':newname+'_ff','loads':len(loads)})
        report.append({'source':name,'q':q[0],'loads':len(consumers),'copies':clones})
    assert report, 'selected registers had no high-fanout loads'
    return data,report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--report',type=pathlib.Path,required=True);p.add_argument('--fanout',type=int,default=8);p.add_argument('--all-ff',action='store_true');p.add_argument('--local-reset',action='store_true');a=p.parse_args()
    out,report=transform(json.loads(a.input.read_text()),a.fanout,a.all_ff,a.local_reset)
    a.output.write_text(json.dumps(out));a.report.write_text(json.dumps(report,indent=1)+'\n')
    print('SELECTORS',len(report),'ADDED_FF',sum(len(r['copies'])for r in report),'MAX_COPY_FANOUT',max(c['loads']for r in report for c in r['copies']))
