#!/usr/bin/env python3
"""Reconstruct immutable default source and check extracted E3 mux expressions."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();source=Path('rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv');cand=source.read_text();gold=subprocess.check_output(['git','show','859fc9132:'+str(source)],text=True);rebuilt=cand
for prefix,law in [('bw','LAW'),('ws','LAWS')]:
 start=gold.index('        always @(posedge clk or negedge rst_n) if (!rst_n) '+prefix+'_we[g]');end=gold.index('\n    end endgenerate',start);original=gold[start:end]
 b=rebuilt.index('        if (WRITE_LEAVES != 0) begin : g_write_leaf');e=rebuilt.index('\n    end endgenerate',b);branch=rebuilt[b:e]
 assert original in branch,'default E3 always block changed'
 expected=original[original.index('            case (src)'):original.index('            endcase')+len('            endcase')]
 expected=re.sub(prefix+r'_line\[g\*'+law+r' \+: '+law+r'\] <=','next_line =',expected)
 expected=re.sub(prefix+r'_mask\[g\*16 \+: 16\] <=','next_mask =',expected)
 expected=re.sub(prefix+r'_data\[g\*512 \+: 512\] <=','next_data =',expected)
 assert expected in branch,'extracted mux differs from original expressions'
 rebuilt=rebuilt[:b]+original+rebuilt[e:]
rebuilt=rebuilt.replace('    // Opt-in E3 write ownership: two existing data256 masters and one control master per bank.\n    // Selection remains parent logic; no new edge or native-bank pin stage.\n    parameter integer WRITE_LEAVES = 0,\n    parameter integer WRITE_CLOCKS = 0,\n','',1).replace('    input wire [(NRB+NRBS)*3-1:0] write_ck,\n','',1).split('\n// E3 write state only.')[0]
assert rebuilt==gold,'source outside opt-in E3 additions changed'
d=dict(golden_commit='859fc9132',golden_sha256=hashlib.sha256(gold.encode()).hexdigest(),candidate_sha256=hashlib.sha256(cand.encode()).hexdigest(),default_source_reconstructed_byte_identical=True,all_non_E3_logic_preserved_byte_identical=True,source_selection_expressions_exact=True,scope='source edit isolation and expression audit; not physical or native/token qualification')
a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
