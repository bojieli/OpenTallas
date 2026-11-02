include /OpenROAD-flow-scripts/flow/Makefile
.PHONY: hroot-place-only
hroot-place-only:
	$(OPENROAD_CMD) /work/place_only.tcl
