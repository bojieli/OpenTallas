#!/usr/bin/env python3
"""Classify a die_case.py run by path class and owner (H-DIE 2026-10-15).
    die_case_classify.py CASE_OUT_DIR [--json OUT]
Reads paths_{tt_max,ff_min}.txt (startpoint endpoint slack, one per endpoint), maps each instance to its master class
(phy / ctl / svg / sm / clock repeater / port) and reports per (start class -> end class, corner): endpoints, failing,
worst, TNS, the owner that fixes it and the structural action."""
import argparse, json, re, gzip
from collections import defaultdict
from pathlib import Path

CLS = [(r'^phy_', 'phy'), (r'^ctl_', 'ctl'), (r'^svg_', 'svg'), (r'^sm_', 'sm'), (r'^dk[hsr]_', 'clktree'),
       # v16 full-die case (H-DIE-D4 2026-10-16): every v16 instance family
       (r'^hb_ckgen$', 'ckgen'), (r'^xc_', 'xcal'), (r'^vmks_', 'vmks'), (r'^vmdel_', 'vmdel'), (r'^cp_', 'cmdtgt'),
       (r'^sfr_', 'rly_sfu'), (r'^rfr_', 'rly_ring'), (r'^lg_', 'vm_lg'), (r'^hb_vms_', 'vm_hub'),
       (r'^(calendar|epcal|vmfc)_', 'vm_cal'), (r'^smw_', 'sm_vm_wr'), (r'^vm_status', 'vm_status'),
       (r'^sfucore_', 'sfu_core'), (r'^sfup_', 'sfu_prog'), (r'^sfus_', 'su_sfustore'), (r'^sfu_', 'sfu_leaf'),
       (r'^hc_eng$', 'hc_eng'), (r'^hc_(SW|SE|NW|NE)$', 'hc_q'), (r'^hc_', 'hc_leaf'),
       (r'^su_prog$', 'su_prog'), (r'^sucore_', 'su_qcore'), (r'^sucx_', 'su_cx'), (r'^subr_', 'su_bridge'), (r'^su_', 'su_pg'),
       (r'^hb_coll_', 'coll'), (r'^cij_', 'coll_inj'), (r'^hb_dbk_', 'dma_back'), (r'^wbk_', 'wb_kport'),
       (r'^hb_(idx(?:__.*)?|argmax)$', 'idx'), (r'^hb_quant', 'quant'), (r'^xl_', 'xload'), (r'^(lk|ep)_', 'link'),
       (r'^(host_|hleaf_)', 'host'), (r'^col_', 'collar'), (r'^sfault_', 'stack_fault'),
       # d4g quadrant services and die transport (GEN2). These are tile pins, never top ports.
       (r'^vmb_', 'vm_bank'), (r'^(vmm_|xq_)', 'vm_merge'), (r'^hidxr_', 'rly_idx'),
       (r'^hcx_', 'rly_hc'), (r'^hcb_', 'hc_leaf'), (r'^hcoll', 'coll'),
       (r'^(cxdl_|cxij_|cxrc_|fcx_)', 'su_cx'), (r'^pgp_', 'su_prog'),
       (r'^tkm_', 'topk_merge'), (r'^cic_', 'coll_inj'), (r'^refcfg_', 'refresh_cfg'),
       (r'^wbc_', 'wb_kport'), (r'^(std_|stu_|stl_|str_)', 'scalar_tree'),
       (r'^(fl_|fs_|fr_)', 'fault_tree'), (r'^l[0-9]+_', 'die_transport')]
# owner of a class (intra-class paths); a cross-class path is a die-level interface: H-DIE + both owners
CLS_OWNER = dict(phy='H-DIE', ctl='H-DIE', svg='H-DIE', sm='H-SM', clktree='H-DIE', ckgen='H-DIE-CKGEN', xcal='H-SM',
                 vmks='H-VM', vmdel='H-VM', cmdtgt='H-NETLIST', rly_sfu='H-DIE', rly_ring='H-DIE', vm_lg='H-VM',
                 vm_hub='H-VM', vm_cal='H-VM', sm_vm_wr='H-VM', vm_status='H-VM', sfu_core='H-SU', sfu_prog='H-SU',
                 su_sfustore='H-SU', sfu_leaf='H-SU', hc_eng='H-HCENG', hc_q='H-HCENG', hc_leaf='H-HCENG',
                 su_prog='H-SU', su_qcore='H-SU', su_cx='H-SU', su_bridge='H-SU', su_pg='H-SU', coll='H-COLL',
                 coll_inj='H-COLL', dma_back='H-HARDEN', wb_kport='H-HARDEN', idx='H-IDX', quant='H-XL', xload='H-XL',
                 link='H-HOST', host='H-HOST', collar='H-NETLIST', stack_fault='H-DIE', port='H-DIE',
                 vm_bank='H-VM', vm_merge='H-VM', rly_idx='H-DIE', rly_hc='H-DIE',
                 topk_merge='H-IDX', refresh_cfg='H-HARDEN', scalar_tree='H-SU',
                 fault_tree='H-DIE', die_transport='H-DIE')


def owner(k):
    if k in OWN:
        return OWN[k]
    a, b = (CLS_OWNER.get(x, 'H-DIE') for x in k)
    if k[0] == k[1]:
        return (a, f'{k[0]} internal / same-family hop (view-internal if one instance)')
    return ('H-DIE + ' + '/'.join(sorted({a, b} - {'H-DIE'})) if {a, b} - {'H-DIE'} else 'H-DIE',
            f'die interface {k[0]} -> {k[1]}: relay staging / pin placement / view boundary budget')
OWN = {('ctl', 'phy'): ('H-DIE', 'PHY command path (leaf output flops, OREG)'),
       ('phy', 'ctl'): ('H-DIE', 'PHY read return into the controller'),
       ('ctl', 'svg'): ('H-DIE', 'K port response/ready controller -> group'),
       ('svg', 'ctl'): ('H-DIE', 'K port request group -> controller'),
       ('ctl', 'ctl'): ('H-DIE', 'K handshake round trip through the group (combinational kr_v->kr_rdy)'),
       ('svg', 'svg'): ('H-DIE', 'group internal / round trip'),
       ('svg', 'sm'): ('H-DIE + H-SM', 'SM_HBM link group -> SM (packet/command): needs die relay stations sized to the hop'),
       ('sm', 'sm'): ('H-SM', 'SM internal (SYNTH ETM)')}


def cls(name):
    inst = name.split('/')[0]
    for r, c in CLS:
        if re.match(r, inst):
            return c
    return 'unclassified_tile' if '/' in name else 'port'


def load(p):
    op = gzip.open if str(p).endswith('.gz') else open
    with op(p, 'rt') as f:
        for line in f:
            a = line.split()
            if len(a) == 3:
                yield a[0], a[1], float(a[2])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--json')
    a = ap.parse_args()
    res = {}
    corners = [('tt_setup', 'paths_tt_max.txt'), ('ff_hold', 'paths_ff_min.txt')]
    if any((Path(a.out) / ('paths_ss_max.txt' + suffix)).exists() for suffix in ('', '.gz')):
        corners.append(('ss_setup_sensitivity', 'paths_ss_max.txt'))
    for corner, fn in corners:
        p = Path(a.out) / fn
        if not p.exists():
            p = Path(str(p) + '.gz')
        g = defaultdict(lambda: dict(endpoints=0, failing=0, worst=1e9, tns=0.0, example=''))
        for s, e, sl in load(p):
            k = (cls(s), cls(e)); r = g[k]
            r['endpoints'] += 1
            if sl < 0:
                r['failing'] += 1; r['tns'] += sl
            if sl < r['worst']:
                r['worst'] = sl; r['example'] = f'{s} -> {e}'
        res[corner] = {f'{k[0]}->{k[1]}': dict(v, worst=round(v['worst'], 2), tns=round(v['tns'], 1),
                                               owner=owner(k)[0], action=owner(k)[1])
                       for k, v in sorted(g.items(), key=lambda t: t[1]['worst'])}
    txt = json.dumps(res, indent=1)
    if a.json:
        Path(a.json).write_text(txt + '\n')
    print(txt)


if __name__ == '__main__':
    main()
