#!/bin/bash
cd /
set -eu
R=/srv/opentallas-scratch2/claude/codex-kv-fdi-0222/parent_size
python3 -I - "$R" <<'PY'
from pathlib import Path
import json,sys,re
r=Path(sys.argv[1]);a=json.load(open(r/'native_parent.json'));top=json.load(open(r/'native_cut_profile.json'))['top'];lines=[]
used={c['type'] for c in a['modules'][top]['cells'].values()}
for name,m in a['modules'].items():
 if name not in used:continue
 if not m.get('attributes',{}).get('blackbox'):continue
 fields=[]
 for p,v in m.get('ports',{}).items():
  n=len(v['bits']);off=v.get('offset',0);rg=f'[{off+n-1}:{off}] ' if n>1 or off else ''
  ident=p if re.fullmatch(r'[A-Za-z_]\w*',p) else '\\'+p+' '
  fields.append(v['direction']+' wire '+rg+ident)
 lines.append('(* blackbox *) module '+name+'('+', '.join(fields)+'); endmodule')
(r/'unqualified_models.sv').write_text('\n'.join(lines)+'\n')
(r/'config.mk').write_text(f'''# Private source-bound synthesis only. FDI blackbox is unqualified; no physical provider/signoff.
export DESIGN_NICKNAME = kv_fdi_parent_model
export DESIGN_NAME = {top}
export PLATFORM = asap7
export VERILOG_FILES = /work/qkd_hr_host_parent.sv /work/unqualified_models.sv
export VERILOG_DEFINES = -DSYNTHESIS
export SDC_FILE = /work/constraint.sdc
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_MEMORY_MAX_BITS = 16384
export CORNER = TC
export ADDER_MAP_FILE = /work/adder_map_dontuse.v
export LEC_CHECK = 0
''')
(r/'constraint.sdc').write_text('create_clock -name ck_pad -period 833 [get_ports ck_pad]\n')
print('SOURCE_BOUND_SIZE_CONFIG',top,'blackbox models',len(lines),flush=True)
PY
cp /srv/opentallas-scratch2/claude/codex-kv-fdi-0222/kits/ot_kv_fdi_join_rf__198.72x198.72/adder_map_dontuse.v "$R/adder_map_dontuse.v"
docker run --name codex-kv-fdi-parent-size-v2-0222 --cpus 4 --memory 16g -v "$R:/work" openroad/orfs:asap7lock bash -c 'cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run NUM_CORES=4 synth' > "$R/synth.log" 2>&1
