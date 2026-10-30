from pathlib import Path
import json,shutil
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336');old=Path('/srv/opentallas-scratch2/claude/die-qc34-a0/kits/qfd_tile_nk_a0c_a0nk14icg2rr1');kit=p/'physical/nk_widen';kit.mkdir(parents=True,exist_ok=True)
for x in old.iterdir():
 if x.name in ('run','diag','__pycache__') or x.suffix in ('.log','.rpt'):continue
 if x.is_dir():shutil.copytree(x,kit/x.name,dirs_exist_ok=True)
 elif x.is_file():shutil.copy2(x,kit/x.name)
fr=json.load(open(p/'widen/nk_freeze_candidate.json'));(kit/'freeze.json').write_text(json.dumps(fr,indent=1)+'\n');s=(kit/'macro_place.tcl').read_text()
for before,after in ((199.8,201.96),(325.94,330.26)):
 s=s.replace(f'round({before} * $dbu)',f'round({after} * $dbu)').replace(f'at {before} ',f'at {after} ')
s+='\n# Internal core rebuild: clock-only micro-islands in expanded row corridors.\nsource /work/clock_corridors.tcl\n';(kit/'macro_place.tcl').write_text(s)
reserve=['set cc_b [ord::get_db_block]','set cc_u [$cc_b getDbUnitsPerMicron]']
rects=[r for c in fr['candidate_clock_corridors'] for r in c['clock_islands_um']]
for r in rects:reserve.append('odb::dbBlockage_create $cc_b '+' '.join(f'[expr {{round({v:.6f}*$cc_u)}}]' for v in r))
reserve.append(f'puts "A0_CLOCK_MICROISLANDS_RESERVED {len(rects)}"');(kit/'clock_corridors.tcl').write_text('\n'.join(reserve)+'\n')
for part in ('results','logs','reports'):
 base=old/f'run/{part}/asap7/kq_qfd_tile_nk_a0c_a0nk14icg2rr1/base';dest=kit/f'run/{part}/asap7/kq_qfd_tile_nk_a0c_a0nk14icg2rr1/base';dest.mkdir(parents=True,exist_ok=True)
 for f in base.glob('1*'):
  if f.is_file():shutil.copy2(f,dest/f.name)
(p/'run_nk_floorplan.sh').write_text('''#!/bin/bash
set -euo pipefail
p=/srv/opentallas-scratch2/claude/codex-qc-a0-0336
k=$p/physical/nk_widen
sudo docker run --rm --name codex-a0-nkwiden-floorplan-0336 --cpus=8 --memory=32g --memory-swap=32g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
r=/work/run/results/asap7/kq_qfd_tile_nk_a0c_a0nk14icg2rr1/base
make -o "$r/1_synth.odb" -o "$r/1_synth.v" -o "$r/1_synth.sdc" -o "$r/1_2_yosys.v" -o "$r/1_2_yosys.sdc" DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 floorplan
' > "$p/widen/nk_floorplan.log" 2>&1
''')
print('NK_PREP',len(rects),'microislands')
