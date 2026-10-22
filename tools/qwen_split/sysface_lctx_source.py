"""Select the source-pinned L-context candidate; no old view or date adoption."""
import hashlib
import os
from pathlib import Path
MASTER = 'qfd_sys_face_ovl_lctx1'
SOURCE = 'rtl/qwen_split/qfd_sys_face_ovl_lctx1.sv'
SHA256 = '296fc8e17a8b819ec90fd201c9fecda8424b9b54dd6d4e57830beb6866927f55'
CAL_SOURCE = 'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv'
CAL_SHA256 = '713858300e2a534ca739afa5579d673f3acc0832cb97386d98a63f4adc53ae2a'

def enabled():
    value = os.environ.get('OT_QWEN_SYSFACE_L_CONTEXTS', '0')
    if value not in ('0','1'):
        raise ValueError('OT_QWEN_SYSFACE_L_CONTEXTS must be 0 or 1')
    return value == '1'

def select(default, root):
    wrapped=wrapper_enabled()
    if not enabled(): return default
    for flag,value in [('OT_QWEN_HEAD_PREP','1'),('OT_QWEN_FAULT_FACE','1'),('OT_QWEN_ROPE','1'),('OT_QWEN_STATUS_OBS','1'),('OT_QWEN_MU_NU','4')]:
        if os.environ.get(flag) != value:
            raise ValueError('L-context candidate requires '+flag+'='+value)
    root=Path(root)
    for path,digest in ((SOURCE,SHA256),(CAL_SOURCE,CAL_SHA256)):
        if hashlib.sha256((root/path).read_bytes()).hexdigest() != digest:
            raise ValueError('L-context selected source differs: '+path)
    from qwen_split.source_pin_plan import rtl_ports
    old=rtl_ports(root/'rtl/qwen_split/qfd_sys_face_ovl_fault1.sv','qfd_sys_face_ovl_fault1')
    selected=(MASTER,SOURCE)
    if wrapped:
        c=wrapper_contract(root);selected=(c['master'],c['source'])
    new=rtl_ports(root/selected[1],selected[0])
    if list(old.items()) != list(new.items()):
        raise ValueError('L-context candidate changed actual external pin ABI/order')
    return selected

WRAPPER_MASTER = 'qfd_sys_face_lctx3_wrapped'
WRAPPER_BINDING = 'results/arch/codex_sysface_l_2000/wrapper_binding.json'
WRAPPER_SHA256 = 'b25c0bdd8ad7f14fe0f5fac605fb87e441c6ce2bbae793b46d685b3973cf8b40'

def wrapper_enabled():
    value=os.environ.get('OT_QWEN_SYSFACE_WRAPPER','0')
    if value not in ('0','3'):
        raise ValueError('OT_QWEN_SYSFACE_WRAPPER must be 0 or 3')
    if value=='3' and not enabled():
        raise ValueError('sysface wrapper requires explicit L_CONTEXTS candidate')
    return value=='3'

def wrapper_contract(root):
    import json
    root=Path(root);path=root/WRAPPER_BINDING;b=json.loads(path.read_text())
    if b['master']!=WRAPPER_MASTER or b['input_capture_edges']!=1 or b['output_capture_edges']!=1 or b['reset_input_relay_edges']!=2 or b['core_reset_release_edges']!=3:
        raise ValueError('sysface wrapper boundary contract differs')
    rows={x['path']:x['sha256']for x in b['sources']}
    if rows.get(b['source_path'])!=WRAPPER_SHA256:
        raise ValueError('sysface wrapper selected source differs')
    for rel,digest in rows.items():
        p=(root/rel).resolve()
        if not p.is_relative_to(root.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
            raise ValueError('sysface wrapper source dependency differs: '+rel)
    receipt=root/'results/arch/codex_sysface_l_2000/wrapper_capture_receipt.json'
    proof=json.loads(receipt.read_text());cases={x['case']:x['returncode']for x in proof['results']}
    if proof['wrapper_sha256']!=WRAPPER_SHA256 or cases.get('selected')!=0 or any(cases.get(x)not in (1,2)for x in ('wrong_source_mutant','extra_capture_edge_mutant')):
        raise ValueError('sysface wrapper exact capture/causal proof missing')
    return dict(master=b['master'],source=b['source_path'],rtl_sha256=WRAPPER_SHA256,
        binding_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),capture_receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
        input_capture_edges=1,output_capture_edges=1,reset_input_relay_edges=2,core_reset_release_edges=3,
        automatic_pin_regs=False,scope='source-local boundary proof only; actual GEN and final programme required')
