#!/usr/bin/env python3
"""Q-RLYFCLK 10-19 (RELEASE_TREE Q.STA.RLY): forwarded-capture payload contract for the die fclk audit.

    fclk_data_ports.py DIE_V  > fclk_data_ports.tcl

The die fclk audit (tools/die_repeaters/fclk_audit.tcl) pairs each forwarded clock (n_fck_*) with the data bits of the
hop it captures.  Without a contract it traces EVERY input of the capture back to its source; a landing (qfd_landh_*)
takes its K strap k0..k2 from its OWN tie_hi / tie_lo outputs (LANDING-CONTRACT L5), so the trace finds the capture
instance itself as a data source and flags every landing fclk net as a BROADCAST (dv2f15r: 86 of 415, all landh).
Every n_fck_* net of the GEN already has exactly one capture (one net per hop, prev.ck_o -> station.ckf).

This emits ::ot_die_rep_fclk_data_ports (the producer contract the audit reads, as S81 tools/s81_dv/dv_rvcase.py):
for every forwarded-lane capture master the complete hop payload and its width, from the GEN's master naming
qfd_<kind>_<bits>_<faces>_<w>x<h> (tools/qwen_rom_fulldie_b3r2.py _relays emit):
    rlyh / landh  (data lanes)  a[bits-1:0] + ea (lane epoch)  -> glob [ae]* , bits + 1
    rlyr          (reset lanes) a[bits-1:0]                    -> same glob, bits
(the glob matches a[i] / ea[0] of the GEN frames AND the scalar a / ea of the bound 1-bit closed views, e.g.
qfd_landh_1_EN_65x30; no other capture input starts with a or e: ck ckf rs k0-k2)
ck / rs / k0..k2 (straps from own ties) are auxiliary, not hop payload.  A missing / undriven / extra payload bit still
fails closed in the audit (pairing_errors), and every payload bit's repeater depth is judged against its fclk.
"""
import re
import sys

KINDS = {'rlyh': 1, 'landh': 1, 'rlyr': 0}      # + ea[0] epoch bit on data lanes
PAT = re.compile(r'^\s*(qfd_(rlyh|landh|rlyr)_(\d+)_[A-Z]+_\d+x\d+)\s+\S+\s*\(', re.M)


def contracts(text):
    out = {}
    for mst, kind, bits in PAT.findall(text):
        out[mst] = int(bits) + KINDS[kind]
    return out


def tcl(c):
    body = ' '.join(f'{{{m}}} {{{{[ae]*}} {n}}}' for m, n in sorted(c.items()))
    return ('# Q-RLYFCLK forwarded-capture payload contract (tools/qwen_split/fclk_data_ports.py)\n'
            f'set ::ot_die_rep_fclk_data_ports [dict create {body}]\n'
            f'puts "OT_DIE_REP_FCLK_CONTRACT masters={len(c)}"\n')


if __name__ == '__main__':
    sys.stdout.write(tcl(contracts(open(sys.argv[1]).read())))
