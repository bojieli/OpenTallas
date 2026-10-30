"""Trace selected emitted C-wrapper leaf command/partial boundary wiring only.

No flattened source graph, public-port aliases or unmeasured local producer ages
are inferred. Bound crossing depth includes source and destination ot_dp_st.
"""
import hashlib,json,re
from pathlib import Path
from layer_prog.emitted_norm_source import EmittedNormSource,_params
from layer_prog.bound_control import BoundControl


def _split(text):
    out=[];start=depth=0
    for i,c in enumerate(text):
        if c in '{(':depth+=1
        elif c in '})':depth-=1
        elif c==','and depth==0:out.append(text[start:i].strip());start=i+1
    out.append(text[start:].strip())
    return out


class Wiring:
    def __init__(self,text):
        self.widths={}
        for m in re.finditer(r'\b(?:wire|reg)\s*(?:\[(\d+):(\d+)\])?\s+(\w+)\s*[,;)]',text):
            if m[1]and m[2]!='0':raise ValueError('nonzero-based emitted wire range')
            self.widths[m[3]]=int(m[1])+1 if m[1]else 1
        self.drives={};self.delays={};self.inputs={};self.outputs={};self.landings={}
        for name,expr in re.findall(r'^\s*assign\s+(\w+)\s*=\s*([^;]+);',text,re.M):
            if name in self.drives:raise ValueError('multiple emitted wire drivers')
            self.drives[name]=expr.strip()
        for kind,params,name,ports in re.findall(r'^\s*(ot_dp_dly|ot_dp_st)\s+#\((.*?)\)\s+(\w+)\s*\((.*?)\);',text,re.M):
            p=_params(params);c=_params(ports);w=BoundControl._integer(p['W'])
            if kind=='ot_dp_dly':
                q=c['q'];self.delays[q]=(c['d'],BoundControl._integer(p['D']))
            elif name.startswith('u_bout_'):
                self.outputs[name.removeprefix('u_bout_')]=(c['d'],w)
            elif name.startswith('u_bin_'):
                self.inputs[c['q']]=(c['d'],w)
        for params,ports in re.findall(r'^\s*ot_dp_clk_landing\s+#\((.*?)\)\s+\w+\s*\((.*?)\);',text,re.M|re.S):
            p=_params(params);c=_params(ports);w=BoundControl._integer(p['W'])
            if len(self.bits(c['d']))!=w or len(self.bits(c['q']))!=w:
                raise ValueError('actual forwarded clock landing width differs')
            self.landings[c['q']]=c['d']
        self.cache={}

    def bits(self,expr):
        expr=expr.strip()
        if expr.startswith('{')and expr.endswith('}'):
            return [bit for part in reversed(_split(expr[1:-1]))for bit in self.bits(part)]
        m=re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?',expr)
        if not m:raise ValueError('unsupported selected emitted wiring expression: '+expr)
        name=m[1]
        if m[2]is None:
            if name not in self.widths:raise ValueError('emitted wire width absent: '+name)
            indexes=range(self.widths[name])
        else:
            hi=int(m[2]);lo=int(m[3])if m[3]is not None else hi
            if lo>hi or name not in self.widths or hi>=self.widths[name]:raise ValueError('selected emitted wire range differs')
            indexes=range(lo,hi+1)
        return [(name,i)for i in indexes]

    def trace(self,bit,terminals,stack=()):
        name,index=bit
        if name in terminals:return name,index,0
        if name in stack:raise ValueError('selected emitted wiring cycle')
        if name in self.delays:expr,delay=self.delays[name]
        elif name in self.drives:expr,delay=self.drives[name],0
        else:raise ValueError('selected emitted wire lacks a direct driver: '+name)
        bits=self.bits(expr)
        if index>=len(bits):raise ValueError('selected emitted driver width differs')
        target,j,age=self.trace(bits[index],terminals,stack+(name,))
        return target,j,age+delay


def collect(source,latency):
    die=EmittedNormSource(source)
    raw=json.loads(Path(latency).read_text())
    if raw.get('schema')!='opentallas.die_plan.bind.v1':raise ValueError('actual bound lane receipt required')
    lanes={r['lane']:r for r in raw['buses']}
    if len(lanes)!=len(raw['buses']):raise ValueError('duplicate actual lane')
    rows=[]
    for sl,row in sorted(die.rows.items(),key=lambda item:item[1]['sid']):
        text=Path(row['wrapper_file']).read_text();w=Wiring(text)
        instance=re.search(r'^\s*'+re.escape(row['xr_master'])+r'\s+#\((.*?)\)\s+'+re.escape(row['xr_instance'])+r'\s*\((.*?)^\s*\);',text,re.M|re.S)
        ports=_params(instance[2]);cmd={p:w.bits(ports[p])for p in ('c_v','c_d')};partial={p:w.bits(ports[p])for p in ('p_v','p_d')}
        cv=cmd['c_v'];cd=cmd['c_d']
        if len(cv)!=5 or len(cd)!=160 or len(partial['p_v'])!=5 or len(partial['p_d'])!=160:
            raise ValueError('actual selected XR command/partial width differs')
        terminals={n for bits in cmd.values()for n,_ in bits}
        # Native input _q names are literal ot_dp_st receiver outputs. Their
        # stages are already included in bind_latency.bound_stages.
        inputs={q:meta for q,meta in w.inputs.items()}
        if not inputs:raise ValueError('actual native boundary input receivers absent')
        for k in range(5):
            dn=lanes['dn_'+row['part'][:-2]+'_L'+str(k)];up=lanes['up_'+row['part'][:-2]+'_L'+str(k)]
            if dn['src']!=row['part']or up['dst']!=row['part']or dn['dst']!=up['src']:
                raise ValueError('selected leaf crossing endpoints differ')
            for bus,direction,port in [(dn,'output',dn['bus_out']),(up,'input',up['bus_in'])]:
                header=re.search(r'^\s*'+direction+r'\s+wire\s+\[(\d+):0\]\s+'+re.escape(port)+r'\s*,\s*//\s*(\d+) data \+ epoch \[(\d+)\]: lane '+re.escape(bus['lane'])+r', (\d+) cycles:',text,re.M)
                if not header or [int(header[i])for i in (1,2,3)]!=[bus['width']]*3 or int(header[4])!=bus['bound_stages']:
                    raise ValueError('actual emitted lane/header width or cycle identity differs')
            expr,width=w.outputs[dn['bus_out']]
            if width!=dn['width']or len(dn['source_bits'])!=width:raise ValueError('native active source width differs')
            routed=[]
            for i,b in enumerate(w.bits(expr)):
                try:routed.append((i,w.trace(b,terminals)))
                except ValueError:pass # Other down-bus fields are outside this exact view.
            valid=[(i,a)for i,(n,j,a)in routed if (n,j)==cv[k]]
            data=[[(i,a)for i,(n,j,a)in routed if (n,j)==bit]for bit in cd]
            if len(valid)!=1 or any(len(hit)!=1 for hit in data):raise ValueError('actual selected command bit missing/duplicated')
            command=list(valid)+[hit[0]for hit in data]
            if len({age for _,age in command})!=1:raise ValueError('selected command valid/data local ages differ')
            producers={b[1]for b in up['source_bits']if b[0]=='leaf'and b[2]in('p_v','p_d')and b[1].startswith(sl+'.')and b[1].endswith('.u_vn.u_b')}
            if len(producers)!=1:raise ValueError('one actual native VN_b partial producer required per selected leaf lane')
            producer=next(iter(producers))
            pa=[];pv=[]
            for port,bits in [('p_v',[partial['p_v'][k]]),('p_d',partial['p_d'][32*k:32*(k+1)])]:
                traced=[]
                for bit in bits:
                    q,index,age=w.trace(bit,set(inputs))
                    ext,n=inputs[q];extbits=w.bits(ext);outside=extbits[index]
                    if outside[0]in w.landings:outside=w.bits(w.landings[outside[0]])[outside[1]]
                    if n!=up['width']or index>=n or outside!=(up['bus_in'],index):
                        raise ValueError('actual partial boundary receiver mapping differs')
                    src=up['source_bits'][index]
                    # Require the actual b-half partial source; no A/Y alias,
                    # guessed public port or spare boundary bit is accepted.
                    expected=['leaf',producer,port,len(traced)]
                    if src!=expected:raise ValueError('actual partial source bit differs: '+str((src,expected)))
                    traced.append(dict(bus_bit=index,local_edges=age))
                (pv if port=='p_v'else pa).extend(traced)
            local={b['local_edges']for b in pv+pa}
            if len(local)!=1:raise ValueError('partial valid/data local stages differ')
            down=dn['bound_stages']+command[0][1];back=up['bound_stages']+next(iter(local))
            rows.append(dict(slice=sl,sid=row['sid'],leaf=k,actual_vn_b_partial_producer=producer,command_lane=dn['lane'],partial_lane=up['lane'],
                command_active_width=dn['width'],command_bus_bits=dict(valid=valid[0][0],data=[hit[0][0]for hit in data]),
                partial_active_width=up['width'],partial_bus_bits=dict(valid=pv[0]['bus_bit'],data=[p['bus_bit']for p in pa]),
                xr_command_to_leaf_boundary_edges=down,vn_b_partial_to_xr_input_edges=back,
                local_command_edges=command[0][1],local_partial_edges=next(iter(local)),pdsk_edges=die.deskew[sl][k],
                crossing_plus_pdsk_edges=down+back+die.deskew[sl][k]))
    return dict(schema='opentallas.s81.emitted_leaf_boundary_routes.v1',verdict='PASS_SELECTED_BOUNDARY_WIRING',
        source_top_sha256=die.die_sha,source_view_sha256=die.source_record['source_view_sha256'],
        bind_latency_sha256=hashlib.sha256(Path(latency).read_bytes()).hexdigest(),leaves=rows,
        scope='actual emitted XR command to native leaf boundary; actual VN_b partial to XR input; local norm producer ages remain separate',
        norm_producer_qualified=False,go_readiness_qualified=False,full_token=False,added_rtl_cycles=0)
