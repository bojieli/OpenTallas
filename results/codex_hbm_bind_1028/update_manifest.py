"""Opt-in C25c manifest fixes; run from the repo root after seed wrapper commit is merged.
usage: update_manifest.py INPUT_MANIFEST OUT_MANIFEST MAP_FILE NETLIST
BASE is the current worktree, no source is read from a Claude worktree.
"""
from pathlib import Path
import argparse,json,sys,os,re
here=Path(__file__).resolve().parent;root=here.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
for field in ('input','output','mapfile','netlist'):parser.add_argument(field)
parser.add_argument('--scorer-children',action='store_true',help='Use exact existing HCOL/tail source packet')
parser.add_argument('--np4-keybuf',action='store_true',help='Select qualified sliced source definitions; top must select sliced quarter')
parser.add_argument('--su-boundaries',action='store_true',help='Only selected KIND0/1 SIDE-zero and D0 source boundaries; FULL KIND2 is rejected')
args=parser.parse_args();a,out,mapfile,netlist=args.input,args.output,args.mapfile,args.netlist
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
extra_rules=[]
if args.scorer_children:
 current+=['rtl/hbm_next/bind/ot_hnx_idx_hcol_plan.sv']
 extra_rules+=json.loads((here/'scorer_exact_packet.json').read_text())['substitute_inst']
if args.np4_keybuf:
 current+=['rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_sliced_np4.sv','rtl/hbm_next/idxn/ot_hnx_idxn_quarter_with_keybuf_sliced.sv']
 d['dissolve']=list(dict.fromkeys(d.get('dissolve',[])+['ot_hnx_idxn_keybuf_sliced_np4','ot_hnx_idxn_quarter_with_keybuf_sliced']))
 # Exactly the actual sixteen proven position IDs; actual source bits are still
 # resolved and checked by Graph and the typed physical ID descriptor frontdoor.
 d['straps']=list(dict.fromkeys(d.get('straps',[])+[re.escape(x['source_path']+'.strap_lane_id') for x in json.loads((here/'keybuf_active_map.json').read_text())['active']]))
if args.su_boundaries:
 current+=['rtl/hbm_next/bind/ot_hnx_su_boundaries.sv']
 extra_rules+=json.loads((here/'su_boundary_substitute_inst.json').read_text())
# Existing arithmetic glue literals are not a blanket leaf-pin permission.
d['internal_primitive_constants']=True
for k in ('files','prefer'):
 d[k]=[x for x in d.get(k,[]) if x not in current]+current
d['substitute_inst']=d.get('substitute_inst',[])+json.loads((here/'seed_substitute_inst.json').read_text())+json.loads((here/'selector_substitute_inst.json').read_text())+json.loads((here/'front_marker_substitute_inst.json').read_text())+extra_rules
d['note']=d.get('note','')+' | CODEX C25c: preserve current NLEG/W/PARTS master interfaces; exact chain seed variants; quarter-preserving8wide selector; internal Yosys primitive literals only'
Path(out).write_text(json.dumps(d,indent=1)+'\n')
