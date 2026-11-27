"""
Production-like pretix server for the k6, ZAP and Lighthouse runs.

pretix is normally deployed behind nginx (static files) and gunicorn (app).
gunicorn does not run on Windows, so this uses waitress (multi-threaded WSGI
server) and whitenoise for the compressed static files. pretix itself runs
unchanged with DEBUG off.

    cd src
    set PRETIX_CONFIG_FILE=tests/team/tawassul/performance/perf_pretix.cfg
    ../.venv/Scripts/python tests/team/tawassul/performance/perf_server.py
"""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pretix.settings")

from django.conf import settings  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402
from waitress import serve  # noqa: E402
from whitenoise import WhiteNoise  # noqa: E402

app = WhiteNoise(get_wsgi_application(), root=settings.STATIC_ROOT, prefix=settings.STATIC_URL)

if __name__ == "__main__":
    port = int(os.environ.get("PERF_PORT", "8000"))
    print(f"pretix perf server on http://0.0.0.0:{port} (threads=8, DEBUG={settings.DEBUG})", flush=True)
    serve(app, host="0.0.0.0", port=port, threads=8)
