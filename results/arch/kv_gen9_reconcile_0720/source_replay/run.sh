#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/codex-kv-ba-regen-0720
mkdir -p "$base"
git --git-dir=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git worktree add --detach "$base/src" 04b625135 > "$base/checkout.log" 2>&1
cd "$base/src"
for variant in r s; do
 cp "/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-04b625135-gen9d11$variant/kv_flags.env" "$base/flags_$variant.env"
 (
  source "$base/flags_$variant.env"
  python3 - "$base" "$variant" <<'PY'
import sys,json,hashlib,re,subprocess
from pathlib import Path
base=Path(sys.argv[1]);variant=sys.argv[2];sys.path.insert(0,'tools/qwen_kv_die');import kv_static_die as k
p=Path(k.RTL_FILE);old=p.read_bytes() if p.exists() else b'';txt=k.rtl_text();new=txt.encode();(base/f'before_{variant}.sv').write_bytes(old);(base/f'after_{variant}.sv').write_bytes(new)
def modules(s):
 return {m[1]:dict(header=m[2].splitlines()[:5],ports=re.findall(r'^\s*(?:input|output|inout)\b[^;\n,]*',m[2],re.M)) for m in re.finditer(r'^module\s+(\w+)\b(.*?)^endmodule',s,re.M|re.S)}
a=modules(old.decode());b=modules(txt)
out=dict(scope='SOURCE_GENERATION_ONLY no live case changes no gate no native qualification',variant=variant,selected_file=k.RTL_FILE,before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest(),equal=(old==new),before_modules=sorted(a),after_modules=sorted(b),port_changes={n:dict(before=a.get(n),after=b.get(n)) for n in sorted(set(a)|set(b)) if a.get(n)!=b.get(n)})
(base/f'regeneration_{variant}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='port_changes'}))
PY
 ) > "$base/regen_$variant.log" 2>&1
 done
