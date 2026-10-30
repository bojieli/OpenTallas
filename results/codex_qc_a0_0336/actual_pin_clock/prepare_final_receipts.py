from pathlib import Path
import shutil
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336')
for k in ('nk','nl'):
 d=p/f'physical/{k}_pin_clock_install';shutil.copy2(p/'src/census.tcl',d/'census.tcl');text=(p/'src/census.tcl').read_text().replace('read_db $::env(ODB)\n','');(d/'census_inmemory.tcl').write_text(text)
 text=(p/'src/macro_interface_reach.tcl').read_text().replace('read_db /work/clock_installed.odb\n','');(d/'macro_interface_inmemory.tcl').write_text(text)
 defs=(p/'src/dump_logic_graph.tcl').read_text().split('read_db /work/input.odb')[0];(d/'logic_graph_defs.tcl').write_text(defs)
 (d/'collect_before.tcl').write_text('read_db /work/input.odb\nsource /work/logic_graph_defs.tcl\ndump_logic_graph /work/logic_before.tsv\n')
 (d/'collect_after.tcl').write_text('read_db /work/clock_installed.odb\nset ::env(OUT) /work/clock_census.tsv\nset ::env(CKP) ck\nsource /work/census_inmemory.tcl\nsource /work/macro_interface_inmemory.tcl\nsource /work/logic_graph_defs.tcl\ndump_logic_graph /work/logic_after.tsv\nputs "A0_FINAL_RECEIPT_COLLECTION_PASS"\n')
 command='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; set -e; openroad -exit /work/collect_before.tcl > /work/collect_before.log 2>&1; openroad -exit /work/collect_after.tcl > /work/collect_after.log 2>&1'
 (d/'collect.sh').write_text('#!/bin/bash\nset -euo pipefail\nsudo docker run --rm --name codex-a0-'+k+'-finalreceipts-0336 --cpus=1 --memory=4g --memory-swap=4g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc '+"'"+command+"'"+'\n')
# Current normal/mutant proofs use exact pin-net files in their census directory.
f=p/'src/clock_netlist_invariants.py';s=f.read_text();s=s.replace("before_geom=p/f'physical/{kind}_public_clock_install/logic_before.tsv'","before_geom=after_census.parent/'logic_before.tsv'").replace("after_geom=p/f'physical/{kind}_public_clock_install/logic_after.tsv'","after_geom=after_census.parent/'logic_after.tsv'");f.write_text(s)
