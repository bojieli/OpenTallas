"""Default-off atomic publication around immutable V3 capture.

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


def verify_payload(root,receipt):
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
        files=verify_payload(staging,receipt)
        publication=dict(schema='DS_ACTUAL_ATOMIC_CHECKPOINT_R66',boundary_pc=boundary_pc,
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


def require_fresh_restore(publication,*,current_pid):
    if type(current_pid)is not int or current_pid==publication['producer_pid']:
        raise ValueError('restore requires a distinct cold process')
    root=Path(publication['destination'])
    if json.loads((root/'ATOMIC_COMPLETE.json').read_bytes())!=publication:
        raise ValueError('exact atomic publication receipt required')
    return verify_payload(root,publication['producer_receipt'])
