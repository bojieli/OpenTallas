#!/usr/bin/env python3
"""dsfd_sp_vm die-port + per-root clock-entry ABI for the die generator (S81 VM owner, 2026-10-15).

Reads the ACTUAL die-name module (rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv, +DSFD_SP_VM_MIX4) with
tools/die_port_bind.py's parser and emits, for S-BIND / S-DIE:
  * every functional port (name, direction, width) the die netlist must bind -- the legacy 18:15 list's 40 ports are
    classified BOUND_IN_SOURCE / RETIRED_STATIC (replaced by a named static port, no die net may remain);
  * every clock / reset category port with its die domain (suffix _t = stream 1.2 GHz, _s = serial 0.9 GHz), the
    hardened master whose clock pin it feeds and that master's routed TT boundary insertion R (insertion.json), so the
    parent delivers phi - wire - R at each root (bank128: R = 222.0 ps).  A category without a closed view is OPEN.
It infers nothing about physical qualification; per-bit instance identity stays with the S-BIND clock contract.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as bind  # noqa: E402

SRC = 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv'
LEGACY_40 = ['ck', 'rst', 'cks', 'rss', 'c_cmd', 'c_done', 'c_st', 't_inp_su', 't_inp_hc',
             'f_su_rqv', 'f_su_rq', 't_su_rsv', 't_su_rs', 'f_su_wqv', 'f_su_wq', 'f_su_wqm', 'f_su_wqd',
             'f_hc_rqv', 'f_hc_rq', 't_hc_rsv', 't_hc_rs', 'f_hc_wqv', 'f_hc_wq', 'f_hc_wqm', 'f_hc_wqd',
             'f_pqx', 't_pqx', 'sel', 'col', 'aSW', 'f_capture', 'f_collective', 'tcs', 't_collective',
             'qSW', 'qSWs', 'f_wfc', 't_wfc', 't_gather', 'f_xgo']
RETIRED = {'ck': 'serial clock -> per-root ck_*_s category entries',
           'rst': 'serial reset -> per-root rst_*_s category entries',
           'tcs': 'legacy collective credit status (backpressure, owner 18:59) -> static f_crq 15 / t_crs 513',
           't_collective': 'legacy 592-b collective channel -> static f_crq 15 / t_crs 513 (L 12 fixed)'}
WIDTH_CHANGED = {'f_collective': (2100, 'four static compiler rows {tag8,data512,mask16,row14,v} = 2204')}
# category port -> (hardened master, its clock pin, closed kit dir) ; None = no closed native view yet
VIEWS = {
    'ck_mem_bank_t': ('dsfd_vm_static_bank128', 'ck', 'dsfd_vm_static_bank128_m4_v20'),
    'ck_mem_relay_req_t': ('dsfd_vm_static_relay128_b4|b8', 'ck_req', 'dsfd_vm_static_relay128_b4_native_cb|dsfd_vm_static_relay128_b8_native_cb'),
    'ck_mem_relay_rsp_t': ('dsfd_vm_static_relay128_b4|b8', 'ck_rsp', 'dsfd_vm_static_relay128_b4_native_cb|dsfd_vm_static_relay128_b8_native_cb'),
    'ck_mem_wcapture_t': ('dsfd_vm_static_write_capture128(E|W)', 'ck', 'dsfd_vm_direct_capture_e_native|dsfd_vm_direct_capture_w_native'),
    'ck_mem_wscatter_t': ('dsfd_vm_static_scatter_b8_out(B0|B8|B16|B24)', 'ck', 'dsfd_vm_direct_scatter_b0_native|dsfd_vm_direct_scatter_b8_native|dsfd_vm_direct_scatter_b16_native|dsfd_vm_direct_scatter_b24_native'),
    'ck_cap_control_s': ('dsfd_vm_static_cap_ctl', 'ck', 'dsfd_vm_static_cap_ctl_1015_r1'),
    'ck_mem_fsr_t': ('dsfd_vm_static_fsr_b0..b3', 'ck', 'dsfd_vm_static_fsr_b0_native_1015_r1|dsfd_vm_static_fsr_b1_native_1015_r1|dsfd_vm_static_fsr_b2_native_1015_r1|dsfd_vm_static_fsr_b3_native_1015_r1'),
    'ck_read_data_t': ('dsfd_vm_static_read_q0..q7', 'ck', 'dsfd_vm_static_read_q0_native_1015_r1|dsfd_vm_static_read_q1_native_1015_r1|dsfd_vm_static_read_q2_native_1015_r1|dsfd_vm_static_read_q3_native_1015_r1|dsfd_vm_static_read_q4_native_1015_r1|dsfd_vm_static_read_q5_native_1015_r1|dsfd_vm_static_read_q6_native_1015_r1|dsfd_vm_static_read_q7_native_1015_r1'),
    'ck_read_valid_t': ('dsfd_vm_static_read_v0..v7', 'ck', 'dsfd_vm_static_read_v0_native_1015_r1|dsfd_vm_static_read_v1_native_1015_r1|dsfd_vm_static_read_v2_native_1015_r1|dsfd_vm_static_read_v3_native_1015_r1|dsfd_vm_static_read_v4_native_1015_r1|dsfd_vm_static_read_v5_native_1015_r1|dsfd_vm_static_read_v6_native_1015_r1|dsfd_vm_static_read_v7_native_1015_r1'),
}


def insertion_r(kit, pin):
    out = []
    for k in kit.split('|'):
        hits = sorted((ROOT / 'physical/ref_tile' / k / 'views').glob('*/insertion.json'))
        if not hits:
            return None
        b = json.loads(hits[0].read_text())['clock_measurements'][pin]['tt']['boundary']
        out.append({'kit': k, 'R_tt_ps': b['mean'], 'min': b['min'], 'max': b['max'], 'n': b['n']})
    return out


def main():
    src = (ROOT / SRC).read_text()
    mod = next(m for m in bind.parse_modules(bind.preprocess(src, {'DSFD_SP_VM_MIX4': ''}), SRC) if m.name == 'dsfd_sp_vm')
    ports = {n: {'dir': d[0], 'bits': mod.width(n, mod.env())} for n, d in mod.ports.items()}
    clocks, resets, func = {}, {}, {}
    for n, p in sorted(ports.items()):
        if n.startswith('ck_') or n == 'cks':
            dom = 'serial' if n.endswith('_s') else 'stream'
            v = VIEWS.get(n)
            clocks[n] = dict(p, domain=dom, master=v[0] if v else None, child_pin=v[1] if v else None,
                             routed_R=(insertion_r(v[2], v[1]) if v else None),
                             delivery='phi - wire - R per root (R from the bound routed view)' if v else
                             'OPEN: no closed native view; parent leaf/CTS root pending')
        elif n.startswith(('rss', 'rst_')):
            resets[n] = dict(p, domain='serial' if n.startswith('rst_') else 'stream')
        else:
            func[n] = p
    legacy = {}
    for n in LEGACY_40:
        if n in RETIRED:
            legacy[n] = {'status': 'RETIRED_STATIC', 'replacement': RETIRED[n], 'in_source': n in ports}
        elif n in WIDTH_CHANGED:
            legacy[n] = {'status': 'WIDTH_CHANGED_STATIC', 'die_legacy_bits': WIDTH_CHANGED[n][0],
                         'source_bits': ports[n]['bits'], 'why': WIDTH_CHANGED[n][1]}
        else:
            legacy[n] = {'status': 'BOUND_IN_SOURCE' if n in ports else 'MISSING', 'bits': ports.get(n, {}).get('bits')}
    stat = {}
    for v in legacy.values():
        stat[v['status']] = stat.get(v['status'], 0) + 1
    rec = {
        'schema': 'opentallas.s81.vm-die-abi.v1', 'source': SRC, 'defines': ['DSFD_SP_VM_MIX4'],
        'legacy_18_15_list': {'count': len(LEGACY_40), 'status': stat, 'ports': legacy},
        'functional_ports': func, 'clock_entries': clocks, 'reset_entries': resets,
        'counts': {'ports': len(ports), 'functional': len(func), 'clock_ports': len(clocks),
                   'clock_bits': sum(c['bits'] for c in clocks.values()), 'reset_ports': len(resets),
                   'reset_bits': sum(r['bits'] for r in resets.values())},
        'generator_requirements': [
            'drop RTL_HUB_EXTRA vm->collective t_collective 592 / tcs 3 (no RTL port, backpressure-era)',
            'collective->vm f_collective 2204 (not 2100); add collective f_crq 15 -> vm, vm t_crs 513 -> collective',
            'replace the RTL_BIND dsfd_sp_vm clock branch (ck/rst serial, cks/rss stream) by these per-bit '
            'clock/reset entries; each clock bit is its own die/parent root delivered at phi - wire - R',
            'MIX4 slot: f_mx_* / t_mx_* nets to dsfd_engram_mix4_c (DSFD_SP_VM_MIX4 in layer1.f)'],
        'not_claimed': 'no die netlist bound, no physical / native qualification; generator side owned by S-BIND/S-DIE',
    }
    out = ROOT / 'results/arch/s81_vm_die_abi_1015/contract.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({'legacy40': stat, 'counts': rec['counts'],
                      'open_clock_categories': sorted(n for n, c in clocks.items() if not c['routed_R'])}))


if __name__ == '__main__':
    main()
