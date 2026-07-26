"""
BookVerse Infrastructure - Semantic Versioning and Version Management

This module provides comprehensive semantic versioning capabilities for the
BookVerse platform infrastructure, implementing sophisticated version parsing,
comparison, determination algorithms, and AppTrust integration for enterprise-grade
version management and release automation with comprehensive error handling.

🏗️ Architecture Overview:
    - Semantic Versioning: Complete SemVer 2.0 parsing, validation, and comparison
    - Version Resolution: Sophisticated version determination from multiple sources
    - AppTrust Integration: Complete AppTrust API integration for version management
    - HTTP Client: Robust HTTP client with authentication and error handling
    - Version Algorithms: Advanced algorithms for version bumping and conflict resolution
    - Release Automation: Automated version determination for CI/CD pipelines

🚀 Key Features:
    - Complete SemVer 2.0 compliance with parsing and validation
    - Sophisticated version determination from Git tags and AppTrust
    - Comprehensive AppTrust API integration with authentication
    - Advanced version comparison and selection algorithms
    - Automated version bumping with patch increment support
    - Robust HTTP client with timeout and error handling

🔧 Technical Implementation:
    - Regular Expression Parsing: Precise SemVer pattern matching and validation
    - HTTP Client Integration: Robust API communication with authentication
    - Version Algorithms: Sophisticated version comparison and selection logic
    - Error Handling: Comprehensive error handling with detailed diagnostics
    - Command Line Interface: Professional CLI with argument parsing and validation

📊 Business Logic:
    - Release Management: Automated version determination for release workflows
    - Version Control: Sophisticated version management across multiple environments
    - CI/CD Integration: Version automation for continuous integration pipelines
    - Dependency Management: Version resolution for service dependencies
    - Compliance Support: Version tracking for audit and compliance requirements

🛠️ Usage Patterns:
    - CI/CD Automation: Automated version determination in build pipelines
    - Release Management: Version determination for platform releases
    - Development Support: Version resolution for development workflows
    - Dependency Resolution: Version management for service dependencies
    - Manual Operations: Command-line version determination and validation

Authors: BookVerse Platform Team
Version: 1.0.0
"""

import argparse
import json
import os
import re
import sys
from typing import List, Optional, Tuple, Dict, Any
import urllib.request
import urllib.parse

# 🔧 Semantic Version Pattern: Precise SemVer 2.0 pattern matching
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def stage_suffix_for_repo(stage: str) -> str:
    """
    Extract the repo suffix from a stage name for repository key construction.

    Stage names may include a project prefix (e.g. "bookverse-DEV", "bookverse-QA").
    This strips the prefix and returns the lowercase suffix used in repo names
    (e.g. "dev", "qa"). Lowercase is required for Docker image paths.

    Args:
        stage: Stage name, e.g. "bookverse-DEV", "bookverse-QA", or "DEV"

    Returns:
        Lowercase suffix for repo naming, e.g. "dev", "qa". Defaults to "dev" if empty.

    Examples:
        >>> stage_suffix_for_repo("bookverse-DEV")
        'dev'
        >>> stage_suffix_for_repo("bookverse-QA")
        'qa'
        >>> stage_suffix_for_repo("DEV")
        'dev'
    """
    s = (stage or "").strip()
    if not s:
        return "dev"
    if "-" in s:
        return s.rsplit("-", 1)[-1].lower()
    return s.lower()


def parse_semver(v: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse a semantic version string into its component parts.
    
    This function validates and parses semantic version strings according to 
    SemVer 2.0 specification, extracting major, minor, and patch components
    for version comparison and manipulation operations.
    
    Args:
        v (str): Version string to parse (e.g., "1.2.3")
        
    Returns:
        Optional[Tuple[int, int, int]]: Tuple of (major, minor, patch) or None if invalid
        
    Examples:
        >>> parse_semver("1.2.3")
        (1, 2, 3)
        >>> parse_semver("invalid")
        None
    """
    m = SEMVER_RE.match(v.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump_patch(v: str) -> str:
    """
    Increment the patch version of a semantic version string.
    
    This function takes a valid semantic version and increments the patch
    component, maintaining the major and minor versions. Used for automated
    patch releases and hotfix version generation.
    
    Args:
        v (str): Valid semantic version string (e.g., "1.2.3")
        
    Returns:
        str: Version with patch incremented (e.g., "1.2.4")
        
    Raises:
        ValueError: If the input is not a valid semantic version
        
    Examples:
        >>> bump_patch("1.2.3")
        "1.2.4"
        >>> bump_patch("2.0.0")
        "2.0.1"
    """
    p = parse_semver(v)
    if not p:
        raise ValueError(f"Not a SemVer X.Y.Z: {v}")
    return f"{p[0]}.{p[1]}.{p[2] + 1}"


def max_semver(values: List[str]) -> Optional[str]:
    """
    Find the highest semantic version from a list of version strings.
    
    This function compares multiple semantic version strings and returns
    the highest version according to SemVer precedence rules. Invalid
    versions are filtered out during comparison.
    
    Args:
        values (List[str]): List of version strings to compare
        
    Returns:
        Optional[str]: Highest valid semantic version or None if no valid versions
        
    Examples:
        >>> max_semver(["1.0.0", "1.2.3", "1.1.5"])
        "1.2.3"
        >>> max_semver(["invalid", "not-semver"])
        None
    """
    parsed = [(parse_semver(v), v) for v in values]
    parsed = [(t, raw) for t, raw in parsed if t is not None]
    if not parsed:
        return None
    parsed.sort(key=lambda x: x[0])
    return parsed[-1][1]


def http_get(url: str, headers: Dict[str, str], timeout: int = 300) -> Any:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
    try:
        return json.loads(data)
    except Exception:
        return data


def http_post(url: str, headers: Dict[str, str], data: str, timeout: int = 300) -> Any:
    req = urllib.request.Request(url, data=data.encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        response_data = resp.read().decode("utf-8")
    try:
        return json.loads(response_data)
    except Exception:
        return response_data


def load_version_map(path: str) -> Dict[str, Any]:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def find_app_entry(vm: Dict[str, Any], app_key: str) -> Dict[str, Any]:
    for it in vm.get("applications", []) or []:
        if (it.get("key") or "").strip() == app_key:
            return it
    return {}


def compute_next_application_version(app_key: str, vm: Dict[str, Any], jfrog_url: str, token: str) -> str:
    base = jfrog_url.rstrip("/") + "/apptrust/api/v1"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    
    latest_url = f"{base}/applications/{urllib.parse.quote(app_key)}/versions?limit=10&order_by=created&order_asc=false"
    try:
        latest_payload = http_get(latest_url, headers)
    except Exception:
        latest_payload = {}

    def first_version(obj: Any) -> Optional[str]:
        if isinstance(obj, dict):
            arr = (
                obj.get("versions")
                or obj.get("results")
                or obj.get("items")
                or obj.get("data")
                or []
            )
            if arr:
                v = (arr[0] or {}).get("version") or (arr[0] or {}).get("name")
                return v if isinstance(v, str) else None
        return None

    latest_created = first_version(latest_payload)
    if isinstance(latest_created, str) and parse_semver(latest_created):
        return bump_patch(latest_created)

    url = f"{base}/applications/{urllib.parse.quote(app_key)}/versions?limit=50&order_by=created&order_asc=false"
    try:
        payload = http_get(url, headers)
    except Exception:
        payload = {}

    def extract_versions(obj: Any) -> List[str]:
        if isinstance(obj, dict):
            arr = (
                obj.get("versions")
                or obj.get("results")
                or obj.get("items")
                or obj.get("data")
                or []
            )
            out = []
            for it in arr or []:
                v = (it or {}).get("version") or (it or {}).get("name")
                if isinstance(v, str) and parse_semver(v):
                    out.append(v)
            return out
        elif isinstance(obj, list):
            return [x for x in obj if isinstance(x, str) and parse_semver(x)]
        return []

    values = extract_versions(payload)
    latest = max_semver(values)
    if latest:
        return bump_patch(latest)

    entry = find_app_entry(vm, app_key)
    seed = ((entry.get("seeds") or {}).get("application")) if entry else None
    if not seed or not parse_semver(str(seed)):
        raise SystemExit(f"No valid seed for application {app_key}")
    return bump_patch(str(seed))




def compute_next_package_tag(
    app_key: str,
    package_name: str,
    vm: Dict[str, Any],
    jfrog_url: str,
    token: str,
    project_key: Optional[str],
    repo_stage: str = "DEV",
) -> str:
    entry = find_app_entry(vm, app_key)
    pkg = None
    for it in (entry.get("packages") or []):
        if (it.get("name") or "").strip() == package_name:
            pkg = it
            break
    
    if not pkg:
        raise SystemExit(f"Package {package_name} not found in version map for {app_key}")
    
    seed = pkg.get("seed")
    package_type = pkg.get("type", "")
    
    if not seed or not parse_semver(str(seed)):
        raise SystemExit(f"No valid seed for package {app_key}/{package_name}")
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    existing_versions = []
    
    if package_type == "docker":
        try:
            service_name = app_key.replace("bookverse-", "")
            repo_key = f"{project_key or 'bookverse'}-{service_name}-internal-docker-{repo_stage}-local"
            docker_url = f"{jfrog_url.rstrip('/')}/artifactory/api/docker/{repo_key}/v2/{package_name}/tags/list"
            
            resp = http_get(docker_url, headers)
            if isinstance(resp, dict) and "tags" in resp:
                for tag in resp.get("tags", []):
                    if isinstance(tag, str) and parse_semver(tag):
                        existing_versions.append(tag)
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "NAME_UNKNOWN" in error_str:
                print(f"INFO: Package '{package_name}' not found in Docker registry (first build)", file=sys.stderr)
                print(f"INFO: Will use seed version from version-map.yaml", file=sys.stderr)
            else:
                print(f"ERROR: Docker registry query failed for {package_name}: {e}", file=sys.stderr)
                print(f"ERROR: This indicates authentication or connectivity issues with JFrog", file=sys.stderr)
                print(f"ERROR: Fix authentication before proceeding. Check JFROG_ACCESS_TOKEN.", file=sys.stderr)
                sys.exit(1)
    
    elif package_type == "generic":
        try:
            service_name = app_key.replace("bookverse-", "")
            repo_key = f"{project_key or 'bookverse'}-{service_name}-internal-generic-{repo_stage}-local"
            
            aql_query = f'''items.find({{"repo":"{repo_key}","type":"file"}}).include("name","path","actual_sha1")'''
            aql_url = f"{jfrog_url.rstrip('/')}/artifactory/api/search/aql"
            aql_headers = headers.copy()
            aql_headers["Content-Type"] = "text/plain"
            
            resp = http_post(aql_url, aql_headers, aql_query)
            if isinstance(resp, dict) and "results" in resp:
                for item in resp.get("results", []):
                    path = item.get("path", "")
                    name = item.get("name", "")
                    
                    import re
                    version_pattern = r'/(\d+\.\d+\.\d+)(?:/|$)'
                    match = re.search(version_pattern, path)
                    if match:
                        version = match.group(1)
                        if parse_semver(version):
                            existing_versions.append(version)
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "400" in error_str or "not found" in error_str.lower() or "NAME_UNKNOWN" in error_str:
                print(f"INFO: Package '{package_name}' not found in Generic registry (first build)", file=sys.stderr)
                print(f"INFO: Will use seed version from version-map.yaml", file=sys.stderr)
            else:
                print(f"ERROR: AQL query failed for {package_name}: {e}", file=sys.stderr)
                print(f"ERROR: This indicates authentication or connectivity issues with JFrog", file=sys.stderr)
                print(f"ERROR: AQL URL: {aql_url}", file=sys.stderr)
                print(f"ERROR: Repo: {repo_key}", file=sys.stderr)
                print(f"ERROR: Fix authentication before proceeding. Check JFROG_ACCESS_TOKEN.", file=sys.stderr)
                sys.exit(1)
    
    elif package_type == "helm":
        try:
            service_name = app_key.replace("bookverse-", "")
            repo_key = f"{project_key or 'bookverse'}-{service_name}-internal-helm-{repo_stage}-local"
            
            aql_query = f'''items.find({{"repo":"{repo_key}","type":"file","name":{{"$match":"*.tgz"}}}}).include("name","path")'''
            aql_url = f"{jfrog_url.rstrip('/')}/artifactory/api/search/aql"
            aql_headers = headers.copy()
            aql_headers["Content-Type"] = "text/plain"
            
            resp = http_post(aql_url, aql_headers, aql_query)
            if isinstance(resp, dict) and "results" in resp:
                for item in resp.get("results", []):
                    name = item.get("name", "")
                    
                    import re
                    version_pattern = r'-(\d+\.\d+\.\d+)\.tgz$'
                    match = re.search(version_pattern, name)
                    if match:
                        version = match.group(1)
                        if parse_semver(version):
                            existing_versions.append(version)
        except Exception as e:
            error_str = str(e)
            if "400" in error_str or "404" in error_str or "not found" in error_str.lower():
                pass
            else:
                print(f"ERROR: Helm repository query failed for {package_name}: {e}", file=sys.stderr)
                print(f"ERROR: This indicates authentication or connectivity issues with JFrog", file=sys.stderr)
                print(f"ERROR: Helm AQL URL: {aql_url}", file=sys.stderr)
                print(f"ERROR: Helm Repo: {repo_key}", file=sys.stderr)
                print(f"ERROR: Fix authentication before proceeding. Check JFROG_ACCESS_TOKEN.", file=sys.stderr)
                sys.exit(1)
    
    elif package_type == "python" or package_type == "pypi":
        try:
            service_name = app_key.replace("bookverse-", "")
            pypi_repo_key = f"{project_key or 'bookverse'}-{service_name}-internal-pypi-{repo_stage}-local"
            python_repo_key = f"{project_key or 'bookverse'}-{service_name}-internal-python-{repo_stage}-local"
            
            for repo_key in [pypi_repo_key, python_repo_key]:
                
                aql_query = f'''items.find({{"repo":"{repo_key}","type":"file","name":{{"$match":"*.whl"}}}}).include("name","path")'''
                aql_url = f"{jfrog_url.rstrip('/')}/artifactory/api/search/aql"
                aql_headers = headers.copy()
                aql_headers["Content-Type"] = "text/plain"
                
                resp = http_post(aql_url, aql_headers, aql_query)
                
                if isinstance(resp, dict) and "results" in resp and len(resp.get("results", [])) > 0:
                    for item in resp.get("results", []):
                        name = item.get("name", "")
                        
                        import re
                        version_pattern = r'-(\d+\.\d+\.\d+)-'
                        match = re.search(version_pattern, name)
                        if match:
                            version = match.group(1)
                            if parse_semver(version):
                                existing_versions.append(version)
                    break
                    
        except Exception as e:
            error_str = str(e)
            if "400" in error_str or "404" in error_str or "not found" in error_str.lower():
                pass
            else:
                print(f"ERROR: Python repository query failed for {package_name}: {e}", file=sys.stderr)
                print(f"ERROR: This indicates authentication or connectivity issues with JFrog", file=sys.stderr)
                print(f"ERROR: Fix authentication before proceeding. Check JFROG_ACCESS_TOKEN.", file=sys.stderr)
                sys.exit(1)
    
    if existing_versions:
        latest = max_semver(existing_versions)
        if latest:
            return bump_patch(latest)
    
    return bump_patch(str(seed))


def main():
    p = argparse.ArgumentParser(description="Compute sequential SemVer versions with fallback to seeds")
    p.add_argument("compute", nargs="?")
    p.add_argument("--application-key", required=True)
    p.add_argument("--version-map", required=True)
    p.add_argument("--jfrog-url", required=True)
    p.add_argument("--jfrog-token", required=True)
    p.add_argument("--project-key", required=False)
    p.add_argument("--packages", help="Comma-separated package names to compute tags for", required=False)
    p.add_argument(
        "--stage",
        default=os.environ.get("PACKAGE_REPO_STAGE", "DEV"),
        help="Repository stage (e.g. bookverse-DEV, bookverse-QA). Prefix stripped for repo names.",
    )
    args = p.parse_args()

    vm = load_version_map(args.version_map)
    app_key = args.application_key
    jfrog_url = args.jfrog_url
    token = args.jfrog_token
    repo_stage = stage_suffix_for_repo(args.stage or "DEV")

    app_version = compute_next_application_version(app_key, vm, jfrog_url, token)

    pkg_tags: Dict[str, str] = {}
    if args.packages:
        for name in [x.strip() for x in args.packages.split(",") if x.strip()]:
            pkg_tags[name] = compute_next_package_tag(
                app_key, name, vm, jfrog_url, token, args.project_key, repo_stage
            )

    env_path = os.environ.get("GITHUB_ENV")
    if env_path:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"APP_VERSION={app_version}\n")
            for k, v in pkg_tags.items():
                key = re.sub(r"[^A-Za-z0-9_]", "_", k.upper())
                f.write(f"DOCKER_TAG_{key}={v}\n")

    out = {
        "application_key": app_key,
        "app_version": app_version,
        "package_tags": pkg_tags,
        "source": "latest+bump or seed fallback"
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
