"""Opt-in native kshare specialization after proving both clock inputs share a net.

Call on the native instance dictionary before emitting the source top. The source
closure must also include ot_hbm_svc_vm_kshare_oneclk.sv. Never applies by default.
"""
from copy import deepcopy

ORIGINAL = 'ot_hbm_svc_vm_kshare_splitstrap'
ONECLOCK = 'ot_hbm_svc_vm_kshare_oneclk'
WRAPPER = 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_vm_kshare_oneclk.sv'


def specialize_instances(instances):
    """Return a copy + equality receipt, refusing any nonidentical clock bits.

    A port expression is matched exactly; this admits an existing alias and
    never substitutes a clock merely because it has the same name/frequency.
    """
    result = deepcopy(instances)
    receipt = []
    for name, obj in result.items():
        if obj.get('master') != ORIGINAL:
            continue
        ports = obj['ports']
        if not ports.get('hbm_clk') or ports['hbm_clk'] != ports.get('stream_clk'):
            raise ValueError(f'{name}: kshare clocks are not identical source expressions')
        if ports['hbm_clk'].get('direction') != 'input':
            raise ValueError(f'{name}: kshare clock source is not an input')
        receipt.append(dict(instance=name, original=ORIGINAL, replacement=ONECLOCK,
                            shared_clock=deepcopy(ports['hbm_clk']),
                            removed_alias='stream_clk', added_cycles=0))
        del ports['stream_clk']
        obj['master'] = ONECLOCK
        obj['origin'] = obj.get('origin', '') + '; same-net kshare one-clock specialization'
    if not receipt:
        raise ValueError('no native kshare instances to specialize')
    return result, receipt
