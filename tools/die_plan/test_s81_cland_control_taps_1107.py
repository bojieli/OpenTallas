#!/usr/bin/env python3
"""Source scope fixture using exact original t36 synth instance names; no STA."""
import ast, pathlib, subprocess
p=pathlib.Path(__file__).with_name('s81_cland_control_taps_1107.py')
s=p.read_text(); tree=ast.parse(s)
g=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GROUP_RE' for t in n.targets))
assert "export OT_TAP_FOLLOW_RE =\\n" in s, 'constructor must explicitly suppress dormant reset followers'
names={
 'control': 'u_bound.u_cland_ft0_i/count[0]$_SDFFE_PN0P_',
 'payload': 'u_bound.u_cland_ft0_i/u_ring.s_d[0][0]$_DFFE_NP_',
 'ft': 'u_bound.u_ft_ft0_o_0/_1106_',
 'reset': 'u_bound.u_rrl_0/_1_',
}
tcl='set group {'+g+'}\nset follow {}\n'
for key,name in names.items():
 expected=1 if key=='control' else 0
 tcl+='set n {'+name+'}\n'
 tcl+='if {[regexp -- $group $n] != '+str(expected)+'} {error {group scope '+key+'}}\n'
 tcl+='if {$follow ne "" && [regexp -- $follow $n]} {error {followers must remain inactive}}\n'
tcl+='puts {PASS 4 actual names: control grouped; payload/FT/reset untargeted; followers inactive}\n'
r=subprocess.run(['tclsh'],input=tcl,text=True,capture_output=True,check=True)
assert 'PASS 4' in r.stdout, r.stderr
print(r.stdout.strip())

# Constructor-level default identity and combined-spacing fixture (source only).
import tempfile
base_config='export OT_TAP_MAX_SINKS = 1500\nexport OT_TAP_TARGET_PS = 250\nexport OT_TAP_WINDOW = 140.0000\nexport OT_CLAND_PINSLOT = 1\n'
anchor='set pinx [cland_place_pinslot_col $ordered $rect $xt $ppins $rev $psp 1]'
yanchor='  lassign [cland_place_pinslot $ordered $rect $tag $sp $ppins $rev $ypsp] na nr how'
landing='u_cland_ft0_i {1401.84000 17.28000 1425.60000 246.10800}\nu_cland_ft1_i {1404.00000 247.29600 1425.60000 487.26000}\n'+anchor+'\n'+yanchor+'\n'
for combined in (False,True):
 d=pathlib.Path(tempfile.mkdtemp(prefix='codex-cland-source-fixture-'))
 (d/'config.mk').write_text(base_config); (d/'clock_taps.tcl').write_text('OT_TAP_GROUP_RE'); (d/'landing_placement.tcl').write_text(landing)
 cmd=['python3','-I',str(p),str(d),'--apply']
 if combined: cmd+=['--north-face-rows','2','--east-spacing','1.25']
 subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
 out=(d/'landing_placement.tcl').read_text()
 assert 'export OT_TAP_FOLLOW_RE =\n' in (d/'config.mk').read_text()
 if not combined: assert out==landing
 else:
  assert anchor[:-2]+'2]' in out
  assert '{1395.90000 17.28000 1425.60000 246.10800}' in out
  assert '{1398.60000 247.29600 1425.60000 487.26000}' in out
  assert '$prefix in {u_cland_ft0_i u_cland_ft1_i}' in out
  assert out.count('cland_place_pinslot $ordered $rect')==1
print('PASS constructor default unchanged + combined exact N/E geometry')
