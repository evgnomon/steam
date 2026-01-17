from invoke import task
import sass
from pathlib import Path


STATIC_DIR = Path(__file__).parent / "static"
SCSS_DIR = STATIC_DIR / "scss"
CSS_DIR = STATIC_DIR / "css"


@task
def scss(c):
    """Compile SCSS files to CSS."""
    CSS_DIR.mkdir(parents=True, exist_ok=True)

    for scss_file in SCSS_DIR.glob("*.scss"):
        if scss_file.name.startswith("_"):
            continue  # Skip partials
        css_content = sass.compile(filename=str(scss_file), output_style="compressed")
        css_file = CSS_DIR / scss_file.with_suffix(".css").name
        css_file.write_text(css_content)
        print(f"Compiled {scss_file.name} -> {css_file.name}")


@task
def watch(c):
    """Watch SCSS files and recompile on changes."""
    import time

    print("Watching for SCSS changes... (Ctrl+C to stop)")
    last_modified = {}

    while True:
        for scss_file in SCSS_DIR.glob("**/*.scss"):
            mtime = scss_file.stat().st_mtime
            if scss_file not in last_modified or last_modified[scss_file] != mtime:
                last_modified[scss_file] = mtime
                print(f"Change detected in {scss_file.name}")
                scss(c)
                break
        time.sleep(1)


@task
def clean(c):
    """Remove compiled CSS files."""
    for css_file in CSS_DIR.glob("*.css"):
        css_file.unlink()
        print(f"Removed {css_file.name}")
