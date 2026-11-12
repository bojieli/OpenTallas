#!/usr/bin/env python3
"""Response calendar for the rd1 hub bench, built with the COMPILER's helper (hbm_vm_static_calendar.shift_response).

  gen_resp_cal.py OUT.mem SHIFT [PERIOD]

One calendar row per edge t (1000 issue edges + drain).  The unshifted compiler timeline answers the request issued at
edge t (clients 0..4, t%PERIOD<4, slot seq = t%PERIOD) at t+9 (the pre-rd1 bank body, 8 pipe stages + the input edge).  SHIFT is the rd1 response calendar +N:
the response_enable / response_seq field bits move from row i to row i+N through shift_response() on the dict rows,
exactly as compile_schedule(resp_shift=N) does.  Output: one hex word per edge, {response_seq[9:0], response_enable[4:0]}.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import hbm_vm_static_calendar as C  # noqa: E402

N_CLIENTS, ISSUE, BASE_RT = 5, 1000, 9
out, shift = Path(sys.argv[1]), int(sys.argv[2])
PERIOD = int(sys.argv[3]) if len(sys.argv) > 3 else 10   # slot period (10 + rd1 body +1)
rows = [dict() for _ in range(ISSUE + BASE_RT + 1)]
for t in range(ISSUE):
    if t % PERIOD < 4:
        row = rows[t + BASE_RT]
        for c in range(N_CLIENTS):
            row['response_enable'] = row.get('response_enable', 0) | 1 << c
            row['response_seq'] = row.get('response_seq', 0) | (t % PERIOD) << (2 * c)
rows = C.shift_response(rows, shift)
rows += [dict() for _ in range(32)]
out.write_text(''.join(f"{(r.get('response_seq', 0) << 5) | r.get('response_enable', 0):04x}\n" for r in rows))
print(f'resp shift {shift}: {len(rows)} edges, {sum(1 for r in rows if r.get("response_enable"))} response edges')
