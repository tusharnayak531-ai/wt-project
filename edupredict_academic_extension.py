"""Add the Academic Intelligence workspace behind EduPredict login."""
from pathlib import Path
from urllib.parse import urlsplit
import edupredict_auth as auth

ROOT = Path(__file__).resolve().parent
BASE_HANDLER_FACTORY = auth.handle_session

NAV_LINK = (
    '<a href="/academic" aria-label="Open academic intelligence dashboard" '
    'style="position:fixed;bottom:16px;right:135px;z-index:10000;'
    'background:#18274c;color:#e8ddff;border:1px solid #9783ef;'
    'border-radius:12px;padding:11px 16px;text-decoration:none;'
    'font:600 13px system-ui;box-shadow:0 5px 20px #06132680">'
    'Academic dashboard ↗</a>'
)

def academic_handler_factory(service):
    parent = BASE_HANDLER_FACTORY(service)

    class AcademicHandler(parent):
        def do_GET(self):
            route = urlsplit(self.path).path
            paths = {
                "/academic": ("edupredict_academic.html", "text/html; charset=utf-8"),
                "/academic.css": ("edupredict_academic.css", "text/css; charset=utf-8"),
                "/academic.js": ("edupredict_academic.js", "text/javascript; charset=utf-8"),
            }
            if route in paths:
                if not self._session_is_valid():
                    return self._redirect("/login")
                filename, content_type = paths[route]
                payload = (ROOT / filename).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(payload)
                return
            return super().do_GET()

    return AcademicHandler

auth.handle_session = academic_handler_factory
auth.LOGOUT_BUTTON += NAV_LINK

if __name__ == "__main__":
    auth.main()
