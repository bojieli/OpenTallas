#!/usr/bin/env python3
"""HEAD-RTL-4: worst copy-B burst-FIFO occupancy of ot_s81hd_mesh_ep_core after a lane-b replay (cycle model of the RTL).
Inputs: S = worst lane-b replay stall (edges by which the most-delayed copy-B record lands late), T = record spacing
contract (edges between own BEST frames).  Replay window: every record whose nominal copy-B landing falls inside the
stall is held by the link and delivered after it: N = floor(S / T) + 1.  Delivery after the stall is back to back at
the gearbox rate (3 flits / 4 edges: offsets 0,1,2,4,5,6,..).  Copy A keeps landing every T edges (any phase) and has
priority on the shared word port; the port decides one word per 2 edges (iss_q).  Occupancy = records held + landing
in flight (na + la), exactly the quantity the RTL compares with BQ.  Prints max over all copy-A phases."""
import sys
def occ(N, T, phase, H=400):
    barr = {}
    for k in range(N):
        barr[(4 * k) // 3 + (1 if (4 * k) % 3 else 0)] = 1   # 0,2,3,4,6,7,8 ... (ceil(4k/3)); 3 per 4 edges
    aarr = {t for t in range(-T + phase, H, T)}
    na = nb = 0; la = lb = 0; iss = 0; pk = 0
    for t in range(-20, H):
        # combinational decision this cycle (from registered state)
        dec = (not iss) and (na or nb); tka = dec and na; tkb = dec and not na
        pk = max(pk, nb + lb)
        nla = 1 if t in aarr else 0; nlb = barr.get(t, 0)
        na += la - (1 if tka else 0); nb += lb - (1 if tkb else 0)
        la, lb, iss = nla, nlb, 1 if dec else 0
    return pk
def bound(S, T):
    N = S // T + 1
    return N, max(occ(N, T, p) for p in range(T))
if __name__ == '__main__':
    S, T = int(sys.argv[1]), int(sys.argv[2])
    N, b = bound(S, T)
    print('S=%d T=%d replay_window_records N=%d worst_copyB_occupancy BQ=%d' % (S, T, N, b))
