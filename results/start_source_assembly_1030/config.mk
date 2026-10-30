# SOURCE-ONLY native virtual START/RAW map, no floorplan or timing qualification.
export DESIGN_NICKNAME = codex_start_source
export DESIGN_NAME = ot_die_start_stages
export PLATFORM = asap7
export VERILOG_FILES = /work/start_source.sv /work/start_primitives.sv
export VERILOG_DEFINES = -DSYNTHESIS
export SDC_FILE = /work/constraint.sdc
export DIE_AREA = 0 0 100 100
export CORE_AREA = 4.32 4.32 95.68 95.68
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export SYNTH_ARGS = -noshare
export LEC_CHECK = 0
export CORNER = TC
export CORNERS = tc bc
export TC_LIB_FILES = $(TC_NLDM_LIB_FILES)
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)
