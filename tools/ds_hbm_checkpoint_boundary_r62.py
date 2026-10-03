"""Additive checkpoint-boundary path normalization and durable stage diagnostics.
Original R55/r37/V3 sources remain unchanged. No numerical launcher.
"""
from pathlib import Path
import json
import traceback
from ds_hbm_connected_prepare_r37 import sha


def source_contract(helper, provider, engine, *, runner_source, source_plan):
    # r37 sha deliberately requires Path: normalize only the filesystem type.
    return dict(identity=helper.identity(provider, engine),
                runner_source_sha256=sha(Path(runner_source)),
                source_plan_sha256=sha(Path(source_plan)))


def boundary_call(receipt_path, stage, operation):
    """Persist last entered stage and exact traceback without swallowing failure."""
    path=Path(receipt_path)
    record=json.loads(path.read_bytes()) if path.exists() else {}
    record.update(last_call_stage=stage, stage_status='ENTERED')
    path.write_text(json.dumps(record,indent=2)+'\n')
    try:
        value=operation()
    except BaseException as exc:
        record.update(stage_status='FAILED',exception_type=type(exc).__name__,
                      reason=str(exc),traceback=traceback.format_exc())
        path.write_text(json.dumps(record,indent=2)+'\n')
        raise
    record.update(stage_status='COMPLETED')
    path.write_text(json.dumps(record,indent=2)+'\n')
    return value


ORIGINAL_R55_SHA256='d8afd90b1d9e9ff374c85caf1e55e71a5e5bca6afd1639d077fdeb9f1c51ab39'


def install_runner_hash_adapter(runner):
    """Explicit additive enrollment for exact original R55; no launch here."""
    path=Path(runner.__file__)
    if sha(path)!=ORIGINAL_R55_SHA256 or runner.sha is not sha:
        raise ValueError('exact original R55 and r37 hash function required')
    def path_sha(value):
        return sha(Path(value))
    runner.sha=path_sha
    return {'original_runner_source_sha256':sha(path),
            'successor_adapter_source_sha256':sha(Path(__file__)),
            'only_change':'normalize filesystem argument to Path before original sha',
            'numerical_launch':False}
