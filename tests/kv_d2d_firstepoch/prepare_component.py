#!/usr/bin/env python3
"""Stage immutable dependency copies and current private source; does not compile."""
import hashlib,json,pathlib,shutil,sys
root=pathlib.Path(__file__).resolve().parents[2]
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
frozen=root/'results/kv_d2d_firstepoch_component_1019/frozen_inputs'
private=root/'rtl/qwen_sys/d2d_static_20261015/firstepoch_private'
inputs=list(frozen.glob('*.sv'))+list(frozen.glob('*.svh'))+list(private.glob('*.sv'))+[pathlib.Path(__file__).with_name('tb_component.sv'),pathlib.Path(__file__).with_name('run_component.sh')]
manifest={}
for p in inputs:
 shutil.copy2(p,out/p.name)
 manifest[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'staging_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(out)
