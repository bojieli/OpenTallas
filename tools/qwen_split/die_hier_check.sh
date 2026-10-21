#!/bin/bash
# Source/file completeness parse of a Qwen compute-die GEN (LEAD-QW2 10-21, owner: required before EVERY GEN launch):
# yosys `hierarchy -check` over the die top and the full RTL file closure of every die master, resolved from the GEN's
# own source tree exactly as the strict bind resolves it (tools/die_port_bind.py --elab-out, same files / straps /
# hard-macro models as tools/qwen_split/port_bind_compute.sh).  Parse + hierarchy only, no synthesis.
# usage: die_hier_check.sh GEN_DIR [DIE_V]    (run from anywhere; GEN_DIR holds src/ and out/case/die.v)
#   exit 0 = HIER_CHECK PASS (every referenced module defined); writes GEN_DIR/hier_check/{die_top.f,hier.ys,yosys.log,verdict.txt}
set -u
S=$(readlink -f "${1:?GEN dir}"); D=$(readlink -f "${2:-$S/out/case/die.v}"); R=$S/src; O=$S/hier_check
[ -e "$D" ] || { echo "HIER_CHECK FAIL no die.v ($D)"; exit 2; }
mkdir -p $O
cd $R || exit 2
python3 tools/qwen_split/gen_relay_rtl.py $D $O/die_glue.sv > $O/die_glue.json || { echo "HIER_CHECK FAIL glue"; exit 3; }
T45=; grep -q 'ck_fa0' $D && T45="--rtl-file $R/rtl/physical/qfd_tile_rp2_45_slots.sv --rtl-file $R/rtl/physical/qfd_tile_nk_rp2_45.sv --rtl-file $R/rtl/physical/qfd_tile_nl_rp2_45.sv"
UV=${OT_PORT_BIND_UCIE_VIEW:-physical/qwen_missing_phy/nface_tall_1017/ot_qfd_ucie_x64_phy}
ST=${OT_PORT_BIND_STRAPS:-$R/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f18mu.json}
python3 tools/die_port_bind.py $D $T45 --rtl-file $O/die_glue.sv --rtl-file $R/rtl/qwen_split/qfd_link_slots.sv \
  --rtl-file $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv \
  --rtl-file $R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
  --rtl-file $R/$UV/ot_qfd_ucie_x64_phy_bb.v \
  --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy_s597/ot_qfd_serdes_112g_x12_phy_s597_bb.v \
  --allow-model qfd_ckbump --allow-model qfd_sigbump --allow-model ot_qkvd_ucie_x64_phy --allow-model ot_qkvd_ucie_x64_phy_model \
  --allow-model ot_qfd_ucie_x64_phy --allow-model ot_qfd_serdes_112g_x12_phy_s597 \
  --lib-root $R/physical/asap7_memory_macros --define OT_QFD_UP4_CK_ENTRIES --ref-tile-prefer --strap-file $ST \
  --elab-out $O --out $O/port_bind_elab.json > $O/port_bind_elab.txt 2>&1
python3 - $O <<'PY' || exit 4
import json, sys, glob, os
o = sys.argv[1]
fl = [l.strip() for l in open(o + '/die_top.f') if l.strip()]
inc = [l[8:] for l in fl if l.startswith('+incdir+')]
dfn = [l[8:] for l in fl if l.startswith('+define+')]
src = [l for l in fl if not l.startswith('+')]
el = json.load(open(o + '/port_bind_elab.json')).get('elab', {})
# memory macros: behavioural/blackbox Verilog of the asap7 macro set when the closure names them; liberty as -lib cells
libs = sorted(set(glob.glob(os.getcwd() + '/physical/asap7_memory_macros/**/*.lib', recursive=True)))
with open(o + '/hier.ys', 'w') as f:
    flags = ' '.join([f'-I{d}' for d in inc] + [f'-D{d}' for d in dfn])
    for p in libs:
        f.write(f'read_liberty -lib -ignore_miss_func {p}\n')
    for p in src:
        f.write(f'read_verilog -sv -defer {flags} {p}\n')
    f.write('hierarchy -check -top qfd_die\n')
json.dump(dict(files=len(src), libs=len(libs), elab_unresolved=el.get('unresolved_modules', [])), open(o + '/closure.json', 'w'))
print('HIER_FILES', len(src), 'libs', len(libs), 'elab_unresolved', len(el.get('unresolved_modules', [])))
PY
yosys -q -l $O/yosys.log -s $O/hier.ys > /dev/null 2>&1; rc=$?
miss=$(grep -cE "is not part of the design|referenced in module .* is not" $O/yosys.log)
err=$(grep -m1 -E "^ERROR" $O/yosys.log | cut -c1-300)
if [ $rc -eq 0 ]; then v="HIER_CHECK PASS files=$(python3 -c "import json;print(json.load(open('$O/closure.json'))['files'])") missing=0"
else v="HIER_CHECK FAIL rc=$rc missing_refs=$miss first: $err"; fi
echo "$v" | tee $O/verdict.txt
[ $rc -eq 0 ]
