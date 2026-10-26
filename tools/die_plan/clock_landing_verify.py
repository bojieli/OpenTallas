"""Independent structural checks for the opt-in landed clock/status network.

The ring's conditional data identity is a proved component contract, not a
claim of phase-window qualification. Every actual ring, forwarded clock,
registered collector operand and observer gate is checked here; no leaf input
is exempted from the ordinary connectivity comparison.
"""
import re
from collections import defaultdict


def ident(s):return re.sub(r'\W','_',s)


def boolean(op,terms):
    items=[]
    for t in terms:
        if t[0]==op:items.extend(t[1:])
        else:items.append(t)
    return (op,*sorted(items,key=repr))


class Verification:
    def __init__(self,F,G,raw,table,names):
        self.F,self.G,self.raw,self.table,self.names=F,G,raw,table,names
        self.observer_seen=set();self.errors=[];self.byname={c.path:c for c in F.cells};self.expected=set();self.memo={}
        self.parts={p['name']:p for p in raw['partitions']};self.collector=table['collector']
        self.region={pn:r['tag'] for r in table['regions'] for pn in r['parts']}
        # Some profile manifests carry the authoritative part map separately.
        for p in self.parts:
            if p not in self.region:
                q=self.parts[p];t=raw['partition_types'][q['type']];x,y=q['origin_um'];w,h=t['outline_um']
                rr=[r['tag'] for r in table['regions'] if r['box_um'][0]<=x+w/2<r['box_um'][2] and r['box_um'][1]<=y+h/2<r['box_um'][3]]
                if len(rr)!=1:raise ValueError('landing verify: ambiguous region '+p)
                self.region[p]=rr[0]
        self.root_collect={};self.checks=0
        for pn,p in self.parts.items():
            info=self.collector['types'][p['type']]
            if info['mask']['active']:
                self.root_collect[pn]=ident(pn)+'.u_cland_collect_'+ident(info['collector_root_node'])
        self._check_all()

    def fail(self,s):self.errors.append(s)
    def pin(self,path,port,bit=0):return ('pin',path,port,bit)
    def output(self,path,port,bit=0):
        c=self.byname.get(path)
        if c is None or bit>=len(c.ports.get(port,[])):
            self.fail(f'missing actual infrastructure output {path}.{port}[{bit}]')
            return ('missing',path,port,bit)
        return self.pin(path,port,bit)

    def term(self,net,seen=()):
        if isinstance(net,str):return ('const',net)
        if net in self.memo:return self.memo[net]
        if net in seen:return ('loop',)
        ds=self.G.drv.get(net,[])
        if net in self.G.top_in:
            if ds:return ('multi',)
            port,bit=self.G.top_in[net];return ('top',port,bit)
        if len(ds)!=1:return ('drivers',len(ds))
        ci,pn,bit=ds[0];c=self.F.cells[ci]
        if c.kind=='glue' and pn=='Y':
            op={'$and':'and','$logic_and':'and','$or':'or','$logic_or':'or','$not':'not','$logic_not':'not','$buf':'buf','$pos':'buf'}.get(c.ytype)
            if op:
                terms=[self.term(b,seen+(net,)) for port in ('A','B') for b in c.ports.get(port,[])]
                result=terms[0] if op=='buf' and len(terms)==1 else boolean(op,terms) if op in ('and','or') else (op,*terms)
                self.memo[net]=result;return result
        return self.pin(c.path,pn,bit)

    def instance(self,path,module):
        self.expected.add(path);c=self.byname.get(path)
        if c is None:self.fail('missing infrastructure '+path);return None
        if c.module!=module:self.fail(f'{path}: expected {module}, actual {c.module}')
        return c

    def equal_input(self,c,port,want):
        self.checks+=1
        got=[self.term(b) for b in c.ports.get(port,[])]
        if got!=want:self.fail(f'{c.path}.{port}: actual {got!r} != expected {want!r}')

    def clock(self,c,part,port='clk'):
        self.equal_input(c,port,[('top','clk_region_'+ident(self.region[part]),0)])

    def check_reset(self,c,part,node,extra=None):
        bits=c.ports.get('rst_n',[])
        if len(bits)!=1:self.fail(c.path+': exact one-bit raw reset required');return
        tree=self.collector['types'][self.parts[part]['type']]['tree']
        rows={r['q']:r for r in tree['relays']};prefix=ident(part)+'.'
        def walk(net,n,seen):
            if n in seen:return False
            ds=self.G.drv.get(net,[])
            if len(ds)!=1:return False
            ci,port,bit=ds[0];up=self.F.cells[ci]
            if n=='rst_root_n':
                # Stop at this partition's original reset entry, preserving
                # its synchronizer/lock qualifier and original global tree.
                roots={'u_rst_in':('ot_dp_rrelay','q'),'u_rst_root':('ot_dp_rsync_s'+str(tree.get('sync_stages',2)),'sync_rst_n')}
                if tree.get('lock'):roots={'u_rst_lockq':('ot_dp_lockq','q')}
                return any(up.path==prefix+k and up.module==v[0] and port==v[1] for k,v in roots.items())
            row=rows.get(n)
            if not row:return False
            allowed={prefix+row['name'],prefix+row['name']+'_r',prefix+'u_cland_reset_'+ident(n)}
            if extra:allowed.add(prefix+extra)
            if up.path not in allowed or up.module!='ot_dp_rrelay' or port!='q':return False
            ib=up.ports.get('d',[])
            return len(ib)==1 and walk(ib[0],row['d'],seen|{n})
        if not walk(bits[0],node,set()):
            self.fail(c.path+': raw reset is not the exact original local reset-parent/depth contract at '+node)

    def _check_all(self):
        rows=self.table['ports'];ports={p['id']:p for p in self.raw['ports']}
        for r in rows:
            pr=ports[r['port']];bus=pr['dst']['bus'];path=ident(r['dst'])+'.u_cland_'+bus
            c=self.instance(path,'ot_dp_clk_landing')
            if c:
                self.clock(c,r['dst']);self.clock(c,r['src'],'fclk')
                info=self.collector['types'][self.parts[r['dst']]['type']]
                local=next(x for x in info['local_sources'] if x['name']==bus)
                self.check_reset(c,r['dst'],f"rst_n_t{local['tap']}",'u_cland_rst_'+bus)
                if len(c.ports.get('q',[]))!=len(c.ports.get('d',[])) or len(c.ports.get('q',[]))<r['width']:
                    self.fail(path+': whole live payload/epoch bus must survive')
        for pn,p in self.parts.items():
            info=self.collector['types'][p['type']]
            if not info['mask']['active']:continue
            sources=[]
            for src in info['local_sources']:
                path=ident(pn)+'.u_cland_'+src['name']
                sources.append(dict(node=f"rst_n_t{src['tap']}",ready=self.output(path,'ready'),fault=self.output(path,'fault')))
            for child in info['children']:
                cn=child['part'];root=self.root_collect[cn];r=self.output(root,'ready_o');f=self.output(root,'fault_o')
                if child['seam']:
                    path=ident(pn)+'.u_cland_monitor_'+str(child['index']);c=self.instance(path,'ot_dp_clk_landing')
                    if c:
                        self.clock(c,pn);self.clock(c,cn,'fclk');self.check_reset(c,pn,child['node'])
                        self.equal_input(c,'d',[r,f])
                        if len(c.ports.get('q',[]))!=2:self.fail(path+': monitor must retain both status bits')
                    r=boolean('and',[self.output(path,'q',0),self.output(path,'ready'),('not',self.output(path,'fault'))])
                    f=boolean('or',[self.output(path,'q',1),self.output(path,'fault')])
                sources.append(dict(node=child['node'],ready=r,fault=f))
            tree=info['tree'];root=info['collector_root_node'];adj=defaultdict(list)
            for row in tree['relays']:adj[row['q']].append(row['d']);adj[row['d']].append(row['q'])
            parent={root:None};todo=[root]
            while todo:
                n=todo.pop()
                for q in adj[n]:
                    if q not in parent:parent[q]=n;todo.append(q)
            active=set();at=defaultdict(list)
            for s in sources:
                n=s['node'];at[n].append(s)
                while n is not None:active.add(n);n=parent[n]
            children=defaultdict(list)
            for n in active-{root}:children[parent[n]].append(n)
            for n in sorted(active):
                path=ident(pn)+'.u_cland_collect_'+ident(n);c=self.instance(path,'ot_dp_landing_collect')
                if not c:continue
                self.clock(c,pn);self.check_reset(c,pn,n)
                for port,key in [('ready_i','ready'),('fault_i','fault')]:
                    want=[s[key] for s in at[n]]+[self.output(ident(pn)+'.u_cland_collect_'+ident(q),key+'_o') for q in sorted(children[n])]
                    # Concatenation is MSB first in RTL, Yosys bits are LSB first.
                    self.equal_input(c,port,list(reversed(want)))
        actual={c.path for c in self.F.cells if c.module in ('ot_dp_clk_landing','ot_dp_landing_collect')}
        for x in sorted(actual-self.expected):self.fail('unexpected/unpriced infrastructure '+x)
        for x in sorted(self.expected-actual):self.fail('missing infrastructure instance '+x)

    def observer_input(self,c,port,bit):
        """Return original input net only after the exact live gate is proved."""
        obs=self.collector['observer'];root=self.root_collect[obs['part']]
        if c.module!=obs['module'] or not c.path.startswith(ident(obs['part'])+'.') or not c.path.endswith(obs['instance_suffix']):return None
        options={obs['fault_port']:('$or','fault_o'),obs['ready_port']:('$and','ready_o')}
        if port not in options:return None
        self.observer_seen.add(port)
        if bit!=0 or len(c.ports[port])!=1:self.fail('observer input is not exactly one bit');return None
        typ,outport=options[port];ds=self.G.drv.get(c.ports[port][0],[])
        if len(ds)!=1:self.fail('observer gate missing/ambiguous '+port);return None
        ci,op,obit=ds[0];gate=self.F.cells[ci]
        if gate.ytype!=typ or op!='Y' or len(gate.ports.get('Y',[]))!=1:
            self.fail(f'observer {port}: exact {typ} gate required');return None
        a=gate.ports.get('A',[]);b=gate.ports.get('B',[])
        if len(a)!=1 or len(b)!=1:self.fail('observer gate operand width');return None
        monitor=self.output(root,outport)
        if self.term(a[0])==monitor:return b[0]
        if self.term(b[0])==monitor:return a[0]
        self.fail('observer '+port+': actual registered monitor root absent');return None

    def report(self):
        obs=self.collector['observer'];want={obs['fault_port'],obs['ready_port']}
        if self.observer_seen!=want:self.fail('actual native observer ports not both verified: '+str(self.observer_seen))
        return dict(errors=self.errors,structural_checks=self.checks,instances=len(self.expected),physical_qualified=False)
