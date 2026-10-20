# BTAB s4: write banks beside their SRAM faces

Authoritative failed predecessor: qfd_dv_s5_btab_s3-btab-s3-9dfddfa90, FLOORPLAN_MARGIN bank_distance, bank2 173.1um/bank3 167.3um versus100um maximum. Preserve its gate and failure; s3 is not admissible for adoption despite clock26.5/20.2ps and native32 PASS.

s4 is a new physical interface: tw_lo[511:0] on W feeds banks0/1 and tw_hi[511:0] on E feeds banks2/3. The electrical core receives exactly {tw_hi,tw_lo}; parent must map .tw_lo(tw_data[511:0]),.tw_hi(tw_data[1023:512]). Shared write enable/kind/address, read edges and all320FF remain unchanged. The full N capture band, centred clock and four43.2-lattice macro origins remain. Both512-bit ports must transfer the same logical1024-bit word on the same edge, without valid retiming, masks or partial-word handshakes.

Model: zero added data/reset/warmup edges; same16KiB SRAM,32B read/edge,128B write/edge. Four302.4x216 master positions unchanged. Split banks target<100um pin-centroid distance and<405um physical paths; actual gate measurement owed. Exact whole-word bench initializes all128rows with distinct row/lane signatures across all32 lanes, then random full-word writes/reads, comparing all256 output bits on every read edge. Real bank-select mutant must fail.

Pregate checklist MODEL: SRAM storage and registered SRAM/capture boundary unchanged; exact mapping and all-drivernative32 owed; reach and fullfacepintrack geometry owed; macros43.2grid/continuousNband planned; W539/E512writepins fitfull216umfaces <=6/um; outlineaspect1.4; samecentre-fedspine actualclockmeasure owed. No gate until exact5.050bench+mutant andmappedcensus PASS. No priorPNGapproval transferred to s4.
