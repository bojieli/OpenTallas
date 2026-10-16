#!/usr/bin/env python3
"""Actual controller/front/ring integration test with independent drain scoreboards.

Only off-chip PHY storage uses behavioral memory. New idle exports are
observations: the full die parent must still join upstream/front/ring quiet.
"""
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def prepare(out):
    env=dict(os.environ,PREP_ONLY='1')
    subprocess.run(['bash',str(ROOT/'tools/qwen_static_kv/run_kv_hbm_elastic_boundary.sh'),str(out),'HEAD'],env=env,check=True)
    # Use the actual candidate RTL; the immutable manifest below pins all bytes.
    rel='rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static.sv'
    shutil.copy2(ROOT/rel,out/'source'/rel)
    p=out/'source/rtl/test/qwen_static_kv/tb_kv_hbm_elastic_boundary.sv'
    text=p.read_text().replace('wire predicted_raw,predicted_corrected;',
      'wire [1:0] idle_core,idle_hbm,drain_fault_core,drain_fault_hbm;\n wire predicted_raw,predicted_corrected;')
    text=text.replace('.completion_fault(cf[g]));',
      '.completion_fault(cf[g]),.idle_core(idle_core[g]),.idle_hbm(idle_hbm[g]),.drain_fault_core(drain_fault_core[g]),.drain_fault_hbm(drain_fault_hbm[g]));')
    # Independent boundary scoreboard: external accepted descriptors, physical
    # WDONE completions, actual returned host data, actual landed KV payloads.
    monitor=r"""
 integer ob_desc[0:1],ob_read[0:1],ob_kv[0:1],drain_checks=0;
 generate for(genvar d=0;d<2;d++)begin:drain_score
  always @(posedge ck)begin
   if(!rst[d])begin ob_desc[d]=0;ob_read[d]=0;ob_kv[d]=0;end
   else begin
    if(es[0])begin ob_desc[d]++;if(!es[286])ob_read[d]++;end
    if(cv[d])ob_desc[d]--;
    if(er[d][0])ob_read[d]--;
    if(po[d][28]&&!po[d][29]&&openrow[po[d][34:30]]==67)ob_kv[d]++;
    if(co[d][0])ob_kv[d]--;
    #0.001;
    drain_checks++;
    if(idle_core[d]&&(ob_desc[d]!=0||ob_read[d]!=0))
     $fatal(1,"DRAIN_EARLY_CORE d%0d descriptors%0d reads%0d",d,ob_desc[d],ob_read[d]);
    if(idle_hbm[d]&&ob_kv[d]!=0)
     $fatal(1,"DRAIN_EARLY_HBM d%0d corrected KV outstanding%0d",d,ob_kv[d]);
    if(drain_fault_core[d]||drain_fault_hbm[d])$fatal(1,"DRAIN_COUNTER_FAULT d%0d",d);
   end
  end
 end endgenerate
"""
    text=text.replace(' function automatic [255:0] data(',monitor+'\n function automatic [255:0] data(')
    text=text.replace('  if(front_bad)begin',
      '  if(!idle_core[1]||!idle_hbm[1]||ob_desc[1]||ob_read[1]||ob_kv[1])$fatal(1,"DRAIN_FINAL_NOT_IDLE");\n  $display("DRAIN_PASS boundary checks%0d actual host WDONE/read and KV landing drained",drain_checks);\n  if(front_bad)begin')
    p.write_text(text)
    manifest={str(p.relative_to(out/'source')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((out/'source').rglob('*.sv'))}
    (out/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


def execute(out):
    controller=out/'source/rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static.sv'
    good=controller.read_text()
    sources=[str(p) for p in sorted((out/'source').rglob('*.sv'))]
    variants={'production':good,
      'missing_host_read_debt':good.replace('drain_desc==0&&drain_reads==0&&drain_credits==0','drain_desc==0&&drain_credits==0'),
      'missing_kv_debt':good.replace('ctl_phase_idle&&t_empty&&raw_out==0&&drain_kv==0','ctl_phase_idle')}
    receipt={'scope':'COMPONENT_ONLY actual controller, pcport/ECC, front and ring; die bind/adoption remains OPEN','cases':[]}
    for name,source in variants.items():
      controller.write_text(source)
      with (out/(name+'.build.log')).open('w') as log:
       subprocess.run(['verilator','--binary','--timing','-Wno-fatal','-j','2','--top-module','tb_kv_hbm_elastic_boundary','--Mdir',str(out/('obj_'+name)),*sources],stdout=log,stderr=subprocess.STDOUT,check=True)
      cases=([(0,False),(8,False),(16,False),(16,True)] if name=='production' else [(16,name=='missing_kv_debt')])
      for jitter,late_tail in cases:
       namecase=name+'_j'+str(jitter)+('_late_tail' if late_tail else '')
       extra=['+faultmode=2','+late=512','+lateby=100'] if late_tail else []
       with (out/(namecase+'.log')).open('w') as log:
        r=subprocess.run([str(out/('obj_'+name)/'Vtb_kv_hbm_elastic_boundary'),'+jit='+str(jitter),'+seed=2',*extra],stdout=log,stderr=subprocess.STDOUT)
       text=(out/(namecase+'.log')).read_text()
       passed=(r.returncode!=0 and 'OBSERVED_HOLD' in text and 'DRAIN_EARLY' not in text and 'DRAIN_COUNTER_FAULT' not in text) if late_tail else (r.returncode==0 and 'DRAIN_PASS' in text and 'PASS 0az' in text)
       rejected=r.returncode!=0 and ('DRAIN_EARLY_CORE' if name=='missing_host_read_debt' else 'DRAIN_EARLY_HBM') in text
       receipt['cases'].append(dict(name=namecase,returncode=r.returncode,pass_observed=passed,mutant_rejected=rejected))
       if (not passed if name=='production' else not rejected):
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');raise RuntimeError('drain proof failed '+namecase)
    controller.write_text(good)
    receipt['status']='PASS';(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--prepare-only',action='store_true');p.add_argument('--execute-only',action='store_true');a=p.parse_args();a.out=a.out.resolve()
 if not a.execute_only:prepare(a.out)
 if not a.prepare_only:execute(a.out)
