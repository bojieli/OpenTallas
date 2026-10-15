#!/usr/bin/env bash
# Run the unchanged real SW-slice ARGMAX numerical/calendar gate through the
# no-SID-pin master; also reject a wrong compiled-in SID through real hardware.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?output directory required}"); mkdir -p "$out"
python3 - "$out" <<'PYTHON'
from pathlib import Path
import sys,shutil
out=Path(sys.argv[1])
# The specialized boundary must preserve every original port except SID.
for rel in ['rtl/hbm_accel/index/ot_hbm_idx_client_static.sv',
            'rtl/hbm_accel/generic/ot_hbm_argmax_static.sv']:
    original=Path(rel); name=original.stem
    base=original.read_text(); wrapper=original.with_name(name+'_sw.sv').read_text()
    base=base[base.index('module '+name):base.index('\n);')+3]
    expected=base.replace('module '+name,'module '+name+'_sw',1)
    if name.endswith('client_static'):
        expected=expected.replace(' input wire[1:0]sid,input wire[15:0]weight_sector,query_sector,',
                                  ' input wire[15:0]weight_sector,query_sector,')
        instance=name+' implementation(.sid(SID), .*);'
    else:
        expected=expected.replace('    input  wire [1:0]    sid,\n','').replace('output reg','output wire')
        instance=name+' #(.MUT(MUT),.ACK(ACK),.ELAT(ELAT)) implementation(.sid(SID), .*);'
    actual=wrapper[wrapper.index('module '+name+'_sw'):wrapper.index('\n);')+3]
    assert actual==expected, 'specialization changed another boundary port: '+rel
    body=wrapper[wrapper.index('\n);')+3:wrapper.index('endmodule')]
    assert ' '.join(body.split()) == "localparam [1:0] SID = 2'd0; "+instance, 'specialization must only bind constant SID: '+rel
print('SW_SPECIALIZATION_PORT_IDENTITY PASS (two actual masters, only SID port removed)')
bench=Path('rtl/test/hbm_idx_static/tb_argmax_static.sv').read_text()
assert bench.count(".sid(2'd0), ") == 1
bench=bench.replace('ot_hbm_argmax_static #','ot_hbm_argmax_static_sw #').replace(".sid(2'd0), ", '')
# Current production SW master has three packet clients plus ring replay.
# Historical benchmark used seven; adapt widths/packed client indices exactly.
for old,new in [('[2365:0] cq_all','[1013:0] cq_all'),('[1917:0] cr_all','[821:0] cr_all'),
                ('[15:0] client_seq','[7:0] client_seq'),('[7:0] response_enable','[3:0] response_enable'),
                ('[15:0] response_seq','[7:0] response_seq'),('[23:0] bank_client','[15:0] bank_client'),
                ('bank_client[b*3 +: 3] = 3\'d0','bank_client[b*2 +: 2] = 2\'d0'),
                ('.hub_ring_client(6\'d0)','.hub_ring_client(4\'d0)')]:
    assert old in bench,old
    bench=bench.replace(old,new)

(out/'tb_argmax_static_sw.sv').write_text(bench)
run=Path('rtl/test/hbm_idx_static/run_argmax_static.sh').read_text()
run=run.replace('rtl/hbm_accel/generic/ot_hbm_argmax_static.sv ', 'rtl/hbm_accel/generic/ot_hbm_argmax_static.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw.sv ')
run=run.replace('rtl/test/hbm_idx_static/tb_argmax_static.sv)',str(out/'tb_argmax_static_sw.sv')+')')
# Icarus 11 leaves dp[7]'s continuous-read net X even while the actual
# array element is known (also reproduced on the original, unwrapped top).
# Use the independent production Verilator implementation of this same bench.
vl=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
if not vl.is_file(): vl=Path(shutil.which('verilator'))
old='iverilog -g2012 -s tb_argmax_static -Ptb_argmax_static.MUT=$m -o "$out/m$m.vvp" "${src[@]}"'
assert old in run
run=run.replace(old,str(vl)+' --binary --timing -Wno-fatal -j 4 --top-module tb_argmax_static -GMUT=$m --Mdir "$out/obj$m" "${src[@]}"')
run=run.replace('vvp "$out/m$m.vvp"','"$out/obj$m/Vtb_argmax_static"')

# Keep root resolution independent of the temporary script location.
run=run.replace('root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"', 'cd '+repr(str(Path.cwd())))
(out/'gate.sh').write_text(run)
# Wrong SID is a compile-time producer/configuration mutant, not an input tie.
wrapper=Path('rtl/hbm_accel/generic/ot_hbm_argmax_static_sw.sv').read_text()
assert wrapper.count("SID = 2'd0") == 1
(out/'wrong_sid.sv').write_text(wrapper.replace("SID = 2'd0", "SID = 2'd1"))
# Run the same expected calendar with MUT=0 and the wrong-SID source. It must fail.
wrong=run.replace('for m in 0 1 2 3; do','for m in 0; do').replace('rtl/hbm_accel/generic/ot_hbm_argmax_static_sw.sv',str(out/'wrong_sid.sv'))
(out/'wrong_gate.sh').write_text(wrong)
PYTHON
bash "$out/gate.sh" "$out/positive_and_mutants" 0
set +e
bash "$out/wrong_gate.sh" "$out/wrong_sid" 0 > "$out/wrong_sid_gate.log" 2>&1
rc=$?
set -e
cat "$out/wrong_sid_gate.log"
[ "$rc" != 0 ]
grep -q 'ARGMAX_STATIC.*FAIL' "$out/wrong_sid_gate.log"
sha256sum rtl/hbm_accel/generic/ot_hbm_argmax_static{,_sw}.sv rtl/hbm_accel/index/ot_hbm_idx_client_static{,_sw}.sv > "$out/specialized_sources.sha256"
echo 'ARGMAX_STATIC_SW GATE PASS (actual SW slice, three engine mutants and wrong compiled SID rejected)'
