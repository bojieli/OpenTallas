# LB2-QWEN-KV G-K1: build + run the KV boot vehicle (as-built HOST loader, DIAGNOSTIC t10 fix, mutants)
G=/srv/opentallas-scratch/claude/lb2-qwen-kv-1018; KSRC=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14-f05f9338f
echo "host $(hostname) start $(date)" > $G/run1.status
bash $G/tools/qwen_layerbench/run_kv_boot.sh $G/out/k_boot $G/run1 $KSRC $G/img_l1 $G/img_die > $G/run1.out 2>&1
echo "rc=$? end $(date)" >> $G/run1.status
