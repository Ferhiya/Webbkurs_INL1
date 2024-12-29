from flask import Flask, render_template, request
from flask_migrate import Migrate, upgrade

from models import db, seedData


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:password@localhost/Bank'
db.app = app
db.init_app(app)
migrate = Migrate(app,db)



@app.route("/")
def startpage():
    return render_template("index.html")


if __name__  == "__main__":
    with app.app_context():
        upgrade()
        seedData(db)
    app.run(debug=True)