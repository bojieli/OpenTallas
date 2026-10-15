import hashlib,json,pathlib,subprocess,shutil
s=pathlib.Path('/srv/opentallas-scratch/codex/s81-hcx-shared-gain-1014')
image=pathlib.Path('/srv/opentallas-scratch/codex/s81-hcx-shared-gain-1014/shared_resident_image')
vec=pathlib.Path('/srv/opentallas-scratch/codex/s81-hcx-native-1014/post_native_sweep/L00')
assert (s/'build_exit.txt').read_text().strip()=='0'
exe=s/'obj/Vtb_s81_hcx_post_gain_native'
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
command=json.loads((s/'command.json').read_text())
manifest={str(s/'src'/p):sha(s/'src'/p) for p in command if (s/'src'/p).is_file()}
mut=s/'gain_bit_mutant';mut.mkdir(exist_ok=True)
for m in range(4):shutil.copyfile(image/f'hcx_post_p{m}.viamap.hex',mut/f'hcx_post_p{m}.viamap.hex')
p=mut/'hcx_post_p0.viamap.hex';rows=p.read_text().split();rows[64]=f'{int(rows[64],16)^(1<<120):0144x}';p.write_text('\n'.join(rows)+'\n')
records=[]
for name,masks in [('positive',image),('weight_bit_mutant',mut)]:
 args=[str(exe),f'+DIR={vec}',f'+GAIN={image}',f'+OT_ROM_DIR={masks}']
 r=subprocess.run(args,capture_output=True,text=True);(s/f'{name}.log').write_text(r.stdout+r.stderr)
 records.append(dict(name=name,exit=r.returncode,command=args))
 if name=='positive':assert r.returncode==0 and 'gainrows640 errors0 fault0' in r.stdout,r.stdout[-2000:]
 else:assert r.returncode!=0 and 'shared gain arithmetic mismatch' in r.stdout,r.stdout[-2000:]
rec=dict(scope='Actual shared four-ROM post/gain and fixed-slot VM pin boundary',full_native_token=False,physical_qualified=False,macros=4,additional_macros=0,mode='compiler-owned fixed slots, no arbitration',jobs='post attn+ffn, main+draft gains, post attn+ffn without reset',arithmetic='unchanged ot_hgi_hc_unit op2 and BF16 gain expansion',source_sha256=manifest,binary_sha256=sha(exe),runs=records,mutant=dict(address=512,rom=0,payload_bit=15,original_sha256=sha(image/'hcx_post_p0.viamap.hex'),mutant_sha256=sha(p)))
(s/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
print('S81_POST_GAIN_SHARED PASS actual six jobs + same-binary ROM sign-bit mutant')
