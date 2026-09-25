import sys

from handcron.cli import CLI

if __name__ == "__main__":
    sys.exit(CLI().run(sys.argv[1:]))
