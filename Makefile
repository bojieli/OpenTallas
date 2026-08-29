.PHONY: abi3-failclosed abi3-equivalence abi3 abi3-spec abi3-test abi3-workloads abi3-oracle abi3-engines abi3-rtl abi3-physical abi3-status abi3-ir profile simulate iso-node model-traffic legacy-sim routing noc sensitivity legacy-sensitivity spec-check formal rtl-sim fault-sim fault-campaign coverage rtl-static rtl pre-synth-verify synth-public spice spice-pdk test verify clean-results

profile:
	python3 tools/profile_hf.py --all

simulate:
	$(MAKE) iso-node
	$(MAKE) model-traffic

iso-node:
	python3 tools/build_iso_node_studies.py --write
	python3 tools/run_iso_node_studies.py

model-traffic:
	python3 tools/run_model_traffic_screen.py

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

abi3: abi3-spec abi3-test abi3-engines abi3-status

abi3-equivalence:
	PYTHONPATH=. python3 tools/prove_storage_class_equivalence.py \
	  --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json --product qwen3 \
	  --output results/abi3/storage_class_equivalence_qwen3.json --force
	PYTHONPATH=. python3 tools/prove_storage_class_equivalence.py \
	  --ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json --product deepseek_v4 \
	  --output results/abi3/storage_class_equivalence_deepseek_v4.json --force

abi3-failclosed:
	PYTHONPATH=. python3 tools/run_abi3_failclosed_campaign.py --force
