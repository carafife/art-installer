"""
Installateur ART — moteur (sans interface graphique).

Détection des installations d'ART, interrogation des releases GitHub,
installation du bundle officiel et compilation depuis les sources.
Tout ce module est utilisable et testable sans GTK.
"""

import glob
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "Installateur ART"
APP_ID = "io.github.carafife.ArtInstaller"
APP_VERSION = "1.0.0"
PROJECT_URL = "https://github.com/carafife/art-installer"
HELP_URL = PROJECT_URL + "/blob/main/AIDE.md"

REPO = "artraweditor/ART"
GIT_URL = f"https://github.com/{REPO}.git"
API_RELEASES = f"https://api.github.com/repos/{REPO}/releases?per_page=20"

HOME = Path.home()
BUNDLE_PARENT = HOME / "programs"
SOURCE_DIR = HOME / "programs" / "ART-source"
BINDIR = HOME / ".local" / "bin"
APPS_DIR = HOME / ".local" / "share" / "applications"
ICONS_DIR = HOME / ".local" / "share" / "icons"
LOG_DIR = HOME / ".cache" / "art-installer"

# Marqueur posé dans le lanceur .desktop créé pour un bundle : permet de
# savoir qu'il nous appartient (et donc qu'on peut le remplacer/retirer).
DESKTOP_MARK = "X-ART-Installer=bundle"

# ---------------------------------------------------------------------------
# Dépendances de compilation (Fedora / dnf)
# ---------------------------------------------------------------------------
DNF_BASE = [
    "git", "cmake", "make", "gcc-c++", "pkgconf-pkg-config",
    "gtk3-devel", "gtkmm30-devel", "glibmm24-devel", "cairomm-devel",
    "libsigc++20-devel", "lensfun-devel", "librsvg2-devel", "exiv2-devel",
    "lcms2-devel", "expat-devel", "fftw-devel", "libtiff-devel",
    "libcanberra-devel", "libjpeg-turbo-devel", "libpng-devel", "zlib-devel",
]
DNF_FEATURES = {
    "ctl": ["ctl-devel", "openexr-devel"],
    "ocio": ["OpenColorIO-devel"],
    "libraw": ["LibRaw-devel"],
    "mimalloc": ["mimalloc-devel"],
    "vulkan": ["vulkan-headers", "vulkan-loader-devel", "glslc"],
}

# Correspondance option de l'interface -> option CMake d'ART
CMAKE_FEATURES = {
    "ctl": "ENABLE_CTL",
    "ocio": "ENABLE_OCIO",
    "libraw": "ENABLE_LIBRAW",
    "mimalloc": "ENABLE_MIMALLOC",
    "vulkan": "ENABLE_VULKAN",
}


def has(cmd):
    return shutil.which(cmd) is not None


def arch_tag():
    m = os.uname().machine
    if m == "x86_64":
        return "linux64"
    if m in ("aarch64", "arm64"):
        return "linux-aarch64"
    return None


def human_size(n):
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return f"{n:.0f} {unit}" if unit in ("o", "Ko") else f"{n:.1f} {unit}"
        n /= 1024


# ---------------------------------------------------------------------------
# Détection
# ---------------------------------------------------------------------------
KIND_LABELS = {
    "bundle": "Bundle officiel",
    "compile": "Compilé depuis les sources",
    "systeme": "Paquet de la distribution",
    "flatpak": "Flatpak",
    "appimage": "AppImage",
}


@dataclass
class ArtInstall:
    path: str                 # exécutable, ou identifiant Flatpak
    kind: str                 # clé de KIND_LABELS
    version: str = None
    ctl: bool = None          # None = inconnu
    ocio: bool = None
    vulkan: bool = None
    active: bool = False      # celui lancé par la commande « ART »

    @property
    def kind_label(self):
        return KIND_LABELS.get(self.kind, self.kind)


def about_file_for(exe):
    """Trouve AboutThisBuild.txt d'un exécutable ART (bundle ou compilé)."""
    real = Path(os.path.realpath(exe))
    for cand in (real.parent / "AboutThisBuild.txt",
                 real.parent.parent / "share" / "doc" / "ART" / "AboutThisBuild.txt"):
        if cand.is_file():
            return cand
    return None


def parse_about(path):
    info = {}
    try:
        for line in Path(path).read_text(errors="replace").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
    except OSError:
        pass
    return info


def _feature(value):
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("", "no", "off", "none", "n/a", "false", "0", "disabled", "not found"):
        return False
    return True


def _clean_version(v):
    if not v:
        return None
    m = re.search(r"\d+(\.\d+)+(-\d+-g[0-9a-f]+)?", v)
    return m.group(0) if m else v


def _classify(real):
    s = str(real)
    if s.lower().endswith(".appimage"):
        return "appimage"
    parent = Path(real).parent
    if (parent / "AboutThisBuild.txt").is_file():
        # Un bundle téléchargé s'appelle ART-<version>-linux64 ;
        # un dossier build/Release est une compilation en mode bundle.
        return "bundle" if parent.name.startswith("ART-") else "compile"
    if s.startswith("/usr/bin/") or s.startswith("/bin/"):
        return "systeme"
    return "compile"


def _inspect(exe, active_real):
    real = os.path.realpath(exe)
    inst = ArtInstall(path=real, kind=_classify(real), active=(real == active_real))
    if inst.kind == "appimage":
        inst.version = _clean_version(Path(real).name)
        return inst
    about = about_file_for(real)
    if about:
        info = parse_about(about)
        inst.version = _clean_version(info.get("Version"))
        inst.ctl = _feature(info.get("CTL interpreter"))
        inst.ocio = _feature(info.get("OpenColorIO"))
        inst.vulkan = _feature(info.get("Vulkan"))
    if inst.ctl is None and has("ldd"):
        try:
            out = subprocess.run(["ldd", real], capture_output=True, text=True, timeout=10).stdout
            if "IlmCtl" in out:
                inst.ctl = True
        except (OSError, subprocess.SubprocessError):
            pass
    return inst


def detect():
    """Liste toutes les installations d'ART trouvées sur la machine."""
    candidates = []
    for name in ("ART", "art"):
        w = shutil.which(name)
        if w:
            candidates.append(w)
    candidates += [
        "/usr/bin/ART", "/usr/local/bin/ART", str(BINDIR / "ART"),
    ]
    for pattern in ("programs/*/ART", "Programmes/*/ART", "Programmes/*/*/ART",
                    "programs/*/build/Release/ART", "Programmes/*/build/Release/ART",
                    "programs/ART-source/build/Release/ART"):
        candidates += glob.glob(str(HOME / pattern))
    appimage_re = re.compile(r"^ART[-_.].*\.appimage$", re.I)
    for d in ("Applications", "Téléchargements", "Downloads", "programs", "Programmes", "bin"):
        folder = HOME / d
        if folder.is_dir():
            for f in folder.iterdir():
                if appimage_re.match(f.name):
                    candidates.append(str(f))

    active = shutil.which("ART")
    active_real = os.path.realpath(active) if active else None

    found, seen = [], set()
    for c in candidates:
        if not (os.path.isfile(c) and os.access(c, os.X_OK)):
            continue
        real = os.path.realpath(c)
        if real in seen:
            continue
        seen.add(real)
        found.append(_inspect(c, active_real))

    if has("flatpak"):
        try:
            out = subprocess.run(["flatpak", "list", "--app", "--columns=application,version"],
                                 capture_output=True, text=True, timeout=15).stdout
            for line in out.splitlines():
                parts = line.split("\t")
                app = parts[0].strip()
                if re.search(r"(^|\.)ART$", app):
                    ver = parts[1].strip() if len(parts) > 1 else None
                    found.append(ArtInstall(path=app, kind="flatpak", version=ver or None))
        except (OSError, subprocess.SubprocessError):
            pass

    found.sort(key=lambda i: (not i.active, i.kind))
    return found


# ---------------------------------------------------------------------------
# Releases GitHub
# ---------------------------------------------------------------------------
@dataclass
class ReleaseInfo:
    latest: str = None         # dernière version publiée (sources)
    bundle_version: str = None  # dernière version ayant un bundle Linux
    bundle_url: str = None
    bundle_size: int = 0
    bundle_name: str = None


def fetch_releases(timeout=15):
    req = urllib.request.Request(API_RELEASES, headers={
        "User-Agent": "art-installer",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    info = ReleaseInfo()
    tag = arch_tag()
    asset_re = re.compile(rf"^ART-.+-{re.escape(tag)}\.tar\.xz$") if tag else None
    for rel in data:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        version = rel.get("tag_name", "").lstrip("v")
        if info.latest is None:
            info.latest = version
        if asset_re and info.bundle_url is None:
            for a in rel.get("assets", []):
                if asset_re.match(a.get("name", "")):
                    info.bundle_version = version
                    info.bundle_url = a["browser_download_url"]
                    info.bundle_size = a.get("size", 0)
                    info.bundle_name = a["name"]
                    break
        if info.latest and info.bundle_url:
            break
    return info


# ---------------------------------------------------------------------------
# Exécution des étapes
# ---------------------------------------------------------------------------
class Cancelled(Exception):
    pass


class StepError(Exception):
    pass


@dataclass
class Step:
    title: str
    fn: object  # callable(runner)


@dataclass
class Result:
    version: str = None
    exe: str = None
    ctl: bool = None
    ocio: bool = None
    vulkan: bool = None
    dest: str = None
    notes: list = field(default_factory=list)


class Runner:
    """Exécute des commandes en relayant journal et progression."""

    def __init__(self, on_log, on_progress):
        self.on_log = on_log
        self.on_progress = on_progress
        self.cancelled = False
        self.proc = None
        self.result = Result()

    def log(self, text):
        self.on_log(text)

    def progress(self, frac):
        self.on_progress(frac)

    def check(self):
        if self.cancelled:
            raise Cancelled()

    def cancel(self):
        self.cancelled = True
        p = self.proc
        if p and p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except (OSError, PermissionError):
                pass

    def run(self, cmd, cwd=None, progress_re=None, env=None):
        self.check()
        self.log("$ " + shlex.join(cmd))
        full_env = dict(os.environ, LC_ALL="C", **(env or {}))
        try:
            p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, bufsize=1,
                                 errors="replace", env=full_env, start_new_session=True)
        except FileNotFoundError:
            raise StepError(f"Commande introuvable : {cmd[0]}")
        self.proc = p
        for line in p.stdout:
            self.log(line.rstrip("\n"))
            if progress_re:
                m = progress_re.search(line)
                if m:
                    self.progress(int(m.group(1)) / 100)
            if self.cancelled:
                break
        rc = p.wait()
        self.proc = None
        self.check()
        if rc != 0:
            if cmd[0] == "pkexec" and rc in (126, 127):
                raise StepError("Autorisation administrateur refusée ou annulée.")
            raise StepError(f"La commande « {cmd[0]} » a échoué (code {rc}). Voir les détails.")

    def download(self, url, dest):
        self.log(f"Téléchargement : {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "art-installer"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                self.check()
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    self.progress(done / total)
        self.log(f"Reçu : {human_size(done)}")


# ---------------------------------------------------------------------------
# Intégration au bureau
# ---------------------------------------------------------------------------
def _remove_bundle_links(runner):
    """Retire les liens ~/.local/bin/ART(-cli) qui pointent vers un bundle,
    et le lanceur .desktop créé par cet installateur."""
    for n in ("ART", "ART-cli"):
        p = BINDIR / n
        if p.is_symlink():
            p.unlink()
            runner.log(f"Lien retiré : {p}")
    desk = APPS_DIR / "ART.desktop"
    try:
        if desk.is_file() and DESKTOP_MARK in desk.read_text(errors="replace"):
            desk.unlink()
            runner.log(f"Ancien lanceur du bundle retiré : {desk}")
    except OSError:
        pass


def _write_bundle_desktop(dest, exe_cmd):
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    icon = "ART"
    for sz in (256, 128, 512, 64, 48):
        src = Path(dest) / "images" / f"ART-logo-{sz}.png"
        if src.is_file():
            shutil.copyfile(src, ICONS_DIR / "ART.png")
            icon = str(ICONS_DIR / "ART.png")
            break
    desk = APPS_DIR / "ART.desktop"
    desk.write_text(f"""[Desktop Entry]
Version=1.0
Type=Application
Name=ART
GenericName=Éditeur RAW
Comment=Développement photo RAW
Exec={exe_cmd} %F
Icon={icon}
Terminal=false
Categories=Graphics;Photography;
MimeType=image/x-dcraw;image/x-adobe-dng;image/x-canon-cr2;image/x-canon-cr3;image/x-nikon-nef;image/x-sony-arw;image/x-fuji-raf;image/x-olympus-orf;image/x-panasonic-rw2;image/x-pentax-pef;image/tiff;image/jpeg;image/png;
StartupNotify=true
{DESKTOP_MARK}
""")
    desk.chmod(0o755)
    if has("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(APPS_DIR)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return desk


def old_bundles(parent, keep):
    tag = arch_tag() or "linux64"
    keep = os.path.realpath(keep) if keep else None
    return sorted(d for d in glob.glob(str(Path(parent) / f"ART-*-{tag}"))
                  if os.path.isdir(d) and os.path.realpath(d) != keep)


def _fill_result_from(runner, exe, dest):
    r = runner.result
    r.exe, r.dest = str(exe), str(dest)
    about = about_file_for(exe)
    if about:
        info = parse_about(about)
        r.version = _clean_version(info.get("Version")) or r.version
        r.ctl = _feature(info.get("CTL interpreter"))
        r.ocio = _feature(info.get("OpenColorIO"))
        r.vulkan = _feature(info.get("Vulkan"))
        runner.log(f"AboutThisBuild : version={r.version} CTL={r.ctl} OCIO={r.ocio} Vulkan={r.vulkan}")
    else:
        runner.log("AboutThisBuild.txt introuvable : fonctionnalités non vérifiées.")


# ---------------------------------------------------------------------------
# Plan : bundle officiel
# ---------------------------------------------------------------------------
def plan_bundle(release, parent=BUNDLE_PARENT, links=True, desktop=True):
    parent = Path(parent).expanduser()
    state = {}

    def s_download(rn):
        parent.mkdir(parents=True, exist_ok=True)
        state["tmp"] = tempfile.mkdtemp(prefix=".art-installer-", dir=parent)
        state["archive"] = os.path.join(state["tmp"], release.bundle_name)
        rn.result.version = release.bundle_version
        rn.download(release.bundle_url, state["archive"])

    def s_extract(rn):
        rn.progress(None)
        try:
            with tarfile.open(state["archive"], "r:xz") as t:
                first = t.next()
            top = first.name.split("/")[0] if first else None
        except tarfile.TarError as e:
            raise StepError(f"Archive illisible : {e}")
        if not top:
            raise StepError("Archive vide.")
        dest = parent / top
        rn.run(["tar", "-xf", state["archive"], "-C", str(parent)])
        shutil.rmtree(state["tmp"], ignore_errors=True)
        exe = dest / "ART"
        if not exe.is_file():
            raise StepError(f"Binaire ART introuvable après extraction : {exe}")
        state["dest"], state["exe"] = dest, exe
        rn.log(f"Extrait dans : {dest}")

    def s_integrate(rn):
        dest, exe = state["dest"], state["exe"]
        exe_cmd = str(exe)
        if links:
            BINDIR.mkdir(parents=True, exist_ok=True)
            blocked = [n for n in ("ART", "ART-cli")
                       if (BINDIR / n).exists() and not (BINDIR / n).is_symlink()]
            if blocked:
                msg = (f"{BINDIR}/ART est un ART compilé : il n'a pas été remplacé. "
                       f"Le bundle se lance depuis le menu ou via {exe}.")
                rn.log("!! " + msg)
                rn.result.notes.append(msg)
            else:
                for n in ("ART", "ART-cli"):
                    link = BINDIR / n
                    if link.is_symlink():
                        link.unlink()
                    link.symlink_to(dest / n)
                    rn.log(f"Lien : {link} → {dest / n}")
                exe_cmd = str(BINDIR / "ART")
                if str(BINDIR) not in os.environ.get("PATH", "").split(":"):
                    rn.result.notes.append(
                        "~/.local/bin n'est pas dans ton PATH : ajoute "
                        "export PATH=\"$HOME/.local/bin:$PATH\" à ~/.bashrc.")
        if desktop:
            desk = APPS_DIR / "ART.desktop"
            ours = (not desk.exists()) or DESKTOP_MARK in desk.read_text(errors="replace")
            if ours:
                _write_bundle_desktop(dest, exe_cmd)
                rn.log(f"Lanceur créé : {desk}")
            else:
                rn.log(f"!! {desk} existe déjà (ART compilé) : laissé tel quel.")

    def s_verify(rn):
        _fill_result_from(rn, state["exe"], state["dest"])

    def cleanup():
        if state.get("tmp"):
            shutil.rmtree(state["tmp"], ignore_errors=True)

    steps = [
        Step(f"Télécharger ART {release.bundle_version}", s_download),
        Step("Extraire l'archive", s_extract),
        Step("Intégrer au bureau", s_integrate),
        Step("Vérifier l'installation", s_verify),
    ]
    return steps, cleanup


# ---------------------------------------------------------------------------
# Plan : compilation
# ---------------------------------------------------------------------------
@dataclass
class CompileOptions:
    ref: str = "master"            # tag de version, ou "master"
    system_wide: bool = False      # False : ~/.local, True : /usr/local
    src_dir: str = str(SOURCE_DIR)
    install_deps: bool = True
    features: dict = field(default_factory=lambda: {
        "ctl": True, "ocio": True, "libraw": True, "mimalloc": True, "vulkan": False})
    native: bool = True
    lto: bool = False
    jobs: int = os.cpu_count() or 2

    @property
    def prefix(self):
        return "/usr/local" if self.system_wide else str(HOME / ".local")

    @property
    def build_dir(self):
        return str(Path(self.src_dir).expanduser() / "build")


def dnf_packages(opts):
    pkgs = list(DNF_BASE)
    for key, on in opts.features.items():
        if on:
            pkgs += DNF_FEATURES.get(key, [])
    return pkgs


def cmake_command(opts):
    src = str(Path(opts.src_dir).expanduser())
    cmd = ["cmake", "-S", src, "-B", opts.build_dir,
           "-DCMAKE_BUILD_TYPE=Release",
           f"-DCMAKE_INSTALL_PREFIX={opts.prefix}",
           "-DCACHE_NAME_SUFFIX=",
           "-DBUILD_BUNDLE=OFF"]
    for key, var in CMAKE_FEATURES.items():
        cmd.append(f"-D{var}={'ON' if opts.features.get(key) else 'OFF'}")
    if opts.features.get("ctl") and os.path.isdir("/usr/include/CTL"):
        cmd.append("-DCTL_INCLUDE_DIR=/usr/include/CTL")
    cmd.append(f"-DPROC_TARGET_NUMBER={2 if opts.native else 0}")
    cmd.append(f"-DWITH_LTO={'ON' if opts.lto else 'OFF'}")
    return cmd


def plan_compile(opts):
    src = Path(opts.src_dir).expanduser()
    progress_re = re.compile(r"^\[\s*(\d+)%\]")

    def s_deps(rn):
        rn.progress(None)
        pkgs = dnf_packages(opts)
        if not has("dnf"):
            raise StepError("dnf introuvable. Installe les dépendances à la main : " + " ".join(pkgs))
        if not has("pkexec"):
            raise StepError("pkexec introuvable. Lance d'abord : sudo dnf install " + " ".join(pkgs))
        rn.run(["pkexec", "dnf", "install", "-y", "--skip-unavailable", *pkgs])

    def s_sources(rn):
        rn.progress(None)
        if (src / ".git").is_dir():
            rn.run(["git", "-C", str(src), "fetch", "--tags", "--force", "origin"])
        else:
            src.parent.mkdir(parents=True, exist_ok=True)
            if src.exists() and any(src.iterdir()):
                raise StepError(f"{src} existe et n'est pas un dépôt git. Choisis un autre dossier.")
            rn.run(["git", "clone", "--filter=blob:none", "--progress", GIT_URL, str(src)])
        if opts.ref == "master":
            rn.run(["git", "-C", str(src), "checkout", "--force", "master"])
            rn.run(["git", "-C", str(src), "reset", "--hard", "origin/master"])
        else:
            rn.run(["git", "-C", str(src), "checkout", "--force", opts.ref])
        out = subprocess.run(["git", "-C", str(src), "describe", "--tags", "--always"],
                             capture_output=True, text=True).stdout.strip()
        rn.result.version = _clean_version(out) or out
        rn.log(f"Version des sources : {out}")

    def s_configure(rn):
        rn.progress(None)
        # Repartir d'un cache propre : les options choisies s'appliquent à coup sûr.
        cache = Path(opts.build_dir) / "CMakeCache.txt"
        if cache.exists():
            cache.unlink()
        rn.run(cmake_command(opts))

    def s_build(rn):
        rn.progress(0)
        rn.run(["cmake", "--build", opts.build_dir, "--parallel", str(opts.jobs)],
               progress_re=progress_re)

    def s_install(rn):
        rn.progress(None)
        _remove_bundle_links(rn)
        cmd = ["cmake", "--install", opts.build_dir]
        if opts.system_wide:
            cmd = ["pkexec", *cmd]
        rn.run(cmd)
        for tool, args in (("update-desktop-database", [str(Path(opts.prefix) / "share/applications")]),
                           ("gtk-update-icon-cache", ["-q", "-t", str(Path(opts.prefix) / "share/icons/hicolor")])):
            if has(tool) and not opts.system_wide:
                subprocess.run([tool, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def s_verify(rn):
        exe = Path(opts.prefix) / "bin" / "ART"
        if not exe.is_file():
            raise StepError(f"{exe} introuvable après l'installation.")
        _fill_result_from(rn, exe, opts.prefix)
        if opts.features.get("ctl") and rn.result.ctl is False:
            rn.result.notes.append("Le CTL a été demandé mais n'est pas actif : "
                                   "vérifie que ctl-devel et openexr-devel sont installés.")
        if opts.features.get("vulkan") and rn.result.vulkan is False:
            rn.result.notes.append("Vulkan a été demandé mais n'est pas actif : "
                                   "vérifie vulkan-headers, vulkan-loader-devel et glslc.")
        active = shutil.which("ART")
        if active and os.path.realpath(active) != os.path.realpath(exe):
            rn.result.notes.append(f"Attention : la commande « ART » lance encore {active}.")

    def cleanup():
        pass

    steps = []
    if opts.install_deps:
        steps.append(Step("Installer les dépendances", s_deps))
    steps += [
        Step("Récupérer les sources", s_sources),
        Step("Configurer (CMake)", s_configure),
        Step("Compiler", s_build),
        Step("Installer", s_install),
        Step("Vérifier l'installation", s_verify),
    ]
    return steps, cleanup
