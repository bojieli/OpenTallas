#!/bin/bash
set -euo pipefail
cd /run
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -exit legalize.tcl > legalize.log 2>&1
openroad -no_init -exit -python child_contacts.py restore > restore.log 2>&1
openroad -no_init -exit -python extract.py > extract.log 2>&1
