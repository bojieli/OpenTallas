#!/bin/bash
# seq_kvn_die_bench.sh OUT DRX DPRG LAND DKW [MUT=0] [NL=36]   (HKV-DIE2 10-19; run from the repository root, on the fleet)
# The seq KVN-arrival check (qkd_seq_core_static_s f_arr at KVN_A0 after the CMD decode) on the KV die's fixed path ages:
# tb_seq_kvn_die = tb_seq_static_s with DRX (d2d_kv -> kvs_attn rx), DPRG + LAND (kvs_attn prg -> seq) and DKW
# (d2d_kv skw -> seq, incl. the kv_bundle_eq S.seq_kvn pads) on the PRODUCTION link calendar (kv_static_programme
# LINK_ARGS + the compiled token path = the committed d2d image compile).  Ages come from the die netlist table
# (kv_static_params.py seq_kvn: S_rx / S_prg / S_kw); legal iff DKW == DRX + DPRG + LAND.
# One SEQ_KVN_DIE line; exit 0 only on PASS (the pads-removed mutant DKW = the as-built skw expects FAIL).
set -u
O=$1; DRX=$2; DPRG=$3; LAND=$4; DKW=$5; M=${6:-0}; NL=${7:-36}
mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 - "$O" > "$O/calendar.log" 2>&1 <<'EOF' || { echo "SEQ_KVN_DIE FAIL production calendar compile"; exit 1; }
import gzip, subprocess, sys
from pathlib import Path
sys.path.insert(0, 'tools/qwen_kv_die')
import kv_static_programme as C
o = Path(sys.argv[1]); tp = o / 'token_path_compiled.json'
tp.write_bytes(gzip.decompress((C.ROOT / C.LINK_TOKEN_PATH).read_bytes()))
cmd = [sys.executable, 'tools/qwen_split/d2d_link_calendar.py', '--out', str(o / 'cal')] + C.LINK_ARGS + ['--token-path', str(tp)]
print(' '.join(cmd)); sys.exit(subprocess.run(cmd).returncode)
EOF
P=$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(next(l['cycles'] for l in d['program']['layers'] if l['id']=='L1'))" "$O/cal/calendar.json")
rm -rf "$O/lp"; python3 tools/qwen_static_kv/layer_roots_from_link.py "$O/cal" "$O/lp" > "$O/roots.log" 2>&1 || { echo "SEQ_KVN_DIE FAIL roots"; exit 1; }
mkdir -p "$O/g"; python3 tools/qwen_static_kv/seq_static_golden.py "$O/cal" "$O/lp/layer_roots.json" "$O/g/seq_gold.svh" > "$O/gold.log" || { echo "SEQ_KVN_DIE FAIL golden"; exit 1; }
S=rtl/qwen_sys/split_20261014
T=obj_m${M}_${DRX}_${DPRG}_${LAND}_${DKW}
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 4 \
  -I"$O/g" --top-module tb_seq_kvn_die -GMUT=$M -GNL=$NL -GP=$P -GDRX=$DRX -GDPRG=$DPRG -GLAND=$LAND -GDKW=$DKW --Mdir "$O/$T" \
  rtl/lib/ot_rst_relay.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv \
  rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv \
  rtl/physical/ot_qwen_kv_centre_slots.sv rtl/physical/ot_qwen_kv_seq_tp8.sv \
  $S/qkd_native59_descriptor_producer.sv $S/qkd_native59_command_guard.sv $S/qkd_native_attention_record.sv \
  $S/qkd_native_attention_static_ctl.sv $S/qkd_native_attention_programme.sv \
  rtl/qwen_sys/static_kv_20261014/qkd_seq_static_prg.sv rtl/qwen_sys/static_kv_20261014/qkd_seq_static_s.sv \
  rtl/test/qwen_static_kv/tb_seq_kvn_die.sv > "$O/build_$T.log" 2>&1 \
  || { echo "SEQ_KVN_DIE FAIL build"; grep -m6 '%Error' "$O/build_$T.log"; exit 1; }
"$O/$T/Vtb_seq_kvn_die" > "$O/run_$T.log" 2>&1
grep -E '^ERR' "$O/run_$T.log" | head -6
echo "$($VL --version | head -1) P=$P $(cat "$O/gold.log" | tail -1)"
line=$(grep -E '^SEQ_KVN_DIE ' "$O/run_$T.log" | tail -1)
echo "${line:-SEQ_KVN_DIE FAIL no verdict line}"
case "$line" in "SEQ_KVN_DIE PASS"*) exit 0;; *) exit 1;; esac
