#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c replay.sha256 >input_guard.log
mkdir -p logs
failed=0
for mode in 0 1 2;do
 for native in 0 1;do
 fault=0;which=none
 if [[ $mode != 2 && $native == 1 ]];then fault=1;which=0;fi
 if ! bin/m${mode} +NATIVE=$native +FAULT=$fault +REQUIRE_SEEN=4 >logs/m${mode}_n${native}.log 2>&1 || ! python3 check_causal.py logs/m${mode}_n${native}.log $which;then echo "FAIL MODE=$mode NATIVE=$native";failed=1;else echo "PASS MODE=$mode NATIVE=$native";fi
 done
 fault=1;which=1
 if [[ $mode == 2 ]];then fault=0;which=none;fi
 if ! bin/m${mode} +NATIVE=1 +NOCHASE=1 +FAULT=$fault +REQUIRE_SEEN=4 >logs/m${mode}_nochase.log 2>&1 || ! python3 check_causal.py logs/m${mode}_nochase.log $which;then echo "FAIL NOCHASE MODE=$mode";failed=1;else echo "PASS NOCHASE MODE=$mode";fi
 done
set +e
bin/m2 +NATIVE=1 +OLD6=1 >logs/old6.log 2>&1
rc=$?
set -e
if [[ $rc == 0 ]] || ! grep -q GME_FIELD_ORDER_OR_BOUNDS logs/old6.log;then echo FAIL_OLD6;failed=1;else echo PASS_OLD6;fi
if ! bin/m2 +NATIVE=1 +BUSY=1 +FAULT=1 +REQUIRE_SEEN=4 >logs/ownbusy.log 2>&1 || ! python3 check_causal.py logs/ownbusy.log 0;then echo FAIL_OWNBUSY;failed=1;else echo PASS_OWNBUSY;fi
echo "TERMINAL failed=$failed"
exit "$failed"
