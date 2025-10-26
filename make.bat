@echo off
REM make.bat - Windows batch file equivalent of Makefile
REM This file provides convenient commands for common operations

REM Default Python interpreter
SET PYTHON=python

REM Default configuration file
SET CONFIG=config.json

REM Parse command-line arguments
IF "%1"=="" GOTO help
IF "%1"=="help" GOTO help
IF "%1"=="all" GOTO all
IF "%1"=="extract" GOTO extract
IF "%1"=="transform" GOTO transform
IF "%1"=="clean" GOTO clean
IF "%1"=="clean-project" GOTO clean-project
IF "%1"=="clean-all" GOTO clean-all
IF "%1"=="project" GOTO project
IF "%1"=="worker" GOTO worker
IF "%1"=="worker-hourly" GOTO worker-hourly
IF "%1"=="worker-interval" GOTO worker-interval
IF "%1"=="worker-background" GOTO worker-background
IF "%1"=="test" GOTO test
IF "%1"=="test-transformer" GOTO test-transformer
IF "%1"=="test-extract" GOTO test-extract
IF "%1"=="setup" GOTO setup

ECHO Unknown command: %1
GOTO help

:all
REM Run the full pipeline
%PYTHON% main.py
GOTO end

:extract
REM Run only the extraction phase
%PYTHON% main.py --extract
GOTO end

:transform
REM Run only the transformation phase
%PYTHON% main.py --transform
GOTO end

:clean
REM Clean checkpoint files and run the pipeline from scratch
%PYTHON% main.py --clean
GOTO end

:clean-project
REM Clean checkpoint files for a specific project
IF "%2"=="" (
    ECHO Error: PROJECT is not specified. Usage: make.bat clean-project HADOOP
    GOTO end
)
%PYTHON% main.py --clean --project %2
GOTO end

:clean-all
REM Clean all data directories (raw, processed, checkpoints)
ECHO Cleaning all data directories...
IF EXIST data\raw\* DEL /Q data\raw\*
IF EXIST data\processed\* DEL /Q data\processed\*
IF EXIST data\checkpoints\* DEL /Q data\checkpoints\*
ECHO Done.
GOTO end

:project
REM Run the pipeline for a specific project
IF "%2"=="" (
    ECHO Error: PROJECT is not specified. Usage: make.bat project HADOOP
    GOTO end
)
%PYTHON% main.py --project %2
GOTO end

:worker
REM Run the worker process with default settings (6 hours)
%PYTHON% worker.py
GOTO end

:worker-hourly
REM Run the worker process every hour
%PYTHON% worker.py --interval 1
GOTO end

:worker-interval
REM Run the worker process with a custom interval
IF "%2"=="" (
    ECHO Error: INTERVAL is not specified. Usage: make.bat worker-interval 12
    GOTO end
)
%PYTHON% worker.py --interval %2
GOTO end

:worker-background
REM Run the worker as a background process (Windows)
powershell -Command "Start-Process %PYTHON% -ArgumentList 'worker.py --interval 1' -WindowStyle Hidden"
ECHO Worker started in background with 1-hour interval. Check Task Manager for the Python process.
GOTO end

:test
REM Run all unit tests
%PYTHON% -m unittest discover -s tests
GOTO end

:test-transformer
REM Run transformer unit tests
%PYTHON% -m unittest tests/test_transformer.py
GOTO end

:test-extract
REM Run extract unit tests
%PYTHON% -m unittest tests/test_extract.py
GOTO end

:setup
REM Set up the project environment
ECHO Setting up project environment...
IF EXIST setup.bat (
    CALL setup.bat
) ELSE (
    %PYTHON% setup.py
)
GOTO end

:help
ECHO Apache Jira Scraper ETL Pipeline
ECHO.
ECHO Available commands:
ECHO   make.bat              Display this help information
ECHO   make.bat all          Run the full pipeline (extraction + transformation)
ECHO   make.bat extract      Run only the extraction phase
ECHO   make.bat transform    Run only the transformation phase
ECHO   make.bat clean        Clean checkpoint files and run the pipeline from scratch
ECHO   make.bat clean-project HADOOP  Clean checkpoint files for a specific project
ECHO   make.bat clean-all    Clean all data directories (raw, processed, checkpoints)
ECHO   make.bat project HADOOP  Run the pipeline for a specific project
ECHO   make.bat worker       Run the worker process with default settings (6 hours)
ECHO   make.bat worker-hourly Run the worker process every hour
ECHO   make.bat worker-interval 12  Run the worker process with a custom interval
ECHO   make.bat worker-background  Run the worker as a background process
ECHO   make.bat test         Run all unit tests
ECHO   make.bat test-transformer  Run transformer unit tests
ECHO   make.bat test-extract  Run extract unit tests
ECHO   make.bat setup        Set up the project environment
ECHO   make.bat help         Display this help information

:end
