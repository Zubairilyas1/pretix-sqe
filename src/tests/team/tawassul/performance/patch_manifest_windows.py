r"""
Windows-only workaround for the perf instance (not a pretix change).

pretix builds the JS-i18n static path with os.path.join, so on Windows it asks
the staticfiles manifest for 'jsi18n\en\djangojs.js', while collectstatic
stores 'jsi18n/en/djangojs.js'. pretix is deployed on Linux, where both are the
same. This adds backslash aliases to the manifest so the production-like
server can render pages. Run after collectstatic/compress.
"""
import json
import sys
from pathlib import Path

manifest = Path(sys.argv[1] if len(sys.argv) > 1 else "pretix/static.dist/staticfiles.json")
data = json.loads(manifest.read_text("utf-8"))
paths = data["paths"]
added = {k.replace("/", "\\"): v for k, v in paths.items() if k.startswith("jsi18n/")}
paths.update(added)
manifest.write_text(json.dumps(data), "utf-8")
print(f"added {len(added)} backslash aliases to {manifest}")
