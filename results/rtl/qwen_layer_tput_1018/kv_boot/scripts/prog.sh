# LB2-QWEN-KV: compile the KV die boot images with the compiler of the netlist's own source tree (kvs14c = f05f9338f)
KSRC=/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14-f05f9338f
G=/srv/opentallas-scratch/claude/lb2-qwen-kv-1018
cd $KSRC && git -C $KSRC rev-parse HEAD > $G/kvprog.src && git -C $KSRC status --porcelain tools/qwen_kv_die tools/qwen_static_kv tools/qwen_split tools/qwen_static_schedule tools/qwen_attention_native results/arch/qwen_kv_static_programme_1017 >> $G/kvprog.src
PYTHONDONTWRITEBYTECODE=1 python3 tools/qwen_kv_die/kv_static_programme.py --out $G/kvprog --profile die > $G/kvprog.log 2>&1; echo "rc=$?" >> $G/kvprog.log
