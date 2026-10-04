"""Default-off R69 capture selection. Original V3 project/restore remain exact.

The stream helper replaces save only. Project, atomic JSON parsing and cold
restore retain their allocations and guards; this module does not admit a run.
"""
import os
from pathlib import Path
import uuid

import ds_hbm_atomic_checkpoint_r67 as atomic
import ds_checkpoint_streamed_state_r2 as stream

STREAM_SHA = '9c6cf76363ce0f95a2794c1afeda755aeb8119c6313f57eaa07c020f6492fcbb'

def selection(base):
    stream.require_source(base)
    if atomic.sha(stream.__file__) != STREAM_SHA:
        raise ValueError('exact parent-reviewed R2 stream source required')
    # The source pin is generated into the successor contract, never hidden
    # behind the original V3 helper identity.
    return dict(schema='DS_STREAMED_SAVE_SELECTION_R69',
                original_V3_sha256=atomic.sha(base.__file__),
                stream_helper_sha256=atomic.sha(stream.__file__),
                boundary_helper_sha256=atomic.sha(Path(__file__)),
                projection='original_V3_project_checkpoint',
                save='source_exact_streamed_two_pass',
                publication='original_R67_publish',
                restore='original_V3_verify_and_restore')

def project_checkpoint(base, engine, provider, witness, *, boundary_pc, destination,
                       source_contract, enabled=False):
    if enabled is not True:
        raise ValueError('R69 streamed checkpoint selection is default off')
    if source_contract.get('checkpoint_selection') != selection(base):
        raise ValueError('exact streamed capture source contract required')
    # No callback replacement or mutation of the pinned V3 module. This phase
    # still builds its encoded tree; its exact positive allocation is retained.
    projection = base.project_checkpoint(engine, provider, witness,
        boundary_pc=boundary_pc, destination=destination)
    extension = len(base.canonical(source_contract))
    projection['metadata_bytes_upper'] += extension
    projection['filesystem_reservation_bytes'] += extension
    if os.statvfs(Path(destination).parent).f_bavail * os.statvfs(Path(destination).parent).f_frsize < projection['filesystem_reservation_bytes']:
        raise ValueError('checkpoint aggregate metadata disk headroom')
    return projection

def capture_atomic(base, engine, provider, witness, *, boundary_pc, destination,
                   source_contract, enabled=False):
    if enabled is not True:
        raise ValueError('R69 streamed capture is default off')
    if atomic.sha(base.__file__) != atomic.V3_SHA256:
        raise ValueError('exact original V3 source required')
    destination = Path(destination)
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError('fresh absolute checkpoint destination required')
    projection = project_checkpoint(base, engine, provider, witness,
        boundary_pc=boundary_pc, destination=destination,
        source_contract=source_contract, enabled=True)
    p = base.unwrap(provider)
    if source_contract.get('identity') != base.identity(p, engine):
        raise ValueError('explicit exact capture source contract')
    staging = destination.parent / ('.' + destination.name + '.pending-' + uuid.uuid4().hex)
    try:
        saved = stream.save_streamed(base, provider, engine, staging, enabled=True)
        seal = saved['producer_seal']
        actual = dict(seen=[list(k) for k in sorted(witness.seen)],
            initialization_provenance=witness.initialization_provenance,
            observation_journal=witness.events.summary(), source_contract=source_contract,
            boundary_pc=boundary_pc, projection=projection, producer_seal=seal,
            run_scope=base.run_scope(p), scope_role_proof=base.scope_role_proof(p, engine))
        atomic.durable_json(staging / 'actual_observations.json', actual)
        receipt = dict(producer_seal=seal,
                       actual_observations_sha256=atomic.sha(staging / 'actual_observations.json'))
        atomic.durable_json(staging / 'RUNNER_COMPLETE.json', receipt)
        atomic.sync_dir(staging)
        publication = atomic.publish(staging, destination, receipt, boundary_pc=boundary_pc)
        return dict(checkpoint_receipt=receipt, publication=publication,
                    stream_metrics=saved['stream_metrics'], selection=selection(base))
    except BaseException as exc:
        if staging.exists() and not (staging / 'ATOMIC_FAILURE.json').exists():
            atomic.durable_json(staging / 'ATOMIC_FAILURE.json',
                dict(exception_type=type(exc).__name__, reason=str(exc)))
            atomic.sync_dir(staging)
        raise

def restore_cold(base, checkpoint, source_contract, receipt, provider, engine,
                 witness, *, next_pc, enabled=False):
    if enabled is not True:
        raise ValueError('R69 cold restore is default off')
    if source_contract.get('checkpoint_selection') != selection(base):
        raise ValueError('exact selected helper contract before restore')
    publication = __import__('json').loads((Path(checkpoint) / 'ATOMIC_COMPLETE.json').read_bytes())
    atomic.require_fresh_restore(publication)
    transition = base.plan_run_scope_transition(checkpoint, source_contract=source_contract,
        checkpoint_receipt=receipt, provider=provider, engine=engine, next_pc=next_pc)
    contract = dict(identity=base.identity(base.unwrap(provider), engine),
        checkpoint_receipt=receipt, run_scope_transition=transition,
        run_scope=base.run_scope(base.unwrap(provider)))
    verified = base.verify_checkpoint(checkpoint, source_contract=source_contract,
        next_pc=next_pc, constructor_contract=contract)
    return base.restore_quiescent(verified, engine, provider, witness)
