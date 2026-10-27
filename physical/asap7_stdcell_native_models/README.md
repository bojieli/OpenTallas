# Actual ASAP7 functional inputs for CDC elaboration

`asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib` is the verbatim local ASAP7 vendor file from
`~/.local/opentallas-pdk-asap7/lib/NLDM/`, SHA256
`fa92e6ab1481810602811b1eea54bc016a341f11fb5188d7512c026599adf038`.
The reviewed cell is `AND2x2_ASAP7_75t_R` (inputs A/B, output Y; vendor function `(A * B)`).

An opt-in `reviewed_gray_fifo_extensions.tech_cell_liberties` row declares its repository path,
this SHA256, and `cells: ["AND2x2_ASAP7_75t_R"]`. The CDC elaborator imports the actual Liberty
functions with Yosys `read_liberty` and removes all undeclared vendor masters before hierarchy
checking. It does not supply handwritten Verilog models, blackboxes, altered FIFO source, or
clock exceptions. Source hash changes, unknown masters and RTL redefinitions are refused.
The file is a keyed lint input and a gate archive dependency. Native synthesis and ORFS continue
using the actual physical standard-cell libraries; this functional elaboration does not qualify
physical closure or change any native census limit.
