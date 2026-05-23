from pythonforandroid.recipes.libffi import LibffiRecipe as _ParentLibffi


class LibffiRecipe(_ParentLibffi):
    """
    Recette libffi officielle de p4a, epinglee en version 3.4.6 et sans
    les patches de l'ancienne version (incompatibles avec la 3.4.6).
    """
    version = "3.4.6"
    url = "https://github.com/libffi/libffi/releases/download/v{version}/libffi-{version}.tar.gz"
    patches = []


recipe = LibffiRecipe()
