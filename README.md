<div align="center">

<img src="data/io.github.carafife.ArtInstaller.png" width="128" alt="Logo de l'Installateur ART">

# Installateur ART

**Installer, mettre à jour ou compiler [ART](https://github.com/artraweditor/ART), le développeur de photos RAW libre, en quelques clics.**

[![Licence GPL-3.0](https://img.shields.io/badge/licence-GPL--3.0-blue)](LICENSE)
![Linux](https://img.shields.io/badge/plateforme-Linux-informational)
![GTK 4 + libadwaita](https://img.shields.io/badge/GTK_4-libadwaita-4a86cf)
![Python 3](https://img.shields.io/badge/Python-3-yellow)
![Interface en français](https://img.shields.io/badge/interface-français-lightgrey)

<img src="docs/captures/1-accueil.png" width="640" alt="Écran d'accueil de l'Installateur ART">

</div>

---

## Pourquoi cet installateur ?

ART n'est pas toujours simple à installer sous Linux : le bundle officiel ne sort pas toujours en même temps que la dernière version, et pour compiler avec le support des scripts CTL, il faut connaître les bonnes dépendances et les bonnes options.

L'Installateur ART s'en charge pour vous, avec une interface claire, et vérifie à la fin que tout fonctionne.

## Fonctionnalités

| | |
|---|---|
| 🔍 **Détection** | Trouve toutes les versions d'ART déjà installées (bundle, compilée, paquet, Flatpak, AppImage) et indique pour chacune si le CTL, l'OCIO et Vulkan sont actifs. |
| 🌐 **Versions à jour** | Interroge le dépôt officiel d'ART et signale quand la dernière version n'a pas encore de bundle Linux. |
| 📦 **Bundle officiel** | Télécharge et installe le bundle prêt à l'emploi (CTL et OCIO inclus), crée les commandes `ART` / `ART-cli` et l'icône dans le menu. |
| 🛠️ **Compilation** | Compile ART depuis les sources, version stable ou de développement, avec les options de votre choix. |
| ⚙️ **Options** | Scripts CTL, OpenColorIO, LibRaw, mimalloc, accélération GPU Vulkan (expérimental), optimisation pour votre processeur, LTO. |
| 📥 **Dépendances** | Repère votre distribution et installe les paquets nécessaires avec `dnf`, `apt`, `pacman`, `zypper` ou `eopkg`. |
| ✅ **Vérification** | Lit le fichier `AboutThisBuild.txt` d'ART pour confirmer que les fonctionnalités demandées sont bien présentes. |
| 🧹 **Nettoyage** | Propose de supprimer les anciens bundles, toujours après confirmation. Une version compilée n'est jamais touchée. |
| 📝 **Journal** | Détails de chaque étape à l'écran, et journal complet copiable pour demander de l'aide sur le forum. |

## Captures d'écran

| Choix de la méthode | Options de compilation |
|:---:|:---:|
| <img src="docs/captures/2-methode.png" width="380"> | <img src="docs/captures/3-compil.png" width="380"> |
| **Installation en cours** | **Terminé** |
| <img src="docs/captures/5-progress.png" width="380"> | <img src="docs/captures/6-fin.png" width="380"> |

## Installation

### Prérequis

Python 3, GTK 4 et libadwaita. Ils sont déjà présents sur Fedora Workstation et sur la plupart des bureaux GNOME récents. Sinon, selon votre distribution :

| Distribution | Commande |
|---|---|
| Fedora, RHEL, Nobara | `sudo dnf install git python3-gobject gtk4 libadwaita` |
| Debian, Ubuntu, Mint | `sudo apt install git python3-gi gir1.2-gtk-4.0 gir1.2-adw-1` |
| Arch, Manjaro | `sudo pacman -S --needed git python-gobject gtk4 libadwaita` |
| openSUSE | `sudo zypper install git python3-gobject-Gdk gtk4 libadwaita-1-0` |
| Solus | `sudo eopkg install git python3-gobject gtk4 libadwaita` |

`install.sh` vérifie ces paquets et affiche la bonne commande si l'un manque.

### 1. Télécharger l'installateur

```bash
git clone https://github.com/carafife/art-installer.git ~/art-installer
```

### 2. L'ajouter au menu des applications

```bash
~/art-installer/install.sh
```

### 3. Le lancer

Ouvrez **Installateur ART** depuis le menu des applications, ou tapez :

```bash
art-installer
```

<details>
<summary><b>Autres opérations</b> (mise à jour, essai, désinstallation, sans git)</summary>

**Mettre à jour l'installateur**

```bash
git -C ~/art-installer pull && ~/art-installer/install.sh
```

**L'essayer sans l'installer**

```bash
~/art-installer/art-installer.py
```

**Le désinstaller** (ART lui-même n'est pas touché)

```bash
~/art-installer/install.sh --remove
```

**Sans git** : bouton **Code → Download ZIP** en haut de cette page, décompressez l'archive, puis lancez `install.sh` depuis le dossier obtenu.

</details>

## Utilisation

1. **Accueil** : l'installateur affiche les versions d'ART présentes sur votre ordinateur et celles disponibles en ligne.
2. **Méthode** : choisissez le **bundle officiel** (recommandé, quelques minutes) ou la **compilation** (dernière version et options au choix, 20 à 40 minutes).
3. **Options** : réglez l'emplacement et les fonctionnalités. Le bouton « Voir les commandes » montre tout ce qui sera exécuté.
4. **Installation** : suivez la progression, avec le journal détaillé si besoin.
5. **Terminé** : vérifiez les fonctionnalités actives, puis lancez ART.

📖 **Le guide complet est dans [AIDE.md](AIDE.md)** : chaque écran, chaque option, à quoi elle sert et quand l'activer, ainsi que les problèmes fréquents. Il s'ouvre aussi depuis le menu ☰ → **Aide** de l'application.

## Bundle ou compilation ?

| | Bundle officiel | Compilation |
|---|:---:|:---:|
| Durée | Quelques minutes | 20 à 40 minutes |
| Espace disque | ~300 Mo | ~2 Go |
| Mot de passe administrateur | Non | Pour les dépendances |
| CTL et OpenColorIO | ✅ Inclus | ✅ Au choix |
| Toute dernière version | Pas toujours | ✅ |
| Accélération Vulkan | ❌ | ✅ Expérimental |
| Optimisé pour votre processeur | ❌ | ✅ |

**En résumé :** prenez le bundle pour simplement utiliser ART, compilez pour avoir la toute dernière version ou une option particulière.

## Après l'installation : les scripts CTL

Pour utiliser des simulations de film et autres scripts `.ctl` :

1. Dans ART, ouvrez **Préférences → Traitement de l'image**.
2. Dans **Dossier CLUT**, indiquez le dossier de vos scripts.
3. **Redémarrez ART.**

## Compatibilité

L'installateur repère votre distribution avec `/etc/os-release` et choisit le gestionnaire de paquets correspondant — y compris sur les dérivées (Mint et Pop!_OS passent par `apt`, Manjaro par `pacman`, Nobara par `dnf`).

| | Installation du bundle | Compilation | Scripts CTL en compilation |
|---|:---:|:---:|:---:|
| Fedora, RHEL, Nobara | ✅ | ✅ `dnf` | ✅ |
| openSUSE Tumbleweed | ✅ | ✅ `zypper` | ✅ |
| Debian, Ubuntu, Mint | ✅ | ✅ `apt` | ❌ non packagé |
| Arch, Manjaro | ✅ | ✅ `pacman` | ❌ dans AUR seulement |
| Solus | ✅ | ✅ `eopkg` | ❌ non packagé |
| Autre | ✅ | Dépendances à installer à la main | — |

**L'installation du bundle fonctionne partout** où GTK 4 et libadwaita sont disponibles : elle ne touche à aucun gestionnaire de paquets et place tout dans `~/.local`. Le bundle officiel **contient déjà le CTL et OpenColorIO** — c'est donc la bonne méthode si vous voulez les scripts CTL sur une distribution qui ne les package pas.

Pour la compilation, les paquets propres à une option absente de vos dépôts sont simplement écartés : l'installateur le signale dans le journal et l'option apparaît comme indisponible, au lieu de faire échouer l'installation.

- **Testé sur :** Fedora (GNOME). Les listes de paquets des autres distributions sont vérifiées avant usage, mais pas encore éprouvées sur machine — [vos retours](https://github.com/carafife/art-installer/issues) sont bienvenus.
- **Architectures :** x86_64 et aarch64.

## Signaler un problème

Ouvrez une [issue](https://github.com/carafife/art-installer/issues) en joignant le journal de l'installation. Il se copie avec le bouton **Copier le journal** de l'écran de fin, ou se trouve dans :

```
~/.cache/art-installer/derniere-installation.log
```

## À propos

L'Installateur ART est un **projet communautaire indépendant**, issu de la communauté francophone d'ART. Il n'est pas développé par l'équipe d'ART.

ART est développé par Alberto Griggio et ses contributeurs : [github.com/artraweditor/ART](https://github.com/artraweditor/ART).

## Licence

[GPL-3.0-or-later](LICENSE) © Philippe (carafife)
