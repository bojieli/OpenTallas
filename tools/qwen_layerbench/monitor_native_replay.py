"""Prepare a private monitor-XA replay from the completed native calendar fixture.

Unchanged native sources retain their frozen paths and cache compatibility.
No production caller, calendar or ROM is edited.
"""
import argparse,hashlib,json,shutil
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--candidate-source',type=Path,required=True)
    p.add_argument('--calendar-source',type=Path,required=True);p.add_argument('--masks',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--copy-cache',action='store_true');a=p.parse_args()
    receipt=json.loads((a.base/'receipt2.json').read_text());old=a.base/'portable'
    if receipt['status']!='PASS' or receipt['native_XA_words']!=512:raise ValueError('completed native baseline required')
    for name,digest in receipt['files_sha256'].items():
        if sha(old/name)!=digest:raise ValueError('frozen source changed: '+name)
    if sha(a.base/'obj/Vtb_mu_native')!=receipt['binary_sha256']:raise ValueError('baseline ELF changed')
    cand=json.loads((a.masks/'candidate.json').read_text())
    if cand['used_rows']!=3824 or cand['stage_stride']!=106 or not cand['emit_masks']:raise ValueError('explicit native tail image candidate required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'.keep').touch();d=a.out/'portable';d.mkdir()
    # Runtime macro masks and frozen input assets are read-only links. Tail files
    # are new copies so changing a control fixture cannot mutate the baseline.
    for z in old.iterdir():
        if z.is_file() and z.suffix=='.hex':(d/z.name).symlink_to(z.resolve())
    for lane in range(4):
        name=f'table_s0_m{lane}.viamap.hex';src=a.masks/name
        if sha(src)!=cand['images'][name]:raise ValueError('candidate mask changed')
        before=(old/name).read_text().splitlines();after=src.read_text().splitlines()
        if len(before)!=512 or before[:477]!=after[:477] or any(int(x,16) for x in before[477:]):
            raise ValueError('candidate is not an extension of this exact frozen native prefix')
        dst=d/name
        if dst.is_symlink():dst.unlink()
        shutil.copy2(src,dst)
    replacements={
        '6_qfd_dv_slice_tload.sv':a.candidate_source/'rtl/qwen_dv/qfd_dv_slice_tload.sv',
        '7_qfd_dv_table_rom_loader.sv':a.candidate_source/'rtl/qwen_dv/qfd_dv_table_rom_loader.sv',
        '48_qfd_dv_cmd_cal_mu.sv':a.calendar_source}
    source=[]
    for line in (old/'source.f').read_text().splitlines():
        z=Path(line)
        if z.name in replacements:
            shutil.copy2(replacements[z.name],d/z.name);z=d/z.name
        elif z.name=='51_tb_mu_native.sv':
            t=z.read_text()
            if t.count('.NWC(34)) load(')!=1:raise ValueError('baseline loader changed')
            t=t.replace('.NWC(34)) load(','.NWC(34),.MONITOR_TAIL(1)) load(')
            t=t.replace("116'd11<<4","116'd14<<4").replace('11+128*active','14+128*active').replace('11+128*issued_user','14+128*issued_user')
            t=t.replace('MU_CALENDAR_NATIVE_XA_PASS','MU_CALENDAR_MONITOR_XA_PASS')
            t=t.replace('repeat(64)@(negedge ck);rst_n=1;', '#0.001;if($test$plusargs("MUT_TAIL"))load.u_ld.m0.arr[477][339]=~load.u_ld.m0.arr[477][339];\n repeat(64)@(negedge ck);rst_n=1;')
            (d/z.name).write_text(t);z=d/z.name
        source.append(z.resolve())
    (d/'source.f').write_text(''.join(str(z)+'\n' for z in source));shutil.copy2(old/'defines.f',d/'defines.f')
    if a.copy_cache:
        size=sum(z.stat().st_size for z in (a.base/'obj').rglob('*') if z.is_file())
        if shutil.disk_usage(a.out).free<size+20*(1<<30):raise ValueError('cache copy lacks scratch headroom')
        shutil.copytree(a.base/'obj',a.out/'obj',copy_function=shutil.copy2)
    (a.out/'preparation.json').write_text(json.dumps(dict(
        schema='opentallas.qwen.monitor-native-replay-prep.v1',qualification='NOT RUN',
        baseline_binary_sha256=receipt['binary_sha256'],baseline=str(a.base),
        source_sha256={str(z):sha(z) for z in source},candidate_manifest_sha256=cand['manifest_sha256'],
        parameters=dict(MONITOR_TAIL=1,CAPTURE_STAGE=0,LOCAL_JOIN=0,MEMORY_ALIGNMENT=3,MIF=0,TABLE_USER_RELOC=1),
        pidx=dict(source=11,copy=14,global_rule='128*user+14'),
        fixture='four explicit loader requests and ROOT/STN inert commands; 512 actual XA golden words',
        held=['production TREQ/global earliest ANY PROG','all other monitor kernels','ROOT/STN arithmetic','HEAD producer','physical/canonical activation']),indent=2)+'\n')
    print('MONITOR_NATIVE_PREP files',len(source),'candidate_only no_production_caller')

if __name__=='__main__':main()
