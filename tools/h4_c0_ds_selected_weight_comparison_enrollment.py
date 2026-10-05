"""Default-off immutable selected-weight comparison, never a source provider.

Controller enrollment must bind this file/bit proof SHA separately. It neither
constructs a provider nor bypasses payload/class/resource admission. Refusal is
terminal for this comparison instance; actual matrix publications have their
own independent StageWitness contract.
"""
import json
from pathlib import Path
from h4_c0_ds_selected_bf16_payload_witness import sha,compare_selected_weight

class SelectedWeightComparisons:
    def __init__(self,proof_path,*,reviewed_proof_sha256):
        if sha(proof_path)!=reviewed_proof_sha256:raise ValueError('reviewed selected-weight bit proof SHA')
        rows=json.loads(Path(proof_path).read_text())
        self.proofs={}
        for row in rows:
            p=row['plan'];key=(p['PC'],p['rank'],p['template'])
            if key in self.proofs:raise ValueError('duplicate selected source call identity')
            self.proofs[key]=row
        if len(self.proofs)!=288 or {k[0] for k in self.proofs}!={115,443,776}:
            raise ValueError('all288 selected source calls required')
        self.reference_sha256=reviewed_proof_sha256;self.seen=set();self.failed=False
    def observe(self,exact_plan,actual_weight_result):
        if self.failed:raise ValueError('failed selected source comparison; no retry')
        try:
            key=(exact_plan['PC'],exact_plan['rank'],exact_plan['template'])
            if key in self.seen or key not in self.proofs:raise ValueError('unknown or duplicate actual selected call')
            result=compare_selected_weight(self.proofs[key],exact_plan,actual_weight_result)
            self.seen.add(key);return dict(result,reference_sha256=self.reference_sha256)
        except Exception:self.failed=True;raise
    def finish(self):
        if self.failed or self.seen!=set(self.proofs):raise ValueError('incomplete or failed selected source comparison')
        return dict(status='PASS_ALL288_ACTUAL_SELECTED_SOURCE_WEIGHT_BITS',calls=len(self.seen),
                    reference_sha256=self.reference_sha256,matrix_arithmetic_qualified=False,
                    V3_source_identity_not_admitted_by_comparison=True,hardware_qualified=False)
