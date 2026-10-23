"""Exact HP13 source selection and earliest-embedding joins; no physical/age adoption."""
import hashlib
import os
from pathlib import Path

MASTER = 'qfd_tt_ctlm_dv_hp13_rrloc_native32'
SOURCE = 'rtl/qwen_dv/headprep13/native32/qfd_tt_ctlm_dv_hp13_rrloc_native32.sv'
SOURCES = {
 SOURCE:'22b5059010fb02abbca2bb9bce1d8773b3e372c1917d2e8ef01164d4da0cbe16',
 'rtl/qwen_dv/headprep13/native32/qfd_tt_ctlm_dv_hp13_rrloc_helpers.sv':'8a1c0d01a5761533e6617eb293adb044cf8c0881e899ec3e5091babc3e5fe58f',
 'rtl/qwen_dv/headprep13/h16za/native32_1r_param.v':'44d54f850a0630849746de3cb907e132ec579b6155fbb10ef21fd5e20c44a9d7',
 'rtl/qwen_dv/headprep13/h16za/native32_helpers.sv':'1e021ff33742ef24529373bfab456eeb95f90c693f597963cd8c2f368c3bec88',
}
PREP = (('emb_start','head_prepare_v',1),('emb_token','head_prepare_token',18),
        ('emb_position','head_prepare_position',18),('emb_user','head_prepare_user',2))
REQUIRED = {p:(w,'output') for p,_,w in PREP}
REQUIRED.update(ck_core=(1,'input'),ck_hr=(1,'input'),hr=(453,'output'),ctx_x=(129,'input'),dh_user=(2,'input'))

def validate_ports(master, ports):
    from qwen_split import headprep_corepub_source as CP
    if master != MASTER and master not in {c['master'] for c in CP.CONTRACTS.values()}:
        raise ValueError('head prepare requires exact unique HP13 source master')
    for p, spec in REQUIRED.items():
        if ports.get(p) != spec:
            raise ValueError('HP13 actual source port differs: '+p)

def select(default, root, env=None):
    env = os.environ if env is None else env
    if env.get('OT_QWEN_HEAD_PREP','0') != '1':
        return default  # no reads, parameter changes, geometry or legacy source changes
    for flag, value in [('OT_QWEN_ROPE','1'),('OT_QWEN_STATUS_OBS','1'),('OT_QWEN_MU_NU','4')]:
        if env.get(flag) != value:
            raise ValueError('selected HP13 coherent source requires '+flag+'='+value)
    root=Path(root)
    for path,digest in SOURCES.items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('HP13 source identity differs: '+path)
    from qwen_split.source_pin_plan import rtl_ports
    validate_ports(MASTER,rtl_ports(root/SOURCE,MASTER))
    variant=env.get('OT_QWEN_HP13_COREPUB','0')
    if variant != '0':
        from qwen_split import headprep_corepub_source as CP
        return CP.select(root,variant)
    return MASTER,SOURCE

def prepare_joins(master, source_ports, native_ports):
    validate_ports(master, source_ports)
    for source, sink, width in PREP:
        if native_ports.get(sink)!=(width,'input'):
            raise ValueError('actual native head-prepare input differs: '+sink)
    return [('hp_tt_'+p,'spine_local',w,[('tt_ctlm',p),('native59',q)]) for p,q,w in PREP]

def reject_unbound_hr_age():
    raise ValueError('HP13 fixed native has no parameter overrides: source construction XPF21 is not actual GEN transport; exact HR source/output age and fixed-XPF route reconciliation remain unqualified (never inherit old HR_PIN_REG1)')

def selected_master(env=None):
    env=os.environ if env is None else env
    variant=env.get('OT_QWEN_HP13_COREPUB','0')
    if variant=='0': return MASTER
    from qwen_split import headprep_corepub_source as CP
    return CP.contract(variant)['master']
