#!/usr/bin/env python3
"""Fresh Wi physical kit: complete existing SRAM provider and land all ADP PG."""
from pathlib import Path
import shutil, json, re

r=Path('/srv/opentallas-scratch3/claude/codex-wi-native-1107')
old=r/'native_gen_v3/kv3_hub_Wi'
new=r/'place3/kv3_hub_Wi'
assert not new.exists()
new.parent.mkdir(parents=True,exist_ok=True)
shutil.copytree(old,new,ignore=shutil.ignore_patterns('run','*.log'))
module='ot_sram_1r1w_64x512_m1_r2c2'
provider=Path('/srv/opentallas-scratch3/claude/kv-slgland-2/wt/physical/asap7_memory_macros_v2')/module
for suffix in ['.lef','_tt.lib','_ff.lib']:
    shutil.copy2(provider/(module+suffix),new/'macros'/(module+suffix))
shutil.copy2('/srv/opentallas-scratch3/claude/codex-wi-adp-abstract-b0-1107/qkd_hr_phy_adp.lef',new/'macros/qkd_hr_phy_adp.lef')
cfg=new/'config.mk'
s=cfg.read_text()
s+='\n# Private complete embedding SRAM provider, same existing RTL master.\n'
s+=f'export ADDITIONAL_LEFS += /work/macros/{module}.lef\n'
s+=f'export TC_LIB_FILES += /work/macros/{module}_tt.lib\n'
s+=f'export BC_LIB_FILES += /work/macros/{module}_ff.lib\n'
s+=f'export ADDITIONAL_LIBS += /work/macros/{module}_tt.lib\n'
cfg.write_text(s)
with (new/'macro_place.tcl').open('a') as f:
    f.write('\n# Private new site, actual aligned-v2 SRAM, 495 retained reservations clear.\n')
    f.write('place_macro -macro_name {u_bound.u_kvs_emb.u_rowtx.u_row} -location {1019.5200 622.0800} -orientation R0 -exact\n')

# Canonical PG-CORECONN form: ADP M5->M6 and SRAM M4->M5. New detailed
# ADP/ING upper OBS are actual shapes; pdngen must measure actual via access.
pdn=new/'pdn.tcl';s=pdn.read_text()
patterns=' '.join('{^u_bound\\.u_host\\.u_native_parent\\.host__qkd_hr_phy_adp_'+str(i)+'$}' for i in range(8))
line=next(l for l in s.splitlines() if l.startswith('define_pdn_grid -macro -name {core_pg_M5}'))
replacement=line.replace('} -voltage_domains',' '+patterns+'} -voltage_domains')
assert replacement!=line
s=s.replace(line,replacement)
s+='\n# Actual embedding SRAM PG interface on M4, no skipped supply pins.\n'
s+='define_pdn_grid -macro -name {core_pg_M4} -instances {{^u_bound\\.u_kvs_emb\\.u_rowtx\\.u_row$}} -voltage_domains {CORE} -halo {0}\n'
s+='add_pdn_connect -grid {core_pg_M4} -layers {M4 M5}\n'
pdn.write_text(s)

# Keep the completed mapped netlist, not the failed synth-ODB or logs. New
# provider geometry changes no RTL, cell mapping, blackbox ABI or net names.
rel=Path('run/results/asap7/dp_kv3_hub_Wi/base')
(new/rel).mkdir(parents=True)
for p in (old/rel).iterdir():
    if p.is_file() and p.suffix in {'.v','.sdc','.json'}: shutil.copy2(p,new/rel/p.name)
assert (new/rel/'1_2_yosys.v').exists()
shutil.copy2(r/'native_gen_v3/run_kit.sh',new.parent/'run_kit.sh')
(new/'resume.json').write_text(json.dumps(dict(start='floorplan',reused_steps=['synth'],
    source=dict(host='epyc4',kit=str(old)),note='Only mapped netlist reused; new synth-ODB is built with complete real providers before runner'),indent=2))
print(new)
