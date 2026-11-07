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
