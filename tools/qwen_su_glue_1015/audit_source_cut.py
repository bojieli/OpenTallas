#!/usr/bin/env python3
"""Audit source-preserving relay composition against pinned original parent."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ORIGINAL='rtl/qwen_sys/static_schedule_20261014/ot_hdc_vstream_static_entries.sv'
src=subprocess.check_output(['git','show','c6c44c12c:'+ORIGINAL],cwd=ROOT).decode()
new=(ROOT/'rtl/physical/ot_hdc_vstream_static_relay_entries.sv').read_text()
old_lane=src[src.index('    generate for (l = 0;'):src.index('    //: the embedding row:')]
new_lane=new[new.index('    generate for (l = 0;'):new.index('    //: the embedding row:')]
# Exact same native offset expressions; no migrated address arithmetic.
for marker in ['wire [AW-1:0] lcura','wire [AW-1:0] lcurb','wire [AW-1:0] lcurc','wire [AW-1:0] lcurd','wire [AW-1:0] tcura','wire [AW-1:0] tcurc']:
 a=next(x.strip() for x in old_lane.splitlines() if marker in x)
 assert a in new_lane,a
# Every original delay declaration is retained in the default path, byte exact.
a=old_lane.index('            ot_hdc_delay #(.W(GBW)')
b=old_lane.index('            wire [NW-1:0] t_i',a)
assert old_lane[a:b] in new_lane
for name in ['u_ov','u_od']:
 line=next(x for x in old_lane.splitlines() if ') '+name+' ' in x)
 assert line in new_lane
# Source-preserving cut only: changes outside reset, delay and leaf insertion prohibited.
r=new
r=r.removeprefix('// Source-preserving opt-in relay leaf candidate derived from c6c44c12c.\n')
r=r.replace('module ot_hdc_vstream_static_relay_entries #(','module ot_hdc_vstream_static_entries #(',1)
r=r.replace('    parameter integer RELAY_CUT = 0, // opt-in exact existing-state leaf; no added edge\n','',1)
r=r.replace('if (RELAY_CUT != 0 && LT != 0 && RTREE != 0) begin : g_relay_reset\n            // rst_l is driven by the extracted leaf below.\n        end else if (RTREE != 0) begin : g_rl','if (RTREE != 0) begin : g_rl',1)
r=r.replace('            if (RELAY_CUT == 0) begin:g_inline_in\n','',1)
r=r.replace('            end\n            wire [NW-1:0] t_i','            wire [NW-1:0] t_i',1)
r=r.replace('            if (RELAY_CUT == 0) begin:g_inline_out\n','',1)
a=r.index('            end else if(RTREE != 0) begin:g_relay_leaf')
b=r.index('            assign {va_re',a)
r=r[:a]+r[b:]
assert r==src,'Unexpected parent edits outside the explicitly replaced relay cuts'
receipt=dict(schema='opentallas.qwen-su-source-cut-audit.v1',original_commit='c6c44c12c',original_path=ORIGINAL,original_sha256=hashlib.sha256(src.encode()).hexdigest(),candidate_sha256=hashlib.sha256(new.encode()).hexdigest(),default_path_original_exact=True,offset_expressions_unchanged=True,extra_state_bits=0,extra_cycles=0,qualification='source cut and component equivalence; physical phase/RC and arithmetic remain separate gates')
print(json.dumps(receipt,indent=2))
