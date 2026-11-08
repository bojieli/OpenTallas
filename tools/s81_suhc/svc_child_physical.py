#!/usr/bin/env python3
"""Generate one private SVC child kit from captured, committed production RTL."""
import argparse,importlib.util,json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[2]
def main():
 a=argparse.ArgumentParser();a.add_argument('--child',required=True,choices=['native_smd','merge_h4_pin','native_sml_c','native_smd_b','merge_h4_pin_b','native_smd_c','native_smd_d']);a.add_argument('--out',required=True);a.add_argument('--hold-safe-shift',action='store_true',help='S81-RCK-9: F4 PAIR + OT_F4_XLEAF_HOLD_PS=10 + OT_F4_XLEAF_GATE1=1 (zero-logic and one-gate cross-leaf pairs); default for later SVC forms');x=a.parse_args();out=pathlib.Path(x.out).resolve();assert not out.exists(),'fresh output root required'
 d=R/'results/physical/codex_svc_hardening_1551'/{'native_smd_d':'native_smd_c'}.get(x.child,x.child);profile=json.load(open(d/'profile.json'));profile['source_commit']=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip();recipe=json.load(open(d/'recipe.json'));view=json.load(open(d/'views.json'))['view_list'][0]['view'];key={'native_smd':'codex_svc_native_smd','merge_h4_pin':'codex_svc_merge_h4_pin','native_sml_c':'codex_svc_native_sml','native_smd_b':'codex_svc_native_smd','merge_h4_pin_b':'codex_svc_merge_h4_pin','native_smd_c':'codex_svc_native_smd','native_smd_d':'codex_svc_native_smd'}[x.child]
 here=R/'physical/die_plan/hbm_arch_cores';sys.path.insert(0,str(here));spec=importlib.util.spec_from_file_location('svc_private_hbc',here/'gen_core_kit_hbm.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
 sys.argv=[str(g.__file__),'--views',str(d/'views.json'),'--view',view,'--out',str(out),'--corner','TC','--util','0.40','--sigmax','M6','--face-shell','off','--clock-pin-entry','on','--trial']
 # S81-RCK-8 form C: co-leaf every zero-logic capture with its launch (kit8p 158 internal FF holds on shift pairs)
 if x.child in ('native_sml_c','native_smd_c','native_smd_d'):sys.argv+=['--orfs-var','OT_F4_PAIR=1']
 # S81-RCK-9 form D (hold-safe shift form, the generator class fix for later SVC builds): F4 PAIR + a +10 ps route-repair
 # hold target on the cross-leaf zero-logic captures F4 could not co-leaf (SMD-C/SML-C routed residue -5.58/36, -3.88/60)
 if x.child=='native_smd_d':sys.argv+=['--orfs-var','OT_F4_XLEAF_HOLD_PS=10']
 if x.hold_safe_shift:sys.argv+=['--orfs-var','OT_F4_PAIR=1','--orfs-var','OT_F4_XLEAF_HOLD_PS=10','--orfs-var','OT_F4_XLEAF_GATE1=1']
 g.main(recipe_overrides={key:recipe},source_overrides={f:str(R/f)for f in recipe['files']},source_profile=profile)
if __name__=='__main__':main()
