from flask import Flask, render_template, request, redirect, url_for, flash, Blueprint
from flask_security.utils import verify_password
from flask_login import login_user, logout_user
from models import  User


Login_LogoutBluePrint = Blueprint('securityPage', __name__)



# Custom login route
@Login_LogoutBluePrint.route("/login", methods=["GET", "POST"])
def custom_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Check if the user exists
        user = User.query.filter_by(email=email).first()
        if user and verify_password(password, user.password):
            login_user(user)
            flash("Inloggning lyckades!", "success")

            # Redirect based on user role
            if user.has_role("Admin"):
                return redirect(url_for("UserPage.admin_page"))
            elif user.has_role("Cashier"):
                return redirect(url_for("CustomerPage.cashier_page"))
            else:
                return redirect(url_for("site.startpage"))
        else:
            flash("Icke godkänd email eller lösenord.", "danger")

    return render_template("login.html")

# Logout route
@Login_LogoutBluePrint.route("/logout")
def logout():
    logout_user()
    flash("Du har loggat ut.", "success")
    return redirect(url_for("securityPage.custom_login"))  # Redirects to login page