# CultureBoost

Application mobile (Android) pour booster sa culture generale.
Ecrite en Python avec Kivy.

---

## Ce que fait l'application

- **Quiz rapide** (10 questions) et **Marathon** (25 questions)
- **Revision ciblee** : un systeme de *repetition espacee* fait revenir les
  questions ratees au bon moment, pour ancrer durablement les connaissances
- **Questions en francais** fournies par QuizzAPI, interrogee plusieurs fois
  par session pour varier les themes et elargir le choix
- **Decouverte** : faits et resumes d'articles tires de Wikipedia (en francais)
  et d'autres sources
- **Statistiques** : XP, niveaux, serie de jours, precision par categorie
- **Mode hors-ligne** : si aucune connexion, l'app utilise une banque de
  questions integree (rien ne plante jamais)
- Toutes les donnees restent **sur le telephone** : aucune inscription, aucun compte

---

## Comment obtenir l'APK (sans rien installer sur ton ordinateur)

La compilation d'un APK Android est lourde. La methode la plus simple est de
laisser **GitHub** la faire gratuitement dans le cloud. Voici les etapes :

### 1. Creer un compte GitHub
Va sur https://github.com et cree un compte (gratuit) si tu n'en as pas.

### 2. Creer un nouveau depot ("repository")
- Clique sur le bouton **New** (nouveau depot).
- Donne-lui un nom, par exemple `cultureboost`.
- Laisse-le en **Public** ou **Private**, peu importe.
- Clique sur **Create repository**.

### 3. Envoyer les fichiers du projet
Sur la page du depot vide, clique sur **uploading an existing file**, puis
glisse-depose **tous les fichiers et dossiers** de ce projet :

```
main.py
core.py
buildozer.spec
requirements-desktop.txt
README.md
.github/workflows/build.yml      <-- important : garder ce dossier
```

> Astuce : si l'interface web ne te laisse pas glisser le dossier `.github`,
> cree d'abord un fichier nomme `.github/workflows/build.yml` directement
> sur GitHub (bouton "Add file" > "Create new file", et tape ce chemin
> complet comme nom de fichier), puis colle son contenu.

Clique sur **Commit changes** pour valider l'envoi.

### 4. Laisser GitHub compiler l'APK
- Va dans l'onglet **Actions** du depot.
- Une tache nommee *"Compiler l'APK CultureBoost"* demarre toute seule.
- La premiere compilation prend **20 a 30 minutes** (les suivantes sont plus
  rapides grace au cache). Tu peux fermer la page, ca continue tout seul.

### 5. Telecharger l'APK
- Quand la tache affiche une coche verte, clique dessus.
- En bas de la page, section **Artifacts**, telecharge **CultureBoost-APK**.
- C'est un fichier `.zip` : decompresse-le pour obtenir le fichier `.apk`.

### 6. Installer sur le telephone
- Transfere le `.apk` sur ton telephone (cable, e-mail, cloud...).
- Ouvre-le depuis le telephone.
- Android demandera d'autoriser l'installation d'applications depuis cette
  source : accepte (Parametres > Securite > "Sources inconnues" ou la
  demande s'affichera directement).
- L'application s'installe. C'est termine.

---

## Tester sur ordinateur (facultatif)

Pas besoin d'attendre l'APK pour essayer l'application :

```bash
pip install -r requirements-desktop.txt
python main.py
```

Une fenetre au format telephone s'ouvre.

---

## Structure du projet

| Fichier | Role |
|---|---|
| `main.py` | Interface graphique (Kivy) et point d'entree de l'app |
| `core.py` | Logique : base de donnees, repetition espacee, sources d'API, statistiques |
| `buildozer.spec` | Configuration de compilation de l'APK |
| `.github/workflows/build.yml` | Recette de compilation automatique sur GitHub |
| `requirements-desktop.txt` | Dependances pour tester sur ordinateur |

---

## Notes

- L'APK produit est en mode *debug* : parfaitement utilisable pour un usage
  personnel. Pour une publication sur le Play Store, il faudrait un APK signe
  en mode *release* (etape supplementaire non couverte ici).
- Pour modifier l'app, edite `main.py` ou `core.py`, renvoie les fichiers sur
  GitHub : un nouvel APK se compile automatiquement.
- Les questions sont en francais. Pour ajouter une source, ecris dans
  `core.py` une fonction `fetch_xxx()` renvoyant des questions francaises
  (sur le modele de `fetch_quizzapi`), puis appelle-la dans `get_questions()`.
