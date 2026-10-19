import sys,json,subprocess,hashlib
from pathlib import Path
root=Path('../src').resolve();sys.path.insert(0,str(root/'rtl/test/mu_qwen_seq'))
import mu_seq_bench as B
B.UVM_STRIDE=4096;B.PIDX_STRIDE=128
rec=json.loads(Path('image/descriptor.json').read_text());body=json.loads(Path('body.json').read_text())
segments=body['segments'];segments['init']=[(t,0 if ((c>>1)&7==6 and (c>>5)&1 and c>>112!=14) else c) for t,c in segments['embed']]
vl=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
sources=[str(root/p) for p in B.SOURCES]+[str(root/'rtl/qwen_dv/qfd_dv_calendar_rom.sv'),
 str(root/'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v'),str(root/'rtl/test/mu_qwen_seq/tb_mu_cmd_cal.sv')]
# Fail closed: comparison checks exact externally visible command, identity and issue edge.
for mut in (0,1,11):
    obj=Path('obj'+str(mut)).resolve()
    cmd=[vl,'--binary','--timing','-Wno-fatal','-j','4','--top-module','tb_mu_cmd_cal','-GNU=4',
         '-GCALENDAR_ROM=1','-GCTX_DW=1','-GUVM_STRIDE=4096','-GPIDX_STRIDE=128',f'-GMUT={mut}','-Mdir',str(obj)]+sources
    source_hash=hashlib.sha256(b''.join(Path(x).read_bytes() for x in sources)+str(cmd).encode()).hexdigest()
    hash_file=obj/'build.sha256'
    if not (obj/'Vtb_mu_cmd_cal').exists() or not hash_file.exists() or hash_file.read_text()!=source_hash:
        r=subprocess.run(cmd,capture_output=True,text=True);Path(f'build{mut}.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('build failed '+str(mut))
        hash_file.write_text(source_hash)
    def load(desc=None):
        dw=desc or rec['descriptor']
        return [(1+i,0,i<<64) for i in range(1024)]+[(1025+i,1,(i<<64)|x) for i,x in enumerate(dw)]
    ev=load();expected=[];start=1200
    for user,name,stage in ((u,n,s) for u in range(4) for n,s in (('embed',0),('decode',1),('head',37),('init',0))):
        if name=='init':
            rr=rec['ranges']['init'];ev.append((start,3,stage|(user<<6)|(rr['first']<<8)|(rr['count']<<18)))
        else:ev.append(B.start(start,user,stage))
        entries=segments[name]
        # Compare command and LOCAL signals, plus DONE at final entry.
        expected += B.expected_user_events([(t,c) for t,c in entries if c&1],user,start,0)[:-1]
        expected.append((start+entries[-1][0],'DONE',user,0))
        start+=entries[-1][0]+100
    exe=Path('wrapped'+str(mut)+'.sh').resolve()
    exe.write_text('#!/bin/bash\nexec '+str(obj/'Vtb_mu_cmd_cal')+' "$@" +OT_ROM_DIR='+str(Path('image').resolve())+'\n')
    exe.chmod(0o755)
    out=B.run(Path('.').resolve(),exe,f'play{mut}',ev,start)
    # Boot follows image seal at1033; check it separately by exact payload.
    actual=out['ev']
    boot=[x for x in actual if x[0]<1200]
    actual=[x for x in actual if x[0]>=1200]
    mismatch=sum(x!=y for x,y in zip(sorted(actual),sorted(expected)))+abs(len(actual)-len(expected))
    good=out['end'][0]==0 and mismatch==0 and len(boot)==2 and boot[0][3]==segments['boot'][0][1]
    print('PLAYBACK',mut,'PASS' if good else 'FAIL','mismatch',mismatch,'fault',out['end'],'counts',len(actual),len(expected),flush=True)
    if mismatch:print('FIRST',[(a,b) for a,b in zip(sorted(actual),sorted(expected)) if a!=b][:4],flush=True)
    if good != (mut==0):raise RuntimeError('wrong positive/mutant outcome')
    if mut==0:
        # Exercise all four live ROM playheads, with exact disjoint issue edges.
        boot=rec['ranges']['boot'];arb=load();want=[]
        for u in range(4):
            edge=1200+u
            arb.append((edge,3,1|(u<<6)|(boot['first']<<8)|(1<<18)))
            want+=B.expected_user_events(segments['boot'],u,edge,0)
        actual_arb=B.run(Path('.').resolve(),exe,'arb4',arb,1300)
        got=[x for x in actual_arb['ev'] if x[0]>=1200]
        if actual_arb['end'][0] or sorted(got)!=sorted(want):raise RuntimeError('four-live-playhead ROM arbitration mismatch')
        print('ROM_FOUR_LIVE_PLAYHEADS_PASS',len(got),flush=True)
        guards=[]
        bad=rec['descriptor'].copy();bad[0]|=1<<10
        guards.append(('count1024',load(bad),1200))
        guards.append(('range_unaligned',load()+[(1200,3,1|(1<<8)|(1<<18))],1300))
        guards.append(('range_overflow',load()+[(1200,3,1|(1020<<8)|(8<<18))],1300))
        for name,events,end in guards:
            guard=B.run(Path('.').resolve(),exe,'guard_'+name,events,end)
            if guard['end'][0]!=1:raise RuntimeError('guard missed '+name)
            print('CAL_GUARD_PASS',name,guard['end'],flush=True)
print('CAL_MU_REAL_BODY_MATRIX_PASS')
