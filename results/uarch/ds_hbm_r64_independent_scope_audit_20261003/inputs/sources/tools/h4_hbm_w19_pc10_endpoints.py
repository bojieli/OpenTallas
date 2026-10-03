#!/usr/bin/env python3
"""Selected W19 production endpoint directory and strict PC10 runtime adapter.

No numerical callback, synthetic source/home, provisional timing admission, or
Git-object dependency. Physical source selection precedes endpoint RTL.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h4_hbm_w19_pc10_endpoints_20261002'
PIN='064d5717b0b0018721f3382d4b25f8463a11c7031ff49b295dda71e4a0ef8c4b'
RF_SM=262144
RF_BYTES=32*2*RF_SM
SHARED_BYTES=65536

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def inputs():
    raw=(BASE/'input_manifest.json').read_bytes()
    if sha(raw)!=PIN:raise ValueError('input manifest pin')
    out={}
    for r in json.loads(raw)['inputs']:
        p=(BASE/r['archive']).resolve()
        if not p.is_relative_to(BASE.resolve()):raise ValueError('archive origin')
        b=p.read_bytes()
        if sha(b)!=r['sha256'] or len(b)!=r['bytes']:raise ValueError('input source pin')
        out[p.name]=b
    return out

def decoded(s,name):return json.loads(gzip.decompress(s[name]))

def select_home(homes,indices,version,rank,sm):
    rows=[(i,homes[i]) for i in indices if homes[i]['version']==version
          and rank in homes[i]['rank_group'] and homes[i]['SM']==sm]
    if len(rows)!=1 or rows[0][1]['home']['class']!='RF':
        raise ValueError('unique production RF home required')
    return rows[0]

def rf_ref(index,home,rank,word_offset):
    if type(rank)is not int or not 0<=rank<96 or type(word_offset)is not int or not 0<=word_offset<home['word_count']:
        raise ValueError('rank/word extent')
    sm=home['SM'];slot=home['home']['slot_first']+word_offset//128
    if slot>=512:raise ValueError('RF slot extent')
    return dict(provider_reference=index,version=home['version'],rank=rank,die=rank,SM=sm,
        slot=slot,page=slot//128,row=slot%128,bank=(word_offset%128)//8,
        word_lane=word_offset%8,instance=f'die{rank}/sm{sm}/g_page[{slot//128}]/g_bank[{(word_offset%128)//8}]',
        mirror_byte_addresses=[(2*sm+c)*RF_SM+home['home']['slot_first']*512+word_offset*4 for c in (0,1)],
        expected_ACK='both operand copy w_ce from write_go; registered host_ack_valid&&host_ack_ready')

def build():
    s=inputs();product=decoded(s,'product.json.gz');homes=decoded(s,'homes.json.gz')['homes']
    if product['tp']!=96 or product['head_dies']!=64 or product['variant']!='oreduce':raise ValueError('W19 selected product')
    if '96 GPU-organised dies' not in s['W19_source.py'].decode():raise ValueError('W19 die source')
    if 'V4.1 HBM tier 3 (96 dies)' not in gzip.decompress(s['unified.py.gz']).decode():raise ValueError('unified die source')
    if "dict(rank=r, die=r, SM=s" not in s['V1_mapping.py'].decode():raise ValueError('reviewed V1 rank mapping')
    plan=next(p for p in decoded(s,'tiles.json.gz') if p['PC']==10)
    fp=decoded(s,'floorplan.json.gz');matrix=next(o for o in product['layers'][0]['ops'] if o.get('fn')=='wo_a_part')
    if matrix['k']!=512 or matrix['out']!='zpart':raise ValueError('whole K512 W19 product')
    mapping=[dict(rank=r,die=r,SM=sm,instance=f'die{r}/sm{sm}') for r in range(96) for sm in range(32)]
    bindings=[]
    for rank in range(96):
        tiles=[]
        for t in plan['tiles']:
            output_i,output_h=select_home(homes,plan['source_writes'][0]['home_indices'],t['destination_version'],rank,t['SM'])
            output=rf_ref(output_i,output_h,rank,t['first']%256)
            source=[]
            for span in t['source_spans']:
                sr=span['source_rank'];ss=span['local_word_first']//256%32
                i,h=select_home(homes,plan['source_reads'][0]['home_indices'],span['source_version'],sr,ss)
                ref=rf_ref(i,h,sr,span['local_word_first']%256)
                ref.update(bytes=512,LOAD_flat_word_first=span['LOAD_flat_word_first'],
                    contributor=span['contributor'],producer_PC=9,
                    matrix_global_row_first=(sr//8)*1024+span['local_word_first'],
                    matrix_whole_K=512,matrix_column_range=[(sr%8)*512,(sr%8+1)*512],
                    consumer_die=rank,consumer_SM=t['SM'],
                    route='source RF -> existing TP96 collective -> destination SM shared64',
                    route_interval_bound=None)
                source.append(ref)
            tiles.append(dict(tile=t['group']*8+t['first']//128,SM=t['SM'],source=source,output=output,
                output_global_first=t['output_flat_word_first'],
                shared=dict(die=rank,SM=t['SM'],base=RF_BYTES+t['SM']*SHARED_BYTES,bytes=SHARED_BYTES,
                    operand_double_buffer_bytes=8192,output_tile_bytes=512,peak_RF_vectors=16,
                    port='g_sm[SM].u_service.scratch_valid/ready/write/addr/wdata/done/done_ready',
                    local_byte_first=0,local_byte_limit=8704),
                output_consumer_and_reverse_bound=None))
        bindings.append(dict(PC=10,rank=rank,die=rank,tiles=tiles))
    # Source floorplan supplies64 actual32KiB SRAMs per slice:8 banks*8 macros.
    # Select one512B transient vector per bank, reducing L2 capacity16KiB
    # per die. This is an explicit NEW allocation, not an installed directory.
    l2=[]
    for slice_id,label in enumerate(('s0','s1','n0','n1')):
        macro_rows={int(x['name'].split('_m')[-1]):x for x in fp['macro_placements'] if x['name'].startswith('l2_'+label+'_m')}
        if set(macro_rows)!=set(range(64)):raise ValueError('actual source L2 macro inventory')
        for bank in range(8):
            macro=macro_rows[56+bank]
            if macro['macro']!='ot_sram_1r1w_1024x256_m2_r2c2':raise ValueError('actual L2 master')
            l2.append(dict(slice=slice_id,bank=bank,macro=macro,byte_first=261632,bytes=512,
                word_rows=list(range(1008,1024)),macro_in_bank=7,
                selected_bank_interleave='macro_index=8*macro_in_bank+bank',credit=1,
                use='matrix/frame or C0/KV vector staging; bank owner held through both RF mirrors and reverse',
                allocation='selected new reservation; old cache/directory must exclude this vector before enable',
                installed=False))
    failure=json.loads(s['prefix_failure.json'])
    return dict(schema='HBM_W19_PRODUCTION_PC10_ENDPOINT_DIRECTORY_V1',default_enabled=False,
        source_mapping_admitted=True,source_mapping_basis='W19 TP96 product + unified96 dies + reviewed V1 map',
        rank_die_SM=mapping,PC10=bindings,source_spans=96*512,output_tiles=96*64,
        production_RF_homes=True,synthetic_state_sources_allowed=False,synthetic_slot32_outputs_allowed=False,
        matrix_owner_selection='local source output block256%32; whole K512 remains in one SM; descriptors carry actual home refs before start',
        matrix_to_L2=dict(frame='existing priced DS256KiB per-SM frame; rv/rrow/rdata has no ready; reserve before start',
            global_row_translation='global_row=(head_rank//8)*1024+local_source_row',
            local_source_row_translation='local_source_row=256*source_SM+8*frame_rrow+column',
            source_output_rows_per_active_SM=256,source_output_words_per_row_packet=8,
            matrix_packet_route_bound=None,source_connected_RTL=False),
        selected_L2_transient_directory=l2,L2_reserved_capacity_bytes_per_die=16384,
        general_L2_capacity_bytes_before=8388608,general_L2_capacity_bytes_after=8372224,
        cache_capacity_loss_fraction=16384/8388608,cache_miss_latency_delta=None,
        vector_owner=dict(range_bytes=512,length_encoding='four128B lines;8bit count reused',
            word_handshakes=32,bank_word_write_accepts=16,bank_word_read_captures=16,
            word_ordinal_bits=5,captured_word_count_bits=6,
            metadata_bits=450,entry_footprint_um2=600.9744+8*.2916*2,
            existing_bank_metadata_reserved_bits=576,new_register_area_charge=0,
            bank_credit_release='after all16 writes+16 reads, H1 both-copy ACK, consumer and reverse',
            RF_assembly='existing512B C0/V1 destination register must remain leased; no unpriced extra vector buffer',
            actual_assembly_register_route_and_hold_bound=None),
        shared_bytes_per_die=32*65536,RF_mirrored_bytes_per_die=RF_BYTES,
        ports=dict(RF_read_vectors=2,RF_write_vectors=1,RF_bytes_per_vector=512,RF_mirrors=2,
            shared_bytes=64,L2_bytes_per_word=32,L2_line_words=4,L2_banks_per_slice=8),
        movement_count_model=dict(scope='selected one PC9+PC10 source execution, all actual ranks; counts, not runtime qualification',
            PC9_matrix_result_bytes=64*1024*4,PC9_active_source_SM_instances=64*4,
            PC9_matrix_frame_packets32=64*4*32,
            PC9_L2_transient_write128=2048,PC9_L2_transient_read128=2048,
            PC9_L2_reference_leaf_work_edges=2048*(8+12),
            PC9_L2_reference_leaf_edges_per_active_SM=8*(8+12),
            PC9_L2_reference_latency_scope='candidate additive matrix-frame connection; external stalls, routes, arbitration and clock latency unknown; not token sum',
            PC9_RF_mirrored_publication_bytes=2*64*1024*4,
            PC10_RF_read_pair_commands=96*512,PC10_RF_pair_response_bytes=96*512*1024,
            PC10_actual_contributor_payload_bytes=96*512*512,
            PC10_shared64_commands=96*9216,PC10_shared64_bytes=96*9216*64,
            PC10_RF_write_vectors=96*64,PC10_RF_two_mirror_write_bytes=96*64*1024,
            PC10_provider_readback_bytes=96*8192*4,
            unused_RF_second_read_payload_is_charged=True,
            no_collective_ideal_multicast_credit=True,
            new_cost_event_keys=['PC9.matrix_frame.L2_transient_write128','PC9.matrix_frame.L2_transient_read128'],
            current_RF_shared_provider_I64_RMW_cost_keys_reused=True,
            new_L2_stage_cost_inserted_into_calendar=False),
        ACK=dict(source='H1 common write_go to both SRAM copies; combined registered host_ACK',
            visibility='both write-edge receipts plus ACK handshake before visibility; hold through consumer and reverse',
            hold_upper_edges=None),
        costs=dict(physical_reference_bits=32,rank_die_bits_reuses_owner_rank=7,
            additional_RF_I64_RMW_C0_provider_charges=0,
            RF_pair_reference_source_edges=3,RF_mirrored_write_reference_edges=2,
            shared64_read_reference_edges=3,shared64_write_reference_edges=2,
            L2_read128_reference_edges=12,L2_write128_reference_edges=8,
            external_backend_consumer_reverse_edges=None,
            source_edges_are_measured_context=False,whole_token_latency_ns=None),
        latest_producer_prefix=dict(status=failure['status'],reason=failure.get('reason'),
            source_receipt_sha256=sha(s['prefix_failure.json']),production_PC10_payloads_ready=False),
        admission='PASS_SELECTED_W19_SOURCE_MAPPING_FAIL_FINITE_PRODUCTION_ENDPOINT_COMPOSITION',
        hardware_admitted=False,engine_build_allowed=False,production_physical_bound_calls=0)

def retained_owner():
    raw=inputs()['owner.py'];ns=dict(__name__='retained_owner',__file__=str(BASE/'inputs/owner.py'))
    exec(compile(raw,'retained54bf_owner','exec'),ns)
    return ns

def vector_finite_bounds(contenders,waits,contender_inventory_pin):
    """Exact512B stage count, with no implicit external bound or tick conversion."""
    required={'drain','bank_write32','bank_read32','mirror_ACK','visibility','consumer','reverse'}
    if set(waits)!=required:raise ValueError('complete explicit vector endpoint contract')
    missing=[k for k,v in waits.items() if v is None]
    if missing or contenders is None:
        return dict(status='FAIL_FINITE_VECTOR_WAIT_BINDING',missing=missing+(['contenders'] if contenders is None else []),upper_edges=None)
    f=retained_owner()['finite_bounds']
    base=dict(contenders=contenders,words=1,drain=waits['drain'],mirror_ACK=waits['mirror_ACK'],
        visibility=waits['visibility'],consumer=waits['consumer'],reverse=waits['reverse'],provenance=contender_inventory_pin)
    f(word_service=waits['bank_write32'],**base)
    result=f(word_service=waits['bank_read32'],**base)
    h=sum(waits[k][0] for k in ('drain','mirror_ACK','visibility','consumer','reverse'))+16*(waits['bank_write32'][0]+waits['bank_read32'][0])
    result.update(credit_hold_upper_edges=h,arbitration_wait_upper_edges=(contenders-1)*(h+1),
        completion_upper_edges=(contenders-1)*(h+1)+h,bank_write_words=16,bank_read_words=16,
        all_endpoint_terms_measured=all(v[1]=='measured_context_SS_FF' for v in waits.values()),
        vector_source_terms={k:list(v) for k,v in waits.items()},
        hardware_qualified=False,existing_costs_recharged=False)
    return result

def vector_owner_controller(physical_dies):
    """Adapt the exact442bit owner FSM to a fenced512B bank reservation.

    Sixteen actual bank write acceptances then sixteen read captures fill the
    leased C0 destination. No RF publication before the resulting host ACK.
    """
    ns=retained_owner()
    class VectorOwner(ns['OwnerController']):
        def acquire(self,owner,*,size,**kw):
            if size!=512:return super().acquire(owner,size=size,**kw)
            address=kw['address']
            if (address!=261632 or not kw['write'] or kw.get('mirror_required',True)is not True
                    or owner[1]!=9 or not 0<=owner[3]<64 or kw['die']!=owner[3]
                    or kw['sm']>=4 or kw['bank']!=kw['sm']%8):
                raise ValueError('selected512B matrix reservation with mirror fence')
            super().acquire(owner,size=128,**kw)
            x=self.sms[kw['die'],kw['sm']];x['size']=512;x['words']=32
        def word_descriptor(self,owner,*,die):
            x=self.sms.get((die,owner[-1]))
            if x is None or x['owner']!=owner or x['phase']!='CAPTURE':raise ValueError('owned vector capture phase')
            n=x['captured_words']
            return dict(ordinal=n,bank=x['bank'][-1],bank_byte_address=x['address']+(n%16)*32,
                macro_in_bank=7,row=1008+n%16,write=n<16,read=n>=16,
                SRAM_bytes=32,source_consumption='leased512B C0 destination' if n>=16 else None)
    return VectorOwner(tuple(physical_dies))

class ProductionPC10:
    """Opt-in adapter for an ACTUAL live provider, never a synthetic control.

    Invoke the existing pinned generic primitive executor only after all64 PC9
    RF producers are present and the actual directory/writer identity matches.
    No source state restoration or high-level numerical result hook is offered.
    """
    def __init__(self,provider):
        s=inputs();self.homes=decoded(s,'homes.json.gz')['homes'];self.provider=provider
        if canonical(provider.homes)!=canonical(self.homes):raise ValueError('complete actual production home directory required')
        self.plan=next(p for p in decoded(s,'tiles.json.gz') if p['PC']==10)

    def identity(self,rank):
        if type(rank)is not int or not 0<=rank<96:raise ValueError('actual W19 rank')
        w=self.plan['source_writes'][0]
        indices=[i for i in w['home_indices'] if rank in self.homes[i]['rank_group']]
        return dict(PC=10,rank=rank,version=w['version'],generation=self.provider.generation,home_indices=indices)

    def ready(self,rank):
        identity=self.identity(rank);version=self.plan['source_reads'][0]['version'];p=self.provider
        for sr in range(64):
            loc=p.locations.get((version,sr))
            expected=[i for i in self.plan['source_reads'][0]['home_indices'] if sr in self.homes[i]['rank_group']]
            if (loc is None or loc.get('kind')=='state_fragment' or sorted(loc.get('indices',[]))!=sorted(expected)
                    or list(loc['shape'])!=[1024] or str(loc['dtype'])!='float32' or loc['pc']!=9):
                raise ValueError('actual PC9 production RF source missing or wrong home')
        return identity

    def execute(self,continuation,calendar,*,rank,shared_factory,primitive_sources,movement_observer=None):
        if continuation.provider is not self.provider:raise ValueError('same actual provider required')
        fn=calendar.execute_ds_provider_group128
        if sha(Path(fn.__code__.co_filename).read_bytes())!=sha(inputs()['calendar.py']):
            raise ValueError('exact generic native calendar executor required; no family oracle')
        identity=self.ready(rank)
        def factory(owner):
            memory=shared_factory(owner);e=memory.extent
            if (e.get('base'),e.get('bytes'),e.get('rank'),e.get('SM'))!=(
                    RF_BYTES+owner['SM']*SHARED_BYTES,SHARED_BYTES,owner['rank'],owner['SM']):
                raise ValueError('selected real shared directory required')
            return memory
        return calendar.execute_ds_provider_group128(continuation,10,rank,generation=self.provider.generation,
            identity=identity,source_store_view=continuation.plan.parents[10]['writes'][0]['native_result_binding'],
            shared_factory=factory,primitive_sources=primitive_sources,movement_observer=movement_observer)

class ProductionSharedFactory:
    """Finite data-only shared port backing with actual selected addresses.

    Uses existing addressed sector primitives; phase ticks remain SOFTWARE
    semantics. Only32 actual SM shared allocations per die are possible.
    """
    def __init__(self,budget):self.budget=budget;self.memories={};self.sources=inputs()
    def __call__(self,owner):
        from hbm_bound_event_journal_r30 import BoundSectorProvider
        import hbm_provider_microvm_r21 as sector
        Identity=sector.Identity
        if sha(Path(BoundSectorProvider.__init__.__code__.co_filename).read_bytes())!=sha(self.sources['journal.py']):
            raise ValueError('exact addressed journal provider source')
        if sha(Path(sector.__file__).read_bytes())!=sha(self.sources['sector.py']):
            raise ValueError('exact sector identity source')
        rank,sm=owner['rank'],owner['SM']
        if (type(rank)is not int or not 0<=rank<96 or type(sm)is not int or not 0<=sm<32
                or owner['PC']!=10 or type(owner['generation'])is not int or owner['generation']<=0):
            raise ValueError('real PC10 shared owner')
        key=(rank,sm)
        if key not in self.memories:
            class Memory:
                def __init__(self):
                    self.extent=dict(base=RF_BYTES+sm*SHARED_BYTES,bytes=SHARED_BYTES,rank=rank,SM=sm)
                    self.p=BoundSectorProvider({('DeepSeek',rank):[dict(base=self.extent['base'],bytes=SHARED_BYTES)]},
                        journal_budget=outer.budget,tags=1,allocation_identity=dict(owner,die=rank,address_class='shared'))
                    self.serial=0;self.owner=dict(owner)
                def transact(self,offset,*,write,payload,length):
                    if type(offset)is not int or offset<0 or offset%32 or type(length)is not int or length<=0 or length%32 or offset+length>SHARED_BYTES:
                        raise ValueError('finite aligned source shared extent')
                    if type(write)is not bool or (write and (not isinstance(payload,bytes) or len(payload)!=length)):
                        raise ValueError('exact opaque shared write payload')
                    chunks=[]
                    for first in range(0,length,32):
                        if self.serial>=2**40:raise ValueError('source sequence overflow requires drain')
                        tx=self.p.submit(Identity('DeepSeek',rank,self.owner['generation'],10,self.serial,
                            (self.extent['base']+offset+first)//32),write=write,payload=payload[first:first+32] if write else b'')
                        self.serial+=1;chunks.append(self.p.wait(tx));self.p.finish(tx)
                    return b''.join(chunks)
            outer=self;self.memories[key]=Memory()
        memory=self.memories[key]
        if any((memory.p.live,memory.p.queue,memory.p.calendar,memory.p.resident)):
            raise ValueError('prior actual shared owner has reverse debt')
        memory.owner=dict(owner);memory.p.allocation_identity=dict(owner,die=rank,address_class='shared')
        return memory

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    raw=gzip.compress(canonical(build()),mtime=0);a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.verify:
        if a.out.read_bytes()!=raw:raise ValueError('endpoint directory replay')
    else:
        if a.out.exists():raise ValueError('fresh evidence required')
        a.out.write_bytes(raw)
    print('PASS_SELECTED_W19_SOURCE_MAPPING; finite production endpoint composition remains FAIL')

if __name__=='__main__':main()
