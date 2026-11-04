# TOK-VERIFY-1: HBM RE-FORM batch d44v part 1 (DIE-HBM-61/PLAN 5e3d43d9772, plan 99b63e3f2c55) vs d44w

- lat_d44v/: compiler LAT ABI (gen.py latency) for d44v = the schedule input (357 die lanes).
- price_d44w_d44v.json: reform_rebaseline.py --die hbm. 10 lanes, +18 lane-cycles, max +3:
  L730/L730m 44->47 (SFU ctl->b112, the max ctl->lane leg: +3 SFU), L35/L35m 8->10, L736/L736m 21->23 (fault/obs: 0),
  L12/L12s 13->14 (NW root->hub; NE already 14 since d44t: 0), L701 21->22, L96 21->22.
- tok/s (TOK-13d, A1 1676.95): d44t expected 1667.99 -> d44v expected 1666.44 (-0.09 %); cumulative bound 1660.66
  (L35/L96/L701 charged +2/+1/+1 on COLL/FUSED/SM, unmapped); tool bound for this delta alone 1668.06 vs A1.
- Token exact: UNCHECKED. HBM bind sets bound_stages = plan cycles, so the RTL follows the table by construction;
  the whole-die vehicle (SOURCE13, intel2) is still on the pre-d44v bind.

## Update 10:3x: d44v parts 1+2 (42cdf1fa3dc), lat_d44v regenerated from it
- 20 lanes +40 cyc: L730/m 44->51 (SFU ctl->lane max leg +7), L6/L6b/L6c(+m) 9->10 (IDX +1), L5/L34/L35(+m) +2, L12 NW +1 (off max), L736 obs, L701/L96 +1.
- corelat/: SFU split3 +4 declared (sfu_vm_*); hcol_h0/lanes8_11/mem 0. subtree32 +17 (DIE-HBM-61/RTL 241306abcdd) NOT in corelat.
- tok/s: lanes only 1664.25; + SFU +4 + subtree32 IDX +17 = 1660.13 expected; bound 1648.64 (A1 1676.95, d44t 1667.99).
