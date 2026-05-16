from pathlib import Path
import runpy

def main():
    app_path = Path(__file__).with_name("app.py")
    runpy.run_path(str(app_path), run_name="__main__")

if __name__ == "__main__":
    main()
