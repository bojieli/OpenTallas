import hashlib,json,os
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-types-1551/q_spt0_native')
d=json.loads((R/'native_restore_manifest.json').read_text())
# Refuse any existing native context root; caller checked no prior worktree here.
roots=[Path('/srv/opentallas-scratch2/claude/hbm-bind-9'),Path('/srv/opentallas-scratch2/claude/hbm-bind-6')]
if any(p.exists() for p in roots):raise ValueError('native context prefix exists; refusing replacement')
for x in d['files']:
 src=R/'incoming'/x['flat'];assert hashlib.sha256(src.read_bytes()).hexdigest()==x['sha256'],x
for x in d['files']:
 dst=Path(x['path']);dst.parent.mkdir(parents=True,exist_ok=True);os.link(R/'incoming'/x['flat'],dst)
for root in roots:
 (root/'.keep').touch();(root/'COMPONENT_PROOF_ONLY.txt').write_text('Exact missing-input restoration for one q_spt0 component proof. Original metadata/source bytes unchanged. NOT a complete GEN/native source cohort. No source tree edits or original record replacements. See owned q_spt0_native/native_restore_manifest.json.\n')
print(json.dumps({'restored':d['files'],'scope':d['scope']},indent=2))
