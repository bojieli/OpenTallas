#!/bin/bash
set -euo pipefail
iverilog -g2012 -s tb -o lockstep.vvp gold_helper.sv candidate_helper.sv tb_lockstep.sv
vvp lockstep.vvp > lockstep.log
