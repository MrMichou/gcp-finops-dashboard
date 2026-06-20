"""PyInstaller entry point for the standalone ``gcp-finops`` binary.

PyInstaller needs a concrete script to analyse; this just delegates to the
package's CLI ``main`` (the same callable behind the ``gcp-finops`` console
script and ``python -m gcp_finops_dashboard``).
"""

import sys

from gcp_finops_dashboard.cli import main

if __name__ == "__main__":
    sys.exit(main())
