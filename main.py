import os
import sys

from bdecode import bdecode
import torrent


def main() -> None:
    try:
        fn = sys.argv[1]
    except IndexError:
        print(f"Usage: {sys.argv[0]} filename.torrent\n")
        raise

    t = torrent.load(fn)
    t = torrent.files(t)
    print(t)
    # with open(fn, "rb") as fo:
    #     meta = bdecode(fo.read())
    #     if not isinstance(meta, dict):
    #         raise ValueError("invalid metadata")
    #     info = meta[b"info"]
    #     print(f"name: {info[b'name'].decode('utf-8')}")
    #     print("files:")
    #     for file in info[b"files"]:
    #         print("\t", os.path.join(*file[b"path"]).decode("utf-8"))


if __name__ == "__main__":
    main()
