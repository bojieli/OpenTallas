"""Opt-in C25c manifest fixes; run from the repo root after seed wrapper commit is merged.
usage: update_manifest.py INPUT_MANIFEST OUT_MANIFEST MAP_FILE NETLIST
BASE is the current worktree, no source is read from a Claude worktree.
"""
from pathlib import Path
import json,sys,os
here=Path(__file__).resolve().parent;root=here.parents[1]
a,out,mapfile,netlist=sys.argv[1:5]
d=json.loads(Path(a).read_text());d['base']=str(root);d['netlist']=[netlist]
map_path=Path(mapfile) if Path(mapfile).is_absolute() else root/mapfile
d['map_file']=os.path.relpath(map_path.resolve(),Path(out).resolve().parent)
rel='rtl/hbm_next/bind/ot_hnx_sm_seed_heads.sv'
stree='rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_stree.sv'
current=[stree,rel,'rtl/hbm_next/bind/ot_hnx_selector_eightwide.sv','rtl/hbm_next/bind/ot_hnx_host_boot_hop.sv','rtl/hbm_next/bind/ot_hnx_calendar_cfg_leaf.sv','rtl/hbm_next/bind/ot_hnx_sm_front_nomarker.sv',
 'rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_qhub_static.sv',
 'rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankq_static.sv',
 'rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankq_term_static.sv',
 'rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme_root_h5.sv']
# Existing arithmetic glue literals are not a blanket leaf-pin permission.
d['internal_primitive_constants']=True
for k in ('files','prefer'):
 d[k]=[x for x in d.get(k,[]) if x not in current]+current
d['substitute_inst']=d.get('substitute_inst',[])+json.loads((here/'seed_substitute_inst.json').read_text())+json.loads((here/'selector_substitute_inst.json').read_text())+json.loads((here/'front_marker_substitute_inst.json').read_text())
d['note']=d.get('note','')+' | CODEX C25c: preserve current NLEG/W/PARTS master interfaces; exact chain seed variants; quarter-preserving8wide selector; internal Yosys primitive literals only'
Path(out).write_text(json.dumps(d,indent=1)+'\n')
