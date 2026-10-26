import sys,json,subprocess,hashlib
from pathlib import Path
root=Path('../src').resolve();sys.path.insert(0,str(root/'rtl/test/mu_qwen_seq'))
import mu_seq_bench as B
rec=json.loads(Path('image_cap1/descriptor.json').read_text())
body=json.loads(Path('body.json').read_text())
pw=[int(x,16) for x in Path('pw_metadata.hex').read_text().split()]
dw=rec['descriptor']
assert len(pw)==1024 and len(dw)==8 and pw[1023]>>12&1
def digest(words):
    d=0x51484f5354505247
    for i,v in enumerate(words):
        d=((d<<7)|(d>>57))&((1<<64)-1)
        desc=int(i>=1024);addr=i-1024 if desc else i
        d^=v  # exact64 data word; descriptor/address xor follows
        d^=(desc<<10)|addr
    return d
auth=digest(pw+dw)
sources=[str(root/p) for p in B.SOURCES]+[str(root/'rtl/qwen_dv/qfd_dv_calendar_rom.sv'),
 str(root/'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v'),
 str(root/'rtl/test/qwen_dv/tb_qfd_dv_calendar_cap1_install.sv'),str(root/'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv')]
vl=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
obj=Path('cap1_obj').resolve()
r=subprocess.run([vl,'--binary','--timing','-Wno-fatal','-j','4','--top-module','tb_qfd_dv_calendar_cap1_install',
 '-GNU=4','-GUVM_STRIDE=4096','-GPIDX_STRIDE=128','-Mdir',str(obj)]+sources,capture_output=True,text=True)
Path('cap1_build.log').write_text(r.stdout+r.stderr)
if r.returncode:raise RuntimeError('build failed')
Path('cap1_sources.sha256').write_text(''.join(hashlib.sha256(Path(p).read_bytes()).hexdigest()+'  '+p+'\n' for p in sources))
def events(words,authorize):
    return [(1,4,0),(3,5,authorize),(6,6,(3000<<18)|(1<<17))]+[(10+i,0,(i<<64)|v) for i,v in enumerate(words)]+[(1034+i,1,(i<<64)|v) for i,v in enumerate(dw)]
def run(name,ev,expect):
    e=Path(name+'.ev');e.write_text(''.join(f'{c} {k} {v:x}\n' for c,k,v in sorted(ev)))
    log=Path(name+'.log')
    r=subprocess.run([str(obj/'Vtb_qfd_dv_calendar_cap1_install'),f'+EV={e.resolve()}',f'+LOG={log.resolve()}',
      '+NCYC=5000',f'+OT_ROM_DIR={Path("image_cap1").resolve()}'],capture_output=True,text=True)
    Path(name+'.out').write_text(r.stdout+r.stderr)
    if expect:
        assert r.returncode==0,r.stdout+r.stderr
        lines=log.read_text().splitlines();commit=[l for l in lines if 'RECEIVER_COMMIT' in l]
        assert len(commit)==1 and commit[0].split()[2:]==['7',f'{auth:016x}','1'],commit
        assert any(' EMB ' in l for l in lines)
        print('CAP1_CALENDAR_COPY_INSTALL_PASS',commit[0],flush=True)
    else:
        assert r.returncode!=0 and ('CALENDAR_RECEIVER_REJECT' in r.stdout or 'CALENDAR_RECEIVER_CAP1_REQUIRED' in r.stdout or 'CALENDAR_RECEIVER_NOT_COMMITTED' in r.stdout)
        print('CAP1_MUTANT_REJECT',name,flush=True)
# Realcap1 metadata and fresh explicit INIT: no prior result emit.
rr=rec['ranges']['init']
start=(1200,3,(rr['first']<<8)|(rr['count']<<18))
run('cap1_nominal',events(pw,auth)+[start,(2200,2,1)],True)
bad=pw.copy();bad[0]^=1;run('cap1_payload_digest_mut',events(bad,auth),False)
bad=pw.copy();bad[1023]^=1<<12;run('cap1_clear_cap_mut',events(bad,digest(bad+dw)),False)
run('cap1_auth_digest_mut',events(pw,auth^1),False)
run('cap1_early_execution_mut',events(pw,auth)+[(1042,2,1)],False)
run('cap1_missing_final_drain_mut',events(pw,auth)[:-1],False)
Path('cap1_receipt.json').write_text(json.dumps(dict(schema='opentallas.qwen.calendar-copy-cap1-install.v1',
 source=body['source'],authorized_digest=f'{auth:016x}',entries=rec['entries'],metadata_words=body['source']['metadata_words'],
 scope='actual cal_mu macro-observed calendar PW/DW copy only; real L-player execution_active binding matching existing FACE; diagnostic one-END L image; ME/XPF sink acceptance and production phase unbound',
 production_bound=False),indent=2)+'\n')
