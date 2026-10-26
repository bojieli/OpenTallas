set -eu
docker run --rm -v "$PWD:/data" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /data/raw.tcl > raw_export.log 2>&1
sha256sum raw.lef original.odb abstract_pin_stub.py
python3 abstract_pin_stub.py raw.lef reconstructed_final.lef
sha256sum reconstructed_final.lef
