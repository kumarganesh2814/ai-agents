from setuptools import setup, find_packages

setup(
    name="devops_gpt",
    version="0.1.0",
    packages=find_packages(include=['devops_gpt', 'devops_gpt.*']),
    install_requires=[
        "openai>=1.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "aiohttp>=3.8.0",
        "requests>=2.31.0",
        "python-dotenv>=0.19.0",
        "prometheus-client>=0.16.0",
        "structlog>=22.1.0"
    ],
    python_requires='>=3.9',
)
