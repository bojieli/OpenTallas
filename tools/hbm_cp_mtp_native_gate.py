#!/usr/bin/env python3
"""Actual fresh CPsouth facade mechanism plus mandatory pin mutants."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native.sv',
 'rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_join.sv',
 'rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue.sv',
 'physical/hbm_accel_die_views/cmdproc/rtl/hfd_cmdproc_s.sv',
 'physical/hbm_accel_die_views/cmdproc/rtl/ot_hfd_cmdproc20_m.sv',
 'physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv',
 'physical/asap7_memory_macros/ot_sram_2rw_512x64_m4_r2c2/ot_sram_2rw_512x64_m4_r2c2.v',
 'rtl/common/ot_fwd_link_stage.sv',
 'physical/hbm_cp_mtp_native/rtl/tb_hfd_cmdproc_s_mtp_native.sv']
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--am',action='store_true');p.add_argument('--mx1',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    sources=list(SOURCES);top='tb_hfd_cmdproc_s_mtp_native'
    if a.am or a.mx1:
        sources[0]='physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native_am.sv'
        sources[1]='rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_cp_join.sv'
        sources[-1]='physical/hbm_cp_mtp_native/rtl/tb_hfd_cmdproc_s_mtp_native_am.sv'
        top+='_'+ 'am'
    if a.mx1:
        sources[0]='physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native_mx1.sv'
        sources[1]='rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_cp_join_mx1.sv'
        sources[2]='rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue_mx1.sv'
        sources[-1]='physical/hbm_cp_mtp_native/rtl/tb_hfd_cmdproc_s_mtp_native_mx1.sv'
        top='tb_hfd_cmdproc_s_mtp_native_mx1'
    mutations=[('actual',None),('epoch_pin_mutant',('f_backend[70+:8]','t_backend[270+:8]')),('constant_ready_mutant',('f_provider[178:140],queue_ready,f_provider[138:0]',"f_provider[178:140],1'b1,f_provider[138:0]"))]
    if a.mx1:
        mutations[1]=('job_pin_mutant',('eng_cpl_job(f_backend[2+:32])','eng_cpl_job(t_backend[202+:32])'))
        mutations.append(('held_done_drain_mutant',('&&f_mtp[81]&&!f_mtp[43]', '&&!f_mtp[81]&&!f_mtp[43]')))
    if a.am or a.mx1:mutations.append(('AM_token16_mutant',('cp_am_idx(f_am[1+:17])','cp_am_idx(f_am[1+:16])')))
    verdicts=[]
    with tempfile.TemporaryDirectory(prefix='cp-mtp-native-') as tmp:
        tmp=Path(tmp)
        for name,mutant in mutations:
            files=list(sources)
            if mutant:
                s=(ROOT/files[0]).read_text();assert s.count(mutant[0])==1
                f=tmp/(name+'.sv');f.write_text(s.replace(*mutant));files[0]=str(f)
            binary=tmp/(name+'.vvp')
            c=subprocess.run(['iverilog','-g2012','-s',top,'-o',str(binary)]+files,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            (a.out/(name+'.compile.log')).write_text(c.stdout)
            if c.returncode:raise RuntimeError('elaboration failed '+name)
            r=subprocess.run(['vvp',str(binary)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            (a.out/(name+'.log')).write_text(r.stdout)
            if (mutant is None and r.returncode!=0) or (mutant is not None and r.returncode==0):raise RuntimeError('unexpected verdict '+name)
            verdicts.append(dict(name=name,verdict='PASS' if mutant is None else 'MUTANT_REJECTED',returncode=r.returncode))
    record=dict(verdict='PASS',cases=verdicts,native_CP_to_MTP_bits=197 if a.am or a.mx1 else 179,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},reset_contract='MX1_drained' if a.mx1 else 'historical_epoch',actual_facade_RTL=True,actual_native_MTP_controller=False,backend_operation_translator_bound=False,physical_qualification=False,full_decode_executable=False)
    (a.out/'gate.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS actual facade, finite8, owned completion and required pin mutants')
if __name__=='__main__':main()
