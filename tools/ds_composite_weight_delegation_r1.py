"""Source-preserving external delegation gate, not a V3 identity exemption.
No constructors, state conversion, handler installation, or payload execution.
"""
import copy
import gzip
import hashlib
import json
from itertools import zip_longest
from pathlib import Path
import ijson
from ijson.common import ObjectBuilder
import h3_ds_composite_weight_binding_r1 as C
import ds_producer_checkpoint_resume_v3 as V3

ROOT=C.ROOT
OUT=Path('results/uarch/ds_composite_weight_delegation_20261003')


def sha(path):
    return V3.sha(path)


def objects(path, key):
    with gzip.open(path,'rb') as stream:
        if key=='instructions':yield from ijson.items(stream,'instructions.item',use_float=True)
        else:yield from ijson.kvitems(stream,'templates',use_float=True)


def remaining_root(path):
    builder=ObjectBuilder()
    with gzip.open(path,'rb') as stream:
        for prefix,event,value in ijson.parse(stream,use_float=True):
            if prefix.split('.')[0] in ('instructions','templates'):
                continue
            if prefix=='' and event=='map_key' and value in ('instructions','templates'):
                continue
            builder.event(event,value)
    return builder.value


def canonical_file_sha(path):
    """Canonical whole-graph hash with at most one instruction/template live."""
    remaining=remaining_root(path);h=hashlib.sha256();h.update(b'{')
    for ordinal,key in enumerate(sorted(set(remaining)|{'instructions','templates'})):
        if ordinal:h.update(b',')
        h.update(C.canonical(key)+b':')
        if key=='instructions':
            h.update(b'[')
            for i,op in enumerate(objects(path,key)):
                if i:h.update(b',')
                h.update(C.canonical(op))
            h.update(b']')
        elif key=='templates':
            h.update(b'{');prior=None
            for i,(name,template) in enumerate(objects(path,key)):
                if prior is not None and name<=prior:raise ValueError('source sorted template dictionary required')
                prior=name
                if i:h.update(b',')
                h.update(C.canonical(name)+b':'+C.canonical(template))
            h.update(b'}')
        else:h.update(C.canonical(remaining[key]))
    h.update(b'}');return h.hexdigest()


def erase_home_indices(op):
    result=dict(op)
    result['writes']=[{k:v for k,v in write.items() if k!='home_indices'} for write in op['writes']]
    return result


def compare_operations(old,new):
    if erase_home_indices(old)!=erase_home_indices(new):
        raise ValueError('home binding changed source arithmetic/call identity')
    for write in new['writes']:
        indices=write.get('home_indices')
        if not isinstance(indices,list) or any(type(i)is not int or i<0 for i in indices) or len(set(indices))!=len(indices):
            raise ValueError('typed distinct captured home indices required')
    return [{'write':i,'old':a['home_indices'],'captured':b['home_indices']}
            for i,(a,b) in enumerate(zip(old['writes'],new['writes'])) if a['home_indices']!=b['home_indices']]


def stable_stamp(path):
    s=Path(path).stat()
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def source_fit(original_path,bound_path,binding,enrollment):
    original_path=Path(original_path);bound_path=Path(bound_path)
    before=[stable_stamp(p) for p in (original_path,bound_path)]
    if sha(original_path)!=enrollment['native_gzip_sha256']:
        raise ValueError('original c65 artifact identity')
    if remaining_root(original_path)!=remaining_root(bound_path):raise ValueError('native root metadata drift')
    selected=[];changed=[];pcs=0;max_object=0
    for old,new in zip_longest(objects(original_path,'instructions'),objects(bound_path,'instructions')):
        if old is None or new is None or old['pc']!=pcs or new['pc']!=pcs:raise ValueError('complete contiguous native source')
        delta=compare_operations(old,new)
        if delta:changed.append(dict(PC=pcs,changes=delta))
        if pcs in C.PCS:selected.append(new)
        max_object=max(max_object,len(C.canonical(old)),len(C.canonical(new)));pcs+=1
    if pcs!=2213:raise ValueError('complete 2213-PC source required')
    tids={r['template'] for op in selected for r in op['rank_bindings']};templates={};count=0
    for old,new in zip_longest(objects(original_path,'templates'),objects(bound_path,'templates')):
        if old is None or new is None or old!=new:raise ValueError('emitted primitive template drift')
        name,template=new;count+=1;max_object=max(max_object,len(C.canonical(template)))
        if name in tids:templates[name]=template
    original_hash=canonical_file_sha(original_path);bound_hash=canonical_file_sha(bound_path)
    if original_hash!=enrollment['native_canonical_sha256']:raise ValueError('original canonical source pin')
    if (binding['arithmetic_unchanged'] is not True or binding['original_native_sha256']!=sha(original_path)
            or binding['effective_native_content_sha256']!=bound_hash):raise ValueError('actual r41 binding report mismatch')
    if before!=[stable_stamp(p) for p in (original_path,bound_path)]:raise ValueError('source artifact changed during fit')
    adapted=copy.deepcopy(enrollment);adapted['native_canonical_sha256']=bound_hash
    for op in selected:adapted['operations'][str(op['pc'])]['operation_sha256']=C.digest(op)
    return dict(schema='DS_COMPOSITE_CAPTURED_HOME_SOURCE_FIT_R1',
        PCs=pcs,templates=count,original_gzip_sha256=sha(original_path),captured_gzip_sha256=sha(bound_path),
        original_native_canonical_sha256=original_hash,captured_native_canonical_sha256=bound_hash,
        changed_write_home_PC_count=len(changed),changed_write_home_indices=changed,
        only_captured_write_home_indices_changed=True,primitive_templates_byte_identity=True,
        original_constructor_and_MRO_transfer=False,maximum_streamed_object_JSON_bytes=max_object,
        checkpoint_or_payload_admission=False),dict(instructions=selected,templates=templates),adapted


def delegation_policy(source_fit_record,enrollment_sha256,handler_sha256):
    if source_fit_record.get('only_captured_write_home_indices_changed') is not True:
        raise ValueError('complete captured home source-fit prerequisite')
    return dict(schema='DS_EXTERNAL_COMPOSITE_DELEGATION_POLICY_R1',
        native_sha256=source_fit_record['captured_native_canonical_sha256'],
        original_enrollment_sha256=enrollment_sha256,handler_sha256=handler_sha256,
        delegated_PCs=list(C.PCS),delegated_operand='weight',state_owner='original_restored_provider_and_engine',
        checkpoint_migration='NONE; no state/identity rewrite or provider/engine class replacement',
        mutation_policy='no __class__, class/instance method patch, manifest mutation, provider wrapping or private-state clone',
        scope='future exact composite weight read only; every earlier PC executes in original order once',
        payload_reads_admitted=False,controller_source_sha256=None)


def verify_owner_binding(policy, *, captured_identity,restored_identity,checkpoint_receipt,restore_receipt):
    """Pure metadata counterpart of the actual V3 re-verification below."""
    if not checkpoint_receipt or not restore_receipt:raise ValueError('actual sealed checkpoint and exact V3 restore receipts required')
    if V3.data_identity(captured_identity)!=V3.data_identity(restored_identity):
        raise ValueError('original V3 source/class/data identity must remain exact')
    if restored_identity.get('native_sha256')!=policy['native_sha256']:
        raise ValueError('delegation source must be actual captured home-bound native')
    unsigned={k:v for k,v in restore_receipt.items() if k!='seal_sha256'}
    if C.digest(unsigned)!=restore_receipt.get('seal_sha256'):raise ValueError('exact V3 restore receipt seal')
    if (restore_receipt.get('schema')!='DS_RESTORED_RUN_SCOPE_RECEIPT_V1'
            or restore_receipt['producer_checkpoint_receipt']!=checkpoint_receipt
            or restore_receipt['old_identity']!=captured_identity
            or restore_receipt['new_identity']!=restored_identity):raise ValueError('exact V3 owner/producer receipt binding')
    retired=restore_receipt['retired']
    if retired!=list(range(11)) or any(type(pc)is not int for pc in retired):
        raise ValueError('actual PC10 retired boundary required; never replay prefix')
    return dict(schema='DS_EXTERNAL_DELEGATION_OWNER_GATE_R1',original_source_identity=restored_identity,
        producer_checkpoint_receipt=checkpoint_receipt,restore_receipt_sha256=C.digest(restore_receipt),
        next_PC=11,delegated_PCs=list(C.PCS),class_and_MRO_unchanged=True,
        state_or_checkpoint_payload_copies=0,handler_payload_or_controller_admitted=False)


def verify_restored_owner(checkpoint, *, source_contract,checkpoint_receipt,provider,engine,policy,restore_receipt_path):
    """Actual gate: invoke unchanged V3 checks, never accept a caller's PASS bit.
    This remains unexecuted until Kepler has the actual checkpoint and resource GO.
    """
    expected_helper=C.load_enrollment()[0]['source_sha256']['tools/ds_producer_checkpoint_resume_v3.py']
    if sha(V3.__file__)!=expected_helper:raise ValueError('original V3 helper source pin')
    p=V3.unwrap(provider)
    receipt=json.loads(Path(restore_receipt_path).read_bytes())
    current=V3.identity(p,engine)
    metadata_gate=verify_owner_binding(policy,captured_identity=source_contract['identity'],
        restored_identity=current,checkpoint_receipt=checkpoint_receipt,restore_receipt=receipt)
    transition=receipt.get('explicit_transition')
    contract=dict(identity=current,checkpoint_receipt=checkpoint_receipt)
    if transition is not None:contract.update(run_scope_transition=transition,run_scope=V3.run_scope(p))
    # Same exact original source-contract and source/class checks as every restore.
    verified=V3.verify_checkpoint(checkpoint,source_contract=source_contract,next_pc=11,constructor_contract=contract)
    if (not getattr(engine,'_verified_checkpoint_resume',False) or engine.provider is not provider
            or engine.retired!=set(range(11))):raise ValueError('actual original verified PC10 restore required')
    V3.quiescent(provider,engine);V3.validate_backing(p);V3.verify_inputs(p)
    V3.verify_shards(json.loads((Path(checkpoint)/'state.json').read_bytes())['opened_checkpoint_shards'])
    actual_path=p.journal_budget.root/'checkpoint_restore_scope.json'
    if Path(restore_receipt_path).resolve()!=actual_path.resolve():raise ValueError('actual original restore journal receipt path')
    if receipt['new_run_scope']!=V3.run_scope(p):raise ValueError('actual restored run scope')
    if policy['payload_reads_admitted'] is not False or policy['controller_source_sha256'] is not None:
        raise ValueError('this gate admits owner metadata only, not payload/controller')
    metadata_gate.update(original_checkpoint_state_sha256=verified['receipt']['producer_seal']['state_sha256'],
        original_checkpoint_payload_sha256=verified['receipt']['producer_seal']['payload_sha256'],
        historical_journal_inventory_preserved=True,actual_owner_verification=True)
    return metadata_gate
