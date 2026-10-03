# Replay: qwen_hbm_sustained_bw_20261003

From the repository root (Verilator 5.050 at ~/.local/opentallas-tools, Python 3):

```bash
# 1. model (about 4 min, one CPU)
python3 tools/qwen_hbm_sustained_bw_model.py --result /tmp/m.json
cmp /tmp/m.json results/uarch/qwen_hbm_sustained_bw_20261003/model-r1.json

# 2. RTL bench: one run per line of logs/list.txt and logs/extra.txt, e.g. the primary case
tests/rtl/run_hbm_stream_bw.sh -GREF_MODE=1 -GHINT=320 -GPHASE=0      # SUMMARY verdict=PASS
tests/rtl/run_hbm_stream_bw.sh -GLAYERS=2 -GMUT=1                     # negative control: FAIL expected
#    save each run's stdout as logs/<name>.log, then
python3 tools/qwen_hbm_sustained_bw_collect.py                        # rewrites rtl-bench-r1.json

# 3. existing timing models, the same stream
tests/rtl/run_hbm_stream_existing_models.sh -GMODEL=0                 # also -GMODEL=0 -GPCRDY=1, -GMODEL=1, -GMODEL=2

# 4. SS screen of one channel slice (2 PCs + arbiter), WC setup / WC,BC hold, 1.2 GHz
python3 tools/run_abi3_physical.py --view asap7 --top ot_hbm_r14_stream_stack \
  --source rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv --source rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv \
  --param ENABLE=1 --param REF_MODE=1 --param NCH=1 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0 --false-path-from rst_n \
  --slew-margin-percent 40 --max-transition-ns 0.32 --purpose characterization --core-utilization 40 \
  --place-density 0.6 --orfs-var ADDER_MAP_FILE= --stages pnr --output /tmp/stream_ch1_ss1p2.json
```

The run names encode the parameters: pb = REF_MODE 1, ab = REF_MODE 0, h = HINT, p = PHASE, b2b = B2B 1, cred = CRED. Each RTL run is under a minute after a build of about 2 to 5 minutes. No pinned file is touched: the new modules are default-off (ENABLE=0) and nothing instantiates them.
