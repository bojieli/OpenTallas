"""Private finite ROOT-approved 2026-10-20 exact7 comparison; no admission."""
from pathlib import Path
import copy, hashlib, json
import compare_ab_graphs as g
E=Path(__file__).with_name('ab_complete_graph')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def labels(a,b,top,rows):
    a,b=copy.deepcopy(a),copy.deepcopy(b)
    for r in rows:
        if r['top']!=top:continue
        ac=a['modules'][r['module']]['cells'][r['cell']]
        bc=b['modules'][r['module']]['cells'][r['cell']]
        # Entire original cells pinned, including exact metadata values and no-pin shape.
        if ac!=r['left'] or bc!=r['right']:raise ValueError('exact scopeinfo cell mismatch')
        for c in (ac,bc):
            if c['type']!='$scopeinfo' or c['parameters']!={'TYPE':'module'} or c['connections'] or c['port_directions']:raise ValueError('unsupported scopeinfo shape')
        del ac['attributes']['module'];del bc['attributes']['module']
    return a,b

def main():
    packet=json.loads((E/'exact7_metadata_packet.json').read_text());result=[]
    for top in ['qkd_static_ectla_kiss','qkd_ectl_b_tp8_direct']:
        paths=[E/f'{top}_{h}.json' for h in (13,15)]
        src=[p.read_bytes() for p in paths];sha=[hashlib.sha256(x).hexdigest() for x in src]
        expected=next(r['source_json_sha256'] for r in packet['rows'] if r['top']==top)
        if sha!=expected:raise ValueError('four original input identities changed')
        raw=[json.loads(x) for x in src]
        a,b=labels(*raw,top,packet['rows']);ca,cb=g.canonical(a,top,13),g.canonical(b,top,15)
        if ca!=cb:raise ValueError('remaining complete graph differs')
        controls=[]
        def refuses(name,mutator):
            x=copy.deepcopy(b);mutator(x)
            if ca==g.canonical(x,top,15):raise AssertionError('causal falsely accepted: '+name)
            controls.append({'name':name,'status':'REFUSED_COMPLETE_GRAPH_DIFF'})
        m=b['modules'][top];cells=m['cells']
        func=next(n for n,c in cells.items() if c['connections'] and c['type']!='$scopeinfo')
        state=next(n for n,c in cells.items() if 'dff' in c['type'].lower())
        mem=next(n for n,c in cells.items() if 'sram' in c['type'].lower())
        port=next(iter(m['ports']));net=next(iter(m['netnames']))
        refuses('real functional TYPE',lambda x:x['modules'][top]['cells'][func].update(type='$wrong_type'))
        refuses('port direction',lambda x:x['modules'][top]['ports'][port].update(direction='inout'))
        refuses('port width',lambda x:x['modules'][top]['ports'][port]['bits'].append('0'))
        refuses('port offset',lambda x:x['modules'][top]['ports'][port].update(offset=123))
        for sp in [p for p in cells[state]['connections'] if p in ('CLK','C','ARST','SRST','R')]:
            refuses('sequential '+sp+' connectivity',lambda x,sp=sp:x['modules'][top]['cells'][state]['connections'].update({sp:['1']}))
        refuses('state parameter',lambda x:x['modules'][top]['cells'][state]['parameters'].update(CAUSAL_CHANGED='1'))
        refuses('SRAM master',lambda x:x['modules'][top]['cells'][mem].update(type='wrong_sram'))
        refuses('SRAM parameter',lambda x:x['modules'][top]['cells'][mem]['parameters'].update(CAUSAL_CHANGED='1'))
        mp=next(iter(cells[mem]['connections']))
        refuses('SRAM full pin graph',lambda x:x['modules'][top]['cells'][mem]['connections'].update({mp:['0']}))
        refuses('extra cell',lambda x:x['modules'][top]['cells'].update(extra=copy.deepcopy(cells[func])))
        refuses('extra alias',lambda x:x['modules'][top]['netnames'].update(extra_alias=copy.deepcopy(m['netnames'][net])))
        refuses('net literal/occurrence',lambda x:x['modules'][top]['netnames'][net]['bits'].append('1'))
        def rename(x):x['modules'][top]['cells']['renamed']=x['modules'][top]['cells'].pop(func)
        refuses('hierarchy/name',rename)
        first=next(r for r in packet['rows'] if r['top']==top)
        third=copy.deepcopy(raw[1]);third['modules'][top]['cells'][first['cell']]['attributes']['module']='UNREVIEWED_THIRD_LABEL'
        try:labels(raw[0],third,top,packet['rows'])
        except ValueError:controls.append({'name':'third scopeinfo string','status':'REFUSED_EXACT_CELL_IDENTITY'})
        else:raise AssertionError('third string admitted')
        result.append({'top':top,'status':'EXACT7_COMPLETE_GRAPH_IDENTICAL','input_sha256':sha,'canonical_sha256':[digest(ca),digest(cb)],'causals':controls,'actual_state_cell':state,'actual_sram_cell':mem})
    out={'scope':'SOURCE_GRAPH_IDENTITY_ONLY_NO_AB_COLD_NATIVE_PHYSICAL_OR_RECEIPT_ADMISSION','root_review':'2026-10-20 exact7 approval, raw strict FAIL preserved','required_separate_lemma':'Exact same authoritative stateful SRAM proof still required','results':result}
    (E/'exact7_private.comparison.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))
if __name__=='__main__':main()
