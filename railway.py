#!/usr/bin/env python
"""
Railway-specific entry point for the CAP application
"""
from app import app

# This file is specifically named for Railway

if __name__ == "__main__":
    # Railway will provide PORT environment variable
    import os
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 