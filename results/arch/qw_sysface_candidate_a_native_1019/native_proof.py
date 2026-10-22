#!/usr/bin/env python3
"""Construct native next-state equations from exact Liberty and native JSON.

Only the measured native FF truth-table form is accepted. Unknown semantics
refuse; no generic behavioral cell substitutions are supplied.
"""
import json, pathlib, re
P=pathlib.Path(__file__).resolve().parent
def groups(text, kind):
    for m in re.finditer(r'\b'+kind+r'\s*\(([^)]*)\)\s*\{',text):
        depth=1;i=m.end()
        while depth:
            depth+=(text[i]=='{')-(text[i]=='}');i+=1
        yield m.group(1).strip().strip('"'),text[m.end():i-1]
def attr(s,k):
    m=re.search(r'\b'+k+r'\s*:\s*([^;]+);',s)
    return m.group(1).strip().strip('"') if m else None
libs={}
for name,body in groups((P/'libs/all.lib').read_text(),'cell'):
    funcs={pn:attr(pb,'function') for pn,pb in groups(body,'pin') if attr(pb,'direction')=='output'}
    ff=list(groups(body,'ff'))
    libs[name]={'functions':funcs,'pins':{n:{k:attr(b,k) for k in ['direction','capacitance','rise_capacitance','fall_capacitance','max_capacitance']} for n,b in groups(body,'pin')}, 'ff':[{k:attr(b,k) for k in ['clear','preset','next_state','clocked_on','clear_preset_var1','clear_preset_var2']} for _,b in ff], 'pg':{n:attr(b,'pg_type') for n,b in groups(body,'pg_pin')}}
source=(P/'proof.sv').read_text()
header=re.search(r'module old_next\((.*?)\);',source,re.S).group(1)
states=[('accepted_v',1),('host_epoch_valid',1),('host_tag',59),('host_gen',2),('host_fusedcap',1),('host_image_epoch',16),('host_image_digest',64),('fault',1)]
def wire(b):return f'n{b}' if isinstance(b,int) else "1'b"+b
receipt={}
for which,oldnew in [('original','old'),('candidate','new')]:
    j=json.loads((P/f'mapped_{which}/netlist.json').read_text());m=next(v for k,v in j['modules'].items() if k.startswith('qfd_host'))
    cells=m['cells'];ffs={k:c for k,c in cells.items() if libs[c['type']]['ff']}
    assert len(ffs)==145,('state_count',which,len(ffs))
    expected={'clear':'!SETN','preset':'!RESETN','next_state':'!D','clocked_on':'CLK','clear_preset_var1':'L','clear_preset_var2':'L'}
    for c in ffs.values():
        lib=libs[c['type']]
        assert lib['ff']==[expected] and lib['functions']=={'QN':'IQN'},('unsupported_ff',c['type'],lib)
        assert c['connections']['SETN']==['1'],('nonconstant_set',c)
        assert c['connections']['RESETN']==m['ports']['rst_n']['bits'],('reset_mismatch',c)
        assert c['connections']['CLK']==m['ports']['ck']['bits'],('clock_mismatch',c)
    # Trace actual native output inversion/buffering to its unique state cell.
    drivers={}
    for k,c in cells.items():
        for pn,d in c['port_directions'].items():
            if d=='output':
                for b in c['connections'][pn]:
                    assert b not in drivers,('multiple_driver',b)
                    drivers[b]=(k,pn)
    def state_origin(bit,seen=()):
        assert bit not in seen,('cycle',bit)
        k,pn=drivers[bit];c=cells[k]
        if k in ffs:return k,0
        f=libs[c['type']]['functions'][pn]
        z=re.fullmatch(r'\s*(!?)\s*([A-Za-z0-9_]+)\s*',f)
        assert z,('nontransparent_state_output',bit,k,f)
        n,inv=state_origin(c['connections'][z[2]][0],seen+(bit,))
        return n,inv^bool(z[1])
    correspondence={};index=144
    for name,width in states:
        bits=m['ports'][name]['bits']
        for i in reversed(range(width)):
            ff,invert=state_origin(bits[i]);assert ff not in correspondence,('state_merged',ff)
            correspondence[ff]={'state_index':index,'name':name,'bit':i,'output_inverted_from_qn':invert};index-=1
    assert index==-1 and set(correspondence)==set(ffs)
    lines=[f'module {which}_native_next({header});']
    allbits={b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b,int)}
    lines+=['wire '+','.join(wire(b) for b in sorted(allbits))+';']
    for name,p in m['ports'].items():
        if p['direction']!='input':continue
        for i,b in enumerate(p['bits']):
            rhs='1\'b0' if name=='ck' else name+(f'[{i}]' if len(p['bits'])>1 else '')
            lines.append(f'assign {wire(b)} = {rhs};')
    for k,c in cells.items():
        if k in ffs:
            corr=correspondence[k];i=corr['state_index'];qn=wire(c['connections']['QN'][0]);d=wire(c['connections']['D'][0]);inv=corr['output_inverted_from_qn']
            lines.append(f'assign {qn} = '+('~' if inv else '')+f'state[{i}];')
            # Actual IQN next-state !D, preset !RESETN. SETN is proven constant1.
            nq=f'(rst_n ? ~{d} : 1\'b1)'
            lines.append(f'wire next_{i}; assign next_{i} = '+('~' if inv else '')+nq+';')
        else:
            for pn,func in libs[c['type']]['functions'].items():
                assert func is not None,('missing_function',c['type'],pn)
                assert not re.search(r"[^A-Za-z0-9_\s!()*+&|^01]",func),('unsupported_function',func)
                expr=re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b',lambda z:wire(c['connections'][z[0]][0]),func)
                expr=expr.replace('!','~').replace('*','&').replace('+','|')
                lines.append(f'assign {wire(c["connections"][pn][0])} = {expr};')
    # All outputs are state aliases in this exact component, including epoch.
    bit_to_index={m['ports'][v['name']]['bits'][v['bit']]:v['state_index'] for v in correspondence.values()}
    outbits=[]
    for name,_ in states+[('host_epoch',16)]:outbits.extend(reversed(m['ports'][name]['bits']))
    assert len(outbits)==161
    lines.append('assign result={'+','.join('next_'+str(bit_to_index[b]) for b in outbits)+'};\nendmodule')
    proofmod=source[source.index('module proof('):].replace('module proof(','module native_proof(')
    proofmod=re.sub(r'old_next u_a',oldnew+'_next u_a',proofmod).replace('new_next u_b',which+'_native_next u_b')
    (P/f'mapped_{which}/native_proof.sv').write_text(source[:source.index('module proof(')]+'\n'+'\n'.join(lines)+'\n'+proofmod)
    (P/f'mapped_{which}/native_proof.ys').write_text(f'read_verilog -formal mapped_{which}/native_proof.sv\nhierarchy -top native_proof\nproc\nflatten\nopt_clean\nsat -verify -prove ok 1 -show-inputs -show-outputs\n')
    receipt[which]={'state_correspondence':correspondence,'native_cell_count':len(cells),'native_ff_count':len(ffs),'output_comparisons':161,'all_native_types':{t:libs[t] for t in sorted({c['type'] for c in cells.values()})}}
(P/'native_semantics.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('NATIVE_PROOF_GENERATED original=145 candidate=145 outputs=161 each')
