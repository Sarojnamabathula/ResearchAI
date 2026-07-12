@echo off
title ResearchAI Backend
"C:\Users\JESSIE\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn researchai.backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
