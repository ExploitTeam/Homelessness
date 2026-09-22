import sys


def info(message: str):
    sys.stderr.write(f"\033[31mINFO:\033[0m {message}\n")
    sys.stderr.flush()