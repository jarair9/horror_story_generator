@echo off
echo Starting Horror Video Generator Console...
call .venv\Scripts\activate
if %errorlevel% neq 0 (
    echo Virtual environment not found. Please ensure .venv exists.
    pause
    exit /b
)
python main.py
pause
