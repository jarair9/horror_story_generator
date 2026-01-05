@echo off
echo Starting Horror Video Generator App...
call .venv\Scripts\activate
if %errorlevel% neq 0 (
    echo Virtual environment not found. Please ensure .venv exists.
    pause
    exit /b
)
streamlit run app.py
pause
