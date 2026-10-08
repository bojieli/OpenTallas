#!/usr/bin/env python3
"""Reproduce the full-slot combined ingress/direct-readback provider gate."""
import argparse,pathlib,json,hashlib,subprocess,shutil,re
p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--book',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--negative',type=int,choices=(0,2),default=0);p.add_argument('--lease-probe',action='store_true');a=p.parse_args()
if a.lease_probe and a.negative:raise SystemExit('--lease-probe and --negative are separate cases')
book=a.book or a.root/'results/rtl/qwen_rom_vm_combined_ingress_20261007';a.out.mkdir(parents=True,exist_ok=True)
if (a.out/'run.log').exists():raise SystemExit('refusing to overwrite existing run evidence; use a new output directory')
pins=json.loads((book/'pins.json').read_text())
for name,want in pins.items():
 src=book/name
 if hashlib.sha256(src.read_bytes()).hexdigest()!=want:raise SystemExit('source pin mismatch: '+name)
 dst=a.out/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
for name in ['addresses.hex','enables.hex']:shutil.copyfile(book/name,a.out/name)
sources=['ot_gpu_w6_secded_pkg.sv','ot_hdc_cg.sv','ot_sram_1r1w_512x128_m4_r2c2.v','ot_qwen_rom_vm_ingress_adapter.sv','ot_qwen_vm_bank4_direct_readback.sv','ot_qwen_checked_vm_bank_direct_readback.sv','ot_qwen_rom_vm_request_normalizer.sv','bench.sv']
if a.lease_probe:
    shutil.copyfile(book/'lease_probe/bench.sv',a.out/'src/bench.sv')
cmd=['iverilog','-g2012','-s',('tb_lease' if a.lease_probe else 'tb_qwen_vm_combined_ingress'),'-o',str(a.out/'sim')]+[str(a.out/'src'/s)for s in sources]
with (a.out/'build.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
fixture=a.root/'results/rtl/qwen_hbm_activation_vm_realization_20261005/minimum_adapter_case/initial_x4096.u32.hex'
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==json.loads((book/'summary.json').read_text())['fixture_sha256']
cmd=['/usr/bin/time','-v','-o',str(a.out/'resources'),'vvp',str(a.out/'sim'),f'+FIXTURE={fixture}',f'+ADDRESSES={a.out/"addresses.hex"}',f'+ENABLES={a.out/"enables.hex"}',f'+NEGATIVE={a.negative}']
with (a.out/'run.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
log=(a.out/'run.log').read_text()
if a.lease_probe:
 assert r.returncode==0 and 'native_me_lease0 edges=3125' in log
elif a.negative:
 assert r.returncode!=0 and 'UNPAID_NATIVE_ADVANCE' in log
else:
 assert r.returncode==0 and 'PASS COMBINED_INGRESS_DIRECT_READBACK' in log
 frames={int(k):dict(edges=int(e),reads=int(rd),acks=int(ack))for k,e,rd,ack in re.findall(r'FRAME kind=(\d+) physical_edges=(\d+) read_delta=(\d+) checked_ACK_delta=(\d+)',log)}
 assert frames[1]==dict(edges=14419,reads=1024,acks=1),frames[1]
 assert frames[3]['reads']==0 and frames[3]['acks']==1,frames[3]
 assert frames[5]['reads']==0 and frames[5]['acks']==0,frames[5]
 assert frames[7]['reads']==0 and frames[7]['acks']==0,frames[7]
(a.out/'verdict.json').write_text(json.dumps(dict(pass_expected_outcome=True,exit_code=r.returncode,negative=a.negative,lease_probe=a.lease_probe,selected_bench_sha256=hashlib.sha256((a.out/'src/bench.sv').read_bytes()).hexdigest(),log_sha256=hashlib.sha256(log.encode()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),scope='Full-slot source-captured parent160 plus directed capture/bounds/zero mechanisms through actual protected provider. No full core, collective or whole-model enrollment.'),indent=2)+'\n')
print('PASS expected outcome',a.negative)
