# Nix Package Search

A command-line tool for searching NixOS packages using the search.nixos.org API.

## Features

- Search for packages by name, description, or other attributes
- Filter results by architecture/platform
- Paginate through search results
- Display results in a formatted table or plain text
- Supports different NixOS channels

## Installation

Clone the repository and make the script executable:

```bash
git clone https://github.com/yourusername/nix-search.git
cd nix-search
chmod +x nix-pkg-query.py
```
## Usage
Basic usage:

```bash
./nix-pkg-query.py QUERY
 ```

### Options
- -a, --arch : Target architecture (e.g., x86_64-linux, aarch64-darwin)
- -n, --num-results : Number of results to display (max 50)
- -p, --page : Page number for results
- -c, --channel : NixOS channel to search (default: 24.11)
- --plain : Output only package names, one per line
### Examples
Search for Python packages:

```bash
./nix-pkg-query.py python
 ```

Search for VSCode on Linux:

```bash
./nix-pkg-query.py -a x86_64-linux vscode
 ```

Show 20 results on page 2 for GCC:

```bash
./nix-pkg-query.py -n 20 -p 2 gcc
 ```

Output just package names for Firefox:

```bash
./nix-pkg-query.py --plain firefox
 ```

## Integration with other tools
The plain output mode is useful for piping results to other commands:

```bash
# Install the first matching package
nix-env -iA nixpkgs.$(./nix-pkg-query.py --plain firefox)

# List all matching packages and select with fzf
./nix-pkg-query.py -n 50 --plain python | fzf | xargs -I{} nix-env -iA nixpkgs.{}
 ```

## How it works
This tool uses the same Elasticsearch API that powers the search.nixos.org website. It authenticates with the API, sends your search query, and formats the results for easy viewing in the terminal.
