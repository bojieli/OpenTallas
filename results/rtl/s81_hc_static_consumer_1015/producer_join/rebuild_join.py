import pathlib,shlex,subprocess,json,hashlib
r=pathlib.Path.cwd()
line=(r/'obj/Vtb_s81_static_collective_slab__verFiles.dat').read_text().splitlines()[1]
args=shlex.split(line[2:].strip()[1:-1]); args[args.index('-j')+1]='4'
i=args.index('-MAKEFLAGS'); args[i+1:i+4]=[' '.join(args[i+1:i+4])]
with open('build-mutantfix.log','w') as f:
 p=subprocess.run(['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator']+args,stdout=f,stderr=subprocess.STDOUT)
if p.returncode: raise SystemExit(p.returncode)
for mode,extra in [('pass-fixed',[]),('mutant-missing-fixed',['+MUT_HC_MISSING'])]:
 with open(mode+'.log','w') as f:p=subprocess.run(['./obj/tb']+extra,stdout=f,stderr=subprocess.STDOUT)
 print(mode,p.returncode,pathlib.Path(mode+'.log').read_text(),flush=True)
 if (not extra and p.returncode) or (extra and not p.returncode):raise SystemExit(1)
manifest={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(r.glob('*')) if p.suffix in ['.sv','.v','.mem','.hex']}
pathlib.Path('source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
