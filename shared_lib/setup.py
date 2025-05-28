from setuptools import setup, find_packages

setup(
    name="shared-lib",                       # PyPI-safe package name
    version="0.1.0",                         # Semantic version
    author="Chiara Visca",
    author_email="",
    description="Shared utilities and schemas for Adaptive MFA System microservices",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(where="."),       # auto-detect shared_lib subpackage
    package_dir={"": "."},                   # root is package root
    include_package_data=True,               # include MANIFEST.in files
    install_requires=[                       # runtime dependencies
        "aio-pika>=8.0",
        "passlib>=1.7.4",
        "pika>=1.3.2",
        "pydantic>=2.11.4",
        "pydantic_settings>=2.9.1",
        "pyjwt>=2.10.1",
        "python_jose>=3.4.0",
        "redis>=5.2.1",
        "setuptools>=78.1.0",
        "sqlalchemy>=2.0.41",
        "asyncpg>=0.30.0",
        "email_validator>=2.2.0"
    ],
    python_requires=">=3.10",
)
