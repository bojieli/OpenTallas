#!/usr/bin/env python3
"""Prepare one native SU/VM plus real stream-tile HEAD component packet.

Legacy mode uses the completed residual2 projection unchanged. Explicit
native-component mode copies the current coupled-MIF SUVM/eight-head packet
and selects its measured reply profile. Both add the production stream tile;
no job, production image or legacy HEAD profile is activated.
"""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import programme_store as P
import dv_lower as D
import dv_lower_vec as V


def prepare(base,stage,stream,out,*,native_component=False,memory_read_extra=0):
    m=json.loads(stage.read_text())
    if m.get('stage')!=37 or sorted(s['slice']for s in m['slices'])!=list(range(12)):
        raise ValueError('complete actual HEAD37 linked stage required')
    if memory_read_extra not in (0,1) or (memory_read_extra and not native_component):
        raise ValueError('extra1 needs an explicit current native-component source packet')
    source_list=base/('sources.f' if native_component else 'source.f')
    if native_component:
        component=(base/'component.sv').read_text()
        if component.count('.MEMORY_READ_EXTRA(PROBE_BAD_REPLY ? 0 : S8_SRAM_MIF)')!=8 or 'localparam integer S8_MEMORY_ALIGNMENT = 3;' not in component:
            raise ValueError('actual eight-head MIF/CROM3 source projection required')
        if 'qfd_dv_s8_suvm_rp1 #(.MIF(S8_SRAM_MIF)) u_suvm' not in component:
            raise ValueError('source projection lacks the coupled actual SUVM MIF input')
    out.mkdir(parents=True,exist_ok=False);dest=out/'input';dest.mkdir();sources=[];hashes={}
    for i,name in enumerate(source_list.read_text().splitlines()):
        src=Path(name)
        if native_component and not src.is_absolute():src=base/src
        elif not src.exists():src=base/'input'/src.name
        if src.name in ('tb_mu_native.sv','tb.sv'):continue
        p=dest/f'{i:03d}_{src.name}';shutil.copy2(src,p);sources.append(p);hashes[src.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    p=dest/'qfd_dv_stream_tile.sv';shutil.copy2(stream,p);sources.append(p)
    initial=[]
    for sl in m['slices']:
        s=sl['slice'];n=len(sl['crom'])*16
        initial.append(f'nwords[{s}]={n};')
        for u,records in enumerate(sl['prog_users']):
            if len(records)!=1 or records[0]['addr']!=8:raise ValueError('actual resident pair8 required')
            payload=int(records[0]['payload_hex'],16);f=D.su_unpack(payload&((1<<457)-1))
            if payload>>512 or f['c']!=1088+2048*u or f['b']!=400+4096*u or f['a']!=4096*u or f['nin']*f['nout']!=n or f['ma']!=V.MA_AB or not f['mc'] or not f['csrc']:
                raise ValueError('linked native HEAD instruction or allocation differs')
            initial.append(f"prog[{s}][{u}]=1024'h{payload:0256x};")
            raw=dict(f);raw.update(ma=0,mc=0)
            initial.append(f"rawprog[{s}][{u}]=1024'h{D.su_word(**raw):0256x};")
        for r in sl['crom']:
            P.encode(1,r['addr'],r['payload_hex']);row=r['addr']-68
            if row<0 or row>=24:raise ValueError('HEAD resident row bounds')
            initial.append(f"gains[{s}][{row}]=1024'h{r['payload_hex']};")
            val=int(r['payload_hex'],16)
            for j in range(16):
                g=(val>>(64*j))&0xffffffff
                if not 0<(g>>23)&255<250:raise ValueError('finite normal model gain required')
                # X=2**(u+1), RSTD=0.5: first product is exactly2**u;
                # scaling each normal FP32 checkpoint gain changes exponent only.
                initial.append(f"gold[{s}][{row*16+j}]=32'h{g:08x};")
    tb=Path(__file__).with_name('tb_head_apply_native.sv').read_text().replace('// SOURCE_INITIALIZERS','\n'.join(initial))
    if native_component:
        tb=tb.replace('qfd_dv_s8_flat dut(',f'native_su_component #(.PROBE_MIF({memory_read_extra}),.PROBE_BAD_REPLY(HEAD_BAD_REPLY)) dut(')
    elif memory_read_extra!=0:
        raise ValueError('legacy HEAD packet profile must remain3/0')
    p=dest/'tb_mu_native.sv';p.write_text(tb);sources.append(p)
    (out/'source.f').write_text(''.join(str(p.relative_to(out))+'\n'for p in sources))
    if (base/'defines.f').exists():shutil.copy2(base/'defines.f',out/'defines.f')
    elif native_component:(out/'defines.f').write_text('')
    else:raise ValueError('legacy source packet lacks defines.f')
    runner=Path(__file__).with_name('run_head_apply_gate.sh').read_text()
    if native_component:
        # A separately named run directory preserves every failed build/runtime.
        runner="""#!/bin/bash
set -uo pipefail
ulimit -c 0
cd "$(dirname "$0")"
case "${HEAD_BAD_REPLY:-0}" in 0) tag=baseline;; 1) tag=old_reply;; *) exit 2;; esac
mkdir "$tag" || { echo REFUSE_EXISTING_RUN;exit 3; }
sha256sum -c packet.sha256 >"$tag/input_guard.log" 2>&1 || { echo SOURCE_GUARD_FAIL >"$tag/status";exit 3; }
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
echo "BUILD_START $(date -Is) host=$(hostname -s)" >"$tag/status"
/usr/bin/time -v -o "$tag/build.time" "$VL" --binary --timing -j 1 -O0 -finline --output-groups 64 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' $(cat defines.f) -GHEAD_BAD_REPLY=${HEAD_BAD_REPLY:-0} --top-module tb_mu_native -f source.f --Mdir "$tag/obj" >"$tag/build.log" 2>&1
rc=$?;echo "BUILD_RC=$rc $(date -Is)" >>"$tag/status"
[ "$rc" = 0 ] || exit "$rc"
/usr/bin/time -v -o "$tag/base.time" ./"$tag"/obj/Vtb_mu_native >"$tag/base.log" 2>&1
rc=$?;echo "BASE_RC=$rc" >>"$tag/status"
if [ "${HEAD_BAD_REPLY:-0}" = 1 ];then
 [ "$rc" != 0 ] && grep -Eq 'HEAD_NATIVE_VALUE|HEAD_WRONG_OUTPUT_ADDR|HEAD_BF16_VALUE|HEAD_COVERAGE' "$tag/base.log" || exit 2
 echo CAUGHT_OLD_HEAD_REPLY_PROFILE >>"$tag/status";exit 0
fi
[ "$rc" = 0 ] && grep -q NATIVE_HEAD_APPLY_PASS "$tag/base.log" || exit 1
for mode in MUT_GAIN MUT_RAW_X MUT_USER;do
 ./"$tag"/obj/Vtb_mu_native +"$mode" >"$tag/$mode.log" 2>&1
 rc=$?;echo "$mode=$rc" >>"$tag/status"
 [ "$rc" != 0 ] && grep -Eq 'HEAD_NATIVE_VALUE|HEAD_WRONG_OUTPUT_ADDR|HEAD_BF16_VALUE' "$tag/$mode.log" || exit 2
done
echo PASS_NATIVE_HEAD_APPLY_COMPONENT >>"$tag/status"
"""
    (out/'run_gate.sh').write_text(runner)
    receipt=dict(status='PREP_ONLY_NOT_LAUNCHED',unchanged_native_sources=hashes,
        source_projection_metadata=json.loads((base/'inputs.json').read_text()) if native_component else None,
        memory_profile=dict(MEMORY_ALIGNMENT=3,MEMORY_READ_EXTRA=memory_read_extra),
        native_component=native_component,old_reply_control='HEAD_BAD_REPLY=1 separate build' if native_component else None,
        stage_source=str(stage),stage_sha256=hashlib.sha256(stage.read_bytes()).hexdigest(),stream_source_sha256=hashlib.sha256(stream.read_bytes()).hexdigest(),
        source_files=len(sources),source_bytes=sum(p.stat().st_size for p in sources),cases=48,words=16384,
        controls=['MUT_GAIN','MUT_USER','MUT_RAW_X']+(['HEAD_BAD_REPLY=1'] if native_component else []),
        dates='actual input sampling edges for CALR, read request, native S2 operand capture, first/last VM write and first/last BF16 stream; no programme-date selection',
        boundary='actual native SU/VM and production stream tile; command/table/VM fixture adapters, external initialized RSTD; no ROOT, calendar, multi-slice transport or whole token')
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    files=sorted(p for p in out.rglob('*')if p.is_file())
    (out/'packet.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n'for p in files))
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','stage','stream','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--native-component',action='store_true')
    p.add_argument('--memory-read-extra',type=int,choices=(0,1),default=0)
    a=p.parse_args();r=prepare(a.base,a.stage,a.stream,a.out,native_component=a.native_component,memory_read_extra=a.memory_read_extra)
    print(json.dumps({k:r[k]for k in ('status','source_files','source_bytes','cases','words')}))
