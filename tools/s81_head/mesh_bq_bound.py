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
# HEAD-CORE-R17 2026-10-27 (COORD ruling 5 on HEAD-CORE-R15 / RULING HEAD-RTL-4: depth from the WORST-CASE replay stall of
# the PRODUCTION link protocol, max retries x replay length, not bench spacing).  ot_s81ph_link_ep_safe4 as instantiated by
# ot_s81ph_coll_lane_safe4 (dsfd_coll_lane_w_safe8_ntf, CH_BOARD 700, REACH 2; hd_mesh straps CH_B 2'b11 = board timeout
# on both lanes): RTTB = 2 CH_BOARD + TX_STAGES + 2 PIPE + RX_STAGES + 6, ATOB = RTTB + 2 KEEPALIVE + 32.  A sender with no
# ACK / NAK rewinds once per ATOB (timer reset at the rewind, TOREG at_lim registered) and declares the link fault
# (retry_exh) at the (MAX_RETRY + 1)-th rewind without progress, so the latest a record can still land is MAX_RETRY
# replays late: S = MAX_RETRY * ATOB (a NAK rewind comes after ~RTTB < ATOB, so it only shortens S).  Each later error
# episode restarts the retry count at progress and again holds at most the records sent within one S window.
# Window N = floor(S / T) + 1 at the minimum static position period T.  Common-mode worst case (the same stall on lane a):
# both bursts land on the same edges and copy A has priority on the word port (2 N edges), while copy B lands 3 per 4
# edges -> copy B holds its whole burst before its first read: BQ = N.  Bench: tb_s81hd_mesh_ep_burst.sv.
def protocol(T, ch_board=700, tx_stages=2, pipe=2, rx_stages=5, keepalive=16, max_retry=8):
    rttb = 2 * ch_board + tx_stages + 2 * pipe + rx_stages + 6
    atob = rttb + 2 * keepalive + 32
    S = max_retry * atob
    N = S // T + 1
    return dict(RTTB=rttb, ATOB=atob, S=S, N=N, BQ=N, margin_to_next_N=(N * T) - S)
if __name__ == '__main__':
    if sys.argv[1] == '--protocol':
        d = protocol(int(sys.argv[2]))
        print('T=%s ' % sys.argv[2] + ' '.join('%s=%s' % kv for kv in d.items()))
        sys.exit(0)
    S, T = int(sys.argv[1]), int(sys.argv[2])
    N, b = bound(S, T)
    print('S=%d T=%d replay_window_records N=%d worst_copyB_occupancy BQ=%d' % (S, T, N, b))
