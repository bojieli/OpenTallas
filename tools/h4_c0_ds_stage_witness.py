"""Actual publication witness for explicitly bounded PC scopes, never an input.

Independent references are loaded only here. Executor/provider acquisition never
receives expected bytes. Complete declared scope and compound fields are required;
missing references refuse qualification without blocking unreferenced execution.
"""
import hashlib
import json
from pathlib import Path
from h3_deepseek_full_token_driver import publication_receipt
from hbm_bound_event_journal_r30 import DiskEvents
from h4_c0_ds_fullgraph_inventory import NATIVE,references,sha,load
from h4_c0_ds_runtime_bindings import canonical

SOURCE_KEYS = ('checkpoint_path','checkpoint_revision','checkpoint_index_sha256','generation',
    'native_program_sha256','source_dispatch_sha256','checkpoint_initial_embedding',
    'initial_versions','view_bindings','query_field_homes','history_images',
    'history_source_receipt','persistent_fragment_extent','source_manifest_provenance','source_state_scope')


def input_identity(manifest):
    if any(k not in manifest for k in SOURCE_KEYS):raise ValueError('complete source input identity required')
    return hashlib.sha256(canonical({k:manifest[k] for k in SOURCE_KEYS})).hexdigest()


def required_outputs(native,first,last):
    if type(first)!=int or type(last)!=int or not 0<=first<=last<len(native['instructions']):
        raise ValueError('exact inclusive source PC scope')
    needed=set()
    for op in native['instructions'][first:last+1]:
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            for w in op['writes']:
                for field in ['data']+op.get('compound_output_fields',{}).get(w['native_result_binding']['result'],[]):
                    needed.add((op['pc'],w['version'],owned['rank'],field))
    return needed


class StageWitness:
    def __init__(self,reference_paths,*,reference_input_manifest,actual_input_manifest,
                 native,first_PC,last_PC,journal_budget):
        original=load(reference_input_manifest)
        if input_identity(original)!=input_identity(actual_input_manifest):
            raise ValueError('actual stage entering checkpoint/source state changed')
        self.native=native;self.first=first_PC;self.last=last_PC
        self.required=required_outputs(native,first_PC,last_PC)
        rows,pins=references(reference_paths,NATIVE)
        if not self.required or not self.required<=rows.keys():
            raise ValueError('independent witness does not cover every rank/field in this scope')
        self.expected={k:rows[k] for k in self.required};self.refs=pins
        for path in reference_paths:
            c=load(path)
            if c['input_manifest_sha256']!=sha(reference_input_manifest) or c['checkpoint_revision']!=actual_input_manifest['checkpoint_revision']:
                raise ValueError('exact independent entering input manifest binding')
        self.generation=actual_input_manifest['generation'];self.seen=set();self.failed=False
        self.native_content_sha256=hashlib.sha256(canonical(native)).hexdigest()
        if self.native_content_sha256 not in ('9d538b80f1e8d3eada8ed4c967426bab5649339ff6fa2f0535eb393f7b15145d',):
            # No inferred native change admission: require explicit reviewed bound source.
            raise ValueError('reviewed effective source-home native required')
        self.events=DiskEvents(journal_budget)
    def observe(self,identity,fields,receipt):
        if self.failed:raise ValueError('failed independent stage witness; no retry')
        if not self.first<=identity['PC']<=self.last:return
        try:
            if hashlib.sha256(canonical(self.native)).hexdigest()!=self.native_content_sha256:
                raise ValueError('actual source mutated')
            if identity['generation']!=self.generation:raise ValueError('actual source generation')
            op=self.native['instructions'][identity['PC']]
            writer=next(w for w in op['writes'] if w['version']==identity['version'])
            hashes={k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in fields.items()}
            publication_receipt(receipt,identity,hashes)
            want_fields={'data',*op.get('compound_output_fields',{}).get(writer['native_result_binding']['result'],[])}
            if set(fields)!=want_fields:raise ValueError('complete actual compound field set required')
            for field,array in fields.items():
                key=(identity['PC'],identity['version'],identity['rank'],field)
                expected=self.expected[key]
                exact=(key not in self.seen and list(array.shape)==expected['shape'] and
                    array.dtype.str==expected['dtype'] and hashes[field]==expected['payload_sha256'])
                self.events.append(dict(event='C0_independent_stage_publication_comparison',identity=identity,
                    field=field,exact=exact,expected_payload_sha256=expected['payload_sha256'],
                    observed_payload_sha256=hashes[field],reference_sha256=expected['reference_sha256'],hardware_qualified=False))
                if not exact:raise ValueError('independent stage output byte/shape/codec mismatch')
                self.seen.add(key)
        except Exception:
            self.failed=True;raise
    def finish(self):
        if self.failed or self.seen!=self.required:raise ValueError('incomplete or failed source scope comparison')
        return dict(status='PASS_INDEPENDENT_SOURCE_PC_SCOPE_EXACT',first_PC=self.first,last_PC=self.last,
            output_fields_compared=len(self.seen),reference_contract_pins=self.refs,
            native_content_sha256=self.native_content_sha256,journal=self.events.summary(),
            provider_operand_acquisition_not_proven_by_witness=True,full_token_qualified=False,hardware_qualified=False)


class ObservedStage:
    def __init__(self,provider,witness):self.provider=provider;self.witness=witness
    def __getattr__(self,name):return getattr(self.provider,name)
    def publish(self,identity,fields,source_store_view):
        receipt=self.provider.publish(identity,fields,source_store_view)
        self.witness.observe(identity,fields,receipt)
        return receipt
