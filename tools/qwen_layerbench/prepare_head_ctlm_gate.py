#!/usr/bin/env python3
"""Prepare the actual selected CALR successor at nent1013, no dispatch.

Three real calendars compare old/default-off/new-optin requests for all36
existing load stages and all4users, then qualify actual stage37 LOCAL4.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
import residual2_calendar_candidate as R
import programme_store as P


def prepare(selected,successor,root,out):
    out.mkdir(parents=True,exist_ok=False);d=out/'input';d.mkdir();rom=out/'rom';rom.mkdir()
    original=selected/'rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv'
    src=original.read_text();main=src[:src.index('endmodule')+len('endmodule')]
    (d/'qfd_dv_cmd_cal_mu_original.sv').write_text(main+'\n')
    shutil.copy2(successor,d/successor.name)
    names=['rtl/qwen_dv/qfd_dv_calendar_rom.sv','rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv','rtl/qwen_sys/program_receiver_20261014/qkd_program_pw_observer_p.sv','rtl/lib/ot_ks_add.sv','physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v','physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']
    for name in names:
        path=selected/name
        if not path.exists():path=root/name
        shutil.copy2(path,d/path.name)
    sourcecal=selected/'rtl/test/qwen_dv/calr_port';w,dw=R.decode_image(sourcecal)
    if dw[0]&1023!=1009:raise ValueError('actual1009 source required')
    i=1012;c=(14<<112)|(37<<4)|9;w[i//4]|=((8<<116)|c)<<(128*(i%4))
    dw[0]=(dw[0]&~1023)|1013
    for lane in (0,1):
        (rom/f'calendar_m{lane}.viamap.hex').write_text(''.join(f'{x:0532x}\n'for x in P.physical_rows(w+[0]*2048,lane)[:256]))
    (out/'dw.hex').write_text(''.join(f'{x:016x}\n'for x in dw))
    shutil.copy2(Path(__file__).with_name('tb_head_ctlm37.sv'),d/'tb_head_ctlm37.sv')
    shutil.copy2(Path(__file__).with_name('run_head_ctlm_gate.sh'),out/'run_gate.sh')
    (out/'source.f').write_text(''.join('input/'+p.name+'\n'for p in sorted(d.iterdir())))
    report=dict(status='PREP_ONLY_NOT_LAUNCHED',source_original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
      successor_sha256=hashlib.sha256(successor.read_bytes()).hexdigest(),source_files=len(list(d.iterdir())),source_bytes=sum(p.stat().st_size for p in d.iterdir()),
      instances='actual original/default-off/optin, NU4 CALREG7 CALR1 TABLE1',existing_load_requests=144,new_load_requests=4,nent=1013,new_range=[1012,1],
      controls=['default-off37 rejection','MUT_USER shared-range wrong-owner catch'],scope='actual CALR/CTLM request source only; no table payload loader, SU, ROOT, physical or token claim')
    (out/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'packet.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n'for p in sorted(out.rglob('*'))if p.is_file()))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('selected','successor','root','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=prepare(a.selected,a.successor,a.root,a.out);print(json.dumps({k:r[k]for k in ('source_files','source_bytes','nent','status')}))
