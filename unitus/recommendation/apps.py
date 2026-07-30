import os
import sys
import threading

from django.apps import AppConfig


class RecommendationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recommendation'

    def ready(self):
        """
        The multi-second delay on the *first* recommendation request isn't
        Django/DB-related — it's SentenceTransformer(...) inside
        recommendation/embedder.py loading the multilingual-e5-small model
        weights into memory for the first time. Previously that happened
        lazily on whichever request first touched MatchScoreService.

        Instead, kick that load off here, in a background thread, as soon
        as the server process starts — so by the time a real user hits
        "Recommended Projects" or "Find Candidates", the model is already
        warm. The thread doesn't block startup, so `runserver` still comes
        up immediately.

        Guards:
        - Only for `runserver` / actual server processes, not one-off
          management commands (migrate, makemigrations, shell, ...) where
          preloading a ~500MB model would just waste time.
        - `RUN_MAIN` check avoids doing this twice under the dev
          autoreloader, which imports apps in both the watcher and the
          real worker process.
        """
        is_manage_py = len(sys.argv) > 0 and sys.argv[0].endswith('manage.py')
        is_runserver = is_manage_py and 'runserver' in sys.argv
        is_other_command = is_manage_py and not is_runserver

        if is_other_command:
            return
        if is_runserver and os.environ.get('RUN_MAIN') != 'true':
            return  # autoreload watcher process — the real worker sets RUN_MAIN

        def _warm_up_embedder():
            try:
                from recommendation.services import get_embedder
                get_embedder()
            except Exception:
                # Never let a preload failure take the server down — it'll
                # just fall back to the old lazy-load-on-first-request path.
                pass

        threading.Thread(target=_warm_up_embedder, daemon=True, name='embedder-warmup').start()
