from pathlib import Path

from flask import Flask

from .db import close_db, init_app as init_db_app
from .routes import bp as main_bp


def create_app() -> Flask:
    package_root = Path(__file__).resolve().parent
    project_root = package_root.parent

    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config["SECRET_KEY"] = "dev"
    app.config["DATABASE"] = str(project_root / "data" / "parseplayer.db")
    app.config["MUSIC_ROOT"] = str(Path.home() / "Music")

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    init_db_app(app)
    app.teardown_appcontext(close_db)
    app.register_blueprint(main_bp)

    with app.app_context():
        from .db import init_db

        init_db()

    return app
