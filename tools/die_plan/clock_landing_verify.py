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


def planned_ring_depths(raw,table):
    """A hardened type uses the largest DEPTH required by any of its copies (12.15a)."""
    ca=table.get('count_aligned') or {};parts={p['name']:p for p in raw['partitions']}
    ports={p['id']:p for p in raw['ports']};depths={}
    for r in table['ports']:
        cfg=ca.get('ports',{}).get(r['port'])
        if cfg is None:continue
        key=(parts[r['dst']]['type'],ports[r['port']]['dst']['bus'])
        depths[key]=max(depths.get(key,0),int(cfg['depth']))
    return depths


class Verification:
    def __init__(self,F,G,raw,table,names,live_widths=None,plan_path=None,reset_tree=None):
        self.F,self.G,self.raw,self.table,self.names=F,G,raw,table,names
        # TOK-QC-4: inactive landing types carry collector tree None, but may still host count-aligned infrastructure
        # (an intra-region start relay rx).  Their raw reset is the type's ordinary plan reset tree, the one the bind
        # emits (RT.for_type); reset_tree(tn) may be injected (tests).  No tree -> FAIL, never skip.
        self.plan_path,self._reset_tree_fn,self._plan_trees=plan_path,reset_tree,{}
        self.observer_seen=set();self.errors=[];self.byname={c.path:c for c in F.cells};self.expected=set();self.memo={};self._fstart_checked=set()
        self.anchor_receipts=[]
        if any('reset_tree_anchor' in ((t or {}).get('clock') or {}) for t in raw.get('partition_types',{}).values()):
            raw=self.raw=self._anchored(raw)
        self.parts={p['name']:p for p in raw['partitions']};self.collector=table['collector']
        self.live_widths=live_widths
        self.ring_depths=planned_ring_depths(raw,table)
        self.transport_stages={}
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

    def _anchored(self,raw):
        """RELAY-ANCHOR (as built: bind.cmd_bind runs reset_anchor.resolve_plan before the landings read the plan): the
        plan's START-chain / local-reset raw names anchored by site are re-picked onto the generated wavefront tree
        (same depth, nearest site).  The verifier re-derives the re-pick on its own copy of the plan (never reads the
        bind's receipt); an anchor that does not resolve is a verify error."""
        import copy,reset_anchor as RA,taps
        raw=copy.deepcopy(raw)
        if self._reset_tree_fn is not None:fn=self._reset_tree_fn
        else:
            import schema as S,reset_tree as RT
            self._P=S.Plan(raw,self.plan_path);fn=lambda tn:RT.for_type(self._P,tn)
        self.anchor_receipts,errs=RA.resolve_plan(raw,None,taps._root(),tree_fn=fn)
        self.errors.extend(errs)
        return raw

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

    def _regional_model(self,pn):
        """Exact opt-in TT_C component contract; default source checks are unchanged."""
        cache=self.__dict__.setdefault('_regional_models',{})
        if pn in cache:return cache[pn]
        tn=self.parts[pn]['type'];cfg=getattr(self,'raw',{}).get('partition_types',{}).get(tn,{}).get('clock',{}).get('landing_regional_origin')
        if not cfg or not cfg.get('enabled',False):cache[pn]=None;return None
        import hashlib,json
        from pathlib import Path
        if tn!='tt_ctlm':raise ValueError('regional source verifier is scoped to existing tt_ctlm')
        path=Path(cfg['model_file'])
        if not path.is_absolute():raise ValueError('regional source model needs exact absolute snapshot path')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=cfg['model_sha256']:raise ValueError('regional source model content changed')
        model=json.loads(data)
        if (model.get('type'),model.get('origin_padw'),model.get('parent_source'),model.get('raw_depth'))!=('tt_ctlm',1,'rst_rl_85',3):
            raise ValueError('regional source model mechanism changed')
        regions=model['qualified_regions']
        mapping={n:r['region'] for r in regions for n in r['receivers']}
        if [r['region'] for r in regions]!=[0,1,2,3] or len(mapping)!=37 or sum(len(r['receivers']) for r in regions)!=37:
            raise ValueError('regional source model needs four regions and37 unique receivers')
        if model['price']['added_state_ff']!=13 or model['price']['added_mission_cycles'] or model['price']['added_boot_cycles']:
            raise ValueError('regional source model price changed')
        model=dict(model,receiver_regions=mapping);cache[pn]=model;return model

    def _regional_origin_module(self,pn):
        return 'ot_dp_landing_origin_s_regional' if self._regional_model(pn) else ('ot_dp_landing_origin_s' if self.table['count_aligned'].get('strap_form') else 'ot_dp_landing_origin')

    def _check_regional_origin(self,pn):
        model=self._regional_model(pn)
        if not model:return
        checked=self.__dict__.setdefault('_regional_checked',set())
        if pn in checked:return
        checked.add(pn)
        if not self.table['count_aligned'].get('strap_form') or self._strap_root(pn):
            self.fail(pn+': regional origin requires selected non-root strap START form');return
        prefix=ident(pn)+'.';path=prefix+'u_cland_origin';origin=self.instance(path,'ot_dp_landing_origin_s_regional')
        if not origin:return
        params=getattr(origin,'params',{})
        def parameter(key,default):
            value=params.get(key,default)
            if isinstance(value,int):return value
            if re.fullmatch(r'-?[0-9]+',str(value)):return int(value)
            match=re.fullmatch(r"([0-9]+)'b([01]+)",str(value))
            if match and len(match[2])==int(match[1]):return int(match[2],2)
            return None
        if [parameter(k,{'ENABLE':0,'PADW':1,'REGIONS':4}[k]) for k in ('ENABLE','PADW','REGIONS')]!=[1,1,4]:self.fail(path+': actual regional parameters differ')
        self.clock(origin,pn)
        if any(len(origin.ports.get(p,[]))!=4 for p in ('start_r','start_d_r','rst_region_raw_n')):
            self.fail(path+': actual regional vector width differs')
        self.equal_input(origin,'rst_raw_n',[self.output(prefix+'u_rrl_87','q')])
        raws=[]
        for r in range(4):
            rp=prefix+f'g_tt_raw_regions.g_region[{r}].u_raw_copy';raw=self.instance(rp,'ot_dp_rrelay')
            raws.append(self.output(rp,'q'))
            if raw:
                self.clock(raw,pn);self.equal_input(raw,'d',[self.output(prefix+'u_rrl_85','q')])
        self.equal_input(origin,'rst_region_raw_n',raws)
        expected_start=defaultdict(set);expected_d=defaultdict(set);expected_raw=defaultdict(set)
        for full,r in model['receiver_regions'].items():
            if not full.startswith('u_bound.u_cland_'):raise ValueError('regional receiver outside actual landing contract')
            name=full[len('u_bound.'):];rp=prefix+name;forward=name.startswith('u_cland_fstart_')
            c=self.instance(rp,'ot_dp_landing_relay' if forward else 'ot_dp_clk_landing_cas')
            if c:
                self.clock(c,pn)
                if forward:
                    self.equal_input(c,'d',[self.output(path,'start_d_r',r)]);self.equal_input(c,'rst_raw_n',[raws[r]])
                else:self.equal_input(c,'rst_n',[self.output(path,'start_r',r)])
            if forward:expected_d[r].add((rp,'d',0));expected_raw[r].add((rp,'rst_raw_n',0))
            else:expected_start[r].add((rp,'rst_n',0))
        def consumers(port,bit):
            bits=origin.ports.get(port,[])
            if bit>=len(bits):self.fail(path+': missing regional output '+port);return set()
            return {(self.F.cells[i].path,p,b) for i,p,b in self.G.loads.get(bits[bit],[])}
        for r in range(4):
            if consumers('start_r',r)!=expected_start[r]:self.fail(path+f': unpriced regional START[{r}] consumers')
            if consumers('start_d_r',r)!=expected_d[r]:self.fail(path+f': unpriced regional D[{r}] consumers')
            rp=prefix+f'g_tt_raw_regions.g_region[{r}].u_raw_copy';c=self.byname.get(rp)
            if c and len(c.ports.get('q',[]))==1:
                actual={(self.F.cells[i].path,p,b) for i,p,b in self.G.loads.get(c.ports['q'][0],[])}
                if actual!=expected_raw[r]|{(path,'rst_region_raw_n',r)}:self.fail(rp+': unpriced regional raw consumers')

    def equal_input(self,c,port,want):
        self.checks+=1
        got=[self.term(b) for b in c.ports.get(port,[])]
        if got!=want:self.fail(f'{c.path}.{port}: actual {got!r} != expected {want!r}')

    def clock(self,c,part,port='clk'):
        self.equal_input(c,port,[('top','clk_region_'+ident(self.region[part]),0)])

    def _tclock(self,pn):
        return (((getattr(self,'raw',None) or {}).get('partition_types',{}).get(self.parts[pn]['type']) or {}).get('clock') or {})

    def local_resets(self,pn):
        """QC-VERIFY-GAPS (DIE-HEAD-38 R1 as built by clock_landings._local_resets): plan clock.landing_local_resets of
        pn's type -> {consumer instance: (copy instance u_cland_lrst_<name>, raw tree node)}.  Each copy is one kept
        ot_dp_rrelay whose D is the raw node; it releases on the same edge as the consumer's planned reset only when
        depth(raw) + 1 == depth(planned node) -- checked at every consumer, never assumed."""
        cache=self.__dict__.setdefault('_lrst',{});tn=self.parts[pn]['type']
        if tn not in cache:
            m={}
            for r in self._tclock(pn).get('landing_local_resets') or []:
                for c in r.get('consumers') or []:m[c]=('u_cland_lrst_'+ident(str(r.get('name'))),r.get('raw'))
            cache[tn]=m
        return cache[tn]

    @staticmethod
    def tree_depths(tree):
        rows={r['q']:r for r in tree['relays']};memo={'rst_root_n':0}
        def depth(n,seen=()):
            if n in memo:return memo[n]
            if n in seen or n not in rows:return None
            d=depth(rows[n]['d'],seen+(n,));memo[n]=None if d is None else d+1;return memo[n]
        return {q:depth(q) for q in rows}|{'rst_root_n':0}

    def release(self,net):
        """(root term, plain relay hops) of a raw reset net: ot_dp_rrelay/_nl q +1, ot_dp_lk q and $buf 0; any other
        driver is the root.  Two resets of one partition with equal release() deassert on the same edge."""
        d=0;seen=set()
        while True:
            if net in seen:return (('loop',),d)
            seen.add(net);ds=self.G.drv.get(net,[])
            if net in self.G.top_in or len(ds)!=1:return (self.term(net),d)
            ci,port,_=ds[0];c=self.F.cells[ci]
            if c.kind=='glue' and port=='Y' and c.ytype in ('$buf','$pos') and len(c.ports.get('A',[]))==1:net=c.ports['A'][0];continue
            if c.module in ('ot_dp_rrelay','ot_dp_rrelay_nl') and port=='q':d+=1
            elif c.module!='ot_dp_lk' or port!='q':return (self.term(net),d)
            ib=c.ports.get('d',[])
            if len(ib)!=1:return (('bad',c.path),d)
            net=ib[0]

    def _local_copy(self,c,part,port,lr):
        """The declared local reset copy lr=(instance, raw node) drives c.port: -> the copy cell, or None (failed)."""
        bits=c.ports.get(port,[]);prefix=ident(part)+'.'
        ds=self.G.drv.get(bits[0],[]) if len(bits)==1 else []
        up=self.F.cells[ds[0][0]] if len(ds)==1 else None
        if up is None or up.path!=prefix+lr[0] or up.module!='ot_dp_rrelay' or ds[0][1]!='q':
            self.fail(f'{c.path}.{port}: declared local reset copy {prefix+lr[0]} is not its driver');return None
        if [self.term(b) for b in up.ports.get('clk',[])]!=[self.term(b) for b in c.ports.get('clk',[])]:
            self.fail(up.path+': local reset copy clock differs from its consumer clock');return None
        return up

    def check_reset(self,c,part,node,extra=None,port='rst_n',wave=False):
        bits=c.ports.get(port,[])
        if len(bits)!=1:self.fail(c.path+': exact one-bit raw reset required');return
        lr=self.local_resets(part).get(c.path[len(ident(part))+1:]) if c.path.startswith(ident(part)+'.') else None
        tree=self.reset_tree(self.parts[part]['type'],wave=wave or bool(lr))
        if tree is None:
            self.fail(c.path+': no planned reset tree for type '+self.parts[part]['type']+' (inactive landing type)');return
        rows={r['q']:r for r in tree['relays']};prefix=ident(part)+'.'
        # DIE-S81-32/BIND: since reset_tree 68e405472 (DIE-S81-27) a non-START wavefront out relay drives only its
        # port rst_o_<k>; its tap net rst_n_t<j> is driven by the same-d, same-depth copy <name>_t (same release
        # cycle).  The copy is a legitimate hop only at an out-relay tap; every other hop keeps the exact planned names.
        import reset_tree as RT
        outq=set(RT.out_relays(tree)) if tree.get('outs') else set()
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
            if n in outq:allowed.add(prefix+row['name']+'_t')
            if up.path not in allowed or up.module not in('ot_dp_rrelay','ot_dp_rrelay_nl') or port!='q':return False
            ib=up.ports.get('d',[])
            if len(ib)==1 and tree.get('relay_lockup')=='latch':
                # RLK-1108 latch form: one hop lockup latch (0 cycles) between this relay and its planned parent
                lds=self.G.drv.get(ib[0],[])
                if len(lds)==1:
                    lc=self.F.cells[lds[0][0]]
                    if lc.module=='ot_dp_lk' and lds[0][1]=='q' and lc.path==prefix+RT.lockup_latch_names(row['name'])[0]:
                        ib=lc.ports.get('d',[])
            return len(ib)==1 and walk(ib[0],row['d'],seen|{n})
        if lr:
            # declared same-cycle local copy: consumer <- u_cland_lrst_<name> <- the planned raw node, one level up
            up=self._local_copy(c,part,port,lr)
            if up is None:return
            dep=self.tree_depths(tree)
            if dep.get(lr[1]) is None or dep.get(node) is None or dep[lr[1]]+1!=dep[node]:
                self.fail(f'{c.path}: local reset copy {lr[0]} raw {lr[1]} depth {dep.get(lr[1])} + 1 != planned {node} depth {dep.get(node)}');return
            ib=up.ports.get('d',[])
            if len(ib)!=1 or not walk(ib[0],lr[1],set()):
                self.fail(up.path+': local reset copy D is not the exact planned raw node '+str(lr[1]))
            return
        if not walk(bits[0],node,set()):
            if not wave and self._wave_ok(c,part,node,extra,port):return
            self.fail(c.path+': raw reset is not the exact original local reset-parent/depth contract at '+node)

    def _wave_ok(self,c,part,node,extra,port):
        """QC-VERIFY-GAPS: the type's relays are emitted from the plan wavefront tree the bind builds (RT.for_type); a
        landing_contract.collector_tree copy whose relay names went stale after a tap re-bin (QC cbf_q01: rst_n_t62
        <- rst_rl_487 as built, the copy names another parent) is not the as-built reference.  The same exact
        parent/depth walk then holds on the bound wavefront tree."""
        saved=self.errors;self.errors=[]
        try:
            self.check_reset(c,part,node,extra,port=port,wave=True);return not self.errors
        finally:self.errors=saved

    def reset_tree(self,tn,wave=False):
        """The reset tree a landing stage of type tn walks: the collector tree (active types), else the type's plan reset
        tree as the bind emits it (RT.for_type on the plan); None (-> FAIL at the caller) if neither exists.
        wave=True: always the plan wavefront tree (the raw_reset / local-reset names rst_rl_<n> of the START chains
        and clock.landing_local_resets are its relay nets)."""
        import landing_collector as LC
        tree=None if wave else LC.effective_tree(self.raw['partition_types'].get(tn),self.collector['types'][tn]['tree'])  # S81-OTHERFAIL-1
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
            # CA-MIXED-1: a mixed table's ring landings are checked as rings
            from clock_landings import ca_port
            if ca and not ca_port(ca,r['port']):ca=None
            c=self.instance(path,('ot_dp_clk_landing_cas' if ca.get('strap_form') else 'ot_dp_clk_landing_ca') if ca else 'ot_dp_clk_landing')
            if c:
                self.clock(c,r['dst']);self.clock(c,r['src'],'fclk')
                info=self.collector['types'][self.parts[r['dst']]['type']]
                # CLAND-SIDECAR-LOCAL-1 (GEN-CLASS-1 11-12, DIE-S81-88 13:18: StopIteration on S81 r12ng t52 dn_s_4N_L0x2_i):
                # a landing whose bus has no collector.types[].local_sources row is a stale sidecar, refused by name
                local=next((x for x in info.get('local_sources',[]) if x['name']==bus),None)
                if local is None:
                    self.fail(f"{path}: CLAND_SIDECAR_LOCAL_SOURCE_MISSING: port {r['port']} lands on bus {bus} of type "
                              f"{self.parts[r['dst']]['type']}, whose sidecar collector.types[].local_sources has no {bus} row "
                              f"(has {[x['name'] for x in info.get('local_sources',[])]}): regenerate the clock-landing sidecar "
                              f"for this plan")
                if ca:
                    cfg=ca['ports'][r['port']]
                    params=getattr(c,'params',{})
                    depth=self.ring_depths[(self.parts[r['dst']]['type'],bus)]
                    if int(params.get('DEPTH',4))!=depth:
                        self.fail(path+': actual count-aligned DEPTH differs from the bound contract')
                    if ca.get('strap_form'):
                        kb=c.ports.get('strap_k',[])
                        kw=depth.bit_length()-1+4
                        expected=list(reversed(format(self.strap_k(r,pr,cfg) & ((1<<kw)-1),f'0{kw}b')))
                        if kb!=expected:self.fail(path+': actual strap_k differs from the bound count')
                    elif (int(params.get('K',2)) & 0xffffffff)!=(int(cfg['K']) & 0xffffffff):
                        self.fail(path+': actual count-aligned K differs from the bound contract')
                    # K is a modular counter offset, not transport cycles. The
                    # fixed latency includes the proven sender/receiver origins.
                    self.transport_stages[path]=int(cfg['sched_lat'])
                    # count-aligned (MESO-INTEG-1): read count from the receiver's origin, write count from the
                    # sender's origin forwarded beside the bus; the origins themselves are checked below
                    self.equal_input(c,'rst_n',[self.reader_start(r['dst'],bus,c)])
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
        if self.table.get('count_aligned'):
            from clock_landings import ca_port
            self._check_origins([r for r in rows if ca_port(self.table['count_aligned'],r['port'])],ports)
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
                else:
                    # DIE-S81-29: a same-region status pin pair is captured by its own face flops (clk, d = the child's
                    # registered root output); the reduction reads their q
                    faced=[]
                    for kind,want in (('ready',r),('fault',f)):
                        path=ident(pn)+f".u_cland_face_{kind}_{child['index']}";c=self.instance(path,'ot_dp_landing_face')
                        if c:self.clock(c,pn);self.equal_input(c,'d',[want])
                        faced.append(self.output(path,'q'))
                    r,f=faced
                sources.append(dict(node=child['node'],ready=r,fault=f))
            import landing_collector as LC
            tree=LC.effective_tree(self.raw['partition_types'].get(p['type']),info['tree'])  # S81-OTHERFAIL-1: one tree
            root=info['collector_root_node'];adj=defaultdict(list)
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
        actual={c.path for c in self.F.cells if c.module in ('ot_dp_clk_landing','ot_dp_landing_collect','ot_dp_clk_landing_ca','ot_dp_landing_face',
                                                             'ot_dp_landing_origin','ot_dp_landing_root','ot_dp_landing_relay',
                                                             'ot_dp_clk_landing_cas','ot_dp_landing_origin_s','ot_dp_landing_origin_s_regional',
                                                             'ot_dp_landing_relay_rep')}
        actual|={c.path for c in self.F.cells if c.module=='ot_dp_rrelay' and re.fullmatch(r'.*\.g_tt_raw_regions\.g_region\[[0-9]+\]\.u_raw_copy',c.path)}
        for x in sorted(actual-self.expected):self.fail('unexpected/unpriced infrastructure '+x)
        for x in sorted(self.expected-actual):self.fail('missing infrastructure instance '+x)

    def strap_k(self,r,pr,cfg):
        """The strap K a strap-form ring of crossing r must carry: the bind K re-referenced to the as-built START edges
        (count_align_bind.strap_ties contract, W1/R proof): the reader count starts R edges later (dst type
        clock.landing_reader_start depth: -R), the sender's writer START W edges later (src type
        clock.landing_writer_start on that output bus: +W), a registered ring writer (landing_ring_wreg: +depth) and an
        output q register outside the ring (landing_output_qreg: -1)."""
        import clock_landings as CL,count_align_bind as CAB
        dt=self.parts[r['dst']]['type'];st=self.parts[pr['src']['part']]['type'];bus=pr['dst']['bus']
        wreg=CL.ring_write_reg(self.raw,dt,bus)
        return (int(cfg['K'])-CAB.reader_start_depth(self.raw,dt)+CAB.writer_start_depth(self.raw,st,pr['src']['bus'])
                +(wreg['depth'] if wreg else 0)-int(CL.output_qreg(self.raw,dt,bus)))

    def _stages(self,pn,key,bus,physical):
        cfg=self._tclock(pn).get(key) or {};br=(cfg.get('branches') or {}).get(bus)
        stages=br.get('stages',[]) if isinstance(br,dict) else []
        if len(stages)!=physical:
            self.fail(f'{pn}: {key}.{bus} plans {len(stages)} physical stages, as-built rule needs {physical}');return None
        return stages

    def _reach_reader(self,pn):
        """CLAND-RING-LOCALITY: the type takes the reach-default reader START (strap form only, the generator's rule)"""
        import clock_landings as CL
        return bool((self.table.get('count_aligned') or {}).get('strap_form')) and bool(
            CL.reader_start_reach(self.raw,self.parts[pn]['type']))

    def reader_start(self,pn,bus,ring):
        """The count start a count-aligned ring reader resets on.  Default: the partition's start.  With the type's
        clock.landing_reader_start (clock_landings._reader_start_rtl): R kept ot_dp_landing_relay stages
        u_cland_reader_start_<bus>_<i> (region clock, d = previous stage / start, rst_raw_n = the stage's planned raw
        tree node), the ring rst_n = the last stage's q; RSTREP: the last stage is ot_dp_landing_relay_rep and the
        ring's rst_xn = its qx copies."""
        start=self.start_net(pn,'u_cland_'+bus)
        rep=len(ring.ports.get('rst_xn',[]))
        cfg=self._tclock(pn).get('landing_reader_start')
        reach=None
        if cfg is None:
            if self._reach_reader(pn):
                # CLAND-RING-LOCALITY reach default (clock_landings.reader_start_reach, the rule the generator and
                # strap K read): ONE stage on the ring's own registered reset (tap node, or its u_cland_rst_<bus> copy)
                info=self.collector['types'][self.parts[pn]['type']]
                reach=(self.ring_reset_node(pn,bus,info),'u_cland_rst_'+bus)
                cfg=dict(depth=1)
            else:
                if rep:self.fail(ring.path+': unpriced ring reset copies rst_xn without a reader START chain')
                return start
        stages=[dict()] if reach else self._stages(pn,'landing_reader_start',bus,int(cfg.get('depth',-1)))
        if not stages:return ('missing',ident(pn)+'.u_cland_reader_start_'+ident(bus))
        prev=start;path=None
        for i,st in enumerate(stages):
            path=ident(pn)+f'.u_cland_reader_start_{ident(bus)}_{i}'
            c=self.instance(path,'ot_dp_landing_relay_rep' if rep and i==len(stages)-1 else 'ot_dp_landing_relay')
            if c:
                self.clock(c,pn);self.equal_input(c,'d',[prev])
                if reach:self.check_reset(c,pn,reach[0],reach[1],port='rst_raw_n',wave=True)
                else:self.check_reset(c,pn,st.get('raw_reset'),port='rst_raw_n',wave=True)
            prev=self.output(path,'q')
        if rep:self.equal_input(ring,'rst_xn',[self.output(path,'qx',k) for k in range(rep)])
        if (self.table.get('count_aligned') or {}).get('strap_form'):
            import clock_landings as CL
            pr=getattr(ring,'params',None) or {}
            need=CL.reader_reset_copies(self.raw,self.parts[pn]['type'],bus,int(pr.get('W',0) or len(ring.ports.get('q',[]))),int(pr.get('READ_CHUNK',0) or 0))
            if need and rep<need:
                self.fail(ring.path+f': reader START copies {rep} < {need} (CLAND-RING-LOCALITY one copy per read chunk)')
        return prev

    def writer_start(self,pn,bus,start_d):
        """The D of a sender's FSTART face flop u_cland_fstart_<bus>.  Default: start_d.  With the type's
        clock.landing_writer_start naming bus (clock_landings._writer_start_rtl): depth - reuse kept ot_dp_landing_relay
        stages u_cland_writer_start_<bus>_<i> (region clock, d = previous stage, first d = start_d, or the relay
        origin's start under reuse_relay_origin, rst_raw_n = the planned raw tree node); the face flop d = the last q."""
        cfg=self._tclock(pn).get('landing_writer_start')
        if not cfg or bus not in (cfg.get('branches') or {}):return start_d
        reuse=cfg.get('reuse_relay_origin',False)
        if reuse and (self.table['count_aligned'].get('parts') or {}).get(pn,{}).get('role')!='relay':
            self.fail(f'{pn}: writer START reuse_relay_origin on a partition without a relay origin');return [('missing',pn,bus)]
        stages=self._stages(pn,'landing_writer_start',bus,int(cfg.get('depth',-1))-int(bool(reuse)))
        if stages is None:return [('missing',pn,bus)]
        prev=[self.start_net(pn)] if reuse else start_d
        for i,st in enumerate(stages):
            path=ident(pn)+f'.u_cland_writer_start_{ident(bus)}_{i}'
            c=self.instance(path,'ot_dp_landing_relay')
            if c:
                self.clock(c,pn);self.equal_input(c,'d',prev);self.check_reset(c,pn,st.get('raw_reset'),port='rst_raw_n',wave=True)
            prev=[self.output(path,'q')]
        return prev

    def face_raw(self,c,pn,src):
        """FSTART face flop raw reset: the start's own raw reset (src.rst_raw_n), or the type's declared local reset
        copy (clock.landing_local_resets consumer): that copy, D = its planned raw tree node, releasing on the same
        edge (equal root and relay depth) as the start's raw reset."""
        default=[self.term(b) for b in src.ports.get('rst_raw_n',[])] if src is not None else [('missing',pn,'rst_raw_n')]
        prefix=ident(pn)+'.';lr=self.local_resets(pn).get(c.path[len(prefix):])
        own=self.local_resets(pn).get(src.path[len(prefix):]) if src is not None else None
        if lr is None and own is None:
            self.equal_input(c,'rst_raw_n',default);return
        self.checks+=1
        bits=c.ports.get('rst_raw_n',[]);sb=src.ports.get('rst_raw_n',[]) if src is not None else []
        if len(bits)!=1 or len(sb)!=1:self.fail(c.path+': exact one-bit raw reset required');return
        if lr is not None:
            up=self._local_copy(c,pn,'rst_raw_n',lr)
            if up is None:return
            # the copy's D is exactly the planned raw tree node (same walk as every planned reset)
            self.check_reset(up,pn,lr[1],port='d',wave=True)
        elif self.term(bits[0])[1:2]!=() and str(self.term(bits[0])[1]).startswith(prefix+'u_cland_lrst_'):
            self.fail(c.path+': undeclared local reset copy on rst_raw_n');return
        if self.release(bits[0])!=self.release(sb[0]):
            self.fail(f'{c.path}.rst_raw_n: release {self.release(bits[0])!r} != start raw release {self.release(sb[0])!r}')

    def start_net(self,pn,receiver=None):
        """a landed partition's count start: its origin's start, or (intra-region relay, DIE-KV-3/CAORIGIN) its rx
        relay flop's q"""
        model=self._regional_model(pn)
        if model:
            self._check_regional_origin(pn)
            r=model['receiver_regions'].get('u_bound.'+receiver) if receiver else 0
            if r is None:self.fail(pn+': reader missing from regional model');r=0
            return self.output(self._origin_path(pn),'start_r',r)
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
        model=self._regional_model(pn)
        if model:
            self._check_regional_origin(pn)
            return self.output(ident(pn)+'.u_cland_fstart_'+bus,'q')
        relay=(ca.get('parts') or {}).get(pn,{}).get('role')=='relay'
        # landing_relay_start_copy (clock_landings._origin_rtl): a strap-form relay partition keeps its own FSTART face
        # flops: d-side = the rx flop's D (cland_rstart_in), raw reset = the rx flop's raw reset
        relay_copy=relay and bool(ca.get('strap_form')) and \
            (self.raw['partition_types'].get(self.parts[pn]['type']) or {}).get('landing_relay_start_copy') is True
        if not ca.get('strap_form') or (relay and not relay_copy):return self.start_net(pn)
        path=ident(pn)+'.u_cland_fstart_'+bus
        if path not in self._fstart_checked:
            self._fstart_checked.add(path)
            c=self.instance(path,'ot_dp_landing_relay')
            if c:
                if relay_copy:
                    o=self.byname.get(ident(pn)+'.u_cland_rstart_rx')
                    start_d=[self.term(b) for b in o.ports.get('d',[])] if o is not None else [self.output(ident(pn)+'.u_cland_rstart_rx','d')]
                else:
                    src=ident(pn)+'.u_cland_root' if self._strap_root(pn) else self._origin_path(pn)
                    start_d=[self.output(src,'start_d')];o=self.byname.get(src)
                self.clock(c,pn)
                self.equal_input(c,'d',self.writer_start(pn,bus,start_d))
                if o is not None:self.face_raw(c,pn,o)
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
            self._check_regional_origin(pn)
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
                c=self.instance(path,self._regional_origin_module(pn))
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
                c=self.instance(path,self._regional_origin_module(pn))
                if c:
                    self.clock(c,pn);self.check_reset(c,pn,self.ring_reset_node(pn,b,info),'u_cland_rst_'+b,port='rst_raw_n')
                    self.equal_input(c,'p_start',[self.fstart_net(tp['src'],ports[tp['port']]['src']['bus'])])
            rel=[q for q in ps if q!=pn]
            if not rel:continue
            tx=self.instance(ident(pn)+'.u_cland_rstart_tx','ot_dp_landing_relay')
            if tx:
                self.clock(tx,pn)
                if ca.get('strap_form'):
                    # strap origin (clock_landings._origin_rtl): the tx flop shares the origin's own raw reset (the
                    # selected tree bus / START pin raw, or the root's), the origin's own raw is checked above
                    self.face_raw(tx,pn,self.byname.get(ident(pn)+'.u_cland_root' if self._strap_root(pn) else path))
                else:
                    node,relay=self._raw_node(pn,ins,info)
                    self.check_reset(tx,pn,node,relay,port='rst_raw_n')
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
