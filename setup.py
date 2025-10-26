"""
setup.py
Helper script to set up the environment and run the pipeline.
"""
import os
import sys
import subprocess
import platform

def create_venv():
    """Create a virtual environment if it doesn't exist"""
    if os.path.exists("venv"):
        print("Virtual environment already exists.")
        return True
    
    print("Creating virtual environment...")
    try:
        # Use the appropriate python command based on the platform
        python_cmd = "python" if platform.system() == "Windows" else "python3"
        subprocess.run([python_cmd, "-m", "venv", "venv"], check=True)
        print("Virtual environment created successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        return False

def activate_venv():
    """Return the activation command for the virtual environment"""
    if platform.system() == "Windows":
        return os.path.join("venv", "Scripts", "activate")
    else:
        return f"source {os.path.join('venv', 'bin', 'activate')}"

def install_dependencies():
    """Install dependencies from requirements.txt"""
    print("Installing dependencies...")
    
    # Determine the pip command based on the platform
    if platform.system() == "Windows":
        pip_cmd = os.path.join("venv", "Scripts", "pip")
    else:
        pip_cmd = os.path.join("venv", "bin", "pip")
    
    try:
        # First try to install with SSL verification bypassed
        print("Attempting to install dependencies with SSL verification bypassed...")
        subprocess.run([
            pip_cmd, "install", "-r", "requirements.txt",
            "--trusted-host", "pypi.org",
            "--trusted-host", "pypi.python.org",
            "--trusted-host", "files.pythonhosted.org"
        ], check=True)
        print("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies with SSL verification bypassed: {e}")
        print("Trying standard installation method...")
        try:
            # Try standard installation as fallback
            subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
            print("Dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            return False

def setup_directories():
    """Create necessary directories for the pipeline"""
    print("Setting up directories...")
    dirs = ["data/raw", "data/processed", "data/checkpoints", "data/logs"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print("Directories created successfully.")

def print_instructions():
    """Print instructions for running the pipeline"""
    activate_cmd = activate_venv()
    
    print("\n" + "="*80)
    print("Setup Complete!")
    print("="*80)
    print("\nTo activate the virtual environment:")
    
    if platform.system() == "Windows":
        print(f"    {activate_cmd}")
    else:
        print(f"    {activate_cmd}")
    
    print("\nTo run the pipeline:")
    print("    python main.py")
    
    print("\nTo run the worker:")
    print("    python worker.py")
    
    print("\nTo deactivate the virtual environment when done:")
    print("    deactivate")
    print("="*80 + "\n")

def main():
    """Main function to set up the environment"""
    print("Setting up the Jira ETL Pipeline environment...")
    
    # Create virtual environment
    if not create_venv():
        print("Failed to create virtual environment. Exiting.")
        return 1
    
    # Install dependencies
    if not install_dependencies():
        print("Failed to install dependencies. Exiting.")
        return 1
    
    # Set up directories
    setup_directories()
    
    # Print instructions
    print_instructions()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
