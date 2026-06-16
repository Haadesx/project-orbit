# SPDX-License-Identifier: MIT
"""Project Orbit — scan all your projects, see what needs attention, bridge data between them."""

from .scanner import scan_projects
from .priority import prioritize
from .dashboard import generate_dashboard
from .config import load_config, init_config

__version__ = "0.1.0"
