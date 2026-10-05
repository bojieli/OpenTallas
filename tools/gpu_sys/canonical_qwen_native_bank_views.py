"""Add readonly persistent scope/Q views and typed RF-workspace query to new leaf.

Original qualified banked module and all fixtures remain byte-identical.
"""
from pathlib import Path
from tools.gpu_sys.canonical_qwen_banked_manifest_owner import generate as banked_generate
import tempfile

def generate(out):
 with tempfile.TemporaryDirectory() as d:s=banked_generate(d).read_text()
 def rep(a,b):
  nonlocal s
  if a not in s:raise ValueError('source anchor missing '+a[:80])
  s=s.replace(a,b)
 rep('ot_gpu_qwen_banked_manifest_range_owner','ot_gpu_qwen_native_aperture_range_owner')
 # Reuse existing helper, do not redeclare a second copy of the same module.
 s=s[:s.index('// All mutable words are sealed full72')]
 rep('QB=303','QB=304')
 rep('input wire query_valid,query_write,input wire [238:0] query_tuple,',
     'input wire query_valid,query_write,query_workspace,input wire native_rf_workspace_free,input wire [238:0] query_tuple,')
 rep('output wire fault,','output wire [10:0] query_result_version,output wire query_result_write,query_result_workspace,\n output wire [8:0] query_result_first,output wire [9:0] query_result_end,\n output wire lease_scope_valid,lease_scope_writable,lease_scope_workspace,\n output wire [238:0] lease_scope_tuple,output wire [54:0] lease_scope_owner,\n output wire fault,')
 at=s.index(' // All matches are computed')
 s=s[:at]+''' localparam integer Q_WORKSPACE=303;
 // A held B prevents claims and source-retirement. Normal source row identity,
 // bounds and owner captured by Q remain immutable throughout this B scope.
 assign lease_scope_valid=active&&b[B_LIVE]&&b[B_GO]&&!b[B_TERMINAL]&&!b[B_REVERSE]&&issuer_match;
 assign lease_scope_writable=lease_scope_valid&&((published_rows&manifest_rows)==0);
 assign lease_scope_workspace=lease_scope_valid&&workspace_held_valid&&native_rf_workspace_free;
 assign lease_scope_tuple=b[B_TUPLE +:239];assign lease_scope_owner=issuer_held_owner55;
 wire saved_workspace=q[Q_WORKSPACE];
 assign query_result_workspace=saved_workspace;assign query_result_write=q[Q_ROLE];
 assign query_result_version=saved_workspace?11'd2047:(qr<7?r[qr][R_SOURCE_VERSION +:11]:11'b0);
 assign query_result_first=saved_workspace?9'd0:(qr<7?r[qr][R_PRODUCER_TUPLE+10 +:9]:9'b0);
 assign query_result_end=saved_workspace?10'd10:(qr<7?r[qr][R_PRODUCER_TUPLE +:10]:10'b0);
''' +s[at:]
 rep('if(query_row>=0)begin','if(!query_workspace&&query_row>=0)begin')
 rep(' wire terminal_match=', ''' wire workspace_query_legal=lease_scope_workspace&&query_tuple==b[B_TUPLE +:239]&&query_slot<10&&query_version==2047;
 wire terminal_match=''')
 rep('assign query_ready=active&&!q[Q_LIVE]&&query_legal;',
     'assign query_ready=active&&!q[Q_LIVE]&&(query_workspace?workspace_query_legal:query_legal);')
 rep('assign source_owner_retained=all_clean&&q[Q_LIVE]&&qr<7&&r[qr][R_LIVE]&&',
     'assign source_owner_retained=all_clean&&q[Q_LIVE]&&(saved_workspace?\n (lease_scope_workspace&&q[Q_TUPLE +:239]==b[B_TUPLE +:239]&&q[Q_OWNER46 +:46]==issuer_held_owner55[54:9]):\n (qr<7&&r[qr][R_LIVE]&&')
 rep('q[Q_TUPLE +:239]==r[qr][R_CONSUMER_TUPLE +:239]));',
     'q[Q_TUPLE +:239]==r[qr][R_CONSUMER_TUPLE +:239]))));')
 rep('qn[Q_ROW +:3]=query_row;qn[Q_SLOT +:9]=query_slot;',
     'qn[Q_WORKSPACE]=query_workspace;qn[Q_ROW +:3]=query_workspace?3\'d7:query_row;qn[Q_SLOT +:9]=query_slot;')
 rep('qn[Q_OWNER46 +:46]=r[query_row][R_OWNER55+9 +:46];',
     'qn[Q_OWNER46 +:46]=query_workspace?issuer_held_owner55[54:9]:r[query_row][R_OWNER55+9 +:46];')
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 f=out/'ot_gpu_qwen_native_aperture_range_owner.sv';f.write_text(s.rstrip()+'\n');return f

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);print(generate(a.parse_args().out))
