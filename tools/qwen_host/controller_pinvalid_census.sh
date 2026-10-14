#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output};mkdir -p "$out";out=$(cd "$out"&&pwd)
h=rtl/qwen_sys/host_20261013;k=rtl/qwen_sys/kv_die_20261009;e=rtl/qwen_sys/emb_hbm_20261008
s="$h/qkd_ctrl_pc_host_pinvalid_candidate.sv $h/ot_qfd_kv_landing_ecc_pinvalid_candidate.sv $h/qkd_host_static_pc.sv $k/ot_qkvd_kcmd_tap.sv $e/ot_qwen_ctrl_pc_emb.sv $e/ot_hbm_r14_stream_pc_srow.sv $e/synth/ot_qfd_emb_pcport.sv $e/ot_qfd_emb_cdc.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv"
yosys -Q -T -p "read_verilog -defer -sv $s; hierarchy -check -top qkd_ctrl_pc_host_pinvalid_candidate -chparam PINVALID 1; proc; opt; memory_map; opt; flatten; opt; write_json $out/net.json; stat" > "$out/synthesis.log"
python3 - "$out" <<'PY'
import pathlib,json,sys,hashlib
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'net.json').read_text())['modules']['qkd_ctrl_pc_host_pinvalid_candidate']
clocks={n:tuple(m['ports'][n]['bits'])for n in ['pll_hbm','ck']};ff={n:0 for n in clocks};qdrivers={}
for n,c in m['cells'].items():
 if 'dff' in c['type'].lower():
  root=next((k for k,b in clocks.items()if tuple(c['connections']['CLK'])==b),None)
  if root is None:raise SystemExit('unclassified FF clock '+n)
  ff[root]+=len(c['connections']['Q'])
  for b in c['connections']['Q']:qdrivers[b]=(n,root)
co0=m['ports']['co']['bits'][0];assert co0 in qdrivers and qdrivers[co0][1]=='pll_hbm','co0 not direct real HBM FF'
j={'master':'qkd_ctrl_pc_host_pinvalid_candidate','PINVALID':1,'default':0,'flop_bits':sum(ff.values()),'clock_flop_bits':ff,'co0_direct_FF':qdrivers[co0],'input_bits':sum(len(v['bits'])for v in m['ports'].values()if v['direction']=='input'),'output_bits':sum(len(v['bits'])for v in m['ports'].values()if v['direction']=='output'),'parameters_preserved':{'CVL':2,'HOFF':3,'WDONE':17},'source_sha256':{n:hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest()for n in ['rtl/qwen_sys/host_20261013/qkd_ctrl_pc_host_pinvalid_candidate.sv','rtl/qwen_sys/host_20261013/ot_qfd_kv_landing_ecc_pinvalid_candidate.sv']},'physical_status':'UNQUALIFIED_OUTLINE_PINS_INSERTION_UNASSIGNED','actual_KV_CDC_composition':'PENDING; standalone exact whole controller and primitive equivalence separate'}
(p/'census.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
PY
rm "$out/net.json"
