#!/usr/bin/env python3
"""Source-pinned HA1 protocol gates; no model inference or physical adoption."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=False)
 prefix='results/uarch/Euclid_W4_RFACK_identity_contract_20261003/selfcontained-peer-r10/design/'
 pkg='rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
 sm='rtl/hbm_accel/txcount/ot_hbm_txcount_sm.sv'
 successor='rtl/hbm_accel/txcount/ot_hbm_rf_visibility_fence_live.sv'
 old='rtl/gpu/w6/ot_gpu_rf_visibility_fence_w6.sv'
 fixture=ROOT/'rtl/test/w6/tb_w6_fullwidth_fence.sv'
 live=fixture.read_text().replace('ot_gpu_rf_visibility_fence_w6','ot_hbm_rf_visibility_fence_live')
 # Reuse every shipped mutation/reset case unchanged, then test new live copies.
 live=live.replace('    $display("PASS_W6_LOCAL_COMPONENT', '''    cold_boot; prefix(0);
    @(negedge clk); dut.enabled.live_a=dut.enabled.live_a ^ 71'd1;
    #1; check(!fault && dut.enabled.identity==owner,"single live-copy upset majority exact");
    tick; check(dut.enabled.live_a==dut.enabled.live_b,"single live-copy self-repair");
    @(negedge clk); dut.enabled.live_a=dut.enabled.live_a ^ 71'd1;
    dut.enabled.live_b=dut.enabled.live_b ^ 71'd1;
    #1; check(fault && quarantine && !host_ack_ready && !visible_valid,"two live copies quarantine before release");
    tick; check(fault && dut.enabled.raw[59],"UE retains accepted owner debt");
    $display("PASS_W6_LOCAL_COMPONENT''')
 gen=out/'tb_w6_live.sv';gen.write_text(live)
 jobs=[('counter','tb_txcount',[pkg,sm,'rtl/hbm_accel/txcount/tb_txcount.sv']),
       ('actual_w4_w6','tb_txcount_actual_w4_w6',[pkg,sm,successor,'rtl/hbm_accel/txcount/ot_hbm_txcount_tap.sv',prefix+'ot_gpu_rf_service.sv',prefix+'ot_sram_1r1w_128x256_m1_r2c2.v','rtl/hbm_accel/txcount/tb_txcount_actual_w4_w6.sv']),
       ('w6_original','tb_w6_fullwidth_fence',[pkg,old,str(fixture)]),
       ('w6_live_mutation','tb_w6_fullwidth_fence',[pkg,successor,str(gen)])]
 pins={}
 results=[]
 for name,top,files in jobs:
  paths=[Path(f) if Path(f).is_absolute() else ROOT/f for f in files]
  pins.update({str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name:sha(p) for p in paths})
  exe=out/(name+'.vvp')
  cmds=[('compile',['iverilog','-g2012','-s',top,'-o',str(exe),*[str(p) for p in paths]]),('run',['vvp',str(exe)])]
  row={'name':name,'stages':[]}
  for stage,cmd in cmds:
   with (out/(name+'-'+stage+'.log')).open('w') as log:
    result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
   row['stages'].append({'stage':stage,'exit_code':result.returncode,'log':name+'-'+stage+'.log'})
   print(name,stage,result.returncode,flush=True)
   if result.returncode:break
  row['pass']=len(row['stages'])==2 and all(s['exit_code']==0 for s in row['stages'])
  results.append(row)
 record={'schema':'opentallas.ha1.txcount.run.v1','source_commit':(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() if (ROOT/'.git').exists() else (ROOT/'SOURCE_COMMIT').read_text().strip()),
         'input_sha256':pins,'jobs':results,'protocol_pass':all(j['pass'] for j in results),
         'exact_real_program':'UNMEASURED','serial_path_including_wire_CDC_credits_refresh':'UNMEASURED',
         'boundary_target_cycles':47,'priced_boundary_cycles':78,'measured_composed_gain':None,
         'area':'ESTIMATE storage-only portbook; full die fit unmeasured','route':'NOT_RUN',
         'SS_WNS':None,'FF_WNS':None,'adopt':False,
         'verdict':'PROTOCOL_ONLY_NOT_QUALIFIED' if all(j['pass'] for j in results) else 'REJECT_FUNCTIONAL_CANDIDATE',
         'qualification_order':['exact','serial_latency','area','route','SS60_FF25','composed_gain_ge_1percent']}
 (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
 return 0 if record['protocol_pass'] else 1
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();raise SystemExit(run(a.out))
