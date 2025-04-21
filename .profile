#!/bin/bash
# This file is used by some hosting platforms
echo "Starting from .profile file"
exec gunicorn app:app 