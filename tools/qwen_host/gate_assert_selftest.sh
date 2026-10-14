#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.."&&pwd)
TMP=$(mktemp -d);trap 'rm -rf "$TMP"' EXIT
mkdir "$TMP/bin"
cat > "$TMP/bin/iverilog" <<'STUB'
#!/usr/bin/env bash
while [[ $# -gt 0 ]];do if [[ $1 == -o ]];then touch "$2";break;fi;shift;done
exit 0
STUB
cat > "$TMP/bin/vvp" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' 'PASS full host' 'PASS full actual HOST'
exit 0
STUB
chmod +x "$TMP/bin/iverilog" "$TMP/bin/vvp"
for GATE in fullcontrol_gate fullcontrol_packet_gate prompt_pin_gate prompt_ue_gate;do
 set +e
 PATH="$TMP/bin:$PATH" bash "$R/tools/qwen_host/$GATE.sh" "$TMP/$GATE" "$R" > "$TMP/$GATE.log" 2>&1
 RC=$?
 set -e
 if [[ $RC == 0 ]];then cat "$TMP/$GATE.log";printf '%s\n' "FAIL $GATE accepted unexpectedly passing mutant";exit 1;fi
 # Stub output deliberately contains no failure evidence. Require reaching the
 # mutant check; a premature unrelated error would not prove the assertion.
 [[ -f "$TMP/$GATE/run-1.log" || -f "$TMP/$GATE/tb_qkd_host_prompt_pins-run-1.log" ]]
done
printf '%s\n' 'PASS all four host gates reject unexpected mutant PASS'
