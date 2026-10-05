"""Exact prefix digest witness; independent reference never feeds arithmetic."""
import hashlib,json
from pathlib import Path
import numpy as np
from hbm_bound_event_journal_r30 import DiskEvents
from h3_ds_connected_provider_r37 import D
REFERENCE_SHA='91c803a93df18e011cd7ee6c5e0a84c8fc091136718ca329e5f2928349b3f342'
class Witness:
    def __init__(self,provider,original_native,reference):
        self.provider=provider;self.events=DiskEvents(provider.journal_budget);self.seen=set();self.expected={};self.failed=False
        raw=Path(reference).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=REFERENCE_SHA:raise ValueError('exact independently committed prefix reference')
        self.reference=json.loads(raw)
        baseline_path=Path(__file__).resolve().parents[1]/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/failed_prefix_r39/actual_manifest.json.gz'
        import gzip
        baseline_raw=baseline_path.read_bytes();baseline=json.loads(gzip.decompress(baseline_raw))
        if hashlib.sha256(baseline_raw).hexdigest()!=self.reference['input_manifest_sha256']:raise ValueError('independent input manifest provenance')
        for name in ('checkpoint_path','checkpoint_revision','checkpoint_index_sha256','checkpoint_initial_embedding','initial_versions','view_bindings','history_images','history_source_receipt','query_field_homes'):
            if baseline[name]!=provider.manifest[name]:raise ValueError('reference input source changed '+name)
        if self.reference['native_program_sha256']!=provider.manifest['native_program_sha256'] or self.reference['checkpoint_revision']!=provider.revision:raise ValueError('reference native/checkpoint identity')
        for row in self.reference['expectations']:
            k=(row['PC'],row['version'],row['rank'],row['generation'],row['field'])
            if k in self.expected:raise ValueError('duplicate reference identity')
            self.expected[k]=row
        pc0=json.loads((D/'inputs/parent_PC0_independent_golden.json').read_bytes())
        for w in original_native['instructions'][0]['writes']:
            name=w['native_result_binding']['result'];r=pc0['results'][name]
            for rank in range(96):
                k=(0,w['version'],rank,provider.generation,'data')
                indices=[i for i in w['home_indices'] if rank in provider.homes[i]['rank_group']]
                self.expected[k]=dict(PC=0,version=w['version'],rank=rank,generation=provider.generation,field='data',home_indices=indices,shape=r['shape'],dtype='<f4',payload_sha256=r['golden_sha256'],independent_PC0_rank_invariant_source=True)
        required=set()
        for op in original_native['instructions'][:10]:
            for owned in op['rank_bindings']:
                if owned.get('empty_owned_extent'):continue
                for w in op['writes']:
                    required.add((op['pc'],w['version'],owned['rank'],provider.generation,'data'))
        if required!=set(self.expected):raise ValueError('complete exact prefix output coverage')
        self.original_native=original_native
    def observe(self,identity,fields,receipt):
        from h3_ds_connected_provider_r37 import peer
        if self.failed:raise ValueError('failed numerical witness; no retry')
        hashes={f:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() for f,a in fields.items()}
        peer('h3_deepseek_full_token_driver').publication_receipt(receipt,identity,hashes)
        for f,a in fields.items():
            k=(identity['PC'],identity['version'],identity['rank'],identity['generation'],f)
            row=self.expected.get(k)
            if row is None or k in self.seen:
                self.failed=True;raise ValueError('missing or duplicate exact observed output key')
            original_w=next(w for w in self.original_native['instructions'][identity['PC']]['writes'] if w['version']==identity['version'])
            original_indices=[i for i in original_w['home_indices'] if identity['rank'] in self.provider.homes[i]['rank_group']]
            if original_indices!=row['home_indices']:
                self.failed=True;raise ValueError('independent source original home identity')
            bound_w=next(w for w in self.provider.native['instructions'][identity['PC']]['writes'] if w['version']==identity['version'])
            allocated=[i for i in bound_w['home_indices'] if identity['rank'] in self.provider.homes[i]['rank_group']]
            exact=(allocated==identity['home_indices'] and list(a.shape)==row['shape'] and a.dtype.str==row['dtype'] and hashes[f]==row['payload_sha256'])
            self.events.append(dict(event='DS_r41_complete_observed_output',identity=identity,field=f,shape=list(a.shape),dtype=a.dtype.str,payload_sha256=hashes[f],original_reference_home_indices=original_indices,allocated_home_records=[self.provider.homes[i] for i in allocated],byte_exact=exact,reference_sha256=REFERENCE_SHA,hardware_qualified=False))
            if not exact:self.failed=True;raise ValueError('actual prefix differs from independent golden shape/dtype/home/bytes')
            self.seen.add(k)
    def finish(self):
        if self.failed or self.seen!=set(self.expected):raise ValueError('incomplete prefix comparison')
        return dict(status='PASS_BYTE_EXACT_COMPLETE_PREFIX_OUTPUTS',outputs=len(self.seen),reference_sha256=REFERENCE_SHA,journal=self.events.summary(),full_token_qualified=False,hardware_qualified=False)
class Observed:
    def __init__(self,provider,witness):self.provider=provider;self.witness=witness
    def __getattr__(self,name):return getattr(self.provider,name)
    def publish(self,identity,fields,view):
        receipt=self.provider.publish(identity,fields,view);self.witness.observe(identity,fields,receipt);return receipt


def comparison_journal_cost(native,homes):
    """Price complete observable output records, including every allocated home."""
    raw=Path(__file__).resolve().parents[1]/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json'
    ref=json.loads(raw.read_bytes());rows=ref['expectations'];total=0;maximum=0;count=0
    expected={(r['PC'],r['version'],r['rank'],r['generation'],r['field']):r for r in rows}
    for op in native['instructions'][:10]:
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            rank=owned['rank']
            for w in op['writes']:
                indices=[i for i in w['home_indices'] if rank in homes[i]['rank_group']]
                row=expected.get((op['pc'],w['version'],rank,1,'data'),{})
                event=dict(event='DS_r41_complete_observed_output',identity=dict(PC=op['pc'],rank=rank,generation=1,version=w['version'],home_indices=indices),field='data',shape=row.get('shape',[4,5120]),dtype='<f4',payload_sha256='f'*64,original_reference_home_indices=row.get('home_indices',indices),allocated_home_records=[homes[i] for i in indices],byte_exact=True,reference_sha256=REFERENCE_SHA,hardware_qualified=False)
                size=len(json.dumps(event,sort_keys=True,separators=(',',':')).encode());maximum=max(maximum,size);total+=8*(size+64);count+=1
    return dict(outputs=count,max_serialized_record_bytes=maximum,additional_page_index_reservation_bytes=total,scope='complete output observation/comparison journal, actual fixed source identities and allocated home records')
