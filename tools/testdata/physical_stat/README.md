Physical statistics regression provenance
=========================================

`s81_ctl_phw10.txt` and `s81_flat_reader.txt` are unmodified stat outputs from
EPYC1 unit `oth-ubuntu-1400030-1792063759`, collected from
`/srv/opentallas-scratch/codex/s81-field-produced-native-v1/mapped-TT/`.
The corresponding work directories are `ot_s81_pq_ctl_static_native-work` and
`ot_s81_pq_calendar_reader-work`. Original remote logs, mapped netlists, and
JSON reports were not modified. The correction JSON records original source,
netlist and report digests, old statistics and the corrected interpretation.
It conveys no new synthesis, timing, physical or source qualification.

`library_cell_metadata.json` contains the actual used-cell metadata extracted
from the original TT Liberty files. Original library paths and SHA256 digests
are recorded. All five original libraries were independently SHA256 matched
between the source host and this replay host. The no-semicolon area lines in
ASAP7 INVBUF are intentional and accepted by Yosys; ignoring them understated
area. The control's corrected area agrees with Yosys's full-precision hierarchy
area: 1829.017260 um2, 12930 primitive cells, 2936 sequential cells, zero macros.
The 2 preserved kreg submodule instances are already included in these totals.

`qwen_sram_pair.txt` is the unmodified committed output from
`results/rtl/qwen_code_pair_physical_20261005/stat.txt` at the parent of this
change. Its 20 actual SRAM cells have unknown area in the stat invocation;
they must remain visible, not be dropped or automatically declared macros.
`sram_pair_metadata.lib` contains actual identity/area/memory metadata excerpts
from those two macros' repository Liberty files, with original blob digests.
The tests separately exercise absence and explicit presence of those views.
The additional `sram_metadata.lib` is an actual SRAM metadata excerpt used with
an explicitly constructed two-instance table, not a new tool-run receipt.

Run without synthesis or external PDK dependencies:

    PYTHONPATH=tools python3 -m unittest tools/test_physical_stat.py -v
