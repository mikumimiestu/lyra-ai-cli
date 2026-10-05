from setuptools import setup

setup(
    name="amagi-cli",
    version="2.2.0",
    description="AstByte Lyra CLI chat client with memory, system time, background reminders, and agentic capabilities",

    py_modules=["app", "styling", "spinner", "tools", "config", "memory", "reminder"],

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
