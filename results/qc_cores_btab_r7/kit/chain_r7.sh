#!/bin/bash
# QC-CORES-1 btab_m0_r7 chain: CTS (mscts_spec_r7.tcl = plan btab_r7_k6_vor_L3, ITERS 0, TritonCTS off) + GRT, then DRT+fill+finish (RCX). No hold repair, no clock edits.
K=$(cd "$(dirname "$0")" && pwd)
echo CHAIN_START $(date -Is) > $K/chain_r7.txt
bash $K/cts_r7.sh; rc=$?; echo CTS_GRT rc $rc $(date -Is) >> $K/chain_r7.txt; [ $rc -eq 0 ] || exit $rc
bash $K/route_r7.sh; rc=$?; echo ROUTE rc $rc $(date -Is) >> $K/chain_r7.txt; exit $rc
