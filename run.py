#!/usr/bin/env python
"""Entry point to run the FitAtAnyAge Flask application."""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fitAtAnyAge.app import app
from fitAtAnyAge.core import config

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=config.PORT, debug=config.DEBUG)
