#!/usr/bin/env python3
"""Explicit safe COLL parent table candidate; preserve the legacy table by default."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as B

SOURCE = 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep_mux_coll_safe2.sv'
OLD = {'ot_s81sl_slice_lepw_mu', 'ot_s81sl_slice_lepw_mus', 'ot_s81sl_slice_lepe_mu',
       'ot_s81sl_slice_lepe_nh_mus', 'ot_s81sl_slice_lepw_mab'}
FILES = [SOURCE, 'rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe2.sv',
         'rtl/common/ot_link_credit_rx_sram.sv', 'rtl/lib/ot_sram_showahead_1r1w.sv',
         'rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe2.sv',
         'rtl/lib/ot_sram_oldread_wreg.sv', 'rtl/lib/ot_rst_relay_tree3.sv']
DEFINE = 'OT_S81PH_COLL_TF_CLEANUP'


def candidate(original, source):
    """Derive every changed master width from the exact selected source; refuse drift."""
    modules = {m.name:m for m in B.parse_modules(B.preprocess(source, {DEFINE:'1'}), SOURCE)}
    table = copy.deepcopy(original)
    changes = []
    for key, master in table['masters'].items():
        old = master.get('module')
        if old not in OLD:
            continue
        name = old + '_coll_safe2'
        m = modules.get(name)
        if m is None or m.port_parse_errors or not m.ports:
            raise ValueError('missing or ambiguous safe parent source: '+name)
        actual = {p:m.width(p,m.env()) for p in m.ports}
        if any(not isinstance(v,int) or v<=0 for v in actual.values()) or set(actual)&{'tf','tfb'}:
            raise ValueError('unresolved or obsolete safe parent ports: '+name)
        expected = original.get('rtl_widths',{}).get(old)
        if not expected or actual != {k:v for k,v in expected.items() if k not in {'tf','tfb'}}:
            raise ValueError('safe parent interface differs from selected legacy contract: '+old)
        table['rtl_widths'][name] = actual
        master['module'] = name
        master['view_note'] = 'Explicit safe2 interface candidate; no behavior/native/parent-fit adoption'
        changes.append({'master':key,'old':old,'new':name,'widths_source':SOURCE})
    if not changes:
        raise ValueError('no supported MU parent masters selected')
    table['defines'] = list(dict.fromkeys([*table.get('defines',[]), DEFINE]))
    table['rtl_files'] = list(dict.fromkeys([*table.get('rtl_files',[]), *FILES]))
    table['coll_safe2_candidate'] = {'changes':changes,'required_define':DEFINE,
        'scope':'SOURCE_INTERFACE_ONLY_NOT_BEHAVIOR_NATIVE_OR_PARENT_FIT',
        'dependencies':{'safe_lane':'83d6b8b7f','helpers':'ba7479f59','TXSAFE':1}}
    return table


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--table',required=True);ap.add_argument('--root',default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument('--out',required=True);a=ap.parse_args()
    root=Path(a.root);result=candidate(json.loads(Path(a.table).read_text()),(root/SOURCE).read_text())
    Path(a.out).write_text(json.dumps(result,indent=1)+'\n')
    print('COLL_SAFE2_TABLE_CANDIDATE',len(result['coll_safe2_candidate']['changes']))
