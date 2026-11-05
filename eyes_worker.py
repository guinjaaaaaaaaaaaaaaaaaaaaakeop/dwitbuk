"""Source-checkout entry point only: the eyes worker is plugin/eyes_worker.py, in the installed payload. No worker code lives here.

`python3 <checkout>/eyes_worker.py ...` runs plugin/eyes_worker.py as `__main__`, with plugin/ first on sys.path and this
checkout's root taken off it, exactly as `python3 <checkout>/plugin/eyes_worker.py ...` would. Imported as `eyes_worker` (a
checkout root on sys.path), it puts the payload's module in its own place in sys.modules, so every importer shares
one instance of the worker (and, through it, of the engine), never a second copy.
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
