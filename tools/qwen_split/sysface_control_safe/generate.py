#!/usr/bin/env python3
"""Emit a profile-specific, real structural SYSFACE candidate from a flat graph.

This is deliberately a separate master, never a replacement for the parameterized
functional source. The input graph and full source/profile manifest are mandatory.
No scheduling parameter is inferred. Clock fanout belongs to CTS, not this pass.
"""
import argparse, collections, copy, hashlib, json
from pathlib import Path

LIMIT = 12  # Native DFFE enable mapping can consume two input pins per abstract load.
BUF = 'BUFx2_ASAP7_75t_R'
FF = {'$_DFF_P_', '$_DFF_PN0_', '$_DFF_PN1_', '$_DFFE_PP_',
      '$_DFFE_PN0P_', '$_DFFE_PN0N_', '$_SDFF_PP0_', '$_SDFF_PN0_'}
GATES = {'$_AND_', '$_OR_', '$_XOR_', '$_NOT_', '$_MUX_'}
MACROS = {'ot_rom_4096x72_m8', 'ot_sram_1r1w_64x16_m1'}
PROFILES = {
    'cold': dict(MU=1, SRAM_CAL=1, OVL=1, CTX_ACCEPTED=1,
                 COLD_PREFIX=1, COLD_START_OFS=2000, OVL_FIRST_OFS=20000, OVL_AW=12),
    'legacy': dict(MU=1, SRAM_CAL=1, OVL=0, CTX_ACCEPTED=0,
                   COLD_PREFIX=0, COLD_START_OFS=0, OVL_FIRST_OFS=1176, OVL_AW=11),
}
# QW-SYSFACE3 10-19: SAFE3 source (balanced fault/enable cones, zero added edges) on the same two profiles.
PROFILES['cold3']=dict(PROFILES['cold'],SAFE3=1)
PROFILES['legacy3']=dict(PROFILES['legacy'],SAFE3=1)
# QW-SYSFACE3: emit kept copies as instances of ONE module per primitive KIND (no per-instance ID parameter).
# bc2/bc2c/bc2l: 16.5k unique ID paramods made every Yosys opt pass ~10 min (bc2/bc2c synth 2700 s timeouts, bc2l
# 1 h 55 min synth). User-module instances are never merged by opt_merge (no -share_all), keep_hierarchy keeps
# them unflattened, and check_emitted.py still proves every instance pin-for-pin, so copies survive with 13 types.
PER_KIND = True

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def loads(m):
    out = collections.defaultdict(list)
    for name, c in m['cells'].items():
        for p, bb in c['connections'].items():
            if c['port_directions'][p] == 'input':
                for k, b in enumerate(bb):
                    if isinstance(b, int): out[b].append((name, p, k))
    return out

def generate(src, manifest, useful_cones=False, physical_wrapper=False):
    orig = src['modules']['qfd_sys_face']
    assert not any(c['type'] not in FF | GATES | MACROS | {'$scopeinfo'}
                   for c in orig['cells'].values()), 'flatten all nonmacro modules first'
    assert manifest['parameters'] == PROFILES.get(manifest['profile']), 'unsupported profile'
    assert manifest['production_origin_bound'] is False, 'origin adoption requires a new review'
    m = copy.deepcopy(orig)
    m['cells'] = {n:c for n,c in m['cells'].items() if c['type'] != '$scopeinfo'}
    maxbit = max(b for v in m['netnames'].values() for b in v['bits'] if isinstance(b, int))
    def alloc():
        nonlocal maxbit
        maxbit += 1
        return maxbit
    def rewire(ref, bit):
        n,p,k=ref; m['cells'][n]['connections'][p][k]=bit
    origins = {n:n for n in m['cells']}
    bit_origin = {}
    before = loads(m)
    copies = []
    rr = orig['netnames']['rr_s']['bits'] + [orig['netnames']['rr_q']['bits'][0]]
    # Copy the actual registered producer, with identical D/C/E/R and priority.
    # Each copy is emitted through a distinct kept paramod, not an identical
    # vector that opt_merge may collapse into a single high-fanout FF.
    for name, c in list(m['cells'].items()):
        if c['type'] not in FF: continue
        q = c['connections']['Q'][0]
        if q in rr: continue
        refs = before[q]
        for k, start in enumerate(range(LIMIT, len(refs), LIMIT), 1):
            nn = name + '__copy_' + str(k)
            nc = copy.deepcopy(c); qb = alloc(); nc['connections']['Q'] = [qb]
            m['cells'][nn] = nc; origins[nn] = name; bit_origin[qb] = q
            for ref in refs[start:start+LIMIT]: rewire(ref, qb)
            copies.append({'cell':nn, 'original':name, 'q':qb, 'original_q':q})

    # Replace only the inherited three-edge rr chain. Synchronous resets in
    # ordinary state remain synchronous, including reset-versus-enable priority.
    assert len(set(rr)) == 3
    clk = orig['ports']['ck']['bits'][0]; rst = orig['ports']['rst_n']['bits'][0]
    rr_cells = []
    for n,c in list(m['cells'].items()):
        if c['type'] in FF and origins[n] in orig['cells'] and orig['cells'][origins[n]]['connections']['Q'][0] in rr:
            rr_cells.append(n)
            del m['cells'][n]; del origins[n]
    assert len(rr_cells) == 3, 'unexpected rr source structure'
    refs = loads(m)[rr[2]]
    assert not loads(m).get(rr[0]) and not loads(m).get(rr[1]), 'rr internal escaped chain'
    nleaf = (len(refs)+LIMIT-1)//LIMIT
    nmid = (nleaf+LIMIT-1)//LIMIT
    nfirst = (nmid+LIMIT-1)//LIMIT
    assert nfirst <= LIMIT, 'reset forest needs a fourth level; unsupported'
    forest = []
    def reset_ff(name, reset, depth):
        q=alloc(); m['cells'][name]={'type':'$_DFF_PN0_', 'parameters':{},
          'attributes':{'keep':1}, 'port_directions':{'C':'input','D':'input','R':'input','Q':'output'},
          'connections':{'C':[clk],'D':['1'],'R':[reset],'Q':[q]}}
        origins[name]=None; bit_origin[q]=rr[depth-1]
        forest.append({'cell':name,'depth':depth,'q':q,'reset':reset})
        return q
    first=[reset_ff('safe_rst_first_'+str(i),rst,1) for i in range(nfirst)]
    mid=[reset_ff('safe_rst_mid_'+str(i),first[i//LIMIT],2) for i in range(nmid)]
    leaf=[reset_ff('safe_rst_leaf_'+str(i),mid[i//LIMIT],3) for i in range(nleaf)]
    for i,ref in enumerate(refs): rewire(ref,leaf[i//LIMIT])

    input_capture_copies=[]
    useful_copies=[]
    if useful_cones:
        # Count terminal pins through INV, never credit transparent distribution.
        # Recompute after every split because new producer inputs are real loads.
        for iteration in range(100000):
            ll=loads(m)
            published=collections.defaultdict(list)
            for port,desc in m['ports'].items():
                if desc['direction']=='output':
                    for k,b in enumerate(desc['bits']):published[b].append(('@'+port,'',k))
            def terminals(bit, path=(), seen=frozenset()):
                assert bit not in seen, 'transparent cycle'
                ans=[]
                for ref in ll.get(bit,[]):
                    n,p,k=ref; c=m['cells'][n]
                    if c['type']=='$_NOT_':
                        ans.extend(terminals(c['connections']['Y'][0],path+(n,),seen|{bit}))
                    else:ans.append((ref,path))
                ans.extend((ref,path) for ref in published.get(bit,[]))
                return ans
            roots=[]
            for n,c in m['cells'].items():
                if c['type'] in (FF | (GATES-{'$_NOT_'})):
                    q=c['connections']['Q' if c['type'] in FF else 'Y'][0]
                    tt=sorted(terminals(q),key=lambda x:not x[0][0].startswith("@"))
                    if len(tt)>LIMIT:roots.append((len(tt),n,q,tt))
            if not roots:break
            _,name,q,tt=max(roots,key=lambda x:(x[0],x[1]))
            if iteration%100==0:print('useful split',iteration,name,len(tt),'cells',len(m['cells']),flush=True)
            c=m['cells'][name]
            for start in range(LIMIT,len(tt),LIMIT):
                nn=name+'__useful_'+str(len(useful_copies)); nc=copy.deepcopy(c);qb=alloc()
                nc['connections']['Q' if c['type'] in FF else 'Y']=[qb]
                m['cells'][nn]=nc;origins[nn]=origins[name];bit_origin[qb]=bit_origin.get(q,q)
                useful_copies.append({'cell':nn,'original':origins[name],'q':qb,'original_q':bit_origin.get(q,q)})
                if origins[name] is None:
                    prior=next(f for f in forest if f['cell']==name)
                    forest.append(dict(prior,cell=nn,q=qb))
                for ref,path in tt[start:start+LIMIT]:
                    b=qb
                    for old in path:
                        inv=copy.deepcopy(m['cells'][old]); ni=old+'__path_'+str(alloc()); ob=alloc()
                        inv['connections']['A']=[b];inv['connections']['Y']=[ob]
                        m['cells'][ni]=inv;origins[ni]=origins[old];bit_origin[ob]=bit_origin.get(m['cells'][old]['connections']['Y'][0],m['cells'][old]['connections']['Y'][0]);b=ob
                    if ref[0].startswith('@'):m['ports'][ref[0][1:]]['bits'][ref[2]]=b
                    else:rewire(ref,b)
        else:raise AssertionError('useful producer replication did not converge')
        if physical_wrapper:
            # These are additional copies of the ALREADY PAID face capture,
            # never an extra core pipeline edge. Expanded ports are private.
            for port,desc in list(m['ports'].items()):
                if desc['direction']!='input' or port in ['ck','rst_n']:continue
                for pin_index,b in enumerate(desc['bits']):
                    ll=loads(m);tt=terminals(b)
                    assert (len(tt)+LIMIT-1)//LIMIT<=32, 'raw pin would exceed32 capture D loads'
                    for start in range(LIMIT,len(tt),LIMIT):
                        nb=alloc();pn='__safe_capture_'+str(len(input_capture_copies))
                        m['ports'][pn]={'direction':'input','bits':[nb]};bit_origin[nb]=b
                        input_capture_copies.append({'port':pn,'bit':nb,'original_bit':b,'original_port':port,'original_index':pin_index})
                        for ref,path in tt[start:start+LIMIT]:
                            out=nb
                            for old in path:
                                inv=copy.deepcopy(m['cells'][old]);ni=old+'__pinpath_'+str(alloc());ob=alloc()
                                inv['connections']['A']=[out];inv['connections']['Y']=[ob]
                                m['cells'][ni]=inv;origins[ni]=origins[old];bit_origin[ob]=bit_origin.get(m['cells'][old]['connections']['Y'][0],m['cells'][old]['connections']['Y'][0]);out=ob
                            if ref[0].startswith('@'):m['ports'][ref[0][1:]]['bits'][ref[2]]=out
                            else:rewire(ref,out)
            ll=loads(m)
        boundary={b:len(terminals(b)) for p in m['ports'].values() if p['direction']=='input' for b in p['bits'] if b!=clk}
        for c in m['cells'].values():
            if c['type'] in MACROS:
                for p,bs in c['connections'].items():
                    if c['port_directions'][p]=='output':
                        for b in bs:boundary[b]=len(terminals(b))
        assert max(boundary.values(),default=0)<=32, 'uncopyable top/memory boundary exceeds32: '+str(sorted(boundary.items(),key=lambda x:-x[1])[:10])

    # Native-cell trees retain all cycles. No abstract buffers or ignored cells.
    # Output capacitance and slew are still physical signoff obligations.
    buffers=[]
    def buffer(src, suffix):
        q=alloc(); n='safe_buf_'+str(len(buffers))+'_'+suffix
        m['cells'][n]={'type':BUF,'parameters':{},'attributes':{'keep':1},
          'port_directions':{'A':'input','Y':'output'},'connections':{'A':[src],'Y':[q]}}
        origins[n]=None; bit_origin[q]=bit_origin.get(src,src)
        buffers.append({'cell':n,'input':src,'output':q})
        return n,q
    for bit,refs in list(loads(m).items()):
        if useful_cones or bit == clk or len(refs)<=LIMIT: continue
        level=[]
        for i,start in enumerate(range(0,len(refs),LIMIT)):
            name,q=buffer(bit,'leaf')
            for ref in refs[start:start+LIMIT]: rewire(ref,q)
            level.append((name,'A',0))
        while len(level)>LIMIT:
            higher=[]
            for start in range(0,len(level),LIMIT):
                name,q=buffer(bit,'branch')
                for ref in level[start:start+LIMIT]: rewire(ref,q)
                higher.append((name,'A',0))
            level=higher
    if not useful_cones:assert max((len(v) for b,v in loads(m).items() if b!=clk),default=0)<=LIMIT
    return m, {'limit':LIMIT,'clock':clk,'reset_chain_original':rr,'removed_reset_cells':rr_cells,
       'physical_wrapper':physical_wrapper,'public_ports':orig['ports'],'input_capture_copies':input_capture_copies,'useful_cones':useful_cones,'useful_copies':useful_copies,'copies':copies,'forest':forest,'buffers':buffers,'origins':origins,
       'bit_origin':bit_origin,'source_graph_sha256':None,'manifest':manifest,
       'macro_bindings':{n:{'emitted_instance':'m'+str(i),'master':c['type']}
                         for i,(n,c) in enumerate(sorted(m['cells'].items())) if c['type'] in MACROS},
       'counts':{'original_cells':len(orig['cells']),'candidate_cells':len(m['cells']),
       'extra_paid_input_captures':len(input_capture_copies),'useful_producer_copies':len(useful_copies),'copied_ff':len(copies),'reset_ff':len(forest),'native_buffers':len(buffers),
       'max_nonclock_load':max(len(v) for b,v in loads(m).items() if b!=clk)}}

def emit(m, top, original, manifest, receipt):
    def bit(x): return ('n'+str(x)) if isinstance(x,int) else "1'b"+x
    def vec(xs): return '{'+','.join(bit(x) for x in reversed(xs))+'}' if len(xs)>1 else bit(xs[0])
    out=['// Generated by tools/qwen_split/sysface_control_safe/generate.py; do not edit.',
         ('(* keep_hierarchy=1 *) ' if receipt.get('physical_wrapper') else '')+'module '+top+' #(parameter ROM_VIAMAP="", ROM_INSTANCE="sys_face_cfg", OVL_ROM_DIR="") (']
    ports=[]
    for n,p in m['ports'].items():
        ports.append('  '+p['direction']+' wire '+('['+str(len(p['bits'])-1)+':0] ' if len(p['bits'])>1 else '')+n)
    out += [',\n'.join(ports),');']
    bits=set(b for c in m['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int))
    bits.update(b for p in m['ports'].values() for b in p['bits'] if isinstance(b,int))
    out += ['wire '+','.join('n'+str(b) for b in sorted(bits))+';']
    for n,p in m['ports'].items():
        out.append('assign '+(vec(p['bits'])+' = '+n if p['direction']=='input' else n+' = '+vec(p['bits']))+';')
    ftypes=sorted(FF)
    for i,(name,c) in enumerate(sorted(m['cells'].items())):
        con={p:vec(v) for p,v in c['connections'].items()}; typ=c['type']
        out.append('// '+name.replace('\n',' '))
        if typ in FF:
            args={p:con.get(p,"1'b0") for p in ['C','D','E','R','Q']}
            out.append('(* keep=1 *) sysface_safe_ff #('+('' if PER_KIND else '.ID('+str(i)+'),')+'.KIND('+str(ftypes.index(typ))+')) f'+str(i)+'('+','.join('.'+p+'('+v+')' for p,v in args.items())+');')
        elif typ in GATES:
            a=con['A']; b=con.get('B'); y=con['Y']
            expr={'$_AND_':lambda:a+'&'+b,'$_OR_':lambda:a+'|'+b,'$_XOR_':lambda:a+'^'+b,
                  '$_NOT_':lambda:'~'+a,'$_MUX_':lambda:con['S']+'?'+b+':'+a}[typ]()
            if receipt.get('useful_cones'):
                kind=sorted(GATES).index(typ)
                out.append('(* keep=1 *) sysface_safe_gate #('+('' if PER_KIND else '.ID('+str(i)+'),')+'.KIND('+str(kind)+')) g'+str(i)+'(.A('+a+'),.B('+con.get('B',"1'b0")+'),.S('+con.get('S',"1'b0")+'),.Y('+y+'));')
            else:out.append('assign '+y+' = '+expr+';')
        elif typ==BUF:
            out.append('(* keep=1 *) '+BUF+' b'+str(i)+'(.A('+con['A']+'),.Y('+con['Y']+'));')
        else:
            param=''
            if typ=='ot_rom_4096x72_m8':
                if name=='u_rom': param='#(.VIAMAP(ROM_VIAMAP),.INSTANCE(ROM_INSTANCE)) '
                elif name.endswith('u_tx_rom'):param='#(.VIAMAP({OVL_ROM_DIR,"/ovl_c_tx.viamap.hex"}),.INSTANCE("ovl_c_tx")) '
                elif name.endswith('u_rx_rom'):param='#(.VIAMAP({OVL_ROM_DIR,"/ovl_c_rx.viamap.hex"}),.INSTANCE("ovl_c_rx")) '
                else:raise ValueError('unknown ROM image binding: '+name)
            if param:out += ['`ifdef SYNTHESIS',typ+' m'+str(i)+'('+','.join('.'+p+'('+v+')' for p,v in con.items())+');','`else']
            out.append(typ+' '+param+'m'+str(i)+'('+','.join('.'+p+'('+v+')' for p,v in con.items())+');')
            if param:out.append('`endif')
    out.append('endmodule')
    if receipt.get('useful_cones'):
        out += ['(* keep_hierarchy=1 *) module sysface_safe_gate #(parameter integer ID=0,KIND=0)(input A,B,S,output Y);']
        expressions={'$_AND_':'A&B','$_OR_':'A|B','$_XOR_':'A^B','$_NOT_':'~A','$_MUX_':'S?B:A'}
        for k,typ in enumerate(sorted(GATES)):
            out.append(('if' if k==0 else 'else if')+'(KIND=='+str(k)+') begin:g'+str(k)+' assign Y='+expressions[typ]+'; end')
        out+=['else begin:bad initial $error("unsupported gate"); end','endmodule']
    out += ['(* keep_hierarchy=1 *) module sysface_safe_ff #(parameter integer ID=0,KIND=0)(input wire C,D,E,R,output reg Q);']
    for k,typ in enumerate(ftypes):
        out.append(('if' if k==0 else 'else if')+'(KIND=='+str(k)+') begin:g'+str(k))
        if typ in {'$_DFF_PN0_','$_DFF_PN1_','$_DFFE_PN0P_','$_DFFE_PN0N_'}:
            val='1' if typ=='$_DFF_PN1_' else '0'
            en=(' if(E)' if typ=='$_DFFE_PN0P_' else ' if(!E)' if typ=='$_DFFE_PN0N_' else '')
            out.append('always @(posedge C or negedge R) if(!R) Q<=1\'b'+val+'; else'+en+' Q<=D;')
        elif typ=='$_DFFE_PP_':out.append('always @(posedge C) if(E) Q<=D;')
        elif typ=='$_SDFF_PP0_':out.append('always @(posedge C) if(R) Q<=0; else Q<=D;')
        elif typ=='$_SDFF_PN0_':out.append('always @(posedge C) if(!R) Q<=0; else Q<=D;')
        else:out.append('always @(posedge C) Q<=D;')
        out.append('end')
    out += ['else begin:bad initial $error("unsupported FF type"); end','endmodule','']
    return '\n'.join(out)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--graph',required=True);ap.add_argument('--manifest',required=True);ap.add_argument('--out',required=True);ap.add_argument('--top',default='qfd_sys_face_control_safe');ap.add_argument('--useful-cones',action='store_true');ap.add_argument('--physical-wrapper',action='store_true');a=ap.parse_args()
    assert not a.physical_wrapper or a.useful_cones, 'physical wrapper requires useful cone model'
    manifest=json.loads(Path(a.manifest).read_text())
    for p,h in manifest['source_sha256'].items():assert digest(p)==h, 'source hash mismatch: '+p
    src=json.loads(Path(a.graph).read_text());m,receipt=generate(src,manifest,a.useful_cones,a.physical_wrapper)
    receipt['source_graph_sha256']=digest(a.graph)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    core_top=a.top+'__safe_core' if a.physical_wrapper else a.top
    text=emit(m,core_top,src['modules']['qfd_sys_face'],manifest,receipt)
    if a.physical_wrapper:
        from physical_wrapper import wrapper
        text+=wrapper(a.top,core_top,receipt)
    receipt['core_top']=core_top;receipt['public_top']=a.top
    (out/'parent.sv').write_text(text)
    receipt['emitted_sha256']=digest(out/'parent.sv')
    (out/'graph.json').write_text(json.dumps({'modules':{core_top:m}},sort_keys=True))
    (out/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts'],sort_keys=True))
if __name__=='__main__':main()
