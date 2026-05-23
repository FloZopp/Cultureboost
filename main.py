# -*- coding: utf-8 -*-
"""
main.py - Interface graphique de CultureBoost
=============================================
Application mobile (Kivy) pour s'entrainer en culture generale.
Point d'entree de l'APK Android.

Pour tester sur ordinateur :  pip install kivy certifi  puis  python main.py
"""

import os
import threading

# Doit etre defini avant l'import de Kivy
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex, platform
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle

import core

# --------------------------------------------------------------------------
# Palette de couleurs
# --------------------------------------------------------------------------

BG      = "#15171C"   # fond
CARD    = "#1E2129"   # carte
CARD2   = "#2A2E38"   # carte secondaire / piste
ACCENT  = "#4F8CFF"   # bleu accent
TEAL    = "#2BB5A0"   # vert-bleu
GREEN   = "#3FB66B"   # bonne reponse
RED     = "#E5544B"   # mauvaise reponse
GOLD    = "#E0A93F"   # XP / mise en avant
TEXT    = "#ECECEC"   # texte principal
DIM     = "#8A8F9A"   # texte attenue

IS_ANDROID = (platform == "android")


# --------------------------------------------------------------------------
# Utilitaires reseau (appels en arriere-plan)
# --------------------------------------------------------------------------

def run_bg(fn, callback):
    """Execute fn() dans un thread, puis appelle callback(resultat, erreur)
    sur le thread principal de Kivy."""
    def worker():
        try:
            res, err = fn(), None
        except Exception as e:  # pragma: no cover
            res, err = None, e
        Clock.schedule_once(lambda dt: callback(res, err), 0)
    threading.Thread(target=worker, daemon=True).start()


# --------------------------------------------------------------------------
# Widgets de base
# --------------------------------------------------------------------------

class Card(BoxLayout):
    """Conteneur a fond colore et coins arrondis."""
    def __init__(self, bg=CARD, radius=14, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._col = Color(*get_color_from_hex(bg))
            self._rect = RoundedRectangle(radius=[radius])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size


class TapButton(ButtonBehavior, Label):
    """Bouton tactile a coins arrondis."""
    def __init__(self, bg=ACCENT, radius=12, **kw):
        kw.setdefault("color", get_color_from_hex(TEXT))
        kw.setdefault("font_size", sp(16))
        kw.setdefault("markup", True)
        super().__init__(**kw)
        with self.canvas.before:
            self._col = Color(*get_color_from_hex(bg))
            self._rect = RoundedRectangle(radius=[radius])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def set_bg(self, hexcolor):
        self._col.rgba = get_color_from_hex(hexcolor)


class Meter(Widget):
    """Petite barre de progression (ratio entre 0 et 1)."""
    def __init__(self, ratio=0.0, fill=GOLD, **kw):
        super().__init__(**kw)
        self.ratio = max(0.0, min(1.0, ratio))
        self.size_hint_y = None
        self.height = dp(12)
        with self.canvas:
            Color(*get_color_from_hex(CARD2))
            self._bg = RoundedRectangle(radius=[6])
            Color(*get_color_from_hex(fill))
            self._fg = RoundedRectangle(radius=[6])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._fg.pos = self.pos
        self._fg.size = (max(self.height, self.width * self.ratio), self.height)


def auto_label(text, font_size=15, color=TEXT, bold=False, halign="left"):
    """Label dont la hauteur s'ajuste automatiquement au contenu."""
    lbl = Label(text=text, font_size=sp(font_size), color=get_color_from_hex(color),
                bold=bold, halign=halign, valign="top", size_hint_y=None,
                markup=True)

    def _upd(*a):
        lbl.text_size = (lbl.width, None)
        lbl.texture_update()
        lbl.height = lbl.texture_size[1]

    lbl.bind(width=_upd, text=_upd)
    Clock.schedule_once(_upd, 0)
    return lbl


def nav_button(text, bg, callback, height=58):
    """Grand bouton de navigation pleine largeur."""
    btn = TapButton(text=text, bg=bg, font_size=sp(17),
                    size_hint_y=None, height=dp(height))
    btn.bind(on_release=lambda *a: callback())
    return btn


def scroll_column(spacing=12, padding=16):
    """Renvoie (scrollview, grille) : grille verticale a hauteur auto."""
    grid = GridLayout(cols=1, spacing=dp(spacing), padding=dp(padding),
                      size_hint_y=None)
    grid.bind(minimum_height=grid.setter("height"))
    sv = ScrollView(do_scroll_x=False)
    sv.add_widget(grid)
    return sv, grid


# --------------------------------------------------------------------------
# Ecran d'accueil
# --------------------------------------------------------------------------

class HomeScreen(Screen):
    def on_pre_enter(self):
        self.clear_widgets()
        s = core.global_stats()
        sv, col = scroll_column()

        # En-tete
        col.add_widget(auto_label("[b]CultureBoost[/b]", font_size=30,
                                  color=ACCENT))
        col.add_widget(auto_label("Entraine ta culture generale, chaque jour.",
                                  font_size=13, color=DIM))

        # Carte de progression
        card = Card(orientation="vertical", padding=dp(16), spacing=dp(8),
                    size_hint_y=None, height=dp(150))
        card.add_widget(auto_label(
            f"[b]Niveau {s['level']}[/b]  -  {s['title']}",
            font_size=18, color=TEXT))
        ratio = s["xp_in_level"] / s["xp_per_level"]
        card.add_widget(Meter(ratio=ratio))
        card.add_widget(auto_label(
            f"{s['xp_in_level']} / {s['xp_per_level']} XP "
            f"vers le niveau {s['level'] + 1}", font_size=12, color=DIM))
        card.add_widget(auto_label(
            f"Serie : [b]{s['day_streak']}[/b] j   -   "
            f"Precision : [b]{s['accuracy']}%[/b]   -   "
            f"A reviser : [b]{s['due']}[/b]", font_size=13, color=GOLD))
        col.add_widget(card)

        # Boutons de navigation
        app = App.get_running_app()
        col.add_widget(nav_button("Quiz rapide  (10 questions)", ACCENT,
                                  lambda: app.start_quiz(10, "Quiz rapide")))
        col.add_widget(nav_button("Marathon  (25 questions)", ACCENT,
                                  lambda: app.start_quiz(25, "Marathon")))
        rev = f"Revision ciblee  ({s['due']} en attente)"
        col.add_widget(nav_button(rev, GOLD,
                                  lambda: app.start_quiz(20, "Revision ciblee",
                                                         revision=True)))
        col.add_widget(nav_button("Decouverte", TEAL,
                                  lambda: app.go("discovery")))
        col.add_widget(nav_button("Statistiques", CARD2,
                                  lambda: app.go("stats")))
        col.add_widget(nav_button("Reglages", CARD2,
                                  lambda: app.go("settings")))
        self.add_widget(sv)


# --------------------------------------------------------------------------
# Ecran de quiz (sert aussi a la revision)
# --------------------------------------------------------------------------

class QuizScreen(Screen):
    def start(self, amount, label, revision=False):
        self.session_label = label
        self.revision = revision
        self.questions = []
        self.index = 0
        self.n_correct = 0
        self.combo = 0
        self.best_combo = 0
        self.answered = False
        self.origin = ""
        self._show_centered("Chargement des questions...")
        core.update_day_streak()
        if revision:
            run_bg(lambda: (core.due_questions(amount), "revision"),
                   self._on_loaded)
        else:
            run_bg(lambda: core.get_questions(amount), self._on_loaded)

    # -- helpers d'affichage ------------------------------------------------

    def _show_centered(self, message, with_back=False):
        self.clear_widgets()
        root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(16))
        root.add_widget(Widget())
        root.add_widget(auto_label(message, font_size=16, color=DIM,
                                   halign="center"))
        if with_back:
            b = nav_button("Retour a l'accueil", ACCENT,
                           lambda: App.get_running_app().go("home"))
            wrap = BoxLayout(size_hint_y=None, height=dp(58))
            wrap.add_widget(b)
            root.add_widget(wrap)
        root.add_widget(Widget())
        self.add_widget(root)

    def _on_loaded(self, res, err):
        if err or not res:
            self._show_centered("Impossible de charger les questions.\n"
                                "Verifie ta connexion internet.", with_back=True)
            return
        questions, origin = res
        if not questions:
            self._show_centered(
                "Aucune question a reviser pour le moment.\n\n"
                "Joue quelques quiz : les questions ratees\n"
                "apparaitront ici au bon moment.", with_back=True)
            return
        self.questions = questions
        self.origin = origin
        self._show_question()

    def _topbar(self):
        bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        q = self.questions[self.index]
        meta = f"Question {self.index + 1}/{len(self.questions)}"
        if q.get("category"):
            meta += "   -   " + q["category"]
        bar.add_widget(auto_label(meta, font_size=13, color=DIM))
        quit_btn = TapButton(text="X", bg=CARD2, font_size=sp(16),
                             size_hint_x=None, width=dp(46))
        quit_btn.bind(on_release=lambda *a:
                      App.get_running_app().go("home"))
        bar.add_widget(quit_btn)
        return bar

    def _show_question(self):
        self.clear_widgets()
        self.answered = False
        q = self.questions[self.index]

        root = BoxLayout(orientation="vertical")
        root.add_widget(self._topbar())

        sv, col = scroll_column(spacing=12, padding=14)

        # Enonce
        qcard = Card(orientation="vertical", padding=dp(16), size_hint_y=None)
        qlabel = auto_label("[b]" + q["question"] + "[/b]", font_size=18)
        qcard.add_widget(qlabel)
        qcard.bind(minimum_height=qcard.setter("height"))
        qlabel.bind(height=lambda *a:
                    setattr(qcard, "height", qlabel.height + dp(32)))
        col.add_widget(qcard)

        # Reponses (melangees)
        options = q["incorrect"][:] + [q["correct"]]
        import random as _r
        _r.shuffle(options)
        self.answer_widgets = []
        for opt in options:
            btn = TapButton(text=opt, bg=CARD2, font_size=sp(16),
                            size_hint_y=None, height=dp(56), halign="center")
            btn.bind(width=lambda i, w: setattr(i, "text_size", (w - dp(20), None)))
            btn.bind(on_release=lambda inst, t=opt: self._answer(inst, t))
            self.answer_widgets.append((btn, opt))
            col.add_widget(btn)

        self._feedback_slot = col  # pour ajouter le retour apres reponse
        root.add_widget(sv)

        # Barre inferieure
        self.bottom = BoxLayout(size_hint_y=None, height=dp(64),
                                padding=[dp(14), dp(4), dp(14), dp(10)])
        root.add_widget(self.bottom)
        self.add_widget(root)

    def _answer(self, chosen_btn, chosen_text):
        if self.answered:
            return
        self.answered = True
        q = self.questions[self.index]
        success = (chosen_text == q["correct"])

        for btn, text in self.answer_widgets:
            if text == q["correct"]:
                btn.set_bg(GREEN)
            elif btn is chosen_btn:
                btn.set_bg(RED)

        core.record_answer(q, success)
        if success:
            self.n_correct += 1
            self.combo += 1
            self.best_combo = max(self.best_combo, self.combo)
        else:
            self.combo = 0

        # Carte de retour (resultat + anecdote)
        fb = Card(orientation="vertical", bg=CARD, padding=dp(14),
                  spacing=dp(6), size_hint_y=None)
        head = "Correct !" if success else "Faux."
        fb.add_widget(auto_label("[b]" + head + "[/b]", font_size=16,
                                 color=GREEN if success else RED))
        if not success:
            fb.add_widget(auto_label("Bonne reponse : " + q["correct"],
                                     font_size=14, color=TEXT))
        if q.get("anecdote"):
            fb.add_widget(auto_label("Le savais-tu ? " + q["anecdote"],
                                     font_size=13, color=DIM))
        fb.bind(minimum_height=fb.setter("height"))
        self._feedback_slot.add_widget(fb)

        # Bouton "suivante"
        last = (self.index + 1 >= len(self.questions))
        nxt = nav_button("Voir le bilan" if last else "Question suivante",
                         ACCENT, self._next)
        self.bottom.add_widget(nxt)

    def _next(self):
        self.index += 1
        if self.index >= len(self.questions):
            self._summary()
        else:
            self._show_question()

    def _summary(self):
        self.clear_widgets()
        answered = self.index  # nombre repondu
        pct = round(100 * self.n_correct / answered) if answered else 0
        sv, col = scroll_column()

        col.add_widget(auto_label("[b]Bilan de la session[/b]", font_size=24,
                                  color=ACCENT))
        col.add_widget(auto_label(self.session_label + "  -  " + self.origin,
                                  font_size=12, color=DIM))

        card = Card(orientation="vertical", padding=dp(18), spacing=dp(10),
                    size_hint_y=None, height=dp(170))
        card.add_widget(auto_label(
            f"Bonnes reponses : [b]{self.n_correct}/{answered}[/b]   ({pct}%)",
            font_size=18))
        card.add_widget(Meter(ratio=pct / 100, fill=GREEN))
        card.add_widget(auto_label(
            f"Meilleur enchainement : [b]{self.best_combo}[/b]",
            font_size=14, color=GOLD))
        card.add_widget(auto_label(
            f"XP gagnes : [b]+{self.n_correct * core.XP_PER_CORRECT}[/b]",
            font_size=14, color=GOLD))
        col.add_widget(card)

        if pct == 100:
            msg = "Sans-faute. Impressionnant !"
        elif pct >= 70:
            msg = "Solide. Continue comme ca."
        elif pct >= 40:
            msg = "Pas mal. La revision fera la difference."
        else:
            msg = "Difficile, mais chaque erreur sera revue. C'est ainsi qu'on progresse."
        col.add_widget(auto_label(msg, font_size=14, color=TEXT))

        col.add_widget(nav_button("Retour a l'accueil", ACCENT,
                                  lambda: App.get_running_app().go("home")))
        self.add_widget(sv)


# --------------------------------------------------------------------------
# Ecran des statistiques
# --------------------------------------------------------------------------

class StatsScreen(Screen):
    def on_pre_enter(self):
        self.clear_widgets()
        s = core.global_stats()
        cats = core.category_stats()
        sv, col = scroll_column()

        col.add_widget(auto_label("[b]Statistiques[/b]", font_size=26,
                                  color=ACCENT))

        # Carte resume
        card = Card(orientation="vertical", padding=dp(16), spacing=dp(8),
                    size_hint_y=None, height=dp(210))
        card.add_widget(auto_label(
            f"[b]Niveau {s['level']}[/b]  -  {s['title']}",
            font_size=18, color=GOLD))
        card.add_widget(Meter(ratio=s["xp_in_level"] / s["xp_per_level"]))
        for line in [
            f"XP total : [b]{s['xp']}[/b]",
            f"Questions repondues : [b]{s['total']}[/b]",
            f"Bonnes reponses : [b]{s['correct']}[/b]  ({s['accuracy']}%)",
            f"Meilleur enchainement : [b]{s['best_combo']}[/b]",
            f"Serie de jours actifs : [b]{s['day_streak']}[/b]",
            f"A reviser maintenant : [b]{s['due']}[/b]",
        ]:
            card.add_widget(auto_label(line, font_size=13))
        col.add_widget(card)

        # Performance par categorie
        col.add_widget(auto_label("[b]Par categorie[/b]", font_size=18))
        if not cats:
            col.add_widget(auto_label(
                "Joue quelques quiz pour voir apparaitre tes points "
                "forts et tes points faibles ici.", font_size=13, color=DIM))
        for c in cats:
            row = Card(orientation="vertical", bg=CARD, padding=dp(12),
                       spacing=dp(6), size_hint_y=None, height=dp(70))
            color = GREEN if c["pct"] >= 70 else (GOLD if c["pct"] >= 40 else RED)
            row.add_widget(auto_label(
                f"{c['category']}   -   [b]{c['pct']}%[/b]  "
                f"({c['correct']}/{c['seen']})", font_size=14, color=color))
            row.add_widget(Meter(ratio=c["pct"] / 100, fill=color))
            col.add_widget(row)

        col.add_widget(nav_button("Retour", CARD2,
                                  lambda: App.get_running_app().go("home")))
        self.add_widget(sv)


# --------------------------------------------------------------------------
# Ecran de decouverte
# --------------------------------------------------------------------------

class DiscoveryScreen(Screen):
    def on_pre_enter(self):
        self._render(loading=True)
        self._reload()

    def _reload(self):
        run_bg(lambda: core.get_facts(4), self._on_facts)

    def _on_facts(self, facts, err):
        self._render(facts=facts or [], err=err)

    def _render(self, facts=None, loading=False, err=None):
        self.clear_widgets()
        sv, col = scroll_column()
        col.add_widget(auto_label("[b]Decouverte[/b]", font_size=26,
                                  color=TEAL))
        col.add_widget(auto_label(
            "Quelques savoirs au hasard pour elargir tes horizons.",
            font_size=13, color=DIM))

        if loading:
            col.add_widget(auto_label("Chargement...", font_size=14, color=DIM))
        elif not facts:
            col.add_widget(auto_label(
                "Aucun contenu recupere. Verifie ta connexion internet.",
                font_size=14, color=DIM))
        else:
            for f in facts:
                card = Card(orientation="vertical", bg=CARD, padding=dp(14),
                            spacing=dp(6), size_hint_y=None)
                card.add_widget(auto_label("[b]" + f["title"] + "[/b]",
                                           font_size=16, color=GREEN))
                card.add_widget(auto_label(f["text"], font_size=14))
                card.add_widget(auto_label("Source : " + f.get("source", ""),
                                           font_size=11, color=DIM))
                card.bind(minimum_height=card.setter("height"))
                col.add_widget(card)

        col.add_widget(nav_button("Nouveaux faits", TEAL,
                                  lambda: self.on_pre_enter()))
        col.add_widget(nav_button("Retour", CARD2,
                                  lambda: App.get_running_app().go("home")))
        self.add_widget(sv)


# --------------------------------------------------------------------------
# Ecran des reglages
# --------------------------------------------------------------------------

class SettingsScreen(Screen):
    def on_pre_enter(self):
        self.clear_widgets()
        sv, col = scroll_column()
        col.add_widget(auto_label("[b]Reglages[/b]", font_size=26, color=ACCENT))

        # Source des questions (information)
        card = Card(orientation="vertical", padding=dp(14), spacing=dp(8),
                    size_hint_y=None, height=dp(150))
        card.add_widget(auto_label("[b]Source des questions[/b]", font_size=15))
        card.add_widget(auto_label(
            "Questions en francais fournies par QuizzAPI. Hors connexion, "
            "une banque de questions integree prend le relais. Tes erreurs "
            "reviennent automatiquement en revision ciblee.",
            font_size=12, color=DIM))
        card.bind(minimum_height=card.setter("height"))
        col.add_widget(card)

        # Reinitialisation
        card2 = Card(orientation="vertical", padding=dp(14), spacing=dp(8),
                     size_hint_y=None, height=dp(120))
        card2.add_widget(auto_label("[b]Progression[/b]", font_size=15))
        card2.add_widget(auto_label(
            "Efface XP, niveaux, statistiques et questions a reviser.",
            font_size=12, color=DIM))
        card2.add_widget(nav_button("Reinitialiser la progression", RED,
                                    self._confirm_reset, height=48))
        col.add_widget(card2)

        col.add_widget(auto_label(
            "CultureBoost - donnees stockees uniquement sur ton telephone.",
            font_size=11, color=DIM))
        col.add_widget(nav_button("Retour", CARD2,
                                  lambda: App.get_running_app().go("home")))
        self.add_widget(sv)

    def _confirm_reset(self):
        content = BoxLayout(orientation="vertical", spacing=dp(14),
                            padding=dp(16))
        content.add_widget(auto_label(
            "Effacer toute la progression ?\nCette action est irreversible.",
            font_size=15, halign="center"))
        row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        popup = Popup(title="Confirmation", size_hint=(0.86, 0.4),
                      content=content)
        cancel = TapButton(text="Annuler", bg=CARD2)
        cancel.bind(on_release=lambda *a: popup.dismiss())
        confirm = TapButton(text="Effacer", bg=RED)

        def _do(*a):
            core.reset_progress()
            popup.dismiss()
            self.on_pre_enter()

        confirm.bind(on_release=_do)
        row.add_widget(cancel)
        row.add_widget(confirm)
        content.add_widget(row)
        popup.open()


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------

class CultureBoostApp(App):
    def build(self):
        self.title = "CultureBoost"
        Window.clearcolor = get_color_from_hex(BG)
        if not IS_ANDROID:
            Window.size = (400, 740)

        core.init_db(self.user_data_dir)

        self.sm = ScreenManager(transition=SlideTransition(duration=0.18))
        self.sm.add_widget(HomeScreen(name="home"))
        self.sm.add_widget(QuizScreen(name="quiz"))
        self.sm.add_widget(StatsScreen(name="stats"))
        self.sm.add_widget(DiscoveryScreen(name="discovery"))
        self.sm.add_widget(SettingsScreen(name="settings"))

        Window.bind(on_keyboard=self._on_key)
        return self.sm

    def go(self, screen_name):
        self.sm.transition.direction = (
            "right" if screen_name == "home" else "left")
        self.sm.current = screen_name

    def start_quiz(self, amount, label, revision=False):
        quiz = self.sm.get_screen("quiz")
        quiz.start(amount, label, revision=revision)
        self.sm.transition.direction = "left"
        self.sm.current = "quiz"

    def _on_key(self, window, key, *args):
        """Gere le bouton 'retour' d'Android (code 27)."""
        if key == 27:
            if self.sm.current != "home":
                self.go("home")
                return True
            return False  # quitte l'application depuis l'accueil
        return False


if __name__ == "__main__":
    CultureBoostApp().run()
