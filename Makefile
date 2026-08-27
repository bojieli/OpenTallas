.PHONY: profile simulate routing noc sensitivity spec-check formal rtl-sim rtl-static rtl spice test verify clean-results

profile:
	python3 tools/profile_hf.py --all

simulate:
	python3 run.py --standard

routing:
	python3 tools/router_traces.py --all

noc:
	python3 tools/noc_sweep.py --standard

sensitivity:
	python3 tornado.py --standard
	python3 decide.py results/standard/analytical.json

spec-check:
	python3 tools/check_spec.py

formal:
	python3 tools/rtl_campaign.py --formal

rtl-sim:
	python3 tools/rtl_sim_campaign.py

rtl-static:
	python3 tools/rtl_static.py

rtl:
	$(MAKE) -C rtl verify

spice:
	$(MAKE) -C spice verify

test:
	PYTHONPATH=src pytest

verify: spec-check test rtl spice simulate noc sensitivity

clean-results:
	find results -type f \( -name '*.csv' -o -name '*.json' -o -name 'REPORT.md' -o -name 'QWEN3_8B_ADDENDUM.md' \) -delete
