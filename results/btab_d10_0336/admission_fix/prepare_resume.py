from pathlib import Path
import re,json,sys,hashlib
b=Path('/srv/opentallas-scratch2/claude/codex-btab-0336');sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-collft-0336/tools/autopilot');import geom_rules as G
D=G.Design(b/'geomB50r1/geom.tsv')
def records(p):
 r={}
 for n,l,x,y in re.findall(r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}',p.read_text()):r[n]=(l,float(x),float(y))
 return r
old=records(b/'variantB/io.tcl');new=records(b/'variantC/io.tcl');actual={p['name']:(p['layer'],p['x'],p['y']) for p in D.pins}
bad=[(n,v,actual.get(n)) for n,v in new.items() if n not in actual or v[0]!=actual[n][0] or abs(v[1]-actual[n][1])>.0001 or abs(v[2]-actual[n][2])>.0001]
r=dict(source_IO_records=len(new),all_nonclock_B_C_identical=all(old[n]==v for n,v in new.items() if n!='ck'),old_stale_IO_clock=old['ck'],canonical_C_clock=new['ck'],approved_B_checkpoint_clock=actual['ck'],all_C_coordinates_match_approved_checkpoint=len(bad)==0,mismatches=bad)
(b/'variantC_pin_identity.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
k=b/'variantC';s=(k/'run_kit.sh').read_text();needle="M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS';"
assert s.count(needle)==1
odb='/work/run/results/asap7/codex_btab_mif1_1847/base/4_cts.odb'
s=s.replace(needle,"M='make -o "+odb+" DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS';")
sha=hashlib.sha256((k/'run/results/asap7/codex_btab_mif1_1847/base/4_cts.odb').read_bytes()).hexdigest()
guard='''set -uo pipefail
# Resume only the exact independently reviewed clocked checkpoint; ordinary native/preflight and downstream gates remain.
checkpoint="$1/run/results/asap7/codex_btab_mif1_1847/base/4_cts.odb"
actual_checkpoint_sha=$(sha256sum "$checkpoint" | cut -d " " -f1)
[ "$actual_checkpoint_sha" = "SHA" ] || { echo "FAIL_REVIEWED_CTS_IDENTITY"; exit 12; }
'''.replace('SHA',sha)
s=s.replace('set -uo pipefail\n',guard,1);(k/'run_reviewed_cts.sh').write_text(s)
