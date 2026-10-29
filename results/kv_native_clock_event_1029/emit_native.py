from pathlib import Path
import re,json,sys,shutil
sys.path.insert(0,'tools/die_plan')
import die_trial as D
old=Path('/srv/opentallas-scratch2/claude/die-kv-21-1028/kit_c/clock')
out=Path('native_source');out.mkdir(exist_ok=True)
t=json.load(open('body_pack02/tree_native.json'));seen=set()
s=(old/'ctree.tcl').read_text()
def repl(m):
 n=m.group(1);seen.add(n);x,y=t['sites'][n];return f'ot_place {{{n}}} {x:.6f} {y:.6f} R0'
s,n=re.subn(r'place_inst -name (\S+) -location \{[^}]+\} -status PLACED',repl,s)
assert seen==set(t['sites']),(len(seen),len(t['sites']))
s=s.replace('read_verilog /work/clock/ctree.v','read_verilog /work/ctree.v')
s=D.PLACE_PROC+'\n'+s
# Native clock base only: retain exact old real tap/root ports; no stale provider stage ports.
shutil.copyfile(old/'ctree.v',out/'ctree.v');(out/'ctree.tcl').write_text(s)
z=s[:s.index('set_wire_rc -signal')]+ '\nwrite_db /work/clock_native.odb\nputs NATIVE_CLOCK_SOURCE_DONE\nexit\n'
(out/'source_only.tcl').write_text(z)
print('NATIVE_EMIT_DONE',n,flush=True)
