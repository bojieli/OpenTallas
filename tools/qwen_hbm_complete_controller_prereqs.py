#!/usr/bin/env python3
"""Source-bound controller extension sizing; no controller RTL admission."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REV='4535be1001d69bc43669e0fdf0401896be4034a6'
SOURCE='rtl/hdc/kv/ot_hdc_hbm_model.sv'

def model(repo,qd=64,rqd=32,write_depth=4):
    if min(qd,rqd,write_depth)<1 or qd<32:
        raise ValueError('finite queues must admit LENMAX32')
    raw=subprocess.check_output(['git','show',REV+':'+SOURCE],cwd=repo)
    for needle in (b'parameter integer TAGW     = 16',b'parameter integer LENW     = 5',
                   b'parameter integer BEATW    = 4',b'parameter integer QD       = 64',
                   b'parameter integer RQD      = 32',b'mem[q_addr[p][slot] % MEM_WORDS] = q_data[p][slot];'):
        if needle not in raw:raise ValueError('pinned controller source audit changed')
    instances=2*4;pcs=32
    # Conservative explicit epoch storage at every queue entry. A global
    # session epoch alternative needs a separately proved drain and is not
    # credited here. WR pending payload lives independently until visibility.
    epoch_bits=instances*pcs*(qd+rqd)*32
    write_fields={'tag':16,'epoch':32,'sector':34,'data':256,'due_ps':64,'valid':1}
    write_bits=instances*write_depth*sum(write_fields.values())
    write_pointer_bits=instances*(2*(write_depth-1).bit_length()+(write_depth+1).bit_length())
    total=epoch_bits+write_bits+write_pointer_bits
    return dict(schema='Qwen_controller_source_extension_prerequisites_r1',
        source_pin=dict(commit=REV,path=SOURCE,sha256=hashlib.sha256(raw).hexdigest()),
        source_defaults=dict(NPC=2,AW=24,TAGW=16,LENW=5,BEATW=4,QD=64,RQD=32),
        proposed_geometry=dict(dies=2,stacks_per_die=4,NPC=pcs,AW=34,TAGW=16,LENW=6,BEATW=5,QD=qd,RQD=rqd,write_pending_depth_per_stack=write_depth),
        controller_extension_state=dict(queue_epoch_bits=epoch_bits,write_pending_fields=write_fields,write_pending_bits=write_bits,write_pointer_bits=write_pointer_bits,total_bits=total,storage_only_area_mm2=total*.2916/.5/1e6),
        missing_composed_costs=['queue widening macros and ports','32-PC held return arbitration','write pending service ordering and refresh/turnaround','WR-visible capture and epoch mux/comparison','drain tree across all controllers/CDC/consumers','NoC routing tracks and full floorplan slot fit','1737 issue/RF/shared ports and token latency'],
        required_source_semantics=['capture producer epoch at request acceptance and move with every reorder swap','retain epoch through read return queue; never receiver-stamp','schedule real backing write visibility after column+CWL+burst, hold full identity/payload until ready','reserve pending-write capacity before issuing WR column; stall rather than drop completion','read-after-write forwarding or wait until backing visibility, preserving address order','full AW34 backing address with no modulo alias','drain observes queued reads/writes, delayed backing writes, all held returns, CDC, RMW and consumer leases','only both-die four-phase return-zero allows tag reuse'],
        baseline_unchanged=True,queue_depth_authority='explicit proposal; source defaults are not whole-system admission',
        area_scope='additional storage only; excludes existing queues and common36 r2 state; no free overlap. Not total element area.',
        actual_provider_credit=False,hardware_build_ready=False,total_token_cycles=None,headline_rate=None)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(model(a.repo),indent=2,sort_keys=True)+'\n')
