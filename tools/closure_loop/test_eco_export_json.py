"""ECO re-export keeps export.json (drive-0849 2026-10-09): the default post-ECO view export writes abstract.json; collect
recipes copy view/export.json (mtp-seedproj a/b collect crashed twice), so the install aliases it."""
import unittest
from unittest.mock import patch

import closure_loop as cl


class EcoExportJson(unittest.TestCase):
    def test_alias(self):
        rb = "/R/routes/L/work/orfs/results/asap7/d/base"
        j = dict(name="j", run="/R", spec=dict(block="blk", hold_eco={}, verdict=dict(corner_sta="{RUN}/c.json", macros=[])),
                 eco=dict(rb=rb, ob=rb, out="/R/cl/eco"))
        with patch.object(cl, "subst", side_effect=lambda s, j: s.replace("{RUN}", "/R")):
            cmd = cl.eco_install_cmd(j)
        self.assertIn("hbm_fmax_attn_abstract.py", cmd)
        self.assertIn("cp /R/routes/L/view/abstract.json /R/routes/L/view/export.json", cmd)
        self.assertIn("[ -f /R/routes/L/view/export.json ] ||", cmd)


if __name__ == "__main__":
    unittest.main()
