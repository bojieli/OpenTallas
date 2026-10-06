#!/usr/bin/env python3
# Exact lexical import expansion only. No codec/repair/clock/protection rewrite.
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[4]
r='physical/hbm_die_abstracts_20261006/links/station_physical_20261006'
paths=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv']
pkg=(root/paths[0]).read_text().split('package ot_gpu_w6_secded_pkg;',1)[1].split('endpackage',1)[0]
s=(root/paths[1]).read_text()
boundary=s.split('package ot_hbm_w2_boundary_pkg;',1)[1].split('endpackage',1)[0]
s=s.split('endpackage',1)[1]
s=s.replace(' import ot_gpu_w6_secded_pkg::*;',pkg).replace(' import ot_hbm_w2_boundary_pkg::*;',boundary)
assert 'package ' not in s and 'import ' not in s
out=root/r/'ot_hbm_w2_protected_bank_lowered.sv';out.write_text('`timescale 1ns/1ps\n// Exact package expansion; keep/dont_touch attributes preserved.\n'+s)
(root/r/'lowering.json').write_text(json.dumps({'operation':'lexical package import expansion only','source_hashes':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'attributes_preserved':True},indent=2)+'\n')
