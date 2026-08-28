.PHONY: profile simulate iso-node model-traffic legacy-sim routing noc sensitivity legacy-sensitivity spec-check formal rtl-sim fault-sim fault-campaign coverage rtl-static rtl pre-synth-verify synth-public spice spice-pdk test verify clean-results

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
