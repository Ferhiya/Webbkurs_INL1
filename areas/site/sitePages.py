from flask import Flask, render_template, Blueprint
from flask_security import login_required, roles_required
from models import db, Customer, Account


siteBluePrint = Blueprint('site', __name__)


@siteBluePrint.route("/")
def startpage():
    total_customers = Customer.query.count()
    total_accounts = Account.query.count()
    total_balance = db.session.query(db.func.sum(Account.balance)).scalar() or 0.0
    total_balance_str = f"{round(total_balance, 2)}"

    # Hämta statistik per land
    country_stats = db.session.query(
        Customer.country,
        db.func.count(db.distinct(Customer.id)).label('total_customers'),
        db.func.count(Account.id).label('total_accounts'),
        db.func.sum(Account.balance).label('total_balance')
    ).join(Account).group_by(Customer.country).all()

    return render_template(
        "index.html",
        total_customers=total_customers,
        total_accounts=total_accounts,
        total_balance=total_balance_str,
        country_stats=country_stats
    )
    
@siteBluePrint.route("/cashier", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def cashier_page():

    return render_template("cashier.html")
    
    

@siteBluePrint.route("/admin")
@login_required
@roles_required("Admin")
def admin_page():
    return render_template("admin.html")    