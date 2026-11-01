#!/usr/bin/env python3
"""Derive raw-native isolated Pstore profile, preserving the wrapped diagnostic cut."""
import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);o=a.out/'cut';shutil.copytree(a.input,o,dirs_exist_ok=True)
T='ot_hgi_sfu_programme_store_r10'
def read(n):return json.loads((o/n).read_text())
def write(n,d):(o/n).write_text(json.dumps(d,indent=2)+'\n')
m=read('core_macros.json');r=read('recipe.json');assert len(m['cores'][T]['macros'])==44 and len(r[T]['register_guides'])==51
for q in m['cores'][T]['macros']:
 assert q['name'].startswith('u_fcore.');q['name']=q['name'].removeprefix('u_fcore.')
for g in r[T]['register_guides']:
 assert all(x.startswith('u_fcore.') for x in g['prefixes']);g['prefixes']=[x.removeprefix('u_fcore.') for x in g['prefixes']]
m['cores'][T]['basis']+=' | RAW NATIVE C11E body: no generic face shell'
r[T]['source']+=' | RAW NATIVE C11E body; require --face-shell off and existing native guard; nativeD5/status3, no shell latency credit'
write('core_macros.json',m);write('recipe.json',r)
s=read('source_model.json');s.update(profile='raw_native_pstore',generic_face_shell=False,required_generator_arguments=['--face-shell','off'],native_guard_required=True,generic_shell_cycle_credit=0);s['pipeline'].update(io_word_latency=5,status_latency=3);s['qualification']='native-body child prototype pending; existing native guard required; wrapped trial remains diagnostic only';write('source_model.json',s)
d=read('die_plan.json');d['note']+=' | RAW NATIVE C11E body, --face-shell off REQUIRED, existing native guard REQUIRED; no generic +1/+1 shell or cycle credit';write('die_plan.json',d)
profile=dict(schema='opentallas.pstore.native_profile.v1',top=T,cut='cut',generator='physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py',required_arguments=['--face-shell','off'],native_guard='tools/die_plan/face_guard.py through ordinary run_kit_hbm.sh after make synth; retain unchanged, never bypass failures',macros=44,guide_regions=51,macro_names_native=True,guide_prefixes_native=True,outline_um=[673.92,803.52],native_data_latency=5,native_status_latency=3,generic_face_shell=False,generic_shell_cycle_credit=0,rtl_source_change=False,added_cycles=0,parent_adoption=False)
write('../native_profile.json',profile);print(json.dumps(profile,indent=2))
