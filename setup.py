"""Package configuration for fireflies-to-bear."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fireflies-to-bear",
    version="1.0.0",
    author="Chad Walters",
    author_email="chad.walters@gmail.com",
    description="A tool to process Fireflies.ai meeting PDFs and create Bear notes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chadwalters/firefliesTranscriptToBear",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Office Suites",
        "Topic :: Text Processing :: General",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: MacOS :: MacOS X",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyMuPDF==1.22.5",
        "watchdog==3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
            "psutil>=5.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fireflies-to-bear=fireflies_to_bear.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
