#!/usr/bin/env python3
"""Export selected VM clock/leaf/operand identity; historical views give no source credit."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from qwen_split.native_compute_join import ROOT,load_nodes
REF='96f30a6a0'
TOP='rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory.sv'
REGION='rtl/qwen_sys/vm_nox_20261014/ot_qfd_vm_region_nx.sv'
BODY='rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv'

def read(path):return subprocess.check_output(['git','show',REF+':'+path],cwd=ROOT,text=True)

def export():
    views_ref=subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip()
    def view_read(path):
        p=subprocess.run(['git','show',views_ref+':'+path],cwd=ROOT,text=True,capture_output=True)
        return p.stdout if p.returncode==0 else None
    source={p:read(p)for p in (TOP,REGION,BODY)}
    lc={int(i):p for i,p in re.findall(r'assign\s+lc\[(\d+)\]\s*=\s*(ck_r\d+_\d+)\s*;',source[TOP])}
    oc={int(i):p for i,p in re.findall(r'assign\s+oc\[(\d+)\]\s*=\s*(ck_r\d+_\d+)\s*;',source[TOP])}
    assert set(lc)==set(range(448)) and set(oc)==set(range(24,63))
    recipes={}
    files=[p for p in subprocess.check_output(['git','ls-tree','-r','--name-only',views_ref,'tools/ref_tile'],cwd=ROOT,text=True).splitlines()if re.search(r'/qfd_vm[^/]*\.json$',p)]
    for f in files:
        a=json.loads(view_read(f))
        if 'top'not in a or 'name'not in a:continue
        view=ROOT/'physical/ref_tile'/a['name']/'views'/a['top']
        lef=view/(a['top']+'.lef');size=None
        lef_data=view_read(str(lef.relative_to(ROOT)))
        tt_lib=view/(a['top']+'_tt.lib');tt_data=view_read(str(tt_lib.relative_to(ROOT)))
        if lef_data:
            m=re.search(r'\bSIZE\s+([0-9.eE+-]+)\s+BY\s+([0-9.eE+-]+)',lef_data)
            if m:size=[float(m[1]),float(m[2])]
        recipes.setdefault(a['top'],[]).append(dict(recipe=f,params=a.get('params',{}),clock_port=a.get('clock_port'),
            candidate_outline=a.get('outline'),view_ref=views_ref,lef=str(lef.relative_to(ROOT))if lef_data else None,lef_sha256=hashlib.sha256(lef_data.encode()).hexdigest()if lef_data else None,
            actual_lef_size_um=size,tt_lib=str(tt_lib.relative_to(ROOT))if tt_data else None,
            source_equivalence='UNQUALIFIED historical reference; selected parameters, clocks, pins and native view must be verified'))
    module_paths={name:path for path,names in {
        REGION:['ot_qfd_vm_bctl_nx','ot_qfd_vm_rr2_nx','qfd_vm_qcommit'],
        BODY:['ot_qfd_vm_bank_t','ot_qfd_vm_su_t'],
        'rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_region_leaf.sv':['ot_qfd_vm_sctl_t','ot_qfd_vm_rr4_t','ot_qfd_vm_delay1_t','ot_qfd_vm_delay2_t'],
        'rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_answer_tiles.sv':['ot_qfd_vm_su1024_t']}.items()for name in names}
    module_identity={}
    for name,path in module_paths.items():
        text=read(path);match=re.search(r'(?ms)^module\s+'+re.escape(name)+r'\b.*?^\s*endmodule\b',text)
        if not match:raise ValueError('selected module definition absent: '+name)
        module_identity[name]=dict(source=path,source_ref=REF,module_sha256=hashlib.sha256(match.group().encode()).hexdigest(),
            meaning='Exact selected module declaration/body identity, independent of unrelated modules in the same file; physical view qualification remains owner-audited.')
    leaves=[]
    def add(clock,master,path,role,region=None,**kw):
        leaves.append(dict(clock=clock,master=master,path=path,role=role,region=region,
            clock_pin='ck'if master in('qfd_vm_qcommit','UNPARTITIONED_VM_RESIDUAL')else'clk',
            selected_module=module_identity.get(master),physical_home=None,source_equivalent_physical_view=None,candidate_recipe_views=recipes.get(master,[]),**kw))
    for r in range(8):
        base=f'u_vm.g_tile.g_t[{r}].u_t'
        for b in range(8):
            for off,master,path,role in [(0,'ot_qfd_vm_bctl_nx',f'g_b[{b}].u_bc','copy0_control'),
                (1,'ot_qfd_vm_delay2_t',f'g_b[{b}].g_wd.u_wd','copy0_write_relay'),
                (2,'ot_qfd_vm_bank_t',f'g_b[{b}].u_bt','copy0_row_bank'),
                (3,'ot_qfd_vm_delay1_t',f'g_b[{b}].g_bx.u_bx','copy0_row_return_relay')]:
                add(lc[56*r+4*b+off],master,base+'.'+path,role,r,global_copy0_bank=8*r+b,
                    parameters=dict(DEPTH=174,LAW=8)if off==2 else {})
        for c,operand in enumerate('ABC'):
            for j in range(2):
                for off,master,path,role in [(0,'ot_qfd_vm_sctl_t',f'g_c[{c}].g_j[{j}].u_sc','operand_bank_control'),
                    (1,'ot_qfd_vm_delay2_t',f'g_c[{c}].g_j[{j}].g_sd.u_sd','operand_write_relay'),
                    (2,'ot_qfd_vm_su_t',f'g_c[{c}].g_j[{j}].u_st','operand_replica_row_bank')]:
                    add(lc[56*r+32+3*(2*c+j)+off],master,base+'.'+path,role,r,operand=operand,
                        replica_bank=2*r+j,parameters=dict(NSB=1,DEPTHS=695,LAWS=10)if off==2 else {})
            add(lc[56*r+50+c],'ot_qfd_vm_su1024_t',base+f'.g_su_leaf[{c}].u_su','operand_region_return',r,
                operand=operand,replica_banks=[2*r,2*r+1],region_return_bits=1024)
        for h in range(2):add(lc[56*r+53+h],'ot_qfd_vm_rr4_t',base+f'.g_r4[{h}].u_r4','row_read_first_rung',r,global_copy0_banks=list(range(8*r+4*h,8*r+4*h+4)))
        add(lc[56*r+55],'ot_qfd_vm_rr2_nx',base+'.u_r2','row_read_second_rung',r)
        for b in range(8):
            g=8*r+b
            if g in oc:add(oc[g],'qfd_vm_qcommit',base+f'.g_qcommit[{b}].g_qbank.u_obs','actual_write_commit_observer',r,
                global_copy0_bank=g,external_commit_index=g-24,q_coverage=g<56,attention_coverage=g>=31)
    add('ck','UNPARTITIONED_VM_RESIDUAL','u_vm + top-level Q/control','main_residual',
        resident_functions=['SU three descriptor pipelines and per-bank read registers','SU per-operand coarse/fine rotate and final3x2048 outputFF','regional input/output relay state','fixed write distribution and hazards','row read control/return and top Q exporter/slot/fault state'],
        size_estimate=None)
    ports=load_nodes()['vm']['ports'];clocks={p for p,s in ports.items()if s['direction']=='input'and(p=='ck'or p.startswith('ck_'))}
    assert len(leaves)==488 and {x['clock']for x in leaves}==clocks and len(clocks)==488
    return dict(schema='opentallas.qwen.vm-native-leaf-inventory.v1',qualified=False,source_ref=REF,candidate_views_ref=views_ref,
        source_sha256={p:hashlib.sha256(s.encode()).hexdigest()for p,s in source.items()},
        counts=dict(region_leaves=448,write_commit_observers=39,main_residual=1,total_roots=488),leaves=leaves,
        operand_mapping=dict(A='sq[2047:0]',B='sq[4095:2048]',C='sq[6143:4096]',
            replica_banks_per_operand=16,elements_per_row=16,rows_per_64lane_stride1_request_max=5,
            address_rule='element=(base+(stride1?lane:0)); row=floor(element/16); replicaBank=row mod16; region=floor(replicaBank/2)',
            fixed_su_octet_bank_ownership=False,
            note='Actual coarse/fine return rotation and lane selection remain in main ck; no fixed octet-to-bank assignment.'),
        limitations=['Recipe/LEF existence is not selected-source/native qualification.','No old full-VM rectangle or parent-container area used.','No actual per-leaf homes/clock phase/route ages assigned.','Main residual is real registered dataflow, not a proven small glue master.'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(export(),indent=2)+'\n')
if __name__=='__main__':main()
