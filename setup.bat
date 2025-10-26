@echo off
echo Setting up Jira ETL Pipeline environment...

REM Create virtual environment
if exist venv (
    echo Virtual environment already exists.
) else (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        exit /b 1
    )
    echo Virtual environment created successfully.
)

REM Activate virtual environment and install dependencies
echo Installing dependencies...
call venv\Scripts\activate

echo Attempting to install dependencies with SSL verification bypassed...
pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
if %errorlevel% neq 0 (
    echo Failed to install dependencies with SSL verification bypassed.
    echo Trying standard installation method...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Failed to install dependencies.
        exit /b 1
    )
)
echo Dependencies installed successfully.

REM Create necessary directories
echo Setting up directories...
if not exist data\raw mkdir data\raw
if not exist data\processed mkdir data\processed
if not exist data\checkpoints mkdir data\checkpoints
if not exist data\logs mkdir data\logs
echo Directories created successfully.

echo.
echo ================================================================================
echo Setup Complete!
echo ================================================================================
echo.
echo To activate the virtual environment:
echo     venv\Scripts\activate
echo.
echo To run the pipeline:
echo     python main.py
echo.
echo To run the worker:
echo     python worker.py
echo.
echo To deactivate the virtual environment when done:
echo     deactivate
echo ================================================================================
echo.

REM Keep the window open
pause
