from pathlib import Path
import argparse,subprocess,shutil,json,hashlib
root=Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser();a.add_argument('out',type=Path);out=a.parse_args().out.resolve()
assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
subprocess.run(['python3',str(root/'physical/qwen_tile_glue_banks_1015/prepare_parent_bench.py'),str(out)],check=True)
src=Path('rtl/qwen_sys/nknl_control_partition_20261015')
for p in (root/src).iterdir():
 dst=out/src/p.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
f=out/'sim_sources.list';paths=f.read_text().splitlines();paths=[p for p in paths if not p.endswith('tb_parent_banked.sv')]
paths += [str(p.relative_to(root)) for p in (root/src).glob('*.sv')]
f.write_text('\n'.join(paths)+'\n')
h={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
(out/'source_hashes.json').write_text(json.dumps(h,indent=1)+'\n')
