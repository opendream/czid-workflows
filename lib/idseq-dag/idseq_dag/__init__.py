''' idseq_dag '''

import os

def _get_version():
    """
    Get version from environment variables or fallback to default.
    
    Priority order:
    1. IDSEQ_DAG_VERSION environment variable
    2. BUILD_VERSION environment variable  
    3. PACKAGE_VERSION environment variable
    4. Git-based version (if available)
    5. Default fallback version
    """
    # Try environment variables first
    version = os.environ.get('IDSEQ_DAG_VERSION')
    if version:
        return version
        
    version = os.environ.get('BUILD_VERSION')
    if version:
        return version
        
    version = os.environ.get('PACKAGE_VERSION')
    if version:
        return version
    
    # Try to get version from git if available
    try:
        import subprocess
        import re
        
        # Get git describe output
        result = subprocess.run(['git', 'describe', '--tags', '--always', '--dirty'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            git_version = result.stdout.strip()
            # Convert git describe to PEP 440 compliant version
            # Examples: v1.2.3 -> 1.2.3, v1.2.3-4-g1234567 -> 1.2.3.dev4+g1234567
            if git_version:
                # Remove 'v' prefix if present
                if git_version.startswith('v'):
                    git_version = git_version[1:]
                
                # Handle git describe format: tag-commits-hash
                match = re.match(r'^(\d+\.\d+\.\d+)(?:-(\d+)-g([a-f0-9]+))?(-dirty)?$', git_version)
                if match:
                    base_version = match.group(1)
                    commits_ahead = match.group(2)
                    git_hash = match.group(3)
                    dirty = match.group(4)
                    
                    if commits_ahead:
                        version = f"{base_version}.dev{commits_ahead}"
                        if git_hash:
                            version += f"+g{git_hash}"
                    else:
                        version = base_version
                        
                    if dirty:
                        version += "+dirty"
                        
                    return version
                
                # If it doesn't match expected format, use as-is if it looks like a version
                if re.match(r'^\d+\.\d+\.\d+', git_version):
                    return git_version
    except (ImportError, subprocess.SubprocessError, FileNotFoundError, OSError):
        # Git not available or other error, continue to fallback
        pass
    
    # Default fallback version (PEP 440 compliant)
    return "0.0.1.dev0"

__version__ = _get_version()
