# drive-1443 aggressive variant: smaller gater clusters (24 sinks per clone) and place density 0.45
export OT_CG_K = 24
include /src/physical/hbm_ha2_fixedpins_20261007/cg/config.mk
export PLACE_DENSITY = 0.45
