from App import create_app
from App.database import db, get_migrate
from App.controllers import initialize

app = create_app()
migrate = get_migrate(app)

@app.cli.command("init", help="Creates and initializes the database")
def init():
    initialize()
    print('database intialized')