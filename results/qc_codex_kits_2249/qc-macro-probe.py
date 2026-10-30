from pathlib import Path
import re,subprocess,json,sys
R=Path('/srv/opentallas-scratch2/claude/codex-qc-kits-2249/macro_probe')
for D in sorted(R.iterdir()):
 if not D.is_dir() or (len(sys.argv)>1 and D.name not in sys.argv[1:]):continue
 c=(D/'config.mk').read_text();top=re.search(r'^export DESIGN_NAME = (.*)$',c,re.M)[1];fs=re.search(r'^export VERILOG_FILES = (.*)$',c,re.M)[1].split();fs=[x.replace('/work/','/all/'+D.name+'/') for x in fs]
 cmd='read_verilog -sv -D SYNTHESIS '+' '.join(fs)+'; hierarchy -top '+top+'; proc; flatten; hierarchy -top '+top+'; opt_clean; tee -o /all/'+D.name+'/stats.json stat -json; tee -o /all/'+D.name+'/macro_cells.txt select -list t:ot_sram* t:ot_rom*'
 p=subprocess.run(['docker','run','--rm','--memory=24g','--cpus=4','-v',str(R)+':/all','openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -T -p '+__import__('shlex').quote(cmd)],stdout=(D/'probe.log').open('w'),stderr=subprocess.STDOUT)
 print(D.name,p.returncode,flush=True)
 if p.returncode:sys.exit(p.returncode)
