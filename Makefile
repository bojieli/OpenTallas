.PHONY: profile simulate routing noc sensitivity rtl spice test verify clean-results

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

rtl:
	$(MAKE) -C rtl verify

spice:
	$(MAKE) -C spice verify

test:
	PYTHONPATH=src pytest

verify: test rtl spice simulate noc sensitivity

clean-results:
	find results -type f \( -name '*.csv' -o -name '*.json' -o -name 'REPORT.md' \) -delete
