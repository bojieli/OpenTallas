#!/usr/bin/env python3
"""Actual four-rank static FMT1 transport, including legacy gearbox RX interop."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
from calendar import fmt1_calendar, fmt1_cycle_controls
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[2];a.out.mkdir(parents=True,exist_ok=True)
sources=sorted((repo/'rtl/dsrom_sys/s81_static_collective').glob('*.sv'))
# Existing source is used byte-for-byte and pinned in the receipt.
sources += [repo/'rtl/link/ot_link_crc32.sv',repo/'rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv']
cases=[]
with tempfile.TemporaryDirectory(prefix='s81-fmt1-') as td:
 exe=Path(td)/'sim'
 subprocess.run(['iverilog','-g2012','-s','tb_s81_static_fmt1_vm_rank','-o',str(exe),*map(str,sources)],check=True)
 for layer,kind in [(0,'a'),(2,'a'),(8,'a'),(14,'a'),(20,'a'),(0,'router')]:
  slots=fmt1_calendar(layer,32,kind=kind);plan=a.out/f'{kind}_L{layer}.mem'
  plan.write_text(''.join(f'{(s.issue<<96)|(s.commit<<64)|(sum(r<<(15*k) for k,r in enumerate(s.rows))<<4)|(s.last<<3):032x}\n' for s in slots))
  beatplan=a.out/f'{kind}_L{layer}_beats.mem'
  beatplan.write_text(''.join(f'{x:02x}\n' for x in fmt1_cycle_controls(slots)))
  for mut in range(7) if layer==2 else [0]:
   cp=subprocess.run(['vvp',str(exe),f'+N={len(slots)}',f'+MUT={mut}',f'+PLAN={plan.resolve()}',f'+BEATS={beatplan.resolve()}'],text=True,capture_output=True)
   log=a.out/f'{kind}_L{layer}_m{mut}.log';log.write_text(cp.stdout+cp.stderr)
   if cp.returncode or 'PASS VM-pin-component-only' not in cp.stdout:raise RuntimeError(str(log))
   cases.append(dict(layer=layer,kind=kind,mutant=mut,records_per_rank=len(slots),
    fp32_per_destination=len(slots)*64,first_issue=slots[0].issue,last_issue=slots[-1].issue,
    first_commit=slots[0].commit,last_commit=slots[-1].commit,log=log.name))
 # A DUT mutation must fail the unchanged bit-exact checker; protocol fault
 # injections above separately exercise the fail-closed schedule behavior.
 original=repo/'rtl/dsrom_sys/s81_static_collective/s81_static_fmt1_vm_rank.sv'
 mutant=Path(td)/'mutant.sv'
 needle='write_tag,vm_data[k*512+:512]'
 assert needle in original.read_text()
 mutant.write_text(original.read_text().replace(needle,"write_tag,(vm_data[k*512+:512]^512'b1)"))
 mutant_sources=[mutant if x==original else x for x in sources]
 subprocess.run(['iverilog','-g2012','-s','tb_s81_static_fmt1_vm_rank','-o',str(exe),*map(str,mutant_sources)],check=True)
 cp=subprocess.run(['vvp',str(exe),f'+N={len(slots)}','+MUT=0',f'+PLAN={plan.resolve()}',f'+BEATS={beatplan.resolve()}'],text=True,capture_output=True)
 (a.out/'dut_payload_mutant.log').write_text(cp.stdout+cp.stderr)
 if cp.returncode==0 or 'source pin data' not in cp.stdout:raise RuntimeError('DUT payload mutant escaped exact checker')

report=dict(vm_service=dict(request_bits=15,response_bits=513,write_bits=2204,write_sources=[44,45,46,47],record_bits=551,request_register_edges=1,vm_read_pin_latency_edges=12,actual_sram_join=False),
 scope='actual static VM service pin packing plus FMT1 four-rank component; actual VM SRAM and FIELD joins remain unqualified',
 protocol=dict(engine_bits=547,flit_bits=552,sequence_bits=10,forward_crc_bits=32,forward_frame_bits=595,
 slot_bits=596,reverse_bits=53,forward_bits_per_phy_beat=456,slots_per_group=3,beats_per_group=4,
 phy_beat_bits=512,phy_beat_period_cycles=4,physical_bits_per_cycle=128,board_budget_bits_per_cycle=157.58,
 package_budget_bits_per_cycle=3864,source_cadence_cycles=[4,4,8],
 normal_credits=False,normal_ready=False,normal_replay=False,initialization_warmup_cycles=32,
 source_issue_to_gather_cycles=11,source_issue_to_vm_source_pin_cycles=12,
 source_issue_to_vm_observation_minimum_cycles=22,bank_drain_extra_cycles=[0,1,2],
 legacy_interoperability='actual ot_s81ph_link_gbx FMT1 receiver checks every record/count after lock'),
 source_sha256={str(s.relative_to(repo)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
 dut_mutant=dict(change='invert bit0 of every VM source payload',expected='FAIL source pin data',observed_returncode=cp.returncode,log='dut_payload_mutant.log'),
 calendar_sha256=hashlib.sha256((Path(__file__).parent/'calendar.py').read_bytes()).hexdigest(),cases=cases,
 unqualified=['actual PHY flight, local alignment and common reset/clock epoch',
 'physical placement/clock/reset/native pin closure in die-owned reservation',
 'native FIELD global ROM tags/capturebuffer and actual grouped VMread producer',
 'actual L12 SRAM reads, E10 SRAM writes and complete compiler job/resource calendar',
 'explicit CRC fault/retry recovery outside deterministic normal mode'])
(a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(cases=len(cases),verdict='PASS_VM_PIN_COMPONENT_ONLY',native_token=False)))
