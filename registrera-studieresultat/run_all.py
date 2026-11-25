"""Startar alla tjänster (Epok, StudentITS, Ladok, Canvas) och GUI:t i varsin process.

    python run_all.py                # starta allt
    python run_all.py --aterstall    # radera databaserna och skapa om dem från seed.sql

Varje tjänst kan också startas för sig, t.ex.:  python -m ladok.app
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request

import config

TJANSTER = [
    ("epok", "epok.app"),
    ("studentits", "studentits.app"),
    ("ladok", "ladok.app"),
    ("canvas", "canvas.app"),
    ("gui", "gui.app"),
]


def ar_igang(tjanst):
    try:
        with urllib.request.urlopen(f"{config.url(tjanst)}/health", timeout=1):
            return True
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--aterstall", action="store_true", help="radera databaserna och börja om")
    args = parser.parse_args()

    if args.aterstall and config.DATA_DIR.exists():
        shutil.rmtree(config.DATA_DIR)
        print("Databaserna raderades - skapas om från seed.sql.")

    miljo = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    processer = []
    try:
        for tjanst, modul in TJANSTER:
            processer.append(subprocess.Popen(
                [sys.executable, "-m", modul], cwd=config.BASE_DIR, env=miljo
            ))

        for tjanst, _ in TJANSTER:
            for _ in range(50):
                if ar_igang(tjanst):
                    break
                time.sleep(0.2)
            else:
                print(f"VARNING: {tjanst} svarade inte inom 10 sekunder.")

        print("\nAlla tjänster är igång:")
        for tjanst, _ in TJANSTER:
            print(f"  {tjanst:<11} {config.url(tjanst)}")
        print(f"\nÖppna gränssnittet: {config.url('gui')}")
        print("Avsluta med Ctrl+C.\n")

        while all(p.poll() is None for p in processer):
            time.sleep(1)
        print("En av tjänsterna avslutades oväntat - stänger ner allt.")
    except KeyboardInterrupt:
        print("\nStänger ner ...")
    finally:
        for p in processer:
            if p.poll() is None:
                p.terminate()
        for p in processer:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
