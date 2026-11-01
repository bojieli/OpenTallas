from pathlib import Path
import copy
import json
import sys
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tools/clk'))
import ot_clk as O
import mesh_form as MF
base=O.load_config(root/'tools/clk/configs/hbm_hubmesh_a3e6sf.yaml')['region']['mesh']
for side in ['NW','NE']:
    config=copy.deepcopy(base)
    config.update(core_geometry='contents_and_hard_cores',core_keepout=2.16)
    config['grid'].update(legal_max_um=600,rep_max_um=360)
    config['ndr'].update(width=.04)
    config['ndr'].pop('fat_vias',None)
    out=root/'geometry'/side
    out.mkdir(parents=True,exist_ok=True)
    (out/'config.json').write_text(json.dumps(config,indent=2))
    print('START',side,flush=True)
    try:
        result=dict(status='GEOMETRY_ONLY_NOT_ROUTED',summary=MF.build(root/'current_C11E_plan.json',root/'C12e_tree.json',side+'_hub',out,config))
    except Exception as exc:
        result=dict(status='FAIL',error=type(exc).__name__+': '+str(exc))
    (out/'result.json').write_text(json.dumps(result,indent=2))
    print(side,result,flush=True)
