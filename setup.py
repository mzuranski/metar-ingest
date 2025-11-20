from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="metar-ingest",
    version="0.1.0",
    author="Your Name",
    description="METAR data ingestion system with PostgreSQL/PostGIS storage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/metar-ingest",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "metar>=1.11.0",
        "psycopg2-binary>=2.9.9",
        "python-daemon>=3.0.1",
        "pyyaml>=6.0.1",
        "metpy>=1.5.0",
        "sqlalchemy>=2.0.23",
        "geoalchemy2>=0.14.2",
        "influxdb-client>=1.38.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "metar-daemon=src.daemon:main",
            "metar-cleanup=src.cleanup:main",
        ],
    },
)