"""Updated cal-copy installation only; sidecar sink/other copies remain unbound."""
import hashlib,json,subprocess
from pathlib import Path
packet=json.loads(Path('witness_template_packet/manifest.json').read_bytes())
pw=[int(x,16) for x in Path('witness_template_packet/model_pw.hex').read_text().split()]
cal=json.loads(Path('image_cap1/descriptor.json').read_bytes());dw=cal['descriptor']
assert len(pw)==1024 and len(dw)==8
au=int(packet['calendar_copy_candidate_digest'],16)
ev=[(1,4,0),(3,5,au),(6,6,(3000<<18)|(1<<17))]
ev += [(10+i,0,(i<<64)|v) for i,v in enumerate(pw)]
ev += [(1034+i,1,(i<<64)|v) for i,v in enumerate(dw)]
rr=cal['ranges']['init'];ev += [(1200,3,(rr['first']<<8)|(rr['count']<<18)),(2200,2,1)]
p=Path('cap1_witness_packet.ev');p.write_text(''.join(f'{c} {k} {v:x}\n' for c,k,v in sorted(ev)))
binary=Path('cap1_obj/Vtb_qfd_dv_calendar_cap1_install');log=Path('cap1_witness_packet.log')
r=subprocess.run([str(binary.resolve()),f'+EV={p.resolve()}',f'+LOG={log.resolve()}','+NCYC=5000',f'+OT_ROM_DIR={Path("image_cap1").resolve()}'],capture_output=True,text=True)
Path('cap1_witness_packet.out').write_text(r.stdout+r.stderr)
assert r.returncode==0,r.stdout+r.stderr
lines=log.read_text().splitlines();commit=[l for l in lines if 'RECEIVER_COMMIT' in l]
assert len(commit)==1 and commit[0].split()==['1044','RECEIVER_COMMIT','7',f'{au:016x}','1'],commit
firstcommand=next(l for l in lines if ' CMD ' in l)
assert int(firstcommand.split()[0])==1050,firstcommand
out=dict(schema='opentallas.qwen.witness-PW-calcopy-install.v1',production_bound=False,
 scope='updated PW packet accepted by actual calendar-copy receiver/macro observer and diagnostic L player; witness-template sink and other ME/XPF copies unbound',
 packet_sha256=hashlib.sha256(Path('witness_template_packet/model_pw.hex').read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),packet_digest=f'{au:016x}',
 PW_transfer_count=1024,PW_first=10,PW_last=1033,new_useful_PW_first_sample=410,new_useful_PW_last_sample=448,
 DW_count=8,DW_first=1034,DW_last=1041,observed_calendar_copy_commit=1044,observed_first_BOOT_CMD=1050,
 calendar_copy_commit_to_BOOT_margin=6,all_copy_authentication_bound=False,
 MODEL_native_sidecar_write_last=452,MODEL_native_sidecar_seal_publication=453,MODEL_native_sidecar_first_usable=454,
 actual_sidecar_sink_sealed_sample=None,production_execution_start=None)
Path('cap1_witness_packet_receipt.json').write_text(json.dumps(out,indent=2)+'\n')
print('UPDATED_WITNESS_PACKET_CALCOPY_INSTALL_PASS',commit[0],firstcommand,'othercopies/unbound')
