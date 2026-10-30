#!/usr/bin/env python3
"""Default-off source-only mapped cut: one kept ordinary BUF8 before full fanout.

Every known mapped INV source load, including local reset and kept BUF2, is moved.
This does not fix long r2r reach or claim a clock, PG, routing or timing receipt.
"""
import argparse,copy,hashlib,json,re
from pathlib import Path
BUF='BUFx8_ASAP7_75t_R'
OUTPUTS={'Y','QN','SN','CON'}


def insert(inventory,mapped):
    original=mapped['modules']['ot_die_start_stages'];m=copy.deepcopy(mapped);p=m['modules']['ot_die_start_stages'];cells=p['cells']
    integers=[b for c in cells.values()for bs in c.get('connections',{}).values()for b in bs if isinstance(b,int)]
    nxt=max(integers)+1;heads=[];bits=set()
    for s in inventory['source_records']:
        if s.get('source')=='GLOBAL_RAW_INPUT':continue
        inv=s['instance'];bit=s['output_bit']
        if bit in bits:raise ValueError('shared/ambiguous source INV output')
        bits.add(bit)
        if cells[inv]['connections']['Y']!=[bit]or cells[inv]['type']!=s['master']:raise ValueError('source cohort mismatch')
        name='sd_shared_'+hashlib.sha256((s['region']+'\0'+s['signal']).encode()).hexdigest()[:20]
        new=nxt;nxt+=1;changed=[]
        for n,c in list(cells.items()):
            if c['type']=='$scopeinfo':continue
            for pin,bs in c['connections'].items():
                if pin in OUTPUTS:continue
                if bit in bs:
                    if pin in ('CLK','CK','CKN'):raise ValueError('DATA source drives clock')
                    changed.append((n,pin));c['connections'][pin]=[new if b==bit else b for b in bs]
        oldexpected={(t['instance'],t['pin'])for t in s['all_output_sinks']if t['kind']=='iterm'}
        if set(changed)!=oldexpected:raise ValueError(('incomplete source sink ledger',inv,set(changed)^oldexpected))
        for port,v in p['ports'].items():
            if v['direction']=='output':v['bits']=[new if b==bit else b for b in v['bits']]
        for v in p['netnames'].values():v['bits']=[new if b==bit else b for b in v['bits']]
        p['netnames'][name+'_in']=dict(hide_name=0,bits=[bit],attributes={'keep':'1'})
        p['netnames'][name+'_q']=dict(hide_name=0,bits=[new],attributes={'keep':'1'})
        cells[name]=dict(hide_name=0,type=BUF,parameters={},attributes={'keep':'1','dont_touch':'1'},port_directions={'A':'input','Y':'output'},connections={'A':[bit],'Y':[new]})
        heads.append(dict(region=s['region'],signal=s['signal'],source_inv=inv,source_master=s['master'],instance=name,master=BUF,input_bit=bit,output_bit=new,
                          downstream_loads=copy.deepcopy(s['all_output_sinks']),xy_um=None,physical_qualified=False))
    count=check_bridge(original,p,heads)
    return m,dict(schema='ot_start_source_shared_buffer/1',heads=heads,added_flops=0,added_cycles=0,existing_flops=count,
                  complete_state_pin_boolean_bridge='PASS after exact noninverting BUF8 collapse',physical_qualified=False,
                  holds=['explicit legal head homes/pin-to-pin wiring and complete postbuffer cap ledger',
                         'registered global START reach recomposition: existing r2r over405 remain',
                         'actual global prefix/native common clock source/PMA/functionalSTDoccupancy',
                         'routed PG/access, cold/warm timing, related-pair TT/FF and full source qualification'])



def check_bridge(original,p,heads):
    # Exact state and functional-pin bridge: collapse only the actual noninverting
    # BUF8 cells we just inserted, then compare every original cell+port connection.
    collapse={h['output_bit']:h['input_bit']for h in heads}
    reduced=copy.deepcopy(p)
    for h in heads:
        c=reduced['cells'].pop(h['instance'])
        if c['type']!=BUF or c['connections']!={'A':[h['input_bit']],'Y':[h['output_bit']]}:raise ValueError('buffer Boolean identity mismatch')
    for c in reduced['cells'].values():
        for pin,bs in c.get('connections',{}).items():c['connections'][pin]=[collapse.get(b,b)for b in bs]
    for v in reduced['ports'].values():v['bits']=[collapse.get(b,b)for b in v['bits']]
    if reduced['cells']!=original['cells']or reduced['ports']!=original['ports']:raise ValueError('complete native state/pin bridge differs')
    ff=lambda x:{n:c for n,c in x['cells'].items()if c['type'].startswith('DFF')}
    for n,c in ff(original).items():
        q=ff(p)[n]
        if c['type']!=q['type']or c['connections']['CLK']!=q['connections']['CLK']or c['connections']['QN']!=q['connections']['QN']:raise ValueError('FF/master/clock source changed')
    return len(ff(p))

def identifier(n):
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',n):return n
    if any(c.isspace()for c in n):raise ValueError('unsupported identifier whitespace')
    return '\\'+n+' '


def verilog(mapped):
    p=mapped['modules']['ot_die_start_stages'];ports=p['ports'];out=['// SOURCE-ONLY mapped literal shared DATA buffers: no physical admission.',
        'module ot_die_start_stages_buffered ('+', '.join(identifier(n)for n in ports)+');']
    bits=sorted({b for c in p['cells'].values()for bs in c.get('connections',{}).values()for b in bs if isinstance(b,int)}|{b for v in ports.values()for b in v['bits']if isinstance(b,int)})
    net=lambda b:'n_'+str(b)if isinstance(b,int)else "1'b"+b
    for n,v in ports.items():
        if len(v['bits'])!=1:raise ValueError('expected actual scalar START assembly interface')
        out.append(v['direction']+' wire '+identifier(n)+';')
    out += ['wire '+', '.join(net(b)for b in bits)+';']
    for n,v in ports.items():out.append('assign '+(net(v['bits'][0])+' = '+identifier(n)if v['direction']=='input'else identifier(n)+' = '+net(v['bits'][0]))+';')
    for n,c in p['cells'].items():
        if c['type']=='$scopeinfo':continue
        if c.get('parameters'):raise ValueError('nonliteral mapped cell parameters')
        attrs='(* keep="true", dont_touch="true" *) 'if n.startswith('sd_shared_')else''
        args=[]
        for pin,bs in c['connections'].items():
            if len(bs)!=1:raise ValueError('expected actual scalar tech pin')
            args.append('.'+identifier(pin)+'('+net(bs[0])+')')
        out.append(attrs+identifier(c['type'])+' '+identifier(n)+' ('+', '.join(args)+');')
    return '\n'.join(out+['endmodule'])+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',required=True);p.add_argument('--mapped',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();load=lambda f:json.loads(Path(f).read_text());m,d=insert(load(a.inventory),load(a.mapped));o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
    (o/'buffered.json').write_text(json.dumps(m,indent=2)+'\n');(o/'buffered.sv').write_text(verilog(m));(o/'buffer_heads.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({k:d[k]for k in ('existing_flops','added_flops','added_cycles','complete_state_pin_boolean_bridge','physical_qualified')}))

if __name__=='__main__':main()
