"""Default-off original870 MATRIX lowering and existing sm_q pin sequencer.

No arithmetic, RTL creation, private clock, provider allocator or Python
payload fallback. The enclosing native owner supplies actual captured sources,
finite hardware leases, RF capture and W4/W6/reverse completion services.
"""
from dataclasses import dataclass, asdict
from collections import Counter
from tools.gpu_sys import canonical_qwen_service_calendar as C

SOURCES=('rtl/gpu/ot_gpu_sm_q.sv','rtl/gpu/ot_gpu_issue.sv',
         'rtl/gpu/ot_gpu_tc_col.sv','rtl/gpu/ot_gpu_tree.sv',
         'rtl/gpu/ot_gpu_stack.sv','rtl/gpu/ot_gpu_xstore.sv','rtl/gpu/ot_gpu_bulk_copy.sv')


@dataclass(frozen=True)
class MatrixTile:
    program_sha256:str
    source_PC:int
    weight_key:str
    weight_rank:int
    input_version:str
    output_version:str
    checkpoint_components:tuple
    row_start:int
    rows:int
    K:int
    split:int
    chunk:int
    groups:int
    weight_descriptor_sha256:str
    native_recipe_sha256:str

    @property
    def line_count(self):return self.rows*self.K//128
    @property
    def fragments(self):return self.K//128

    def line(self,index):
        """One existing bulk-copy LINE address; not a physical HBM address."""
        C.need(type(index) is int and 0<=index<self.line_count,'line aperture')
        # Existing issue order: rowblock, group, chunk-k, slot. Tile128
        # is a multiple of IL8, so no padded weight lines are transmitted.
        line_address=index
        block,index=divmod(index,self.groups*self.chunk*8)
        group,index=divmod(index,self.chunk*8)
        step,slot=divmod(index,8)
        row=self.row_start+block*8+slot
        ks=tuple((group*128+lane)*self.chunk+step for lane in range(128))
        return dict(line_address=line_address,source_row=row,source_K_indices=ks,
                    source_code_byte_offsets=tuple(row*self.K+k for k in ks),
                    dtype='I8',bytes=128,weight_key=self.weight_key,
                    source_PC=self.source_PC,rank=self.weight_rank)

    def x_fragment(self,index):
        C.need(type(index) is int and 0<=index<self.fragments,'fragment aperture')
        group,step=divmod(index,self.chunk)
        ks=tuple((group*128+lane)*self.chunk+step for lane in range(128))
        return dict(fragment=index,input_version=self.input_version,
                    source_K_indices=ks,source_rounding='original bf16 recipe',
                    dtype='BF16',columns=16,bytes=4096,
                    layout='column-major; identical128-leaf source vector in each of16columns')

    def record(self):return asdict(self)


def lower_matrix(native,source_PC,*,enabled=False):
    C.need(enabled,'MATRIX engine lowering default off')
    C.need(C.sha(C.canonical(native))==C.PROGRAM_SHA,'exact canonical1737 identity')
    C.need(type(source_PC) is int and 0<=source_PC<1737,'source PC aperture')
    return _lower_verified(native,source_PC)


def _lower_verified(native,source_PC):
    # Only caller lower_matrix or locally verified compose_inventory.
    op=native['operations'][source_PC]
    C.need(op['opcode']=='MATRIX','only actual MATRIX source operation')
    C.need(len(op['reads'])==len(op['writes'])==1,'exact MATRIX input/output versions')
    d=native['source_program']['weight_descriptors'][op['attributes']['weight']]
    K,S,R=d['K'],d['split'],d['rows']
    C.need(S>=128 and S&(S-1)==0 and S%128==0 and K%S==0,'unproved split64 padding or irregular split refused')
    C.need(S//128<=32 and R%8==0 and 0<K//S<65536,'existing issue/stack aperture')
    C.need((K//128)*8<=1024,'finite existing xstore macro word aperture')
    recipes={key:native['microcode'][key] for key in ('bf16','convert','mul','add')}
    return tuple(MatrixTile(C.PROGRAM_SHA,source_PC,d['key'],d['die'],
        op['reads'][0],op['writes'][0],tuple(d['checkpoint_sources']),r,min(128,R-r),K,S,K//S,S//128,
        C.sha(C.canonical(d)),C.sha(C.canonical(recipes))) for r in range(0,R,128))


def price_tiles(tiles,source_primitive_calls):
    """Exact port counts and local schedule floors; no invented owner delays."""
    n=len(tiles);lines=sum(t.line_count for t in tiles)
    # SUB4*LS32, IL8, NC16.16 identical columns are paid, not useful batch16.
    xbeats=sum(t.fragments*16 for t in tiles)
    issue=sum(t.rows*t.groups*t.chunk for t in tiles)
    scatter_sectors=sum(t.rows*sum(len({k//32 for k in t.x_fragment(f)['source_K_indices']})
                        for f in range(t.fragments)) for t in tiles)
    return dict(schema='QWEN_MATRIX_EXISTING_ENGINE_LOWERING_R1',source_tiles=n,
        whole_loop_host_launches_if_enrolled=n,baseline_primitive_host_calls=source_primitive_calls,
        native_arithmetic_removed=0,source_weight_bytes=sum(t.rows*t.K for t in tiles),
        bulk_copy_line_bytes=128,weight_line_requests=lines,
        useful_source_MACs_per_issue=128,physical_MACs_per_issue=2048,
        weight_ingress_bytes_per_edge=128,RF_result_capture_bytes_per_edge=64,
        source_unique_code_sectors32=sum(t.rows*t.K//32 for t in tiles),
        uncached_gather_code_sector_reads32=scatter_sectors,
        xstore_write_bytes_per_beat=256,xstore_write_beats=xbeats,
        engine_boundary_bits_per_issue=dict(weight=1024,activation_fragment=32768,result=512),
        issue_edges_no_stalls=issue,same_row_recurrence_II_edges=8,
        local_serial_preload_and_issue_floor_edges=xbeats+issue,
        W2_same_client_sector_II_edges=19,physical_W2_request_count=None,
        # Scatter can touch many sectors/line. No optimistic four contiguous
        # sectors/line; exact physical route and retained capture policy needed.
        existing_engine_resources=dict(xstore_macros=16,xstore_bytes=524288,
            weight_ring_bytes=131072,bulk_copy_MAX_OUT=512,ring_lines=1024,
            row_slots=8,columns=16,source_vectors=1),
        required_output_capture=dict(rows_per_tile=128,bits_per_row=512,bytes_per_tile=8192,
            SECDED_64plus8_storage_bits=73728,
            backpressure=False,physical_owner='native enclosing owner'),
        additional_engine_replicas_if_existing_slot_reused=0,
        existing_engine_area_reservation_um2=None,selected_engine_slot_source_joined=False,
        new_capture_protection_area_um2=None,source_staging_route_tracks=None,
        startup_and_launch_edges=None,weight_scatter_gather_edges=None,
        pipeline_tail_edges=None,W4_ACK_W6_reverse_edges=None,
        composed_token_latency_ps=None,physical_admission=False,
        clock_policy=dict(streaming_period_ps=str(C.FAST),setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        missing='Actual finite physical gather/x-BF16/capture services, endpoint routes, protected output capacity and completion intervals must be priced before controller RTL/build.')


class MatrixLoopController:
    """Cycle-driven transactor for existing engine, using enclosing shared tick.

    services are real physical provider bindings, not value-generating callbacks.
    Their interfaces expose retained request tags and actual capture/retirement.
    This API supplies no implementation of those owned services.
    """
    ID_WIDTHS={'session':64,'source_PC':11,'native_tag':64,'native_generation':64,
               'rank':1,'SM':5,'owner55':55,'output_version_id':11,'range_begin':9,'range_end':10}
    METHODS=('reserve_tile','capture_x_fragment','offer_weight_line','poll_weight_line',
             'capture_result','completion','release_tile')
    def __init__(self,pins,services,tile,*,enabled=False,issuer_identity=None):
        C.need(enabled,'controller default off')
        C.need(isinstance(tile,MatrixTile),'source-bound tile descriptor')
        C.need(all(callable(getattr(pins,k,None)) for k in ('get','set','tick')),'real engine pins/shared tick')
        C.need(all(callable(getattr(services,k,None)) for k in self.METHODS),'complete physical MATRIX services required')
        self.p=pins;self.s=services;self.t=tile
        self.phase='reserve';self.fragment=0;self.beat=0;self.frame=None
        self.pending={};self.accepted=0;self.rows=set();self.reservation=None
        self.started=False;self.descriptor_accepted=False;self.cycles=0
        self.issuer_identity=issuer_identity

    def step(self):
        C.need(self.phase!='done','completed source tile cannot reissue')
        p,s,t=self.p,self.s,self.t
        for name in ('start','d_valid','req_ready','rsp_v','xw_en','sw_en'):p.set(name,0)
        C.need(not p.get('fault'),'actual matrix engine fault')
        if self.phase=='reserve':
            r=s.reserve_tile(t.record())
            if r is not None:
                C.need(r.get('retained') is True and r.get('source_PC')==t.source_PC
                    and r.get('row_start')==t.row_start
                    and r.get('input_version')==t.input_version and r.get('output_version')==t.output_version
                    and r.get('weight_descriptor_sha256')==t.weight_descriptor_sha256
                    and r.get('identity') is not None and r.get('input_home') is not None
                    and r.get('engine_quiescent') is True
                    and r.get('output_capture_bytes',0)>=8192,'actual source/workspace/output reservation')
                identity=r['identity']
                C.need(type(identity) is dict and all(type(identity.get(k)) is int
                    and 0<=identity[k]<2**width for k,width in self.ID_WIDTHS.items()),
                    'complete captured full issuer identity')
                C.need(identity['source_PC']==t.source_PC 
                    and identity['range_begin']<identity['range_end']<=512
                    and r.get('GO_captured') is True,'matched actual issuer GO and finite RF range')
                if self.issuer_identity is not None:
                    C.need(all(identity[k]==self.issuer_identity[k] for k in
                        ('session','source_PC','native_tag','native_generation','rank','SM')),
                        'tile belongs to actual whole-operator issuer GO')
                self.reservation=r;self.phase='preload'
        elif self.phase=='preload':
            if self.frame is None:
                self.frame=s.capture_x_fragment(t.x_fragment(self.fragment),self.reservation)
                if self.frame is not None:
                    C.need(self.frame.get('captured') is True and self.frame.get('dtype')=='BF16'
                        and self.frame.get('fragment')==self.fragment
                        and self.frame.get('input_version')==t.input_version
                        and self.frame.get('home')==self.reservation['input_home']
                        and self.frame.get('native_recipe_sha256')==t.native_recipe_sha256,
                        'actual BF16 source capture')
                    data=self.frame['payload']
                    C.need(type(data) is bytes and len(data)==256,'128 source BF16 values')
            if self.frame is not None:
                # Byte routing only. No conversion/rounding in Python. Repeat
                # captured128BF16 values in each existing tensor column.
                data=self.frame['payload']*16;part=data[self.beat*256:(self.beat+1)*256]
                p.set('xw_en',1);p.set('xw_addr',self.fragment*8+self.beat//2)
                p.set('xw_grp',self.beat%2);p.set('xw_data',int.from_bytes(part,'little'))
                self.beat+=1
                if self.beat==16:
                    self.beat=0;self.fragment+=1;self.frame=None
                    if self.fragment==t.fragments:self.phase='issue'
        elif self.phase=='issue':
            if not self.started:
                C.need(not p.get('busy'),'existing engine idle required')
                p.set('op_rows',t.rows);p.set('op_c',t.chunk);p.set('op_g',t.groups)
                p.set('op_scale',0);p.set('start',1);self.started=True
            if not self.descriptor_accepted:
                p.set('d_base',0);p.set('d_lines',t.line_count);p.set('d_valid',1)
                if p.get('d_ready'):self.descriptor_accepted=True
            if p.get('req_v'):
                tag=p.get('req_tag');index=p.get('req_addr')
                C.need(tag not in self.pending and len(self.pending)<512,'retained bulk-copy tag capacity')
                C.need(index==self.accepted,'actual bulk-copy sequential line identity')
                plan=t.line(index)
                if s.offer_weight_line(tag,plan,self.reservation):
                    self.pending[tag]=index;self.accepted+=1;p.set('req_ready',1)
            rsp=s.poll_weight_line(self.reservation)
            if rsp is not None:
                tag=rsp['tag'];data=rsp['payload']
                C.need(tag in self.pending and rsp.get('line_address')==self.pending[tag]
                    and rsp.get('captured') is True
                    and rsp.get('weight_descriptor_sha256')==t.weight_descriptor_sha256
                    and rsp.get('rank')==t.weight_rank
                    and type(data) is bytes and len(data)==128,
                    'actual retained source weight capture/tag')
                p.set('rsp_v',1);p.set('rsp_tag',tag);p.set('rsp_data',int.from_bytes(data,'little'))
                del self.pending[tag]
            if p.get('rv'):
                row=p.get('rrow');data=p.get('rdata')
                C.need(0<=row<t.rows and row not in self.rows,'actual unique row capture')
                C.need(s.capture_result(row,data,self.reservation) is True,
                       'unbackpressured result requires actual finite hardware capture')
                self.rows.add(row)
            if len(self.rows)==t.rows and not self.pending:
                C.need(self.accepted==t.line_count,'all source lines physically delivered')
                self.phase='retire'
        elif self.phase=='retire':
            r=s.completion(self.reservation)
            if r is not None:
                C.need(r.get('identity')==self.reservation['identity']
                    and r.get('source_PC')==t.source_PC and r.get('row_start')==t.row_start
                    and all(r.get(k) is True for k in ('RF_visible','W4_ACK','W6_retired','reverse_validated')),
                    'real full result visibility/ACK/retirement/reverse required')
                C.need(not p.get('busy'),'internal busy is not physical retirement')
                if s.release_tile(self.reservation,r):self.phase='done'
        p.tick();self.cycles+=1
        return self.phase



class MatrixOperatorController:
    """One full original MATRIX PC. Tile retirement is not whole publication.

    All service methods are nonblocking and must not advance a private clock.
    release_tile releases only the tile workspace; the actual issuer/source
    lease stays owned until whole_completion + release_operator succeed.
    """
    def __init__(self,pins,services,native,source_PC,*,enabled=False):
        self.tiles=lower_matrix(native,source_PC,enabled=enabled)
        C.need(all(callable(getattr(services,k,None)) for k in
            ('begin_operator','whole_completion','release_operator')),'actual whole-operator issuer services')
        self.p=pins;self.s=services;self.index=0;self.tile=None;self.origin=None;self.phase='begin'

    def step(self):
        C.need(self.phase!='done','whole MATRIX already retired')
        t=self.tiles[0]
        if self.phase=='begin':
            origin=self.s.begin_operator(dict(program_sha256=t.program_sha256,source_PC=t.source_PC,
                input_version=t.input_version,output_version=t.output_version,weight_key=t.weight_key,
                weight_rank=t.weight_rank,tile_count=len(self.tiles),
                weight_descriptor_sha256=t.weight_descriptor_sha256,native_recipe_sha256=t.native_recipe_sha256))
            if origin is not None:
                identity=origin.get('identity',{})
                C.need(origin.get('GO_captured') is True and all(type(identity.get(k)) is int
                    and 0<=identity[k]<2**width for k,width in MatrixLoopController.ID_WIDTHS.items())
                    and identity['source_PC']==t.source_PC,'actual full MATRIX issuer GO')
                self.origin=origin;self.phase='tiles'
            self.p.tick()
        elif self.phase=='tiles':
            if self.tile is None:
                self.tile=MatrixLoopController(self.p,self.s,self.tiles[self.index],
                    enabled=True,issuer_identity=self.origin['identity'])
            self.tile.step()
            if self.tile.phase=='done':
                self.index+=1;self.tile=None
                if self.index==len(self.tiles):self.phase='whole_retire'
        elif self.phase=='whole_retire':
            receipt=self.s.whole_completion(self.origin)
            if receipt is not None:
                C.need(receipt.get('identity')==self.origin['identity']
                    and receipt.get('tile_count')==len(self.tiles)
                    and all(receipt.get(k) is True for k in
                        ('all_output_RF_visible','all_W4_ACK','whole_terminal','whole_reverse_validated','source_publication')),
                    'whole MATRIX source publication/terminal/reverse, not first row or tile')
                if self.s.release_operator(self.origin,receipt):self.phase='done'
            self.p.tick()
        return self.phase


def compose_inventory(native):
    rows=[];refusals=[];demand=C.source_demands(native,8191,C.counting_functions((C.ROOT/C.SOURCE).read_bytes()))
    C.need(C.sha(C.canonical(native))==C.PROGRAM_SHA,'exact canonical1737 identity')
    for op in native['operations']:
        if op['opcode']!='MATRIX':continue
        try:tiles=_lower_verified(native,op['pc'])
        except ValueError as e:
            refusals.append(dict(source_PC=op['pc'],reason=str(e)));continue
        price=price_tiles(tiles,sum(demand[op['pc']]['native_units'].values()))
        rows.append(dict(source_PC=op['pc'],tile_count=len(tiles),first_tile=tiles[0].record(),model=price))
    return dict(schema='QWEN_MATRIX_LOOP_SOURCE_IMPLEMENTATION_R1',operations=rows,refusals=refusals,
        program_sha256=C.PROGRAM_SHA,source_pins={name:C.sha((C.ROOT/name).read_bytes()) for name in SOURCES+(C.PROGRAM,C.SOURCE,
            'tools/gpu_sys/canonical_qwen_service_calendar.py',
            'tools/gpu_sys/canonical_qwen_matrix_loop.py',
            'tools/gpu_sys/test_canonical_qwen_matrix_loop.py')},
        compiler_source_sha256=C.sha(__import__('pathlib').Path(__file__).read_bytes()),
        physical_admission=False,EXP_reduction_modified=False,
        engine_controller_API='MatrixOperatorController(pins,services,native,source_PC,enabled=True).step()',
        handler_join='Claude native handler delegates exact MATRIX tile loop after source-contract enrollment; original classes/guards unchanged.')


if __name__=='__main__':
    import argparse,gzip
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',required=True,type=__import__('pathlib').Path)
    a.add_argument('--verify',action='store_true');args=a.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    raw=C.canonical(compose_inventory(C.read(C.ROOT/C.PROGRAM)))
    if args.verify:C.need(args.out.read_bytes()==raw,'cold source loop model equality')
    else:
        C.need(not args.out.exists(),'preserve frozen evidence');args.out.write_bytes(raw)
