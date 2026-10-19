#!/usr/bin/env python3
"""Generate opt-in safe hard landing halves; never bind or submit the parent."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=['rtl/physical/qcluster/qfd_c_land_safe.sv']
BENCHSRC=SRC+['rtl/physical/qcluster/qfd_c_land.sv','rtl/test/tb_qfd_c_land_safe.sv']
CHECKS='''1 FIXED: data outputs are register Qs; ring inputs capture directly in slot registers. Read bank inputs are the explicitly landed crossing and terminate at read output flops (same window as parent). Reset r1/r2 per 24-bit slice, no reset on ring data.
2 PASS: 216 x129.6 outline; every possible local wire <=345.6 um Manhattan, no inter-child wire included in this leaf.
3 FIXED: kept hierarchy and per-24bit kept sel/r1/r2/warm copies. Select bit <=24 data gates +1 rotation. Confirm mapped keep audit in gate; unverified until synthesis.
4 FIXED: registered rotating one-hot selects, 4-way masked OR read, no runtime binary wide mux.
5 FIXED: full 514/516 ring splits into two 257/258b hard children; each ring <=1032b. Ring is circular storage, not a serial delay line. No indexed flop mux.
6 WAIVER: pin-bound 216x129.6 (aspect1.667), bank face <=1032/214.92=4.81pins/um; no macros; one full-width standard cell region. Low utilisation expected from bank-export pin perimeter; this is explicit, not a measured 40-60% claim. Parent origins must be snapped43.2 and channels>=20um before parent gate.
7 FIXED: local hard-child clock, root beside register mass, io_hold_margin_ns0.03. TT/FF spread awaits gate. Parent root only hard-child clocks remains integration prerequisite.
8 FIXED: static continuous ring, no credit/backpressure. Two reset stages shift both landing epochs +1 versus historical halves; normal data latency unchanged K=2. Parent warm-up/compiler reset update required BEFORE binding. New halves remain unbound pending that work.
'''
def main():
 out=ROOT/'tools/ref_tile/specs_qcluster';out.mkdir(parents=True,exist_ok=True)
 for width in [257,258]:
  for half in ['w','r']:
   name=f'qfd_c_land_{half}{width}_safe'
   spec=dict(name=name,top=name,kind='tile',sources=BENCHSRC,params={},clock_port='ck',reset_ports=['rsi'],
     outline=dict(w=216,h=129.6,exact=True),layer_cap='M5',
     pins={'S':['i' if half=='w' else 'o','ck','rsi'],'N':['bank']},
     pin_ranges={('i' if half=='w' else 'o'):[0.54,205.74],'ck':[207.36,210.6],'rsi':[211.68,215.46],'bank':[0.54,215.46]},
     route=dict(pd=0.50,threads=8,peak_ram_gb=24,pin_h='M4',pin_v='M5',hold_margin_ns=0.03,io_hold_margin_ns=0.03,
       pin_balance=dict(group_max=1,h='M4',v='M3 M5')),
     macros=[],children=[],inter=[],recipe=4,hold_budget='die',inhold=False,outhold=False,io_flop_at_pins=False,
     pin_regs=dict(enable=False,reason='ring capture flops and registered read output are the landed bank endpoint; adding input stages changes the priced ring window'),
     reset_landing=dict(enable=False,reason='rsi lands through kept r1/r2 flops separately in each <=24bit slice'),
     structural_change='SAFE-QW-CB16: replace 163k soft parent DFFs with <=258bit ring/read hard halves, kept per24bit rotating onehot selects and 2stage reset. Geometry pin limited; parent not yet bound.',
     job=dict(owner='Codex:SAFE-QW-CB16',branch='codex/safe-qw-cb16-1019',tag='safe1',purpose='hard landing half; critical CB16 parent prerequisite, gate only',submit=False,
       benches=[dict(name='safe_land',cmd='bash tools/qwen_cluster/bench_land_safe.sh bench_safe',expect='pass',pass_regex='SAFE_LAND_EXIT 0',threads=8,peak_ram_gb=16)]))
   (out/f'{name}.json').write_text(json.dumps(spec,indent=1)+'\n')
   kit=ROOT/'physical/ref_tile'/name;kit.mkdir(parents=True,exist_ok=True)
   (kit/'SAFE_CHECKLIST.md').write_text(f'# {name}: SAFE-QW-CB16 checklist\n\n'+CHECKS)
   print(out/f'{name}.json')
if __name__=='__main__':main()
