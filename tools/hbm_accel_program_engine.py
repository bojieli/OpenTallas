"""Default-off native Sagan generator / real DS20 callback join.

No model construction, numeric interpretation or private simulation clock.
Use the existing source generator to emit OTG-1 words; use actual DS20 pins
to execute them. The reduced source image extent is separate from POS20.
"""
import ast
import copy
import hashlib
import inspect
import textwrap


def native_generator(base, *, enable=False, moe_sha256=None):
    """Return a subclass; never patch Sagan's modules or original class.

    Preserve every source operation except the expert issue order and holding
    the shared down result until its original last addition. Existing K2's
    allocator must fit that additional live value into the existing RF.
    """
    if not enable:
        return base
    original = base.moe
    source = textwrap.dedent(inspect.getsource(original))
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != moe_sha256:
        raise ValueError('native moe source pin mismatch')
    tree = ast.parse(source)
    fn = tree.body[0]
    loops = [n for n in fn.body if isinstance(n,ast.For)
             and isinstance(n.target,ast.Name) and n.target.id=='e'
             and ast.unparse(n.iter)=='range(ke + 1)']
    if len(loops)!=2:
        raise ValueError('expected native prefix and down loops')
    for loop in loops:
        loop.iter = ast.parse('(ke, *range(ke))',mode='eval').body
    down = loops[1]
    assignments = [n for n in down.body if isinstance(n,ast.Assign)
                   and any(isinstance(t,ast.Name) and t.id=='y' for t in n.targets)]
    if len(assignments)!=1 or ast.unparse(assignments[0].value)!='ye if e == 0 else lib.add(y, ye)':
        raise ValueError('native accumulation contract differs')
    at=down.body.index(assignments[0])
    down.body[at:at+1]=ast.parse(
        'if e == ke:\n    shared_y = ye\nelif e == 0:\n    y = ye\nelse:\n    y = lib.add(y, ye)').body
    end=fn.body.index(down)+1
    fn.body[end:end]=ast.parse('y = lib.add(y, shared_y)').body
    for loop,phase in zip(loops,('prefix','down')):
        loop.body[:0]=ast.parse(f"self._ha5_mark('{phase}_begin', e)").body
        loop.body.extend(ast.parse(f"self._ha5_mark('{phase}_end', e)").body)
    fn.name='ha5_native_moe'
    ast.fix_missing_locations(tree)
    namespace={}
    exec(compile(tree,original.__code__.co_filename,'exec'),original.__globals__,namespace)
    def mark(self,phase,slot):
        if not hasattr(self,'ha5_boundaries'):
            self.ha5_boundaries=[]
        self.ha5_boundaries.append(dict(phase=phase,slot=slot,word_offset=len(self.k.ins)))
    cls=type('HA5'+base.__name__,(base,),{'moe':namespace['ha5_native_moe'],'_ha5_mark':mark})
    cls.ha5_native_source_sha256=digest
    cls.ha5_native_ast=ast.unparse(tree)
    return cls


def native_price(nsm=2,ndie=2,lanes=128):
    return dict(schema='opentallas.ha5-native-program-price.v1',
                status='ESTIMATE until native allocator and actual source-bound layer gate',
                new_rtl=False,added_memory_ports=0,added_boundary_bits_per_cycle=0,
                added_storage_macros=0,added_hardware_area_mm2=0,
                existing_rf_additional_live_bits_per_sm=lanes*32,
                existing_rf_additional_live_bits_total=lanes*32*nsm*ndie,
                existing_rf_ports='unchanged; source-native LDS, FP32 adds and STG',
                issue_order='shared then routed; final addition remains shared last',
                admission='native K2.assemble must fit existing NV; no spills or new RF allowed',
                composed_latency_us=None,routed_corridor='same physical interfaces; context gate pending',
                ss_setup_uncertainty_ps=60,ff_hold_uncertainty_ps=25,adopt=False)


def compile_native(program,native_class,kinds,link,*,enable=False,moe_sha256=None,
                   ndie=2,nsm=2):
    """Compile an already prepared source program using the existing linker.

    The caller retains build_images/finish_images and source memory ownership.
    Neither checkpoint construction nor golden/inference is performed here.
    """
    generator=native_generator(native_class,enable=enable,moe_sha256=moe_sha256)
    code=[];registers=[];boundaries=[]
    for kind in kinds:
        kernels={}
        for die in range(ndie):
            for sm in range(nsm):
                gen=generator(program,die,sm,kind)
                kernel=getattr(gen,'kernel_'+kind)()
                kernels[die,sm]=kernel.assemble()
                registers.append(dict(kind=kind,die=die,sm=sm,peak=kernel.peak,
                                      capacity=kernel.nv,words=len(kernels[die,sm])))
                for boundary in getattr(gen,'ha5_boundaries',[]):
                    boundaries.append(dict(boundary,kind=kind,die=die,sm=sm))
        code.append((kind,kernels))
    images,entries=link(code)
    for boundary in boundaries:
        boundary['linked_pc']=entries[boundary['kind']]+boundary['word_offset']
        boundary['admission']='internal entry; same held native RF/activation/router context required'
    return dict(code=code,images=images,entries=entries,registers=registers,
                boundaries=boundaries,enable=enable,adopt=False)


def program_adapter(original_engine,*,enable=False,**actual_bindings):
    """Default off keeps the caller's original engine object unchanged."""
    if not enable:
        return original_engine
    return RTLColumnEngine(enable=True,**actual_bindings)


def slot6_overlap(events):
    """Overlap of actual SM interval with actual outstanding routed fetch.

    All events carry simulator time_ps and the same retained epoch/layer/rank/
    SM/column/job/generation. This interval is NOT a token-rate gain. Sources
    are accepted request, actual SM issue/completion and first routed line
    accepted by the real SM (not fetch expert_done or staging arrival).
    """
    kinds=('routed_fetch_request','shared_sm_issue','shared_sm_complete','routed_sm_first_line')
    keys=('epoch','layer','rank','sm','column','job','generation','source_sha256')
    grouped={}
    for event in events:
        if event['kind'] not in kinds:
            continue
        key=tuple(event[k] for k in keys)
        if type(event['time_ps']) is not int or event['time_ps']<0:
            raise ValueError('actual simulator timestamp required')
        group=grouped.setdefault(key,{})
        if event['kind'] in group:
            raise ValueError('ambiguous slot6 interval; provide one source-bound phase')
        group[event['kind']]=event['time_ps']
    if not grouped:
        raise ValueError('no actual slot6 engine events')
    rows=[]
    for key,group in grouped.items():
        if set(group)!=set(kinds):
            raise ValueError('incomplete actual slot6 overlap interval')
        request,issue,complete,first=(group[k] for k in kinds)
        if complete<issue or first<request or issue<request:
            raise ValueError('invalid source event ordering')
        overlap=max(0,min(complete,first)-max(issue,request))
        rows.append(dict(zip(keys,key),shared_sm_time_ns=(complete-issue)/1000,
                         routed_wait_ns=(first-request)/1000,overlap_ns=overlap/1000,
                         system_gain_ns=None,adopt=False))
    return rows


def decode_completion(raw):
    if type(raw) is not int or not 0<=raw<1<<109:
        raise ValueError('actual CPL109 width')
    return dict(token=raw&((1<<17)-1),pos=(raw>>17)&((1<<20)-1),
                status=(raw>>37)&15,cycles=(raw>>41)&((1<<32)-1),
                generation=(raw>>73)&15,job=(raw>>77)&((1<<32)-1))


class RTLColumnEngine:
    """Engine.run(cmd,want_logits) on existing DS20 cluster callbacks.

    pins.snapshot() returns rst_sm_n,sys_fault,cycle and dies[{db_rdy,cpl_v,
    cpl_data:CPL109}]. drive_die(index,**ports) and tick() are Sagan's actual
    shared-edge owner callbacks. expand(cmd) is source D.expand. Linked entry
    PCs and the memory image extent come from the same native program record.
    read_logits, when supplied, reads actual completed source bytes; never a
    numerical callback. No completion or caller lease is synthesized/released.
    """
    def __init__(self,pins,entries,expand,*,ndie,nsm,position_extent,
                 source_sha256,enable=False,read_logits=None,swapin_positions=(),
                 sm_engine_factory=None,imw=14):
        if not enable:
            raise ValueError('HA5 actual engine requires explicit enable')
        for method in ('snapshot','drive_die','tick'):
            if not callable(getattr(pins,method,None)):
                raise ValueError('missing actual engine callback: '+method)
        if not 1<=ndie<=96 or not 1<=nsm<=16 or not 1<=position_extent<=1<<20:
            raise ValueError('actual source geometry')
        if not source_sha256 or any(type(p) is not int or not 0<=p<1<<32 for p in entries.values()):
            raise ValueError('source-bound entries required')
        self.pins,self.entries,self.expand=pins,dict(entries),expand
        self.ndie,self.nsm,self.position_extent=ndie,nsm,position_extent
        self.source_sha256,self.read_logits=source_sha256,read_logits
        self.swapin_positions=tuple(swapin_positions)
        self.launches=0;self.failed=None;self.receipts=[]
        if sm_engine_factory is None:
            from tools.gpu_sys.ds_hbm_sm_engine20_guarded import SMEngine20Guarded
            sm_engine_factory=SMEngine20Guarded
        self.sm_engine=sm_engine_factory(pins,enable=True,ndie=ndie,nsm=nsm,imw=imw)

    def _valid_position(self,kind,pos):
        if type(pos) is not int or not 0<=pos<1<<20:
            return False
        # SWAPIN UR1 is a source layer/descriptor selector, including the
        # source's special head selector. It is not a token-storage position.
        return pos in self.swapin_positions if kind=='swapin' else pos<self.position_extent

    def _snapshot(self):
        s=self.pins.snapshot()
        if s['sys_fault']:
            raise RuntimeError('actual DS20 system fault')
        if not s['rst_sm_n']:
            raise RuntimeError('actual engine reset during owned launch')
        if len(s['dies'])!=self.ndie:
            raise RuntimeError('actual die census mismatch')
        return s

    def _launch(self,kind,token,pos,job,generation):
        if type(token) is not int or not 0<=token<1<<17:
            raise ValueError('actual token17 refuses narrowing')
        if not self._valid_position(kind,pos):
            raise ValueError('source image position extent, not just POS20 width')
        start=self._snapshot()['cycle']
        expected_status=0 if kind in ('head','markov') else 2
        self.sm_engine.launch(entry_pc=self.entries[kind],token=token,position=pos,
                              job=job,generation=generation,expected_status=expected_status)
        receipt=None
        while receipt is None:
            snapshot=self._snapshot()
            # poll is the ONE CP/SM edge owner. No tick in this adapter.
            receipt=self.sm_engine.poll()
        self.launches+=1
        self.receipts.append(dict(kind=kind,token=token if expected_status==2 else receipt.token,
                                 input_token=token,
                                 completion_token=receipt.token,pos=pos,job=job,
                                 generation=generation,start_cycle=start,
                                 final_completion_cycle=self.pins.snapshot()['cycle'],
                                 cycles_by_die=receipt.cycles_by_die,
                                 elapsed_edges=receipt.elapsed_edges,
                                 source_sha256=self.source_sha256))
        return receipt.token if expected_status==0 else None

    def run(self,cmd,want_logits=False):
        if self.failed:
            raise RuntimeError('engine retains failed command: '+self.failed)
        command=copy.deepcopy(cmd)
        for name,bits in (('job',32),('generation',4)):
            if type(command.get(name)) is not int or not 0<=command[name]<1<<bits:
                raise ValueError('source-held command '+name+' required')
        if want_logits and not callable(self.read_logits):
            raise ValueError('actual completed-logit reader required')
        launches=list(self.expand(command))
        # Refuse bad entries/positions before first mutation, not mid-layer.
        for kind,token,pos in launches:
            if kind not in self.entries or type(token) is not int or not 0<=token<1<<17 or not self._valid_position(kind,pos):
                raise ValueError('source launch outside linked image geometry')
        if not launches:
            raise ValueError('empty engine command')
        result=[];logits=[]
        try:
            for kind,token,pos in launches:
                value=self._launch(kind,token,pos,command['job'],command['generation'])
                if value is not None:
                    result.append(value)
                    if want_logits and kind=='head':
                        logits.append(self.read_logits(copy.deepcopy(self.receipts[-1])))
        except Exception as exc:
            self.failed=str(exc)
            # Freeze offers on failure; actual CP/SM debts and leases remain live.
            for i in range(self.ndie):
                self.pins.drive_die(i,cmd_we=0,cmd_addr=0,cmd_wdata=0,db_v=0,
                                    db_token=0,db_pos=0,db_job=command['job'],
                                    db_generation=command['generation'],cpl_rdy=0)
            raise
        return result,logits
