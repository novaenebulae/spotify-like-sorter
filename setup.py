from setuptools import setup, find_packages

setup(
    name="spotify-like-sorter",
    version="1.0.0",
    description="Application de tri automatique des titres likés Spotify",
    author="Lucas",
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        # API & Web
        "spotipy",
        "requests",
        "requests-oauthlib",
        "aiohttp",
        "asyncio",

        # Database
        "sqlalchemy",
        "alembic",

        # Configuration
        "python-dotenv",
        "pydantic",
        "pydantic-settings",

        # Utilities
        "tqdm",
        "loguru",
        "PyYAML",

        # Data processing
        "numpy",
        "pandas",
        "pytz",

        # Cache
        "redis",

        # Dev tools
        "mypy",
        "pylint",
        "pytest",
        "six",
    ],
    entry_points={
        "console_scripts": [
            "spotify-sorter=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio",
    ],
)