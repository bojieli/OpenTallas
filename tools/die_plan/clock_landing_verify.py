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
    def __init__(self,F,G,raw,table,names,live_widths=None,plan_path=None,reset_tree=None):
        self.F,self.G,self.raw,self.table,self.names=F,G,raw,table,names
        # TOK-QC-4: inactive landing types carry collector tree None, but may still host count-aligned infrastructure
        # (an intra-region start relay rx).  Their raw reset is the type's ordinary plan reset tree, the one the bind
        # emits (RT.for_type); reset_tree(tn) may be injected (tests).  No tree -> FAIL, never skip.
        self.plan_path,self._reset_tree_fn,self._plan_trees=plan_path,reset_tree,{}
        self.observer_seen=set();self.errors=[];self.byname={c.path:c for c in F.cells};self.expected=set();self.memo={};self._fstart_checked=set()
        self.parts={p['name']:p for p in raw['partitions']};self.collector=table['collector']
        self.live_widths=live_widths
        self.region={pn:r['tag'] for r in table['regions']
                     if isinstance(r.get('parts'),list) for pn in r['parts']}
        for r in table['regions']:
            if type(r.get('parts')) not in (int,list):
                raise ValueError('landing verify: region parts must be a count or explicit list')
        # Some profile manifests carry the authoritative part map separately.
        for p in self.parts:
            if p not in self.region:
                q=self.parts[p];t=raw['partition_types'][q['type']];x,y=q['origin_um'];w,h=t['outline_um']
                rr=[r['tag'] for r in table['regions'] if r['box_um'][0]<=x+w/2<r['box_um'][2] and r['box_um'][1]<=y+h/2<r['box_um'][3]]
                if len(rr)!=1:raise ValueError('landing verify: ambiguous region '+p)
                self.region[p]=rr[0]
        for r in table['regions']:
            if type(r.get('parts')) is int:
                count=sum(tag==r['tag'] for tag in self.region.values())
                if count!=r['parts']:
                    raise ValueError(f"landing verify: region {r['tag']} has {count} actual parts, expected {r['parts']}")
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

    def check_reset(self,c,part,node,extra=None,port='rst_n'):
        bits=c.ports.get(port,[])
        if len(bits)!=1:self.fail(c.path+': exact one-bit raw reset required');return
        tree=self.reset_tree(self.parts[part]['type'])
        if tree is None:
            self.fail(c.path+': no planned reset tree for type '+self.parts[part]['type']+' (inactive landing type)');return
        rows={r['q']:r for r in tree['relays']};prefix=ident(part)+'.'
        if tree.get('hard'):
            # Hard wrapper: every landing/collector stage uses the delivered
            # reset, i.e. exactly the reset of the wrapper's own stations.
            ref=self.hard_reset(part)
            if ref is None or self.term(bits[0])!=ref:
                self.fail(c.path+': hard-wrapper landing reset is not the delivered partition reset')
            return
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

    def reset_tree(self,tn):
        """The reset tree a landing stage of type tn walks: the collector tree (active types), else the type's plan reset
        tree as the bind emits it (RT.for_type on the plan); None (-> FAIL at the caller) if neither exists."""
        tree=self.collector['types'][tn]['tree']
        if tree is not None:return tree
        if tn not in self._plan_trees:
            try:
                if self._reset_tree_fn is not None:t=self._reset_tree_fn(tn)
                else:
                    import schema as S,reset_tree as RT
                    if not hasattr(self,'_P'):self._P=S.Plan(self.raw,self.plan_path)
                    t=RT.for_type(self._P,tn)
            except Exception as e:
                self.fail(f'type {tn}: plan reset tree unavailable ({type(e).__name__}: {e})');t=None
            if t is not None and (t.get('hard') or not isinstance(t.get('relays'),list)):
                self.fail(f'type {tn}: plan reset tree has no relay list');t=None
            self._plan_trees[tn]=t
        return self._plan_trees[tn]

    def hard_reset(self,part):
        if not hasattr(self,'_hard_reset'):self._hard_reset={}
        if part not in self._hard_reset:
            prefix=ident(part)+'.';ref=None
            for c in self.F.cells:
                if c.path.startswith(prefix) and c.module=='ot_dp_st' and len(c.ports.get('rst_n',[]))==1:
                    ref=self.term(c.ports['rst_n'][0]);break
            self._hard_reset[part]=ref
        return self._hard_reset[part]

    def ring_reset_node(self,part,bus,info):
        """Ring reset follows nearest physical clock tap, independently of status collector tap."""
        t=self.raw['partition_types'][self.parts[part]['type']]
        geom=next((b for b in t.get('buses',[]) if b['name']==bus and 'face' in b and 'window_um' in b),None)
        if geom is None:geom=info.get('bus_geometry',{}).get(bus)
        if geom is None:
            slot=next((x for x in t.get('ft_slots',[]) if x['name']+'_i'==bus),None)
            if slot and 'in_window_um' in slot:geom=dict(face=slot['in_face'],window_um=slot['in_window_um'])
        if geom is None:raise ValueError('landing verify: missing planned ring geometry '+part+'.'+bus)
        face=geom['face'];at=sum(geom['window_um'])/2;w,h=t['outline_um']
        x,y=(0 if face=='W' else w,at) if face in 'EW' else (at,0 if face=='S' else h)
        from clock_landings import ring_taps
        taps=ring_taps(self.raw,self.parts[part]['type'])
        tap=min(range(len(taps)),key=lambda i:abs(taps[i][0]-x)+abs(taps[i][1]-y)) if taps else 0
        return f'rst_n_t{tap}'

    def _check_all(self):
        rows=self.table['ports'];ports={p['id']:p for p in self.raw['ports']}
        for r in rows:
            pr=ports[r['port']];bus=pr['dst']['bus'];path=ident(r['dst'])+'.u_cland_'+bus
            ca=self.table.get('count_aligned')
            c=self.instance(path,('ot_dp_clk_landing_cas' if ca.get('strap_form') else 'ot_dp_clk_landing_ca') if ca else 'ot_dp_clk_landing')
            if c:
                self.clock(c,r['dst']);self.clock(c,r['src'],'fclk')
                info=self.collector['types'][self.parts[r['dst']]['type']]
                local=next(x for x in info['local_sources'] if x['name']==bus)
                if ca:
                    cfg=ca['ports'][r['port']]
                    params=getattr(c,'params',{})
                    if int(params.get('DEPTH',4))!=int(cfg['depth']):
                        self.fail(path+': actual count-aligned DEPTH differs from the bound contract')
                    if ca.get('strap_form'):
                        kb=c.ports.get('strap_k',[])
                        kw=int(cfg['depth']).bit_length()-1+4
                        expected=list(reversed(format(int(cfg['K']) & ((1<<kw)-1),f'0{kw}b')))
                        if kb!=expected:self.fail(path+': actual strap_k differs from the bound count')
                    elif (int(params.get('K',2)) & 0xffffffff)!=(int(cfg['K']) & 0xffffffff):
                        self.fail(path+': actual count-aligned K differs from the bound contract')
                    # count-aligned (MESO-INTEG-1): read count from the receiver's origin, write count from the
                    # sender's origin forwarded beside the bus; the origins themselves are checked below
                    self.equal_input(c,'rst_n',[self.start_net(r['dst'])])
                    self.equal_input(c,'t_rst_n',[self.fstart_net(r['src'],pr['src']['bus'])])
                else:
                    self.check_reset(c,r['dst'],self.ring_reset_node(r['dst'],bus,info),'u_cland_rst_'+bus)
                import schema
                lane=r.get('lane',r['port'])
                data_width=int(r['width']) if self.live_widths is None else self.live_widths.get(lane)
                if type(data_width) is not int or not 0<data_width<=int(r['width']):
                    self.fail(path+': missing/invalid authoritative live lane width')
                else:
                    expected=data_width+int(schema.has_epoch(pr))
                    if len(c.ports.get('q',[]))!=expected or len(c.ports.get('d',[]))!=expected:
                        self.fail(path+f': whole live payload/epoch bus must survive (expected {expected})')
        if self.table.get('count_aligned'):self._check_origins(rows,ports)
        for pn,p in self.parts.items():
            info=self.collector['types'][p['type']]
            if not info['mask']['active']:continue
            sources=[]
            for src in info['local_sources']:
                path=ident(pn)+'.u_cland_'+src['name']
                sources.append(dict(node=src.get('node') or f"rst_n_t{src['tap']}",ready=self.output(path,'ready'),fault=self.output(path,'fault')))
            for child in info['children']:
                edges=[e for e in self.collector['edges'] if e['dst']==pn and e['dst_index']==child['index']]
                if len(edges)!=1:raise ValueError('landing verify: exact collector child edge absent/ambiguous')
                edge=edges[0]
                if bool(edge['seam'])!=bool(child['seam']):raise ValueError('landing verify: collector seam mismatch')
                cn=edge['src'];root=self.root_collect[cn];r=self.output(root,'ready_o');f=self.output(root,'fault_o')
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
        actual={c.path for c in self.F.cells if c.module in ('ot_dp_clk_landing','ot_dp_landing_collect','ot_dp_clk_landing_ca',
                                                             'ot_dp_landing_origin','ot_dp_landing_root','ot_dp_landing_relay',
                                                             'ot_dp_clk_landing_cas','ot_dp_landing_origin_s')}
        for x in sorted(actual-self.expected):self.fail('unexpected/unpriced infrastructure '+x)
        for x in sorted(self.expected-actual):self.fail('missing infrastructure instance '+x)

    def start_net(self,pn):
        """a landed partition's count start: its origin's start, or (intra-region relay, DIE-KV-3/CAORIGIN) its rx
        relay flop's q"""
        parts=self.table['count_aligned'].get('parts') or {}
        if parts.get(pn,{}).get('role')=='relay':return self.output(ident(pn)+'.u_cland_rstart_rx','q')
        if self._strap_root(pn):return self.output(ident(pn)+'.u_cland_root','start')
        return self.output(self._origin_path(pn),'start')

    def _origin_path(self,pn):
        """Select the sampler by the declared static tie; older single-sampler source stays readable."""
        ca=self.table.get('count_aligned') or {}
        if ca.get('strap_form'):
            self._strap_root(pn)
            st=self._strap['types'].get(self.parts[pn]['type'],{}).get('origin',{})
            buses=st.get('tree_buses') or []
            prefix=ident(pn)+'.u_cland_origin_t'
            if len(buses)>1 and any(c.path.startswith(prefix) for c in self.F.cells):
                i=min(int(self._strap['instances'][pn]['values'].get('strap_ca_tsel',0)),len(buses)-1)
                return prefix+str(i)
        return ident(pn)+'.u_cland_origin'

    def fstart_net(self,pn,bus):
        """the start a sender forwards on cland_fstart_out_<bus> (receiver ring t_rst_n, child origin p_start).  Strap
        form (DIE-HEAD-10), every origin but a relay rx: the pin's own face flop u_cland_fstart_<bus>
        (ot_dp_landing_relay); checked here: region clock, d = the live origin's start_d, rst_raw_n = that origin's
        raw reset (its 0-cycle equality with start is the RTL proof fv_start_o.sh).  Otherwise the shared start."""
        ca=self.table.get('count_aligned') or {}
        if not ca.get('strap_form') or (ca.get('parts') or {}).get(pn,{}).get('role')=='relay':return self.start_net(pn)
        path=ident(pn)+'.u_cland_fstart_'+bus
        if path not in self._fstart_checked:
            self._fstart_checked.add(path)
            c=self.instance(path,'ot_dp_landing_relay')
            if c:
                src=ident(pn)+('.u_cland_root' if self._strap_root(pn) else '.u_cland_origin')
                self.clock(c,pn)
                self.equal_input(c,'d',[self.output(src,'start_d')])
                o=self.byname.get(src)
                if o is not None:self.equal_input(c,'rst_raw_n',[self.term(b) for b in o.ports.get('rst_raw_n',[])])
        return self.output(path,'q')

    def _strap_root(self,pn):
        """MESO-STRAP-1 strap form: the root copy of a type that also has child copies keeps its root counter as
        u_cland_root (strap_ca_root selects it); the strap select muxes fold on the die's constant ties."""
        ca=self.table.get('count_aligned') or {}
        if not ca.get('strap_form'):return False
        if not hasattr(self,'_strap'):
            import count_align_bind as CAB
            self._strap=CAB.strap_ties(ca,self.raw)
        si=self._strap['instances'].get(pn)
        return bool(si and si['values'].get('strap_ca_root'))

    def _raw_node(self,pn,ins,info):
        b=sorted(ins[pn])[0] if ins[pn] else None
        return (self.ring_reset_node(pn,b,info) if b else 'rst_n_t0'),('u_cland_rst_'+b if b else 'u_cland_origin_rst')

    def _check_origins(self,rows,ports):
        """Start tree: one origin per region; root = ot_dp_landing_root on a raw reset, child = ot_dp_landing_origin on
        its tree bus's raw ring reset with p_start = the tree port SENDER partition's start.  Intra-region relay (bind
        "parts", COORD 21:14 ASK 3): the origin partition's u_cland_rstart_tx (d = origin start) drives every relay
        partition's u_cland_rstart_rx (q = that partition's start), both ot_dp_landing_relay on the region clock and the
        partition's raw reset; without "parts" a region must hold exactly one landed partition."""
        ca=self.table['count_aligned'];ins=defaultdict(list);landed=set();cparts=ca.get('parts')
        for r in rows:
            pr=ports[r['port']];ins[r['dst']].append(pr['dst']['bus']);landed.update((r['src'],r['dst']))
        by_region={}
        for pn in landed:by_region.setdefault(self.region[pn],[]).append(pn)
        for tag,ps in sorted(by_region.items()):
            rg=ca['regions'].get(tag)
            if rg is None:self.fail(f'count-aligned region {tag} not in the start tree');continue
            if cparts is None:
                if len(ps)!=1:self.fail(f'count-aligned region {tag}: one landed partition required, actual {sorted(ps)}');continue
                pn=ps[0]
            else:
                pn=rg.get('origin_part')
                roles={q:(cparts.get(q) or {}).get('role') for q in ps}
                if pn not in ps or roles[pn]!='origin' or sorted(q for q,v in roles.items() if v=='origin')!=[pn] or None in roles.values():
                    self.fail(f'count-aligned region {tag}: bind roles {roles} need exactly one origin {pn}');continue
            path=self._origin_path(pn)
            info=self.collector['types'][self.parts[pn]['type']]
            if ca.get('strap_form'):
                self._strap_root(pn)
                st=self._strap['types'].get(self.parts[pn]['type'],{}).get('origin',{})
                buses=st.get('tree_buses') or []
                if path!=ident(pn)+'.u_cland_origin':
                    # Every per-input sampler remains declared infrastructure. Check its local clock and its
                    # bus-specific raw reset/START, including samplers not selected in this copy.
                    for i,b in enumerate(buses):
                        oc=self.instance(ident(pn)+'.u_cland_origin_t'+str(i),'ot_dp_landing_origin_s')
                        if not oc:continue
                        self.clock(oc,pn)
                        import clock_landings as CL
                        if b==CL.START_PIN_IN:
                            node,relay=self._raw_node(pn,ins,info)
                        else:
                            node,relay=self.ring_reset_node(pn,b,info),'u_cland_rst_'+b
                            ring=self.byname.get(ident(pn)+'.u_cland_'+ident(b))
                            if ring:self.equal_input(oc,'p_start',[self.term(x) for x in ring.ports.get('t_rst_n',[])])
                        self.check_reset(oc,pn,node,relay,port='rst_raw_n')
                if st.get('root'):   # root and child origins exist; the static root strap selects one
                    self.expected|={ident(pn)+'.u_cland_root',path}
            if rg['parent'] is None:
                c=self.instance(ident(pn)+'.u_cland_root' if self._strap_root(pn) else path,'ot_dp_landing_root')
                if c:
                    node,relay=self._raw_node(pn,ins,info)
                    self.clock(c,pn);self.check_reset(c,pn,node,relay,port='rst_raw_n')
            elif rg['tree_port'] in (ca.get('start_ports') or {}):
                # START-TREE compose slice: p_start = the dedicated start pin, driven by the parent origin's start or
                # (virtual parent region) the die-top start-stage port pst_<region>; raw reset = the local raw relay
                sp=ca['start_ports'][rg['tree_port']]
                if (sp.get('dst_part') or sp.get('capture_part'))!=pn:
                    self.fail(f'count-aligned region {tag}: start port {rg["tree_port"]} does not start {pn}');continue
                c=self.instance(path,'ot_dp_landing_origin_s' if ca.get('strap_form') else 'ot_dp_landing_origin')
                if c:
                    import clock_landings as CL
                    node,relay=self._raw_node(pn,ins,info)
                    self.clock(c,pn);self.check_reset(c,pn,node,relay,port='rst_raw_n')
                    src=sp.get('src_part') or sp.get('launch_part')
                    want=[self.start_net(src)] if src and not str(sp['src']).startswith('st:') else \
                         [('top','pst_'+CL.start_net_name(tag),0)]
                    self.equal_input(c,'p_start',want)
            else:
                tp=next((r for r in rows if r['port']==rg['tree_port']),None)
                if tp is None or tp['dst']!=pn:self.fail(f'count-aligned region {tag}: tree port {rg["tree_port"]} does not land in {pn}');continue
                b=ports[tp['port']]['dst']['bus']
                if self.region.get(tp['src'])!=rg['parent']:
                    self.fail(f'count-aligned region {tag}: tree port sender {tp["src"]} is not in parent region {rg["parent"]}');continue
                c=self.instance(path,'ot_dp_landing_origin_s' if ca.get('strap_form') else 'ot_dp_landing_origin')
                if c:
                    self.clock(c,pn);self.check_reset(c,pn,self.ring_reset_node(pn,b,info),'u_cland_rst_'+b,port='rst_raw_n')
                    self.equal_input(c,'p_start',[self.fstart_net(tp['src'],ports[tp['port']]['src']['bus'])])
            rel=[q for q in ps if q!=pn]
            if not rel:continue
            tx=self.instance(ident(pn)+'.u_cland_rstart_tx','ot_dp_landing_relay')
            if tx:
                node,relay=self._raw_node(pn,ins,info)
                self.clock(tx,pn);self.check_reset(tx,pn,node,relay,port='rst_raw_n')
                self.equal_input(tx,'d',[self.output(path,'start')])
            for q in sorted(rel):
                v=cparts[q]
                if v.get('src')!=pn or int(v.get('stages',-1))!=2:
                    self.fail(f'count-aligned relay {q}: bind relay {v} != relay({pn}, 2 stages)');continue
                rx=self.instance(ident(q)+'.u_cland_rstart_rx','ot_dp_landing_relay')
                if rx:
                    qi=self.collector['types'][self.parts[q]['type']]
                    node,relay=self._raw_node(q,ins,qi)
                    self.clock(rx,q);self.check_reset(rx,q,node,relay,port='rst_raw_n')
                    self.equal_input(rx,'d',[self.output(ident(pn)+'.u_cland_rstart_tx','q')])

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
