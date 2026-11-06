#!/bin/bash
set -eu
cd "$(dirname "$0")"
gcc -O2 -Wall -Wextra -o algebra algebra.c
/usr/bin/time -v ./algebra > algebra_result.json 2>algebra_time.log
