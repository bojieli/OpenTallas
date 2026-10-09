#!/usr/bin/env python3
"""Remote minimum SOURCE/STAGE successor gates, including wrong-user negative control."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import dsrom_mtp_rom_bench as B
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--case');p.add_argument('--hard-token',action='store_true');p.add_argument('--raw-negative',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 common=list(B.COMMON)+['rtl/dsrom_sys/mtp/ot_dsrom_wfc_tok_r3.sv','rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv','rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_src.sv','rtl/dsrom_sys/mtp/ot_dsrom_wfc_tokpipe_stg.sv']
 base=B.cases();base['stg_neg_prevuser']=dict(base['stg_r1'],defines=['OT_WFC_TOKPIPE_MUT_PREVUSER'],expect='fail')
 names=('s0_tr_dspark','s0_tr_forced','s0_tr_forced_w16','s0_hash_u3','s0_hash_u1_fast','s0_neg_noepoch','stg_vmnat','stg_r1','stg_lag1','stg_neg_prevuser')
 if a.case:
  if a.case not in names:raise ValueError(a.case)
  names=(a.case,)
 if a.raw_negative and (len(names)!=1 or base[names[0]]['expect']!='fail'):raise ValueError('raw-negative requires one negative case')
 rec=[];pins={}
 for name in names:
  spec=dict(base[name]);stage=name.startswith('stg_');spec['tb']='tb_mtp_rom_stg_tokpipe' if stage else 'tb_mtp_rom_s0_tokpipe'
  d=a.out/name;d.mkdir(parents=True,exist_ok=True)
  cfg=spec.get('trace');metadata=B.trace_hex(ROOT/B.TRACES/f'{cfg}.cfg.json',d/'trace.hex') if cfg else None
  original=ROOT/f'rtl/dsrom_sys/mtp/tb/{spec["tb"]}.sv'
  generated=d/'tb.sv';body=original.read_text();
  if a.hard_token and not stage:body=body.replace('dsfd_wfc_tok_r3 u_tok','dsfd_wfc_tok_hard u_tok').replace('ot_rom_pkg_ctrl_wfc_tokpipe #(','ot_rom_pkg_ctrl_wfc_tokpipe #(.PROMPT_EXTRA(2),')
  generated.write_text(body.replace('ot_rom_pkg_ctrl_wfc_tokpipe #(',f'ot_dsrom_wfc_tokpipe_{"stg" if stage else "src"} #('))
  sources=[str(ROOT/s) for s in common]+[str(generated)]
  for path in sources:pins[str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else name+'/tb.sv']=hashlib.sha256(Path(path).read_bytes()).hexdigest()
  cmd=['iverilog','-g2012','-s',spec['tb'],'-o',str(d/'sim.vvp')]+[f'-D{x}' for x in spec.get('defines',[])]+[f'-P{spec["tb"]}.{k}={v}' for k,v in spec.get('params',{}).items()]+sources
  run=subprocess.run(cmd,text=True,capture_output=True);(d/'build.log').write_text(run.stdout+run.stderr)
  if run.returncode:raise RuntimeError('compile failed '+name+': '+run.stderr[-2000:])
  run=subprocess.run(['vvp','-n',str(d/'sim.vvp')],cwd=d,text=True,capture_output=True);(d/'run.log').write_text(run.stdout+run.stderr)
  tag='MTP_STG' if stage else 'MTP_S0';want=tag+(' PASS' if spec['expect']=='pass' else ' FAIL')
  ok=run.returncode==0 and want in run.stdout and not (spec['expect']=='pass' and tag+' FAIL' in run.stdout)
  rec.append(dict(case=name,expected=spec['expect'],pass_=ok,trace=metadata,log=name+'/run.log',returncode=run.returncode))
  if not ok:
   (a.out/'summary.json').write_text(json.dumps(dict(all_ok=False,cases=rec,source_sha256=pins),indent=2)+'\n')
   raise RuntimeError(name+' '+run.stdout[-2000:])
 (a.out/'summary.json').write_text(json.dumps(dict(all_ok=all(r['pass_'] for r in rec),source='approved+1prompt cut matchedSOURCE metadata and current-user STAGE launch',source_sha256=pins,cases=rec),indent=2)+'\n')
 if a.raw_negative:
  print('WFC_TOKPIPE_NEGATIVE FAIL_AS_REQUIRED '+json.dumps(rec));raise SystemExit(1)
 print('WFC_TOKPIPE_GATE PASS '+json.dumps(rec))
if __name__=='__main__':main()
