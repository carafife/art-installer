#!/usr/bin/env python3
"""
Installateur ART — interface GTK4 / libadwaita.

Programme indépendant pour installer, mettre à jour ou compiler ART
(Another RawTherapee), le développeur de photos RAW libre.
Licence : GPL-3.0-or-later
"""

import os
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core  # noqa: E402

LOGO = HERE / "data" / "io.github.carafife.ArtInstaller.png"

CSS = """
.hero-title { font-size: 24pt; font-weight: 800; letter-spacing: -0.5px; }
.hero-sub { font-size: 11.5pt; }
.pill { border-radius: 999px; padding: 1px 9px; font-size: 8.5pt; font-weight: 700; }
.pill-yes { background: alpha(@success_color, 0.16); color: @success_color; }
.pill-no { background: alpha(@error_color, 0.14); color: @error_color; }
.pill-unk { background: alpha(currentColor, 0.08); color: alpha(currentColor, 0.6); }
.pill-active { background: alpha(@accent_bg_color, 0.18); color: @accent_color; }
.log-view { font-family: monospace; font-size: 9pt; padding: 8px; }
.log-frame { border-radius: 12px; }
.step-title { font-size: 15pt; font-weight: 700; }
.choice-title { font-weight: 700; }
.bottom-bar { padding: 12px; }
"""


def pill(text, kind):
    lbl = Gtk.Label(label=text, valign=Gtk.Align.CENTER)
    lbl.add_css_class("pill")
    lbl.add_css_class(f"pill-{kind}")
    return lbl


def feature_pill(name, value):
    if value is True:
        return pill(f"{name} ✓", "yes")
    if value is False:
        return pill(f"sans {name}", "no")
    return pill(f"{name} ?", "unk")


def logo_image(size):
    img = Gtk.Image.new_from_file(str(LOGO))
    img.set_pixel_size(size)
    return img


def tilde(path):
    p = str(path)
    home = str(Path.home())
    return "~" + p[len(home):] if p.startswith(home) else p


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=core.APP_NAME)
        self.set_default_size(780, 760)
        self.releases = None
        self.release_error = None
        self.installs = []
        self.runner = None
        self.running = False

        self.toasts = Adw.ToastOverlay()
        self.nav = Adw.NavigationView()
        self.toasts.set_child(self.nav)
        self.set_content(self.toasts)

        self.nav.add(self.build_welcome())
        self.connect("close-request", self.on_close_request)
        self.refresh()

    # ------------------------------------------------------------------ helpers
    def make_page(self, title, tag, body, bottom=None, menu=False, can_pop=True):
        tv = Adw.ToolbarView()
        header = Adw.HeaderBar()
        if menu:
            mb = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text="Menu")
            m = Gio.Menu()
            m.append("Réanalyser", "win.refresh")
            m.append("Aide", "win.help")
            m.append(f"À propos de l'{core.APP_NAME}", "win.about")
            mb.set_menu_model(m)
            header.pack_end(mb)
        tv.add_top_bar(header)
        clamp = Adw.Clamp(maximum_size=660, tightening_threshold=480)
        clamp.set_child(body)
        sc = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        sc.set_child(clamp)
        tv.set_content(sc)
        if bottom:
            tv.add_bottom_bar(bottom)
        page = Adw.NavigationPage(title=title, tag=tag, child=tv)
        page.set_can_pop(can_pop)
        return page

    def vbox(self, spacing=24):
        return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing,
                       margin_top=24, margin_bottom=24, margin_start=16, margin_end=16)

    def bottom_bar(self, *buttons):
        box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        box.add_css_class("bottom-bar")
        for b in buttons:
            box.append(b)
        return box

    def button(self, label, cb, style="suggested-action"):
        b = Gtk.Button(label=label)
        b.add_css_class("pill")
        if style:
            b.add_css_class(style)
        b.connect("clicked", cb)
        return b

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=4))

    # ------------------------------------------------------------------ accueil
    def build_welcome(self):
        body = self.vbox()

        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hero.append(logo_image(128))
        t = Gtk.Label(label=core.APP_NAME)
        t.add_css_class("hero-title")
        hero.append(t)
        s = Gtk.Label(label="Installer, mettre à jour ou compiler ART,\nle développeur de photos RAW libre.",
                      justify=Gtk.Justification.CENTER, wrap=True)
        s.add_css_class("hero-sub")
        s.add_css_class("dim-label")
        hero.append(s)
        body.append(hero)

        self.found_group = Adw.PreferencesGroup(title="ART sur cet ordinateur")
        rb = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Réanalyser",
                        valign=Gtk.Align.CENTER)
        rb.add_css_class("flat")
        rb.connect("clicked", lambda *_: self.refresh())
        self.found_group.set_header_suffix(rb)
        body.append(self.found_group)
        self.found_rows = []

        self.rel_group = Adw.PreferencesGroup(title="Versions disponibles",
                                              description="Source : dépôt officiel artraweditor/ART sur GitHub")
        self.row_latest = Adw.ActionRow(title="Dernière version", subtitle="…")
        self.row_bundle = Adw.ActionRow(title="Dernier bundle Linux prêt à l'emploi", subtitle="…")
        for r in (self.row_latest, self.row_bundle):
            r.add_css_class("property")
            self.rel_group.add(r)
        body.append(self.rel_group)

        self.btn_continue = self.button("Continuer", lambda *_: self.nav.push(self.build_method()))
        self.btn_continue.set_sensitive(False)

        act = Gio.SimpleAction(name="refresh")
        act.connect("activate", lambda *_: self.refresh())
        self.add_action(act)
        act = Gio.SimpleAction(name="about")
        act.connect("activate", lambda *_: self.show_about())
        self.add_action(act)
        act = Gio.SimpleAction(name="help")
        act.connect("activate", lambda *_: self.show_help())
        self.add_action(act)

        return self.make_page(core.APP_NAME, "welcome", body,
                              self.bottom_bar(self.btn_continue), menu=True)

    def set_found_rows(self, rows):
        for r in self.found_rows:
            self.found_group.remove(r)
        self.found_rows = rows
        for r in rows:
            self.found_group.add(r)

    def refresh(self):
        self.btn_continue.set_sensitive(False)
        spin_row = Adw.ActionRow(title="Recherche des installations d'ART…")
        spin_row.add_prefix(Gtk.Spinner(spinning=True))
        self.set_found_rows([spin_row])
        self.row_latest.set_subtitle("Interrogation de GitHub…")
        self.row_bundle.set_subtitle("…")

        def work():
            installs = core.detect()
            GLib.idle_add(self.on_detected, installs)
            try:
                rel, err = core.fetch_releases(), None
            except Exception as e:  # réseau, quota GitHub…
                rel, err = None, str(e)
            GLib.idle_add(self.on_releases, rel, err)

        threading.Thread(target=work, daemon=True).start()

    def on_detected(self, installs):
        self.installs = installs
        rows = []
        if not installs:
            r = Adw.ActionRow(title="Aucune installation d'ART détectée",
                              subtitle="Pas de souci : c'est justement le rôle de cet installateur.")
            r.add_prefix(Gtk.Image(icon_name="dialog-information-symbolic"))
            rows.append(r)
        for inst in installs:
            r = Adw.ActionRow(title=f"ART {inst.version or '(version inconnue)'}",
                              subtitle=f"{inst.kind_label} — {tilde(inst.path)}")
            r.set_use_markup(False)
            r.set_subtitle_lines(2)
            icon = {"bundle": "package-x-generic-symbolic", "compile": "applications-engineering-symbolic",
                    "flatpak": "system-software-install-symbolic", "appimage": "application-x-executable-symbolic",
                    "systeme": "computer-symbolic"}.get(inst.kind, "image-x-generic-symbolic")
            r.add_prefix(Gtk.Image(icon_name=icon))
            box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
            if inst.active:
                box.append(pill("par défaut", "active"))
            if inst.kind not in ("flatpak", "appimage"):
                box.append(feature_pill("CTL", inst.ctl))
                box.append(feature_pill("OCIO", inst.ocio))
                if inst.vulkan:
                    box.append(feature_pill("Vulkan", True))
            r.add_suffix(box)
            rows.append(r)
        if any(i.kind in ("flatpak", "appimage") for i in installs):
            r = Adw.ActionRow(title="Flatpak / AppImage : fonctionnement isolé",
                              subtitle="Ces versions accèdent mal aux scripts CTL et aux outils externes. "
                                       "Le bundle officiel ou une compilation est recommandé.")
            r.add_prefix(Gtk.Image(icon_name="dialog-warning-symbolic"))
            rows.append(r)
        self.set_found_rows(rows)
        return False

    def on_releases(self, rel, err):
        self.releases, self.release_error = rel, err
        if rel is None:
            self.row_latest.set_subtitle("Impossible de joindre GitHub — vérifie la connexion")
            self.row_bundle.set_subtitle(err or "")
            self.btn_continue.set_sensitive(False)
            return False
        self.row_latest.set_subtitle(rel.latest or "inconnue")
        if rel.bundle_version:
            self.row_bundle.set_subtitle(f"{rel.bundle_version}  ·  {core.human_size(rel.bundle_size)}")
        else:
            self.row_bundle.set_subtitle(f"Aucun pour cette architecture ({os.uname().machine})")
        self.btn_continue.set_sensitive(True)
        return False

    # ------------------------------------------------------------------ méthode
    def build_method(self):
        rel = self.releases
        body = self.vbox()

        intro = Gtk.Label(label="Comment veux-tu installer ART ?", xalign=0, wrap=True)
        intro.add_css_class("title-2")
        body.append(intro)

        group = Adw.PreferencesGroup()
        self.chk_bundle = Gtk.CheckButton(valign=Gtk.Align.CENTER)
        self.chk_compile = Gtk.CheckButton(valign=Gtk.Align.CENTER, group=self.chk_bundle)

        r1 = Adw.ActionRow(title="Bundle officiel  —  recommandé")
        if rel.bundle_version:
            r1.set_subtitle(f"ART {rel.bundle_version}, prêt à l'emploi, CTL et OCIO inclus.\n"
                            f"Téléchargement de {core.human_size(rel.bundle_size)}, quelques minutes.")
        else:
            r1.set_subtitle("Aucun bundle Linux disponible pour cet ordinateur.")
            r1.set_sensitive(False)
        r1.add_prefix(self.chk_bundle)
        r1.set_activatable_widget(self.chk_bundle)

        r2 = Adw.ActionRow(title="Compiler depuis les sources")
        r2.set_subtitle(f"Toute dernière version ({rel.latest}), options au choix : CTL, OCIO, Vulkan…\n"
                        "Compte 20 à 40 minutes et environ 2 Go d'espace disque.")
        r2.add_prefix(self.chk_compile)
        r2.set_activatable_widget(self.chk_compile)
        for r in (r1, r2):
            group.add(r)
        body.append(group)

        if rel.bundle_version:
            self.chk_bundle.set_active(True)
        else:
            self.chk_compile.set_active(True)

        if rel.bundle_version and rel.latest and rel.bundle_version != rel.latest:
            note = Adw.PreferencesGroup()
            nr = Adw.ActionRow(title=f"ART {rel.latest} n'a pas encore de bundle Linux",
                               subtitle=f"Le bundle installera la {rel.bundle_version}. "
                                        f"Pour avoir la {rel.latest} tout de suite, choisis la compilation.")
            nr.add_prefix(Gtk.Image(icon_name="dialog-information-symbolic"))
            note.add(nr)
            body.append(note)

        def go(*_):
            if self.chk_bundle.get_active():
                self.nav.push(self.build_bundle_options())
            else:
                self.nav.push(self.build_compile_options())

        return self.make_page("Méthode", "method", body,
                              self.bottom_bar(self.button("Continuer", go)))

    # ------------------------------------------------------------------ options bundle
    def build_bundle_options(self):
        rel = self.releases
        body = self.vbox()

        g1 = Adw.PreferencesGroup(title="Emplacement",
                                  description=f"Le bundle sera extrait dans un sous-dossier "
                                              f"{rel.bundle_name.removesuffix('.tar.xz')}")
        self.e_parent = Adw.EntryRow(title="Dossier d'installation", text=tilde(core.BUNDLE_PARENT))
        g1.add(self.e_parent)
        body.append(g1)

        g2 = Adw.PreferencesGroup(title="Intégration")
        self.sw_links = Adw.SwitchRow(title="Commandes « ART » et « ART-cli » dans le terminal",
                                      subtitle="Liens dans ~/.local/bin", active=True)
        self.sw_desktop = Adw.SwitchRow(title="Icône dans le menu des applications", active=True)
        self.sw_clean = Adw.SwitchRow(title="Proposer de supprimer les anciens bundles",
                                      subtitle="Uniquement les bundles téléchargés. Une confirmation sera demandée.",
                                      active=False)
        for r in (self.sw_links, self.sw_desktop, self.sw_clean):
            g2.add(r)
        body.append(g2)

        def start(*_):
            parent = Path(os.path.expanduser(self.e_parent.get_text().strip() or str(core.BUNDLE_PARENT)))
            steps, cleanup = core.plan_bundle(rel, parent, self.sw_links.get_active(),
                                              self.sw_desktop.get_active())
            self.after_success = (lambda: self.offer_cleanup(parent)) if self.sw_clean.get_active() else None
            self.start_run(f"Installation d'ART {rel.bundle_version}", steps, cleanup)

        return self.make_page("Bundle officiel", "bundle", body,
                              self.bottom_bar(self.button("Installer", start)))

    # ------------------------------------------------------------------ options compilation
    def build_compile_options(self):
        rel = self.releases
        body = self.vbox()
        o = core.CompileOptions()

        g1 = Adw.PreferencesGroup(title="Version")
        self.c_ref = Adw.ComboRow(title="Version à compiler",
                                  model=Gtk.StringList.new([f"Stable — {rel.latest}",
                                                            "Développement — master"]))
        g1.add(self.c_ref)
        body.append(g1)

        g2 = Adw.PreferencesGroup(title="Emplacement")
        self.c_prefix = Adw.ComboRow(title="Installer pour",
                                     model=Gtk.StringList.new(["Moi seulement (~/.local)",
                                                               "Tous les utilisateurs (/usr/local)"]))
        self.c_prefix.set_subtitle("Sans mot de passe")
        self.c_prefix.connect("notify::selected", lambda r, *_: r.set_subtitle(
            "Mot de passe administrateur demandé" if r.get_selected() else "Sans mot de passe"))
        self.e_src = Adw.EntryRow(title="Dossier des sources", text=tilde(o.src_dir))
        self.pkg_mgr = core.package_manager()
        self.sw_deps = Adw.SwitchRow(
            title="Installer les dépendances automatiquement",
            subtitle=f"Via {self.pkg_mgr}, mot de passe administrateur demandé" if self.pkg_mgr
            else f"Gestionnaire de paquets non reconnu sur {core.distro_name()} : "
                 "installe les dépendances toi-même",
            active=bool(self.pkg_mgr), sensitive=bool(self.pkg_mgr))
        for r in (self.c_prefix, self.e_src, self.sw_deps):
            g2.add(r)
        body.append(g2)

        g3 = Adw.PreferencesGroup(title="Fonctionnalités")
        specs = [
            ("ctl", "Scripts CTL", "Simulations de film et scripts couleur (recommandé)"),
            ("ocio", "OpenColorIO", "Application de LUT et transformations de couleur"),
            ("libraw", "LibRaw", "Décodage complémentaire, utile pour les boîtiers récents"),
            ("mimalloc", "mimalloc", "Allocateur mémoire plus rapide"),
            ("vulkan", "Accélération GPU Vulkan  —  expérimental",
             "Calcul sur la carte graphique (AMD, Intel, NVIDIA)"),
        ]
        sans_paquet = core.unsupported_features(self.pkg_mgr) if self.pkg_mgr else []
        self.sw_feat = {}
        for key, title, sub in specs:
            if key in sans_paquet:
                sub = ("Pas de paquet sur cette distribution — "
                       "le bundle officiel l'inclut déjà" if key in ("ctl", "ocio")
                       else "Pas de paquet sur cette distribution")
            sw = Adw.SwitchRow(title=title, subtitle=sub,
                               active=o.features[key] and key not in sans_paquet)
            self.sw_feat[key] = sw
            g3.add(sw)
        body.append(g3)

        g4 = Adw.PreferencesGroup(title="Optimisation")
        self.sw_native = Adw.SwitchRow(title="Optimiser pour ce processeur",
                                       subtitle="Plus rapide, mais ce binaire ne fonctionnera que sur cette machine",
                                       active=True)
        self.sw_lto = Adw.SwitchRow(title="Optimisation à l'édition de liens (LTO)",
                                    subtitle="Légèrement plus rapide, compilation plus longue", active=False)
        ncpu = os.cpu_count() or 2
        self.sp_jobs = Adw.SpinRow.new_with_range(1, ncpu, 1)
        self.sp_jobs.set_title("Tâches de compilation en parallèle")
        self.sp_jobs.set_subtitle(f"{ncpu} cœurs détectés")
        self.sp_jobs.set_value(ncpu)
        for r in (self.sw_native, self.sw_lto, self.sp_jobs):
            g4.add(r)
        body.append(g4)

        g5 = Adw.PreferencesGroup()
        exp = Adw.ExpanderRow(title="Voir les commandes", subtitle="Pour les curieux et les forums")
        self.cmd_label = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                   margin_top=10, margin_bottom=10, margin_start=12, margin_end=12)
        self.cmd_label.add_css_class("monospace")
        self.cmd_label.add_css_class("caption")
        exp.add_row(self.cmd_label)
        g5.add(exp)
        body.append(g5)

        widgets = [self.c_ref, self.c_prefix, self.sw_deps, self.sw_native, self.sw_lto,
                   *self.sw_feat.values()]
        for w in widgets:
            w.connect("notify::active" if isinstance(w, Adw.SwitchRow) else "notify::selected",
                      lambda *_: self.update_cmd_preview())
        self.sp_jobs.connect("notify::value", lambda *_: self.update_cmd_preview())
        self.e_src.connect("changed", lambda *_: self.update_cmd_preview())
        self.update_cmd_preview()

        def start(*_):
            opts = self.compile_options()
            steps, cleanup = core.plan_compile(opts)
            self.after_success = None
            self.start_run("Compilation d'ART", steps, cleanup)

        return self.make_page("Compilation", "compile", body,
                              self.bottom_bar(self.button("Compiler et installer", start)))

    def compile_options(self):
        o = core.CompileOptions()
        o.ref = self.releases.latest if self.c_ref.get_selected() == 0 else "master"
        o.system_wide = self.c_prefix.get_selected() == 1
        o.src_dir = os.path.expanduser(self.e_src.get_text().strip() or str(core.SOURCE_DIR))
        o.install_deps = self.sw_deps.get_active()
        o.features = {k: sw.get_active() for k, sw in self.sw_feat.items()}
        o.native = self.sw_native.get_active()
        o.lto = self.sw_lto.get_active()
        o.jobs = int(self.sp_jobs.get_value())
        return o

    def update_cmd_preview(self):
        o = self.compile_options()
        lines = []
        if o.install_deps and self.pkg_mgr:
            cmd = core.PKG_COMMANDS[self.pkg_mgr]
            if cmd.get("refresh"):
                lines.append("sudo " + " ".join(cmd["refresh"]))
            lines.append("sudo " + " ".join(cmd["install"] + cmd.get("skip", []))
                         + " " + " ".join(core.packages(o, self.pkg_mgr)))
        lines.append(f"git clone {core.GIT_URL} {tilde(o.src_dir)}")
        lines.append(f"git -C {tilde(o.src_dir)} checkout {o.ref}")
        lines.append(shlex.join(core.cmake_command(o)).replace(str(Path.home()), "~"))
        lines.append(f"cmake --build {tilde(o.build_dir)} --parallel {o.jobs}")
        lines.append(("sudo " if o.system_wide else "") + f"cmake --install {tilde(o.build_dir)}")
        self.cmd_label.set_label("\n\n".join(lines))

    # ------------------------------------------------------------------ exécution
    def start_run(self, title, steps, cleanup):
        self.steps = steps
        self.cleanup = cleanup
        self.cur = 0
        self.step_frac = None
        self.log_lines = []
        self.log_lock = threading.Lock()
        self.log_all = []
        self.started = time.monotonic()

        body = self.vbox(18)
        head = Gtk.Box(spacing=16)
        head.append(logo_image(64))
        tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, spacing=2)
        self.lbl_step = Gtk.Label(label=title, xalign=0, wrap=True)
        self.lbl_step.add_css_class("step-title")
        self.lbl_sub = Gtk.Label(label="Préparation…", xalign=0)
        self.lbl_sub.add_css_class("dim-label")
        tb.append(self.lbl_step)
        tb.append(self.lbl_sub)
        head.append(tb)
        body.append(head)

        self.pbar = Gtk.ProgressBar(show_text=True)
        body.append(self.pbar)

        g = Adw.PreferencesGroup()
        self.step_rows = []
        for s in steps:
            r = Adw.ActionRow(title=s.title)
            stack = Gtk.Stack()
            stack.add_named(Gtk.Image(icon_name="content-loading-symbolic", opacity=0.35), "wait")
            stack.add_named(Gtk.Spinner(spinning=True), "run")
            ok = Gtk.Image(icon_name="object-select-symbolic")
            ok.add_css_class("success")
            stack.add_named(ok, "ok")
            ko = Gtk.Image(icon_name="dialog-error-symbolic")
            ko.add_css_class("error")
            stack.add_named(ko, "fail")
            r.add_prefix(stack)
            g.add(r)
            self.step_rows.append((r, stack))
        body.append(g)

        exp = Gtk.Expander(label="Afficher les détails")
        self.log_buf = Gtk.TextBuffer()
        tv = Gtk.TextView(buffer=self.log_buf, editable=False, cursor_visible=False,
                          monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        tv.add_css_class("log-view")
        self.log_view = tv
        sc = Gtk.ScrolledWindow(min_content_height=260, vexpand=True)
        sc.set_child(tv)
        fr = Gtk.Frame(child=sc, margin_top=8)
        fr.add_css_class("log-frame")
        exp.set_child(fr)
        body.append(exp)

        self.btn_cancel = self.button("Annuler", self.on_cancel, "destructive-action")
        page = self.make_page("Installation", "run", body, self.bottom_bar(self.btn_cancel), can_pop=False)
        self.nav.push(page)

        self.runner = core.Runner(self._on_log, self._on_progress)
        self.running = True
        self.flush_id = GLib.timeout_add(120, self.flush)
        threading.Thread(target=self.worker, daemon=True).start()

    # appelés depuis le thread de travail
    def _on_log(self, text):
        with self.log_lock:
            self.log_lines.append(text)

    def _on_progress(self, frac):
        self.step_frac = frac

    def worker(self):
        status, err = "ok", None
        try:
            for i, step in enumerate(self.steps):
                self.cur, self.step_frac = i, None
                GLib.idle_add(self.set_step_state, i, "run")
                self._on_log(f"\n=== {step.title} ===")
                self.runner.step = step.title
                step.fn(self.runner)
                GLib.idle_add(self.set_step_state, i, "ok")
        except core.Cancelled:
            status = "cancel"
        except Exception as e:
            status, err = "fail", str(e)
            self._on_log(f"ERREUR : {e}")
        finally:
            try:
                self.cleanup()
            except Exception:
                pass
        GLib.idle_add(self.finish, status, err)

    def set_step_state(self, i, state):
        r, stack = self.step_rows[i]
        stack.set_visible_child_name(state)
        if state == "run":
            self.lbl_sub.set_label(f"Étape {i + 1} sur {len(self.steps)} : {self.steps[i].title}")
        return False

    def flush(self):
        with self.log_lock:
            lines, self.log_lines = self.log_lines, []
        if lines:
            self.log_all.extend(lines)
            self.log_buf.insert(self.log_buf.get_end_iter(), "\n".join(lines) + "\n")
            # Garder le TextView léger pendant une longue compilation
            if self.log_buf.get_line_count() > 4000:
                start = self.log_buf.get_start_iter()
                cut = self.log_buf.get_iter_at_line(self.log_buf.get_line_count() - 3000)
                cut = cut[1] if isinstance(cut, tuple) else cut
                self.log_buf.delete(start, cut)
            self.log_view.scroll_to_iter(self.log_buf.get_end_iter(), 0, False, 0, 1)
        n = len(self.steps)
        frac = self.step_frac
        if frac is None:
            self.pbar.pulse()
            self.pbar.set_text(f"{self.elapsed()}")
        else:
            self.pbar.set_fraction(min(1.0, (self.cur + frac) / n))
            self.pbar.set_text(f"{int(frac * 100)} %  ·  {self.elapsed()}")
        return self.running

    def elapsed(self):
        s = int(time.monotonic() - self.started)
        return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"

    def save_log(self):
        try:
            core.LOG_DIR.mkdir(parents=True, exist_ok=True)
            p = core.LOG_DIR / "derniere-installation.log"
            p.write_text("\n".join(self.log_all) + "\n")
            return p
        except OSError:
            return None

    def on_cancel(self, *_):
        self.btn_cancel.set_sensitive(False)
        self.lbl_sub.set_label("Annulation en cours…")
        if self.runner:
            self.runner.cancel()

    def finish(self, status, err):
        self.flush()
        self.running = False
        log_path = self.save_log()
        self.nav.push(self.build_end(status, err, log_path))
        if status == "ok" and getattr(self, "after_success", None):
            self.after_success()
        return False

    # ------------------------------------------------------------------ fin
    def build_end(self, status, err, log_path):
        res = self.runner.result
        sp = Adw.StatusPage()
        buttons = []
        if status == "ok":
            sp.set_paintable(Gdk.Texture.new_from_filename(str(LOGO)))
            sp.set_title(f"ART {res.version or ''} est installé !".replace("  ", " "))
            sp.set_description(f"Durée : {self.elapsed()}")
            g = Adw.PreferencesGroup()
            r = Adw.ActionRow(title="Emplacement", subtitle=tilde(res.dest or ""))
            r.add_css_class("property")
            r.set_subtitle_selectable(True)
            g.add(r)
            feats = Adw.ActionRow(title="Fonctionnalités")
            box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
            box.append(feature_pill("CTL", res.ctl))
            box.append(feature_pill("OCIO", res.ocio))
            if res.vulkan:
                box.append(feature_pill("Vulkan", True))
            feats.add_suffix(box)
            g.add(feats)
            for n in res.notes:
                nr = Adw.ActionRow(title="À savoir", subtitle=n)
                nr.add_prefix(Gtk.Image(icon_name="dialog-warning-symbolic"))
                g.add(nr)
            if res.ctl:
                tip = Adw.ActionRow(title="Astuce pour les scripts CTL",
                                    subtitle="Dans ART : Préférences → Traitement de l'image → « Dossier CLUT », "
                                             "indique le dossier de tes scripts .ctl puis redémarre ART.")
                tip.add_prefix(Gtk.Image(icon_name="dialog-information-symbolic"))
                g.add(tip)
            sp.set_child(Adw.Clamp(maximum_size=600, child=g))
            buttons.append(self.button("Lancer ART", lambda *_: self.launch_art(res.exe)))
            buttons.append(self.button("Fermer", lambda *_: self.close(), None))
        else:
            sp.set_icon_name("process-stop-symbolic" if status == "cancel" else "dialog-error-symbolic")
            sp.set_title("Installation annulée" if status == "cancel" else "L'installation a échoué")
            desc = err or "Rien d'irréversible n'a été fait."
            if log_path:
                desc += f"\n\nJournal complet : {tilde(log_path)}"
            sp.set_description(GLib.markup_escape_text(desc))
            buttons.append(self.button("Copier le journal", lambda *_: self.copy_log(), None))
            buttons.append(self.button("Recommencer", lambda *_: self.restart()))

        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar(show_back_button=False))
        sc = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        sc.set_child(sp)
        tv.set_content(sc)
        tv.add_bottom_bar(self.bottom_bar(*buttons))
        page = Adw.NavigationPage(title="Terminé", tag="end", child=tv)
        page.set_can_pop(False)
        return page

    def restart(self):
        self.nav.pop_to_tag("welcome")
        self.refresh()

    def copy_log(self):
        self.get_clipboard().set("\n".join(self.log_all))
        self.toast("Journal copié dans le presse-papiers")

    def launch_art(self, exe):
        try:
            subprocess.Popen([exe], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.toast("ART démarre…")
        except OSError as e:
            self.toast(f"Impossible de lancer ART : {e}")

    def offer_cleanup(self, parent):
        olds = core.old_bundles(parent, self.runner.result.dest)
        if not olds:
            return
        listing = "\n".join("• " + tilde(d) for d in olds)
        dlg = Adw.AlertDialog(
            heading="Supprimer les anciens bundles ?",
            body=f"Ces anciennes versions d'ART ont été trouvées :\n\n{listing}\n\n"
                 "Cette suppression est définitive. Un ART compilé n'est jamais concerné.")
        dlg.add_response("keep", "Conserver")
        dlg.add_response("delete", "Supprimer")
        dlg.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("keep")
        dlg.set_close_response("keep")

        def on_resp(_d, resp):
            if resp == "delete":
                import shutil
                for d in olds:
                    shutil.rmtree(d, ignore_errors=True)
                self.toast(f"{len(olds)} ancien(s) bundle(s) supprimé(s)")
        dlg.connect("response", on_resp)
        dlg.present(self)

    # ------------------------------------------------------------------ divers
    def show_help(self):
        try:
            Gtk.UriLauncher.new(core.HELP_URL).launch(self, None, None, None)
        except Exception:
            Gio.AppInfo.launch_default_for_uri(core.HELP_URL, None)

    def show_about(self):
        kw = dict(application_name=core.APP_NAME, version=core.APP_VERSION,
                  developer_name="Philippe (carafife)",
                  comments="Installe, met à jour ou compile ART, le développeur de photos RAW libre.\n"
                           "Projet communautaire, indépendant de l'équipe d'ART.",
                  website="https://github.com/carafife/art-installer",
                  license_type=Gtk.License.GPL_3_0,
                  application_icon=core.APP_ID)
        if hasattr(Adw, "AboutDialog"):
            Adw.AboutDialog(**kw).present(self)
        else:
            Adw.AboutWindow(transient_for=self, **kw).present()

    def on_close_request(self, *_):
        if self.running and self.runner:
            self.runner.cancel()
        return False


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=core.APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        GLib.set_application_name(core.APP_NAME)

    def do_startup(self):
        Adw.Application.do_startup(self)
        prov = Gtk.CssProvider()
        prov.load_from_string(CSS) if hasattr(prov, "load_from_string") else prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        theme.add_search_path(str(HERE / "data"))
        Gtk.Window.set_default_icon_name(core.APP_ID)

    def do_activate(self):
        win = self.props.active_window or Window(self)
        win.present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
