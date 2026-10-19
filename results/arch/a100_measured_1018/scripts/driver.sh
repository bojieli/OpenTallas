#!/bin/bash
# A100-BENCH 10-18 local driver: rent -> bench -> fetch -> DESTROY (trap on every exit path).
set -u
eval "$(grep -E '^export VAST_AI_CLIENT_API_KEY=' ~/.bashrc)"
V="$HOME/.local/bin/vastai"; K="--api-key $VAST_AI_CLIENT_API_KEY"
OFFER=${OFFER:-54858898}
IMAGE=vllm/vllm-openai:v0.31.0
B=/home/ubuntu/a100bench; mkdir -p $B/out
KEY=$HOME/.ssh/vast_a100_1018
SO="-i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlPath=none -o ServerAliveInterval=30 -o ConnectTimeout=20 -o LogLevel=ERROR"
START=$(date +%s); DEADLINE=$(( START + 5*3600 + 30*60 ))   # 5.5 h of work; watchdog kills at 6 h
log(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a $B/driver.log; }

ID=""
cleanup(){
  if [ -n "$ID" ]; then
    log "DESTROY $ID"
    for i in 1 2 3 4 5; do $V destroy instance $ID -y $K >>$B/driver.log 2>&1 && break; sleep 10; done
    kill $(cat $B/watchdog_pid 2>/dev/null) 2>/dev/null
    sleep 5; $V show instances $K 2>&1 | tail -3 | tee -a $B/driver.log
  fi
}
trap cleanup EXIT
trap 'exit 1' INT TERM HUP

RES=$($V create instance $OFFER --image $IMAGE --disk 120 --ssh --direct --env '-e HF_HOME=/root/hf' --raw $K 2>&1)
ID=$(echo "$RES" | python3 -c 'import json,sys;print(json.load(sys.stdin)["new_contract"])' 2>/dev/null)
[ -z "$ID" ] && { log "CREATE FAILED: $(echo "$RES" | head -c 300)"; exit 1; }
echo $ID > $B/instance_id; log "created $ID on offer $OFFER"
# independent watchdog: destroys at 6 h even if this driver dies
nohup bash -c "sleep 21600; $V destroy instance $ID -y $K" >/dev/null 2>&1 &
echo $! > $B/watchdog_pid

for i in $(seq 1 90); do
  ST=$($V show instance $ID --raw $K 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("actual_status"))' 2>/dev/null)
  [ "$ST" = running ] && break
  [ $((i % 5)) = 0 ] && log "status=$ST"
  sleep 20
done
[ "$ST" = running ] || { log "never reached running ($ST)"; exit 1; }
$V attach ssh $ID "$(cat $KEY.pub)" $K >>$B/driver.log 2>&1
URL=$($V ssh-url $ID $K 2>/dev/null | tail -1)          # ssh://root@host:port
HP=${URL#ssh://root@}; H=${HP%:*}; P=${HP##*:}
log "ssh $H:$P"
S(){ ssh $SO -p $P root@$H "$@"; }
for i in $(seq 1 30); do S true 2>/dev/null && break; sleep 10; done
S 'nvidia-smi; nvidia-smi -q -d CLOCK,POWER | head -80' > $B/out/nvidia-smi-initial.txt 2>&1 || { log "ssh failed"; exit 1; }
log "ssh ok: $(grep -m1 -oE 'A100[^|]*' $B/out/nvidia-smi-initial.txt)"
scp $SO -P $P $B/scripts/remote_bench.sh root@$H:/root/ >/dev/null
S 'mkdir -p /root/out; cat > /root/all.sh <<EOF
cd /root
bash remote_bench.sh w8a8_kvfp8 RedHatAI/Qwen3-8B-quantized.w8a8 fp8
bash remote_bench.sh w8a8_kvauto RedHatAI/Qwen3-8B-quantized.w8a8 auto
bash remote_bench.sh bf16_kvauto Qwen/Qwen3-8B auto
bash remote_bench.sh bf16_kvfp8 Qwen/Qwen3-8B fp8
touch /root/out/ALLDONE
EOF
nohup bash /root/all.sh > /root/out/all.log 2>&1 &'
log "bench launched"

fetch(){ mkdir -p $B/out/remote; S 'tar -C /root/out -cf - .' 2>/dev/null | tar -C $B/out/remote -xf - 2>/dev/null; }
while :; do
  sleep 120
  fetch
  grep -h '^\[' $B/out/remote/all.log 2>/dev/null | tail -1 | sed 's/^/  /' >> $B/driver.log
  [ -f $B/out/remote/ALLDONE ] && { log "ALLDONE"; break; }
  [ $(date +%s) -gt $DEADLINE ] && { log "DEADLINE reached, stopping"; break; }
  CR=$($V show user --raw $K 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("credit",99))' 2>/dev/null)
  echo "  credit=$CR" >> $B/driver.log
  python3 -c "import sys;sys.exit(0 if float('${CR:-99}')<2.5 else 1)" && { log "CREDIT LOW ($CR), stopping"; break; }
done
fetch
log "elapsed $(( ($(date +%s) - START) / 60 )) min"
exit 0
