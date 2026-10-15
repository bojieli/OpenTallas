"""Real released K256 vectors, all48 rows, fixed16 beat calendar and poison gaps."""
from pathlib import Path
import subprocess,sys,json,hashlib,shutil
root=Path.cwd();out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
for n in ['w','x','head','gold']:shutil.copy2(root/f'results/rtl/dsrom_markov_row_20261008/{n}.hex',out/f'{n}.hex')
src=['rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv','rtl/experimental/dsrom_markov_20261008/ot_s81_markov_k256_native.sv','rtl/experimental/dsrom_markov_20261008/ot_s81_markov_k256_static.sv','rtl/test/dsrom_markov_20261008/tb_markov_static.sv']
mut=len(sys.argv)>2 and sys.argv[2]=='mutant'
cmd=['iverilog','-g2012','-s','tb_markov_static','-o',str(out/'sim')]+(['-DOT_S81_MARKOV_STATIC_DROP_BEAT'] if mut else [])+src
p=subprocess.run(cmd,capture_output=True,text=True);(out/'build.log').write_text(p.stdout+p.stderr)
if p.returncode:print(p.stderr[-2000:]);sys.exit(p.returncode)
p=subprocess.run(['vvp',str(out/'sim'),f'+DIR={out}'],capture_output=True,text=True);(out/'bench.log').write_text(p.stdout+p.stderr)
print(p.stdout[-800:],flush=True)
(out/'receipt.json').write_text(json.dumps({'mutant':mut,'rc':p.returncode,'stdout':p.stdout,'source_sha256':{s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in src}},indent=2)+'\n')
sys.exit(p.returncode)
