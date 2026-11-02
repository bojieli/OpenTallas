"""Source-only actual SYNTH FF join; run after read_synth_inventory.tcl, never P&R."""
from pathlib import Path
import hashlib,json,sys
P=Path('/work/producer');W=Path('/work')
sys.path.insert(0,str(P/'tools/die_plan/tt_regional_origin'))
from native_inventory import build,read
config=(W/'config.mk').read_text();lines=[s for s in config.splitlines() if s.startswith('export VERILOG_FILES = ')]
if len(lines)!=1:raise ValueError('Missing/ambiguous actual native source read set')
sources=[Path(p) for p in lines[0].split('=',1)[1].split()]
libs=sorted(Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('asap7sc7p5t_*RVT_TT*.lib*'))
if len(libs)!=5:raise ValueError('Selected normal profile requires the exact five TT RVT library groups')
libs+=sorted((W/'macros').glob('*_tt.lib'))
if len(libs)!=9:raise ValueError('Selected TT_C requires the original four macro libraries')
netlist=W/'run/results/asap7/dp_tt_ctlm/base/1_2_yosys.v'
readset=dict(scope='mapped_source_ONLY',source_event='tt_regional_origin_13ff',cycles_added=0,net_ff_added=13,
 inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[W/'config.mk',W/'constraint.sdc']+libs},
 mapped_netlist_sha256=hashlib.sha256(netlist.read_bytes()).hexdigest(),physical_release=False,canonical_default_off=True)
(P/'actual_source_readset.json').write_text(json.dumps(readset,indent=1)+'\n')
try:
 result=build(P/'actual_synth.tsv',libs,W/'constraint.sdc',read(P/'full_ff_intent_HELD.json.gz'),read(P/'clock_proposal.json.gz'),P/'actual_source_readset.json',netlist,ff_only=True)
except ValueError as e:
 (P/'actual_synth_join_FAILURE.json').write_text(json.dumps(dict(status='FAIL_ACTUAL_NATIVE_JOIN',reason=str(e),physical_release=False,inventory_emitted=False),indent=1)+'\n')
 raise
import gzip
with gzip.GzipFile(filename=str(P/'actual_synth_ff_inventory.json.gz'),mode='wb',mtime=0) as f:f.write((json.dumps(result,separators=(',',':'))+'\n').encode())
print('TT_ACTUAL_SYNTH_FF_JOIN',result['status'],len(result['ff_cells']),'FF; no physical/global source credit',flush=True)
