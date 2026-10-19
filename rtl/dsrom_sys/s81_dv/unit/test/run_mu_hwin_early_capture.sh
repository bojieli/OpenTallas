#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "${1:?output directory required}")
# Atomic refusal happens before any receipt, object, version or log is written.
if ! mkdir "$O"; then echo "REFUSE existing output $O" >&2; exit 73; fi
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
U="$R/rtl/dsrom_sys/s81_dv/unit"
files=("$R/rtl/lib/ot_rst_relay.sv" "$R/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv"
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v"
 "$U/dsdv_mu_hslot.sv" "$U/dsdv_mu_mem.sv" "$U/dsdv_mu_mem_early_capture.sv" "$U/dsdv_mu_hwin.sv"
 "$U/test/tb_dsdv_mu_hwin_early_capture.sv" "$U/test/tb_dsdv_mu_mem_early_capture.sv")
sha256sum "${files[@]}" > "$O/sources.sha256"
verilator --version > "$O/verilator_version.txt"
grep -q 'Verilator 5.050' "$O/verilator_version.txt"
run() {
 local name=$1 top=$2 expected=$3; shift 3
 local case_dir="$O/$name"
 mkdir "$case_dir" || { echo "REFUSE existing case $case_dir" >&2; exit 73; }
 printf '%s\n' "$@" > "$case_dir/arguments.txt"
 verilator --binary --timing --x-initial unique --x-assign unique -j "${OT_THREADS:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
  +define+OT_MEM_NO_INIT --top-module "$top" "$@" "${files[@]}" \
  --Mdir "$case_dir/obj" -o tb > "$case_dir/build.log" 2>&1
 for seed in ${RUN_SEEDS:-1 19 313}; do
  local rc=0
  "$case_dir/obj/tb" +verilator+rand+reset+2 +verilator+seed+$seed +reset_phase=${SIM_RESET_PHASE:-0} +rx_shift=${SIM_RX_SHIFT:--1} > "$case_dir/run_seed$seed.log" 2>&1 || rc=$?
  if [[ "$expected" == FAIL:* ]]; then
    [[ $rc -ne 0 ]]; grep -q "${expected#FAIL:}" "$case_dir/run_seed$seed.log"
  elif [[ "$expected" == REJECT:* ]]; then
    [[ $rc -eq 0 ]]; grep -q '^ERR' "$case_dir/run_seed$seed.log"; grep -q "${expected#REJECT:}" "$case_dir/run_seed$seed.log"
  else
    [[ $rc -eq 0 ]]; grep -q "$expected" "$case_dir/run_seed$seed.log"
  fi
 done
}
case "${2:-initial}" in
initial)
RUN_SEEDS=1 run original_assert_repro tb_dsdv_mu_hwin_early_capture 'FAIL:event boot count differs event0' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+ANCHOR_ONLY_REPRO +define+ORIGINAL_ASSERT_REPRO +define+DSDV_MU_POINTER_ASSERT
RUN_SEEDS=1 run guarded_assert_corruption tb_dsdv_mu_hwin_early_capture 'FAIL:event boot count differs event0' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+ANCHOR_ONLY_REPRO +define+ASSERT_CORRUPT
run ns2_ev1 tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D
run ns47 tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=47 +define+MIN_D
printf '%s\n' 'EARLY_CAPTURE_INITIAL PASS'
 ;;
wrapper)
 for width in 2 32; do run width$width tb_dsdv_mu_mem_early_capture 'EC_MEM PASS' +define+EC_WIDTH=$width; done
 for mut in 1 2 3 4; do RUN_SEEDS=1 run mechanism_mut$mut tb_dsdv_mu_mem_early_capture 'FAIL:EC_MEM IDENTITY' +define+EC_MUT=$mut; done
 ;;
matrix)
 run base tb_dsdv_mu_hwin_early_capture '^MUWIN PASS'
 run fast_cfg tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+FAST_CFG +define+MIN_D
 run min_d tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+MIN_D
 run badd tb_dsdv_mu_hwin_early_capture '^MUWIN BADD PASS' +define+BAD_D
 run badd_high tb_dsdv_mu_hwin_early_capture '^MUWIN BADD_HIGH PASS' +define+BAD_D_HIGH
 run collision tb_dsdv_mu_hwin_early_capture '^MUWIN COLLISION PASS' +define+COLLIDE_EVENTS
 run badrt tb_dsdv_mu_hwin_early_capture '^MUWIN BADRT PASS' +define+BADRT=1
 run headcompare tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+HEAD_COMPARE
 for mut in 3 4; do RUN_SEEDS=1 run old_mut$mut tb_dsdv_mu_hwin_early_capture 'REJECT:^MUWIN FAIL' +define+WMUT=$mut; done
 run ns2_collision tb_dsdv_mu_hwin_early_capture '^MUWIN COLLISION PASS' +define+NSLOT_TEST=2 +define+NEV=2 +define+MIN_D +define+COLLIDE_EVENTS
 run ns2_illegal_original tb_dsdv_mu_hwin_early_capture '^MUWIN FAIL' +define+NSLOT_TEST=2 +define+MIN_D
 run s256_ns2 tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=2 +define+MIN_D +define+SWEEP256
 run s256_ns47 tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=47 +define+MIN_D +define+SWEEP256
 ;;
stress)
 run reset_ns2 tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+OCCUPIED_RESET_STRESS
 for phase in 1 2 3 4 5 6 7 8 90 93; do
  for seed in 1 19 313; do
   log="$O/reset_ns2/run_seed${seed}_phase${phase}.log"
   "$O/reset_ns2/obj/tb" +verilator+rand+reset+2 +verilator+seed+$seed +reset_phase=$phase > "$log" 2>&1
   grep -q '^MUWIN PASS' "$log"
  done
 done
 run reset_ns47 tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=47 +define+MIN_D +define+OCCUPIED_RESET_STRESS
 ;;
four_state)
 mkdir "$O/four_state"
 iverilog -V > "$O/four_state/iverilog_version.txt" 2>&1
 python3 - "$U" "$O/four_state" <<'PYPROJECT'
import difflib, hashlib, json, pathlib, sys
u=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); records=[]
for name in ('dsdv_mu_mem.sv','dsdv_mu_mem_early_capture.sv'):
    src=(u/name).read_text(); projected=src
    for net,value,tail in [('padded','wdata','raw'),('forwarded','fd','picked')]:
        old=" wire [N*16-1:0] "+net+"={{(N*16-W){1'b0}},"+value+"}, "+tail+";"
        new=" wire [N*16-1:0] "+net+", "+tail+";\n assign "+net+"={{(N*16-W){1'b0}},"+value+"};"
        if projected.count(old)!=1: raise SystemExit('REFUSE declaration match count '+name+' '+net)
        projected=projected.replace(old,new)
        if projected.count(new)!=1: raise SystemExit('REFUSE projected count')
    (out/name).write_text(projected)
    (out/(name+'.diff')).write_text(''.join(difflib.unified_diff(src.splitlines(True),projected.splitlines(True),fromfile=name,tofile='parser/'+name)))
    records.append({'source':str(u/name),'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'projected_sha256':hashlib.sha256(projected.encode()).hexdigest(),'change':'exact declaration split to same-width nets and identical continuous assignment; no other edits'})
name='dsdv_mu_hwin.sv';src=(u/name).read_text()
decl='    wire [6:0] global_count;\n'
anchor='    localparam integer PTR_CTL=(NSLOT+7)/8;\n'
if src.count(decl)!=1 or src.count(anchor)!=1: raise SystemExit('REFUSE HWIN declaration reorder matchcount')
projected=src.replace(decl,'').replace(anchor,anchor+decl)
(out/name).write_text(projected)
(out/(name+'.diff')).write_text(''.join(difflib.unified_diff(src.splitlines(True),projected.splitlines(True),fromfile=name,tofile='parser/'+name)))
records.append({'source':str(u/name),'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'projected_sha256':hashlib.sha256(projected.encode()).hexdigest(),'change':'single global_count wire declaration moved before generate use; no expression or statement changed'})
(out/'parser_projection.json').write_text(json.dumps(records,indent=2)+'\n')
PYPROJECT
 projected_files=()
 for file in "${files[@]}"; do
  case "$file" in
   "$U/dsdv_mu_mem.sv"|"$U/dsdv_mu_mem_early_capture.sv"|"$U/dsdv_mu_hwin.sv") projected_files+=("$O/four_state/$(basename "$file")");;
   *) projected_files+=("$file");;
  esac
 done
 cat > "$O/four_state/primitive_probe.sv" <<'SVPROBE'
module primitive_probe;
 reg [135:0] a=0,d=0;reg[43:0] b=0,e=0;reg[1:0] c=0,f=0;integer i,j,n=0;
 task check(input bit want);
 begin
  #1;
  if(($isunknown(a)||$isunknown(b)||$isunknown(c)||$isunknown(d)||$isunknown(e)||$isunknown(f))!==want)
   $fatal(1,"PRIMITIVE_PROBE incorrectpervector unknown result");
  n=n+1;
 end endtask
 initial begin
  check(0);
  $display("PRIMITIVE_PROBE knownconcat%b pervector%b%b%b%b%b%b",$isunknown({a,b,c,d,e,f}),$isunknown(a),$isunknown(b),$isunknown(c),$isunknown(d),$isunknown(e),$isunknown(f));
  for(j=0;j<2;j=j+1)for(i=0;i<6;i=i+1)begin
   a=0;b=0;c=0;d=0;e=0;f=0;
   case(i)
    0:a[0]=j?1'bz:1'bx;1:b[0]=j?1'bz:1'bx;2:c[0]=j?1'bz:1'bx;
    3:d[0]=j?1'bz:1'bx;4:e[0]=j?1'bz:1'bx;5:f[0]=j?1'bz:1'bx;
   endcase
   check(1);
  end
  $display("PRIMITIVE_PROBE PASS cases%0d",n);$finish;
 end
endmodule
SVPROBE
 iverilog -g2012 -s primitive_probe -o "$O/four_state/primitive_probe.vvp" "$O/four_state/primitive_probe.sv" > "$O/four_state/primitive_probe_build.log" 2>&1
 vvp "$O/four_state/primitive_probe.vvp" > "$O/four_state/primitive_probe.log" 2>&1
 grep -q 'PRIMITIVE_PROBE PASS cases13' "$O/four_state/primitive_probe.log"
 iverilog -g2012 -s tb_dsdv_mu_hwin_early_capture -DOT_MEM_NO_INIT -DFOUR_STATE_GUARDS \
  -DNSLOT_TEST=2 -DNEV=1 -DMIN_D -DOCCUPIED_RESET_STRESS -o "$O/four_state/tb.vvp" "${projected_files[@]}" \
  > "$O/four_state/build.log" 2>&1
 python3 - "$O/four_state/tb.vvp" "$O/four_state/binding_audit.json" <<'PYBIND'
import json,pathlib,re,sys
text=pathlib.Path(sys.argv[1]).read_text()
parents=set(re.findall(r'\.net "global_count", 6 0, (\w+);',text))
checks=[]
for chunk in re.split(r'(?=S_\w+ \.scope )',text):
    if not re.match(r'S_\w+ \.scope module, "u_cr[lm]" ',chunk):continue
    m=re.search(r'\.net "count", 6 0, (\w+);',chunk)
    checks.append({'scope':chunk.splitlines()[0],'driver':m.group(1) if m else None,'bound_parent':bool(m and m.group(1) in parents)})
if len(parents)!=2 or len(checks)!=12 or not all(x['bound_parent'] for x in checks):raise SystemExit('REFUSE incorrect parent global_count binding')
pathlib.Path(sys.argv[2]).write_text(json.dumps({'parent_drivers':sorted(parents),'count_ports':checks,'verdict':'PASS'},indent=2)+'\n')
PYBIND
 if grep -q 'Port 1 (count).*got 1' "$O/four_state/build.log"; then echo 'REFUSE count widthwarning'; exit 1; fi
 # Bounded 5.050 original/projected source trace equivalence under identical input/reset/seed.
 for variant in original projected; do
  selected=("${files[@]}"); [[ "$variant" != projected ]] || selected=("${projected_files[@]}")
  verilator --binary --timing --x-initial unique --x-assign unique -j "${OT_THREADS:-8}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
   +define+OT_MEM_NO_INIT +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+OCCUPIED_RESET_STRESS \
   --top-module tb_dsdv_mu_hwin_early_capture "${selected[@]}" --Mdir "$O/four_state/obj_$variant" -o tb > "$O/four_state/build_equiv_$variant.log" 2>&1
  for seed in 1 19 313; do
   "$O/four_state/obj_$variant/tb" +verilator+rand+reset+2 +verilator+seed+$seed > "$O/four_state/equiv_${variant}_seed$seed.log" 2>&1
   grep -q '^MUWIN PASS' "$O/four_state/equiv_${variant}_seed$seed.log"
   grep -E '^(KU |MUWIN |EARLY_RESET |EARLY_MITER )' "$O/four_state/equiv_${variant}_seed$seed.log" > "$O/four_state/equiv_${variant}_seed$seed.trace"
  done
 done
 for seed in 1 19 313; do cmp "$O/four_state/equiv_original_seed$seed.trace" "$O/four_state/equiv_projected_seed$seed.trace"; done
 for phase in 0 1 2 3 4 5 6 7 8 90 93; do
  log="$O/four_state/run_phase${phase}.log"
  vvp "$O/four_state/tb.vvp" +reset_phase=$phase > "$log" 2>&1
  grep -q '^MUWIN PASS' "$log"
 done
 for mutant in PAYLOAD CONTROL; do
  iverilog -g2012 -s tb_dsdv_mu_hwin_early_capture -DOT_MEM_NO_INIT -DFOUR_STATE_GUARDS \
   -DNSLOT_TEST=2 -DNEV=1 -DMIN_D -DFOUR_STATE_INJECT_$mutant -o "$O/four_state/mutant_$mutant.vvp" "${projected_files[@]}" \
   > "$O/four_state/build_mutant_$mutant.log" 2>&1
  rc=0;vvp "$O/four_state/mutant_$mutant.vvp" > "$O/four_state/run_mutant_$mutant.log" 2>&1 || rc=$?
  [[ $rc -ne 0 ]]; grep -q "EARLY_X_CAUSAL" "$O/four_state/run_mutant_$mutant.log"
  grep -q "EARLY_X" "$O/four_state/run_mutant_$mutant.log"
 done
 ;;
sweep)
 for ns in $(seq "${SWEEP_LOW:-2}" "${SWEEP_HIGH:-47}"); do
  run uniform_ns$ns tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=$ns +define+MIN_D +define+SWEEP256
  run nonuniform_short_ns$ns tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=$ns +define+MIN_D +define+SWEEP256 +define+NONUNIFORM_GAPS +define+SHORT_RL
  for shift in 0 1; do for seed in 1 19 313; do
   log="$O/nonuniform_short_ns$ns/run_seed${seed}_rxshift${shift}.log"
   "$O/nonuniform_short_ns$ns/obj/tb" +verilator+rand+reset+2 +verilator+seed+$seed +rx_shift=$shift > "$log" 2>&1
   grep -q '^MUWIN RX_EXPIRED PASS' "$log"
  done;done
 done
 ;;
calendar_mutants)
 run long_d_positive tb_dsdv_mu_hwin_early_capture '^MUWIN PASS' +define+NSLOT_TEST=2 +define+MIN_D +define+SWEEP256 +define+LONG_D
 RUN_SEEDS=1 run wrong_wrap tb_dsdv_mu_hwin_early_capture 'FAIL:EARLY_MITER' +define+NSLOT_TEST=2 +define+MIN_D +define+SWEEP256 +define+LONG_D +define+NEXT_WRAP_MUTANT
 RUN_SEEDS=1 run timestamp_shift tb_dsdv_mu_hwin_early_capture 'FAIL:EARLY_MITER' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+TIMESTAMP_MUTANT
 RUN_SEEDS=1 run delayed_retirement tb_dsdv_mu_hwin_early_capture 'FAIL:EARLY_MITER' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+DELAY_RETIRE_MUTANT
 RUN_SEEDS=1 SIM_RESET_PHASE=5 run reset_validity tb_dsdv_mu_hwin_early_capture 'FAIL:EARLY_MITER' +define+NSLOT_TEST=2 +define+NEV=1 +define+MIN_D +define+OCCUPIED_RESET_STRESS +define+RESET_VALID_MUTANT
 ;;
*) echo 'unknown phase' >&2; exit 64;;
esac
