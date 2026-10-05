#!/usr/bin/env python3
"""Emit one reverse-bank-row physical recipe from immutable Kant759 inputs.

No engine/wrapper edits or physical tools. Pauli's sole launch helper consumes
these inputs and the already-mapped frozen banklocal context.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FROZEN='759205d6acbef7a723bea8b80d45f351fa9b5085'
BASE=Path('results/uarch/hbm_accel_fulldie_inputs_20261004/code_pair_slot')
OUT=Path('results/uarch/hbm_accel_fulldie_inputs_20261004/code_pair_reversebanks')


def emit(root=ROOT):
    out=root/OUT;out.mkdir(parents=True,exist_ok=True)
    origins={}
    def raw(name):
        p=BASE/name
        b=subprocess.check_output(['git','show',FROZEN+':'+str(p)],cwd=root)
        origins[str(p)]=hashlib.sha256(b).hexdigest()
        return b.decode()
    def obj(name):return json.loads(raw(name))
    model=obj('model.json')
    assert model['die_xyxy_um']==[0,0,864,673.92]
    assert model['macro_count']==20
    def delta(b):return (4-2*b)*96.66
    for m in model['macro_inventory']:
        b=int(re.search(r'\.bank\[(\d+)\]',m['instance'])[1])
        m['box_xywh_um'][1]=round(m['box_xywh_um'][1]+delta(b),6)
    mp=obj('macro_pins.json')
    for pin in mp:
        b=int(re.search(r'\.bank\[(\d+)\]',pin['instance'])[1]);pin['xy_um'][1]=round(pin['xy_um'][1]+delta(b),6)
    captures=obj('capture_bit_locality.json')
    for c in captures:
        dy=delta(c['bank']);c['preferred_capture_D_xy_um'][1]=round(c['preferred_capture_D_xy_um'][1]+dy,6)
        if c['source_pin']:c['source_pin']['xy_um'][1]=round(c['source_pin']['xy_um'][1]+dy,6)
    for r in model['bank_local_capture_candidate']['local_placement_regions']:
        b=int(re.search(r'\.bank(\d+)\.',r['name'])[1]);r['box_xywh_um'][1]=round(r['box_xywh_um'][1]+delta(b),6)
    model.update(variant='kant-code-pair-banklocal-reversebanks-r1',
        frozen_input_commit=FROZEN,actual_bank_row_order_bottom_to_top=[4,3,2,1,0],
        physical_execution_authorized_by='/tmp/claude-review-20261003/CODEX_DIRECTIVE_20261005_parallel_fanout.md',
        execution_authorization_supersedes_pricing_only_hold=True,
        existing_unplaced_timing_failure_preserved=True,
        route_result_measured=False,physical_fit=False,
        Pauli_scope='sole wrapper/engine-selection/launch-helper and physical-flow writer',
        Kant_scope='one independent physical recipe execution, macro/locality input only',
        engine_and_wrapper_changed=False,source_identity='banklocal8b713f7c +pipelinebdbfd5c9 +context633ae741',
        mapped_objects_reuse_required=True,registry_name='kant-code-pair-banklocal-reversebanks-r1')
    for n,v in [('model.json',model),('macro_pins.json',mp),('capture_bit_locality.json',captures)]:
        (out/n).write_text(json.dumps(v,indent=2)+'\n')
    for n in ['floorplan.tcl','pins.tcl','boundary_pins.json','boundary.sdc','timing_paths.json']:
        (out/n).write_text(raw(n))
    # Retain required API/ownership assertions, change only literal row Y.
    macros=raw('macros.tcl')
    for m in model['macro_inventory']:
        b=int(re.search(r'\.bank\[(\d+)\]',m['instance'])[1]);old_y=m['box_xywh_um'][1]-delta(b)
        old=f"-location {{{m['box_xywh_um'][0]:.6f} {old_y:.6f}}}"
        new=f"-location {{{m['box_xywh_um'][0]:.6f} {m['box_xywh_um'][1]:.6f}}}"
        lines=macros.splitlines()
        count=0
        for i,line in enumerate(lines):
            if '{'+m['instance']+'}' in line:
                assert old in line;lines[i]=line.replace(old,new);count+=1
        assert count==1;macros='\n'.join(lines)+'\n'
    (out/'macros.tcl').write_text(macros)
    local=raw('local_capture_regions.tcl').replace('8.64+$b*96.66','8.64+(4-$b)*96.66')
    (out/'local_capture_regions.tcl').write_text(local)
    for m in model['macro_inventory']:
        x,y,w,h=m['box_xywh_um'];assert 8.64<=x and x+w<=855.36 and 8.64<=y and y+h<=665.28
    assert len(model['macro_inventory'])==20 and len(captures)==2880
    assert {m['instance'] for m in model['macro_inventory']}=={p['instance'] for p in mp}
    model['frozen_input_sha256']=origins
    (out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    print(json.dumps(dict(variant=model['variant'],macro_count=20,frozen=FROZEN,rows=[4,3,2,1,0],source_changed=False)))


if __name__=='__main__':emit()
