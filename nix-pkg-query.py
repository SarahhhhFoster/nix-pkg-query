#!/usr/bin/env python3

import base64
import requests
import platform
import argparse

def get_system_arch():
    """
    Generate a Nix-compatible architecture string for the current system.
    
    Returns:
        str: Architecture string in the format '{cpu}-{os}', e.g., 'aarch64-darwin' or 'x86_64-linux'
    """
    machine = platform.machine().lower()
    system = platform.system().lower()
    
    # Map CPU architectures to Nix nomenclature
    cpu_map = {
        'x86_64': 'x86_64',
        'amd64': 'x86_64',
        'arm64': 'aarch64',
        'aarch64': 'aarch64',
    }
    
    cpu = cpu_map.get(machine, machine)
    
    # For Darwin and Linux, the platform.system() value already matches Nix's naming
    return f"{cpu}-{system}"

def generate_auth_token(username="aWVSALXpZv", password="X8gPHnzL52wFEekuxsfQ9cSh"):
    """
    Generate a Basic Authentication token for Elasticsearch requests.
    
    Args:
        username: The Elasticsearch username (default from the bundle.js)
        password: The Elasticsearch password (default from the bundle.js)
    
    Returns:
        str: The Basic Authentication token
    """
    credentials = f"{username}:{password}"
    token = base64.b64encode(credentials.encode()).decode()
    return f"Basic {token}"

def search_packages(query, channel="24.11", size=50, from_index=0, platform=None):
    """
    Search for NixOS packages using the Elasticsearch API.
    
    Args:
        query: The search query string
        channel: The NixOS channel to search in (default: "24.11")
        size: Maximum number of results to return
        from_index: Starting index for pagination
        platform: System platform to filter by (default: current system)
    
    Returns:
        dict: The search results from Elasticsearch
    """
    url = f"https://search.nixos.org/backend/latest-42-nixos-{channel}/_search"
    
    # Use current system architecture if not specified
    if platform is None:
        platform = get_system_arch()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": generate_auth_token()
    }
    
    payload = {
        "from": from_index,
        "size": size,
        "sort": [
            {
                "_score": "desc",
                "package_attr_name": "desc",
                "package_pversion": "desc"
            }
        ],
        "aggs": {
            "package_platforms": {
                "terms": {
                    "field": "package_platforms",
                    "size": 20
                }
            },
            "package_attr_set": {
                "terms": {
                    "field": "package_attr_set",
                    "size": 20
                }
            },
            "all": {
                "global": {},
                "aggregations": {
                    "package_platforms": {
                        "terms": {
                            "field": "package_platforms",
                            "size": 20
                        }
                    }
                }
            }
        },
        "query": {
            "bool": {
                "filter": [
                    {
                        "term": {
                            "type": {
                                "value": "package",
                                "_name": "filter_packages"
                            }
                        }
                    },
                    {
                        "bool": {
                            "must": [
                                {"bool": {"should": [
                                    {
                                        "term": {
                                            "package_platforms": {
                                                "_name": f"filter_bucket_package_platforms",
                                                "value": platform
                                            }
                                        }
                                    }
                                ]}}
                            ]
                        }
                    }
                ],
                "must": [
                    {
                        "dis_max": {
                            "tie_breaker": 0.7,
                            "queries": [
                                {
                                    "multi_match": {
                                        "type": "cross_fields",
                                        "query": query,
                                        "analyzer": "whitespace",
                                        "auto_generate_synonyms_phrase_query": False,
                                        "operator": "and",
                                        "_name": f"multi_match_{query}",
                                        "fields": [
                                            "package_attr_name^9",
                                            "package_attr_name.*^5.3999999999999995",
                                            "package_programs^9",
                                            "package_programs.*^5.3999999999999995",
                                            "package_pname^6",
                                            "package_pname.*^3.5999999999999996",
                                            "package_description^1.3",
                                            "package_description.*^0.78",
                                            "package_longDescription^1",
                                            "package_longDescription.*^0.6",
                                            "flake_name^0.5",
                                            "flake_name.*^0.3"
                                        ]
                                    }
                                },
                                {
                                    "wildcard": {
                                        "package_attr_name": {
                                            "value": f"*{query}*",
                                            "case_insensitive": True
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def print_results_table(results):
    """
    Print search results as a formatted table with package names, versions, and descriptions.
    
    Args:
        results: The search results dictionary returned by search_packages()
    """
    hits = results.get('hits', {}).get('hits', [])
    total_count = results.get('hits', {}).get('total', {}).get('value', 0)
    
    if not hits:
        print("No packages found.")
        return
    
    # Find the longest package name for formatting
    max_name_length = max(len(hit.get('_source', {}).get('package_attr_name', '')) for hit in hits)
    max_name_length = max(max_name_length, 15)  # Minimum width for the name column
    
    # Find the longest version string for formatting
    max_version_length = max(len(hit.get('_source', {}).get('package_pversion', '')) for hit in hits)
    max_version_length = max(max_version_length, 10)  # Minimum width for the version column
    
    # Print header
    print(f"\nFound {total_count} packages:")
    print(f"{'Package Name':{max_name_length}} | {'Version':{max_version_length}} | Description")
    print(f"{'-' * max_name_length}-+-{'-' * max_version_length}-+-{'-' * 50}")
    
    # Print each package
    for hit in hits:
        source = hit.get('_source', {})
        name = source.get('package_attr_name', 'N/A')
        version = source.get('package_pversion', 'N/A')
        description = source.get('package_description', 'No description')
        if description == 'None':  # Handle cases where description is string 'None'
            description = 'No description'
        elif description is None:  # Handle cases where description is None
            description = 'No description'
        
        # Truncate description if too long
        if len(description) > 50:
            description = description[:47] + "..."
        
        print(f"{name:{max_name_length}} | {version:{max_version_length}} | {description}")
    
    # Print platform information
    arch = get_system_arch()
    print(f"\nResults filtered for platform: {arch}")

def main():
    parser = argparse.ArgumentParser(
        description='Search for NixOS packages using the search.nixos.org API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s python                    # Search for Python packages
  %(prog)s -a x86_64-linux vscode   # Search for VSCode on Linux
  %(prog)s -n 20 -p 2 gcc           # Show 20 results on page 2 for GCC
  %(prog)s --plain firefox          # Output just package names, one per line
        """
    )
    
    parser.add_argument('query', nargs='?', help='The search query')
    parser.add_argument('-a', '--arch', 
                       help='Target architecture (e.g., x86_64-linux, aarch64-darwin)')
    parser.add_argument('-n', '--num-results', type=int,
                       help='Number of results to display (max 50)')
    parser.add_argument('-p', '--page', type=int, default=1,
                       help='Page number for results')
    parser.add_argument('-c', '--channel', default="24.11",
                       help='NixOS channel to search (default: 24.11)')
    parser.add_argument('--plain', action='store_true',
                       help='Output only package names, one per line')
    
    args = parser.parse_args()
    
    # Show help if no query provided
    if args.query is None:
        parser.print_help()
        return
    
    # Set default number of results based on output mode
    if args.num_results is None:
        args.num_results = 1 if args.plain else 50
    
    # Validate and adjust arguments
    if args.num_results > 50:
        print("Warning: Number of results capped at 50")
        args.num_results = 50
    
    # Calculate from_index based on page number
    from_index = (args.page - 1) * args.num_results
    
    # Perform search
    results = search_packages(
        query=args.query,
        channel=args.channel,
        size=args.num_results,
        from_index=from_index,
        platform=args.arch
    )
    
    # Display results
    if args.plain:
        hits = results.get('hits', {}).get('hits', [])
        for hit in hits:
            name = hit.get('_source', {}).get('package_attr_name', '')
            if name:
                print(name)
    else:
        print_results_table(results)

if __name__ == "__main__":
    main()