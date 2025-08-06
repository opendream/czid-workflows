from setuptools import setup, find_packages
import os
import re


def get_version():
    """
    Get version without importing the package (avoids dependency issues during setup).
    
    Priority order:
    1. IDSEQ_DAG_VERSION environment variable
    2. BUILD_VERSION environment variable  
    3. PACKAGE_VERSION environment variable
    4. Git-based version (if available)
    5. Parse from __init__.py if imports work
    6. Default fallback version
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
        
        # Get git describe output
        result = subprocess.run(['git', 'describe', '--tags', '--always', '--dirty'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            git_version = result.stdout.strip()
            # Convert git describe to PEP 440 compliant version
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
    
    # Try to import version from the package as a last resort
    try:
        from idseq_dag import __version__
        # Validate that it's a proper version string, not EXTERNALLY_MANAGED
        if __version__ and __version__ != "EXTERNALLY_MANAGED" and re.match(r'^\d+\.\d+', __version__):
            return __version__
    except (ImportError, AttributeError):
        pass
    
    # Default fallback version (PEP 440 compliant)
    return "0.0.1.dev0"


__version__ = get_version()

setup(name='idseq_dag',
      version=__version__,
      description='executing a DAG for idseq pipeline',
      url='http://github.com/chanzuckerberg/idseq-dag',
      author='IdSeq Team @ Chan Zuckerberg Initiative',
      author_email='idseqhelp@chanzuckerberg.com',
      license='MIT',
      packages=find_packages(exclude=["tests.*", "tests"]),
      package_data={'idseq_dag': ['scripts/fastq-fasta-line-validation.awk']},
      install_requires=["pytz", "biopython"],
      extras_require={"test": ["coverage", "flake8", "wheel"]},
      dependency_links=[],
      entry_points={
          'console_scripts': [
              'idseq_dag = idseq_dag.__main__:main',
              'idseq-dag-run-step = idseq_dag.__main__:run_step',
          ]
      },
      zip_safe=False)
