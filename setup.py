from setuptools import setup

setup(
    name="amagi-cli",
    version="1.0.0",
    description="AstByte Lyra CLI chat client with agentic capabilities and Amagi logo",
    py_modules=["app", "styling", "spinner", "tools", "config"],
    install_requires=[
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "amagi=app:main",
        ],
    },
    python_requires=">=3.7",
)
