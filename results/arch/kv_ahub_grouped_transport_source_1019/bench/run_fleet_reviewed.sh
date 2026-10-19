#!/usr/bin/env bash
# REMOTE runner, not a launcher. Parent must review/authorize the exact source.
set -euo pipefail
[[ ${1:-} == --reviewed-source ]] || { echo 'Source review authorization argument required' >&2; exit 2; }
: "${GROUPED_SOURCE:?absolute frozen source path}"
: "${PREDECESSOR_SOURCE:?absolute frozen 4415 source path}"
: "${REVIEWED_SHA256:?reviewed grouped source SHA256}"
# Select only exact 5.050; never accept another installed version silently.
candidates=("${VERILATOR:-}" "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" "/opt/opentallas-tools/verilator-5.050/bin/verilator" "$(command -v verilator || true)")
VERILATOR=''
for candidate in "${candidates[@]}"; do
 if [[ -n $candidate && -x $candidate ]] && "$candidate" --version | grep -q 'Verilator 5.050'; then VERILATOR=$candidate;break;fi
done
[[ -n $VERILATOR ]] || { echo 'Required Verilator 5.050 unavailable' >&2;exit 2; }
IVERILOG=$(command -v iverilog)
VVP=$(command -v vvp)
case $(hostname) in ot-epyc*|oth-ubuntu-*|ot-ubuntu-*) ;; *) echo 'Fleet execution required' >&2; exit 2;; esac
cd "$(dirname "$0")"
printf '%s  %s\n' "$REVIEWED_SHA256" "$GROUPED_SOURCE" | sha256sum --check --strict
"$VERILATOR" --version > tool_version.log
grep -q 'Verilator 5.050' tool_version.log
"$IVERILOG" -V > iverilog_version.log 2>&1
"$VVP" -V > vvp_version.log 2>&1
mkdir -p logs
sha256sum "$GROUPED_SOURCE" "$PREDECESSOR_SOURCE" ./*.sv ./*.svh > frozen_inputs.sha256
build() {
 local top=$1 name=$2 source="$GROUPED_SOURCE";shift 2
 if [[ $name =~ _m([1-6])_ ]]; then source="mut_source_${BASH_REMATCH[1]}.sv"; fi
 /usr/bin/time -v -o "logs/${name}_build.time" "$VERILATOR" --binary --timing \
  --top-module "$top" --Mdir "obj_$name" -j 2 -Wno-fatal \
  --x-initial unique --x-assign unique -I. "$@" \
  "$source" "$PREDECESSOR_SOURCE" "${top}.sv" >"logs/${name}_build.log" 2>&1
}
run() {
 local name=$1 top=$2 seed=$3 expectation=$4 log="logs/${1}_seed${3}.log" rc
 set +e
 /usr/bin/time -v -o "$log.time" "obj_$name/V$top" +verilator+rand+reset+2 +verilator+seed+"$seed" >"$log" 2>&1
 rc=$?
 set -e
 printf '%s\n' "$rc" > "$log.rc"
 if [[ $expectation == pass ]]; then
  [[ $rc == 0 ]] && grep -Eq '^(GROUP_PASS|DEFAULT_PASS)' "$log" && ! grep -Eq '(GROUP_FAIL|DEFAULT_FAIL)' "$log"
 else
  [[ $rc != 0 ]] && grep -Eq 'GROUP_FAIL (raw_authority|accept_frontier|release_delta|valid_frontier|payload)' "$log" && ! grep -q GROUP_PASS "$log"
 fi
}
build tb_grouped_default default
run default tb_grouped_default 1 pass
for width in 268 68; do
 for init in 0 1 2; do
  name=w${width}_m0_i${init}
  build tb_grouped_transport "$name" -GW="$width" -GMUT=0 -GINIT_CASE="$init"
  for seed in 1 7 31; do run "$name" tb_grouped_transport "$seed" pass; done
 done
 for mut in 1 2 3 4 5 6; do
  [[ $width == 268 && $mut == 6 ]] && continue
  name=w${width}_m${mut}_i0
  build tb_grouped_transport "$name" -GW="$width" -GMUT=0 -GINIT_CASE=0
  for seed in 1 7 31; do run "$name" tb_grouped_transport "$seed" fail; done
 done
done
# Four-state simulator uses the identical functional bench and old-Q deposits.
# All raw failures remain in their own logs; never replace failed attempts.
for width in 268 68; do
 for init in 0 1 2 3; do
  name=iv_w${width}_i${init}
  /usr/bin/time -v -o "logs/${name}_build.time" "$IVERILOG" -g2012 -I. \
   -s tb_grouped_transport -Ptb_grouped_transport.W="$width" \
   -Ptb_grouped_transport.MUT=0 -Ptb_grouped_transport.INIT_CASE="$init" \
   -o "${name}.vvp" "$GROUPED_SOURCE" "$PREDECESSOR_SOURCE" tb_grouped_transport.sv \
   >"logs/${name}_build.log" 2>&1
  set +e
  /usr/bin/time -v -o "logs/${name}.time" "$VVP" "${name}.vvp" >"logs/${name}.log" 2>&1
  rc=$?
  set -e
  printf '%s\n' "$rc" >"logs/${name}.log.rc"
  [[ $rc == 0 ]] && grep -q GROUP_PASS "logs/${name}.log" && ! grep -q GROUP_FAIL "logs/${name}.log"
 done
done
/usr/bin/time -v -o logs/iv_default_build.time "$IVERILOG" -g2012 -I. \
 -s tb_grouped_default -o iv_default.vvp "$GROUPED_SOURCE" "$PREDECESSOR_SOURCE" tb_grouped_default.sv \
 >logs/iv_default_build.log 2>&1
set +e
/usr/bin/time -v -o logs/iv_default.time "$VVP" iv_default.vvp >logs/iv_default.log 2>&1
rc=$?
set -e
printf '%s\n' "$rc" >logs/iv_default.log.rc
[[ $rc == 0 ]] && grep -q DEFAULT_PASS logs/iv_default.log && ! grep -q DEFAULT_FAIL logs/iv_default.log
sha256sum --check --strict frozen_inputs.sha256 > logs/input_identity_after.log
printf '%s\n' 'GROUP_SUITE_PASS: default bypass in both simulators,18 Verilator positive/33 causal cases,8 four-state positives; functional only'
