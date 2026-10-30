"""Selected source receipt phase/identity guards shared by native boot encoders."""
import hashlib
from pathlib import Path


def seqhost_phase_contract(receipt):
    current=receipt.get('seqhost_input_clock');prior=receipt.get('input_clock')
    if current is not None and prior is not None and current!=prior:
        raise ValueError('conflicting source-qualified seqhost reset/KS phase contracts')
    contract=current if current is not None else prior
    key='accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4'
    if not isinstance(contract,dict) or type(contract.get(key))is not int or not 0<=contract[key]<4:
        raise ValueError('source-qualified seqhost reset/KS phase contract missing or outside mod4')
    return contract


def qualify_selected(receipt, source_root, manifest, inventory):
    if source_root is None or manifest is None or inventory is None:
        raise ValueError('unbooked local encoding requires explicit selected source/manifest/inventory')
    from layer_prog.slice_source import manifest_selection
    from layer_prog.bound_control import BoundControl
    import bind_elab
    root=Path(source_root).resolve();master=receipt['masters']['dsdv_hostb_seqhost_mux']
    hashes=receipt.get('source_sha256',{})
    required={master['source_path'],'rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host.sv','rtl/dsrom_sys/s81_dv/unit/ot_dsdv_walk_issue.sv','rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hslot.sv'}
    if not required<=set(hashes):raise ValueError('complete selected seqhost dependency identities required')
    for name,digest in hashes.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('selected native boot dependency changed: '+name)
    selected=manifest_selection(root,manifest)
    picked,ambiguous=bind_elab.pick(selected[2],'dsdv_hostb_seqhost_mux',selected[3])
    if ambiguous or not picked or Path(picked).resolve()!=root/master['source_path']:
        raise ValueError('selected native seqhost master differs')
    if set(master.get('defines',[]))!=set(selected[1].get('defines',[])):
        raise ValueError('selected native seqhost defines differ')
    actual=inventory.get('units',{}).get('u_seqhost',{})
    if actual.get('master')!='dsdv_hostb_seqhost_mux':raise ValueError('actual native seqhost instance absent')
    body=bind_elab.module_body(Path(picked),'dsdv_hostb_seqhost_mux')
    import re
    expected=dict(HOSTB_ENABLE=0,STATIC_KS6=0,STATIC_KS_SPAN=0,STATIC_KS_GRAPH_TAG=0,FMUT=0)
    if set(actual.get('params',{}))-set(expected):raise ValueError('unqualified native seqhost parameter')
    for name,wanted in expected.items():
        value=actual.get('params',{}).get(name)
        if value is None:
            default=re.search(r'\b'+name+r'\s*=\s*([^,)\n]+)',body)
            if not default:raise ValueError('selected native parameter default absent')
            value=default[1]
        if BoundControl._integer(value)!=wanted:raise ValueError('actual native seqhost parameter differs: '+name)
    return True
