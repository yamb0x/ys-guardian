# built in imports
import os, c4d, sys

# global vars
directory = os.path.dirname(__file__)
PluginID = 1058910

# plugin imports
modules = os.path.join(directory, 'modules')
if modules not in sys.path:
    sys.path.append(modules)

import abc_retime

if __name__ == "__main__":
    # Find icon
    fn = os.path.join(directory, "res", "icon.png")

    bmp = c4d.bitmaps.BaseBitmap()
    if bmp is None:
        raise MemoryError("Failed to create a BaseBitmap.")

    if bmp.InitWith(fn)[0] != c4d.IMAGERESULT_OK:
        raise MemoryError("Failed to initialize the BaseBitmap.")

    # Register plugin
    c4d.plugins.RegisterTagPlugin(
        id=PluginID,
        str="Alembic Retime",
        g=abc_retime.abc_retime,
        description='abcretime',
        icon=bmp,
        info=c4d.TAG_EXPRESSION | c4d.TAG_VISIBLE
    )