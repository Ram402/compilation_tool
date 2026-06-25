"""
VectorCAST — Homepage Dashboard
Ultra-premium futuristic UI with:
  • AI Core 3D centerpiece (multi-ring mechanical fusion, NOT a sphere/cube/cylinder)
  • Lamborghini 3D photo-projection car viewer (4-view perspective homography)
  • Particle field + neural-network lines background
  • Glassmorphism feature cards with neon hover
  • Animated hero with breathing camera effect
  • All alpha values clamped — zero Qt warnings
  • Stats strip removed from homepage
"""

import os, sys, platform, math, random, urllib.request, threading
import PySide6

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QLabel, QPushButton, QGridLayout, QSizePolicy,
    QGraphicsDropShadowEffect, QStackedWidget, QSplitter,
)
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QPoint
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QPixmap, QLinearGradient,
    QRadialGradient, QBrush, QTransform, QPolygonF, QPainterPath,
    QConicalGradient,
)

from ui.widgets import SectionBanner, SectionSep
from ui.style_helpers import UI_FONT, MONO_FONT, DISPLAY_FONT
from ui.car_viewer_360 import LuxuryCar360Viewer


# ── helpers ──────────────────────────────────────────────────────────────────
def _cl(v):          return max(0.0, min(1.0, float(v)))
def _a(c, a):
    q = QColor(c); q.setAlphaF(_cl(a)); return q
def _hex(s):         return QColor(s)
def _lerp(a, b, t):  return a + (b - a) * t

C_BG    = "#050816"
C_CYAN  = "#00F5FF"
C_PUR   = "#7B61FF"
C_MINT  = "#00FFB2"
C_RED   = "#ef4444"
C_GOLD  = "#FFD700"
C_WHT   = "#FFFFFF"
C_MUT   = "#A0AEC0"
C_STEEL = "#8892A4"

CYAN   = _hex(C_CYAN)
PUR    = _hex(C_PUR)
MINT   = _hex(C_MINT)
RED    = _hex(C_RED)
GOLD   = _hex(C_GOLD)
WHITE  = _hex(C_WHT)
MUTED  = _hex(C_MUT)


# ════════════════════════════════════════════════════════════════════════════
#  NEURAL PARTICLE FIELD  (background layer, transparent mouse passthrough)
# ════════════════════════════════════════════════════════════════════════════
class NeuralField(QWidget):
    """Animated particles + neural-network connection lines behind everything."""
    N_NODES   = 52
    MAX_DIST  = 0.18   # fraction of diagonal for connection

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._t = 0
        rng = random.Random(99)
        self._nodes = [
            {
                'x': rng.random(), 'y': rng.random(),
                'vx': (rng.random()-.5)*.00025, 'vy': (rng.random()-.5)*.00025,
                'r': rng.uniform(.9,2.2),
                'a0': rng.uniform(.12,.38),
                'ph': rng.uniform(0, math.pi*2),
                'col': rng.choice([CYAN, PUR, MINT]),
            }
            for _ in range(self.N_NODES)
        ]
        # A few bright fast streaks
        self._streaks = [
            {
                'x': rng.random(), 'y': rng.random(),
                'len': rng.uniform(.03,.09),
                'ang': rng.uniform(0,math.pi*2),
                'spd': rng.uniform(.00012,.00050),
                'a0': rng.uniform(.04,.12),
                'col': rng.choice([CYAN,PUR]),
            }
            for _ in range(9)
        ]
        QTimer(self, timeout=self._step, interval=38).start()

    def _step(self):
        self._t += 1
        for n in self._nodes:
            n['x'] = (n['x']+n['vx'])%1.0
            n['y'] = (n['y']+n['vy'])%1.0
        for s in self._streaks:
            s['x'] = (s['x']+math.cos(s['ang'])*s['spd'])%1.0
            s['y'] = (s['y']+math.sin(s['ang'])*s['spd'])%1.0
        self.update()

    def paintEvent(self, _):
        if self.width()<2: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        diag = math.hypot(w, h)
        t = self._t*.05

        # streaks
        for s in self._streaks:
            c = _a(s['col'], s['a0'])
            p.setPen(QPen(c, .8))
            sx,sy = s['x']*w, s['y']*h
            p.drawLine(QPointF(sx,sy),
                       QPointF(sx+math.cos(s['ang'])*s['len']*w,
                               sy+math.sin(s['ang'])*s['len']*h))

        # connections
        nodes = self._nodes
        for i, a in enumerate(nodes):
            ax,ay = a['x']*w, a['y']*h
            for b in nodes[i+1:]:
                bx,by = b['x']*w, b['y']*h
                d = math.hypot(ax-bx,ay-by)/diag
                if d < self.MAX_DIST:
                    alpha = _cl(.12*(1-d/self.MAX_DIST))
                    p.setPen(QPen(_a(CYAN, alpha), .6))
                    p.drawLine(QPointF(ax,ay), QPointF(bx,by))

        # nodes
        p.setPen(Qt.NoPen)
        for n in nodes:
            pulse = .5+.5*math.sin(t+n['ph'])
            a = _cl(n['a0']*(0.55+0.45*pulse))
            r = n['r']*(0.8+0.3*pulse)
            p.setBrush(_a(n['col'],a))
            p.drawEllipse(QPointF(n['x']*w, n['y']*h), r, r)


# ════════════════════════════════════════════════════════════════════════════
#  AI CORE  — the 3D centerpiece
#  Fusion of: floating metallic rings / mechanical segments / holographic
#  scanning layers / energy filaments / precision titanium architecture
# ════════════════════════════════════════════════════════════════════════════
class AiCore(QWidget):
    """
    Fully custom 3D AI Core rendered with QPainter.
    NOT a sphere, cube, cylinder or pyramid.
    Components:
      - 5 orbital metallic rings at varied tilts
      - Inner rotating mechanical iris (6 blades)
      - Central energy nexus (pulsing)
      - 4 quadrant arc segments (titanium brackets)
      - 3 holographic scan layers
      - Orbiting data fragments
      - Radial light channels (8)
      - Volumetric glow
      - Floating data filaments
    Mouse drag for manual rotation + inertia.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        # rotation state
        self._ry   = 0.0    # Y axis angle (main rotation)
        self._rx   = 0.18   # X axis tilt
        self._vy   = 0.008  # angular velocity Y
        self._vx   = 0.0
        self._drag = False
        self._last = None
        self._idle = 0      # ticks since last drag

        self._t = 0.0
        QTimer(self, timeout=self._tick, interval=16).start()

    # ── interaction ──────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button()==Qt.LeftButton:
            self._drag=True; self._last=e.position(); self._idle=0
    def mouseMoveEvent(self, e):
        if self._drag and self._last:
            dx = e.position().x()-self._last.x()
            dy = e.position().y()-self._last.y()
            self._vy = dx*.0045
            self._vx = dy*.0025
            self._ry += dx*.0045
            self._rx += dy*.0025
            self._rx  = _cl(self._rx,-0.6,0.6)
            self._last = e.position()
            self._idle = 0
    def mouseReleaseEvent(self, e):
        if e.button()==Qt.LeftButton:
            self._drag=False; self._last=None

    def _tick(self):
        self._t += 1
        self._idle += 1
        if not self._drag:
            # inertia decay
            self._vy = _lerp(self._vy, 0.008, 0.04)
            self._vx = _lerp(self._vx, 0.0,   0.06)
            self._ry += self._vy
            self._rx += self._vx
            self._rx  = _cl(self._rx,-0.6,0.6)
        # slight camera breathing
        self._rx = self._rx + math.sin(self._t*0.008)*0.0003
        self.update()

    # ── 3D projection ─────────────────────────────────────────────────────
    def _proj(self, x, y, z, cx, cy, cam=350, scale=1.0):
        """Project 3D point → 2D screen QPointF."""
        ry,rx = self._ry, self._rx
        # rotate Y
        x2  =  x*math.cos(ry)+z*math.sin(ry)
        z2  = -x*math.sin(ry)+z*math.cos(ry)
        # rotate X
        y2  =  y*math.cos(rx)-z2*math.sin(rx)
        z3  =  y*math.sin(rx)+z2*math.cos(rx)
        d = z3+cam
        if abs(d)<.1: d=.1
        s = cam/d*scale
        return QPointF(cx+x2*s, cy+y2*s), z3

    def _ring_pts(self, radius, n, tilt_x=0, tilt_z=0, phase=0):
        """Generate world-space points for a tilted ring."""
        pts=[]
        for i in range(n):
            a = 2*math.pi*i/n+phase
            x = math.cos(a)*radius
            y = math.sin(a)*radius*math.cos(tilt_x)+0
            z = math.sin(a)*radius*math.sin(tilt_x)
            # tilt around Z
            x2 = x*math.cos(tilt_z)-y*math.sin(tilt_z)
            y2 = x*math.sin(tilt_z)+y*math.cos(tilt_z)
            pts.append((x2,y2,z))
        return pts

    # ── paint ─────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p  = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        cx,cy = w/2, h/2
        t = self._t

        # ── Background ─────────────────────────────────────────────────
        p.fillRect(self.rect(), _hex(C_BG))

        # Volumetric outer glow
        for col,rad,alp in [(CYAN,220,.035),(PUR,180,.04),(MINT,130,.03)]:
            pulse = .85+.15*math.sin(t*.03+rad*.01)
            g = QRadialGradient(cx,cy,rad*pulse)
            g.setColorAt(0, _a(col,alp)); g.setColorAt(1,_a(col,0))
            p.fillRect(self.rect(),g)

        # ── Holographic grid floor ──────────────────────────────────────
        p.save()
        p.translate(cx,cy+80)
        grid_col = _a(CYAN,.04)
        p.setPen(QPen(grid_col,.5))
        for i in range(-5,6):
            p.drawLine(int(i*40),-50,int(i*20),80)
        for j in range(3):
            frac=j/3
            y=int(-50+frac*130)
            p.drawLine(int((-5+frac*2)*40),y,int((5-frac*2)*40),y)
        p.restore()

        # ── RADIAL LIGHT CHANNELS ──────────────────────────────────────
        p.save()
        p.translate(cx,cy)
        for i in range(8):
            a0 = self._ry+i*math.pi/4
            pulse_a = _cl(.18+.12*math.sin(t*.04+i*.7))
            g = QLinearGradient(0,0,
                                math.cos(a0)*170, math.sin(a0)*100)
            g.setColorAt(0,_a(CYAN,0)); g.setColorAt(.5,_a(CYAN,pulse_a))
            g.setColorAt(1,_a(CYAN,0))
            p.setPen(QPen(QBrush(g),1.0))
            p.drawLine(QPointF(math.cos(a0)*40, math.sin(a0)*40*.6),
                       QPointF(math.cos(a0)*165,math.sin(a0)*100))
        p.restore()

        # ── TITANIUM BRACKET ARCS (4 quadrant segments) ────────────────
        p.save()
        p.translate(cx,cy)
        for qi in range(4):
            base_a = self._ry + qi*math.pi/2
            a_start= math.degrees(base_a)+10
            a_span = 70
            r_out,r_in = 155,140
            # outer arc (gold titanium)
            pth = QPainterPath()
            pth.moveTo(r_out*math.cos(math.radians(a_start)),
                       r_out*math.sin(math.radians(a_start))*.6)
            for da in range(1,a_span+1):
                a=math.radians(a_start+da)
                pth.lineTo(r_out*math.cos(a),r_out*math.sin(a)*.6)
            pulse_b = _cl(.55+.20*math.sin(t*.025+qi*1.5))
            p.setPen(QPen(_a(GOLD, pulse_b),2.0))
            p.setBrush(Qt.NoBrush)
            p.drawPath(pth)
            # inner arc (cyan)
            pth2=QPainterPath()
            pth2.moveTo(r_in*math.cos(math.radians(a_start)),
                        r_in*math.sin(math.radians(a_start))*.6)
            for da in range(1,a_span+1):
                a=math.radians(a_start+da)
                pth2.lineTo(r_in*math.cos(a), r_in*math.sin(a)*.6)
            p.setPen(QPen(_a(CYAN,_cl(.3+.15*math.sin(t*.03+qi))), 1.0))
            p.drawPath(pth2)
            # bracket teeth (3 per quadrant)
            for ti in range(3):
                frac=(ti+1)/4
                a=math.radians(a_start+a_span*frac)
                x1=r_in*math.cos(a);  y1=r_in*math.sin(a)*.6
                x2=r_out*math.cos(a); y2=r_out*math.sin(a)*.6
                p.setPen(QPen(_a(GOLD,_cl(.4+.2*math.sin(t*.05+ti))),1.2))
                p.drawLine(QPointF(x1,y1),QPointF(x2,y2))
        p.restore()

        # ── FLOATING ORBITAL RINGS (5 rings, varied tilts) ─────────────
        ring_defs = [
            dict(r=130, tilt_x=math.pi*.15, tilt_z=0,           phase=t*.012,  col=CYAN,  lw=2.0, seg=96),
            dict(r=110, tilt_x=math.pi*.42, tilt_z=math.pi*.1,  phase=t*.018,  col=PUR,   lw=1.5, seg=80),
            dict(r= 95, tilt_x=math.pi*.08, tilt_z=math.pi*.35, phase=-t*.022, col=MINT,  lw=1.8, seg=72),
            dict(r= 75, tilt_x=math.pi*.60, tilt_z=math.pi*.2,  phase=t*.030,  col=GOLD,  lw=1.2, seg=64),
            dict(r= 58, tilt_x=math.pi*.25, tilt_z=math.pi*.55, phase=-t*.040, col=CYAN,  lw=1.0, seg=48),
        ]
        for rd in ring_defs:
            pts3 = self._ring_pts(rd['r'],rd['seg'],rd['tilt_x'],rd['tilt_z'],rd['phase'])
            # Project and sort by Z for depth
            proj2 = []
            for (x,y,z) in pts3:
                pt2d, z2d = self._proj(x,y,z,cx,cy)
                proj2.append((pt2d, z2d))
            # Draw ring segments with depth-based brightness
            z_vals = [z for _,z in proj2]
            z_min,z_max = min(z_vals),max(z_vals)
            z_rng = max(z_max-z_min,1)
            for i in range(len(proj2)):
                j=(i+1)%len(proj2)
                pt_a,za = proj2[i]
                pt_b,zb = proj2[j]
                depth_a = _cl((za-z_min)/z_rng)
                bright  = _cl(.25+.70*depth_a)
                tick_pulse = _cl(bright*.8+.15*math.sin(t*.04+i*.12))
                p.setPen(QPen(_a(rd['col'],tick_pulse), rd['lw']))
                p.drawLine(pt_a, pt_b)
            # Bright node on ring
            if proj2:
                peak_idx = max(range(len(proj2)), key=lambda i: proj2[i][1])
                node_pt  = proj2[peak_idx][0]
                p.setBrush(_a(rd['col'],.90))
                p.setPen(Qt.NoPen)
                p.drawEllipse(node_pt,4,4)

        # ── MECHANICAL IRIS / BLADES (6 blades, counter-rotating) ──────
        p.save()
        p.translate(cx,cy)
        iris_angle = t*.028
        for bi in range(6):
            a0 = iris_angle + bi*math.pi/3
            a1 = a0 + math.pi/4
            # blade as a narrow arc segment
            inner,outer = 35, 65
            pts = []
            for step in range(8):
                frac=step/7
                a=a0+frac*(a1-a0)
                r=inner+(outer-inner)*(.5+.5*math.sin(math.pi*frac))
                pts.append(QPointF(r*math.cos(a), r*math.sin(a)*.65))
            if len(pts)>1:
                blade_col = _a(STEEL, _cl(.50+.25*math.sin(t*.035+bi*1.0)))
                p.setPen(QPen(blade_col,1.5))
                p.setBrush(Qt.NoBrush)
                for k in range(len(pts)-1):
                    p.drawLine(pts[k],pts[k+1])
            # blade tip dot
            tip = pts[4] if len(pts)>4 else pts[-1]
            p.setBrush(_a(CYAN,_cl(.6+.3*math.sin(t*.05+bi))))
            p.setPen(Qt.NoPen)
            p.drawEllipse(tip,2.5,2.5)
        p.restore()

        # ── HOLOGRAPHIC SCAN LAYERS (3 horizontal discs sweeping Y) ────
        p.save()
        p.translate(cx,cy)
        for li in range(3):
            phase_off = li*math.pi*.66
            y_off = math.sin(t*.022+phase_off)*55
            scan_a = _cl(.10+.08*math.sin(t*.03+li))
            # ellipse representing a horizontal scan disc
            scan_col = _a(CYAN if li%2==0 else MINT, scan_a)
            p.setPen(QPen(scan_col, .8))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(0,y_off),125,18)
            # inner tick marks on scan disc
            for ti in range(16):
                a=2*math.pi*ti/16+t*.018
                r_s=120; r_e=126
                p.setPen(QPen(_a(CYAN,_cl(.3+.2*math.sin(t*.04+ti))),1.0))
                p.drawLine(QPointF(r_s*math.cos(a),(r_s*math.sin(a)+y_off)*.145),
                           QPointF(r_e*math.cos(a),(r_e*math.sin(a)+y_off)*.145))
        p.restore()

        # ── DATA STREAM FILAMENTS ───────────────────────────────────────
        p.save()
        p.translate(cx,cy)
        rng2 = random.Random(42)
        for fi in range(14):
            a   = 2*math.pi*fi/14 + t*.015
            r0  = rng2.uniform(65,90)
            r1  = rng2.uniform(130,160)
            pts_fil=[]
            for step in range(8):
                frac=step/7
                r=r0+(r1-r0)*frac
                wobble=math.sin(t*.04+fi*1.2+frac*3)*4
                a2=a+wobble*.012
                pts_fil.append(QPointF(r*math.cos(a2), r*math.sin(a2)*.65))
            fil_a = _cl(.10+.08*math.sin(t*.06+fi*.8))
            col_f = CYAN if fi%3==0 else (PUR if fi%3==1 else MINT)
            p.setPen(QPen(_a(col_f,fil_a),.8))
            for k in range(len(pts_fil)-1):
                p.drawLine(pts_fil[k],pts_fil[k+1])
        p.restore()

        # ── ORBITING PARTICLES (two shells, 12 + 8) ────────────────────
        p.save()
        p.translate(cx,cy)
        shells = [(12,105,.65),(8,78,.62)]
        for n_p,orb_r,squish in shells:
            for pi2 in range(n_p):
                a = 2*math.pi*pi2/n_p + t*.022*(1 if squish>.6 else -1)
                x = orb_r*math.cos(a)
                y = orb_r*math.sin(a)*squish
                pr = 2.0+1.2*math.sin(t*.04+pi2*.6)
                pa_v = _cl(.55+.30*math.sin(t*.05+pi2*.4))
                col_o = CYAN if pi2%2==0 else MINT
                p.setBrush(_a(col_o,pa_v))
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(x,y),pr,pr)
                # tail
                a_prev=a-.12
                xp=orb_r*math.cos(a_prev); yp=orb_r*math.sin(a_prev)*squish
                p.setPen(QPen(_a(col_o,_cl(pa_v*.4)),.8))
                p.drawLine(QPointF(xp,yp),QPointF(x,y))
        p.restore()

        # ── CENTRAL ENERGY NEXUS ───────────────────────────────────────
        p.save()
        p.translate(cx,cy)
        pulse_core = .5+.5*math.sin(t*.04)
        # outer soft glow
        for rg,ag in [(34,.12),(24,.18),(16,.25),(10,.35)]:
            g2=QRadialGradient(0,0,rg*(.9+.1*pulse_core))
            g2.setColorAt(0,_a(CYAN,_cl(ag*(1+.3*pulse_core))))
            g2.setColorAt(1,_a(CYAN,0))
            p.setBrush(QBrush(g2))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(0,0),rg,rg*.75)
        # core bright disc
        g3=QRadialGradient(-4,-4,14)
        g3.setColorAt(0,_a(WHITE,.95))
        g3.setColorAt(.4,_a(CYAN,.85))
        g3.setColorAt(1,_a(CYAN,0))
        p.setBrush(QBrush(g3))
        p.drawEllipse(QPointF(0,0),14*(1+.06*pulse_core),10*(1+.06*pulse_core))
        # inner energy ring
        p.setPen(QPen(_a(WHITE,_cl(.70+.25*pulse_core)),1.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0,0),18,13)
        # hexagonal segments inside core
        for hi in range(6):
            a=t*.08+hi*math.pi/3
            r_h=7
            x1=r_h*.5*math.cos(a); y1=r_h*.5*math.sin(a)*.75
            x2=r_h*math.cos(a);    y2=r_h*math.sin(a)*.75
            p.setPen(QPen(_a(CYAN,_cl(.5+.3*math.sin(t*.06+hi))),1.0))
            p.drawLine(QPointF(x1,y1),QPointF(x2,y2))
        p.restore()

        # ── HUD READOUTS ───────────────────────────────────────────────
        hf=QFont("JetBrains Mono")
        if not hf.exactMatch(): hf=QFont("Courier New")
        hf.setPixelSize(9)
        p.setFont(hf)
        p.setPen(_a(CYAN,.45))
        deg_y = math.degrees(self._ry)%360
        p.drawText(14,20,f"YAW   {deg_y:05.1f}°")
        p.drawText(14,32,f"PITCH {math.degrees(self._rx)%360:05.1f}°")
        p.drawText(14,44,f"CORE  {int(90+10*math.sin(t*.04)):03d}%")
        p.setPen(_a(MUTED,.35))
        p.drawText(w-115,h-10,"DRAG TO ROTATE  ·  AI CORE")

        # ── Corner HUD brackets ────────────────────────────────────────
        p.setPen(QPen(_a(CYAN,.28),1.2))
        bk=18
        for (ox,oy),(sx,sy) in [((10,10),(1,1)),((w-10,10),(-1,1)),
                                  ((10,h-10),(1,-1)),((w-10,h-10),(-1,-1))]:
            p.drawLine(ox,oy,ox+sx*bk,oy)
            p.drawLine(ox,oy,ox,oy+sy*bk)


# ════════════════════════════════════════════════════════════════════════════
#  LAMBORGHINI 3D CAR VIEWER
# ════════════════════════════════════════════════════════════════════════════
class CarViewer(QWidget):
    URLS={
        "side":  "https://images.unsplash.com/photo-1544636331-e26879cd4d9b?w=600&q=80",
        "front": "https://images.unsplash.com/photo-1617788138017-80ad40651399?w=600&q=80",
        "rear":  "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=600&q=80",
    }
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320,240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._px={k:None for k in self.URLS}
        self._px_flip=None
        self._ay=0.5; self._ax=0.22
        self._vy=0.009; self._vx=0.0
        self._drag=False; self._last=None
        self._t=0; self._loading=True
        self._fetch()
        QTimer(self,timeout=self._tick,interval=16).start()

    def _fetch(self):
        def w():
            hdr={"User-Agent":"Mozilla/5.0"}
            ld={}
            for k,u in self.URLS.items():
                try:
                    req=urllib.request.Request(u,headers=hdr)
                    d=urllib.request.urlopen(req,timeout=8).read()
                    px=QPixmap(); px.loadFromData(d)
                    if not px.isNull(): ld[k]=px
                except: pass
            if len(ld)==3:
                self._px=ld
                self._px_flip=ld["side"].transformed(QTransform().scale(-1,1))
                self._loading=False
                self.update()
        threading.Thread(target=w,daemon=True).start()

    def _tick(self):
        self._t+=1
        if not self._drag:
            self._vy=_lerp(self._vy,.009,.04)
            self._vx=_lerp(self._vx,0,.06)
            self._ay+=self._vy; self._ax+=self._vx
            self._ax=_cl(self._ax,-0.5,0.5)
        self.update()

    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton: self._drag=True;self._last=e.position()
    def mouseMoveEvent(self,e):
        if self._drag and self._last:
            self._vy=(e.position().x()-self._last.x())*.007
            self._vx=(e.position().y()-self._last.y())*.004
            self._ay+=self._vy; self._ax+=self._vx
            self._ax=_cl(self._ax,-0.5,0.5)
            self._last=e.position()
    def mouseReleaseEvent(self,e):
        if e.button()==Qt.LeftButton: self._drag=False

    def paintEvent(self,_):
        pa=QPainter(self)
        pa.setRenderHint(QPainter.Antialiasing)
        pa.setRenderHint(QPainter.SmoothPixmapTransform)
        w,h=self.width(),self.height()
        cx,cy=w/2,h/2
        pa.fillRect(self.rect(),_hex(C_BG))

        g=QRadialGradient(cx,cy,min(w,h)*.5)
        g.setColorAt(0,_a(CYAN,.040)); g.setColorAt(1,_a(CYAN,.000))
        pa.fillRect(self.rect(),g)

        pa.setPen(QPen(_a(WHITE,.03),.8))
        for x in range(0,w,44): pa.drawLine(x,0,x,h)
        for y in range(0,h,44): pa.drawLine(0,y,w,y)

        # HUD corners
        pa.setPen(QPen(_a(CYAN,.28),1.2))
        bk=14
        for (ox,oy),(sx,sy) in [((8,8),(1,1)),((w-8,8),(-1,1)),
                                  ((8,h-8),(1,-1)),((w-8,h-8),(-1,-1))]:
            pa.drawLine(ox,oy,ox+sx*bk,oy); pa.drawLine(ox,oy,ox,oy+sy*bk)

        hf=QFont("JetBrains Mono")
        if not hf.exactMatch(): hf=QFont("Courier New")
        hf.setPixelSize(8)
        pa.setFont(hf)
        pa.setPen(_a(CYAN,.40))
        pa.drawText(13,18,f"YAW {math.degrees(self._ay)%360:05.1f}°")
        pa.drawText(w-90,h-8,"DRAG TO SPIN")

        if self._loading:
            pa.setPen(_a(MUTED,.6))
            pa.setFont(QFont("JetBrains Mono" if hf.exactMatch() else "Courier New"))
            pa.drawText(self.rect(),Qt.AlignCenter,"LOADING VEHICLE …")
            return

        TAU=2*math.pi
        ang=self._ay%TAU
        if ang<TAU*.25:   px=self._px.get("side")
        elif ang<TAU*.50: px=self._px.get("front")
        elif ang<TAU*.75: px=self._px_flip
        else:             px=self._px.get("rear")
        if not px or px.isNull(): return

        bw,bh=190,107; cam=270; sc=1.5
        cx_a=self._ax; cy_a=self._ay
        cos_x=math.cos(cx_a); sin_x=math.sin(cx_a)
        cos_y=math.cos(cy_a); sin_y=math.sin(cy_a)
        def proj(x,y,z):
            rx=x*cos_y-z*sin_y; rz=x*sin_y+z*cos_y
            ry=y*cos_x-rz*sin_x; rz2=y*sin_x+rz*cos_x
            d=rz2+cam; d=d if abs(d)>.01 else .01
            return QPointF(cx+(rx*sc*cam)/d, cy+(ry*sc*cam)/d)
        corners=[(-bw/2,-bh/2,0),(bw/2,-bh/2,0),(bw/2,bh/2,0),(-bw/2,bh/2,0)]
        proj_c=[proj(x,y,z) for x,y,z in corners]

        bd=22
        box3=[(-bw/2-3,-bh/2-3,-bd),(bw/2+3,-bh/2-3,-bd),(bw/2+3,bh/2+3,-bd),(-bw/2-3,bh/2+3,-bd),
              (-bw/2-3,-bh/2-3, bd),(bw/2+3,-bh/2-3, bd),(bw/2+3,bh/2+3, bd),(-bw/2-3,bh/2+3, bd)]
        bp=[proj(x,y,z) for x,y,z in box3]
        pa.setPen(QPen(_a(CYAN,.16),.7))
        for i in range(4):
            j=(i+1)%4
            pa.drawLine(bp[i],bp[j]); pa.drawLine(bp[i+4],bp[j+4]); pa.drawLine(bp[i],bp[i+4])

        src=QPolygonF([QPointF(0,0),QPointF(px.width(),0),
                       QPointF(px.width(),px.height()),QPointF(0,px.height())])
        dst=QPolygonF(proj_c)
        tr=QTransform()
        if QTransform.quadToQuad(src,dst,tr):
            pa.save(); pa.setTransform(tr,True); pa.drawPixmap(0,0,px); pa.restore()

        pa.setPen(Qt.NoPen)
        for pt in proj_c:
            pa.setBrush(_a(CYAN,.75)); pa.drawEllipse(pt,2.5,2.5)

        floor_y=max(p.y() for p in proj_c)+4
        if floor_y<h:
            gf=QLinearGradient(0,floor_y,0,floor_y+45)
            gf.setColorAt(0,_a(CYAN,.06)); gf.setColorAt(1,_a(CYAN,.00))
            pa.fillRect(0,int(floor_y),w,50,gf)

        pa.setPen(_a(CYAN,.45)); pa.setFont(hf)
        pa.drawText(int(cx)-50,h-8,"LAMBORGHINI  ·  LIVE 3D")


# ════════════════════════════════════════════════════════════════════════════
#  GLASS FEATURE CARD
# ════════════════════════════════════════════════════════════════════════════
class GlassCard(QFrame):
    def __init__(self,title,desc,icon,color,index,cb,parent=None):
        super().__init__(parent)
        self._col=_hex(color); self._cs=color; self._hover=False
        self.setMinimumHeight(170)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover,True)
        sh=QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(14); sh.setColor(QColor(0,0,0,120)); sh.setOffset(0,5)
        self.setGraphicsEffect(sh); self._sh=sh

        v=QVBoxLayout(self)
        v.setContentsMargins(20,20,20,20); v.setSpacing(9)
        rw=QHBoxLayout(); rw.setSpacing(10)
        ic=QLabel(icon); ic.setFont(UI_FONT(20))
        ic.setStyleSheet("background:transparent;border:none;"); rw.addWidget(ic)
        tl=QLabel(title); tl.setFont(UI_FONT(14,bold=True))
        tl.setStyleSheet(f"color:{C_WHT};background:transparent;border:none;")
        rw.addWidget(tl,1); v.addLayout(rw)
        dl=QLabel(desc); dl.setFont(UI_FONT(11)); dl.setWordWrap(True)
        dl.setStyleSheet(f"color:{C_MUT};background:transparent;border:none;")
        v.addWidget(dl,1)
        bn=QPushButton("OPEN →"); bn.setFont(UI_FONT(10,bold=True))
        bn.setCursor(Qt.PointingHandCursor); bn.clicked.connect(lambda:cb(index))
        bn.setFixedHeight(28)
        bn.setStyleSheet(f"""QPushButton{{background:transparent;border:1px solid {color};
            border-radius:5px;color:{color};padding:0 12px;letter-spacing:2px;
            font-size:10px;font-weight:700;}}
            QPushButton:hover{{background:{color};color:#050816;}}""")
        v.addWidget(bn,0,Qt.AlignLeft)

    def enterEvent(self,e):
        self._hover=True
        self._sh.setBlurRadius(30)
        c=QColor(self._col); c.setAlpha(90); self._sh.setColor(c)
        self._sh.setOffset(0,10); self.update()
    def leaveEvent(self,e):
        self._hover=False
        self._sh.setBlurRadius(14); self._sh.setColor(QColor(0,0,0,120))
        self._sh.setOffset(0,5); self.update()
    def paintEvent(self,_):
        pa=QPainter(self); pa.setRenderHint(QPainter.Antialiasing)
        r=QRectF(self.rect()).adjusted(1,1,-1,-1)
        pa.setBrush(_a(WHITE,.055 if self._hover else .025))
        pa.setPen(Qt.NoPen); pa.drawRoundedRect(r,13,13)
        pa.setPen(QPen(_a(self._col,.55 if self._hover else .18),1.0))
        pa.setBrush(Qt.NoBrush); pa.drawRoundedRect(r,13,13)
        strip=QRectF(r.x(),r.y()+13,2.5,r.height()-26)
        pa.setBrush(self._col); pa.setPen(Qt.NoPen); pa.drawRoundedRect(strip,1.5,1.5)
        super().paintEvent(_)


# ════════════════════════════════════════════════════════════════════════════
#  STATS SUMMARY CARD  (sidebar, always visible)
# ════════════════════════════════════════════════════════════════════════════
class StatsSummaryCard(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        v=QVBoxLayout(self); v.setContentsMargins(22,18,22,18); v.setSpacing(11)
        tl=QLabel("RUN TELEMETRY"); tl.setFont(UI_FONT(10,bold=True))
        tl.setStyleSheet("color:#fbbf24;background:transparent;border:none;letter-spacing:3px;")
        v.addWidget(tl)
        self._rows={}
        for lbl,col,key in [("TOTAL RUNS",C_WHT,"total"),("PASSED",C_MINT,"pass"),
                              ("FAILED",C_RED,"fail"),("ELAPSED",C_CYAN,"time")]:
            rw=QHBoxLayout()
            lb=QLabel(lbl); lb.setFont(UI_FONT(10,bold=True))
            lb.setStyleSheet("color:#5e7a8a;background:transparent;border:none;letter-spacing:1px;")
            lb.setFixedWidth(105); rw.addWidget(lb)
            vl=QLabel("0"); f=QFont("JetBrains Mono")
            if not f.exactMatch(): f=QFont("Courier New")
            f.setPixelSize(13); vl.setFont(f)
            vl.setStyleSheet(f"color:{col};background:transparent;border:none;")
            rw.addWidget(vl,1); self._rows[key]=vl; v.addLayout(rw)
        v.addStretch()

    def update_data(self,total,passed,failed,elapsed):
        self._rows["total"].setText(str(total)); self._rows["pass"].setText(str(passed))
        self._rows["fail"].setText(str(failed)); self._rows["time"].setText(str(elapsed))

    def paintEvent(self,_):
        pa=QPainter(self); pa.setRenderHint(QPainter.Antialiasing)
        r=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        pa.setBrush(_a(WHITE,.04)); pa.setPen(Qt.NoPen); pa.drawRoundedRect(r,13,13)
        pa.setPen(QPen(_a(_hex("#fbbf24"),.18),1.0)); pa.setBrush(Qt.NoBrush)
        pa.drawRoundedRect(r,13,13)


# ════════════════════════════════════════════════════════════════════════════
#  SYSTEM DIAG PANEL
# ════════════════════════════════════════════════════════════════════════════
class _DiagBg(QWidget):
    def paintEvent(self,_):
        pa=QPainter(self); pa.setRenderHint(QPainter.Antialiasing)
        r=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        pa.setBrush(_a(WHITE,.04)); pa.setPen(Qt.NoPen); pa.drawRoundedRect(r,13,13)
        pa.setPen(QPen(_a(CYAN,.14),1.0)); pa.setBrush(Qt.NoBrush); pa.drawRoundedRect(r,13,13)

def _build_diag_panel():
    c=_DiagBg(); v=QVBoxLayout(c); v.setContentsMargins(22,18,22,18); v.setSpacing(11)
    tl=QLabel("SYSTEM DIAGNOSTICS"); tl.setFont(UI_FONT(10,bold=True))
    tl.setStyleSheet(f"color:{C_CYAN};background:transparent;border:none;letter-spacing:3px;")
    v.addWidget(tl)
    def rw(label,value,vc=C_MUT):
        r=QHBoxLayout()
        lb=QLabel(label); lb.setFont(UI_FONT(10,bold=True))
        lb.setStyleSheet("color:#5e7a8a;background:transparent;border:none;letter-spacing:1px;")
        lb.setFixedWidth(110); r.addWidget(lb)
        vl=QLabel(str(value)); f=QFont("JetBrains Mono")
        if not f.exactMatch(): f=QFont("Courier New")
        f.setPixelSize(11); vl.setFont(f); vl.setWordWrap(True)
        vl.setStyleSheet(f"color:{vc};background:transparent;border:none;")
        r.addWidget(vl,1); return r
    v.addLayout(rw("HOST OS",   platform.system()+" "+platform.release()))
    v.addLayout(rw("PYTHON",    sys.version.split()[0]))
    v.addLayout(rw("PYSIDE6",   PySide6.__version__))
    v.addLayout(rw("STATUS",    "● READY", C_MINT))
    #v.addLayout(rw("WORKSPACE", os.getcwd()))
    v.addStretch()
    return c


# ════════════════════════════════════════════════════════════════════════════
#  HERO HEADER
# ════════════════════════════════════════════════════════════════════════════
class HeroHeader(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setFixedHeight(195)
        self._t=0.0
        QTimer(self,timeout=self._tick,interval=33).start()
        h=QHBoxLayout(self); h.setContentsMargins(60,0,60,0)
        left=QVBoxLayout(); left.setSpacing(5); left.setAlignment(Qt.AlignVCenter)
        ey=QLabel("VECTORCAST  //  AUTOMOTIVE COMPILATION SUITE")
        ey.setFont(UI_FONT(9,bold=True))
        ey.setStyleSheet(f"color:{C_CYAN};background:transparent;border:none;letter-spacing:4px;")
        left.addWidget(ey)
        tl=QLabel("WELCOME\nDASHBOARD")
        f=QFont("Bebas Neue")
        if not f.exactMatch(): f=QFont("Impact")
        f.setPixelSize(64); tl.setFont(f)
        tl.setStyleSheet(f"color:{C_WHT};background:transparent;border:none;")
        left.addWidget(tl)
        sb=QLabel("Compilation · Verification · Metrics · Reports")
        sb.setFont(UI_FONT(11))
        sb.setStyleSheet(f"color:{C_MUT};background:transparent;border:none;letter-spacing:2px;")
        left.addWidget(sb)
        h.addLayout(left,1)

    def _tick(self): self._t+=.022; self.update()
    def paintEvent(self,_):
        pa=QPainter(self); pa.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height(); t=self._t
        pa.fillRect(self.rect(),_hex(C_BG))
        g=QLinearGradient(0,0,w,h)
        s=math.sin(t*.45)*.11
        g.setColorAt(_cl(s),        QColor(0,8,38,255))
        g.setColorAt(_cl(.44+s),    QColor(8,0,55,210))
        g.setColorAt(_cl(.87+s*.5), QColor(0,28,48,255))
        pa.fillRect(self.rect(),g)
        sx=(math.sin(t*.35)*.5+.5)*w
        g2=QRadialGradient(sx,h*.65,250)
        g2.setColorAt(0,_a(CYAN,.018)); g2.setColorAt(1,_a(CYAN,.000))
        pa.fillRect(self.rect(),g2)
        g3=QRadialGradient(w*.82,h*.3,180)
        g3.setColorAt(0,_a(PUR,.015)); g3.setColorAt(1,_a(PUR,.000))
        pa.fillRect(self.rect(),g3)
        fade=QLinearGradient(0,h*.5,0,h)
        fade.setColorAt(0,_a(_hex(C_BG),.0)); fade.setColorAt(1,_a(_hex(C_BG),1.0))
        pa.fillRect(self.rect(),fade)
        pa.setPen(QPen(_a(WHITE,.035),.8))
        for x in range(0,w,48): pa.drawLine(x,0,x,h)
        for y in range(0,h,48): pa.drawLine(0,y,w,y)
        super().paintEvent(_)


# ════════════════════════════════════════════════════════════════════════════
#  WORKFLOW STEP
# ════════════════════════════════════════════════════════════════════════════
class _WFBg(QWidget):
    def __init__(self,col,parent=None):
        super().__init__(parent); self._c=_hex(col)
    def paintEvent(self,_):
        pa=QPainter(self); pa.setRenderHint(QPainter.Antialiasing)
        r=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        pa.setBrush(_a(WHITE,.04)); pa.setPen(Qt.NoPen); pa.drawRoundedRect(r,10,10)
        pa.setPen(QPen(_a(self._c,.22),1.0)); pa.setBrush(Qt.NoBrush); pa.drawRoundedRect(r,10,10)

def _wf_step(num,title,desc,col):
    w=_WFBg(col); v=QVBoxLayout(w); v.setContentsMargins(15,15,15,15); v.setSpacing(5)
    n=QLabel(num); f=QFont("JetBrains Mono")
    if not f.exactMatch(): f=QFont("Courier New")
    f.setPixelSize(24); f.setBold(True); n.setFont(f)
    n.setStyleSheet(f"color:{col};background:transparent;border:none;"); v.addWidget(n)
    tl=QLabel(title.upper()); tl.setFont(UI_FONT(11,bold=True))
    tl.setStyleSheet(f"color:{C_WHT};background:transparent;border:none;letter-spacing:2px;")
    v.addWidget(tl)
    dl=QLabel(desc); dl.setFont(UI_FONT(11)); dl.setWordWrap(True)
    dl.setStyleSheet(f"color:{C_MUT};background:transparent;border:none;"); v.addWidget(dl)
    return w


# ════════════════════════════════════════════════════════════════════════════
#  HOME TAB
# ════════════════════════════════════════════════════════════════════════════
class HomeTab(QWidget):
    def __init__(self,switch_to_tab):
        super().__init__()
        self._sw=switch_to_tab
        self.setStyleSheet(f"background:{C_BG};")
        self._build()

    def _build(self):
        outer=QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)

        # Hero
        outer.addWidget(HeroHeader())

        # Scroll body
        scroll=QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet(f"background:{C_BG};")
        outer.addWidget(scroll,1)

        body=QWidget(); body.setStyleSheet(f"background:{C_BG};")
        scroll.setWidget(body)

        # Neural field behind everything
        self._nf=NeuralField(body)
        self._nf.setAttribute(Qt.WA_TransparentForMouseEvents)

        v=QVBoxLayout(body); v.setContentsMargins(55,20,55,60); v.setSpacing(0)

        # ── SECTION: AI Core + car viewer ────────────────────────────────
        v.addWidget(self._sec("◆  DASHBOARD OVERVIEW",C_CYAN))
        v.addSpacing(14)

        core_row=QHBoxLayout(); core_row.setSpacing(16)

        # Single diagnostics panel
        dashboard_panel = _build_diag_panel()
        dashboard_panel.setFixedHeight(170)
        core_row.addWidget(dashboard_panel, 1)

        # Luxury Car 360° Viewer
        self.car_viewer = LuxuryCar360Viewer()
        self.car_viewer.setFixedHeight(170)
        core_row.addWidget(self.car_viewer, 1)

        v.addLayout(core_row)

        # ── SECTION: Feature cards ────────────────────────────────────────
        v.addSpacing(36)
        v.addWidget(self._sec("◆  CONTROL PANEL MODULES",C_PUR))
        v.addSpacing(14)

        grid=QGridLayout(); grid.setSpacing(14)
        cards=[
            ("Project Analysis",
             "Scan source tree · catalog modules · code metrics · Excel reports.",
             "📊",C_CYAN,1),
            ("UT Compilation",
             "Batch compile Unit Test environments · per-module pass/fail dashboard.",
             "⚡",C_RED,2),
            ("IT Compilation",
             "Integration tests · SBF stub injection · multi-UUT · retry logic.",
             "🔗","#fbbf24",3),
            ("Import Excel",
             "Load module lists from .xlsx/.csv · populate UT queue instantly.",
             "📁",C_MINT,4),
            ("Logs & Diagnostics",
             "Run history · console output · records · elapsed time tracking.",
             "📜",C_MUT,5),
        ]
        pos=[(0,0),(0,1),(0,2),(1,0),(1,1)]
        for (ti,de,ic,co,ix),(ro,cl) in zip(cards,pos):
            grid.addWidget(GlassCard(ti,de,ic,co,ix,self._sw),ro,cl)

        v.addLayout(grid)

        # ── SECTION: Workflow ─────────────────────────────────────────────
        v.addSpacing(36)
        v.addWidget(self._sec("◆  VERIFICATION PIPELINE",C_RED))
        v.addSpacing(14)
        wf=QHBoxLayout(); wf.setSpacing(8)
        steps=[
            ("01","Scan Source", "Walk directory tree, discover .c modules, evaluate code volume.",   C_CYAN),
            ("02","Configure",   "Load details manually or import Excel lists into UT batches.",      C_MINT),
            ("03","Compile",     "Execute batch compilation for Unit (UT) or Integration (IT) envs.", C_RED),
            ("04","Diagnostics", "Monitor log streams · confirm pass/fail · view reports.",            C_MUT),
        ]
        for i,(n,ti,de,co) in enumerate(steps):
            wf.addWidget(_wf_step(n,ti,de,co),1)
            if i<len(steps)-1:
                arr=QLabel("→"); arr.setFont(UI_FONT(20))
                arr.setStyleSheet("color:#1e3050;background:transparent;")
                arr.setAlignment(Qt.AlignCenter); wf.addWidget(arr,0)
        v.addLayout(wf)
        v.addStretch()

    @staticmethod
    def _sec(text,color):
        lb=QLabel(text); lb.setFont(UI_FONT(10,bold=True))
        lb.setStyleSheet(
            f"color:{color};background:transparent;border:none;"
            f"letter-spacing:3px;border-bottom:1px solid rgba(255,255,255,0.05);"
            f"padding-bottom:6px;")
        return lb

    def resizeEvent(self,e):
        super().resizeEvent(e)
        if hasattr(self,'_nf') and self._nf.parent():
            p=self._nf.parent()
            self._nf.setGeometry(0,0,p.width(),p.height())

    def update_stats(self,total,passed,failed,elapsed):
        self.stats_summary.update_data(total,passed,failed,elapsed)