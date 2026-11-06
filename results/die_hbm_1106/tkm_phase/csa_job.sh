#!/bin/bash
set -eu
cd "$(dirname "$0")"
/usr/bin/time -v yosys -p 'read_verilog leaf.v csa_miter.v; hierarchy -top csa_miter; flatten; proc; opt; sat -prove bad 0 -verify' > csa_formal.log 2>&1
