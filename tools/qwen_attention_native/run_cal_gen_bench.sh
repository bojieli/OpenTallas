#!/bin/bash
# KVJ-B 2026-10-17: exhaustive gate of qkd_attn_cal_gen (T = 1..8192, both G3S2, two RX_CMD) against the calendar
# generators that feed the attention benches (attn_calendar.calendar_w16; compile_native_endpoint tx_first / end),
# plus mutants that must fail and a yosys stat of the generator.  Usage: run_cal_gen_bench.sh OUT_DIR
# KVJ-SMALL 10-17: STRETCH=1 configs (profile component / die) against the KV static programme compiler's calendar
# kv_static_programme.attention_calendar(T, profile, service_end) and its fixed link words (die/report.json), every T.
set -euo pipefail
R=$(git rev-parse --show-toplevel); O=$(realpath -m "$1"); mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 - "$R" "$O" <<'PY'
import sys
R, O = sys.argv[1], sys.argv[2]
sys.path.insert(0, R + '/tools/qwen_attention_native'); sys.path.insert(0, R + '/tools/qwen_kv_die')
import attn_calendar as A, compile_native_endpoint as CE
for g in (0, 1):
    for rx in (2, 4):
        with open(f'{O}/gold_g{g}_rx{rx}.hex', 'w') as f:
            for T in range(1, 8193):
                c = A.calendar_w16(T, head_g3s2=bool(g))
                if g:
                    p = CE.compile_programme(0, 0, T - 1, 0, rx)
                    assert p['calendar_hex'] == A.hexcal(c)
                    tx, en = p['compiled_tx_first'], p['compiled_end']
                else:
                    tx = rx + 2 + A.service_cycles(c) - 31; en = tx + 34
                f.write('%04x%s%04x%04x\n' % (T, A.hexcal(c), tx, en))
import json
from pathlib import Path
import kv_static_programme as C
rep = json.loads(Path(R, 'results/arch/qwen_kv_static_programme_1017/die/report.json').read_text())['attention']
se, rx, tx, en = rep['service_end'], rep['compiled_rx_cmd'], rep['compiled_tx_first'], rep['compiled_end']
assert tx == rx + 2 + se - 31 and en == tx + 34
for name in ('component', 'die'):
    pr = C.profile(name) if name == 'component' else C.profile('die', json.loads((C.ROOT / C.AGES).read_text()))
    with open(f'{O}/gold_s_{name}.hex', 'w') as f:
        for T in range(1, 8193):
            f.write('%04x%s%04x%04x\n' % (T, A.hexcal(C.attention_calendar(T, pr, se)), tx, en))
    Path(f'{O}/params_s_{name}').write_text('%d %d %d %d\n' % (rx, pr['d_qk'], pr['d_rl'], se))
PY
SRC=("$R/rtl/qwen_sys/split_20261014/qkd_attn_cal_gen.sv" "$R/rtl/test/qwen_split/tb_qkd_attn_cal_gen.sv")
# g:rx:mut[:stretch profile]; a stretch config takes RX_CMD / D_QK / D_RL / SERVICE_END from params_s_<profile>
CFG="1:2:0 1:4:0 0:2:0 0:4:0 1:2:1 1:2:2 1:2:3 1:2:0:component 1:2:0:die 1:2:4:die 1:2:5:die 1:2:1:die"
for c in $CFG; do IFS=: read g rx m sp <<< "$c"
 if [ -n "${sp:-}" ]; then read rx dq dr se < "$O/params_s_$sp"; k="${g}_${rx}_${m}_$sp"; gold="$O/gold_s_$sp.hex"
   gp="-GSTRETCH=1 -GD_QK=$dq -GD_RL=$dr -GSERVICE_END=$se"
 else k="${g}_${rx}_${m}"; gold="$O/gold_g${g}_rx${rx}.hex"; gp=""; fi
 ( "$VL" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_qkd_attn_cal_gen -GG3S2=$g -GRX_CMD=$rx -GMUT=$m $gp \
   --Mdir "$O/b_$k" "${SRC[@]}" > "$O/b_$k.build.log" 2>&1 && \
   "$O/b_$k/Vtb_qkd_attn_cal_gen" +GOLD="$gold" > "$O/run_$k.log" 2>&1 ) &
done; wait
YS=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
"$YS" -p "read_verilog -sv $R/rtl/qwen_sys/split_20261014/qkd_attn_cal_gen.sv; synth -top qkd_attn_cal_gen -flatten; stat" > "$O/yosys_stat.log" 2>&1 || true
python3 - "$O" "$R" "$CFG" <<'PY'
import hashlib, json, re, subprocess, sys
from pathlib import Path
O, R, cfg = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3].split()
runs, ok = [], True
for c in cfg:
    f = c.split(':'); g, rx, m = map(int, f[:3]); sp = f[3] if len(f) > 3 else None
    k = f'{g}_{rx}_{m}' + (f'_{sp}' if sp else '')
    t = (O / f'run_{k}.log').read_text() if (O / f'run_{k}.log').exists() else ''
    line = next((l for l in t.splitlines() if l.startswith('CALGEN PASS') or l.startswith('CALGEN FAIL')), 'NO_RESULT')
    want = m == 0
    ok &= line.startswith('CALGEN PASS') == want
    runs.append(dict(G3S2=g, RX_CMD=rx, mut=m, stretch=sp, expect='PASS' if want else 'FAIL', result=line))
st = (O / 'yosys_stat.log').read_text()
cells = re.findall(r'^\s+(\d+) cells$', st, re.M) or re.findall(r'Number of cells:\s+(\d+)', st)
src = ['rtl/qwen_sys/split_20261014/qkd_attn_cal_gen.sv', 'rtl/test/qwen_split/tb_qkd_attn_cal_gen.sv',
       'tools/qwen_attention_native/run_cal_gen_bench.sh', 'tools/qwen_attention_native/attn_calendar.py',
       'tools/qwen_kv_die/compile_native_endpoint.py', 'tools/qwen_kv_die/static_qk_calendar.py',
       'tools/qwen_kv_die/kv_static_programme.py', 'results/arch/qwen_kv_static_programme_1017/die_ages.json',
       'results/arch/qwen_kv_static_programme_1017/die/report.json']
rec = dict(schema='opentallas.kvjb.attn_cal_gen_bench.v1', verdict='PASS' if ok else 'FAIL',
           commit=subprocess.run(['git', '-C', str(R), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
           dirty=bool(subprocess.run(['git', '-C', str(R), 'status', '--porcelain', '--', *src], capture_output=True, text=True).stdout.strip()),
           sources={p: hashlib.sha256((R / p).read_bytes()).hexdigest() for p in src},
           golden='attn_calendar.calendar_w16(T, head_g3s2) + compile_native_endpoint.compile_programme(rx_cmd) for every T=1..8192; '
                  'STRETCH=1: kv_static_programme.attention_calendar(T, profile, service_end) + the fixed link words',
           generic_yosys_cells=int(cells[-1]) if cells else None, runs=runs)
(O / 'receipt.json').write_text(json.dumps(rec, indent=1) + '\n')
print(rec['verdict'], 'cells', rec['generic_yosys_cells']); [print(r) for r in runs]
sys.exit(0 if ok else 1)
PY
