from pythonforandroid.recipes.libffi import LibffiRecipe as _ParentLibffi


class LibffiRecipe(_ParentLibffi):
    version = "3.4.6"
    url = "https://github.com/libffi/libffi/releases/download/v{version}/libffi-{version}.tar.gz"


recipe = LibffiRecipe()
