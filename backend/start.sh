#!/bin/bash
cd /Users/rajatthakral/ai-data-platform/ai-data-platform
# source ../venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
