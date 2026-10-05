"""Immutable expected-output witness. Never computes a native family result."""
import hashlib,json
from pathlib import Path
from hbm_bound_event_journal_r30 import DiskEvents
from h3_deepseek_full_token_driver import publication_receipt

class ExpectedOutputs:
    def __init__(self,path,*,native_sha256,checkpoint_revision,generation,input_manifest_sha256,native,journal_budget):
        raw=Path(path).read_bytes();self.reference_sha256=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
        if r.get('status')!='INDEPENDENT_EXPECTED_OUTPUTS_COMMITTED':raise ValueError('independent expected outputs required')
        for name,want in dict(native_program_sha256=native_sha256,checkpoint_revision=checkpoint_revision,generation=generation,input_manifest_sha256=input_manifest_sha256).items():
            if r.get(name)!=want:raise ValueError('expected-output input/source binding '+name)
        if not r.get('reference_source_sha256'):raise ValueError('independent golden source pins required')
        self.expected={};self.seen=set();self.failed=False;self.events=DiskEvents(journal_budget)
        for row in r['outputs']:
            key=(row['PC'],row['version'],row['rank'],row['field'])
            if key in self.expected:raise ValueError('duplicate expected source output')
            self.expected[key]=row
        # Full software numerical qualification requires every source head
        # row and final selected token, not merely one selected top-k value.
        required=set()
        for op in native['instructions']:
            if op['source_op'].get('out')=='logits' or op['pc']==native['instructions'][-1]['pc']:
                for write in op['writes']:
                    for rb in op['rank_bindings']:
                        if not rb.get('empty_owned_extent'):required.add((op['pc'],write['version'],rb['rank'],'data'))
        if not required or not required<=self.expected.keys():raise ValueError('complete native logits/token expected-output coverage required')
        self.required=required
    def observe(self,identity,fields,receipt):
        if self.failed:raise ValueError('failed numerical witness; no retry')
        hashes={name:hashlib.sha256(a.tobytes()).hexdigest() for name,a in fields.items()}
        publication_receipt(receipt,identity,hashes)
        for field,array in fields.items():
            key=(identity['PC'],identity['version'],identity['rank'],field)
            if key not in self.expected:continue
            expected=self.expected[key]
            exact=(key not in self.seen and list(array.shape)==expected['shape'] and str(array.dtype)==expected['dtype'] and hashes[field]==expected['payload_sha256'])
            self.events.append(dict(event='C0_independent_expected_output_comparison',identity=identity,field=field,expected=expected,observed_shape=list(array.shape),observed_dtype=str(array.dtype),observed_payload_sha256=hashes[field],exact=exact,reference_sha256=self.reference_sha256,hardware_qualified=False))
            if not exact:
                self.failed=True;raise ValueError('actual native output differs from independently pinned expected bytes')
            self.seen.add(key)
    def finish(self):
        if self.failed or self.seen!=set(self.expected):raise ValueError('incomplete independent actual-output comparison')
        return dict(status='PASS_BYTE_EXACT_INDEPENDENT_LOGITS_AND_TOKEN',reference_sha256=self.reference_sha256,compared_outputs=len(self.seen),journal=self.events.summary(),hardware_qualified=False)

class ObservedProvider:
    def __init__(self,provider,witness):self.provider=provider;self.witness=witness
    def __getattr__(self,name):return getattr(self.provider,name)
    def publish(self,identity,fields,source_store_view):
        receipt=self.provider.publish(identity,fields,source_store_view)
        self.witness.observe(identity,fields,receipt)
        return receipt
