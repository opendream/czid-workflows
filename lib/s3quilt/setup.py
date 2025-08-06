from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().strip().split("\n")

setup(
    name="s3quilt",
    version="2.0.0",
    author="CZ ID Team @ Chan Zuckerberg Initiative",
    author_email="idseqhelp@chanzuckerberg.com",
    description="Pure Python S3 chunk downloader for parallel access to large S3 objects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chanzuckerberg/czid-workflows",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    include_package_data=True,
    zip_safe=False,
)