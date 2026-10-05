"""Source-bound128-lane operands for the corrected eight-group DS program.

Software planning/control only. Keeps each group's original contributor tree,
round points and group/word flatten. No reprice or hardware latency credit.
"""
import gzip,hashlib,json
from collections import Counter
import numpy as np
from h4_c0_model import pinned
from h3_qwen_bounded_native import NativePrimitiveVM

DEWEY='ba0c1ba0625b58add3216d77a91e010a1daece6f'
PATH='results/uarch/h3_complete_native_calendar_20261002/portable_input_closure_r1/r34_portable_r4/source_inventory.json.gz'
NATIVE='c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264'
DISPATCH='bcf7d800aa64aeff92b8a1954cab328911c400025179d6a9ab9f211a934c253c'
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def last_uses(program):
    counts=Counter(v for n in program['code'] for v in n['src'])
    counts.update(program['outputs'].values());return counts
def live_RF_bound(program):
    counts=last_uses(program);live={};peak=0
    for node in program['code']:
        live[node['dst']]=8 if node['op']=='LOAD' else 1
        peak=max(peak,sum(live.values()))
        for source in node['src']:
            counts[source]-=1
            if not counts[source]:live.pop(source)
    return peak

class GroupOperandTiles:
    def __init__(self):
        self.inventory=json.loads(gzip.decompress(pinned(PATH,DEWEY)))
        if (self.inventory['source_native_sha256'],self.inventory['source_dispatch_sha256'])!=(NATIVE,DISPATCH):raise ValueError('exact corrected eight-group source required')
        self.parents={row['pc']:row for row in self.inventory['corrected_PC_bindings']}
        if len(self.parents)!=40:raise ValueError('all40 actual corrected source PCs required')
        self.templates=self.inventory['native_templates']
        for parent in self.parents.values():
            ranks=parent['actual_rank_template_bindings']
            if len(ranks)!=96 or [row['rank'] for row in ranks]!=list(range(96)) or any(row['template']!=parent['new_template'] for row in ranks):raise ValueError('all96 current rank/template bindings required')
        for tid,p in self.templates.items():
            if digest(p)!=tid or p['providers']['parts']['shape']!=[8,8,1024]:raise ValueError('exact original lowerer template and LOAD shape required')
            code=p['code'];leaves={}
            for node in code:
                if node['op']=='SLICE':leaves[node['dst']]=node['attrs']['start']
                elif node['op']=='RESHAPE' and node['src'][0] in leaves:leaves[node['dst']]=leaves[node['src'][0]]
                elif node['op']=='FADD':leaves[node['dst']]=tuple(leaves[v] for v in node['src'])
            if leaves['v23']!=(((0,1),(2,3)),((4,5),(6,7))):raise ValueError('golden contributor order changed')
            if p['outputs']!={'out':'r34_group_output'} or code[-1]['shape']!=[8192]:raise ValueError('source group flatten changed')
    def tile(self,PC,destination_rank,group,first):
        if PC not in self.parents or type(destination_rank)!=int or not 0<=destination_rank<96 or type(group)!=int or not 0<=group<8 or type(first)!=int or first not in range(0,1024,128):raise ValueError('actual bounded group/word/rank source tile required')
        parent=self.parents[PC];tid=parent['new_template'];bindings=parent['actual_rank_template_bindings']
        if bindings[destination_rank]['rank']!=destination_rank or bindings[destination_rank]['template']!=tid or not bindings[destination_rank]['SM_partition'].startswith('block256%32;'):raise ValueError('actual source rank/template/SM partition required')
        source_version=parent['provider_bindings'][tid]['parts']['version']
        spans=[dict(contributor=j,source_rank=8*group+j,source_version=source_version,local_word_first=first,
            source_global_word_first=group*1024+first,LOAD_flat_word_first=(j*8+group)*1024+first,
            words=128,bytes=512,shared64_beats=8) for j in range(8)]
        tile=dict(schema='C0_R34_GROUP_OPERAND_TILE_V1',native_sha256=NATIVE,dispatch_sha256=DISPATCH,
            source_PC=PC,parent_template=tid,destination_rank=destination_rank,SM=(group*1024+first)//256%32,
            group=group,first=first,active_lanes=128,tile_ordinal=group*8+first//128,
            source_spans=spans,destination_version=parent['writes'][0]['version'],output_flat_word_first=group*1024+first,
            output_words=128,output_bytes=512,physical_RF_mapping_qualified=False,hardware_qualified=False)
        tile['C0_tile_template_id']=digest(tile);return tile
    def run_control(self,PC,group,first,inputs):
        """Original primitive operations/attrs over one source tile, CPU only."""
        tile=self.tile(PC,0,group,first);p=self.templates[tile['parent_template']]
        a=np.asarray(inputs)
        if a.shape!=(8,128) or a.dtype!=np.float32:raise ValueError('all eight ordered actual F32 source operand spans required')
        values={};vm=NativePrimitiveVM();uses=last_uses(p)
        for node in p['code']:
            if node['op']=='LOAD':value=a
            elif node['op']=='SLICE':
                attrs=node['attrs']
                if attrs['axis']!=0:raise ValueError('source contributor axis changed')
                value=values[node['src'][0]][attrs['start']:attrs['stop']:attrs['step']]
            else:
                shape=() if node['shape']==[] else ((1,128) if node['shape']==[1,8,1024] else (128,))
                value=vm.primitive(node['op'],[values[v] for v in node['src']],attrs=node['attrs'],shape=shape)
            values[node['dst']]=value
            for source in node['src']:
                uses[source]-=1
                if not uses[source]:del values[source]
        return values[p['outputs']['out']]
    def report(self):
        return dict(schema='C0_R34_GROUP_OPERAND_SPAN_MODEL_V1',source_native_sha256=NATIVE,source_dispatch_sha256=DISPATCH,Dewey_commit=DEWEY,
            corrected_PCs=40,corrected_rank_calls=3840,tiles_per_call=64,source_contributor_rank='8*group+j, j=0..7; never reassociate',
            tree='((0+1)+(2+3))+((4+5)+(6+7)), then original BF16 RNE instructions',
            source_input_bytes_per_call=262144,output_bytes_per_call=32768,
            physical_shared_capacity_bytes=65536,input_double_buffer_bytes=8192,output_buffer_bytes=512,
            planned_data_scratch_peak_bytes=8704,controller_state_in_scratch=False,
            overlap_assumed=False,double_buffer_reserved_not_overlapped=True,
            native_RF_upper_bound_vectors_per_tile=43,RF_upper_bound_bytes_per_tile=22016,
            ordered_last_use_RF_vectors=max(live_RF_bound(p) for p in self.templates.values()),
            ordered_last_use_RF_bytes=512*max(live_RF_bound(p) for p in self.templates.values()),
            reuse_requires_source_capture_and_result_ACK_before_reassignment=True,
            last_use_reuse_software_only=True,
            shared64_input_refill_beats_per_tile=64,shared64_input_capture_beats_per_tile=64,
            shared64_output_write_beats_per_tile=8,shared64_output_consume_beats_per_tile=8,
            planned_shared64_beats_per_call=9216,shared_service_bpc=64,
            lease_order=['accept unique PC/template/generation/destination-rank/SM/tile owner',
                'serial finite512B span credit per contributor; retain version/home lease',
                'real refill backing/shared visibility plus reverse receipt for each accepted tag/generation',
                'all eight input spans visible before native source capture',
                'original arithmetic/rounding instructions; keep intermediates lane-local',
                'both RF mirrored result ACKs before output writeback',
                'output consumer accept and exact reverse grant before reuse of output/bank/ticket',
                'next tile; keep destination version unpublished until all64 tiles commit and reverse-drain',
                'release source version only after all64 tiles/consumers and actual dependent rank consumers retire'],
            provider_fragment_credit=1,provider_fragment_bytes_max=512,tiles_live_per_SM=1,
            source_tag_bits=16,source_generation_bits=64,tile_sequence_bits=64,source_rank_bits=7,SM_bits=5,group_bits=3,word_offset_bits=10,
            actual_parent_movement_journals=None,unknown_calls_retained=193316,
            native_reprice_count_unchanged=1,C0_reprice_count_unchanged=1,RF_mirror_I64_RMW_recharged=False,
            existing_full_workspace_software_bytes=524288,software_spill_is_not_physical_fit=True,
            composed_state_area_route_latency_pending=True,whole_service_latency=None,hardware_admitted=False)
