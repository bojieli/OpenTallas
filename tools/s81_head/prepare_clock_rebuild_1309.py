from pathlib import Path
import shutil,json
r=Path('/srv/opentallas-scratch2/claude/wt/codex-head1309')
src=Path('/srv/opentallas-scratch2/claude/path-s81-headb/elemB_if2d')
d=Path('/srv/opentallas-scratch2/claude/codex-head1309/elemB_if2e')
shutil.copytree(src,d,ignore=shutil.ignore_patterns('run','*.log','signoff','views','__pycache__'))
p=d/'run/results/asap7/hd_elemB_rb/base';p.mkdir(parents=True)
for f in (src/'run/results/asap7/hd_elemB_rb/base').iterdir():
 if f.is_file() and (f.name[0] in '123' or f.name in ['clock_period.txt','mem.json']):shutil.copy2(f,p/f.name)
shutil.copy2(r/'tools/die_plan/leaf_affinity.tcl',d/'leaf_affinity.tcl')
(d/'head_cts_post.tcl').write_text('# Structural zero-logic logical-stage clock groups, native single clock only.\nuplevel #0 [list source /work/leaf_affinity.tcl]\n')
(d/'config.mk').write_text((d/'config.mk').read_text()+'''\n# HEAD1309: rebuild macro and register clock trees at balanced levels; avoid ROM obstacles.
export CORNER = TC
export CORNERS = tc
export OT_HOLD_MM = 0
export SKIP_CTS_REPAIR_TIMING = 1
export POST_CTS_TCL = /work/head_cts_post.tcl
export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 -balance_levels -obstruction_aware -macro_clustering_size 2 -macro_clustering_max_diameter 40
''')
(d/'clock_rebuild.json').write_text(json.dumps(dict(seed=str(src),source_data='byte-identical RTL and placed data cells; rebuild from3_place',target='equal macro/register tree depth and guarded same-clock zero-logic stage affinity',added_cycles=0,expected='Remove confirmed macro0 CK early62-78ps versus IF; improve short shift-stage leaf skew. Actual GRT calibration and review required.',geometry_review='Inherited actual3_place/ROM IF images viewed, no pin/macro/data placement change; clock structure changes only.',route_approval=False),indent=1)+'\n')
print(d)
