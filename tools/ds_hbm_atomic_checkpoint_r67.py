"""Default-off atomic publication with exact retired boundary around immutable V3 capture.

This helper does not execute a native PC or grant numerical admission. A sealed
producer must exit; subsequent execution uses a fresh process/journal. Failed
staging directories and their failure receipts remain evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import uuid

V3_SHA256='e323ce55e837e32418a74ae271897357952780681a5161205d8a12498060321e'
FILES=('payload.bin','state.json','COMPLETE.json','actual_observations.json','RUNNER_COMPLETE.json')


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):digest.update(block)
    return digest.hexdigest()


def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(',',':')).encode()


def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def durable_json(path,value):
    with Path(path).open('xb') as f:
        f.write(canonical(value));f.flush();os.fsync(f.fileno())


def verify_payload(root,receipt,*,boundary_pc=None):
    """Verify actual serialized data and observations, never witness as payload."""
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('real checkpoint directory required')
    for name in FILES:
        p=root/name
        if p.is_symlink() or not p.is_file():raise ValueError('regular complete checkpoint file required: '+name)
    runner=json.loads((root/'RUNNER_COMPLETE.json').read_bytes())
    if runner!=receipt:raise ValueError('external producer receipt mismatch')
    seal=receipt['producer_seal']
    for name,key in [('state.json','state_sha256'),('payload.bin','payload_sha256')]:
        if sha(root/name)!=seal[key]:raise ValueError('actual payload/state checksum mismatch')
    if json.loads((root/'COMPLETE.json').read_bytes())!=seal:
        raise ValueError('complete seal mismatch')
    if sha(root/'actual_observations.json')!=receipt['actual_observations_sha256']:
        raise ValueError('actual observations checksum mismatch')
    closure=json.loads((root/'state.json').read_bytes())
    if closure['payload_sha256']!=seal['payload_sha256'] or closure['payload_bytes']!=(root/'payload.bin').stat().st_size:
        raise ValueError('closure payload identity mismatch')
    if boundary_pc is not None:
        actual=json.loads((root/'actual_observations.json').read_bytes())
        if type(boundary_pc)is not int or type(actual.get('boundary_pc'))is not int or actual['boundary_pc']!=boundary_pc:
            raise ValueError('actual checkpoint boundary mismatch')
        expected=list(range(boundary_pc+1))
        projection=actual.get('projection',{})
        inventory=closure.get('inventory',{})
        if projection.get('retired_PCs')!=expected or inventory.get('retired_PCs')!=expected:
            raise ValueError('projected/actual retired prefix mismatch')
        state=closure.get('state',{})
        if set(state)!={'dict'}:raise ValueError('exact V3 typed state required')
        entries=state['dict']
        retired=[value for key,value in entries if key=='retired']
        if len(retired)!=1 or set(retired[0])!={'set'} or sorted(retired[0]['set'])!=expected or len(retired[0]['set'])!=len(expected):
            raise ValueError('serialized actual retired prefix mismatch')
        if closure.get('schema')!='DS_ACTUAL_PRODUCER_QUIESCENT_RESUME_V3' or receipt['producer_seal'].get('schema')!=closure['schema']:
            raise ValueError('exact V3 quiescent state schema required')
        identity=actual.get('source_contract',{}).get('identity')
        if not identity or identity!=closure.get('identity') or identity.get('helper_sha256')!=V3_SHA256:
            raise ValueError('source-bound quiescent capture identity mismatch')
        if projection.get('same_home_restore') is not True or inventory.get('same_home_restore') is not True:
            raise ValueError('actual same-home projection required')
    return {name:dict(bytes=(root/name).stat().st_size,sha256=sha(root/name)) for name in FILES}


def publish(staging,destination,receipt,*,boundary_pc):
    """Same-filesystem directory rename after checksums and durable completion.

    Both paths are caller-owned fresh siblings. Lock serializes cooperating
    publishers; output root is private to this run. No checkpoint is overwritten.
    """
    staging=Path(staging);destination=Path(destination)
    if staging.parent.resolve()!=destination.parent.resolve() or staging==destination:
        raise ValueError('fresh sibling staging/final paths required')
    if type(boundary_pc)is not int or boundary_pc<0:raise ValueError('typed retired PC required')
    lock=destination.parent/('.'+destination.name+'.publish-lock')
    fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        os.fsync(fd);sync_dir(lock.parent)
        if destination.exists() or destination.is_symlink():raise ValueError('checkpoint destination already exists')
        files=verify_payload(staging,receipt,boundary_pc=boundary_pc)
        publication=dict(schema='DS_ACTUAL_ATOMIC_CHECKPOINT_R67',boundary_pc=boundary_pc,
            producer_pid=os.getpid(),destination=str(destination.resolve()),files=files,
            producer_receipt=receipt,requires_fresh_process_restore=True)
        durable_json(staging/'ATOMIC_COMPLETE.json',publication)
        sync_dir(staging)
        os.rename(staging,destination)
        sync_dir(destination.parent)
        return publication
    finally:
        os.close(fd)
        lock.unlink();sync_dir(lock.parent)


def capture_atomic(helper,engine,provider,witness,*,boundary_pc,destination,source_contract,enabled=False):
    if enabled is not True:raise ValueError('atomic capture is default off')
    if sha(helper.__file__)!=V3_SHA256:raise ValueError('exact original V3 source required')
    destination=Path(destination)
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError('fresh absolute checkpoint destination required')
    # V3 refuses nonquiescent ownership and all live debts before writing. It
    # saves actual cached arrays and RF/state/shared backing plus generation,
    # port ownership, serial counters and compact lifecycle watermarks.
    staging=destination.parent/('.'+destination.name+'.pending-'+uuid.uuid4().hex)
    try:
        receipt=helper.capture_quiescent(engine,provider,witness,boundary_pc=boundary_pc,
            destination=staging,source_contract=source_contract)
        publication=publish(staging,destination,receipt,boundary_pc=boundary_pc)
        return dict(checkpoint_receipt=receipt,publication=publication)
    except BaseException as exc:
        # Do not delete incomplete or sealed staging data. The final checkpoint
        # is absent until atomic publication succeeds.
        if staging.exists() and not (staging/'ATOMIC_FAILURE.json').exists():
            durable_json(staging/'ATOMIC_FAILURE.json',dict(exception_type=type(exc).__name__,reason=str(exc)))
            sync_dir(staging)
        raise


def require_fresh_restore(publication,*,current_pid=None):
    actual_pid=os.getpid()
    if current_pid is not None and (type(current_pid)is not int or current_pid!=actual_pid):
        raise ValueError('caller PID differs from actual process PID')
    if actual_pid==publication['producer_pid']:
        raise ValueError('restore requires a distinct cold process')
    root=Path(publication['destination'])
    if json.loads((root/'ATOMIC_COMPLETE.json').read_bytes())!=publication:
        raise ValueError('exact atomic publication receipt required')
    return verify_payload(root,publication['producer_receipt'],boundary_pc=publication['boundary_pc'])
