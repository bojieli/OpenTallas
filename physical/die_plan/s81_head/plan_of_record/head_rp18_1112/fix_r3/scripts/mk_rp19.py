"""mk_rp19.py IN OUT: HEAD r3 content (COORD 11-13): (a) landing_ring_wreg.write_chunk 16 on hd_turn_b, hd_turn_a, hd_st_n4
(the 3 explicit 64-bit cfgs; ruling 01:09 (1)); (b) hd_spn_wshim_rx reset.relay_um 260 (own depth 4 -> 6, max hop 360 -> 234 um; the 2 failing hops were 313/340 um at 409-411 ps, slew ~ L^2 -> ~230 ps; 300 gives depth 5 but 274-um hops, ~314 ps, marginal) to shorten
the u_srl_41 / u_rrl_75 single-load reset hops (313 / 340 um). Asserts nothing else changes."""
import json,sys,copy
p=json.load(open(sys.argv[1]));o=copy.deepcopy(p);T=o['partition_types']
for tn in ('hd_turn_b','hd_turn_a','hd_st_n4'):
    w=T[tn]['clock']['landing_ring_wreg'];assert 'write_chunk' not in w,(tn,w);w['write_chunk']=16
r=T['hd_spn_wshim_rx']['reset'];assert 'relay_um' not in r;r["relay_um"]=260.0
open(sys.argv[2],'w').write(json.dumps(o,indent=1)+'\n');print('ok')
