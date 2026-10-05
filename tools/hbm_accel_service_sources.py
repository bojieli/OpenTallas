"""Explicit HA8 source selection; never drive readiness, owners or a clock."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def lifecycle_sources(root=ROOT, *, enable=False):
    root=Path(root)
    base=root/'rtl/model/qwen_native_consumer_drain_20261003'
    common=[root/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',base/'ot_gpu_qwen_native_consumer_drain.sv',
            root/'rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv',
            base/'ot_gpu_qwen_kv_native_lifecycle.sv']
    if not enable:return 'ot_gpu_qwen_kv_native_lifecycle',common
    new=root/'rtl/hbm_accel/service'
    return 'ot_hbm_accel_native_lifecycle_select',common+[new/(n+'.sv') for n in
        ['ot_hbm_accel_kv_lifecycle','ot_hbm_accel_kv_native_lifecycle','ot_hbm_accel_native_lifecycle_select']]

def expert_sources(root=ROOT, *, inspect_rejected=False):
    if not inspect_rejected:
        raise RuntimeError('HA4 expert draft REJECTED: paused column offer/acceptance mismatch; use existing causal provider in combined design')
    root=Path(root);new=root/'rtl/hbm_accel/service'
    return [root/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',root/'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv',
            root/'rtl/model_ready_hbm_r14/ot_hbm_r14_fifo2.sv',root/'rtl/gpu/ot_gpu_expert_fetch.sv',
            root/'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']+[
            new/(n+'.sv') for n in ['ot_hbm_accel_stream_pc','ot_hbm_accel_return_fifo',
            'ot_hbm_accel_expert_service','ot_hbm_accel_expert_fetch','ot_hbm_accel_owned_crossing','ot_hbm_accel_expert_stack']]


def index_sources(root=ROOT):
    """Reuse the existing scored/select arithmetic; no second implementation."""
    import ast, subprocess
    campaign = subprocess.check_output(
        ['git', 'show', '67d69cb75:tools/dsrom_edge_scorer_campaign.py'], cwd=ROOT, text=True)
    names = None
    for node in ast.parse(campaign).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'STK_RTL' for t in node.targets):
            names = ast.literal_eval(node.value)
    if names is None:
        raise RuntimeError('Cicero source inventory unavailable')
    root = Path(root)
    return [root/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', root/'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv'] + [root/n for n in names] + [root/'rtl/hbm_accel/service/ot_hbm_accel_index_stack.sv']


def lifecycle_parameters(*, enable=False, block_enable=False):
    """Separate opt-in successor selection from the enclosing block's enable."""
    return dict(ENABLE=int(block_enable), USE_REGISTERED_FLAGS=int(enable))


def check_source_pins(root=ROOT):
    """Refuse changed reused RTL before joining the sole enclosing build."""
    import hashlib, subprocess
    root = Path(root)
    pins = {
        'rtl/gpu/ot_gpu_expert_fetch.sv': 'c52ae6d7f',
        'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv': '52ce3e9c1',
        'rtl/model_ready_hbm_r14/ot_hbm_r14_fifo2.sv': '52ce3e9c1',
        'rtl/model/qwen_native_consumer_drain_20261003/ot_gpu_qwen_kv_native_lifecycle.sv': '86b693089',
    }
    # The inventory is shared with Cicero; use the actual original files.
    for path in index_sources(root)[2:-1]:
        pins[str(path.relative_to(root))] = 'ac7104cf6'
    result = {}
    for rel, commit in pins.items():
        expected = subprocess.check_output(['git','show',commit+':'+rel], cwd=ROOT)
        path = root/rel
        if not path.is_file() or path.read_bytes() != expected:
            raise ValueError('missing or changed pinned source: '+str(path))
        result[rel] = dict(commit=commit,sha256=hashlib.sha256(expected).hexdigest())
    return result
