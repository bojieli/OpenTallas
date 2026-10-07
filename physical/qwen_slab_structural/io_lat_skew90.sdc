# Sign-off form of io_lat_skew.sdc for the docker STA (tools/w18/corner_sta.py --post-sdc passes no environment): intra-region
# ports, OT_IO_SKEW 90 ps (65 measured region pair skew + 25), hold allowance OT_IO_HOLD_SKEW 50 ps (Claude decision 2026-10-06).
set ::env(OT_IO_SKEW) 90
set ::env(OT_IO_HOLD_SKEW) 50
source /src/physical/qwen_slab_structural/io_lat_skew.sdc
