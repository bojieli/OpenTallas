#!/bin/bash
set -eu
out=$1; width=$2; mutant=${3:-0}
case "$width" in 26|27) ;; *) exit 2;; esac
case "$mutant" in 0|1) ;; *) exit 2;; esac
mkdir -p "$out"
python3 - "$out/dut.sv" "$mutant" <<'PYS'
import pathlib,sys,json,hashlib
p=pathlib.Path('rtl/qwen_sys/vm_native_physical_20261015/qvm_write_control_native.sv');s=p.read_text();original=s
if int(sys.argv[2]):
 assert s.count('.we(we)')==2;s=s.replace('.we(we)','.we(~we)')
pathlib.Path(sys.argv[1]).write_text(s)
pathlib.Path(sys.argv[1]+'.provenance.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(original.encode()).hexdigest(),compiled_sha256=hashlib.sha256(s.encode()).hexdigest(),actual_hardware_mutation='invert WE at real helper input'if int(sys.argv[2])else'none'),indent=2)+'\n')
PYS
iverilog -g2012 -s tb -Ptb.W="$width" -DDUT=qvm_write_control_w"$width"_native -o "$out/sim.vvp" rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv "$out/dut.sv" rtl/test/qwen_vm_residual/tb_write_control.sv > "$out/build.log" 2>&1
sha256sum "$out/sim.vvp" "$out/dut.sv" rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/test/qwen_vm_residual/tb_write_control.sv > "$out/hashes.sha256"
set +e
vvp "$out/sim.vvp" > "$out/run.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/exit"
cat "$out/run.log"
exit "$rc"
