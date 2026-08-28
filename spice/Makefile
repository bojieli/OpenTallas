.PHONY: verify topology sky130-contracts sky130-physical sky130-extracted-pvt sky130-extracted-mismatch sky130-resistance sky130 ihp-contracts ihp-device-smoke ihp-physical ihp-extracted-pvt ihp-resistance ihp pdk-contracts clean

verify: topology

topology:
	python3 check_spice.py

sky130-contracts:
	python3 run_sky130_rom_read.py --validate-only
	python3 ../tools/run_sky130_physical.py --validate-only
	python3 ../tools/run_sky130_extracted_pvt.py --validate-only
	python3 ../tools/run_sky130_extracted_mismatch.py --validate-only
	python3 ../tools/run_sky130_resistance.py --validate-only

ihp-contracts:
	python3 ../tools/run_ihp_device_smoke.py --validate-only
	python3 ../tools/run_ihp_physical.py --validate-only
	python3 ../tools/run_ihp_extracted_pvt.py --validate-only
	python3 ../tools/run_ihp_resistance.py --validate-only

pdk-contracts: sky130-contracts ihp-contracts

sky130-physical: sky130-contracts
	python3 ../tools/run_sky130_physical.py

sky130-extracted-pvt: sky130-physical
	python3 ../tools/run_sky130_extracted_pvt.py

sky130-extracted-mismatch: sky130-extracted-pvt
	python3 ../tools/run_sky130_extracted_mismatch.py

sky130-resistance: sky130-extracted-pvt
	python3 ../tools/run_sky130_resistance.py

sky130: sky130-extracted-mismatch sky130-resistance
	python3 run_sky130_rom_read.py

ihp-device-smoke: ihp-contracts
	python3 ../tools/run_ihp_device_smoke.py

ihp-physical: ihp-device-smoke
	python3 ../tools/run_ihp_physical.py

ihp-extracted-pvt: ihp-physical
	python3 ../tools/run_ihp_extracted_pvt.py

ihp-resistance: ihp-extracted-pvt
	python3 ../tools/run_ihp_resistance.py

ihp: ihp-resistance

clean:
	rm -rf build
