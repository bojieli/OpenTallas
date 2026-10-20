import pathlib,subprocess,hashlib,json,base64,io,tarfile,sys
w=pathlib.Path(__file__).resolve().parents[3];b='rtl/qwen_sys/static_kv_20261014/';m='physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/';paths=[b+'qkd_kvpc_sram_1019.sv',b+'qkd_kvpc_front_native32_1020.sv',b+'qkd_static_kv_pc_path_nc.sv',b+'qkd_kv_hbm_elastic_front_mc.sv',m+'ot_sram_1r1w2c_32x64_m1.v','rtl/test/qwen_static_kv/kvpc_sram/tb_kvpc_front.sv'];files={p:(w/p).read_bytes()for p in paths};p=paths[-1];s=files[p].decode().replace('qkd_kvpc_s_front #','qkd_kvpc_s_front_native32 #');init='''
        #1;u_ref.out_q={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};u_dut.out_q=u_ref.out_q;
''';
for g in range(4):init+='        for(integer j=0;j<32;j=j+1)u_ref.g_storage['+str(g)+'].bank_mem[j]={$urandom,$urandom,$urandom};\n'
for g in range(5):init+='        for(integer j=0;j<32;j=j+1)u_dut.u_mem.g_b['+str(g)+'].u_m.arr[j]={$urandom,$urandom};\n'
s=s.replace('repeat (10) @(negedge clk);',init+'        repeat (10) @(negedge clk);');files[p]=s.encode();manifest={p:hashlib.sha256(x).hexdigest()for p,x in files.items()};ident=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:10];e=w/'results/rtl/kv_pc_native32_1020';(e/('front_inputs_'+ident+'.json')).write_text(json.dumps(manifest,indent=1)+'\n');buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz')as t:
 for p,x in files.items():i=tarfile.TarInfo(p);i.size=len(x);t.addfile(i,io.BytesIO(x))
code='''import pathlib,tarfile,io,base64,os,subprocess
p=pathlib.Path(os.environ.get('OT_SCRATCH','/srv/opentallas-scratch'))/'claude'/__NAME__;p.mkdir(exist_ok=True);os.chdir(p);tarfile.open(fileobj=io.BytesIO(base64.b64decode(__PAYLOAD__)),mode='r:gz').extractall();print('SOURCE_ROOT',p,flush=True)
v=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
for m in [0,1,4,5]:
 with open('m'+str(m)+'-build.log','w')as f:r=subprocess.run([v,'--binary','--timing','-O2','-j','4','-Wno-fatal','--top-module','tb_kvpc_front','-DKVPC_MUT='+str(m),'--Mdir','obj'+str(m),*__FILES__],stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:print(pathlib.Path('m'+str(m)+'-build.log').read_text()[-3000:]);raise SystemExit(r.returncode)
 r=subprocess.run(['obj'+str(m)+'/Vtb_kvpc_front'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);pathlib.Path('m'+str(m)+'.log').write_text(r.stdout);print(r.stdout[-2000:],flush=True)
 if (m==0 and 'KVPC_FRONT PASS'not in r.stdout)or(m!=0 and 'KVPC_FRONT FAIL'not in r.stdout):raise SystemExit(2)
print('PC_FRONT_NATIVE32_EXPECTED_VERDICTS_PASS',flush=True)
'''.replace('__NAME__',repr('codex-pc-front-native32-'+ident)).replace('__PAYLOAD__',repr(base64.b64encode(buf.getvalue()).decode())).replace('__FILES__',repr(list(files)))
raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','12','--threads','4','--dir','/tmp','--','python3','-c',code]))
