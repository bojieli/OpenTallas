#!/usr/bin/env python3
"""All16 rawSC heads, one loaded programme/start and persistent actual EB VM.

No host reconfiguration occurs between heads. Only rawSC initializes numerical
VM state. Final-head scaledSC/E and every head's MB/SE/EB are expected-only.
"""
import argparse,json,shutil
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True)
p.add_argument('--per-head-cases',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
for rows in (128,640):
    case=a.out/f't{rows}_h16';case.mkdir(parents=True,exist_ok=True)
    for name in ('arithmetic.hex','io.hex','aux.hex','config.txt'):
        shutil.copyfile(a.per_head_cases/f't{rows}_h00'/name,case/name)
    raw=[int(x,16) for x in (a.fixture/f'SC{rows}.hex').read_text().split()]
    assert len(raw)==16*rows
    (case/'raw_sc_sectors.hex').write_text(''.join(f'{sum(raw[s*8+w]<<(32*w) for w in range(8)):064x}\n' for s in range(len(raw)//8)))
    for name in ('MB','SE','EB'):
        shutil.copyfile(a.fixture/f'{name}{rows}.hex',case/f'expected_{name.lower()}.hex')
    for name in ('scaled','e'):
        shutil.copyfile(a.per_head_cases/f't{rows}_h15'/f'expected_{name}.hex',case/f'expected_{name}.hex')
    model=json.loads((a.per_head_cases/f't{rows}_h00'/'calendar.json').read_text())
    model.update(heads=16,external_starts=1,between_head_host_config_edges=0,
                 arithmetic_starts=16,io_aux_loops=16,total_io_edges=16*model['io_aux_rows'],
                 head_reconfiguration_setup_not_priced=False,
                 actual_source_control_register_bits=140,
                 note='One real protected programme loops16; actual headcounter remaps SC/EB and scalar bank/word. Immutable throughput and physical qualification still open.')
    (case/'model.json').write_text(json.dumps(model,indent=2)+'\n')
