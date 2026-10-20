#!/usr/bin/env python3
"""Generate opt-in parent source candidates with the split-port BTAB s3 leaf.
No current default parent is edited. These candidates are compile integration
vehicles, not physical closure/adoption. All other source bytes are preserved.
"""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'rtl/qwen_dv/s5/btab_candidate'
REPORT=ROOT/'results/arch/qw_slice6_1019/landing_contract_1020/btab_candidate_binding.json'
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=True); rows=[]
    for top in ['qfd_dv_s5_flat','qfd_dv_s5_lp','qfd_dv_s5b_lp']:
        src=ROOT/'rtl/qwen_dv/s5'/('' if top.endswith('flat') else 'lp')/(top+'.sv')
        original=src.read_text();newtop=top+'_btab_s3_candidate'
        pattern=r'qfd_dv_s5_btab u_btab\s*\([^;]+;'
        matches=list(re.finditer(pattern,original));assert len(matches)==1
        old=matches[0].group();assert old.count('.bt_q(bt_q)')==1
        new=old.replace('qfd_dv_s5_btab u_btab','qfd_dv_s5_btab_s3 u_btab').replace('.bt_q(bt_q)','.bt_ql(bt_q[127:0]), .bt_qh(bt_q[255:128])')
        changed=original.replace(old,new).replace('module '+top+' ', 'module '+newtop+' ')
        assert ('module '+newtop+' ') in changed
        # Reversibility audit includes every byte outside module name and cell binding.
        assert changed.replace(new,old).replace('module '+newtop+' ','module '+top+' ')==original
        target=OUT/(newtop+'.sv');target.write_text(changed)
        rows.append({'source':str(src.relative_to(ROOT)),'source_sha256':digest(original),'candidate':str(target.relative_to(ROOT)),
            'candidate_sha256':digest(changed),'top':newtop,'child':'u_btab','leaf':'qfd_dv_s5_btab_s3',
            'reversible_source_diff':'PASS_only_module_name_and_btab_instance','added_data_edges':0,'added_reset_edges':0,
            'clock_and_other_port_bytes':'identical','physical_binding':'HOLD_until_exact_leaf_CLOSED_and_parent_contracts_pass'})
    REPORT.write_text(json.dumps({'status':'OPT_IN_SOURCE_COMPILE_CANDIDATES_ONLY','bindings':rows},indent=2)+'\n')
if __name__=='__main__':main()
