"""Connectivity-driven fixed layouts for the PORTFIX r4 gunit / bk_sel masters.

The pin tables and hard core views are unchanged. R0/MX/MY/R180 are LEF
orientations, not repinned variants. Apply before nonframe_hard_cores, then
regenerate station sites and latency from the connections in core_conns.
"""

PLACE = {'gunit': {'u_gunit.u_l5': (34.56, 34.56, 'MX'),
           'u_gunit.u_l1': (397.44, 34.56, 'MX'),
           'u_gunit.u_l1c': (760.32, 34.56, 'R0'),
           'u_gunit.u_l0': (864.0, 34.56, 'MX'),
           'u_gunit.u_l2': (1226.88, 34.56, 'MX'),
           'u_gunit.u_l3': (1589.76, 34.56, 'R0'),
           'u_gunit.u_l0r': (1952.64, 34.56, 'R0'),
           'u_gunit.u_l5f': (2142.72, 34.56, 'R0'),
           'u_gunit.u_l4r': (2315.52, 34.56, 'MY'),
           'u_gunit.u_l4': (2462.4, 34.56, 'R180')},
 'bk_sel': {'u_bk_sel.u_sel.g_q[0].u_q': (449.28, 34.56, 'R0'),
            'u_bk_sel.u_sel.g_q[1].u_q': (2013.12, 34.56, 'R0'),
            'u_bk_sel.u_sel.g_q[2].u_q': (1114.56, 544.32, 'MX'),
            'u_bk_sel.u_sel.g_q[3].u_q': (2678.4, 544.32, 'MX'),
            'u_bk_sel.u_tx': (3343.68, 34.56, 'R0'),
            'u_bk_sel.u_sel.u_c': (34.56, 518.4, 'R0'),
            'u_bk_sel.u_sel.u_g': (1779.84, 250.56, 'R0')}}

def apply(specs):
    for key, place in PLACE.items():
        specs[key]["place"] = place
        # Fixed face assignments were reviewed in this type frame; do not mirror
        # the complete shelf toward another corner and reverse boundary facing.
        specs[key]["mirrors"] = ((False, False),)
