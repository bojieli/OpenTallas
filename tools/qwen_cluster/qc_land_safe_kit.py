#!/usr/bin/env python3
"""Generate opt-in safe hard landing halves; never bind or submit the parent."""
import json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=['rtl/physical/qcluster/qfd_c_land_safe.sv']
BENCHSRC=SRC+['rtl/physical/qcluster/qfd_c_land.sv','rtl/test/tb_qfd_c_land_safe.sv']
CHECKS='''1 FIXED: data outputs are register Qs; ring inputs capture directly in slot registers. Read bank inputs are the explicitly landed crossing and terminate at read output flops (same window as parent). Reset shared face rst_l0 -> kept r2 per 24-bit slice, no reset on ring data.
2 PASS: 216 x129.6 outline; every possible local wire <=345.6 um Manhattan, no inter-child wire included in this leaf.
3 FIXED: kept hierarchy and per-24bit kept sel/r2/warm copies; shared face rst_l0 drives <=12 stage2 copies. Select bit <=24 data gates +1 rotation. Confirm mapped keep audit in gate; unverified until synthesis.
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
     pins={'S':['i' if half=='w' else 'o','ck','rsi'],'N':['bank'],'E':['vld']},
     pin_ranges={('i' if half=='w' else 'o'):[0.54,205.74],'ck':[207.36,210.6],'rsi':[211.68,215.46],'bank':[0.54,215.46],'vld':[10.,20.]},
     route=dict(pd=0.50,threads=8,peak_ram_gb=24,pin_h='M4',pin_v='M5',hold_margin_ns=0.03,io_hold_margin_ns=0.03,
       pin_balance=dict(group_max=1,h='M4',v='M3 M5')),
     macros=[],children=[],inter=[],recipe=4,hold_budget='die',inhold=False,outhold=False,io_flop_at_pins=False,
     pin_regs=dict(enable=False,reason='ring capture flops and registered read output are the landed bank endpoint; adding input stages changes the priced ring window'),
     reset_landing=dict(enable=False,reason='one shared kept face rst_l0 then kept r2 per <=24bit slice; exactly two stages, first-stage fanout <=12'),
     structural_change='SAFE-QW-CB16: replace 163k soft parent DFFs with <=258bit ring/read hard halves, kept per24bit rotating onehot selects and 2stage reset. Geometry pin limited; parent not yet bound.',
     job=dict(owner='Codex:SAFE-QW-CB16',branch='codex/safe-qw-cb16-1019',tag='safe1',purpose='hard landing half; critical CB16 parent prerequisite, gate only',submit=False,
       benches=[dict(name='safe_land',cmd='bash tools/qwen_cluster/bench_land_safe.sh bench_safe',expect='pass',pass_regex='SAFE_LAND_EXIT 0',threads=8,peak_ram_gb=16,sources=['tools/qwen_cluster/bench_land_safe.sh'])]))
   variants=[spec]
   narrow=copy.deepcopy(spec);narrow['name']=narrow['top']=f'qfd_c_land_{half}{width}_narrow'
   narrow['outline']=dict(w=64.8,h=129.6,exact=True)
   narrow['pins']={'N':['i' if half=='w' else 'o'],'W':['bank_w'],'E':['bank_e'],'S':['ck','rsi','vld']}
   narrow['pin_ranges']={('i' if half=='w' else 'o'):[.54,64.26],'bank_w':[.54,129.06],'bank_e':[.54,129.06],'ck':[28.08,31.32],'rsi':[33.48,36.72],'vld':[40.,50.]}
   narrow['structural_change']+=' Narrow split bank_w/e at516bits per128.52um face (4.02pins/um); explicit4 slot-written flags restore phase-shifted reset behavior.'
   variants.append(narrow)
   for v in variants:
    name=v['name'];(out/f'{name}.json').write_text(json.dumps(v,indent=1)+'\n')
    text=CHECKS
    if name.endswith('_narrow'):text=text.replace('216 x129.6','64.8 x129.6').replace('216x129.6','64.8x129.6').replace('aspect1.667','aspect2').replace('1032/214.92=4.81','516/128.52=4.02').replace('345.6','194.4')
    text+='\nSlot-written flags:4 per-source-ring flags, same2stage reset epoch; each drives11 local masks, each mask<=24 data gates. Prevents stale reset output at +0.1T receiver phase.\n'
    kit=ROOT/'physical/ref_tile'/name;kit.mkdir(parents=True,exist_ok=True)
    (kit/'SAFE_CHECKLIST.md').write_text(f'# {name}: SAFE-QW-CB16 checklist\n\n'+text)
    print(out/f'{name}.json')
if __name__=='__main__':main()
