from pathlib import Path
import json
import shutil
import subprocess

lane = Path('/srv/opentallas-scratch2/claude/codex-flow-hold-2249')
repo = Path('/srv/opentallas-scratch2/claude/wt/codex-flow-hold-2249')
base = lane / 'phy_baseline'
old = lane / 'phy_hb4_m10'
out = lane / 'phy_hb4_m10b'
if out.exists():
    raise SystemExit('refuse existing retry output')
subprocess.run(['bash', str(repo / 'physical/die_plan/qwen_kvsys/cores/harden/eco/mk_eco.sh'), str(base), str(out), 'm10', str(repo)], check=True)
for name in ('prd_hook.tcl', 'prd_count.tcl', 'prd_run.sh', 'prd_mk.sh', 'orfs_hold_mm.py', 'orfs_hold_mm.tcl', 'hold_pad_hb4.tcl', 'eco_post.tcl', 'PRD.json'):
    shutil.copy2(old / name, out / name)
config = (out / 'config.mk').read_text()
assert 'export OT_HOLD_MM = 1' in config, 'expected coupled TT/FF PHY kit'
env = (out / 'variant.env').read_text().replace('OT_MAX_FANOUT=24', 'OT_MAX_FANOUT=0')
env += 'OT_HOLD_MM_KIT=1\n'
(out / 'variant.env').write_text(env)
print(json.dumps(dict(out=str(out), correction='KV maker to PRD runner adapter now carries MM staging marker', mode='TT/FF two-mode; guard retained')))
