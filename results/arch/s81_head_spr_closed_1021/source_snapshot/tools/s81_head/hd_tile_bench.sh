#!/usr/bin/env bash
# S81-HEAD HD-TILE (10-21): ot_s81hd_tile / spo / spr mini-array bench (cwd = repo root, Verilator 5.050).
#   hd_tile_bench.sh OUTDIR SCEN [MUT]
#   SCEN A    t0 = rows 21888.. (ten 1), t1 = rows 22016.. (ten 1), 2 positions: golden argmax 21946 / 4173a558, cycles
#        B    t0 = rows 22016.. (ten 1), t1 = rows 21888.. (ten 0): 22141 / 40cdce35 (the golden bundle is excluded)
#        C    t0 = rows 21888.. row0 21888, t1 = the same image with strap row0 21760: equal logits, lowest id 21818 wins
#        D    as A with one x slice lane at BF16 +Inf: the bundle faults, flt = 1 must reach the spr output (no logit check)
#        ALL  A B C D on one build
#   MUT  none | TIE_FLIP | GO_DROP | TEN_IGNORED | FLT_DROP (ot_s81hd_tile) | SPO_OW_DROP (spo) | SPR_EARLY (spr)
#        (+define+OT_S81HD_MUT_<MUT>)
# Images: results/rtl/s81_head_tile_1021/img (tools/s81_head/hd_tile_images.py --sk 7, released head.weight + golden x of
# the 1M token, golden logits <P>lg.hex).  Every logit a running bundle forms is checked bit-exact against the golden.  Last line BENCH_PASS / BENCH_FAIL; exit 0 only on BENCH_PASS.
set -u
# CLOSED SPR bb8dd356c replay uses the exact RTL, ROM images, and native models below.
# Current main may evolve them. An explicit frozen checkout can supply the
# source root; never silently replay a different arithmetic source as bb8.
S81HD_RUN_OUT=$(realpath -m "${1:?outdir}")
if [ -n "${S81HD_SELECTED_SOURCE_ROOT:-}" ]; then
  cd "$S81HD_SELECTED_SOURCE_ROOT" || exit 3
fi
python3 - <<'S81HD_SOURCE_GUARD'
import hashlib
from pathlib import Path
expected = {'rtl/hdc/ot_hdc_prefix.sv': '98f2492a22012ffbaae49ac8405c2af693e16cb7bcdfafc5eb66db7943240587', 'rtl/hdc/ot_hdc_fastfp.sv': 'ff9d928d809eef91c349e4be8b34e359548a24dab473be05fcab8b9f43db2643', 'rtl/hdc/ot_hdc_fp32_add_lat.sv': 'f5e88cfcd8ce4809826eccf77fa8b83bc1ef14b430964dcf01cef70f70577b30', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv': 'ddc4c3bfb4f22788534148049bf381d469053ff5b54c6197548636a3f4aac8e3', 'rtl/hdc/ot_hdc_fp32_mul_lat_ncr.sv': '8af05d9c0a96ca9685a2167f556b8baeb064a53ce6c5e07e5032430e45e20d63', 'rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv': '07273570b2df52df1cb942f2a81dfe607161f4e73de5001cc71ed1ca7fbc1fbd', 'rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v': '5bd2448e4914cefa7b1d8dd8ffa294dd3c3e69e24910658d994a564b7593e5a7', 'rtl/common/ot_prefix.sv': '01de55a0d8c474008eb4446e41e00788d466b5dfb2e2e8d85a0b70ff931f8cfc', 'rtl/v41rom/ot_v41_fadd.sv': '9062c07e99f3baedf2b4e6399d5e12e2501be1db2d99bf71a73c2437bf3a5b91', 'rtl/v41rom/ot_v41_bmul2.sv': '15015cbd92c76526298c6647561f530499ee678e7bbe656bcc689fa40bb7c1e6', 'rtl/v41rom/ot_dsrom_bmul3.sv': '753636fd6fdc34a2229b492c46b71d130ed41d95cf97665cac5d1df6daa27498', 'rtl/hdc/ot_hdc_delay.sv': '7b37c18daacc0e2c592dc3acf1e65e2225a69697a39de9c1e4d2fc22421cb688', 'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v': '57823a0353236533a2b15a669025480c61930874cde8af6e77f7fca372f6fada', 'rtl/dsrom_sys/s81_head/ot_s81hd_key.sv': 'aeafa93ba3d90605bf8f0bab670baf11da763dfbf2911e3f1ea00cf93a5aad92', 'rtl/dsrom_sys/s81_head/ot_s81hd_fadd.sv': '1576738e776fef98c28bf8d39c1bf933a00b9a7adf75d7466cd75d6c428c97db', 'rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv': 'f2ac91efe9862aae9edae274b3cbd2a68589dfb52c1727140c7cb7c7259c7b49', 'rtl/dsrom_sys/s81_head/ot_s81hd_bundle.sv': 'd61bad344fcd38e3ddbfa2fe93e019fae52d7517d0d0126b196d8e2b13740bb5', 'rtl/dsrom_sys/s81_head/ot_s81hd_tile.sv': 'd9ba09832577a44d31c0df3cc88d88b2473c3d4155fbc16fb97b25dc93d74cdb', 'rtl/dsrom_sys/s81_head/ot_s81hd_spo.sv': 'fb71f1a497b0ebbcf879ceeeeec54db73fba60c129ed99ee4604a8e0b2eaae3e', 'rtl/dsrom_sys/s81_head/ot_s81hd_spr.sv': '3836fd6ddb71024b9486575f273e6db9baf8b87baa3eb6f44104d2e15b14a809', 'rtl/dsrom_sys/s81_head/test/tb_s81hd_mini.sv': '85ab78bd56cbca869bf3c6ddbcb43fb4889d949a852526a1315a8ba8ff0f54bd', 'results/rtl/s81_head_tile_1021/img/ga0_0.viamap.hex': '8d387d795aff82067102e3c4bcec761c7e372e943e91eef90fb81882b20b815d', 'results/rtl/s81_head_tile_1021/img/ga0_1.viamap.hex': '2a77febb2cc4a0cf4bc5fae6cdb9ec1a3788665f84df3944a4c1a52bfef1f2b7', 'results/rtl/s81_head_tile_1021/img/ga1_0.viamap.hex': 'e0c1346c01c44f8dfa5dc083416ad385ae70595bb5a4f1a04779de5c4a6e4c96', 'results/rtl/s81_head_tile_1021/img/ga1_1.viamap.hex': '0ece84bbd3d2050caa67244bce8f994c65250b4a4750416950e2e4ffa846e34f', 'results/rtl/s81_head_tile_1021/img/ga2_0.viamap.hex': 'cd7dce07319bb93104a204264f960062dab44d0673c6c9d2dc4727148882f39d', 'results/rtl/s81_head_tile_1021/img/ga2_1.viamap.hex': '7dd408ce02122354d405c12e78562ca0ccffb497547b51c45c6cba9e7364596b', 'results/rtl/s81_head_tile_1021/img/ga3_0.viamap.hex': '2716c6bf58cd2137c0416b3e9404a8778622a77d3e8db535506bd347da303e3e', 'results/rtl/s81_head_tile_1021/img/ga3_1.viamap.hex': '0fd5262a4be3373d38da794822d0f45d6231365d19bdf6838ae8dea5947c3431', 'results/rtl/s81_head_tile_1021/img/gb_0.viamap.hex': 'c0ad6b9ad63af5d118ad6eb3d011150197cbeea6fe78152b93b2e2cb1e360334', 'results/rtl/s81_head_tile_1021/img/gb_1.viamap.hex': '2d14cbe7cd0c62b38f1b7002adbcf9d1d4a94fd032451c9b1f94747fc6bb2824', 'results/rtl/s81_head_tile_1021/img/glg.hex': '28c7743057c0417a3c91d0187b8d434915a241be81022275a0a4dd66f2283a44', 'results/rtl/s81_head_tile_1021/img/golden.json': '85dbab58048fa0539f83a01ddfc9fcc640fa0d2a0b8f59989d091362146e5483', 'results/rtl/s81_head_tile_1021/img/ha0_0.viamap.hex': '6865de25e9150fd4acea09754b0b7df0ad3ceeff523791aabe438163836854ae', 'results/rtl/s81_head_tile_1021/img/ha0_1.viamap.hex': 'e21296c1e20afaaf4369171b9954462ac499dc0a61977ba813a1f052e1873045', 'results/rtl/s81_head_tile_1021/img/ha1_0.viamap.hex': 'b3c23690fac71ab545ffe75ef5ec18c6dcfd425449a707c02676937c60a993ab', 'results/rtl/s81_head_tile_1021/img/ha1_1.viamap.hex': '6616c58cab3d13e225c7993afd0fd142d0db185ec0c199880798cab88c7db463', 'results/rtl/s81_head_tile_1021/img/ha2_0.viamap.hex': '539b74fab3ba2d9aa7e36b8662faaa42371a5bbef62b553d50a74507f82846e0', 'results/rtl/s81_head_tile_1021/img/ha2_1.viamap.hex': '9ca148f8fc2dd617f80bd29aea1ac470fc0b3c4411e493bcfd2613127d587d15', 'results/rtl/s81_head_tile_1021/img/ha3_0.viamap.hex': '05f471de86ab7b050d326d914360c20f30698335754df046be3a893999b8c975', 'results/rtl/s81_head_tile_1021/img/ha3_1.viamap.hex': '3f41abce5d05f07afacdb7cf56ec791a9689f8cfd8a6f1bc85fc67aee4c38115', 'results/rtl/s81_head_tile_1021/img/hb_0.viamap.hex': '5b3e732fa3dce4a02c6d08190de345ccfaf2f8780c1d694ee0d5709e12972b6f', 'results/rtl/s81_head_tile_1021/img/hb_1.viamap.hex': 'c80653e2470d470336c4f7a97a379d23aaaa8a2783b22d115e5258415f882ed2', 'results/rtl/s81_head_tile_1021/img/hlg.hex': '3556ceb7c3280d928179ba09c7f3db7375d06f060e89a80cd157496d4fbf376f', 'results/rtl/s81_head_tile_1021/img/xa.hex': '0a99e90ab6d97f2170969666b548271afbe4b75d654dc1a3c3a4c9a383acbc99', 'results/rtl/s81_head_tile_1021/img/xb.hex': '414cb62a864a7638b5d80a4e91e91b1821b367b8b418a6b8257ad5f4c598756c', 'results/rtl/fp32_add_native_clone_1020/final_packet/cells.v.gz': '04d91d0f2ad485fc614b77a80e2d9896a5c52dca879a7791e400e946ab82e1a4'}
for name, sha in expected.items():
    p=Path(name)
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
        raise SystemExit('REFUSED S81HD bb8dd356c consumed source mismatch: '+str(p)+
                         '; set S81HD_SELECTED_SOURCE_ROOT to the exact frozen closure checkout')
print('S81HD_SOURCE_GUARD_PASS closure=bb8dd356c')
S81HD_SOURCE_GUARD
if [ $? -ne 0 ]; then exit 3; fi
O=$S81HD_RUN_OUT; SC=${2:?scen}; M=${3:-none}; mkdir -p "$O"
IMG=$(realpath results/rtl/s81_head_tile_1021/img)
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version
python3 tools/prepare_fp32_fan32_models.py --out $O/cells.v || { echo "BENCH_FAIL models"; exit 3; }
SRCS="$O/cells.v rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_mul_lat_ncr.sv rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v
 rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_fadd.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_dsrom_bmul3.sv rtl/hdc/ot_hdc_delay.sv
 physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v
 rtl/dsrom_sys/s81_head/ot_s81hd_key.sv rtl/dsrom_sys/s81_head/ot_s81hd_fadd.sv rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv rtl/dsrom_sys/s81_head/ot_s81hd_bundle.sv rtl/dsrom_sys/s81_head/ot_s81hd_tile.sv
 rtl/dsrom_sys/s81_head/ot_s81hd_spo.sv rtl/dsrom_sys/s81_head/ot_s81hd_spr.sv rtl/dsrom_sys/s81_head/test/tb_s81hd_mini.sv"
D=""; [ "$M" != none ] && D="+define+OT_S81HD_MUT_$M"
OBJ=$O/obj_$M
if [ ! -x $OBJ/Vtb_s81hd_mini ]; then
  $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style $D --top-module tb_s81hd_mini -Mdir $OBJ $SRCS --build-jobs ${J:-8} \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build_$M.log 2>&1 || { grep -m10 %Error $O/build_$M.log; echo "BUILD_FAILED $M"; exit 3; }
fi
link() {   # link DIR T SRC: tile T's ROM instances -> image prefix SRC
  for e in a0 a1 a2 a3 b; do for k in 0 1; do ln -sf $IMG/$3${e}_$k.viamap.hex $1/$2${e}_$k.viamap.hex; done; done
}
# Native successor: old measured 8375 -18 (8 systolic+1 pair+8 tree+1 join,
# LAT/SK 8 -> 7) +1 element key +2 bundle tree +4 two tile keys +2 SPR key =8366.
# Keep the strict cycle check; results/arch/s81_head_1021/NATIVE_TIMING.md records provenance.
EXP_CYC_A=${EXP_CYC_A:-8366}
run() {    # run NAME T0SRC T1SRC args...
  local N=$1 a=$2 b=$3; shift 3; local W=$O/scen_${N}_$M; mkdir -p $W
  ln -sf $IMG/xa.hex $W/xa.hex; ln -sf $IMG/xb.hex $W/xb.hex; link $W t0 $a; link $W t1 $b
  ln -sf $IMG/${a}lg.hex $W/t0lg.hex; ln -sf $IMG/${b}lg.hex $W/t1lg.hex
  $OBJ/Vtb_s81hd_mini +DIR=$W +OT_ROM_DIR=$W "$@" > $O/run_${N}_$M.log 2>&1
  grep -E "^(POS|LOGITS|LOGIT_MISMATCH|TB_PASS|TB_FAIL|%Error|.*readmem)" $O/run_${N}_$M.log | sed "s/^/$N: /" | head -12
  grep -q "^TB_PASS" $O/run_${N}_$M.log
}
ok=0; n=0
for s in $( [ "$SC" = ALL ] && echo "A B C D" || echo $SC ); do
  n=$((n+1))
  case $s in
  A) run A h g +ROW0_0=21888 +ROW0_1=22016 +NPOS=2 +EXP_ROW=21946 +EXP_BITS=4173a558 +EXP_FLT=0 +EXP_CYC=$EXP_CYC_A && ok=$((ok+1)) ;;
  B) run B g h +ROW0_0=22016 +ROW0_1=21888 +TEN1=0 +EXP_ROW=22141 +EXP_BITS=40cdce35 +EXP_FLT=0 && ok=$((ok+1)) ;;
  C) run C h h +ROW0_0=21888 +ROW0_1=21760 +EXP_ROW=21818 +EXP_BITS=4173a558 +EXP_FLT=0 && ok=$((ok+1)) ;;
  D) run D h g +ROW0_0=21888 +ROW0_1=22016 +XINF_M=100 +NOLG +EXP_ROW=-1 +EXP_FLT=1 && ok=$((ok+1)) ;;
  *) echo "unknown scenario $s"; exit 2 ;;
  esac
done
[ $ok = $n ] && { echo "BENCH_PASS s81hd_mini SCEN=$SC MUT=$M ($ok/$n)"; exit 0; }
echo "BENCH_FAIL s81hd_mini SCEN=$SC MUT=$M ($ok/$n)"; exit 1
