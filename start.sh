#!/bin/bash
# Start script for Render deployment
gunicorn main:app -c gunicorn.conf.py
