.PHONY: abi3-tokens abi3-tokens-deepseek abi3-tokens-deepseek-rom abi3-tokens-deepseek-hbm abi3-tokens-qwen-rom abi3-tokens-qwen-hbm abi3-restart abi3-restart-qwen-hbm abi3-restart-qwen-rom abi3-restart-deepseek-hbm abi3-restart-deepseek-rom abi3-context-gate abi3-prefix-workloads abi3-hbm-qwen-deployment abi3-hbm-deepseek-deployment abi3-rom-schedule-check abi3-rom-qwen-degraded-build rom-service rom-service-vectors rom-service-physical abi3-rtl-engines check-evidence-grades check-prose-figures check-prose-coverage check-figures roofline abi3-failclosed abi3-equivalence abi3 abi3-engine-rate abi3-cost-tables abi3-cost-tables-check abi3-spec abi3-test abi3-workloads abi3-oracle abi3-engines abi3-rtl abi3-physical abi3-status abi3-ir profile simulate iso-node model-traffic world-model world-model-landscape legacy-sim routing noc sensitivity legacy-sensitivity spec-check formal rtl-sim fault-sim fault-campaign coverage rtl-static rtl pre-synth-verify synth-public spice spice-pdk test verify clean-results
.PHONY: abi3-rom-qwen-build abi3-rom-deepseek-build abi3-rom-deepseek-array-build abi3-hbm-qwen-build abi3-hbm-deepseek-build abi3-comparison-deepseek abi3-comparison-deepseek-array abi3-comparison-deepseek-wafer-array abi3-evidence-source-current abi3-rtl-vectors abi3-rtl-deployment-vectors abi3-rtl-deployment
.PHONY: abi3-comparison-asap7-readiness abi3-comparison-asap7-gate
.PHONY: abi3-w10-natural-oracle abi3-w10-natural-hbm-a abi3-w10-natural-hbm-b abi3-w10-natural-rom abi3-w10-natural-check abi3-w10-stress-hbm abi3-w10-stress-rom abi3-w10-stress-check
.PHONY: checkpoint-source-deepseek-pro
.PHONY: speculative

profile:
	python3 tools/profile_hf.py --all

simulate:
	$(MAKE) iso-node
	$(MAKE) model-traffic
	$(MAKE) world-model-landscape

iso-node:
	python3 tools/build_iso_node_studies.py --write
	python3 tools/run_iso_node_studies.py

roofline:
	python3 tools/run_roofline_studies.py --force

model-traffic:
	python3 tools/run_model_traffic_screen.py

world-model:
	PYTHONPATH=src python3 tools/run_world_model_study.py

world-model-landscape:
	$(MAKE) world-model
	PYTHONPATH=src python3 tools/run_world_model_landscape_study.py

legacy-sim:
	python3 run.py --standard

routing:
	python3 tools/router_traces.py --all

noc:
	python3 tools/noc_sweep.py --standard

sensitivity:
	python3 tools/run_iso_node_studies.py

legacy-sensitivity:
	python3 tornado.py --standard
	python3 decide.py results/standard/analytical.json --output results/standard/DECISION_LEGACY.md

spec-check:
	python3 tools/check_spec.py

# Evidence checks. `check-evidence-grades` reads the grade vocabulary in one
# JSON file; `check-prose-figures` reads the numbers in the documents. Until the
# second existed, nothing anywhere read a figure in prose -- which is how 80 of
# 108 load-bearing figures went stale unnoticed (docs/EVIDENCE_LEDGER.md).
check-evidence-grades:
	python3 tools/check_evidence_grades.py \
	  --also configs/studies/world_model_rom.json \
	  --also configs/studies/world_model_landscape_rom.json \
	  --also data/world-model/recent-world-models-2026-09.json \
	  --also results/abi3/deepseek_v4_prefix_workload_pins.json \
	  --also results/abi3/deepseek_v4_context_threshold_workload_pins.json

check-prose-figures:
	python3 tools/check_prose_figures.py

check-prose-coverage:
	python3 tools/audit_prose_figure_coverage.py --check

check-figures: check-evidence-grades check-prose-figures check-prose-coverage

# Speculative decoding as an ADDITIVE layer over the roofline artifacts that
# already exist.  `tools/run_speculative_roofline.py` READS
# results/roofline/**/analytical.json and writes only under
# results/roofline/speculative/; it never imports the study driver and never
# calls `opentallas.roofline.evaluate`.
#
# `roofline` is deliberately NOT a prerequisite.  That target owns every
# published figure and takes about nine minutes, and asking for the speculative
# layer must never silently start a re-evaluation of every design.  The tool
# refuses to run at all if the technology and model files it reads no longer
# hash to the pins the artifact was produced against, so a stale artifact is a
# refusal rather than a silent mixture.
#
# The grade check is run on the profile config, which is where every graded
# parameter is defined; the emitted artifact embeds copies of those same
# entries and is too large to be worth re-parsing here.
speculative:
	PYTHONPATH=. python3 tools/run_speculative_roofline.py --force
	python3 tools/check_evidence_grades.py \
	  --also configs/studies/speculative_profiles.json

formal:
	python3 tools/rtl_campaign.py --formal

rtl-sim:
	python3 tools/rtl_sim_campaign.py

fault-sim fault-campaign:
	python3 tools/rtl_fault_campaign.py

coverage:
	python3 tools/rtl_coverage_campaign.py

rtl-static:
	python3 tools/rtl_static.py

rtl:
	$(MAKE) -C rtl verify

spice:
	$(MAKE) -C spice verify

spice-pdk:
	python3 tools/run_sky130_physical.py
	python3 tools/run_sky130_extracted_pvt.py
	python3 tools/run_sky130_extracted_mismatch.py
	python3 tools/run_sky130_resistance.py
	python3 tools/run_ihp_device_smoke.py
	python3 tools/run_ihp_physical.py
	python3 tools/run_ihp_extracted_pvt.py
	python3 tools/run_ihp_resistance.py

test:
	PYTHONPATH=src pytest -q

pre-synth-verify:
	$(MAKE) spec-check
	$(MAKE) check-figures
	$(MAKE) test
	$(MAKE) -C rtl pre-synth-verify

synth-public:
	$(MAKE) -C rtl synth
	$(MAKE) -C rtl synth-reference

verify:
	$(MAKE) pre-synth-verify
	$(MAKE) synth-public
	$(MAKE) spice
	$(MAKE) simulate
	$(MAKE) noc

clean-results:
	find results -type f \( -name '*.csv' -o -name '*.json' -o -name 'REPORT.md' -o -name 'QWEN3_8B_ADDENDUM.md' \) -delete

# --- ABI 3.0 program -------------------------------------------------------
# The unified stack: one wire format, one verifier, one device, one counter
# registry, one neutral IR. Every target is a set of descriptors produced by
# this one path.

abi3-spec:
	PYTHONPATH=. python3 tools/publish_abi3_spec.py --check

abi3-test:
	PYTHONPATH=. python3 -m pytest tests/abi3 tests/sim -q
	PYTHONPATH=. python3 -m pytest tests/runtime/test_abi3_driver_evidence_agent.py -q

abi3-engines:
	@PYTHONPATH=. python3 -c "from runtime.sim.engines import load_engines; \
	r = load_engines(); \
	print(f\"engines: {r['implemented_count']} implemented, {r['missing_count']} missing\"); \
	[print('  missing', name) for name in r['missing']]"

abi3-workloads:
	PYTHONPATH=. python3 tools/build_qwen3_workloads.py

abi3-oracle:
	PYTHONPATH=. python3 tools/run_qwen3_reference_oracle.py \
	  --only TA-QW-CHAT-1 --only TA-QW-AGENT-1 \
	  --output results/abi3/qwen3_reference_oracle_short.json --force

abi3-rtl:
	PYTHONPATH=. python3 tools/rtl_abi3_campaign.py --output results/rtl/abi3_campaign.json --force

abi3-rtl-vectors:
	PYTHONPATH=. python3 tools/build_abi3_rtl_vectors.py

# The four deployments this program ships, co-simulated against
# runtime.sim.device.Device.  The vector set is built from the deployment
# bundles under build/ (ignored), so `abi3-rtl-deployment-vectors` needs them
# built first; the campaign itself reads only the committed vector images.
abi3-rtl-deployment-vectors:
	PYTHONPATH=. python3 tools/build_abi3_deployment_rtl_vectors.py

abi3-rtl-deployment:
	PYTHONPATH=. python3 tools/rtl_abi3_deployment_campaign.py \
	  --output results/rtl/abi3_deployment_campaign.json --force

abi3-rtl-engines:
	PYTHONPATH=. python3 tools/build_abi3_engine_vectors.py
	PYTHONPATH=. python3 tools/rtl_abi3_engine_campaign.py --output results/rtl/abi3_engine_campaign.json --force

rom-service-vectors:
	PYTHONPATH=. python3 tools/build_rom_service_vectors.py \
	  --deployment build/abi3/qwen3-8b-rom --product qwen3-chip --scenario nominal \
	  --checkpoint-root $(QWEN3_SNAPSHOT) \
	  --output-dir testdata/compiler/rom_service/qwen_chip --beat-budget 2500000 \
	  --executed --capability configs/hardware/abi3_capability/rom_qwen3.json \
	  --workload build/workloads/qwen3-8b/TA-QW-CHAT-1.json \
	  --prompt-tokens 16 --max-new-tokens 1
	PYTHONPATH=. python3 tools/build_rom_service_vectors.py \
	  --deployment build/abi3/qwen3-8b-rom-degraded --product qwen3-chip --scenario degraded \
	  --checkpoint-root $(QWEN3_SNAPSHOT) \
	  --output-dir testdata/compiler/rom_service/qwen_chip_degraded --beat-budget 600000 \
	  --executed --capability configs/hardware/abi3_capability/rom_qwen3.json \
	  --workload build/workloads/qwen3-8b/TA-QW-CHAT-1.json \
	  --prompt-tokens 16 --max-new-tokens 1 \
	  --mask-region rom.r0.p003.s1 --quarantine-resource 12
	PYTHONPATH=. python3 tools/build_rom_service_vectors.py \
	  --deployment build/abi3/deepseek-v4-flash-rom --product deepseek-wafer \
	  --scenario nominal \
	  --output-dir testdata/compiler/rom_service/deepseek_wafer \
	  --beat-budget 1200000 --plan-slots 1 \
	  --mask-region rom.r0.p058.s1 --quarantine-resource 4096

rom-service:
	PYTHONPATH=. python3 tools/rtl_rom_service_campaign.py \
	  --output results/rtl/rom_service_campaign.json --force

rom-service-physical:
	PYTHONPATH=. python3 tools/run_rom_service_physical.py \
	  --period-ns 20 --utilization 25 --density 0.45 --threads 8 \
	  --congestion-iterations 80 --droute-end-iter 64 --repair-timing \
	  --output results/rtl/rom_service_physical.json

abi3-physical:
	PYTHONPATH=. python3 tools/run_abi3_physical.py --view sky130hd --block reduction_endpoint --force
	PYTHONPATH=. python3 tools/run_abi3_physical.py --view asap7 --block reduction_endpoint --force

abi3-ir:
	PYTHONPATH=. python3 tools/build_qwen3_kernel_ir_v3.py \
	  --output build/ir-v3/qwen3-8b/kernel_ir.v3.json
	PYTHONPATH=. python3 tools/build_deepseek_v4_kernel_ir_v3.py \
	  --output build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  --census-output build/ir-v3/deepseek-v4-flash-0731/census.json

abi3-status:
	PYTHONPATH=. python3 tools/build_program_status.py

# W9.5.  The cost tables the cycle model reads are derived from the routed
# blocks and the executed RTL campaigns, so `--check` is what catches a table
# that has drifted from the evidence it cites.  `abi3-engine-rate` measures the
# rate `abi3-cost-tables` then consumes, so it runs first.
abi3-engine-rate:
	PYTHONPATH=. python3 tools/run_abi3_engine_rate_campaign.py 	  --output results/rtl/abi3_engine_rate.json --force

abi3-cost-tables:
	PYTHONPATH=. python3 tools/build_abi3_cost_tables.py

abi3-cost-tables-check:
	PYTHONPATH=. python3 tools/build_abi3_cost_tables.py --check

# W11.2. Generation produces an honest audit even while evidence is missing;
# the separate strict gate fails closed until every same-view input exists.
abi3-comparison-asap7-readiness:
	PYTHONPATH=. python3 tools/audit_abi3_asap7_comparison_readiness.py

abi3-comparison-asap7-gate:
	PYTHONPATH=. python3 tools/audit_abi3_asap7_comparison_readiness.py --check --require-ready

abi3: abi3-spec abi3-test abi3-engines abi3-status abi3-cost-tables-check

abi3-equivalence:
	PYTHONPATH=. python3 tools/prove_storage_class_equivalence.py \
	  --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json --product qwen3 \
	  --output results/abi3/storage_class_equivalence_qwen3.json --force
	PYTHONPATH=. python3 tools/prove_storage_class_equivalence.py \
	  --ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json --product deepseek_v4 \
	  --output results/abi3/storage_class_equivalence_deepseek_v4.json --force

abi3-failclosed:
	PYTHONPATH=. python3 tools/run_abi3_failclosed_campaign.py --force

# Build and check remain separate atomic operations.  In particular, invoking
# a certificate target below does not start a token simulation or rebuild an
# ignored deployment bundle; the ordered umbrella target does that explicitly.
abi3-rom-qwen-build:
	PYTHONPATH=. python3 tools/build_rom_deployment.py qwen3-8b \
	  --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --output build/abi3/qwen3-8b-rom \
	  --checkpoint-root $(QWEN3_SNAPSHOT) \
	  --verify --inverse --determinism

abi3-rom-qwen-degraded-build:
	PYTHONPATH=. python3 tools/build_rom_deployment.py qwen3-8b \
	  --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --defects testdata/compiler/rom_service/qwen_bist_defects.json \
	  --output build/abi3/qwen3-8b-rom-degraded \
	  --checkpoint-root $(QWEN3_SNAPSHOT) \
	  --verify --inverse --determinism

abi3-rom-deepseek-build:
	PYTHONPATH=. python3 tools/build_rom_deployment.py deepseek-v4-flash \
	  --ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  --output build/abi3/deepseek-v4-flash-rom \
	  --checkpoint-root $(DEEPSEEK_SNAPSHOT) \
	  --verify --inverse --determinism

abi3-rom-deepseek-array-build:
	PYTHONPATH=. python3 tools/build_rom_deployment.py deepseek-v4-flash-array \
	  --ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  --output build/abi3/deepseek-v4-flash-rom-array-32 \
	  --checkpoint-root $(DEEPSEEK_SNAPSHOT) \
	  --verify --inverse --determinism

abi3-hbm-qwen-build:
	PYTHONPATH=. python3 tools/build_hbm_sram_deployment.py \
	  --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --profile single-chip --out build/abi3/qwen3-8b-hbm-tokens \
	  --check-determinism

abi3-hbm-deepseek-build:
	PYTHONPATH=. python3 tools/build_hbm_sram_deployment.py \
	  --ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  --profile cluster-32 --out build/abi3/deepseek-v4-flash-hbm-tokens \
	  --check-determinism

abi3-hbm-qwen-deployment:
	PYTHONPATH=. python3 tools/check_hbm_deployments.py --jobs 1 --force

abi3-hbm-deepseek-deployment:
	PYTHONPATH=. python3 tools/check_hbm_deployments.py \
	  --case deepseek-v4-flash-hbm-cluster deepseek \
	  build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  build/abi3/deepseek-v4-flash-hbm-tokens \
	  configs/hardware/abi3_capability/hbm_sram_cluster_32.json \
	  --output results/abi3/hbm_deepseek_deployment_certificate.json \
	  --jobs 1 --force

abi3-rom-schedule-check:
	PYTHONPATH=. python3 tools/check_rom_schedules.py --jobs 2 --force

# --- accelerator tokens ----------------------------------------------------
# The token deliverable: a design is not shown to run the model until it has
# emitted tokens an external comparator validates.  One tool, one shape of
# evidence, both backends -- so that a ROM-versus-HBM comparison is between two
# runs and not between a run and an assertion.
#
# The oracle is an external comparator only (ADR-003 section 18): it supplies no
# activation, weight or token to the accelerator path.  The only values written
# into the device are the workload's own prompt token ids.
#
# The 32-token prefix is the gate because a 104-token DeepSeek run takes about
# seven hours.  It is a full-depth numeric gate -- all 43 layers, the routed
# experts, the compressor, RoPE, the FP8 dense path, the float32 head -- and it
# is *not* a sparsity gate: window_size is 128 and index_topk 512, so at 32
# tokens (and at TA-DS-CHAT-1's full 104) none of the three thresholds is
# reached.  Sparse selection under pressure is the TA-DS-CTX-* ladder's job.
DEEPSEEK_SNAPSHOT ?= $(HOME)/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/7872f01b1d1fe23eabc4c98b48bffcef5a386062
QWEN3_SNAPSHOT ?= $(HOME)/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218
#: How many tokens each lane decodes.  One token proves the forward pass and
#: says nothing about the KV transaction across decode steps, so the default is
#: more than one.
DS_TOKENS ?= 4

abi3-prefix-workloads:
	PYTHONPATH=. python3 tools/build_deepseek_v4_prefix_workloads.py \
	  --snapshot $(DEEPSEEK_SNAPSHOT)

abi3-tokens-deepseek-rom:
	PYTHONPATH=. python3 tools/run_accelerator_tokens.py \
	  --kernel-ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  --backend rom_deepseek_v4 \
	  --capability configs/hardware/abi3_capability/rom_deepseek_v4.json \
	  --workload build/workloads/deepseek-v4-flash-0731-prefix/TA-DS-CHAT-1-P32.json \
	  --reference results/abi3/deepseek_v4_reference_oracle_prefix.json \
	  --checkpoint $(DEEPSEEK_SNAPSHOT) \
	  --publish build/abi3/deepseek-v4-flash-rom-tokens \
	  --expert-numeric-path fp8 --max-new-tokens $(DS_TOKENS) \
	  --output results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json --force

abi3-tokens-deepseek-hbm:
	PYTHONPATH=. python3 tools/run_accelerator_tokens.py \
	  --kernel-ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  --backend hbm_sram \
	  --capability configs/hardware/abi3_capability/hbm_sram_cluster_32.json \
	  --workload build/workloads/deepseek-v4-flash-0731-prefix/TA-DS-CHAT-1-P32.json \
	  --reference results/abi3/deepseek_v4_reference_oracle_prefix.json \
	  --checkpoint $(DEEPSEEK_SNAPSHOT) \
	  --publish build/abi3/deepseek-v4-flash-hbm-tokens \
	  --expert-numeric-path fp8 --max-new-tokens $(DS_TOKENS) \
	  --output results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json --force

abi3-tokens-deepseek: abi3-tokens-deepseek-rom abi3-tokens-deepseek-hbm

abi3-context-gate:
	PYTHONPATH=. python3 tools/check_deepseek_v4_context_gate.py \
	  results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json \
	  --output results/abi3/deepseek_v4_context_gate.json

abi3-tokens-qwen-hbm:
	PYTHONPATH=. python3 tools/run_accelerator_tokens.py \
	  --kernel-ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --backend hbm_sram \
	  --capability configs/hardware/abi3_capability/hbm_sram_single_chip.json \
	  --workload build/workloads/qwen3-8b/TA-QW-CHAT-1.json \
	  --reference results/abi3/qwen3_reference_oracle_short.json \
	  --checkpoint $(QWEN3_SNAPSHOT) \
	  --publish build/abi3/qwen3-8b-hbm-tokens \
	  --max-new-tokens $(DS_TOKENS) \
	  --output results/abi3/accelerator_tokens/qwen3_8b_hbm_chat1.json --force

abi3-tokens-qwen-rom:
	PYTHONPATH=. python3 tools/run_accelerator_tokens.py \
	  --kernel-ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --backend rom_qwen3 \
	  --capability configs/hardware/abi3_capability/rom_qwen3.json \
	  --workload build/workloads/qwen3-8b/TA-QW-CHAT-1.json \
	  --reference results/abi3/qwen3_reference_oracle_short.json \
	  --checkpoint $(QWEN3_SNAPSHOT) \
	  --publish build/abi3/qwen3-8b-rom-tokens \
	  --max-new-tokens $(DS_TOKENS) \
	  --output results/abi3/accelerator_tokens/qwen3_8b_rom_chat1.json --force

abi3-tokens: abi3-tokens-qwen-rom abi3-tokens-qwen-hbm abi3-tokens-deepseek

# W10 long-form acceptance lanes.  These targets are deliberately atomic and
# have no execution prerequisites: invoking a checker never starts several
# hours of simulation.  Build `abi3-ir` and `abi3-workloads` explicitly before
# launching them.  The first complete 8K lane remains serialized and timed;
# only measured resource headroom may justify overlapping later lanes.
W10_ENV = env PYTHONPATH=. OPENTALLAS_ABI3_BACKEND=numpy OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 NUMEXPR_NUM_THREADS=8 VECLIB_MAXIMUM_THREADS=8

abi3-w10-natural-oracle:
	PYTHONPATH=. python3 tools/run_qwen3_gate1_attempt.py oracle

abi3-w10-natural-hbm-a:
	PYTHONPATH=. python3 tools/run_qwen3_gate1_attempt.py hbm-a

abi3-w10-natural-hbm-b:
	PYTHONPATH=. python3 tools/run_qwen3_gate1_attempt.py hbm-b

abi3-w10-natural-rom:
	PYTHONPATH=. python3 tools/run_qwen3_gate1_attempt.py rom

abi3-w10-natural-check:
	PYTHONPATH=. python3 tools/check_qwen3_w10_acceptance.py natural \
	  results/abi3/w10/qwen3_8b_hbm_natural_a.json \
	  results/abi3/w10/qwen3_8b_hbm_natural_b.json \
	  results/abi3/w10/qwen3_8b_rom_natural.json \
	  --output results/abi3/w10/qwen3_8b_natural_acceptance.json

abi3-w10-stress-hbm:
	$(W10_ENV) /usr/bin/time -v python3 tools/run_accelerator_tokens.py \
	  --kernel-ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --backend hbm_sram \
	  --capability configs/hardware/abi3_capability/hbm_sram_single_chip.json \
	  --workload build/workloads/qwen3-8b/TA-QW-STRESS-1.json \
	  --reference results/abi3/qwen3_reference_oracle_long.json \
	  --checkpoint $(QWEN3_SNAPSHOT) \
	  --publish build/abi3/qwen3-8b-hbm-w10-stress \
	  --max-new-tokens 32 --terminal-contract exact_cap \
	  --output results/abi3/w10/qwen3_8b_hbm_stress.json --force

abi3-w10-stress-rom:
	$(W10_ENV) /usr/bin/time -v python3 tools/run_accelerator_tokens.py \
	  --kernel-ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --backend rom_qwen3 \
	  --capability configs/hardware/abi3_capability/rom_qwen3.json \
	  --workload build/workloads/qwen3-8b/TA-QW-STRESS-1.json \
	  --reference results/abi3/qwen3_reference_oracle_long.json \
	  --checkpoint $(QWEN3_SNAPSHOT) \
	  --publish build/abi3/qwen3-8b-rom-w10-stress \
	  --max-new-tokens 32 --terminal-contract exact_cap \
	  --output results/abi3/w10/qwen3_8b_rom_stress.json --force

abi3-w10-stress-check:
	PYTHONPATH=. python3 tools/check_qwen3_w10_acceptance.py stress \
	  results/abi3/w10/qwen3_8b_hbm_stress.json \
	  results/abi3/w10/qwen3_8b_rom_stress.json \
	  --output results/abi3/w10/qwen3_8b_stress_acceptance.json

# Atomic promotion of the two already-produced, governed DeepSeek captures.
# No token prerequisite is attached: a comparison request must never
# unexpectedly turn into hours of model execution.
abi3-comparison-deepseek:
	PYTHONPATH=. python3 tools/build_comparison_report.py \
	  --rom results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json \
	  --hbm results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json \
	  --comparison-id deepseek-v4-flash-rom-vs-hbm-p32 \
	  --output results/abi3/comparison_deepseek_rom_vs_hbm.json --force

# The array against the same HBM cluster: the storage-class comparison at a
# fixed node count, which is what the array target was built to make possible.
abi3-comparison-deepseek-array:
	PYTHONPATH=. python3 tools/build_comparison_report.py \
	  --rom results/abi3/accelerator_tokens/deepseek_v4_flash_rom_array_p32.json \
	  --hbm results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json \
	  --comparison-id deepseek-v4-flash-rom-array-32-vs-hbm-cluster-32-p32 \
	  --rom-deployment build/abi3/deepseek-v4-flash-rom-array-32 \
	  --right-deployment build/abi3/deepseek-v4-flash-hbm-tokens \
	  --output results/abi3/comparison_deepseek_rom_array_vs_hbm.json --force

# The wafer against the array: the packaging comparison, both sides immutable
# ROM.  The 32-node array holds node count fixed rather than area, so this pair
# is the equal-node control; the iso-area comparator is the reticle count whose
# silicon matches the wafer's, which the contract states and the roofline
# reports.  See configs/abi3/comparison_contracts/
# deepseek_v4_rom_wafer_vs_rom_array_32_v1.json.
abi3-comparison-deepseek-wafer-array:
	PYTHONPATH=. python3 tools/build_comparison_report.py \
	  --rom results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json \
	  --rom-array results/abi3/accelerator_tokens/deepseek_v4_flash_rom_array_p32.json \
	  --comparison-id deepseek-v4-flash-rom-wafer-vs-rom-array-32-p32 \
	  --rom-deployment build/abi3/deepseek-v4-flash-rom \
	  --right-deployment build/abi3/deepseek-v4-flash-rom-array-32 \
	  --output results/abi3/comparison_deepseek_wafer_vs_array.json --force

# Source-current evidence regeneration has explicit barriers.  All four
# canonical bundles are rebuilt before consumers inspect them.  Token lanes and
# HBM certificates stay sequential: the DeepSeek checkpoint is about 156 GB and
# this host has no demonstrated headroom for two numerical lanes or certificate
# rebuilds at once.  Bounded JSON consumers, the schedule checker's own workers,
# and the RTL campaigns' Icarus/Verilator pair retain safe internal parallelism.
# The atomic targets above remain independently invocable; only this umbrella
# opts into the long-running token work.
abi3-evidence-source-current:
	$(MAKE) abi3-rom-qwen-build
	$(MAKE) abi3-hbm-qwen-build
	$(MAKE) abi3-rom-deepseek-build
	$(MAKE) abi3-hbm-deepseek-build
	$(MAKE) abi3-tokens-qwen-rom
	$(MAKE) abi3-tokens-qwen-hbm
	$(MAKE) abi3-tokens-deepseek-rom
	$(MAKE) abi3-tokens-deepseek-hbm
	$(MAKE) abi3-hbm-qwen-deployment
	$(MAKE) abi3-hbm-deepseek-deployment
	$(MAKE) abi3-rom-schedule-check
	$(MAKE) -j2 abi3-context-gate abi3-comparison-deepseek
	$(MAKE) abi3-rtl-vectors
	$(MAKE) abi3-rtl
	$(MAKE) abi3-rtl-engines
	$(MAKE) abi3-rtl-deployment-vectors
	$(MAKE) abi3-rtl-deployment

# --- checkpoint/restart exactness ------------------------------------------
# Each target runs an uninterrupted comparator, an interrupted prefix, and a
# fresh-process resume.  The state-erased negative control and complementary
# state-only control are enabled by default.  Three generated tokens split 2+1
# put the checkpoint after a real decode transaction while keeping the governed
# DeepSeek campaign tractable.
RESTART_TOKENS ?= 3
RESTART_STOP_AFTER ?= 2

abi3-restart-qwen-hbm:
	PYTHONPATH=. python3 tools/run_abi3_restart_exactness.py \
	  --kernel-ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --backend hbm_sram \
	  --capability configs/hardware/abi3_capability/hbm_sram_single_chip.json \
	  --workload build/workloads/qwen3-8b/TA-QW-CHAT-1.json \
	  --deployment-root $(QWEN3_SNAPSHOT) \
	  --max-new-tokens $(RESTART_TOKENS) --stop-after $(RESTART_STOP_AFTER) \
	  --work-dir build/restart/qwen3-hbm \
	  --output results/abi3/restart_exactness_qwen3_hbm.json --force

abi3-restart-qwen-rom:
	PYTHONPATH=. python3 tools/run_abi3_restart_exactness.py \
	  --kernel-ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
	  --backend rom_qwen3 \
	  --capability configs/hardware/abi3_capability/rom_qwen3.json \
	  --workload build/workloads/qwen3-8b/TA-QW-CHAT-1.json \
	  --deployment-root $(QWEN3_SNAPSHOT) \
	  --max-new-tokens $(RESTART_TOKENS) --stop-after $(RESTART_STOP_AFTER) \
	  --work-dir build/restart/qwen3-rom \
	  --output results/abi3/restart_exactness_qwen3_rom.json --force

abi3-restart-deepseek-hbm:
	PYTHONPATH=. python3 tools/run_abi3_restart_exactness.py \
	  --kernel-ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  --backend hbm_sram \
	  --capability configs/hardware/abi3_capability/hbm_sram_cluster_32.json \
	  --workload build/workloads/deepseek-v4-flash-0731-prefix/TA-DS-CHAT-1-P32.json \
	  --deployment-root $(DEEPSEEK_SNAPSHOT) \
	  --max-new-tokens $(RESTART_TOKENS) --stop-after $(RESTART_STOP_AFTER) \
	  --work-dir build/restart/deepseek-hbm \
	  --output results/abi3/restart_exactness_deepseek_hbm_p32.json --force

abi3-restart-deepseek-rom:
	PYTHONPATH=. python3 tools/run_abi3_restart_exactness.py \
	  --kernel-ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
	  --backend rom_deepseek_v4 \
	  --capability configs/hardware/abi3_capability/rom_deepseek_v4.json \
	  --workload build/workloads/deepseek-v4-flash-0731-prefix/TA-DS-CHAT-1-P32.json \
	  --deployment-root $(DEEPSEEK_SNAPSHOT) \
	  --max-new-tokens $(RESTART_TOKENS) --stop-after $(RESTART_STOP_AFTER) \
	  --work-dir build/restart/deepseek-rom \
	  --output results/abi3/restart_exactness_deepseek_rom_p32.json --force

abi3-restart: abi3-restart-qwen-hbm abi3-restart-qwen-rom abi3-restart-deepseek-hbm abi3-restart-deepseek-rom

# --- checkpoint source expectations ----------------------------------------
# `tools/build_checkpoint_source.py` writes the expectation half of a
# checkpoint identity: the digest and size of every file the registry lists at
# the pinned revision, each local digest confronted with the registry's own
# per-file record so the expectation is not derived from the bytes it will later
# be used to check.  The witness is committed beside the byte inventories under
# data/inventory/ rather than fetched, so a rerun needs no network.
#
# This target reads and hashes every byte of the released Pro checkpoint:
# 892,762,497,859 bytes (831 GiB) over the 92 files the registry lists at
# revision 72e1d3230f6c, 66 of them safetensors shards.  Expect roughly 17
# minutes -- a projection from the 0.90 GB/s this host measured hashing the
# 166,878,536,440-byte Flash checkpoint in 185 s, not a measured Pro runtime.
# It fails closed unless the whole snapshot is present locally.  Because of that
# cost it is deliberately not a prerequisite of any aggregate target; invoke it
# by name, once, when the checkpoint is complete.
DEEPSEEK_PRO_REVISION ?= 72e1d3230f6c080a530b0a1d46f8eb4602340597
DEEPSEEK_PRO_SNAPSHOT ?= $(HOME)/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Pro-0813/snapshots/$(DEEPSEEK_PRO_REVISION)
DEEPSEEK_PRO_REGISTRY_LISTING ?= data/inventory/deepseek-v4-pro-0813-registry-listing.json

checkpoint-source-deepseek-pro:
	PYTHONPATH=. python3 tools/build_checkpoint_source.py \
	  --repository deepseek-ai/DeepSeek-V4-Pro-0813 \
	  --revision $(DEEPSEEK_PRO_REVISION) \
	  --snapshot $(DEEPSEEK_PRO_SNAPSHOT) \
	  --registry-listing $(DEEPSEEK_PRO_REGISTRY_LISTING) \
	  --output compiler/models/deepseek-v4-pro-0813/checkpoint_source.json
