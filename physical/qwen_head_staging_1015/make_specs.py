#!/usr/bin/env python3
"""Canonical real packet-leaf contracts; skinny slots approved by KV die owner."""
import json
from pathlib import Path
r=Path(__file__).resolve().parents[2]
for w,orient in [(519,'H'),(519,'V'),(512,'H'),(256,'H'),(34,'V'),(16,'V')]:
 name=f'qkh_packet_{orient.lower()}{w}'
 shape=[64.8,15.12] if orient=='H' else [15.12,64.8]
 if w<=112:shape=[21.6,21.6]
 pins={'S':['d'],'N':['q'],'W':['clk','rst_n']} if orient=='H' else {'W':['d'],'E':['q'],'S':['clk','rst_n']}
 benches=[]
 for mode,expect in [(0,'pass'),(1,'fail'),(2,'fail')]:
  b=dict(name=f'fixed_packet_{mode}',cmd=f'bash physical/qwen_head_staging_1015/bench.sh {{RUN}}/bench/packet_{mode} {w} {mode}',expect=expect,threads=1,peak_ram_gb=1,needs=['iverilog'])
  b['pass_regex' if expect=='pass' else 'fail_regex']=f'^{"PASS" if expect=="pass" else "FAIL"} qkh_packet_stage W={w} checks='
  benches.append(b)
 s=dict(name=name,top='ot_qkh_packet_pipe',kind='tile',sources=['rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv','rtl/lib/ot_rst_relay.sv'],params=dict(W=w,MUT=0),clock_port='clk',reset_ports=['rst_n'],outline=dict(w=shape[0],h=shape[1]),pins=pins,inter=[],refglob='*',layer_cap='M5',recipe=2,keep_pin_regs=True,pin_reg_split=True,inhold=True,outhold=True,io_flop_at_pins=dict(cols=4),route=dict(pd=.5,threads=8,peak_ram_gb=8,hold_margin_ns=.03,pin_balance=dict(group_max=1,h='M4',v='M5')),structural_change='New actual fixed-cycle ECTL/head and score/ECTL pin stage; actual input capture and output launch flops; no enable/ready/credit. Skinny slot approved by q_kv_die; parent global per-bit wires and composed cycle ages remain separately gated.',job=dict(owner='Codex:q_compute_elem_head_stage',branch='codex/q-compute-native-parents-1014',tag='p1',purpose='Native actual packet staging for classified ECTL/head die timing failure',extra_paths=['physical/qwen_head_staging_1015','rtl/test/qwen_head_staging'],benches=benches,views_to='physical/ref_tile/'+name+'/views',record_to='results/rtl/ref_tile/'+name))
 out=r/'tools/ref_tile/specs_q_compute_native'/(name+'.json');out.write_text(json.dumps(s,indent=2)+'\n');print(out.relative_to(r))
