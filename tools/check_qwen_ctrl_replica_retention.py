"""Audit retained hierarchy and state roots; physical mapped evidence is separate."""
import argparse,json,re,hashlib
from pathlib import Path

def audit(path,stage='generic'):
    d=json.loads(Path(path).read_text());mods=d['modules'];top=mods['ot_qwen_ctrl_protected_pc00']
    roots=[f'u.g_replica[{i}].u' for i in range(2)];errs=[];records=[]
    outputs=[]
    for root in roots:
        c=top['cells'].get(root)
        if not c or c['type'] not in mods:errs.append('missing independent replica '+root);continue
        m=mods[c['type']];qdrivers={}
        for name,cell in m['cells'].items():
            if 'DFF' in cell['type'].upper():
                for port,bits in cell['connections'].items():
                    if port in ('Q','QN'):
                        for bit in bits:qdrivers[bit]=name
        names=['head','core.on.write_ready_bank']+[f'core.on.wq_oh[{i}]' for i in range(4)]
        bits=[]
        for name in names:
            n=m.get('netnames',{}).get(name,{})
            if len(n.get('bits',[]))!=32:errs.append(root+' missing32bits '+name)
            bits.extend(n.get('bits',[]))
        ffroots=[qdrivers.get(bit) for bit in bits]
        if None in ffroots or len(set(ffroots))!=192:errs.append(root+' added192state bits not independent direct FF roots')
        outbits={b for name,port in m['ports'].items() if port['direction']=='output' for b in c['connections'][name] if isinstance(b,int)}
        outputs.append(outbits)
        records.append(dict(root=root,ff_cells=len(set(qdrivers.values())),critical_added_ff_roots=len(set(ffroots))))
    if len(outputs)==2 and outputs[0]&outputs[1]:errs.append('replica output nets alias')
    guard=[]
    for name in ('u.trip_seen','u.permit_state'):
        bits=top.get('netnames',{}).get(name,{}).get('bits',[])
        for cellname,c in top['cells'].items():
            if 'DFF' in c['type'].upper() and any(b in c['connections'].get('Q',[])+c['connections'].get('QN',[]) for b in bits):guard.append(cellname)
    if len(guard)!=2 or len(set(guard))!=2:errs.append('sticky halt rails merged or absent')
    return dict(pass_retention=not errs,stage=stage,source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),replicas=records,sticky_ff_roots=guard,errors=errs,physical_qualification=False,note='Generic synthesis receipt does not establish final mapped or placed independence; mapped output must pass equivalent root audit before adoption.')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('--stage',default='generic');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();r=audit(a.input,a.stage);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(not r['pass_retention'])
