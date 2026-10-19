#!/usr/bin/env python3
"""Enumerate diagnostic D4K2 data-only windows; never emits timing exceptions."""
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--mut-overwrite',action='store_true');a=p.parse_args();rows=[];T=833.333;D=4;K=2
for n in range(16,32):
 slot=(n-K)%D;launch=n-K;overwrite=launch+(2 if a.mut_overwrite else D)
 for phase in [-.4,0,.4]:
  capture=n+phase;setup=capture-launch;hold=overwrite-capture
  rows.append(dict(slot=slot,writer_launch_edge=launch,receiver_capture_edge=n,receiver_phase_T=phase,capture_time_T=capture,next_same_slot_overwrite_edge=overwrite,setup_age_T=round(setup,6),hold_gap_T=round(hold,6)))
minimum_setup=min(r['setup_age_T']for r in rows);minimum_hold=min(r['hold_gap_T']for r in rows);ok=minimum_setup>=1.6 and minimum_hold>=1.6
s=Path('rtl/physical/qcluster/qfd_c_land_safe.sv').read_bytes();o=dict(schema='opentallas.cb16.bank_window.v1',diagnostic_only=True,rtl_sha256=hashlib.sha256(s).hexdigest(),source='b25f19be20174b6f98218ed6fa9ca6641e99b166',D=D,K=K,T_ps=T,phase_envelope_T=[-.4,.4],minimum_setup_age_T=minimum_setup,minimum_hold_gap_T=minimum_hold,minimum_setup_age_ps=minimum_setup*T,minimum_hold_gap_ps=minimum_hold*T,enumeration_pass=ok,rows=rows,endpoint_scope='write b0..b3 flopQ to read o flopD DATA ONLY; select/status/writtenflags/epochs ordinary timing; no flags included without independent proof',release_ready=False,blockers=['actual TT/FF phi-R/rootspread envelope plus150ps setup/100ps hold reserves not yet certified in parent','reset warm/written/epoch proof for both reset orders missing','routed bank/endpoint geometry405um, native launch/capture budgets and parent clock composition not qualified','finite max/min actual Tcl dispatch requires tool/schema owner and root review; no timing exceptions emitted'])
Path(a.out).write_text(json.dumps(o,indent=1)+'\n');print('BANK_WINDOW',ok,'setupT',minimum_setup,'holdT',minimum_hold)
if not ok:raise SystemExit(1)
