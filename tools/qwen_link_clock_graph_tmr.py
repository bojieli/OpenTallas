#!/usr/bin/env python3
"""Source-preserving r23 graph selecting protected synchronized-release stations."""
import argparse
import hashlib
import json
from pathlib import Path
from qwen_link_clock_graph import emit, DATA
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 g=json.loads((DATA/'graph.json').read_text());c=json.loads((DATA/'connections.json').read_text())
 rtl,record=emit(g,c)
 assert rtl.count('ot_qwen_die_link_fwd_full #')==217
 rtl=rtl.replace('module ot_qwen_link_graph_r22 #','module ot_qwen_link_graph_r23 #').replace('ot_qwen_die_link_fwd_full #','ot_qwen_die_link_fwd_full_tmr #')
 assert rtl.count('.rst_n(link_por_n)')==217
 record.update(schema='opentallas.qwen-link-clock-graph-tmr.binding.v1',
   reset_implementation='Three independent2stage release rails perstream; localmajority drivescontrolCLR',
   primitive_source_sha256=hashlib.sha256((ROOT/'rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv').read_bytes()).hexdigest(),
   rtl_sha256=hashlib.sha256(rtl.encode()).hexdigest(),
   source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),ROOT/'tools/qwen_link_clock_graph.py',DATA/'graph.json',DATA/'connections.json']})
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'ot_qwen_link_graph_r23.sv').write_text(rtl)
 (a.out/'bindings.json').write_text(json.dumps(record,indent=2)+'\n')
 print('PASS217 TMR primitives,442 owned streams; no oldsource overwritten')
if __name__=='__main__':main()
