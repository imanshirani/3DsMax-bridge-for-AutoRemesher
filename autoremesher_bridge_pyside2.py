"""
AutoRemesher Bridge for 3ds Max
────────────────────────────────
Python 3 + PySide2 UI that wraps the autoremesher CLI tool.

"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from PySide2.QtCore import QSettings, QThread, QTimer, Qt, Signal
from PySide2.QtGui import QColor, QPalette
from PySide2.QtWidgets import ( QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
                               QPushButton, QSizePolicy, QSlider, QSpinBox, QStatusBar, QVBoxLayout, QWidget
)

try:
    import pymxs
    _IN_MAX = True
except ImportError:
    _IN_MAX = False

import webbrowser

SETTINGS_ORG  = "AutoRemesherBridge"
SETTINGS_APP  = "Settings"
AUTHOR        = "Iman Shirani"
VERSION       = "0.0.1"
GITHUB_URL    = "https://github.com/imanshirani/3DsMax-bridge-for-AutoRemesher"
PAYPAL_URL    = "https://www.paypal.com/donate/?hosted_button_id=LAMNRY6DDWDC4"


# ══════════════════════════════════════════════════════════════════════════
#  Dark palette (matches 3ds Max dark skin)
# ══════════════════════════════════════════════════════════════════════════
def _dark_palette():
    p = QPalette()
    BG      = QColor("#1e1e1e")
    SURFACE = QColor("#2a2a2a")
    FG      = QColor("#d4d4d4")
    ACCENT  = QColor("#e8823c")
    DIS     = QColor("#555555")

    p.setColor(QPalette.Window,          SURFACE)
    p.setColor(QPalette.WindowText,      FG)
    p.setColor(QPalette.Base,            BG)
    p.setColor(QPalette.AlternateBase,   SURFACE)
    p.setColor(QPalette.ToolTipBase,     BG)
    p.setColor(QPalette.ToolTipText,     FG)
    p.setColor(QPalette.Text,            FG)
    p.setColor(QPalette.Button,          SURFACE)
    p.setColor(QPalette.ButtonText,      FG)
    p.setColor(QPalette.BrightText,      Qt.white)
    p.setColor(QPalette.Link,            ACCENT)
    p.setColor(QPalette.Highlight,       ACCENT)
    p.setColor(QPalette.HighlightedText, Qt.black)
    p.setColor(QPalette.Disabled, QPalette.Text,       DIS)
    p.setColor(QPalette.Disabled, QPalette.ButtonText, DIS)
    return p


_QSS = """
* { font-family: "Segoe UI", sans-serif; font-size: 12px; }

QMainWindow, QWidget#root { background: #1e1e1e; }

QGroupBox {
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    margin-top: 10px;
    padding: 8px 6px 6px 6px;
    color: #888;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QLineEdit, QSpinBox, QDoubleSpinBox {
    background: #111;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    padding: 4px 6px;
    color: #d4d4d4;
    selection-background-color: #e8823c;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #e8823c; }

QPushButton {
    background: #2f2f2f;
    border: 1px solid #444;
    border-radius: 3px;
    padding: 5px 12px;
    color: #d4d4d4;
}
QPushButton:hover   { background: #3a3a3a; border-color: #e8823c; }
QPushButton:pressed { background: #1a1a1a; }
QPushButton:disabled { color: #555; border-color: #333; }

QPushButton#btn_remesh {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #e8823c, stop:1 #c0601e);
    border: none;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    border-radius: 4px;
    padding: 9px 0;
    letter-spacing: 0.5px;
}
QPushButton#btn_remesh:hover    { background: #f0944e; }
QPushButton#btn_remesh:pressed  { background: #b05010; }
QPushButton#btn_remesh:disabled { background: #3a3a3a; color: #666; }

QProgressBar {
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    background: #111;
    text-align: center;
    color: #888;
    font-size: 11px;
    height: 14px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #c0601e, stop:1 #e8823c);
    border-radius: 2px;
}

QComboBox {
    background: #111;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    padding: 4px 6px;
    color: #d4d4d4;
}
QComboBox:focus { border-color: #e8823c; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #1e1e1e;
    border: 1px solid #3a3a3a;
    selection-background-color: #e8823c;
    color: #d4d4d4;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #3a3a3a;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 12px; height: 12px;
    background: #e8823c;
    border-radius: 6px;
    margin: -4px 0;
}
QSlider::sub-page:horizontal {
    background: #e8823c;
    border-radius: 2px;
}

QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #555;
    border-radius: 2px;
    background: #111;
}
QCheckBox::indicator:checked { background: #e8823c; border-color: #e8823c; }

QLabel#lbl_status { color: #888; font-size: 11px; }
QLabel#lbl_header { color: #e8823c; font-size: 15px; font-weight: 700; letter-spacing: 1px; }
QLabel#lbl_sub    { color: #555;    font-size: 10px; letter-spacing: 2px; text-transform: uppercase; }
"""


# ══════════════════════════════════════════════════════════════════════════
#  Background worker
# ══════════════════════════════════════════════════════════════════════════
class RemeshWorker(QThread):
    progress = Signal(int, str)   # value 0-100, message
    finished = Signal(bool, str)  # success, message

    def __init__(self, exe_path, in_file, out_file,
                 target_count, smooth, sharp_edge, adaptivity, edge_scaling):
        super().__init__()
        self.exe_path     = exe_path
        self.in_file      = in_file
        self.out_file     = out_file
        self.target_count = target_count
        self.smooth       = smooth
        self.sharp_edge   = sharp_edge
        self.adaptivity   = adaptivity
        self.edge_scaling = edge_scaling

    def run(self):
        print("[AR] worker.run() entered")
        self.progress.emit(30, "Running AutoRemesher…")
        print("[AR] progress(30) emitted")
        cmd = [
            self.exe_path,
            "--input",         self.in_file,
            "--output",        self.out_file,
            "--target-quads",  str(self.target_count),
            "--smooth-normal", "{:.4f}".format(self.smooth),
            "--sharp-edge",    "{:.4f}".format(self.sharp_edge),
            "--adaptivity",    "{:.4f}".format(self.adaptivity),
            "--edge-scaling",  "{:.4f}".format(self.edge_scaling),
        ]
        print("[AR] subprocess.run: {}".format(" ".join(cmd)))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            print("[AR] subprocess done — exit={}".format(result.returncode))
            if result.stderr.strip():
                print("[AR] stderr: {}".format(result.stderr.strip()))
        except FileNotFoundError:
            self.finished.emit(False, "Executable not found:\n{}".format(self.exe_path))
            return
        except Exception as exc:
            self.finished.emit(False, "Unexpected error:\n{}".format(exc))
            return

        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            self.finished.emit(
                False,
                "AutoRemesher exited with code {}.\n\n{}".format(result.returncode, err),
            )
            return

        if not Path(self.out_file).exists():
            self.finished.emit(False, "AutoRemesher finished but no output file was created.")
            return

        print("[AR] emitting progress(80) and finished(True)")
        self.progress.emit(80, "Importing result…")
        self.finished.emit(True, "")
        print("[AR] worker.run() done")


# ══════════════════════════════════════════════════════════════════════════
#  3ds Max I/O helpers (pymxs)
# ══════════════════════════════════════════════════════════════════════════
def _max_selected_name():
    if not _IN_MAX:
        return None
    rt = pymxs.runtime
    sel = rt.selection
    if sel.count == 0:
        return None
    return str(sel[0].name)


def _max_export_obj(obj_name, file_path):
    if not _IN_MAX:
        return False
    rt   = pymxs.runtime
    print("[AR] export: getNodeByName '{}'".format(obj_name))
    node = rt.getNodeByName(obj_name)
    if node is None:
        print("[AR] export: node not found")
        return False

    print("[AR] export: snapshotAsMesh...")
    mesh = rt.snapshotAsMesh(node)
    if mesh is None:
        print("[AR] export: snapshotAsMesh returned None")
        return False

    tm = node.transform
    nv = rt.getNumVerts(mesh)
    print("[AR] export: verts={}".format(nv))

    pos = node.position
    print("[AR] export: pivot  X={:.3f}  Y={:.3f}  Z={:.3f}".format(pos.x, pos.y, pos.z))

    # snapshotAsMesh returns world-space vertices.
    # Max OBJ importer does a plain Y↔Z swap on read.
    # Write (x, z, y) so after importer swaps them back vertices land correctly.
    raw_verts = []
    xs_w, ys_w, zs_w = [], [], []
    for i in range(1, nv + 1):
        v = rt.getVert(mesh, i)
        xs_w.append(v.x); ys_w.append(v.y); zs_w.append(v.z)
        raw_verts.append((v.x, v.z, v.y))

    if xs_w:
        print("[AR] export: origin size   X={:.3f}  Y={:.3f}  Z={:.3f}".format(
            max(xs_w)-min(xs_w), max(ys_w)-min(ys_w), max(zs_w)-min(zs_w)))
        cx = (max(xs_w)+min(xs_w))/2
        cy = (max(ys_w)+min(ys_w))/2
        cz = (max(zs_w)+min(zs_w))/2
        print("[AR] export: mesh center   X={:.3f}  Y={:.3f}  Z={:.3f}".format(cx, cy, cz))

    # Weld coincident vertices in Python (fixes non-manifold seams like Teapot)
    PREC = 4
    key_to_new = {}
    new_verts  = []
    old_to_new = {}
    for old_i, p in enumerate(raw_verts, start=1):
        key = (round(p[0], PREC), round(p[1], PREC), round(p[2], PREC))
        if key not in key_to_new:
            new_verts.append(p)
            key_to_new[key] = len(new_verts)
        old_to_new[old_i] = key_to_new[key]
    print("[AR] export: {} verts → {} after weld".format(nv, len(new_verts)))

    lines = []
    for (x, y, z) in new_verts:
        lines.append("v {} {} {}".format(x, y, z))

    nf      = rt.getNumFaces(mesh)
    skipped = 0
    print("[AR] export: faces={}".format(nf))
    for i in range(1, nf + 1):
        f  = rt.getFace(mesh, i)
        vi = (old_to_new[int(f.x)], old_to_new[int(f.y)], old_to_new[int(f.z)])
        if vi[0] == vi[1] or vi[1] == vi[2] or vi[0] == vi[2]:
            skipped += 1
            continue
        # Y↔Z swap changes coordinate handedness — reverse winding to keep normals outward
        lines.append("f {} {} {}".format(vi[0], vi[2], vi[1]))
    if skipped:
        print("[AR] export: skipped {} degenerate faces".format(skipped))

    # Do NOT call rt.delete(mesh) — TriMesh value is not a scene node;
    # delete() on it triggers DirtyNotificationEventMonitor.
    Path(file_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    size = Path(file_path).stat().st_size
    print("[AR] export: done — size={}".format(size))
    return size > 0


def _max_import_obj(file_path, origin_name):
    if not _IN_MAX:
        return None
    rt = pymxs.runtime
    new_name    = origin_name + "_remeshed"
    origin_node = rt.getNodeByName(origin_name)

    before_names = {str(n.name) for n in rt.objects}
    rt.importFile(file_path, rt.name("noPrompt"))
    imported = None
    for n in rt.objects:
        if str(n.name) not in before_names:
            n.name = new_name
            imported = n
            break

    # Vertices were exported in world space — no transform manipulation needed.

    safe = new_name.replace('"', '\\"')
    rt.execute('''(
        local n = getNodeByName "{}"
        if n != undefined do (
            local bb = nodeGetBoundingBox n (matrix3 1)
            local szx = bb[2].x-bb[1].x
            local szy = bb[2].y-bb[1].y
            local szz = bb[2].z-bb[1].z
            local cx = (bb[1].x+bb[2].x)/2.0
            local cy = (bb[1].y+bb[2].y)/2.0
            local cz = (bb[1].z+bb[2].z)/2.0
            format "[AR] import: result size   X=% Y=% Z=%\\n" szx szy szz
            format "[AR] import: mesh center   X=% Y=% Z=%\\n" cx cy cz
            format "[AR] import: pivot         X=% Y=% Z=%\\n" n.position.x n.position.y n.position.z
        )
    )'''.format(safe))
    return new_name


def _max_hide(obj_name):
    if not _IN_MAX:
        return
    safe = obj_name.replace('"', '\\"')
    pymxs.runtime.execute('''(
        local n = getNodeByName "{}"
        if n != undefined do n.visibility = false
    )'''.format(safe))


# ══════════════════════════════════════════════════════════════════════════
#  About dialog
# ══════════════════════════════════════════════════════════════════════════
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About AutoRemesher Bridge")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setFixedWidth(340)
        self.setStyleSheet(_QSS)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(24, 24, 24, 24)
        vbox.setSpacing(12)

        title = QLabel("AUTOREMESHER BRIDGE")
        title.setObjectName("lbl_header")
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        ver = QLabel("Version {}".format(VERSION))
        ver.setObjectName("lbl_sub")
        ver.setAlignment(Qt.AlignCenter)
        vbox.addWidget(ver)

        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #3a3a3a;")
        vbox.addWidget(line)

        author = QLabel("Developed by  <b>{}</b>".format(AUTHOR))
        author.setStyleSheet("color: #aaa; font-size: 12px;")
        author.setAlignment(Qt.AlignCenter)
        vbox.addWidget(author)

        desc = QLabel("A 3ds Max bridge for the\nhuxingyi/autoremesher CLI tool.")
        desc.setStyleSheet("color: #666; font-size: 11px;")
        desc.setAlignment(Qt.AlignCenter)
        vbox.addWidget(desc)

        vbox.addSpacing(6)

        btn_gh = QPushButton("  View on GitHub")
        btn_gh.setFixedHeight(36)
        btn_gh.setCursor(Qt.PointingHandCursor)
        btn_gh.setStyleSheet("""
            QPushButton {
                background: #24292e;
                color: #fff;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                padding-left: 8px;
            }
            QPushButton:hover  { background: #3a4046; }
            QPushButton:pressed { background: #1a1e22; }
        """)
        btn_gh.clicked.connect(lambda: webbrowser.open(GITHUB_URL))
        vbox.addWidget(btn_gh)

        btn_pp = QPushButton("  Support via PayPal")
        btn_pp.setFixedHeight(36)
        btn_pp.setCursor(Qt.PointingHandCursor)
        btn_pp.setStyleSheet("""
            QPushButton {
                background: #009cde;
                color: #fff;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                padding-left: 8px;
            }
            QPushButton:hover  { background: #00b3ff; }
            QPushButton:pressed { background: #007ab0; }
        """)
        btn_pp.clicked.connect(lambda: webbrowser.open(PAYPAL_URL))
        vbox.addWidget(btn_pp)

        vbox.addSpacing(4)

        btn_close = QPushButton("Close")
        btn_close.setFixedHeight(30)
        btn_close.clicked.connect(self.accept)
        vbox.addWidget(btn_close)


# ══════════════════════════════════════════════════════════════════════════
#  SliderRow widget  (label + slider + spinbox, synced)
# ══════════════════════════════════════════════════════════════════════════
class SliderRow(QWidget):
    def __init__(self, label, min_val, max_val, default, decimals=2, step=None):
        super().__init__()
        self._decimals = decimals
        self._factor   = 10 ** decimals

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 4)
        vbox.setSpacing(3)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #888; font-size: 11px;")
        top.addWidget(lbl)
        top.addStretch()

        if decimals == 0:
            self._spin = QSpinBox()
            self._spin.setRange(int(min_val), int(max_val))
            self._spin.setValue(int(default))
            self._spin.setSingleStep(int(step) if step else 500)
        else:
            self._spin = QDoubleSpinBox()
            self._spin.setRange(min_val, max_val)
            self._spin.setValue(default)
            self._spin.setDecimals(decimals)
            self._spin.setSingleStep(step if step else 10 ** -decimals * 5)

        self._spin.setFixedWidth(90)
        top.addWidget(self._spin)
        vbox.addLayout(top)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(int(min_val * self._factor),
                              int(max_val * self._factor))
        self._slider.setValue(int(default * self._factor))
        self._slider.setFixedHeight(16)
        vbox.addWidget(self._slider)

        self._slider.valueChanged.connect(self._slider_changed)
        self._spin.valueChanged.connect(self._spin_changed)

    def _slider_changed(self, v):
        val = v / self._factor
        self._spin.blockSignals(True)
        if self._decimals == 0:
            self._spin.setValue(int(val))
        else:
            self._spin.setValue(val)
        self._spin.blockSignals(False)

    def _spin_changed(self, v):
        self._slider.blockSignals(True)
        self._slider.setValue(int(float(v) * self._factor))
        self._slider.blockSignals(False)

    @property
    def value(self):
        return float(self._spin.value())

    @value.setter
    def value(self, v):
        if self._decimals == 0:
            self._spin.setValue(int(v))
        else:
            self._spin.setValue(float(v))


# ══════════════════════════════════════════════════════════════════════════
#  Path-row widget  (label + text field + browse button)
# ══════════════════════════════════════════════════════════════════════════
class PathRow(QWidget):
    def __init__(self, label, placeholder, browse_mode="file"):
        super().__init__()
        self._mode = browse_mode
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(120)
        lbl.setStyleSheet("color: #888; font-size: 11px;")
        row.addWidget(lbl)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        row.addWidget(self.edit)

        btn = QPushButton("…")
        btn.setFixedWidth(28)
        btn.clicked.connect(self._browse)
        row.addWidget(btn)

    def _browse(self):
        current = self.edit.text().strip()
        if self._mode == "file":
            start_dir = str(Path(current).parent) if current and Path(current).parent.exists() else ""
            path, _ = QFileDialog.getOpenFileName(
                self, "Select autoremesher.exe", start_dir, "Executable (*.exe);;All Files (*)"
            )
        else:
            start_dir = current if current and Path(current).exists() else ""
            path = QFileDialog.getExistingDirectory(self, "Select Temp Folder", start_dir)
        if path:
            self.edit.setText(path)

    @property
    def value(self):
        return self.edit.text().strip()

    @value.setter
    def value(self, v):
        self.edit.setText(v)


# ══════════════════════════════════════════════════════════════════════════
#  Main Window
# ══════════════════════════════════════════════════════════════════════════
class AutoRemesherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoRemesher Bridge")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(380)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self._worker = None
        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._current_obj_name = None

        self._build_ui()
        self._load_settings()
        self.row_exe.edit.editingFinished.connect(self._save_settings)
        self.row_tmp.edit.editingFinished.connect(self._save_settings)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(14, 14, 14, 14)
        vbox.setSpacing(10)

        hdr_row = QHBoxLayout()
        hdr = QLabel("AUTOREMESHER")
        hdr.setObjectName("lbl_header")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        btn_about = QPushButton("About")
        btn_about.setFixedSize(54, 22)
        btn_about.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                color: #555;
                font-size: 10px;
            }
            QPushButton:hover { border-color: #e8823c; color: #e8823c; }
        """)
        btn_about.clicked.connect(lambda: AboutDialog(self).exec_())
        hdr_row.addWidget(btn_about)
        vbox.addLayout(hdr_row)

        sub = QLabel("QUAD REMESHING BRIDGE  ·  3DS MAX")
        sub.setObjectName("lbl_sub")
        vbox.addWidget(sub)

        grp_path = QGroupBox("Paths")
        gp = QVBoxLayout(grp_path)
        gp.setSpacing(6)
        self.row_exe = PathRow("autoremesher.exe", "Path to autoremesher.exe", "file")
        self.row_tmp = PathRow("Temp folder",
                               str(Path(tempfile.gettempdir()) / "autoremesher"), "dir")
        self.row_tmp.value = str(Path(tempfile.gettempdir()) / "autoremesher")
        gp.addWidget(self.row_exe)
        gp.addWidget(self.row_tmp)
        vbox.addWidget(grp_path)

        grp_set = QGroupBox("Remesh Settings")
        gs = QVBoxLayout(grp_set)
        gs.setSpacing(6)

        self.sld_count  = SliderRow("Target quad count",        100,  500000, 2000,  decimals=0, step=500)
        self.sld_smooth = SliderRow("Smooth normal  (0-1)",      0.0,  1.0,    0.5,   decimals=2, step=0.05)
        self.sld_sharp  = SliderRow("Sharp edge angle (deg)",    0.0,  180.0,  180.0, decimals=1, step=5.0)
        self.sld_adapt  = SliderRow("Adaptivity  (0 = uniform)", 0.0,  1.0,    1.0,   decimals=2, step=0.05)
        self.sld_edge   = SliderRow("Edge scaling",              0.1,  10.0,   1.0,   decimals=2, step=0.1)
        for w in (self.sld_count, self.sld_smooth, self.sld_sharp, self.sld_adapt, self.sld_edge):
            gs.addWidget(w)

        self.chk_keep = QCheckBox("Keep original mesh in scene")
        self.chk_keep.setChecked(True)
        gs.addWidget(self.chk_keep)

        uv_row = QHBoxLayout()
        lbl_uv = QLabel("UV map")
        lbl_uv.setStyleSheet("color: #888; font-size: 11px;")
        self.cmb_uv = QComboBox()
        self.cmb_uv.addItems([
            "Keep from remesher (auto-UV)",
            "Add UVW Map modifier (box)",
            "Add UVW Map modifier (planar)",
            "Add Unwrap UVW (manual)",
            "No UV",
        ])
        uv_row.addWidget(lbl_uv)
        uv_row.addStretch()
        uv_row.addWidget(self.cmb_uv)
        gs.addLayout(uv_row)

        vbox.addWidget(grp_set)

        self.btn_remesh = QPushButton("  Remesh Selected Mesh")
        self.btn_remesh.setObjectName("btn_remesh")
        self.btn_remesh.setFixedHeight(40)
        self.btn_remesh.clicked.connect(self._on_remesh)
        vbox.addWidget(self.btn_remesh)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("")
        self.progress.setFixedHeight(14)
        vbox.addWidget(self.progress)

        sb = QStatusBar()
        sb.setStyleSheet("QStatusBar { color: #555; font-size: 11px; }")
        self.lbl_status = QLabel("Select a mesh in 3ds Max and press Remesh.")
        self.lbl_status.setObjectName("lbl_status")
        sb.addPermanentWidget(self.lbl_status, 1)
        self.setStatusBar(sb)

    def _load_settings(self):
        self.row_exe.value    = self._settings.value("exe_path", "")
        self.row_tmp.value    = self._settings.value("tmp_path", self.row_tmp.value)
        self.sld_count.value  = float(self._settings.value("tri_count",    2000))
        self.sld_smooth.value = float(self._settings.value("smooth",       0.5))
        self.sld_sharp.value  = float(self._settings.value("sharp_edge",   180.0))
        self.sld_adapt.value  = float(self._settings.value("adaptivity",   1.0))
        self.sld_edge.value   = float(self._settings.value("edge_scaling",  1.0))
        self.chk_keep.setChecked(self._settings.value("keep_orig", True, type=bool))
        self.cmb_uv.setCurrentIndex(int(self._settings.value("uv_mode", 0)))

    def _save_settings(self):
        self._settings.setValue("exe_path",    self.row_exe.value)
        self._settings.setValue("tmp_path",    self.row_tmp.value)
        self._settings.setValue("tri_count",   self.sld_count.value)
        self._settings.setValue("smooth",      self.sld_smooth.value)
        self._settings.setValue("sharp_edge",  self.sld_sharp.value)
        self._settings.setValue("adaptivity",  self.sld_adapt.value)
        self._settings.setValue("edge_scaling",self.sld_edge.value)
        self._settings.setValue("keep_orig",   self.chk_keep.isChecked())
        self._settings.setValue("uv_mode",     self.cmb_uv.currentIndex())
        self._settings.sync()

    def _on_remesh(self):
        exe = self.row_exe.value
        if not exe or not Path(exe).is_file():
            self._set_status("autoremesher.exe path is invalid.", error=True)
            return

        if _IN_MAX:
            obj_name = _max_selected_name()
            if not obj_name:
                self._set_status("Nothing selected in 3ds Max.", error=True)
                return
        else:
            obj_name = "test_mesh"

        self._current_obj_name = obj_name

        tmp_dir  = Path(self.row_tmp.value)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        in_file  = str(tmp_dir / "input.obj")
        out_file = str(tmp_dir / "output.obj")

        for stale in (in_file, out_file):
            try:
                if Path(stale).exists():
                    Path(stale).unlink()
            except OSError:
                pass

        self._set_status("Exporting mesh…")
        self.progress.setValue(10)
        self._set_worker_running(True)
        self._save_settings()

        QTimer.singleShot(0, lambda: self._deferred_export_and_start(
            obj_name, in_file, out_file, exe))

    def _deferred_export_and_start(self, obj_name, in_file, out_file, exe):
        print("[AR] --- Remesh started: {} ---".format(obj_name))
        print("[AR] calling export...")
        if _IN_MAX:
            if not _max_export_obj(obj_name, in_file):
                self._set_status("Export failed. Is the mesh valid geometry?", error=True)
                self.progress.setValue(0)
                self._set_worker_running(False)
                return
        else:
            Path(in_file).write_text(
                "v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\n"
                "f 1 2 3\nf 1 2 4\nf 1 3 4\nf 2 3 4\n"
            )
        print("[AR] export done, starting worker...")

        self._worker = RemeshWorker(
            exe_path     = exe,
            in_file      = in_file,
            out_file     = out_file,
            target_count = int(self.sld_count.value),
            smooth       = self.sld_smooth.value,
            sharp_edge   = self.sld_sharp.value,
            adaptivity   = self.sld_adapt.value,
            edge_scaling = self.sld_edge.value,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(
            lambda ok, msg: QTimer.singleShot(0, lambda: self._on_finished(ok, msg))
        )
        self._worker.start()
        print("[AR] worker started, isRunning={}".format(self._worker.isRunning()))

    def _on_progress(self, value, msg):
        self.progress.setValue(value)
        self._set_status(msg)

    def _on_finished(self, success, message):
        self._set_worker_running(False)

        if not success:
            self.progress.setValue(0)
            self._set_status(message.splitlines()[0], error=True)
            QMessageBox.critical(self, "AutoRemesher Error", message)
            return

        tmp_dir  = Path(self.row_tmp.value)
        out_file = str(tmp_dir / "output.obj")

        if _IN_MAX:
            if not self.chk_keep.isChecked() and self._current_obj_name:
                _max_hide(self._current_obj_name)
            new_name = _max_import_obj(out_file, self._current_obj_name or "")
            label = new_name or "imported"

            uv_mode  = self.cmb_uv.currentIndex()
            safe_new = (new_name or "").replace('"', '\\"')
            if uv_mode == 1 and new_name:
                pymxs.runtime.execute('''(
                    local n = getNodeByName "{}"
                    if n != undefined do (
                        addModifier n (Uvwmap())
                        n.modifiers[#UVW_Map].maptype = 4
                    )
                )'''.format(safe_new))
            elif uv_mode == 2 and new_name:
                pymxs.runtime.execute('''(
                    local n = getNodeByName "{}"
                    if n != undefined do (
                        addModifier n (Uvwmap())
                        n.modifiers[#UVW_Map].maptype = 0
                    )
                )'''.format(safe_new))
            elif uv_mode == 3 and new_name:
                pymxs.runtime.execute('''(
                    local n = getNodeByName "{}"
                    if n != undefined do addModifier n (Unwrap_UVW())
                )'''.format(safe_new))
        else:
            label = "output.obj (not in Max)"

        self.progress.setValue(100)
        self._set_status("Done — {}".format(label))

    def _set_worker_running(self, running):
        self.btn_remesh.setEnabled(not running)
        self.progress.setFormat("" if not running else "%p%")

    def _set_status(self, msg, error=False):
        color = "#e05050" if error else "#888"
        self.lbl_status.setText(msg)
        self.lbl_status.setStyleSheet("color: {}; font-size: 11px;".format(color))

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════════════════════
#  Entry points
# ══════════════════════════════════════════════════════════════════════════
_window_ref = None


def launch():
    global _window_ref

    if _window_ref is not None:
        try:
            _window_ref.close()
        except RuntimeError:
            pass

    _window_ref = AutoRemesherWindow()
    _window_ref.setPalette(_dark_palette())
    _window_ref.setStyleSheet(_QSS)
    _window_ref.show()


if __name__ == "__main__":
    launch()
