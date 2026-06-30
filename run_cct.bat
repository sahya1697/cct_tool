@echo off
echo Starting CCT Pipeline...

cd /d %WORKSPACE%

if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate

pip install -r requirements.txt

python main.py data/sample_c_files/

if %ERRORLEVEL% neq 0 (
    echo CCT failed
    exit /b 1
)

echo CCT completed successfully