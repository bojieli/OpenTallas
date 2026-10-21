# qfd_c_b16_fullkm -- CB16 parent FALLBACK (b) (QW-CB16REG 10-20): qfd_c_b16_fulln + cluster-root regional clock distribution

CRITICAL prefix qfd_c_b16: gate + coordinator review only (no REVIEW.json, no submit). A0 = STAND-IN (as fulln).
Same RTL / sites / fences / pins / SDC / PDN / outline / cycles as qfd_c_b16_fulln (see its README). ONE change:
pre_cts_extra tools/qwen_cluster/cb16_km/cb16_ckkm.tcl (buffers only):
- each region root ck_c<c>r<r>: register sinks -> K = clamp(N/500, 12, 40) k-means clusters, then any cluster wider than
  250 um (half-perimeter) bisected; one BUFx24 local root per cluster; hard-child clock pins stay on the port net;
- CTS -clk_nets = 16 ports + all cluster nets (one short tree per cluster);
- after CTS every cluster's latest arrival and every hard-child clock pin (+ recorded TT child insertion) measured in one
  STA pass; early groups padded (HB4xp67 coarse, BUFx2 fine) to the latest group of ALL 16 roots (aligned regions for the
  single-cycle landing-ring reads).
Why: fulln/fullnb/fullm one tree per root: within-region TT spread 410-813 ps, insertion 1.3-2.7 ns, post-CTS WNS
-1.4..-1.7 ns (scratch/qw-cb16r/ev_*). Same method on the A0 rc11 ODBs: 124-273 -> 27-37 ps.
Split smoke on the fulln 3_place.odb (ep9, openroad, fake CTS): 16 ports, 11.3k-20.9k register sinks -> 23-79 clusters,
max cluster half-perimeter <= 250 um (k-means alone left 25 sparse scalar clusters at 500-1488 um), 43-58 hard-child
clock pins per port, -clk_nets 16 + clusters.
## Safe-design checklist + pre-gate census: items 1-6, 8 unchanged from qfd_c_b16_fulln (in-flow census limit 32 re-run by
the gate). Item 7 Clock: FIXED as above (gate --cts measures per-root pin-flop spread TT/FF). 0 added cycles.
