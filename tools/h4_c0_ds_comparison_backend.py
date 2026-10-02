"""Default-off Kepler publication backend for explicitly reviewed new references.

Pinned e10 loader/witness stay byte-identical. This observes an existing actual
publication, not operand acquisition or a new native execution path.
"""
import hashlib
import inspect
from pathlib import Path
import numpy as np
from h4_c0_ds_stage_witness import StageWitness,ObservedStage,input_identity,required_outputs
from h4_c0_ds_fullgraph_inventory import NATIVE,load,sha
from h4_c0_ds_runtime_bindings import canonical
from h3_deepseek_full_token_driver import publication_receipt
from hbm_bound_event_journal_r30 import DiskEvents


class ReviewedReferenceWitness(StageWitness):
    def __init__(self,*,reviewed_contracts,reference_input_manifest,provider,native,
                 first_PC,last_PC,reviewed_native_content_sha256):
        original=load(reference_input_manifest);actual=provider.manifest
        if input_identity(original)!=input_identity(actual):raise ValueError('exact actual entering-state source identity')
        digest=hashlib.sha256(canonical(native)).hexdigest()
        if digest!=reviewed_native_content_sha256 or len(digest)!=64:raise ValueError('explicit reviewed current bound source required')
        self.native=native;self.native_content_sha256=digest;self.first=first_PC;self.last=last_PC
        self._op_pins={o['pc']:hashlib.sha256(canonical(o)).hexdigest() for o in native['instructions']}
        self._template_pins={k:hashlib.sha256(canonical(t)).hexdigest() for k,t in native['templates'].items()}
        self.required=required_outputs(native,first_PC,last_PC);self.expected={};self.refs={}
        self.generation=actual['generation'];self.seen=set();self.failed=False
        self.unobserved_nonpublication_PCs={o['pc'] for o in native['instructions'][first_PC:last_PC+1] if not o['writes']}
        for path,reviewed_sha in reviewed_contracts.items():
            path=Path(path)
            if sha(path)!=reviewed_sha:raise ValueError('explicit reviewed comparison contract bytes')
            c=load(path)
            if c.get('native_program_sha256')!=NATIVE or c.get('golden_stimuli_in_executor') is not False:
                raise ValueError('independent comparison-only canonical reference')
            if c['input_manifest_sha256']!=sha(reference_input_manifest):raise ValueError('exact reference entering source manifest')
            if 'checkpoint_revision' in c and c['checkpoint_revision']!=actual['checkpoint_revision']:
                raise ValueError('reference released checkpoint revision')
            for source,h in c['reference_source_sha256'].items():
                if sha(source)!=h:raise ValueError('independent arithmetic/source closure changed')
            self.refs[str(path.resolve())]=reviewed_sha
            for row in c['expectations']:
                k=(row['PC'],row['version'],row['rank'],row['field'])
                if k not in self.required:continue
                if k in self.expected:raise ValueError('duplicate independent witness identity')
                p=path.parent/row['path']
                if sha(p)!=row['file_sha256']:raise ValueError('comparison payload file changed')
                a=np.load(p,allow_pickle=False)
                if list(a.shape)!=row['shape'] or a.dtype.str!=row['dtype'] or hashlib.sha256(a.tobytes()).hexdigest()!=row['payload_sha256']:
                    raise ValueError('comparison payload shape/dtype/bytes')
                if row['generation']!=self.generation:raise ValueError('exact independent source generation')
                self.expected[k]=dict(row,reference_sha256=reviewed_sha)
        if not self.required or self.required!=self.expected.keys():raise ValueError('complete scoped independent reference rank/field coverage')
        self.events=DiskEvents(provider.journal_budget)
    def observe(self,identity,fields,receipt):
        if self.failed:raise ValueError('failed independent stage witness; no retry')
        if not self.first<=identity['PC']<=self.last:return
        try:
            if identity['generation']!=self.generation:raise ValueError('actual source generation')
            op=self.native['instructions'][identity['PC']]
            if hashlib.sha256(canonical(op)).hexdigest()!=self._op_pins[identity['PC']]:raise ValueError('actual instruction source mutated')
            rank=next(r for r in op['rank_bindings'] if r['rank']==identity['rank'])
            templates={rank['template'],*[b['template'] for b in rank.get('buffer_programs',[])]}
            for key in templates:
                if hashlib.sha256(canonical(self.native['templates'][key])).hexdigest()!=self._template_pins[key]:raise ValueError('actual template source mutated')
            writer=next(w for w in op['writes'] if w['version']==identity['version'])
            hashes={k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in fields.items()}
            publication_receipt(receipt,identity,hashes)
            want_fields={'data',*op.get('compound_output_fields',{}).get(writer['native_result_binding']['result'],[])}
            if set(fields)!=want_fields:raise ValueError('complete actual compound field set required')
            for field,array in fields.items():
                key=(identity['PC'],identity['version'],identity['rank'],field);expected=self.expected[key]
                exact=(key not in self.seen and list(array.shape)==expected['shape'] and array.dtype.str==expected['dtype'] and hashes[field]==expected['payload_sha256'])
                self.events.append(dict(event='C0_independent_stage_publication_comparison',identity=identity,field=field,exact=exact,
                    expected_payload_sha256=expected['payload_sha256'],observed_payload_sha256=hashes[field],
                    reference_sha256=expected['reference_sha256'],hardware_qualified=False))
                if not exact:raise ValueError('independent stage output byte/shape/codec mismatch')
                self.seen.add(key)
        except Exception:
            self.failed=True;raise
    def finish(self):
        if hashlib.sha256(canonical(self.native)).hexdigest()!=self.native_content_sha256:
            self.failed=True;raise ValueError('actual complete source mutated')
        if self.unobserved_nonpublication_PCs:
            raise ValueError('actual selected descriptor/acquisition witness missing for PCs '+str(sorted(self.unobserved_nonpublication_PCs)))
        return super().finish()


def bind_comparison(provider,*,enabled=False,**reviewed):
    """Call only while constructing a fresh owner engine; default returns identity."""
    if not enabled:return provider,None
    if 'witness' in getattr(provider,'__dict__',{}):
        raise ValueError('do not nest an old prefix observer; use explicit Kepler continuation multiplexing')
    witness=ReviewedReferenceWitness(provider=provider,**reviewed)
    return ObservedStage(provider,witness),witness


def bind_kepler_continuation(observed,*,enabled=False,**reviewed):
    """Fresh R50 owner adapter: same publisher once, old and new exact scopes.

    Defaults to the exact existing object. This does not relax the owner's
    checkpoint serializer, resume admission, state pins or execution scope.
    """
    if not enabled:return observed,None
    source=Path(inspect.getmodule(type(observed)).__file__)
    if sha(source)!='c1068f2e82ff8fb0b6ad4677eaadbbb28351e03631142bf05f850d577a38de74' or type(observed).__name__!='Observed':
        raise ValueError('exact current Kepler R42/R50 publication wrapper source required')
    base=observed.provider;prefix=observed.witness
    if prefix.provider is not base:raise ValueError('same actual provider instance required')
    continuation=ReviewedReferenceWitness(provider=base,**reviewed)
    prefix_PCs={k[0] for k in prefix.expected}
    if any(continuation.first<=pc<=continuation.last for pc in prefix_PCs):raise ValueError('disjoint reviewed publication scopes required')
    class Multiplexed:
        def __getattr__(self,name):return getattr(prefix,name)
        def observe(self,identity,fields,receipt):
            pc=identity['PC']
            if pc in prefix_PCs:return prefix.observe(identity,fields,receipt)
            if continuation.first<=pc<=continuation.last:return continuation.observe(identity,fields,receipt)
            raise ValueError('actual publication outside explicitly reviewed numerical scopes')
        def finish(self):
            return dict(prefix=prefix.finish(),continuation=continuation.finish(),hardware_qualified=False,full_token_qualified=False)
    # Preserve the real existing wrapper class and its original publish method.
    return type(observed)(base,Multiplexed()),continuation
