from flask import Flask
from flask_migrate import Migrate, upgrade
from flask_security import Security
from models import db, seedData, user_datastore 
import os
from dotenv import load_dotenv
from config import Config  # Import Config class

#------ import the blue prints -------------#
from areas.site.sitePages import siteBluePrint
from areas.cashier.transactions import TransactionBluePrint
from areas.cashier.customerpages import CustomerPageBluePrint
from areas.admin.userpage import userPageBluePrint
from areas.login_logout.sec import Login_LogoutBluePrint
from areas.mobil.mobile import mobileBluePrint


load_dotenv()

# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)  # Load configurations from config.py


db.app = app
db.init_app(app)
migrate = Migrate(app,db)
security = Security(app, user_datastore)


#------------ blueprints setup
app.register_blueprint(siteBluePrint)
app.register_blueprint(TransactionBluePrint)
app.register_blueprint(CustomerPageBluePrint)
app.register_blueprint(userPageBluePrint)
app.register_blueprint(Login_LogoutBluePrint)
app.register_blueprint(mobileBluePrint)





if __name__  == "__main__":
    with app.app_context():
        upgrade()
        seedData(db)
    app.run(debug=True)