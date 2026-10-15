#!/usr/bin/env python3
import hashlib,json,subprocess,shutil
from pathlib import Path
repo=Path('/home/ubuntu/wt/codex-s81-pq-collective-1103');here=Path(__file__).resolve().parent;dst=here/'join_source';base='2eb33e9a8';closure=subprocess.check_output(['python3','tools/die_port_bind.py','none','--closure','dsfd_sp_vm'],cwd=repo,text=True).splitlines()
paths=[str(Path(x).relative_to(repo)) for x in closure]
paths+=json.loads((here.parent/'census/source_paths.json').read_text())
paths+=['rtl/ot_fp32_rne_pkg.sv','tools/s81_static_collective/tb_s81_static_collective_slab.sv','tools/s81_static_collective/build_slab_fixture.py','tools/s81_static_collective/controller_image.py','physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
records=[]
for name in dict.fromkeys(paths):
 data=subprocess.check_output(['git','-C',str(repo),'show',base+':'+name]);p=dst/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);records.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),binding='git:'+base))
for p in (here.parents[3]/'rtl/dsrom_sys/s81_static_collective/physical_roots').glob('*.sv'):
 name=str(p.relative_to(here.parents[3]));data=p.read_bytes();q=dst/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data);records.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),binding='new root candidate'))
slab=dst/'rtl/dsrom_sys/s81_static_collective/s81_static_collective_slab.sv';s=slab.read_text();start=s.index(' s81_static_hc_reduce_clocked #');end=s.index(' wire raw_send;',start)
replacement=''' wire[31:0]row_tag;
 assign t_hc_tag=row_tag;
 s81_static_hc_roots hc_roots(
 .clk_lane(ck_hc_lane),.clk_control(ck_control[4]),.rst_n(rst_n),.reduce_slot(hc_reduce_slot),
 .rank_valid(gather_we&{4{hc_reduce_slot}}),.rank_data(gather_data),.tag(gather_tag),.seq(gather_seq),.last(gather_last),
 .word_valid(reduced_valid),.word_data(reduced_data),.word_tag(reduced_tag),.word_seq(reduced_seq),.word_last(reduced_last),.word_error(reduced_error),.reduce_fault(reduce_fault),
 .assemble_slot(hc_assemble_slot),.word_index(hc_word_index),.emit_slot(hc_emit_slot),.emit_tag(hc_emit_tag),
 .row_valid(t_hc_yv),.row_data(t_hc_y),.row_tag(row_tag),.assemble_fault(assemble_fault));
'''
s=s[:start]+replacement+s[end:];assert 'for(root=0;root<5;' in s;s=s.replace('for(root=0;root<5;','for(root=0;root<4;');slab.write_text(s)
records.append(dict(path=str(slab.relative_to(dst)),sha256=hashlib.sha256(s.encode()).hexdigest(),binding='temporary integration: replace original HC pair and move original control4 reset into metadata root; no functional edge changes'))
# Compile all required source snapshots except alternative top wrappers/test benches.
compile_paths=[x for x in dict.fromkeys(paths) if x.endswith(('.sv','.v')) and not x.startswith('tools/')]
compile_paths+= [str(x.relative_to(dst)) for x in (dst/'rtl/dsrom_sys/s81_static_collective/physical_roots').glob('*.sv')]
compile_paths+=['tools/s81_static_collective/tb_s81_static_collective_slab.sv']
(here/'join_source_manifest.json').write_text(json.dumps(dict(base_commit=base,files=records,compile_paths=compile_paths),indent=2)+'\n')
script='''#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/join_source" && pwd)
WORK=$(mkdir -p "$ROOT/../join_run" && cd "$ROOT/../join_run" && pwd)
python3 "$ROOT/tools/s81_static_collective/build_slab_fixture.py" --out "$WORK" > "$WORK/fixture.log"
cd "$WORK"
V=${OT_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81_static_collective_slab --Mdir obj '''+' '.join('"$ROOT/'+x+'"' for x in compile_paths)+''' > build.log 2>&1
./obj/Vtb_s81_static_collective_slab > run.log 2>&1
cat run.log
'''
(here/'run_join.sh').write_text(script)
print(len(records),len(compile_paths),dst)
