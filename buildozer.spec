[app]

# Nom affiche sous l'icone
title = CultureBoost

# Identifiants du paquet (doivent rester sans espace ni tiret)
package.name = cultureboost
package.domain = org.cultureboost

# Dossier contenant le code source
source.dir = .

# Types de fichiers a inclure dans l'APK
source.include_exts = py,png,jpg,kv,atlas,json

# Version de l'application
version = 2.0

# Dependances Python embarquees dans l'APK
# - python3, kivy : le moteur de l'app
# - certifi, openssl : indispensables pour les appels HTTPS aux API
# - requests/urllib3 : confort reseau
requirements = python3,kivy==2.3.1,certifi,openssl
p4a.local_recipes = ./p4a-recipes

# Orientation de l'ecran
orientation = portrait

# Affichage plein ecran (0 = barre de statut visible)
fullscreen = 0

# --- Specifique Android ---------------------------------------------------

# Permission necessaire : acces internet pour telecharger les questions
android.permissions = INTERNET, ACCESS_NETWORK_STATE

# Niveaux d'API Android (cible recente, minimum large pour la compatibilite)
android.api = 34
android.minapi = 24

# Architectures processeur generees (couvre la quasi-totalite des telephones)
android.archs = arm64-v8a, armeabi-v7a

# Accepte automatiquement les licences du SDK Android lors du build
android.accept_sdk_license = True

# Couleur de l'ecran de demarrage (fond sombre, comme l'app)
android.presplash_color = #15171C

[buildozer]

# Niveau de detail des journaux (2 = complet, utile en cas d'erreur)
log_level = 2

# Avertit si buildozer est lance en root (sans bloquer)
warn_on_root = 1
