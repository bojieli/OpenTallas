"""Independent native pre/post connectivity partition check. Never uses net names as roles."""
import hashlib,json,sys,math
from pathlib import Path
from dft.liberty import read_liberty,parse_function,expr_vars

def require(ok,msg):
    if not ok: raise ValueError(msg)

def check(before,after,bpos,apos,native,caps):
    def module(raw):
        require(raw.get('no_exclusions') is True,'raw exclusions')
        require(len(raw['modules'])==1,'module inventory')
        return next(iter(raw['modules'].values()))
    bm,am=module(before),module(after); bc,ac=bm['cells'],am['cells']
    require(bpos['units']==apos['units'],'geometry units')
    require(bpos['bterms']==apos['bterms'],'BTerm geometry')
    require(bpos['die']==apos['die'] and bpos['rows']==apos['rows'],'die/row geometry')
    require(set(bc)<=set(ac),'removed original cell')
    require(bm['ports'].keys()==am['ports'].keys(),'BTerm inventory')
    # Build every signal endpoint, verifying actual native MTerm roles first.
    def graph(raw,mod):
        nets={}; ep={}
        def add(e,bits):
            require(len(bits)<=1,'unexpected bus raw endpoint')
            ep[e]=tuple(bits)
            if bits:nets.setdefault(bits[0],set()).add(e)
        for name,c in mod['cells'].items():
            pins=raw['native_master_pins'][c['type']]
            require(set(pins)==set(c['connections'])==set(c['port_directions'])==set(c['pin_signal_types']),'pin inventory '+name)
            for p,r in pins.items():
                require(r['direction']==c['port_directions'][p] and r['signal_type']==c['pin_signal_types'][p],'pin role '+name+'/'+p)
                if r['signal_type'] not in ('POWER','GROUND'): add(('I',name,p),c['connections'][p])
        for p,r in mod['ports'].items():
            if r['signal_type'] not in ('POWER','GROUND'): add(('B',p),r['bits'])
        return nets,ep
    bn,be=graph(before,bm); an,ae=graph(after,am)
    clock=set(); sinks=set()
    for name,c in bc.items():
        require(c['type']==ac[name]['type'],'master '+name)
        require(bpos['insts'][name]==apos['insts'][name],'placement/orient '+name)
        require(c['port_directions']==ac[name]['port_directions'] and c['pin_signal_types']==ac[name]['pin_signal_types'],'changed pin roles '+name)
        lib=native.get(c['type'])
        # PG-only physical masters carry no ordinary pins and need no Liberty.
        if all(r in ('POWER','GROUND') for r in c['pin_signal_types'].values()):continue
        require(lib is not None,'unknown native master '+c['type'])
        if lib['ff']:
            roles=expr_vars(parse_function(lib['ff']['clocked_on']))
            require(len(roles)==1,'unsupported source clock expression')
            for p in roles:
                require(lib['pins'][p]['clock'],'native clock role disagreement')
                sinks.add(('I',name,p))
    require(('B','clk') in be,'source clk BTerm missing')
    root=be[('B','clk')];require(len(root)==1,'clock disconnected')
    clock=bn[root[0]]
    require(clock==sinks|{('B','clk')},'source clock mixed with data or missing clock sink')
    # The exact reviewed source has direct root-to-FF clock connections.
    for p in bm['ports']:
        require({k:v for k,v in bm['ports'][p].items() if k!='bits'}=={k:v for k,v in am['ports'][p].items() if k!='bits'},'BTerm role '+p)
    # All nonclock connectivity equivalence classes remain exact, including ties/reset/IO.
    for e,bits in be.items():
        if e in clock:continue
        require(e in ae and bool(bits)==bool(ae[e]),'connection/open '+str(e))
        if bits:
            require(bn[bits[0]]==an[ae[e][0]],'signal partition '+str(e))
            require(bm['net_metadata'][str(bits[0])]==am['net_metadata'][str(ae[e][0])],'ordinary net metadata '+str(e))
    added=set(ac)-set(bc); edges={}; neweps=set(); open_outputs=set(); rows=[]
    for name in sorted(added):
        c=ac[name];lib=native.get(c['type']);require(lib and not lib['ff'] and not lib['latch'],'new sequential/unknown cell '+name)
        pins={p:r for p,r in lib['pins'].items() if r['direction'] in ('input','output')}
        ins=[p for p,r in pins.items() if r['direction']=='input'];outs=[p for p,r in pins.items() if r['direction']=='output']
        require(len(ins)==len(outs)==1,'new unary pin shape '+name)
        i=('I',name,ins[0]);o=('I',name,outs[0])
        require(set(e for e in ae if len(e)>2 and e[1]==name)=={i,o},'new cell extra signal pin '+name)
        require(ae[i],'new input disconnected '+name)
        f=parse_function(pins[outs[0]]['function']); positive=f==parse_function(ins[0]);negative=f==parse_function('!'+ins[0])
        require(positive or negative,'new nonidentity function '+name)
        cp=caps[c['type']]['pins'][ins[0]]['native_capacitance'];cap=float(cp['capacitance'])
        require(caps[c['type']]['pins'][ins[0]]['capacitance_unit']==['1','ff'],'wrong native capacitance unit '+name)
        require(math.isfinite(cap) and cap>0,'missing/invalid native clock input capacitance '+name)
        area=float(lib['area']);require(math.isfinite(area) and area>0,'missing native area '+name)
        if ae[o]:
            require(positive,'connected inverter output '+name)
            edges.setdefault(ae[i][0],[]).append(ae[o][0]);kind='TREE'
        else:
            kind='LOAD';open_outputs.add(o)
        neweps|={i,o}
        rows.append(dict(instance=name,master=c['type'],kind=kind,polarity='positive' if positive else 'inverting',input_pin=ins[0],output_pin=outs[0],input_net=ae[i][0],output_net=list(ae[o]),native_TT_input_cap_fF=cap,native_area_um2=area))
    seen=set();todo=list(ae[('B','clk')]);allowed=clock|neweps
    while todo:
        n=todo.pop();require(n not in seen,'clock reconvergence/cycle');seen.add(n)
        require(an[n]<=allowed,'clock/data mixed net')
        todo.extend(edges.get(n,[]))
    require(all(ae[e] and ae[e][0] in seen for e in allowed-open_outputs),'clock graph disconnected or data-net load')
    # Every connected tree branch must terminate in at least one actual original FF clock.
    live={ae[e][0] for e in sinks};changed=True
    while changed:
        changed=False
        for n,ds in edges.items():
            if any(d in live for d in ds) and n not in live:live.add(n);changed=True
    require(all(r['output_net'][0] in live for r in rows if r['kind']=='TREE'),'tree branch has no FF sink')
    from collections import Counter
    def unused(mod,nets):
        return Counter(json.dumps(v,sort_keys=True) for k,v in mod['net_metadata'].items() if int(k) not in nets and v['signal_type'] not in ('POWER','GROUND'))
    require(unused(bm,bn)==unused(am,an),'unexpected unused ordinary nets')
    require(len(added)>0,'no CTS insertion')
    return {'schema':'int8.checkpoint.identity.successor.v1','checkpoint_identity_PASS':True,'qualification':'checkpoint/unqualified; no route, boundary or release qualification','original_cells':len(bc),'new_cells':len(added),'tree_cells':sum(r['kind']=='TREE' for r in rows),'load_cells':sum(r['kind']=='LOAD' for r in rows),'original_clock_sinks':len(sinks),'ordinary_endpoints_checked':len(be)-len(clock),'new_native_area_um2':sum(r['native_area_um2'] for r in rows),'new_TT_input_cap_fF':sum(r['native_TT_input_cap_fF'] for r in rows),'rows':rows,'policy':'only positive unary combinational TREE cells; genuine unary identity/inverting LOAD cells with truly open output and priced native input capacitance/area; graph rooted at exact source clk and native FF clock roles, no instance-name classification'}

def main():
    pre,post,libs,out=map(Path,sys.argv[1:]);load=lambda p:json.loads(p.read_text())
    paths=sorted(libs.glob('*_TT_*.lib*'));require(bool(paths),'TT native libraries missing')
    from strict_contract import native_cells
    result=check(load(pre/'raw.json'),load(post/'raw.json'),load(pre/'positions.json'),load(post/'positions.json'),read_liberty(paths),native_cells(paths,used_masters={c['type'] for c in next(iter(load(post/'raw.json')['modules'].values()))['cells'].values()}))
    result['inputs_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [pre/'raw.json',post/'raw.json',pre/'positions.json',post/'positions.json',*paths]}
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()
