#!/usr/bin/env python3
"""Select actual compatible CLOSED view directories in the consumed die contract.
This selection preserves source ports/parameters and does not qualify the parent die.
"""
import argparse,json
from pathlib import Path

def apply(c):
    selected=[]
    for n,i in c['instances'].items():
        if i['master']=='ot_hbm_static_cfg_collar_idx256r' and i.get('params',{}).get('FAN32')==1:
            i['physical_view']='physical/ref_tile/hdie_col_idx256r_b/views/ot_hbm_static_cfg_collar_idx256r'
            i['closed_record']='HBM-TREE8 idx256r_b CLOSED; unchanged FAN32=1 parameter configuration'
            selected.append(n)
        elif i['master']=='ot_hbm_svc_pc_ctrl_leaf_cfg_h9b':
            i['physical_view']='physical/ref_tile/hdie_pc_ctrl_cfg_h9c/views/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b'
            i['closed_record']='HBM-H9R11 CLOSED h9c fallback selected by l25'
            selected.append(n)
    return selected

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
    c=json.loads(a.input.read_text());names=apply(c);a.output.write_text(json.dumps(c,indent=1)+'\n')
    r=dict(selected_instances=names, count=len(names), qualification='CLOSED_CHILD_VIEW_SELECTION; parent physical implementation outstanding', conditional_unbound=['n12 pg1b requires actual VM_RT_EXTRA=171 assembled budget'])
    if a.report:a.report.write_text(json.dumps(r,indent=1)+'\n')
    print('CLOSED_VIEW_SELECTION',len(names))
