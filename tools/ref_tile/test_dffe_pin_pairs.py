#!/usr/bin/env python3
"""Actual 512-bit EN1 mapped-cone oracle and adversarial graph/function edits."""
import argparse
import copy
import json
from pathlib import Path
from recognize_dffe_pin_pairs import Recognizer,Reject,read_module,read_liberty


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--netlist',required=True,type=Path);p.add_argument('--libs',nargs='+',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    mod=read_module(a.netlist,'ot_qfd_vm_face_sn_e1');lib=read_liberty(a.libs)
    baseline=Recognizer(mod,lib).run()
    assert len(baseline['pairs'])==512 and not baseline['rejected']
    assert {x['d'] for x in baseline['pairs']}=={f'd[{i}]' for i in range(512)}
    results={'actual_mapped_512_pairs':'PASS','mutants':{}}
    def edit_pin(m,n,p,net):next(i for i in m.instances if i.name==n).pins[p]=[net]
    def add_sink(m,net):
        i=copy.deepcopy(next(i for i in m.instances if i.name=='_3103_'))
        i.name='illegal_extra_sink';i.pins={'A':[net],'Y':['illegal_new_net']};m.instances.append(i)
    # Actual mapped cone with the recipe's separate output/input hold stages.
    # The feedback tap stays ahead of output-only BUF/HB/BUF, as actual oracle.
    held=copy.deepcopy(mod)
    edit_pin(held,'_1738_','Y','q334_internal')
    edit_pin(held,'_3121_','A','q334_internal')
    def chain(m,src,dst,prefix,kinds):
        for j,kind in enumerate(kinds):
            i=copy.deepcopy(next(i for i in m.instances if i.name=='_3103_'))
            i.name=prefix+str(j);i.cell=kind
            nxt=dst if j==len(kinds)-1 else prefix+'_net'+str(j)
            i.pins={'A':[src],'Y':[nxt]};m.instances.append(i);src=nxt
    chain(held,'q334_internal','q[334]','holdout_',[
        'BUFx4f_ASAP7_75t_R','HB4xp67_ASAP7_75t_R','BUFx4f_ASAP7_75t_R'])
    edit_pin(held,'_3122_','A2','d334_internal')
    chain(held,'d[334]','d334_internal','holdin_',['HB4xp67_ASAP7_75t_R','BUFx4f_ASAP7_75t_R'])
    hr=Recognizer(held,lib).run()
    assert len(hr['pairs'])==512 and not hr['rejected']
    results['mapped_cone_with_separate_hold_chains']='PASS'
    cases={
      'feedback_from_other_bit':lambda m,c:edit_pin(m,'_3121_','A','q[333]'),
      'different_enable_root':lambda m,c:edit_pin(m,'_3104_','A','_0005_'),
      'same_enable_polarity':lambda m,c:edit_pin(m,'_3104_','A','_1518_'),
      'different_data_clock':lambda m,c:edit_pin(m,'q[334]$_DFFE_PP_','CLK','wrong_clock'),
      'extra_feedback_sink':lambda m,c:add_sink(m,'q[334]'),
      'extra_AND_output_sink':lambda m,c:add_sink(m,'_1554_'),
      'extra_FF_D_sink':lambda m,c:add_sink(m,'_0944_'),
      'data_is_other_output':lambda m,c:edit_pin(m,'_3122_','A2','q[333]'),
      'shared_data_input':lambda m,c:edit_pin(m,'_3122_','A2','d[333]'),
      'wrong_AO21_function':lambda m,c:c['AO21x1_ASAP7_75t_R']['pins']['Y'].update(function='A1 + A2 + B'),
      'wrong_AND2_function':lambda m,c:c['AND2x2_ASAP7_75t_R']['pins']['Y'].update(function='A + B'),
      'unknown_function':lambda m,c:c['AO21x1_ASAP7_75t_R']['pins']['Y'].update(function=None),
      'wrong_FF_state_polarity':lambda m,c:c['DFFHQNx1_ASAP7_75t_R']['ff'].update(next_state='D'),
      'ME_registered_from_other_input':lambda m,c:edit_pin(m,'g_me[2].me_r$_DFF_P_','D','d[300]'),
    }
    for name,change in cases.items():
        m=copy.deepcopy(mod);c=copy.deepcopy(lib);change(m,c)
        try:
            r=Recognizer(m,c).run()
            assert 'q[334]' not in {x['q'] for x in r['pairs']},name
            reason=r['rejected'].get('q[334]','ambiguous pair set')
        except Reject as e:reason=str(e)
        results['mutants'][name]={'status':'REJECT','reason':reason}
    a.out.write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))


if __name__=='__main__':main()
