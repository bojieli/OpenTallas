# LB2-QWEN-KV (G-K1): cut the KV boot vehicle from the kvs14c GEN netlist
. /srv/opentallas-scratch/claude/layerbench-qwen-1018/env.sh
G=/srv/opentallas-scratch/claude/lb2-qwen-kv-1018
CUT="python3 $G/tools/qwen_layerbench/slice_cut.py"
set -u
# full vehicle: kvs_ctl + 4 hroot + 32 grp (160 boot CDC sinks) + 128 pc tiles + the die relays / reset regions between them
$CUT --die-v $KDIE --bind $KBIND --src $KSRC --master 'qkd_kvs_(ctl|hroot|grp|grp_h|pc|pc_h)' --grow 'qkd_rlys_.*|qkd_rst_region' --top qwk_slice_boot --out $G/out/k_boot > $G/out/k_boot.log 2>&1; echo "k_boot rc=$?"
# without the 128 PC tiles (their o_grp returns become slice inputs)
$CUT --die-v $KDIE --bind $KBIND --src $KSRC --master 'qkd_kvs_(ctl|hroot|grp|grp_h)' --grow 'qkd_rlys_.*|qkd_rst_region' --top qwk_slice_bootg --out $G/out/k_bootg > $G/out/k_bootg.log 2>&1; echo "k_bootg rc=$?"
