from pathlib import Path
import json,re,collections,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import die_sta as D
p=Path(__file__).resolve().parent
top=D.read_verilog(p/'source_top.sv')['s81_head_top']
selected={'turnE0a':'turn_a.v','turnE0b':'turn_b.v'}
uf={}
def root(x):
    while uf.get(x,x)!=x:x=uf[x]
    return x
for a,b in top.assigns:
    x,y=root(a),root(b)
    if x!=y:uf[x]=y
usage=collections.defaultdict(list);instances=[];joins={}
for module,inst,cs in top.insts:
    if inst not in selected:continue
    actual=D.read_verilog(p/selected[inst])[module]
    dirs={n:d for d,n,_m,_l in actual.ports}
    assert set(dirs)==set(dict(cs)),(inst,'source/actual ports differ')
    normalized=[]
    for port,bits in cs:
        # This bounded boundary assembly uses a common ideal parent root;
        # every CHILD routed tree/clock RC and the forwarded seam stay real.
        bits=['clk'] if re.fullmatch(r'clk(?:_t[0-9]+)?',port) else [root(b) for b in bits]
        normalized.append((port,bits))
        for b in bits:
            if "'" not in b:usage[b].append((inst,port,dirs[port]))
    instances.append((module,inst,normalized))
    joins[inst]={'actual_module':module,'ports':len(dirs),'source_actual_port_match':True}
def ident(s):return s if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',s) else '\\'+s+' '
external={};internal=[]
for b,u in sorted(usage.items()):
    writers=[x for x in u if x[2]=='output'];readers=[x for x in u if x[2]=='input']
    assert len(writers)<=1,(b,writers)
    if writers and readers:internal.append(b)
    elif writers:external[b]='output'
    else:external[b]='input'
lines=['// Bounded HEAD signed-child boundary assembly: actual source connections, routed child RC.',
       '// Parent source taps use one IDEAL common root. No full-die-clock or freeze claim.',
       'module head_pair ('+', '.join(ident(n) for n in external)+');']
lines += [d+' '+ident(n)+';' for n,d in external.items()]
lines += ['wire '+ident(n)+';' for n in internal]
for mod,inst,cs in instances:
    conn=[]
    for port,bits in cs:
        expr=','.join(b if "'" in b else ident(b) for b in bits)
        if len(bits)>1:expr='{'+expr+'}'
        conn.append('.'+ident(port)+'('+expr+')')
    lines.append(mod+' '+inst+' ('+',\n'.join(conn)+');')
lines.append('endmodule')
(p/'head_pair.v').write_text('\n'.join(lines)+'\n')
(p/'pair_scope.json').write_text(json.dumps({'parts':joins,'internal_bits':len(internal),'clock':'ideal common parent root, actual propagated child clock RC and forwarded seam','parent_plan':'l48uh','inputs':'unconnected external interface nets exposed as ports, no invented tie-offs','full_die_sta':'NOT RUN'},indent=1)+'\n')
print('PAIR',joins,'internal_bits',len(internal),'external_bits',len(external))
