"""Terracotta-bird status mascot: a transparent, frameless, always-on-top web
view showing the bird + a small toast, driven by set_state() from the controller."""
from __future__ import annotations

import json

from PySide6.QtCore import QByteArray, QEvent, Qt, QTimer
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWebEngineWidgets import QWebEngineView

# ---- mascot SVG (from Tuffet-UI.html) ----
_BODY = """
<g class="tuffet-whole">
  <ellipse cx="50" cy="70" rx="27" ry="23" fill="#e87553"/>
  <ellipse cx="50" cy="77" rx="19" ry="13" fill="#f18d69" opacity=".62"/>
  <path class="tuffet-wing" d="M25 62c-7 8-7 18 0 24 9-5 12-13 8-22-2-4-5-5-8-2Z" fill="#b84e36"/>
  <path d="M72 68c9 3 13 9 12 17-7 0-13-4-17-11Z" fill="#b84e36" opacity=".96"/>
  <g class="tuffet-head">
    <circle cx="50" cy="43" r="21" fill="#e87553"/>
    <circle cx="37" cy="50" r="5" fill="#f8c8ad" opacity=".72"/>
    <g class="tuffet-crest">
      <path d="M40 25c1-10 6-14 10-6 1-11 7-12 9-2 6-5 8 0 2 10-8-3-14-3-21-2Z" fill="#b84e36"/>
    </g>
    <g class="tuffet-eye">
      <ellipse cx="45" cy="42" rx="3.2" ry="3.8" fill="#2f2927"/>
      <circle cx="46" cy="41" r="1" fill="#fffaf4"/>
    </g>
    <g class="tuffet-beak">
      <path d="M64 40l17 4-17 5Z" fill="#f2b75f"/>
      <path d="M64 44h14l-14 5Z" fill="#dfa045" opacity=".72"/>
    </g>
  </g>
  <g class="tuffet-feet" fill="#f2b75f">
    <ellipse cx="42" cy="92" rx="5" ry="2.4"/>
    <ellipse cx="57" cy="92" rx="5" ry="2.4"/>
  </g>
</g>"""

_ORBIT = """
<g class="processing-orbit" aria-hidden="true">
  <circle cx="50" cy="50" r="42" fill="none" stroke="#e87553" stroke-width="1.3" stroke-dasharray="2 7" opacity=".7"/>
  <circle cx="87" cy="49" r="3" fill="#f2b75f"/>
  <circle cx="22" cy="22" r="2.2" fill="#e87553"/>
</g>"""

_MASCOT_SVG = f'<svg viewBox="0 0 100 100" role="img" aria-label="Yapper">{_ORBIT}{_BODY}</svg>'
_ICON_SVG = f'<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">{_BODY}</svg>'

# size preset -> mascot px, toast font px, window (w, h)
SIZES = {
    "small":  {"mascot": 68,  "toast": 10.5, "win": (168, 138)},
    "medium": {"mascot": 92,  "toast": 12.0, "win": (198, 168)},
    "large":  {"mascot": 118, "toast": 13.0, "win": (226, 198)},
}

_CSS = """
  *{box-sizing:border-box;user-select:none;-webkit-user-select:none;-webkit-user-drag:none;}
  html,body{margin:0;background:transparent;overflow:hidden;cursor:grab;
    font-family:"Segoe UI",system-ui,-apple-system,sans-serif;}
  body:active{cursor:grabbing;}
  /* toast ABOVE the mascot; both docked to the bottom-right corner */
  #wrap{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;
    gap:8px;height:100vh;padding:8px 8px 14px;}
  .mascot-slot{--size:__MASCOT__px;width:var(--size);height:var(--size);display:grid;place-items:center;color:#e87553;}
  .mascot-slot svg{width:100%;height:100%;overflow:visible;filter:drop-shadow(0 5px 9px rgba(77,50,38,.26));}
  .tuffet-whole{transform-origin:50px 91px}
  .tuffet-head{transform-origin:50px 52px}
  .tuffet-crest{transform-origin:50px 25px}
  .tuffet-wing{transform-origin:31px 65px}
  .tuffet-beak{transform-origin:69px 43px}
  .tuffet-eye{transform-origin:45px 43px}
  .tuffet-feet{transform-origin:50px 88px}
  .processing-orbit{opacity:0;transform-origin:center}
  [data-state="idle"] .tuffet-whole,[data-state="ready"] .tuffet-whole{animation:breathe 3.8s ease-in-out infinite}
  [data-state="idle"] .tuffet-eye,[data-state="ready"] .tuffet-eye{animation:blink 5.2s ease-in-out infinite}
  [data-state="loading"] .tuffet-whole,[data-state="wake"] .tuffet-whole{animation:wake 1.8s cubic-bezier(.2,.8,.2,1) infinite}
  [data-state="loading"] .tuffet-crest,[data-state="wake"] .tuffet-crest{animation:crest-alert 1.8s cubic-bezier(.2,.8,.2,1) infinite}
  [data-state="listening"] .tuffet-whole{animation:listen-bob 1.1s ease-in-out infinite}
  [data-state="listening"] .tuffet-crest{animation:crest-listen .9s ease-in-out infinite}
  [data-state="listening"] .tuffet-beak{animation:beak-talk .76s ease-in-out infinite}
  [data-state="listening"] .tuffet-wing{animation:wing .9s ease-in-out infinite}
  [data-state="processing"] .tuffet-whole{animation:think 1.7s ease-in-out infinite}
  [data-state="processing"] .tuffet-eye{transform:translate(1px,-2px)}
  [data-state="processing"] .processing-orbit{opacity:1;animation:orbit 2.4s linear infinite}
  [data-state="success"] .tuffet-whole{animation:success .8s cubic-bezier(.22,1.3,.36,1) infinite alternate}
  [data-state="error"] .tuffet-whole{animation:error-shake 1.25s ease-in-out infinite}
  [data-state="error"] .tuffet-crest{transform:translateY(4px) scaleY(.7)}
  @keyframes breathe{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-2px) scale(1.02,1.03)}}
  @keyframes blink{0%,91%,100%{transform:scaleY(1)}94%,97%{transform:scaleY(.08)}}
  @keyframes wake{0%,68%,100%{transform:translateY(0) scale(1)}12%{transform:translateY(3px) scale(1.02,.98)}26%{transform:translateY(-6px) scale(.99,1.03)}44%{transform:translateY(0) scale(1.02,.99)}}
  @keyframes crest-alert{0%,68%,100%{transform:scaleY(1)}20%,40%{transform:translateY(-4px) scaleY(1.34)}}
  @keyframes listen-bob{0%,100%{transform:translateY(0) rotate(-1deg)}50%{transform:translateY(-3px) rotate(1deg)}}
  @keyframes crest-listen{0%,100%{transform:translateY(-3px) scaleY(1.27) rotate(-2deg)}50%{transform:translateY(-5px) scaleY(1.4) rotate(2deg)}}
  @keyframes beak-talk{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.35)}}
  @keyframes wing{0%,100%{transform:rotate(0)}50%{transform:rotate(-9deg)}}
  @keyframes think{0%,100%{transform:rotate(-3deg) translateY(0)}50%{transform:rotate(4deg) translateY(-1px)}}
  @keyframes orbit{to{transform:rotate(360deg)}}
  @keyframes success{from{transform:translateY(0) scale(1)}to{transform:translateY(-3px) scale(1.02)}}
  @keyframes error-shake{0%,55%,100%{transform:translateX(0) rotate(0)}63%{transform:translateX(-3px) rotate(-2deg)}72%{transform:translateX(3px) rotate(2deg)}81%{transform:translateX(-2px) rotate(-1deg)}90%{transform:translateX(1px) rotate(1deg)}}
  @keyframes wave{0%,100%{transform:scaleY(.4);opacity:.6}50%{transform:scaleY(1);opacity:1}}
  .toast{display:none;align-items:center;gap:8px;padding:6px 12px 6px 10px;border-radius:999px;
    color:#fffaf4;background:#2f2927;box-shadow:0 10px 24px rgba(47,41,39,.28);
    font-size:__TOAST__px;font-weight:650;white-space:nowrap;}
  .toast.show{display:inline-flex}
  .toast[data-tone="light"]{color:#2f2927;background:rgba(255,250,244,.98)}
  .toast[data-tone="success"]{color:#fff;background:#2f7f61}
  .toast[data-tone="error"]{color:#fff;background:#9f4744}
  .wave{display:none;align-items:center;gap:2px;height:__WAVE__px}
  .wave.show{display:inline-flex}
  .wave i{width:2px;height:40%;border-radius:9px;background:currentColor;animation:wave .8s ease-in-out infinite}
  .wave i:nth-child(2){height:85%;animation-delay:-.55s}
  .wave i:nth-child(3){height:62%;animation-delay:-.3s}
  .wave i:nth-child(4){height:100%;animation-delay:-.65s}
"""

_BODY_HTML = """
  <div id="wrap">
    <div class="toast" id="toast"><span class="wave" id="wave"><i></i><i></i><i></i><i></i></span><span id="ttext"></span></div>
    <div class="mascot-slot" id="m" data-state="loading">__SVG__</div>
  </div>
  <script>
    const S = {
      loading:{toast:'Loading\\u2026',tone:'light'},
      idle:{toast:null},
      listening:{toast:'Listening\\u2026',tone:'dark',wave:true},
      processing:{toast:'Working\\u2026',tone:'light'},
      success:{toast:'Pasted',tone:'success'},
      error:{toast:"Didn't catch that",tone:'error'}
    };
    function _toast(text, tone, wave){
      const t=document.getElementById('toast'), w=document.getElementById('wave');
      if(text){ t.classList.add('show'); t.dataset.tone=tone||'dark';
        document.getElementById('ttext').textContent=text; w.classList.toggle('show', wave===true); }
      else { t.classList.remove('show'); w.classList.remove('show'); }
    }
    function setState(s){
      const meta=S[s]||S.idle; document.getElementById('m').dataset.state=s;
      _toast(meta.toast, meta.tone, meta.wave===true);
    }
    function setReady(text){ document.getElementById('m').dataset.state='ready'; _toast(text,'dark',false); }
    window.setState=setState; window.setReady=setReady;
  </script>
"""


def _build_page(mascot_px: float, toast_px: float) -> str:
    css = (_CSS.replace("__MASCOT__", str(mascot_px))
               .replace("__TOAST__", str(toast_px))
               .replace("__WAVE__", str(round(toast_px + 1))))
    body = _BODY_HTML.replace("__SVG__", _MASCOT_SVG)
    return f"<!doctype html><html><head><meta charset=\"utf-8\"><style>{css}</style></head><body>{body}</body></html>"


def mascot_icon(size: int = 64) -> QIcon:
    """Render the static mascot to a QIcon (tray / app icon)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    r = QSvgRenderer(QByteArray(_ICON_SVG.encode("utf-8")))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    r.render(p)
    p.end()
    return QIcon(pm)


# controller state -> tuffet state
_MAP = {"loading": "loading", "idle": "idle", "listening": "listening",
        "processing": "processing", "done": "success", "error": "error"}


class MascotWidget(QWebEngineView):
    def __init__(self, size: str = "medium", margin=(24, 56), pos=None, on_move=None):
        super().__init__(None)
        preset = SIZES.get(size, SIZES["medium"])
        self._margin = margin
        self._pos = pos                # saved top-left [x, y], or None to dock in the corner
        self._on_move = on_move        # callback(x, y) when the user finishes dragging
        self._drag = None
        self._fp = None
        self._pending = "loading"
        self._ready_text = None
        self._loaded = False

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.page().setBackgroundColor(Qt.transparent)
        self.resize(*preset["win"])

        self.loadFinished.connect(self._on_loaded)
        self.setHtml(_build_page(preset["mascot"], preset["toast"]))

    def _on_loaded(self, ok: bool):
        self._loaded = True
        if self._pending == "ready":
            self.show_ready(self._ready_text or "")
        else:
            self.set_state(self._pending)

    def set_state(self, controller_state: str) -> None:
        s = _MAP.get(controller_state, "idle")
        self._pending = controller_state
        if self._loaded:
            self.page().runJavaScript(f"window.setState && window.setState('{s}')")

    def show_ready(self, text: str) -> None:
        """First-run hint: mascot breathes (ready) with a persistent toast until first use."""
        self._pending = "ready"
        self._ready_text = text
        if self._loaded:
            self.page().runJavaScript(f"window.setReady && window.setReady({json.dumps(text)})")

    def dock(self) -> None:
        scr = self.screen().availableGeometry()
        mx, my = self._margin
        self.move(scr.right() - self.width() - mx, scr.bottom() - self.height() - my)

    def showEvent(self, e):
        super().showEvent(e)
        if self._pos and len(self._pos) == 2:
            self.move(int(self._pos[0]), int(self._pos[1]))
        else:
            self.dock()
        self._install_drag_filter()
        QTimer.singleShot(0, self._install_drag_filter)   # focusProxy may appear a tick later

    # ---- dragging (mouse events land on the web view's internal render widget) ----
    def _install_drag_filter(self):
        fp = self.focusProxy()
        if fp is not None and fp is not self._fp:
            fp.installEventFilter(self)
            self._fp = fp

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.Type.MouseButtonPress and ev.button() == Qt.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.pos()
        elif t == QEvent.Type.MouseMove and self._drag is not None and (ev.buttons() & Qt.LeftButton):
            self.move(ev.globalPosition().toPoint() - self._drag)
        elif t == QEvent.Type.MouseButtonRelease and self._drag is not None and ev.button() == Qt.LeftButton:
            self._drag = None
            p = self.pos()
            if self._on_move:
                self._on_move(p.x(), p.y())
        return super().eventFilter(obj, ev)
