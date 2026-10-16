#!/usr/bin/env python3
"""Actual HOST leaf composition: fixed ingress slots, source-exact IKEY and boot.

External HBM storage/ACKs and expected numerical images are test models. Every
on-chip packet/FIFO/arithmetic/decoder result comes from actual source RTL.
Scope is initialization/off-chip ingress; normal-token compiler reservations,
physical pin/clock timing and die/full-token throughput remain OPEN.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import rtl_rom_host_ingest_bench as B
p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--legacy-address',action='store_true');p.add_argument('--case',choices=['ikey','rows'],default='ikey');a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
SRC=['rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv','rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv','rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv','physical/rom_host_ingest/rtl/dsfd_host.sv','rtl/hdc/ingest/ot_rom_host_ingest.sv','rtl/link/ot_link_afifo.sv','rtl/hdc/ingest/ot_hdc_kv_ingest.sv','rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd_sliced.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_c_sliced.sv']
DEFS=['-DDSFD_HOST_C_STATIC','-DDSFD_HOST_PQ_BOOT','-DOT_S81_HOST_PHASESAFE','-DOT_S81_HOST_BOOT300']
if not a.legacy_address:DEFS.append('-DOT_S81_HOST_ADDR_PREFIX')
c=B.C.case_ikey(np.random.default_rng(20261016),1024) if a.case=='ikey' else B.C.case_rows(np.random.default_rng(20261016),'ckv',64,first=32)
c['nb']=B.stream_nb(c['descs']);B.write_case(a.out,c,65536)
# Mixed intercepted stage/PQ/length CSRs precede real native ingress.
words=[(0,0x10 | (0x1234567<<32)),(0,0x12 | (1<<96) | (0x2345678<<32)),(0,0x11 | (4<<32)),(0,0)];pi=0
for desc,nb in zip(c['descs'],c['nb']):
    words.append((1,int(desc)))
    for _ in range(nb):words.append((2,int(c['beats'][pi])));pi+=1
(a.out/'packets.mem').write_text(''.join(f'{(cls<<513)|(word<<1)|1:0129x}\n' for cls,word in words))
# The declared new native ACK input edge is modeled by one real FF in
# the otherwise unchanged actual legacy HOST reference. Its original source
# and generated registered-boundary source are both pinned in the receipt.
reference_source=(ROOT/'rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv').read_text()
reference=reference_source.replace('module dsfd_host_c #','module dsfd_host_c_ack_ref #')
ackdecl='wire ov, owe, ocr, hf, sf; wire [31:0] oa; wire [255:0] od; wire [7:0] ack;'
assert reference.count(ackdecl)==1
reference=reference.replace(ackdecl,ackdecl+"\n    wire ack_ref_rn;reg[7:0]ack_ref;\n    ot_reset_sync ack_ref_reset(.clk(ck),.async_rst_n(rst),.sync_rst_n(ack_ref_rn));\n    always @(posedge ck or negedge ack_ref_rn)if(!ack_ref_rn)ack_ref<=0;else ack_ref<=ack;")
ackinput='.host_ack_n(ack), .fault(hf)'
assert reference.count(ackinput)==1
reference=reference.replace(ackinput,'.host_ack_n(ack_ref), .fault(hf)')
reference_path=a.out/'dsfd_host_c_ack_ref.sv';reference_path.write_text(reference)
records=[]
def build(top,tb,mut,name,replacement=None,engine_replacement=None):
    exe=a.out/(name+'.vvp')
    cmd=['iverilog','-g2012','-s',top,f'-P{top}.MUT={mut}',*DEFS,'-o',str(exe),str(tb),str(reference_path),*[str(replacement) if replacement and x=='rtl/dsrom_sys/s81_ingest/dsfd_host_c_sliced.sv' else str(engine_replacement) if engine_replacement and x=='rtl/hdc/ingest/ot_hdc_kv_ingest.sv' else str(ROOT/x) for x in SRC]]
    cp=subprocess.run(cmd,capture_output=True,text=True)
    (a.out/(name+'.build.log')).write_text(cp.stdout+cp.stderr)
    if cp.returncode:raise SystemExit('HOST_C_SLICED BUILD_FAIL '+name+' '+cp.stderr[-1000:])
    return exe
def run(exe,name,args,expect,marker):
    cp=subprocess.run(['vvp','-n',str(exe),*args],cwd=a.out,capture_output=True,text=True,timeout=300)
    output=cp.stdout+cp.stderr;(a.out/(name+'.log')).write_text(output)
    if (cp.returncode==0)!=expect or marker not in output:raise SystemExit('HOST_C_SLICED UNEXPECTED '+name+' '+output[-1500:])
    records.append(dict(case=name,returncode=cp.returncode,marker=marker))
    print(name,output.strip().splitlines()[-1],flush=True)
for mut in [0,6]:
    name=f'native_m{mut}';exe=build('tb_host_c_sliced_native',ROOT/'tests/s81/tb_host_c_sliced_native.sv',mut,name)
    run(exe,name,[f'+NP={len(words)}'],mut==0,'HOST_SLICED_NATIVE PASS' if mut==0 else 'HOST_SLICED_NATIVE FAIL exact producer/calendar')
    if mut==0:
        # Later MUT0 interception-negative run uses the same DUT filename.
        # Preserve the positive emit calendar before that intentional failure.
        (a.out/'emit_calendar_exact.tsv').write_bytes((a.out/'emit_calendar_m0.tsv').read_bytes())
        (a.out/'completion_calendar_exact.tsv').write_bytes((a.out/'completion_calendar_m0.tsv').read_bytes())
# The actual measured ROWS carry path must affect real numerical writes.
# This shared-engine mutant corrupts both old/new RTL, so only the external
# golden memory comparison can detect it; no internal result is supplied.
if a.case=='rows' and not a.legacy_address:
    engine=(ROOT/'rtl/hdc/ingest/ot_hdc_kv_ingest.sv').read_text()
    carry="q[5*i+:4]+{3'd0,g3[i-1]}"
    assert engine.count(carry)==1
    badengine=a.out/'wrong_address_carry.sv';badengine.write_text(engine.replace(carry,"q[5*i+:4]+4'd0"))
    exe=build('tb_host_c_sliced_native',ROOT/'tests/s81/tb_host_c_sliced_native.sv',0,'native_wrong_address_carry',engine_replacement=badengine)
    run(exe,'native_wrong_address_carry',[f'+NP={len(words)}'],False,'HOST_SLICED_NATIVE FAIL external memory')
# Negative control: bypass only the relocated native launch filter. The
# mixed-CSR bench must catch an intercepted CSR on the actual native port.
original=(ROOT/'rtl/dsrom_sys/s81_ingest/dsfd_host_c_sliced.sv').read_text()
needle="wire csr=hv&&hcl==0&&(hd[7:0]==8'h10||hd[7:0]==8'h11||hd[7:0]==8'h12);"
assert original.count(needle)==1
mutant=a.out/'bypass_intercepts.sv';mutant.write_text(original.replace(needle,"wire csr=1'b0; // mutant: leak intercepted CSRs into native ingest"))
exe=build('tb_host_c_sliced_native',ROOT/'tests/s81/tb_host_c_sliced_native.sv',0,'native_bypass_intercepts',mutant)
run(exe,'native_bypass_intercepts',[f'+NP={len(words)}'],False,'HOST_SLICED_NATIVE FAIL interceptedCSR reached native ingest port')
# Negative control: retain the capture register but illegally bypass it at
# the actual fence input. The edge assertion must detect the early count.
ackneedle='.host_ack_n(ack_pin),.fault(hf)'
assert original.count(ackneedle)==1
ackmut=a.out/'bypass_ack_pin.sv';ackmut.write_text(original.replace(ackneedle,'.host_ack_n(host_ack_n),.fault(hf)'))
exe=build('tb_host_c_sliced_native',ROOT/'tests/s81/tb_host_c_sliced_native.sv',0,'native_bypass_ack_pin',ackmut)
run(exe,'native_bypass_ack_pin',[f'+NP={len(words)}'],False,'HOST_SLICED_NATIVE FAIL ACK fixed pin-stage calendar')
# Actual native ACK capture/count checks at every source-family phase, with
# reset during traffic. The same bypass-negative must fail this direct bench.
exe=build('tb_host_ack_pin',ROOT/'tests/s81/tb_host_ack_pin.sv',0,'ack_phase_exact')
for phase in range(6):run(exe,f'ack_phase{phase}',[f'+phase={phase}'],True,'ACK_PIN PASS')
exe=build('tb_host_ack_pin',ROOT/'tests/s81/tb_host_ack_pin.sv',0,'ack_phase_bypass',ackmut)
run(exe,'ack_phase_bypass',['+phase=2'],False,'ACK_PIN FAIL fixed capture/count edge')
# Reuse the exact legacy boundary transport vectors, with actual new clock
# entry pins bound to their ideal source-family phase. This is not timing proof.
boot=(ROOT/'tests/s81/tb_host_boot300.sv').read_text().replace('module tb_host_boot300;', 'module tb_host_boot300_sliced;').replace('dsfd_host_c #','dsfd_host_c_sliced #').replace('.ck(ck),.ckv(ckv)', '.ck(ck),.ck_data({4{ck}}),.ck_native(ck),.ck_launch(ck),.ck_return(ck),.ckv(ckv)')
tb=a.out/'boot_sliced.sv';tb.write_text(boot)
exe=build('tb_host_boot300_sliced',tb,0,'boot0')
for phase in range(8):run(exe,f'boot_phase{phase}',[f'+serial_phase={phase}'],True,'BOOT300 PASS')
for name,arg in [('stop','+stop_boot=1'),('capacity','+overload=1')]:run(exe,'boot_'+name,[arg],True,'BOOT300 FAIL_EXPECTED')
exe=build('tb_host_boot300_sliced',tb,5,'boot_kind_mutant')
run(exe,'boot_kind_mutant',[],False,'BOOT300 FAIL payload/kind')
rec=dict(scope=__doc__,native_case=a.case,native_case_metadata=c['meta'],host_address_prefix_enabled=not a.legacy_address,reference_pin_stage=dict(origin_sha256=hashlib.sha256(reference_source.encode()).hexdigest(),generated_sha256=hashlib.sha256(reference.encode()).hexdigest(),native_ACK_capture_edges=1,other_reference_logic='Unchanged actual legacy HOST source; this is the explicit input pin FF contract, not a result producer'),output_artifact_sha256={x:hashlib.sha256((a.out/x).read_bytes()).hexdigest()for x in ['emit_calendar_exact.tsv','completion_calendar_exact.tsv']},generator_source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in ['tools/rtl_rom_host_ingest_bench.py','tools/rtl_hdc_kv_ingest_campaign.py','tools/kv_ingest_ref.py','tools/s81_static_control/host_c_sliced_gate.py']},input_image_sha256={x:hashlib.sha256((a.out/x).read_bytes()).hexdigest() for x in ['packets.mem','init.mem','exp.mem']},source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in SRC+['tests/s81/tb_host_c_sliced_native.sv','tests/s81/tb_host_boot300.sv','tests/s81/tb_host_ack_pin.sv']},input_slots=dict(first=128,stride=32,packets=len(words),final_verification_edge=60000),normal_token_reservation='OPEN: queue-nonempty service is not a compiled execution calendar',diagnostic_delta=dict(native_fault_host_edges=1,payload_emit_service_edges=0,ACK_pin_to_fence_count_edges_added=1,measured_IKEY_completion_edge_delta=0),cases=records)
(a.out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
print('HOST_C_SLICED_GATE PASS actual '+a.case+' /full256 exact59989edges + badpayload/interceptbypass/ACKearlycount mutants + mixedCSR + boot8phases/kind/missingclock/capacity')
