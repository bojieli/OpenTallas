"""Fail-closed domain/cut census of an actual proc/opt Yosys hierarchy.

This diagnostic does not admit a physical parent. In particular its JSON input
is not trusted as an authenticated replacement for elaborating pinned sources.
It identifies extra crossings and public payload consumer nets needed by a
future mapped-graph admission, while retaining an explicit source-binding debt.
"""
from collections import defaultdict
import re


class Bits:
    def __init__(self): self.parent={}
    def find(self,x):
        if isinstance(x,str):return x  # Yosys literal x/z/0/1; no timing source.
        self.parent.setdefault(x,x)
        if self.parent[x]!=x:self.parent[x]=self.find(self.parent[x])
        return self.parent[x]
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a==b:return
        if isinstance(a,str):self.parent[b]=a
        else:self.parent[a]=b


def audit(document,top,clock_domains,input_domains=None,output_domains=None,require_bit_graph=False):
    """Find every inferred input ownership and non-FIFO inter-domain data edge.

    Clock roots are literal top ports. Approved FIFO implementations are cut at
    their real writer/read ports; callers must authenticate their source first.
    No combinational/FF naming grants an asynchronous exception.
    """
    modules=document['modules'];bits=Bits();cells=[];fifos=[];names=defaultdict(set)
    def bit(scope,b):return b if isinstance(b,str)else(scope,b)
    def walk(module_name,scope):
        module=modules[module_name]
        if module.get('processes') or module.get('memories'):
            raise ValueError(f'{scope}: proc/opt cell graph and explicit flop memory required')
        for name,net in module.get('netnames',{}).items():
            if not net.get('hide_name'):
                for i,b in enumerate(net['bits']):
                    if isinstance(b,str):continue
                    label=(scope+'.'if scope else'')+name
                    if len(net['bits'])>1 or net.get('offset',0):label+='['+str(i+net.get('offset',0))+']'
                    names[bit(scope,b)].add(label)
        for name,cell in module.get('cells',{}).items():
            full=(scope+'.'if scope else'')+name
            con={p:[bit(scope,b)for b in bs]for p,bs in cell['connections'].items()}
            typ=cell['type']
            if typ in modules:
                child=modules[typ]
                if child.get('attributes',{}).get('hdlname')=='ot_hbm_svc_async_fifo' or typ=='ot_hbm_svc_async_fifo':
                    fifos.append(dict(path=full,module=typ,connections=con,parameters=child.get('parameter_default_values',{})))
                    continue
                for p,info in child['ports'].items():
                    if not con.get(p) and info['direction']=='output':continue
                    if p not in con or len(info['bits'])!=len(con[p]):raise ValueError(f'{full}: port width mismatch {p}')
                    for local,parent in zip(info['bits'],con[p]):bits.join(bit(full,local),parent)
                walk(typ,full)
            else:cells.append((full,cell,con))
    walk(top,'')
    def canon(bs):return[bits.find(b)for b in bs]
    top_ports=modules[top]['ports']
    roots={}
    for name,domain in clock_domains.items():
        match=re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)(?:\[([0-9]+)\])?',name)
        if not match or match[1]not in top_ports:raise ValueError(f'invalid actual clock root {name}')
        port=top_ports[match[1]];index=int(match[2])-port.get('offset',0)if match[2]is not None else 0
        if (match[2]is None and len(port['bits'])!=1)or not 0<=index<len(port['bits']):
            raise ValueError(f'invalid actual clock root {name}')
        key=bits.find(bit('',port['bits'][index]))
        if isinstance(key,str):raise ValueError('clock root is constant or unknown')
        if key in roots and roots[key]!=domain:raise ValueError('clock domain aliases disagree')
        roots[key]=domain
    def root(bs,where):
        if len(bs)!=1 or bits.find(bs[0])not in roots:raise ValueError(f'{where}: clock not driven by declared top root')
        return roots[bits.find(bs[0])]
    origins=defaultdict(set);edges=[];consumers=[];violations=[];fifo_records=[]
    public_names=defaultdict(set)
    for b,values in names.items():public_names[bits.find(b)].update(values)
    for name,p in top_ports.items():
        if p['direction']=='input' and name not in clock_domains:
            for b in p['bits']:
                key=bits.find(bit('',b))
                if key not in roots:origins[key].add('input:'+name)
    for path,cell,con in cells:
        typ=cell['type']
        if typ=='$scopeinfo':continue
        if typ in ('$dff','$dffe','$adff','$adffe','$sdff','$sdffe','$sdffce','$_DFF_P_','$_DFF_PN0_','$_DFF_PP0_','$_DFF_PN1_','$_DFF_PP1_'):
            domain=root(con.get('CLK',con.get('C',[])),path)
            for b in canon(con['Q']):origins[b].add('domain:'+domain)
            # Asynchronous controls keep recovery/removal timing separately;
            # synchronous reset/enable are real data-domain dependencies.
            if len(con['D'])!=len(con['Q']):raise ValueError('flop data/output width mismatch')
            for d,q in zip(con['D'],con['Q']):consumers.append((path+':D',domain,canon([d]),canon([q])))
            for control in ('EN','SRST'):
                if control in con:consumers.append((path+':'+control,domain,canon(con[control]),[]))
        elif typ in {'$add','$sub','$mul','$div','$mod','$divfloor','$modfloor','$pow','$shl','$shr','$sshl','$sshr','$shift','$shiftx','$lt','$le','$eq','$ne','$eqx','$nex','$ge','$gt','$not','$and','$or','$xor','$xnor','$reduce_and','$reduce_or','$reduce_xor','$reduce_xnor','$reduce_bool','$logic_not','$logic_and','$logic_or','$mux','$pmux','$bmux','$demux','$slice','$concat','$pos','$neg','$alu','$fa','$lcu','$lut','$sop','$_AND_','$_OR_','$_XOR_','$_NOT_','$_MUX_','$_XNOR_','$_ANDNOT_','$_ORNOT_','$_NAND_','$_NOR_'}:
            if typ in ('$assert','$assume','$cover','$check'):raise ValueError(f'{path}: unsupported formal cell {typ}')
            if any(k in con for k in ('CLK','C','ARST','SRST'))or 'mem'in typ.lower()or 'latch'in typ.lower():
                raise ValueError(f'{path}: unsupported state primitive {typ}')
            ins=[];outs=[]
            for p,direction in cell['port_directions'].items():
                if direction=='input':ins+=canon(con[p])
                elif direction=='output':outs+=canon(con[p])
                else:raise ValueError(f'{path}: unsupported bidirectional cell')
            if require_bit_graph and (len(outs)!=1 or any(len(con[p])!=1 for p in con)):
                raise ValueError(f'{path}: payload grants require actual bit-level primitive graph')
            edges.append((ins,outs))
        else:raise ValueError(f'{path}: missing actual module {typ}')
    for f in fifos:
        con=f['connections'];wr=root(con['wr_clk'],f['path']);rd=root(con['rd_clk'],f['path'])
        if wr==rd:raise ValueError(f"{f['path']}: FIFO clocks are not two declared domains")
        for p in ('wr_ready','wr_overflow'):
            for b in canon(con[p]):origins[b].add('domain:'+wr)
        for p in ('rd_valid','rd_underflow','rd_data'):
            for b in canon(con[p]):origins[b].add('domain:'+rd)
        for index,b in enumerate(canon(con['rd_data'])):origins[b].add('payload:'+f['path']+':'+str(index))
        for domain,ports in ((wr,('wr_valid','wr_data')),(rd,('rd_ready',))):
            consumers.append((f['path']+':'+domain,domain,canon(sum((con[p]for p in ports),[])),[]))
        fifo_records.append(dict(path=f['path'],writer_domain=wr,reader_domain=rd,parameters=f['parameters']))
    # Monotone finite union; no iteration cut-off can hide an unresolved cone.
    changed=True
    while changed:
        changed=False
        for ins,outs in edges:
            value=set().union(*(origins[b]for b in ins))
            for b in outs:
                if isinstance(b,str):continue
                old=len(origins[b]);origins[b].update(value);changed|=len(origins[b])!=old
    input_uses=defaultdict(set);payload_targets=defaultdict(set);payload_outputs=defaultdict(set);target_bits=defaultdict(lambda:defaultdict(set));output_bits=defaultdict(lambda:defaultdict(set))
    def check(path,domain,data,outputs):
        value=set().union(*(origins[b]for b in data))
        for origin in value:
            kind,name=origin.split(':',1)
            if kind=='input':input_uses[name].add(domain)
            elif kind=='domain'and name!=domain:violations.append(dict(kind='extra_crossing',consumer=path,source_domain=name,target_domain=domain))
            elif kind=='payload':
                scope,index=name.rsplit(':',1)
                if path.endswith((':EN',':SRST')):
                    violations.append(dict(kind='payload_control',consumer=path,fifo=scope))
                for b in outputs:
                    if isinstance(b,str):continue
                    payload_targets[scope].update(public_names[b]);target_bits[scope][index].update(public_names[b])
        for b in data:
            if not isinstance(b,str)and not origins[b]:violations.append(dict(kind='unowned_cone',consumer=path,bit=repr(b)))
    for path,domain,data,outputs in consumers:check(path,domain,data,outputs)
    for name,p in top_ports.items():
        if p['direction']=='output':
            values=set().union(*(origins[bits.find(bit('',b))]for b in p['bits']))
            domains={v[7:]for v in values if v.startswith('domain:')}
            if len(domains)>1:violations.append(dict(kind='mixed_output_domains',output=name,domains=sorted(domains)))
            literal=all(bits.find(bit('',b))in ('0','1')for b in p['bits'])
            if output_domains is not None and not literal and domains!={output_domains.get(name)}:
                violations.append(dict(kind='output_owner_mismatch',output=name,actual=sorted(domains),declared=output_domains.get(name)))
            for index,b in enumerate(p['bits']):
                label=name+'['+str(index+p.get('offset',0))+']'if len(p['bits'])>1 or p.get('offset',0)else name
                for v in origins[bits.find(bit('',b))]:
                    if v.startswith('payload:'):
                        scope,source_bit=v[8:].rsplit(':',1)
                        payload_outputs[scope].add(label);output_bits[scope][source_bit].add(label)
    for name,used in input_uses.items():
        if len(used)>1:violations.append(dict(kind='shared_input_domains',input=name,domains=sorted(used)))
        if input_domains is not None and used!={input_domains.get(name)}:
            violations.append(dict(kind='input_owner_mismatch',input=name,actual=sorted(used),declared=input_domains.get(name)))
    return dict(schema='opentallas.async_fifo.source_domain_census.v1',top=top,
                scope='diagnostic source hierarchy; source authentication and actual mapped path proof still required',
                verdict='REFUSE'if violations else'PASS_SOURCE_GRAPH_ONLY',fifo_instances=fifo_records,
                input_domains={k:sorted(v)for k,v in sorted(input_uses.items())},
                payload_consumer_public_nets={k:sorted(v)for k,v in sorted(payload_targets.items())},
                payload_output_ports={k:sorted(v)for k,v in sorted(payload_outputs.items())},
                payload_consumer_bits={scope:{i:sorted(v)for i,v in data.items()}for scope,data in target_bits.items()},
                payload_output_bits={scope:{i:sorted(v)for i,v in data.items()}for scope,data in output_bits.items()},
                bit_graph_required=require_bit_graph,
                violations=violations,physical_admitted=False)


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('json');p.add_argument('--top',required=True)
    p.add_argument('--clock',action='append',required=True,help='literal top clock port:domain')
    a=p.parse_args();clock_domains={}
    for item in a.clock:
        name,domain=item.rsplit(':',1)
        if name in clock_domains:p.error('duplicate clock root')
        clock_domains[name]=domain
    print(json.dumps(audit(json.load(open(a.json)),a.top,clock_domains),indent=2))
