import importlib.util
import inspect
import os
import sys
import shutil
import subprocess
import ast
import logging
import time
import platform
import toml
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def prompt_user():
    """Prompt user for the Python file path and class name."""
    path = input("Enter the path to the Python file containing the class: ").strip()
    class_name = input("Enter the class name to load: ").strip()
    return path, class_name

def ensure_venv(venv_dir=".venv"):
    """Create and validate a virtual environment using uv if it doesn't exist."""
    if not os.path.exists(venv_dir):
        logger.info(f"Creating virtual environment at {venv_dir} using uv...")
        try:
            result = subprocess.run(["uv", "venv", venv_dir], capture_output=True, text=True, check=True)
            logger.info(f"uv venv output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create virtual environment: {e}\nuv stderr: {e.stderr}")
            logger.error("Ensure uv is installed and up-to-date. Run 'uv --version' to check.")
            raise
        except FileNotFoundError:
            logger.error("uv is not installed or not in PATH. Install it using 'pip install uv' or follow instructions at https://github.com/astral-sh/uv")
            raise

    # Determine Python binary path
    python_bin = os.path.join(venv_dir, "Scripts" if os.name == "nt" else "bin", "python" + (".exe" if os.name == "nt" else ""))
    
    # Wait for the Python binary to appear (30-second timeout)
    timeout = 30
    for _ in range(timeout * 2):  # Check every 0.5 seconds
        if os.path.exists(python_bin):
            break
        time.sleep(0.5)
    else:
        logger.error(f"Python binary not found in venv at {python_bin} after {timeout} seconds")
        logger.error(f"System: {platform.system()} {platform.release()}, Python: {sys.version}")
        logger.error("Try deleting the .venv directory and running the script again.")
        raise RuntimeError(f"Python binary not found in venv at {python_bin}")

    # Validate the virtual environment
    try:
        result = subprocess.run([python_bin, "--version"], capture_output=True, text=True, check=True)
        logger.info(f"Virtual environment Python version: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Virtual environment at {venv_dir} is not functional: {e}\nstderr: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error(f"Python binary at {python_bin} is not executable")
        raise

    return os.path.abspath(venv_dir)

def get_imports_from_file(path):
    """Extract non-standard library imports from the Python file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        raise
    except SyntaxError as e:
        logger.error(f"Syntax error in file {path}: {e}")
        raise
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    # Standard library modules to exclude
    stdlib = {
        "os", "sys", "math", "re", "json", "typing", "logging", "collections", "itertools",
        "functools", "datetime", "time", "random", "copy", "subprocess", "shutil", "pathlib",
        "threading", "multiprocessing", "warnings", "ast", "inspect", "enum", "traceback",
        "unittest", "doctest", "pprint", "contextlib", "abc", "io", "csv", "glob", "tempfile",
        "types", "builtins", "platform"
    }
    return [imp for imp in imports if imp not in stdlib]

def update_pyproject_toml(packages, output_path="pyproject.toml"):
    """Update or create pyproject.toml with the specified dependencies."""
    # Default pyproject.toml template
    default_project_data = {
        "project": {
            "name": "MCP-maker",
            "version": "0.1.0",
            "description": "MCP-maker",
            "readme": "README.md",
            "requires-python": ">=3.12",
            "dependencies": []
        },
        "tool": {
            "uv": {}
        }
    }

    # Read existing pyproject.toml or use default
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                project_data = toml.load(f)
            logger.info(f"Found existing pyproject.toml at {output_path}")
        except Exception as e:
            logger.error(f"Failed to read pyproject.toml: {e}. Using default template.")
            project_data = default_project_data
    else:
        logger.info(f"No pyproject.toml found at {output_path}. Creating new one.")
        project_data = default_project_data

    # Ensure dependencies section exists
    if "project" not in project_data:
        project_data["project"] = {}
    if "dependencies" not in project_data["project"]:
        project_data["project"]["dependencies"] = []

    # Add new packages and mcp if not already present
    existing_deps = set(project_data["project"]["dependencies"])
    new_deps = set(packages) - existing_deps
    if "mcp" not in existing_deps:
        new_deps.add("mcp")
    if new_deps:
        project_data["project"]["dependencies"].extend(new_deps)
        logger.info(f"Added dependencies to pyproject.toml: {new_deps}")
    
    # Write updated pyproject.toml
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            toml.dump(project_data, f)
        logger.info(f"Updated pyproject.toml at {output_path}")
    except Exception as e:
        logger.error(f"Failed to update pyproject.toml: {e}")
        raise

def install_missing_packages(venv_dir, packages):
    """Install dependencies from pyproject.toml using uv sync, ignoring sklearn."""
    uv_bin = shutil.which("uv")
    if not uv_bin:
        logger.error("uv is not installed or not in PATH")
        raise RuntimeError("uv is not installed or not in PATH")

    # Filter out sklearn from packages
    filtered_packages = [pkg for pkg in packages if pkg.lower() != "sklearn"]
    if len(filtered_packages) < len(packages):
        logger.info("Ignoring 'sklearn' package as it is installed as 'scikit-learn'")

    # Update pyproject.toml with filtered packages
    update_pyproject_toml(filtered_packages)

    # Run uv sync to install dependencies
    logger.info(f"Installing dependencies from pyproject.toml using uv sync...")
    try:
        result = subprocess.run([uv_bin, "sync"], capture_output=True, text=True, check=True)
        logger.info(f"uv sync output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies with uv sync: {e}\nstderr: {e.stderr}")
        raise

def load_class_from_path(path, class_name, venv_dir):
    """Load the specified class from the Python file within the virtual environment."""
    python_bin = os.path.join(venv_dir, "Scripts" if os.name == "nt" else "bin", "python" + (".exe" if os.name == "nt" else ""))
    if python_bin not in sys.executable:
        logger.info("Restarting script inside the virtual environment...")
        os.execv(python_bin, [python_bin] + sys.argv)
    
    module_name = os.path.splitext(os.path.basename(path))[0]
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None:
            logger.error(f"Failed to create spec for module at {path}")
            raise RuntimeError(f"Failed to create spec for module at {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        cls = getattr(module, class_name, None)
        if cls is None:
            logger.error(f"Class '{class_name}' not found in {path}")
            raise AttributeError(f"Class '{class_name}' not found in {path}")
        return cls, module_name
    except Exception as e:
        logger.error(f"Failed to load class '{class_name}' from {path}: {e}")
        raise

def create_mcp_copy(path, class_name, module_name):
    """Create a new MCP-enabled Python file by appending MCP code at the end."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
            lines = source.splitlines()
    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        raise
    
    # Prepare new filename
    dir_name = os.path.dirname(path)
    base_name = os.path.basename(path)
    new_filename = os.path.join(dir_name, f"mcp-{base_name}")
    
    # Load class to get its methods
    cls, _ = load_class_from_path(path, class_name, ensure_venv())
    instance_name = "analyzer_instance"
    
    # Prepare MCP lines
    mcp_lines = [
        "",
        "",
        "from mcp.server.fastmcp import FastMCP",
        'mcp = FastMCP("MCP-Server")',
        f"{instance_name} = {class_name}()",
    ]
    for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith("_"):
            mcp_lines.append(f"mcp.add_tool({instance_name}.{name})")
    
    mcp_lines.extend([
        "",
        'if __name__ == "__main__":',
        '    print("Starting MCP Server...")',
        '    mcp.run()',
    ])
    
    # Append MCP lines at the end of the file
    new_lines = lines + mcp_lines
    
    try:
        with open(new_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        logger.info(f"Created MCP-enabled copy: {new_filename}")
    except Exception as e:
        logger.error(f"Failed to write MCP-enabled file {new_filename}: {e}")
        raise

def main():
    """Main function to orchestrate the process."""
    try:
        path, class_name = prompt_user()
        venv_dir = ensure_venv()
        imports = get_imports_from_file(path)
        if imports:
            logger.info(f"Detected non-standard packages: {imports}")
            install_missing_packages(venv_dir, imports)
        else:
            logger.info("No non-standard packages detected in the file")
        cls, module_name = load_class_from_path(path, class_name, venv_dir)
        create_mcp_copy(path, class_name, module_name)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()