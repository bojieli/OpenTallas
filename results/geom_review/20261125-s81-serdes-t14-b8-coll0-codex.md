# S81 SerDes t14 coll_o0 source geometry review

Viewed the exact B8 and 72da1c5dd1c8 type renders in E12 S81HEAD-TAPSPLIT/t14_b8_current_1125 and t14_b8_coll0_1125_scope. The CHN hard core stays at the B8 site. The second and third coll_o0 banks sit 34.56 and 75.60 µm further east toward the existing E output window. Their rank leg does not cross the CHN macro. The exact bank occupancy check covers all three 515-bit ranks and the independent coll_i0 banks. It found zero overlaps or macro intruders.

The 456.9 µm output reach violation clears in the source model. The largest modeled window hop is 403.6 µm and the two bit-matched bank hops top out at 352.512 and 353.808 µm. The older H2 placement used a different CHN seat and cannot supply native bins for this footprint. Scoped PRE and strict bind are running. The next physical action is placement-only to obtain matching sink geometry and check the actual station and routing access. Route remains held.
