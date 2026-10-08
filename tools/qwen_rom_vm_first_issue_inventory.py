#!/usr/bin/env python3
"""Extend pinned PART2 VM address obligations across compiled HEAD and L20.

These are first k/j/round static address sets. They are not a temporal activity
trace, simultaneous read/write proof, token timing, or hardware admission.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from hdc_isa import decode
from qwen_rom_finite_vm_schedule import BOOK, proposal, static_first_issue

def report(root):
    root=Path(root)
    base=proposal(root)  # Check original source and geometry pins first.
    rows=[]; unresolved=[]
    for program in ['head_program.hex','L20_program.hex']:
        raw=(root/BOOK/'inputs'/program).read_text().splitlines()
        for pc,line in enumerate(raw):
            instruction=decode(int(line,16))
            if instruction['unit']!=1: continue
            try: frame=static_first_issue(raw,pc)
            except ValueError as exc:
                unresolved.append(dict(program=program,pc=pc,reason=str(exc)))
                continue
            batches=frame['ordered_masked_write_batches']
            destinations=Counter((b['word']//4//512,b['bank']) for b in batches)
            distinct=Counter()
            for group,bank in destinations:
                distinct[(group,bank)]=len({b['word']//4%512 for b in batches if b['word']//4//512==group and b['bank']==bank})
            rows.append(dict(program=program,pc=pc,split=frame['split'],xbase=frame['xbase'],xcs=frame['xcs'],
                read_seats=frame['read_seats'],distinct_read_scalars=frame['distinct_read_scalars'],
                max_scalar_reuse=frame['maximum_same_scalar_reuse'],aligned_read_windows=frame['unique_aligned_read_windows'],
                adapter_read_window_misses=frame['current_adapter_window_misses'],write_scalar_seats=frame['write_seats'],
                ordered_masked_write_batches=frame['physical_write_batches'],write_batches_per_bank=frame['bank_write_batches'],
                distinct_write_rows_per_group_bank=[dict(group=g,bank=b,rows=n) for (g,b),n in sorted(distinct.items())],
                max_distinct_write_rows_one_group_bank=max(distinct.values(),default=0),
                instruction_sha256=frame['instruction_sha256']))
    # Reconfirm the two previously committed examples before extending coverage.
    for key,program,pc in [('HEAD_PC3','head_program.hex',3),('L20_W1_PC20','L20_program.hex',20)]:
        existing=base['examples'][key]
        got=next(r for r in rows if r['program']==program and r['pc']==pc)
        if got['write_batches_per_bank']!=existing['bank_write_batches'] or got['aligned_read_windows']!=existing['unique_aligned_read_windows']:
            raise ValueError('prior pinned example disagreement')
    paths=['tools/qwen_rom_finite_vm_schedule.py','tools/qwen_hbm_activation_vm_realization.py',
        'tools/hdc_isa.py','tools/qwen_rom_vm_first_issue_inventory.py']
    return dict(schema='opentallas.qwen-rom.vm-first-issue-inventory.v1',source_pins=base['source_sha256'],
        tool_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},rows=rows,unresolved=unresolved,
        scope='Literal first k0/j0/round0 address obligations from pinned compiled HEAD/L20, no claim that reads and writes co-issue',
        recovered_current_behavioral_capacity_bytes=4194304,historical_finite_adapter_retained_bytes=711232,
        capacity_binding='The177808 retained-word proposal is smaller than the behavioral1M-word ABI; selected workload live extent must be proved before replacing it',
        observed_temporal_schedule=False,whole_workload_covered=False,RTL_added=False,physical_admission=False,adopted=False,
        next_gate='Pin a current native PRE-edge enabled/address/mask trace on the minimum selected operation, including every SU/ME/MX/reducer/sequencer writer and original ME clock enable. Preserve read-old and later-writer priority. Then size banks, check sidecars, captured request/response queues and owner-coded flow; compose measured stall/crossing costs in the unified model before hardware.',
        fallback='Retain the existing source-ordered finite-walker proposal as a correctness reference. Per-group controller replication alone cannot resolve48 W1 rows in the same group/bank; price a different physical bank map or serialization and matched source holds.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();result=report(a.root);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(static_instructions=len(result['rows']),unresolved=len(result['unresolved']),adopted=False)))
