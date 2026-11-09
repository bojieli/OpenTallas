#!/usr/bin/env python3
"""HBM-Q2NF-RF vE: plan outline + plan pins + vD RTL/netlist; macros off the W/N faces, M4-on-track y. Stages kit, never launches."""
import shutil,json,re,hashlib,sys
from pathlib import Path
SRC=Path('/srv/opentallas-scratch2/claude/die-hbm-92-open/q2nf/vd1/kit_vD')
PLAN=Path('/srv/opentallas-scratch2/claude/die-hbm-89/q2nf/kits/ot_q2nf_rest_vA1/ot_q2nf_rest_420e7cd7fa90')
OUT=Path(sys.argv[1])
assert not OUT.exists()
skip={'run','lec','lec_vd','lec_vd_r1','views','signoff','__pycache__','face_shell_work','lec_cone'}
shutil.copytree(SRC,OUT,ignore=lambda p,n:[x for x in n if x in skip or x.startswith('FAIL_') or x.endswith(('.log','.rc')) or x in('placed.csv','ot_face_flops.txt','hold_census.txt','dtap.txt','face_guard.json','CTSGRT_DONE.txt','PLACE_DONE.txt') or x.startswith('run_vd') or x.startswith('vd_inner') or x.startswith('postcts_gate')])
# netlist checkpoint (source-identical)
BASE='run/results/asap7/hbc_ot_q2nf_rest/base'
(OUT/BASE).mkdir(parents=True)
for f in ['1_2_yosys.v','1_2_yosys.sdc','1_synth.v','1_synth.odb','1_synth.sdc','clock_period.txt','mem.json']:
    shutil.copy2(SRC/BASE/f,OUT/BASE/f)
for f in ['io.tcl','pins.json','plan_pins.json']:
    (OUT/f).unlink(missing_ok=True); shutil.copy2(PLAN/f,OUT/f)
if (OUT/'candidate_geometry.json').exists(): (OUT/'candidate_geometry.json').unlink()
# config: restore plan outline, M5 ceiling; density as vD
W,H=786.24,622.08
cfg=(OUT/'config.mk').read_text()
(OUT/'config.mk').unlink()
cfg+=f"""
# HBM-Q2NF-RF vE (2026-11-08): plan outline + plan pins, macros off the pin faces, y on M4 tracks; no RTL/netlist change vs vD (PIN CYCLES 0).
override export DIE_AREA = 0 0 {W} {H}
override export CORE_AREA = 4.32 4.32 781.92 617.76
override export MAX_ROUTING_LAYER = M5
override export PLACE_DENSITY = 0.40
"""
(OUT/'config.mk').write_text(cfg)
# freeze: plan outline, plan pins
f=json.loads((OUT/'freeze.json').read_text()); p=json.loads((PLAN/'freeze.json').read_text())
f['outline_um']=[W,H]
for k in ('pins_file','pins_sha256','pins_canon_sha256','pins','plan','plan_sha256'): f[k]=p[k]
f.pop('candidate_only',None); f.pop('candidate_geometry',None)
f['form']='vE plan outline/plan pins/M5, macros off faces (HBM-Q2NF-RF 2026-11-08)'
(OUT/'freeze.json').unlink(); (OUT/'freeze.json').write_text(json.dumps(f,indent=1)+'\n')
# macros
def snap(y): return round(round((y-0.012)/0.048)*0.048+0.012,3)
LB=r'u_fcore.u_x.u_body.g_link\[%d\].u_link.g_bank\[%d\].u_store.u_native.u_sram'
ISS=r'u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[%d\].u_bank.u_sram_%s'
META=r'u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[%d\].u_sram'
FLOW='u_fcore.u_x.u_body.g_q2.n_u_fj.u_fj.u.u_program.g_fsram.u_flow'
G256='ot_sram_1r1w_256x256_m2_r0c0_g256'; L64='ot_sram_1r1w_64x141_m1_r0c0_g141'; M64='ot_sram_1rw_256x64_m4_r2c2'
m=[]
for i,y in enumerate([239.004,317.004,405.996,483.996]):
    m.append((LB%(0,i),L64,133.008,y)); m.append((LB%(1,i),L64,597.024,y))
stack=[ISS%(0,'lo'),ISS%(0,'hi'),ISS%(1,'lo'),ISS%(1,'hi'),ISS%(2,'lo'),ISS%(2,'hi')]
for i,inst in enumerate(stack): m.append((inst,G256,308.4,snap(56.0+40.392*i)))
my=snap(303.0)
for inst,x in zip([META%1,META%0,META%2,META%3],[195.0,272.4,349.8,427.2]): m.append((inst,M64,x,my))
m.append((FLOW,M64,504.6,my))
txt=['# HBM-Q2NF-RF vE: plan outline/pins; macros off W+N faces, issuer stack south, y on M4 tracks (y = 0.012 mod 0.048).','foreach {inst master x y orient} {']
for inst,mast,x,y in m:
    assert abs(((y-0.012)/0.048)-round((y-0.012)/0.048))<1e-6,inst
    txt.append('  {%s} %s %.3f %.3f R0'%(inst,mast,x,y))
txt+=['} {','  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact','}']
(OUT/'macro_placement.tcl').unlink(); (OUT/'macro_placement.tcl').write_text('\n'.join(txt)+'\n')
assert len(m)==19
# markers
(OUT/'DO_NOT_COUNT').unlink(missing_ok=True); (OUT/'DO_NOT_COUNT').write_text('DO_NOT_COUNT until sign-off: HBM-Q2NF-RF vE (plan outline, plan pins, right-width macros, vD RTL)\n')
(OUT/'SOURCE_REUSE.json').write_text(json.dumps(dict(source_kit=str(SRC),plan_pins_from=str(PLAN),rtl='c2d955fe (vD)',netlist='vD 1_2_yosys.v unchanged',lec='vD kit EQUIVALENT 102366/102366 same netlist/RTL',new_pin_cycles=0))+'\n')
print('STAGED',OUT,len(m),'macros', 'pins',len(json.loads((OUT/'pins.json').read_text())))
