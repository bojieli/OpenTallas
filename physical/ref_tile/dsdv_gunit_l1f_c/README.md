# dsdv_gunit_l1f_c: L1f contiguous routing plane

Measured predecessor GRT overflow471496(main)/271601(fallback), native32PASS. The two interior SRAMs blocked W input to E sort/gather routing; move both to E bank at x259.2, y43.2/84.288, leaving full-height W logic plane x0..248.4 and full-width upper/lower channels. Outline 388.8x302.4; same source, zero added edges. Existing protocol8PASS/router38/hc748 and causal MUT1FAIL40 retained in results/rtl/drives81_gunit_l1f_1020/gunit2. Composed parent must reserve the winner outline for each of its four L1f instances.

SAFE review before layout:
1 PASS registered input/output and reset landing2.
2 PASS outlineW388.8/H<=345.6 reach<=405um plan; source timing gate decides.
3 PASS exact source312cb42b6 mapped native max32/0violations, kept fences retained.
4 PASS same staged add/sort; one compare per stage.
5 WAIVED source SC112x32 flopstore static sparse write and simultaneous gather read (owner10/20 rulefreeze); no new storage.
6 FIXED E SRAM bank on43.2 X/Y except second stacked abuttedY84.288 (qualified macroheight41.088), full-height continuous W std plane, channel10.8 at pinface, fullfacepins, fill~38.0% routing-bound (newarea not squeezed); source std36915um2.
7 PASS same localclock region, entryS underneath logic x108..122.4, io_hold0.03; predecessor66.8/64.7ps; newspread gate judges.
8 PASS static schedule/router38/hc748 unchanged,0extra cycles.

No prior failure evidence overwritten. Plan/model: results/arch/s81_gunit_channels_1021/MODEL.json.
