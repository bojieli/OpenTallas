"""Apply only measured SerDes geometry/census; keep PMA period and routed-view adoption held.
usage: python apply_serdes_geometry.py INPUT_DIR
Writes source_plan.json, source_sidecar.json and a new relative child pin file.
PMA role template is a sidecar hold, never a periodless clock.pad_clock source declaration.
"""
import json,sys,shutil
from pathlib import Path
r=Path(sys.argv[1]);here=Path(__file__).resolve().parent
pp=r/'source_plan.json';sp=r/'source_sidecar.json';p=json.load(pp.open());s=json.load(sp.open()) if sp.exists() else {}
o=json.load((here/'source_overlay.json').open());t=p['partition_types']['hd_serdes']
t['cells']=o['cells']
c=dict(o['hard_cores'][-1]);c.pop('cells',None)
c['note']='ACTUAL PLACE/GRT50+CTS PASS-COND, NOT SIGNED:189510 native synth cells; exact945 pins; outline276.48x138.24 fits150um digital CORE VDD strip. Recovered pma_rck clock domain, never parent clk. Matching new routed LEF/TT/FF libraries pending; no old216x194.4 view substitution.'
h=[x for x in t.get('hard_cores',[]) if x['inst']!=c['inst']];h.append(c);t['hard_cores']=h
old=t.get('note','');tag='CODEX_SERDES_COMPONENT_CENSUS'
if tag not in old:t['note']=old+'; '+tag+':422104=232594shell+189510KP4 raw synth cells. ShellFF clk10303/fclk_in_coll_i02086/pma_rck13509; KP4 own3237FF recovered-domain only. Do not assign RX/forwarded demand to core clock grid; PMA period and clock-pad adoption OWNER held.'
(r/'core_pins').mkdir(exist_ok=True);shutil.copyfile(here/'plan_pins.json',r/'core_pins/kp4_276x138_pins.json')
s['codex_serdes_geometry']=o
s['codex_serdes_geometry']['clock_domain_binding']={ 'kind':'actual_native_clock_nets', 'native_shell_ff':{'clk':10303,'fclk_in_coll_i0':2086,'pma_rck':13509}, 'child_internal_ff':{'root':'pma_rck','inst':c['inst'],'count':3237}, 'parent_macro_clocks':[{'inst':x['inst'],'pin':x['pin'],'source_clock_port':'pma_rck'} for x in o['clock_domains']['recovered']['macro_clock_pins']], 'exclude_from_core_grid':['pma_rck','fclk_in_coll_i0'], 'spatial_inventory':'unplaced synthesis only; no measured bins', 'source_boot_delta':'add actually emitted new reset/start FF by actual clock root' }
s['codex_serdes_geometry']['pad_clock_hold']={'helper':'codex/pma-clock-1030@2afca0b80','adopted':False,'reason':'reviewed PMA period/source authority pending; no period default or RX clock qualification', 'pins':[{'name':'pma_rck','dir':'in','period_ps':None,'source':None,'layer':'M7','xy_um':[1106.528,149.728],'sink_pins':[{'module':'ot_s81_kp4_dchn','pin':'clk'},{'module':'ot_sram_1r1w_32x546_m1','pin':'clk'},{'module':'ot_sram_1r1w2c_64x546_m1','pin':'wclk'},{'module':'ot_sram_1r1w2c_64x546_m1','pin':'rclk'}]},{'name':'pma_tck','dir':'out','period_ps':None,'source':None,'source_clock_port':'clk','layer':'M7','xy_um':[1443.488,149.728]}]}
prep=here/'parent_tree_prep'/'recipe.json'
if prep.exists():
 shutil.copyfile(prep,r/'serdes_parent_tree_prep.json');s['codex_serdes_geometry']['physical_tree_geometry_prep_file']='serdes_parent_tree_prep.json'
pp.write_text(json.dumps(p,indent=1)+'\n');sp.write_text(json.dumps(s,indent=1)+'\n')
print('APPLIED SerDes third core/native census; separate-root binding in sidecar; PMA period/routed views HELD')
