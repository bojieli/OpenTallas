cd /root
while kill -0 1037 2>/dev/null; do sleep 10; done
bash remote_bench2.sh w8a8_kvfp8 nm-testing/Qwen3-8B-W8A8-INT8 fp8 all
bash remote_bench2.sh bf16_kvfp8 Qwen/Qwen3-8B fp8 all
bash remote_bench2.sh w8a8_kvauto nm-testing/Qwen3-8B-W8A8-INT8 auto all
bash remote_bench2.sh bf16_kvauto Qwen/Qwen3-8B auto dec
touch /root/out/ALLDONE
