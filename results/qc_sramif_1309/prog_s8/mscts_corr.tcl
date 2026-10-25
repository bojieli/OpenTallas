# Native routed SPEF minus fresh GRT estimate, same final DB; TT=max, FF=min.
# Used only for re-CTS structural balance; no routed timing or constraint modification.
set ot_ms_corr {
 Ehi {-23.8 -15.1}
 Elo {-3.1 0.6}
 SE {-6.6 -3.5}
 SW {-7.0 -4.9}
 Whi {27.0 22.4}
 Wlo {3.2 4.0}
}
set ot_ms_corr_mac {
 g_prog?0?.u_hi {1.6 2.7}
 g_prog?0?.u_lo {1.0 1.7}
 g_prog?1?.u_hi {30.0 25.2}
 g_prog?1?.u_lo {28.3 23.8}
}
