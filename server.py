#!/usr/bin/env python
"""
Railway entry point for the CAP application
"""
from app import app
import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))) 