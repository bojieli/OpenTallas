#!/bin/bash
set -eu
cd "$(dirname "$0")"
for corner in TT FF;do CORNER=$corner sta -exit coupon_pi320.tcl > coupon_pi320_$corner.log 2>&1;done
