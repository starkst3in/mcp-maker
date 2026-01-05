# MCP Generator

This repository contains `mcp_generator.py`, a Python script that automates the creation of a FastMCP-enabled (Model Context Protocol) STDIO server of a Python file containing MCP functions. It sets up a virtual environment, installs dependencies, and adds MCP server code to expose the class’s methods as tools in an MCP server.

## Purpose

The script takes a Python file with a class containing your MCP functions and generates a new file (prefixed with `mcp-`) that includes code to run the class’s public methods as an MCP server. It ensures all dependencies are installed in a virtual environment and places the MCP code at the end of the file to avoid errors like referencing a class before it’s defined.

## Features

- Creates a virtual environment using `uv` (a fast Python package manager).
- Detects non-standard imports and installs them via `pyproject.toml`.
- Dynamically registers public class methods as MCP tools.
- Appends MCP server code at the end of the file for correct execution.

## Prerequisites

- **Python 3.12+**: Required as specified in `pyproject.toml`.
- **uv**: Install with `pip install uv` for virtual environment and dependency management.
- **toml**: Install with `pip install toml` for parsing `pyproject.toml`.
- **Input File**: A Python file with valid syntax and a class containing public methods.
- **MCP Package**: Ensure the `mcp` package is available on PyPI or a configured index.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/starkst3in/mcp-maker.git
   cd mcp-maker
   ```

2. Install `uv` and `toml` globally:
   ```bash
   pip install uv toml
   ```

3. Ensure a `pyproject.toml` file exists in the repository root containing the dependancy 'toml'. This is required to run the `mcp_generator.py`code.

   ```toml
   [project]
   name = "MCP-maker"
   version = "0.1.0"
   description = "MCP-maker"
   readme = "README.md"
   requires-python = ">=3.12"
   dependencies = ["toml>=0.10.2"]
   [tool.uv]
   ```

## Usage

1. Run the script:
   ```bash
   python mcp_generator.py
   ```

2. When prompted, provide:
   - **Path to the Python file**: E.g., `C:\Users\<user-name>\Desktop\sample.py`.
   - **Class name**: E.g., `Class-Name`.

3. The script will:
   - Create a virtual environment in `.venv` if it doesn’t exist.
   - Detect non-standard imports (e.g., `numpy`, `pandas`) and update `pyproject.toml`.
   - Install dependencies using `uv sync`.
   - Generate a new file (e.g., `mcp-file-name.py`) with MCP server code appended.

4. Run the generated file to start the MCP server.

## How It Works

1. **Prompts for Input**: Asks for the Python file path and class name.
2. **Sets Up Virtual Environment**: Uses `uv` to create `.venv` and validates it.
3. **Detects Dependencies**: Parses the input file for non-standard imports, excluding `sklearn`.
4. **Installs Dependencies**: Updates `pyproject.toml` and runs `uv sync`.
5. **Loads the Class**: Dynamically loads the class to inspect its public methods.
6. **Generates MCP File**: Copies the original file, appends MCP code (import, server setup, method registration, and run command) at the end, and saves it as `mcp-<filename>.py`.

### Example Output

For `sample.py` with class `SampleClass`, the script creates `mcp-sample.py`, adding at the end:
```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("MCP-Server")
analyzer_instance = SampleClass()
mcp.add_tool(analyzer_instance.apply_somefunction)
# ... other methods ...
if __name__ == "__main__":
    print("Starting MCP Server...")
    mcp.run()
```

## Troubleshooting

- **MCP Code Placement**: Verify the MCP code is at the end of the generated file. If not, check the input file for syntax issues.
- **Dependency Errors**: Ensure `pyproject.toml` lists all required packages. Run `uv sync` manually in `.venv` if needed.
- **Virtual Environment Issues**: Delete `.venv` (`rm -rf .venv` or `rd /s /q .venv`) and retry.
- **Permissions**: Ensure write access to the directory.

## License

[MIT License](LICENSE) (or specify your preferred license).

## Contributing

Feel free to open issues or submit pull requests for improvements or bug fixes.
