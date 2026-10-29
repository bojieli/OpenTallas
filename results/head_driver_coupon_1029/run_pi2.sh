#!/bin/bash
set -eu
cd "$(dirname "$0")"
for corner in TT FF;do CORNER=$corner sta -exit coupon_pi2.tcl > coupon_pi2_$corner.log 2>&1;done
