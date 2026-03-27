"""Allow running as: python -m chiark_mcp"""

import anyio
from chiark_mcp.server import main

anyio.run(main)
