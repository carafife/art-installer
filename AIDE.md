# Aide de l'Installateur ART

Ce guide décrit le déroulement de l'installation, écran par écran, puis chaque option : ce qu'elle fait, à quoi elle correspond dans ART, et quand l'activer.

**Sommaire**

1. [Avant de commencer](#1-avant-de-commencer)
2. [Écran 1 : l'accueil](#2-écran-1--laccueil)
3. [Écran 2 : bundle ou compilation ?](#3-écran-2--bundle-ou-compilation-)
4. [Les options du bundle officiel](#4-les-options-du-bundle-officiel)
5. [Les options de compilation](#5-les-options-de-compilation)
6. [Écran de progression](#6-écran-de-progression)
7. [Écran de fin](#7-écran-de-fin)
8. [Après l'installation](#8-après-linstallation)
9. [Problèmes fréquents](#9-problèmes-fréquents)
10. [Où sont les fichiers ?](#10-où-sont-les-fichiers-)

---

## 1. Avant de commencer

**Il vous faut :**

- une connexion Internet ;
- environ **300 Mo** d'espace libre pour le bundle, ou **2 Go** pour une compilation ;
- pour la compilation : le mot de passe administrateur si vous laissez l'installateur installer les dépendances.

**Ce que l'installateur ne fait jamais :**

- il ne supprime rien sans vous demander de confirmer ;
- il ne touche ni à vos réglages d'ART (`~/.config/ART`) ni à vos profils de traitement ;
- il ne modifie pas une version d'ART installée par Flatpak ou par le gestionnaire de paquets.

---

## 2. Écran 1 : l'accueil

L'accueil fait l'inventaire de votre ordinateur.

### « ART sur cet ordinateur »

Chaque version d'ART trouvée apparaît sur une ligne avec :

- **la version** (par exemple `1.26.9`, ou `1.26.10-12-g3fa2b1c` pour une version de développement compilée) ;
- **le type d'installation** et son emplacement :

  | Type | Signification |
  |---|---|
  | Bundle officiel | Archive prête à l'emploi téléchargée depuis le site d'ART |
  | Compilé depuis les sources | Version que vous (ou l'installateur) avez compilée |
  | Paquet de la distribution | Installée par `dnf` depuis les dépôts Fedora |
  | Flatpak / AppImage | Versions isolées du reste du système |

- **des badges** :

  | Badge | Signification |
  |---|---|
  | `par défaut` | C'est cette version qui démarre quand vous tapez `ART` dans un terminal |
  | `CTL ✓` / `sans CTL` | Les scripts CTL fonctionnent / ne fonctionnent pas dans cette version |
  | `OCIO ✓` / `sans OCIO` | OpenColorIO est présent / absent |
  | `Vulkan ✓` | L'accélération par la carte graphique est compilée |
  | `CTL ?` | Impossible de vérifier (fichier `AboutThisBuild.txt` absent) |

Le bouton ⟳ relance l'analyse, par exemple après avoir installé ART d'une autre façon.

### « Versions disponibles »

L'installateur interroge le dépôt officiel d'ART sur GitHub et affiche deux informations :

- **Dernière version** : la plus récente publiée, disponible au moins en code source ;
- **Dernier bundle Linux prêt à l'emploi** : la plus récente qui existe sous forme d'archive Linux.

Ces deux numéros peuvent être différents : l'auteur d'ART publie parfois une version pour Windows et en sources avant le bundle Linux. Dans ce cas, seule la compilation donne accès à la toute dernière version.

---

## 3. Écran 2 : bundle ou compilation ?

### Bundle officiel (recommandé)

Le bundle est une archive préparée par l'auteur d'ART, qui contient le programme et toutes ses bibliothèques.

- ✅ Rapide : quelques minutes.
- ✅ Aucun outil de développement à installer, aucun mot de passe.
- ✅ **CTL et OpenColorIO déjà inclus.**
- ❌ Pas toujours la toute dernière version.
- ❌ Options figées : pas d'accélération Vulkan, pas d'optimisation pour votre processeur.

**Choisissez-le si** vous voulez simplement utiliser ART.

### Compiler depuis les sources

L'installateur télécharge le code source d'ART et le transforme en programme sur votre machine.

- ✅ La toute dernière version, ou même la version de développement.
- ✅ Vous choisissez les fonctionnalités.
- ✅ Peut être optimisé pour votre processeur.
- ❌ Plus long : 20 à 40 minutes selon l'ordinateur.
- ❌ Demande environ 2 Go et l'installation d'outils de développement.

**Choisissez-la si** vous voulez une version que le bundle ne propose pas encore, ou une fonctionnalité comme Vulkan.

> 💡 Si la dernière version n'a pas encore de bundle Linux, un encadré vous le signale sous les deux choix.

---

## 4. Les options du bundle officiel

### Dossier d'installation

*Par défaut : `~/programs`*

Le bundle est extrait dans un sous-dossier qui porte son nom, par exemple `~/programs/ART-1.26.9-linux64`. Chaque version a son propre dossier : installer une nouvelle version n'écrase pas l'ancienne.

**Pourquoi le changer ?** Si vous rangez vos logiciels ailleurs, par exemple dans `~/Programmes`.

### Commandes « ART » et « ART-cli » dans le terminal

*Par défaut : activé*

Crée deux raccourcis dans `~/.local/bin` :

- `ART` lance l'éditeur ;
- `ART-cli` est la version en ligne de commande, qui sert à traiter des photos par lot sans ouvrir l'interface.

**Pourquoi le garder activé ?** Beaucoup de scripts et d'outils externes (greffons GIMP, scripts de traitement) appellent ART par ces commandes. Après une mise à jour, les raccourcis pointent automatiquement vers la nouvelle version.

> Si `~/.local/bin/ART` est déjà un ART **compilé**, l'installateur ne le remplace pas et vous prévient.

### Icône dans le menu des applications

*Par défaut : activé*

Ajoute ART au menu des applications de votre bureau, avec son icône, et l'associe aux fichiers RAW, TIFF, JPEG et PNG (clic droit → « Ouvrir avec »).

### Proposer de supprimer les anciens bundles

*Par défaut : désactivé*

Une fois l'installation réussie, l'installateur liste les anciens bundles présents dans le dossier d'installation et vous demande si vous voulez les supprimer.

- Rien n'est supprimé sans votre confirmation.
- Seuls les dossiers `ART-<version>-linux64` sont concernés : un ART compilé n'est **jamais** touché.
- Vos réglages et vos profils de traitement ne sont pas dans ces dossiers : ils sont conservés.

**Pourquoi l'activer ?** Chaque bundle occupe environ 300 Mo. Gardez au moins une ancienne version tant que vous n'avez pas vérifié que la nouvelle vous convient.

---

## 5. Les options de compilation

### Version à compiler

| Choix | Description |
|---|---|
| **Stable — 1.26.x** | La dernière version publiée officiellement. **Recommandé.** |
| **Développement — master** | Le code le plus récent, avec les nouveautés en cours. Peut contenir des bugs. |

Choisissez « Développement » seulement pour tester une nouveauté annoncée sur le forum, ou pour aider l'auteur à trouver des bugs.

### Installer pour

| Choix | Emplacement | Mot de passe |
|---|---|---|
| **Moi seulement** | `~/.local` | Non |
| **Tous les utilisateurs** | `/usr/local` | Oui |

« Moi seulement » suffit sur un ordinateur personnel. Choisissez « Tous les utilisateurs » si plusieurs comptes doivent utiliser ART.

> Si un bundle était lié dans `~/.local/bin`, ces liens sont retirés pour que la commande `ART` lance bien la version compilée. Le dossier du bundle, lui, reste en place.

### Dossier des sources

*Par défaut : `~/programs/ART-source`*

Le code source d'ART y est téléchargé et compilé. **Conservez ce dossier** : à la prochaine mise à jour, seules les modifications sont téléchargées et la compilation est beaucoup plus rapide.

### Installer les dépendances automatiquement

*Par défaut : activé (si `dnf` est présent)*

Pour compiler ART, il faut un compilateur et des bibliothèques de développement (paquets `-devel`). L'installateur les installe avec `dnf` ; une fenêtre système vous demande votre mot de passe.

La liste dépend des fonctionnalités cochées : décocher Vulkan, par exemple, évite d'installer les outils Vulkan.

**Pourquoi le désactiver ?** Si vous êtes sur une autre distribution que Fedora, ou si les dépendances sont déjà installées. Le bouton « Voir les commandes » affiche la liste des paquets nécessaires.

### Fonctionnalités

Chaque interrupteur correspond à une option de compilation d'ART.

#### Scripts CTL

*Option CMake : `ENABLE_CTL` — par défaut : activé*

Le CTL (*Color Transformation Language*) est un langage de script pour les couleurs, issu du monde du cinéma (ACES). Dans ART, il permet d'utiliser des **scripts de transformation des couleurs** : simulations de films argentiques, looks, conversions d'espaces colorimétriques. Ces scripts se choisissent dans l'outil « LUT » de l'onglet Couleur.

**Activez-le** si vous utilisez ou voulez essayer des simulations de film. C'est la principale raison de compiler soi-même : sans cette option, ART fonctionne mais ignore les fichiers `.ctl`.

Paquets installés : `ctl-devel`, `openexr-devel`.

#### OpenColorIO

*Option CMake : `ENABLE_OCIO` — par défaut : activé*

OpenColorIO est la bibliothèque de gestion des couleurs utilisée dans le cinéma et les effets spéciaux. ART s'en sert pour appliquer des **LUT** (`.cube`, `.clf`…) et des transformations de couleur avancées.

**Gardez-le activé** sauf problème de compilation lié à cette bibliothèque.

Paquet installé : `OpenColorIO-devel`.

#### LibRaw

*Option CMake : `ENABLE_LIBRAW` — par défaut : activé*

ART décode les fichiers RAW avec son propre moteur. LibRaw est un décodeur supplémentaire, qui sert de secours pour certains boîtiers, en particulier **les appareils récents** et certains formats compressés (Canon CR3, par exemple).

**Gardez-le activé.**

Paquet installé : `LibRaw-devel`.

#### mimalloc

*Option CMake : `ENABLE_MIMALLOC` — par défaut : activé*

mimalloc est une bibliothèque de gestion de la mémoire, plus rapide que celle du système. ART manipule de grosses images : le gain est sensible, surtout sur les traitements par lot.

**Gardez-le activé.**

Paquet installé : `mimalloc-devel`.

#### Accélération GPU Vulkan (expérimental)

*Option CMake : `ENABLE_VULKAN` — par défaut : désactivé*

Fait exécuter certains calculs d'ART par la **carte graphique** plutôt que par le processeur, grâce à Vulkan. Fonctionne avec les cartes AMD, Intel et NVIDIA, à condition que le pilote Vulkan soit installé (c'est le cas par défaut sous Fedora pour AMD et Intel).

**Activez-le** si vous voulez tester des traitements plus rapides et que vous acceptez quelques imperfections : la fonction est récente. En cas de souci, recompilez sans cette option.

Paquets installés : `vulkan-headers`, `vulkan-loader-devel`, `glslc`.

### Optimisation

#### Optimiser pour ce processeur

*Option CMake : `PROC_TARGET_NUMBER=2` (« native ») — par défaut : activé*

Le compilateur utilise toutes les instructions de **votre** processeur (AVX2, etc.). ART est un peu plus rapide.

**Désactivez-le** si vous voulez copier le programme compilé sur un autre ordinateur : un binaire optimisé pour un processeur peut planter sur un autre.

#### Optimisation à l'édition de liens (LTO)

*Option CMake : `WITH_LTO` — par défaut : désactivé*

Le compilateur optimise le programme dans son ensemble plutôt que fichier par fichier. Le gain est faible, mais la compilation est nettement plus longue et demande plus de mémoire.

**Activez-le** seulement si vous avez beaucoup de mémoire vive (16 Go ou plus) et du temps.

#### Tâches de compilation en parallèle

*Par défaut : nombre de cœurs du processeur*

Le nombre de fichiers compilés en même temps. Plus il est élevé, plus la compilation est rapide, mais chaque tâche peut demander jusqu'à 1 Go de mémoire.

**Baissez-le** si l'ordinateur devient inutilisable pendant la compilation ou si elle échoue par manque de mémoire (message *« Killed »* ou *« out of memory »* dans les détails). Règle simple : pas plus d'une tâche par Go de mémoire vive libre.

### Voir les commandes

Affiche exactement ce que l'installateur va exécuter : `dnf`, `git`, `cmake`. Utile pour comprendre, pour reproduire à la main, ou pour demander de l'aide sur le forum.

---

## 6. Écran de progression

L'écran montre :

- l'étape en cours et la durée écoulée ;
- une barre de progression : elle avance en pourcentage pendant le téléchargement et la compilation, et oscille pendant les étapes dont la durée est inconnue ;
- la liste des étapes avec leur état (en attente, en cours, ✓ terminée, ✗ en échec) ;
- **Afficher les détails** : le journal complet, ligne par ligne.

**Étapes du bundle :** télécharger → extraire → intégrer au bureau → vérifier.

**Étapes de la compilation :** installer les dépendances → récupérer les sources → configurer (CMake) → compiler → installer → vérifier.

Le bouton **Annuler** interrompt proprement l'étape en cours. Une compilation annulée peut être reprise plus tard : le travail déjà fait est conservé dans le dossier des sources.

---

## 7. Écran de fin

### En cas de réussite

- La **version installée** et son emplacement.
- Les **fonctionnalités réellement présentes**, lues dans le fichier `AboutThisBuild.txt` d'ART. C'est la meilleure vérification : si vous avez demandé le CTL et que le badge indique « sans CTL », une dépendance manquait.
- D'éventuels **avertissements « À savoir »** (par exemple : la commande `ART` lance encore une autre version).
- Le bouton **Lancer ART**.

### En cas d'échec

- Le message d'erreur.
- **Copier le journal** : copie tout le journal dans le presse-papiers, prêt à coller dans un message sur le forum.
- **Recommencer** : retour à l'accueil.

Le journal de la dernière installation est aussi enregistré dans :

```
~/.cache/art-installer/derniere-installation.log
```

---

## 8. Après l'installation

### Utiliser vos scripts CTL

1. Placez vos scripts `.ctl` dans un dossier, par exemple `~/.config/ART/ctlscripts`.
2. Dans ART, ouvrez **Préférences → Traitement de l'image**.
3. Dans **Dossier CLUT**, indiquez ce dossier.
4. **Redémarrez ART.**

Les scripts se choisissent alors dans l'outil « LUT » de l'onglet Couleur.

### Mettre à jour ART

Relancez simplement l'Installateur ART : il détecte votre version actuelle et vous propose la nouvelle.

- Bundle : la nouvelle version est installée à côté de l'ancienne, et les raccourcis basculent vers elle.
- Compilation : seules les modifications du code sont téléchargées, et la compilation est plus rapide que la première fois.

---

## 9. Problèmes fréquents

**« Impossible de joindre GitHub »**
Vérifiez la connexion Internet, puis cliquez sur ⟳. GitHub limite aussi le nombre de requêtes anonymes à 60 par heure : en cas d'usage intensif, patientez un peu.

**La fenêtre de mot de passe ne s'affiche pas**
L'installateur utilise `pkexec`. Sous GNOME et KDE, c'est automatique. Sur un bureau minimaliste, installez et lancez un agent polkit, ou décochez « Installer les dépendances » et lancez vous-même la commande `dnf` affichée dans « Voir les commandes ».

**La compilation échoue à l'étape « Configurer »**
Une bibliothèque manque. Ouvrez les détails : la ligne contenant `Could not find` ou `not found` indique laquelle. Installez le paquet `-devel` correspondant, ou décochez la fonctionnalité concernée.

**La compilation s'arrête avec « Killed »**
La mémoire est saturée. Réduisez le nombre de tâches en parallèle et désactivez le LTO.

**« Le CTL a été demandé mais n'est pas actif »**
Vérifiez que `ctl-devel` et `openexr-devel` sont installés :

```bash
dnf list --installed ctl-devel openexr-devel
```

puis relancez la compilation.

**La commande `ART` lance une autre version**
Plusieurs ART sont installés. Le premier trouvé dans le `PATH` gagne : `~/.local/bin` passe avant `/usr/local/bin`, qui passe avant `/usr/bin`. L'accueil de l'installateur indique laquelle est `par défaut`.

**Une version Flatpak est détectée**
Elle fonctionne, mais isolée du système : les scripts CTL et les outils externes y fonctionnent mal. Vous pouvez la garder à côté ou la retirer avec `flatpak uninstall`.

---

## 10. Où sont les fichiers ?

| Élément | Emplacement |
|---|---|
| Bundles d'ART | `~/programs/ART-<version>-linux64/` |
| Sources pour la compilation | `~/programs/ART-source/` |
| ART compilé (moi seulement) | `~/.local/bin/ART`, `~/.local/share/ART/` |
| ART compilé (tous les utilisateurs) | `/usr/local/bin/ART`, `/usr/local/share/ART/` |
| Raccourcis du bundle | `~/.local/bin/ART`, `~/.local/bin/ART-cli` |
| Icône dans le menu | `~/.local/share/applications/ART.desktop` |
| Réglages d'ART (jamais modifiés) | `~/.config/ART/` |
| Journal de l'installateur | `~/.cache/art-installer/derniere-installation.log` |
