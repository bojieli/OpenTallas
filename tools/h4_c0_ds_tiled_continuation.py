"""Opt-in actual addressed DS group continuation. Software execution only.

Reads retained producer backing, executes the unchanged native instruction
tree, then publishes through the provider's actual mirrored RF writer. The
32KiB unpublished output is explicitly charged alongside the operand bank.
Failures retain the source lease and evidence; callers must not retry it.
"""
import ast, gzip, hashlib, json, math, pathlib, re
from collections import Counter
import numpy as np
from h4_c0_ds_source_views import SourceViews, canonical
from h4_c0_group_operand_tiles import GroupOperandTiles, NATIVE
from h4_c0_provider_movement import prove_sector_span
from h4_c0_model import pinned

def operand_receiver():
    """Load only the retained b212 receiver functions, with no generator run."""
    raw=pinned('tools/h3_complete_native_calendar.py',
        'b2120f45d9a9fc419bc78d52d3224065483e4c87')
    tree=ast.parse(raw)
    names={'positive','native_value_specs','resolve_ds_movement_reference','verify_ds_operand_journal'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes}!=names:raise ValueError('exact b212 receiver closure')
    scope=dict(math=math,re=re,json=json,hashlib=hashlib,Counter=Counter)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'b212_receiver','exec'),scope)
    return scope['verify_ds_operand_journal']

def compose_r36(base, *, base_sha256):
    """Keep Kepler query/history interception above the Sagan source bridge."""
    from h4_c0_ds_source_views import provider_class
    from h3_ds_query_provider_r36 import QueryMixin
    from h3_ds_history_provider_r36 import HistoryMixin
    for cls, expected in ((QueryMixin,'717f127d48779d3552a1fc00aab25e2468d768d9a4cbcf6c690326959fdb78f9'),
                          (HistoryMixin,'04b8f20c9aec5591be7fd86f2c4e11e31e42967a08918ab42bd98b0dcd4545df')):
        source=pathlib.Path(cls.publish.__code__.co_filename)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
            raise ValueError('exact reviewed r36 mixin source required')
    sagan = provider_class(base, expected_provider_sha256=base_sha256)
    class Provider(QueryMixin, HistoryMixin, sagan):
        pass
    return Provider

class TiledContinuation:
    def __init__(self, provider, *, native_artifact_path):
        artifact=pathlib.Path(native_artifact_path).read_bytes()
        native_artifact_sha256=hashlib.sha256(artifact).hexdigest()
        if native_artifact_sha256 != NATIVE:
            raise ValueError('corrected c65 native artifact required')
        if canonical(json.loads(gzip.decompress(artifact)))!=canonical(provider.native):
            raise ValueError('complete provider native differs from pinned artifact')
        self.provider = provider
        self.plan = GroupOperandTiles()
        self.bridge = SourceViews(provider, native_content_sha256=
            hashlib.sha256(canonical(provider.native)).hexdigest())
        # An artifact label alone is insufficient: compare every changed
        # template and actual PC/rank/provider/writer binding to its inventory.
        for pc, parent in self.plan.parents.items():
            ops = [o for o in provider.native['instructions'] if o['pc'] == pc]
            tid = parent['new_template']
            if len(ops) != 1 or provider.native['templates'].get(tid) != self.plan.templates[tid]:
                raise ValueError('actual current arithmetic template mismatch')
            op = ops[0]
            if (op['provider_bindings'] != parent['provider_bindings'] or
                    op['writes'] != parent['writes'] or
                    [(r['rank'], r['template']) for r in op['rank_bindings']] !=
                    [(r['rank'], r['template']) for r in parent['actual_rank_template_bindings']]):
                raise ValueError('actual current PC/rank/version bindings mismatch')
        self.failed = False
        self.completed = set()
        self.receiver = operand_receiver()

    def receive(self, tile, span, loc, receipt, lease_id):
        """Join source storage identity to the consumer's original LOAD span.

        Producer-PC journal ownership is distinct from destination-PC dispatch.
        This is an explicit software backing translation, not installed HBM.
        """
        p=self.provider;rank=span['source_rank'];first=span['local_word_first']
        if not p._leased(span['source_version']):raise ValueError('actual source version lease lost')
        if loc.get('kind')=='state_fragment':
            engine=p.state[rank];address=loc['binding']['base']+first*4
            source_sm=tile['SM']
        else:
            from h3_ds_checkpoint_provider_r30 import RF_SM
            source_sm=first//256%32
            homes=[p.homes[i] for i in loc['indices'] if p.homes[i]['SM']==source_sm]
            if len(homes)!=1:raise ValueError('concrete contiguous source RF home required')
            h=homes[0];chosen=np.arange(1024);chosen=chosen[chosen//256%32==source_sm]
            positions=np.searchsorted(chosen,np.arange(first,first+128))
            if not np.array_equal(chosen[positions],np.arange(first,first+128)) or not np.all(np.diff(positions)==1):raise ValueError('contiguous actual source128 span required')
            address=source_sm*2*RF_SM+h['home']['slot_first']*512+int(positions[0])*4
            engine=p.rf[rank]
        template=tile['parent_template'];index=1+2*span['contributor']
        node=self.plan.templates[template]['code'][index]
        offset=span['LOAD_flat_word_first']*4
        reference=dict(template=template,code_index=index,opcode=node['op'],attrs=node['attrs'],result_shape=node['shape'],operand='src:0',value='v0',logical_byte_offset=offset,payload_bytes=512)
        binding=dict(PC=loc['pc'],rank=rank,SM=source_sm,generation=p.generation,
            lease=lease_id,lease_state='active',version=span['source_version'],native_SSA_value='v0',
            logical_base=address,allocation_bytes=512,operand_base_offset=offset,
            shared_tile_offset=span['contributor']*512,shared_capacity_bytes=65536,provider_tag_capacity=engine.tags)
        translation={k:binding[k] for k in ('rank','SM','generation','version','lease')}
        translation.update(logical_base=address,physical_base=address,bytes=512,AW=27)
        proof=self.receiver({'templates':self.plan.templates},template,reference,binding,
            engine.events[receipt['start']:receipt['end']],translation=translation)
        proof.update(consumer_PC=tile['source_PC'],consumer_rank=tile['destination_rank'],
            translation_scope='explicit provider software backing namespace; not installed hardware',
            dispatch_binding_checked=True)
        return proof

    def run(self, PC, rank, *, generation, identity, source_store_view):
        p = self.provider
        if self.failed or (PC, rank, generation) in self.completed:
            raise ValueError('failed or already completed continuation; no duplicate')
        if generation != p.generation:
            raise ValueError('actual generation required')
        self.bridge._check()
        parent = self.plan.parents[PC]
        version = parent['provider_bindings'][parent['new_template']]['parts']['version']
        writer = parent['writes'][0]
        if (identity.get('PC'), identity.get('rank'), identity.get('generation'), identity.get('version')) != (PC, rank, generation, writer['version']) or source_store_view != writer['native_result_binding']:
            raise ValueError('exact native destination writer required')
        if not identity.get('home_indices') or p._leased(writer['version']):
            raise ValueError('concrete unleased destination RF homes required')
        if any(k[:3] == (PC, rank, generation) for k in p.views):
            raise ValueError('native operation owner already live')
        # Existing provider release_version recognises this lease. Register it
        # before any reads, not after constructing the full operand array.
        lease = {'parts': dict(version=version, leased_versions=[version],
            source_ranks=list(range(64)), provenance_certified=False, data=None)}
        key = (PC, rank, generation, id(lease))
        p.views[key] = lease
        output = np.empty(8192, np.float32)  # unpublished finite staging
        tiles = []
        try:
            for group in range(8):
                for first in range(0, 1024, 128):
                    tile = self.plan.tile(PC, rank, group, first)
                    inputs = np.empty((8, 128), np.float32)
                    receipts = []
                    for span in tile['source_spans']:
                        loc = p.locations.get((version, span['source_rank']))
                        if loc is None or list(loc['shape']) != [1024] or np.dtype(loc['dtype']) != np.dtype('float32'):
                            raise ValueError('actual owned1024 F32 producer backing required')
                        words, loc, receipt = self.bridge._read_words(version,
                            span['source_rank'], np.arange(first, first+128))
                        receipt['b212_source_join']=self.receive(tile,span,loc,receipt,
                            f'C0:{PC}:{rank}:{generation}:{version}')
                        inputs[span['contributor']] = words.view(np.float32)
                        receipts.append(receipt)
                    value = self.plan.run_control(PC, group, first, inputs)
                    offset = tile['output_flat_word_first']
                    output[offset:offset+128] = value
                    tiles.append(dict(tile=tile, source_reads=receipts,
                        result_sha256=hashlib.sha256(value.tobytes()).hexdigest(),
                        result_state='unpublished_staging', hardware_qualified=False))
                    del inputs, value
            # The retained writer performs both mirrors and addressed readback.
            engine = p.rf.get(rank)
            start = len(engine.events) if engine is not None else 0
            publication = p.publish(identity, {'data': output}, source_store_view)
            engine = p.rf[rank]
            end = len(engine.events)
            transactions = prove_sector_span(engine.events[start:end],
                model='DeepSeek', rank=rank, PC=PC, generation=generation)
            if not any(t['direction'] == 'write' for t in transactions) or any(
                    (engine.live, engine.queue, engine.calendar, engine.resident)):
                raise ValueError('actual result backing/reverse obligations retained')
            if publication['payload_sha256']['data'] != hashlib.sha256(output.tobytes()).hexdigest():
                raise ValueError('actual result publication digest differs')
            p.release_views(PC, rank, generation, lease)
            self.completed.add((PC, rank, generation))
            return dict(schema='C0_DS_EXECUTABLE_GROUP_CONTINUATION_V1',
                PC=PC, rank=rank, generation=generation,
                native_artifact_sha256=NATIVE, tiles=tiles, publication=publication,
                result_journal=dict(path=str(engine.events.path), id=engine.events.id,
                    start=start, end=end, sector_transactions=len(transactions)),
                source_lease_released=True, source_version_retired=False,
                scratch_data_bound_bytes=8704+32768,
                arithmetic_RF_bound_bytes=self.plan.report()['ordered_last_use_RF_bytes'],
                source_payload_scope='caller-retained addressed backing',
                actual_shared_port_execution=False, installed_translation=False,
                production_calls_closed=0, unknown_calls_retained=193316,
                hardware_qualified=False, full_token_qualified=False)
        except Exception:
            self.failed = True
            raise
