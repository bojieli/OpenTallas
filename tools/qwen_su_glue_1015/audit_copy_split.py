#!/usr/bin/env python3
import hashlib,json,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
def source(path):return subprocess.check_output(['git','show','c6c44c12c:'+path],cwd=root).decode()
old=source('rtl/qwen_split/qfd_su_static_copy.sv')
new=(root/'rtl/physical/ot_qfd_su_copy_core.sv').read_text()
pattern=r'always @\(posedge ck or negedge rst_n\) begin.*?\n end\n'
a=re.search(pattern,old,re.S).group();b=re.search(pattern,new,re.S).group();assert a==b
wrapper=(root/'rtl/physical/qfd_su_static_copy_entries.sv').read_text()
marker=' wire [2366:0] copy_va;'
assert wrapper[wrapper.index(marker):]==old[old.index(marker):]
parent=subprocess.check_output(['git','show','96f30a6a0:rtl/qwen_split/qfd_sp_su64_sfu.sv'],cwd=root).decode()
candidate=(root/'rtl/physical/qfd_sp_su64_sfu_glue_entries.sv').read_text()
r=candidate.removeprefix('// Distinct source-preserving347root successor; historical346root source unchanged.\n')
r=r.replace('module qfd_sp_su64_sfu_glue_entries #(','module qfd_sp_su64_sfu #(',1)
r=r.replace('    input wire ck_copy, // exact existing static-copy state root; no added edge\n','',1)
r=r.replace('qfd_su_static_copy_entries #(.READ_EDGES(15),.DATA_MUT(COPY_DATA_MUT)) u_copy(.ck_copy(ck_copy),','qfd_su_static_copy #(.READ_EDGES(15),.DATA_MUT(COPY_DATA_MUT)) u_copy(.ck(ck),',1)
r=r.replace('ot_qfd_sp_su64_static_glue_entries #(','ot_qfd_sp_su64_static_entries #(',1)
assert r==parent
inner=source('rtl/qwen_sys/static_schedule_20261014/ot_qfd_sp_su64_static_entries.sv')
ni=(root/'rtl/physical/ot_qfd_sp_su64_static_glue_entries.sv').read_text()
assert ni.replace('module ot_qfd_sp_su64_static_glue_entries #(','module ot_qfd_sp_su64_static_entries #(',1).replace('ot_hdc_vstream_static_relay_entries #(.RELAY_CUT(1),','ot_hdc_vstream_static_entries #(',1)==inner
def clocks(s):
 h=s[s.index('module '):s.index(');',s.index('module '))]
 h=re.sub(r'//[^\n]*','',h)
 return sorted(set(re.findall(r'\bck(?:_[A-Za-z0-9]+)?\b',h)))
oc,nc=clocks(parent),clocks(candidate)
assert len(oc)==346 and len(nc)==347 and set(nc)-set(oc)=={'ck_copy'}
print(json.dumps(dict(schema='opentallas.qwen-su-copy-source-audit.v1',original_commit='c6c44c12c',outer_parent_commit='96f30a6a0',registered_cp_active_status_preserved=True,original_copy_sha256=hashlib.sha256(old.encode()).hexdigest(),sequential_always_sha256=hashlib.sha256(a.encode()).hexdigest(),sequential_always_exact=True,parent_mux_packaging_exact=True,other_parent_source_exact=True,old_clock_roots=346,new_clock_roots=347,new_clock='ck_copy',clock_roots=nc,cycles_added=0,state_bits_added=0,source_files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'rtl/physical/ot_qfd_su_copy_core.sv',root/'rtl/physical/qfd_su_static_copy_entries.sv',root/'rtl/physical/qfd_sp_su64_sfu_glue_entries.sv',root/'rtl/physical/ot_qfd_sp_su64_static_glue_entries.sv']}),indent=2))
