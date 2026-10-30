import glob,subprocess
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-hbm-1030/load_lot')
libs=sorted(x for x in glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*') if 'FAKE' not in x)
assert len(libs)==5,libs
seq=next(x for x in libs if '_SEQ_' in x)
args=' '.join('-liberty '+x for x in libs)
script=['read_json /srv/opentallas-scratch2/claude/codex-hbm-bind-1030/load_delta/load.json']
script+=['read_liberty -lib '+x for x in libs]
script+=['dffunmap','dfflibmap -liberty '+seq,'abc '+args+' -D 833','tee -o '+str(r/'mapped_stat.txt')+' stat '+args,'write_json '+str(r/'mapped.json')]
(r/'map.ys').write_text('\n'.join(script)+'\n')
rc=subprocess.call(['yosys','-Q','-T','-s',str(r/'map.ys')]);(r/'map.rc').write_text(str(rc)+'\n');raise SystemExit(rc)
