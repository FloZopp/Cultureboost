from pythonforandroid.recipes.libffi import LibffiRecipe as _ParentLibffi


class LibffiRecipe(_ParentLibffi):
    """
    Reprend la recette libffi officielle de python-for-android, mais epingle
    la version 3.4.6 (compatible avec autoconf/libtool recents). Toutes les
    autres methodes (get_include_dirs, etc.) sont heritees telles quelles.
    """
    version = "3.4.6"
    url = "https://github.com/libffi/libffi/releases/download/v{version}/libffi-{version}.tar.gz"


recipe = LibffiRecipe()
