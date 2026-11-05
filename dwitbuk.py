"""Source-checkout entry point only: the engine is plugin/dwitbuk.py, the installed payload. No engine code lives here.

`python3 <checkout>/dwitbuk.py ...` runs plugin/dwitbuk.py as `__main__`, with plugin/ first on sys.path and this
checkout's root taken off it, exactly as `python3 <checkout>/plugin/dwitbuk.py ...` would. Imported as `dwitbuk` (a
checkout root on sys.path), it puts the payload's module in its own place in sys.modules, so every importer shares
one instance of the engine, never a second copy.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_PAYLOAD = os.path.join(_ROOT, "plugin")
_FILE = os.path.join(_PAYLOAD, os.path.basename(__file__))

if __name__ == "__main__":
    import runpy
    sys.path[:] = [_PAYLOAD] + [p for p in sys.path if os.path.abspath(p or os.curdir) != _ROOT]
    runpy.run_path(_FILE, run_name="__main__")
else:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(__name__, _FILE)
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[__name__] = _module
    _spec.loader.exec_module(_module)
