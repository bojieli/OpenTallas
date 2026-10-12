# klayout -zz -rd tech_file= -rd in_def= -rd design_name= -rd in_files= -rd out_file= -r stream.py
# ORFS def2stream.py, except: only cells that have a GDS in in_files are cleared and replaced; macros without a GDS keep
# the LEF abstract geometry (pins/OBS) KLayout built when reading the DEF, so the stream is never silently empty there.
import pya
tech = pya.Technology()
tech.load(tech_file)  # noqa: F821
opts = tech.load_layout_options
lay = pya.Layout()
lay.read(in_def, opts)  # noqa: F821
top = lay.cell(design_name)  # noqa: F821
have = set()
for f in in_files.split():  # noqa: F821
    t = pya.Layout()
    t.read(f)
    have |= {c.name for c in t.each_cell()}
abstract = []
for c in lay.each_cell():
    if c.cell_index() == top.cell_index() or c.name.startswith("VIA_") or c.name.endswith("_DEF_FILL"):
        continue
    if c.name in have:
        c.clear()
    else:
        abstract.append(c.name)
for f in in_files.split():  # noqa: F821
    lay.read(f)
out = pya.Layout()
out.dbu = lay.dbu
o = out.create_cell(design_name)  # noqa: F821
o.copy_tree(lay.cell(design_name))  # noqa: F821
empty = [c.name for c in out.each_cell() if c.is_empty() and c.name != design_name]  # noqa: F821
out.write(out_file)  # noqa: F821
print("STREAM_ABSTRACT " + " ".join(sorted(set(abstract))))
print("STREAM_EMPTY " + " ".join(sorted(set(empty))))
print("STREAM_OK")
