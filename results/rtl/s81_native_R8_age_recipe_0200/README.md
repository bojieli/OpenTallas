# Literal R8 age recipe FAIL; scoped native diagnostic complete

The metadata-age recipe46/41/45/47 fails both original and current direct paths in the smallest existing selected native vehicle. Uniform41 remains PASS. This result does NOT call the asbuilt table wrong or replace its native/physical contract: applying metadata counts as plain positive-edge lane delays under this vehicle's unchanged clock/startup mapping breaks framing. A coherent actual clock+transport sampling relation is still required.

Exact staged source843 reconstructs u_s_0S.u_sl.$16.Y from native xg.xw_d. Packetbit1 (lane0) and bit567 (lane2) are two copies of THE SAME xw_d[0] valid. Native dsfd_cfifo_crs4 reconstructs oa_[0]/ob_[0] from them and explicitly faults on oa_[0]^ob_[0]. Uniform41 gives equal ages. Literal metadata delays give46 vs45, a one-edge split of the valid copies. Native ot_s81_land epoch checks depend only on the unchanged clocks/reset/K, so this data-only change exposes the bundle-valid XOR. Packetbits0/566 are released-reset bubble markers, not epochs; they are already stable before phase controls.

|case|captured Q GOs|partials|faults|result|
|---|---|---|---|---|
|uniform41 original/current|763/tag1,1787/tag3|4 literal gold partials at934/1958|all0|PASS|
|46/41/45/47 original/current|1787/tag1 only|2 wrong partials at1963|CFIFO1; XRT/XS/Q/CFG7=0|FAIL|
|wrong lane0+1 only|1787/tag1 only|2 wrong partials at1959|CFIFO1|control caught|

For the age recipe, actual MB0/MB1 words are bc1baa9b/ba3c2d48 instead of independent checkpoint gold bcf61f4b/bad48640. Original and current agree exactly even on the failing recipe: no GB-tag bug or repair is implied. Wrong-date and wrong-tag controls also fail their independent date/tag oracles. check.json PASS_NATIVE_R8_RECIPE_DIAGNOSTIC means the diagnostic and controls worked; the asbuilt_age_status fields are explicitly FAIL. No failed result overwritten.

Age semantics: the TB delays reconstructed native packet bits on the same positive-edge clk by41/45/46/47 before native CFIFO lane inputs. These are applied metadata transport counts, not absolute source→arithmetic consumer dates. All downstream real landing rings, CFG7/station/bank/GB captures stay unchanged. Core833ps; cr=cr_s=clk; every xk is the same forwarded fclk=clk&gate; gate opens on a negedge after CFIFO rs release; allK=2, LFACE0/LGATE0. Actual original per-lane forwarded-clock phases, reset epochs and physical clock sampling have NOT been reconstructed. alias_clock_scope.json records this explicit premise and source/consumer aliases.

Source and images are unchanged from the selected native mixed fixture77eadd758: actual rstopt_xo header producer,144 gathers, earlier held-checkpoint preload, actual0/106/0 calendar, independent OPTAG1/global broadcast history and checkpoint Q gold. Default transport_mode0 stays uniform41; opt-in mode1 is the age recipe; mode2 is a single-lane+1 control. No wholeframe build or production RTL source change. Hypothetical age-padding cost would be15*276=4140 packet FF including existing valid/marker bits, with source epochs, clock loads, reset and geometry unprepared; this FAIL gives no reason to adopt that cost.

Epyc2 normal8GB2T frontend unit1115239-1793613794 PASS102CPP/36193794B, backend/native unit1132881-1793613902 terminal0. Remote scratch2/claude/codex-ds-native-r8-0200; raw seven-case logs retained. No live own native component job remains. R8/provider/cohort/production flags remainfalse, BF arithmetic/all-lane payload and mission source epochs remain unqualified. Current global100within-lane/13replica holds are not relabeled or waived.
