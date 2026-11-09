R=/home/ubuntu/OpenTallas
F=physical/die_plan/s81/plan_h2_2249.json
for t in w2 u3; do T=/dev/shm/rm56/$t; ( cd $T && git checkout-index -f -- $F && timeout 280 python3 -m pytest -q -p no:cacheprovider --basetemp=/dev/shm/rm56/tmp/ccl_$t tools/s81_dv/tokfunc/test_compose_current_latency.py 2>&1 | tail -6 | cut -c1-200 | sed "s/^/$t: /" ) & done; wait
