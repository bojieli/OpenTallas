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
    new=rtl_ports(root/SOURCE,MASTER)
    if list(old.items()) != list(new.items()):
        raise ValueError('L-context candidate changed actual external pin ABI/order')
    return MASTER,SOURCE
