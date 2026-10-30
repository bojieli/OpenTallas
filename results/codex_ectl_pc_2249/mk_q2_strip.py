from pathlib import Path

r = Path('/srv/opentallas-scratch2/claude/codex-ectl-pc-2249/q2_stripchain')
s = (r / 'strip_feed_source.tcl').read_text()
s = s.replace('ot_sf_${side}', 'ot_sf_${sf_prefix}_${side}')
s = s.replace('set sf_mode [sf_env OT_SF_MODE sibling]', 'set sf_mode [sf_env OT_SF_MODE sibling]\nset sf_prefix [sf_env OT_SF_PREFIX strip]')
s = s.replace('global sf_b sf_u sf_x0 sf_y0 sf_x1 sf_y1 sf_mode sf_master sf_leaf sf_bad sf_mid sf_plevel sf_gone', 'global sf_b sf_u sf_x0 sf_y0 sf_x1 sf_y1 sf_mode sf_master sf_leaf sf_bad sf_mid sf_plevel sf_gone sf_prefix')
(r / 'strip_feed_kernel.tcl').write_text(s)
wrap = '''# Fixed macro-shadow strips; geometry only, same buffer depth, no timing inputs or pads.
proc q2_strip_apply {tag rect west east wtop etop} {
 global env sf_prefix
 set env(OT_SF_PREFIX) $tag
 set env(OT_SF_MODE) chain
 set env(OT_SF_RECT) $rect
 set env(OT_SF_W_XY) $west
 set env(OT_SF_E_XY) $east
 set env(OT_SF_WTOP_XY) $wtop
 set env(OT_SF_ETOP_XY) $etop
 source /work/strip_feed_kernel.tcl
}
q2_strip_apply L {15.12 4.32 109.944 13.26} {11.34 9.45} {113.4 9.45} {11.34 57.24} {113.4 57.24}
q2_strip_apply R {133.488 4.32 228.312 13.26} {129.168 9.45} {230.472 9.45} {129.168 57.24} {230.472 57.24}
'''
(r / 'strip_feed_both.tcl').write_text(wrap)
p = r / 'post_cts_setup.tcl'
old = p.read_text()
assert 'strip_feed_both' not in old
p.write_text('source /work/strip_feed_both.tcl\n' + old)
