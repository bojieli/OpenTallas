# QW-KVATTN step 1: KV boot vehicle on the kvs14p-fa7fe4ff9 netlist with the F-K1-fixed HOST loader
set -u
G=/srv/opentallas-scratch/claude/qw-kvattn-1018
KP=/srv/opentallas-scratch/claude/qwen-kvsys/kvs14p-fa7fe4ff9
KSRC=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14p-fa7fe4ff9
KDIE=$KP/port_bind_v2/die_bound.v; KBIND=$KP/port_bind_v2/port_bind_v2.json
cd $G
echo "host $(hostname) start $(date)" > boot.status
# images compiled by the netlist's own source tree
git -C $KSRC rev-parse HEAD > kvprog.src; git -C $KSRC status --porcelain tools/qwen_kv_die tools/qwen_static_kv tools/qwen_split results/arch/qwen_kv_static_programme_1017 >> kvprog.src
(cd $KSRC && PYTHONDONTWRITEBYTECODE=1 python3 tools/qwen_kv_die/kv_static_programme.py --out $G/kvprog --profile die > $G/kvprog.log 2>&1); echo "kvprog rc=$?" | tee -a boot.status
python3 tools/qwen_layerbench/kv_boot_images.py --kvprog kvprog --out img_die > img.log 2>&1; echo "img rc=$?" | tee -a boot.status
python3 tools/qwen_layerbench/slice_cut.py --die-v $KDIE --bind $KBIND --src $KSRC --master 'qkd_kvs_(ctl|hroot|grp|grp_h|pc|pc_h)' --grow 'qkd_rlys.*|qkd_landsh.*|qkd_rst_region.*' --top qwk_slice_boot --out out/k_boot > out_k_boot.log 2>&1; echo "cut rc=$?" | tee -a boot.status
KVB_LD=$G/ld/qkd_host_program_loader_target.sv KVB_ALT=76 bash tools/qwen_layerbench/run_kv_boot.sh out/k_boot run_boot $KSRC img_die img_die > run_boot.out 2>&1
echo "run rc=$? end $(date)" >> boot.status
