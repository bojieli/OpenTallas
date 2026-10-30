from pathlib import Path
import json
import shutil
import subprocess

lane = Path('/srv/opentallas-scratch2/claude/codex-flow-hold-2249')
repo = Path('/srv/opentallas-scratch2/claude/wt/codex-flow-hold-2249')
original = Path('/srv/opentallas-scratch2/claude/kv-kits-18-1029/phy_pad/qkd_hr_phy_pad__86.4x95.04')
archive = Path('/srv/opentallas-scratch2/claude/die-kv-30-1029/phy_selA')
nick = 'hc_qkd_hr_phy_pad__86_4x95_04'
base = lane / 'phy_baseline'
out = lane / 'phy_hb4_m10'
if base.exists() or out.exists():
    raise SystemExit('refuse existing trial outputs')
base.mkdir()
subprocess.run(['rsync', '-a', '--exclude', '/run', '--exclude', '/views', '--exclude', '/signoff', '--exclude', '/signoff_*', str(original) + '/', str(base) + '/'], check=True)
src = archive / 'run/results/asap7' / nick / 'base'
dst = base / 'run/results/asap7' / nick / 'base'
dst.mkdir(parents=True)
for name in ('5_2_route.odb', '6_final.spef', '1_2_yosys.v', '1_synth.v', 'clock_period.txt', 'mem.json', 'ot_face_flops.txt', 'ot_unreg_pins.txt'):
    if (src / name).is_file():
        shutil.copy2(src / name, dst / name)
objects = base / 'run/objects/asap7' / nick / 'base'
objects.mkdir(parents=True)
subprocess.run(['rsync', '-a', str(archive / 'run/objects/asap7' / nick / 'base') + '/', str(objects) + '/'], check=True)
maker = repo / 'physical/die_plan/qwen_kvsys/cores/harden/eco/mk_eco.sh'
subprocess.run(['bash', str(maker), str(base), str(out), 'm10', str(repo)], check=True)
prd = repo / 'tools/die_plan/post_route_drv'
for name in ('prd_hook.tcl', 'prd_count.tcl', 'prd_run.sh', 'prd_mk.sh'):
    shutil.copy2(prd / name, out / name)
for name in ('orfs_hold_mm.py', 'orfs_hold_mm.tcl'):
    shutil.copy2(repo / 'tools' / name, out / name)
shutil.copy2(repo / 'physical/common_flow/hold_pad_hb4.tcl', out / 'hold_pad_hb4.tcl')
post = 'source /work/kit_modes_eco.tcl\nsource /work/hold_pad_hb4.tcl\nsource /work/prd_hook.tcl\nkit_modes_eco_done\n'
if (out / 'grt_post_core.tcl').is_file():
    post += 'source /work/grt_post_core.tcl\n'
(out / 'eco_post.tcl').write_text(post)
env = (out / 'variant.env').read_text().replace('OT_MAX_FANOUT=24', 'OT_MAX_FANOUT=0')
(out / 'variant.env').write_text(env)
(out / 'PRD.json').write_text(json.dumps(dict(tool='post_route_drv', variant='m10', source_kit=str(original), source_route=str(src / '5_2_route.odb'), source_route_frame='actual untouched 03:17 baseline post-route, not GRT', parasitics=str(src / '6_final.spef'), signoff_tools=str(repo)), indent=2) + '\n')
print(json.dumps(dict(out=str(out), frame='post_route', margin=10, max_fanout=0, max_wire=0, guard='current MM chunked helper', hb4=True)))
