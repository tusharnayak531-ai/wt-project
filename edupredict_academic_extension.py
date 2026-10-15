"""Add the Academic Intelligence workspace behind EduPredict login."""
from pathlib import Path
from urllib.parse import urlsplit
import edupredict_auth as auth

ROOT = Path(__file__).resolve().parent
BASE_HANDLER_FACTORY = auth.handle_session

NAV_LINK = """
<style>
.edupredict-marks-cta {display:flex;justify-content:space-between;align-items:center;gap:20px;
 background:linear-gradient(112deg,#222953,#153d55);border:1px solid #7d80cb;
 border-radius:18px;padding:20px 23px;margin:0 0 22px;color:#f3f6ff;
 box-shadow:0 16px 38px rgba(0,0,0,.15)}
.edupredict-marks-cta h2 {font-size:21px;margin:2px 0 4px;color:#fff}
.edupredict-marks-cta p {margin:0;color:#bdcce5;font-size:13px}
.edupredict-marks-cta .marks-action {display:inline-block;white-space:nowrap;
 padding:13px 19px;border-radius:11px;background:#ab9aff;color:#0a1a38;
 font-weight:850;text-decoration:none;font-size:14px}
.edupredict-marks-cta .marks-action:hover {background:#d1c9ff}
.edupredict-marks-link {display:block!important;color:#e8dfff!important;background:#312f5f!important;
 border:1px solid #9583e6;border-radius:11px;padding:12px 14px;margin:9px 4px;font-weight:800!important;
 text-decoration:none;font-size:14px}
@media(max-width:750px){.edupredict-marks-cta{display:block;padding:17px;margin:0 0 17px}
.edupredict-marks-cta .marks-action{display:block;text-align:center;margin-top:13px}
.edupredict-marks-cta h2{font-size:18px}}
</style>
<script>
(function () {
  var sidebar = document.querySelector('.sidebar');
  if (sidebar && !document.getElementById('edupredict-marks-nav')) {
    var link = document.createElement('a');
    link.id='edupredict-marks-nav';
    link.href='/academic#marks';
    link.className='edupredict-marks-link';
    link.textContent='✎  ENTER MARKS / SGPA';
    var prediction = sidebar.querySelector('.nav-link');
    if (prediction) prediction.insertAdjacentElement('afterend',link);
    else sidebar.appendChild(link);
  }
  var content = document.querySelector('.content');
  if (content && !document.getElementById('edupredict-marks-banner')) {
    var banner = document.createElement('section');
    banner.id='edupredict-marks-banner';
    banner.className='edupredict-marks-cta';
    banner.innerHTML='<div><span style="letter-spacing:1.6px;color:#c6b5ff;font-size:10px;font-weight:850">ACADEMIC RECORDS</span>'+
      '<h2>Enter your subject marks manually</h2><p>Add CIE Theory, Mid-Sem, CIE Practical, ESE Theory and ESE Practical marks. Get SGPA &amp; CGPA automatically.</p></div>'+
      '<a class="marks-action" href="/academic#marks">✎ Enter Marks →</a>';
    content.insertBefore(banner,content.firstChild);
  }
})();
</script>
"""

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
