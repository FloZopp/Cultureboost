from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
from os.path import exists, join
import sh


class LibffiRecipe(Recipe):
    """
    Recette libffi epinglee sur la version 3.4.6, compatible avec les
    outils autoconf/libtool recents (corrige l'erreur LT_SYS_SYMBOL_USCORE).
    """
    version = "3.4.6"
    url = "https://github.com/libffi/libffi/releases/download/v{version}/libffi-{version}.tar.gz"
    built_libraries = {"libffi.so": ".libs"}

    def should_build(self, arch):
        return not exists(join(self.get_build_dir(arch.arch), ".libs",
                               "libffi.so"))

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            if not exists("configure"):
                shprint(sh.Command("./autogen.sh"), _env=env)
            shprint(
                sh.Command("./configure"),
                "--host=" + arch.command_prefix,
                "--prefix=" + self.get_build_dir(arch.arch),
                "--disable-builddir",
                "--enable-shared",
                _env=env,
            )
            shprint(sh.make, "-j5", "libffi.la", _env=env)


recipe = LibffiRecipe()
