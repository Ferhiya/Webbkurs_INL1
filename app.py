from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_migrate import Migrate, upgrade
from flask_security import Security, SQLAlchemyUserDatastore, login_required, roles_required, LoginForm, url_for_security, current_user
from flask_security.utils import verify_password
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash
from models import db, seedData, Customer, Account, user_datastore, User, Role, Transaction, TransactionOperation, TransactionType, AccountType
import os
from dotenv import load_dotenv
from sqlalchemy import or_, func, String
from decimal import Decimal
import random
import decimal
import datetime
from datetime import datetime
from forms import AccountForm
load_dotenv()
from flask import Blueprint



app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:password@localhost/Bank'
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SECURITY_PASSWORD_SALT'] = os.getenv("SECURITY_PASSWORD_SALT")

app.config['SECURITY_LOGIN_USER_TEMPLATE']='login.html'

db.app = app
db.init_app(app)
migrate = Migrate(app,db)
security = Security(app, user_datastore)



@app.route("/")
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
# Custom login route
@app.route("/login", methods=["GET", "POST"])
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
                return redirect(url_for("admin_page"))
            elif user.has_role("Cashier"):
                return redirect(url_for("cashier_page"))
            else:
                return redirect(url_for("startpage"))
        else:
            flash("Icke godkänd email eller lösenord.", "danger")

    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    logout_user()
    flash("Du har loggat ut.", "success")
    return redirect(url_for("custom_login"))  # Redirects to login page

#------------Cashier work pages-----------
@app.route("/cashier", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def cashier_page():

    return render_template("cashier.html")



#search customer
@app.route("/cashierwork/customer", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def customer_page():
    # Get search input from the user
    search_query = request.args.get('search', '').strip()  
    sort_by = request.args.get('search_field_or_sort_by', 'given_name')  # Default sort by name
    sort_order = request.args.get('sort_order', 'asc')  # Default sorting is ascending
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Number of customers per page

    # Start with all customers
    customers_query = Customer.query

    # If the user entered a search query
    if search_query:
        search_terms = search_query.split(",")  # Split by commas
        search_terms = [term.strip().lower() for term in search_terms]  # Remove spaces and lowercase

        # Build a search filter for each term
        filters = []
        for term in search_terms:
            filters.append(
                or_(
                    func.lower(Customer.given_name).ilike(f"%{term}%"),  # Search in given_name
                    func.lower(Customer.city).ilike(f"%{term}%")  # Search in city
                )
            )

        # Apply the search filters
        customers_query = customers_query.filter(or_(*filters))  

    # Sorting logic
    if sort_order == 'desc':
        customers_query = customers_query.order_by(db.desc(getattr(Customer, sort_by)))
    else:
        customers_query = customers_query.order_by(getattr(Customer, sort_by))

    # Paginate the results (limit results per page)
    customers = customers_query.paginate(page=page, per_page=per_page, error_out=False)

    # Calculate the total balance for each customer
    for customer in customers.items:
        customer.total_balance = sum(account.balance for account in customer.accounts)

    # Send the customer data to the template
    return render_template(
        "cashierwork/customer.html",
        customers=customers.items,
        search_query=search_query,
        search_field_or_sort_by=sort_by,
        page=page,
        total_pages=customers.pages,
        sort_order=sort_order
    )
    
    

# View account
@app.route("/cashierwork/view_account", methods=["GET"])
@login_required
@roles_required("Cashier")
def view_account():
    customer_id = request.args.get('customer_id', type=int)

    if not customer_id:
        flash("Kund-ID saknas!", "danger")
        return redirect(url_for("cashier_page"))

    customer = Customer.query.get(customer_id)

    if not customer:
        flash("Kunden hittades inte!", "danger")
        return redirect(url_for("cashier_page"))

    return render_template("cashierwork/view_account.html", customer=customer)


#transactions record/history for accounts
@app.route('/cashierwork/account_details/<int:account_id>')
@login_required
@roles_required("Cashier")
def account_details(account_id):
    # Fetch the account by its ID
    account = Account.query.filter_by(id=account_id).first()

    # Check if the account exists
    if account is None:
        # If no account is found, handle it here (e.g., show an error message)
        flash("Konto hittades inte", "danger")
        return redirect(url_for('some_route'))  # Redirect to some other page

    # Fetch all transactions for this account and order them by date descending
    transactions = account.transactions  # This will give you all related transactions

    # Sort transactions by date in descending order manually
    transactions = sorted(transactions, key=lambda t: t.date, reverse=True)

    return render_template(
        'cashierwork/account_details.html', 
        account=account, 
        transactions=transactions
    )



#Edit customer   
@app.route('/cashierwork/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
@login_required
@roles_required("Cashier")
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    if request.method == 'POST':
        # Update customer details from form input
        
        customer.given_name = request.form['given_name']
        customer.surname = request.form['surname']
        customer.streetaddress = request.form['streetaddress']
        customer.city = request.form['city']
        customer.zipcode = request.form['zipcode']
        customer.country = request.form['country']
        customer.country_code = request.form['country_code']
        customer.telephone_country_code = request.form['telephone_country_code']
        customer.telephone = request.form['telephone']
        customer.email_address = request.form['email_address']
        
        # Server-side validation
        if not all([customer.given_name, customer.surname, customer.streetaddress, customer.city, customer.zipcode, customer.country, customer.country_code, customer.telephone_country_code, customer.telephone, customer.email_address]):
            flash('Alla fält måste fyllas i!', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        # Validate that the length of the input fields doesn't exceed the maximum lengths defined in the model
        if len(customer.given_name) > 50 or len(customer.surname) > 50:
            flash('Namn och efter namn kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        if len(customer.streetaddress) > 50:
            flash('Adress kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        if len(customer.city) > 70:
            flash('Stad kan inte vara mer än 70 kärkaterer', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        if len(customer.zipcode) > 15:
            flash('Postnummer kan inte vara mer än 15 kärkaterer', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        if len(customer.country) > 60:
            flash('Land kan inte vara mer än 60 kärkaterer', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        if len(customer.country_code) != 2:
            flash('Landskod kan inte kan inte vara mer än 2 kärkaterer.', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))




        if len(customer.telephone_country_code) > 10:
            flash('Telefonkod kan inte vara mer än 10 kärkaterer', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        if len(customer.telephone) < 10 or len(customer.telephone) > 20:
            flash('Telefon kan inte vara mer än 10 kärkaterer', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        if len(customer.email_address) > 50:
            flash('Email kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


        # Validate email format
        if not validate_email(customer.email_address):
            flash('Icke godkänd email format', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer.id))


       

        db.session.commit()
        flash('Kundinformation uppdaterad!', 'success')
        return redirect(url_for('view_account', customer_id=customer.id))

    return render_template('cashierwork/edit_customer.html', customer=customer)


#search customer
@app.route("/cashierwork/search_customer_for_account", methods=["GET"])
@login_required
@roles_required("Cashier")
def search_customer_for_account():
    search_query = request.args.get("search", "").strip()  # Get the search term
    customers = []  # Default to an empty list (no results shown initially)

    if search_query:  # Only search if a query is entered
        customers = Customer.query.filter(
            func.lower(Customer.given_name).like(f"%{search_query.lower()}%")
            | func.lower(Customer.surname).like(f"%{search_query.lower()}%")
            | func.cast(Customer.id, String).like(f"%{search_query}%")  # Search by ID (numeric)
            | func.lower(Customer.email_address).like(f"%{search_query.lower()}%")
        ).all()  # Fetch all matching customers

    return render_template(
        "cashierwork/search_customer_for_account.html",
        customers=customers,  # Pass the customers list
        search_query=search_query
    )

 
#create account    
@app.route("/cashierwork/create_account", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def create_account():
    customer_id = request.args.get('customer_id')
    customer = Customer.query.get(customer_id)
    if not customer:
        flash("Kunden hittades inte!", "danger")
        return redirect(url_for('cashier_page'))

    form = AccountForm()

    if form.validate_on_submit():
        # Create the new account
        account = Account(
            customer_id=customer.id,
            account_type=form.account_type.data,
            balance=form.initial_balance.data,
            created=datetime.utcnow()  # Set the created column to the current UTC time
        )

        db.session.add(account)
        db.session.commit()

        flash("Konto har skapats!", "success")
        return redirect(url_for('create_account'))  # Redirect to the cashier page or wherever you want

    return render_template("cashierwork/create_account.html", form=form, customer=customer)





#Create customer
@app.route("/cashierwork/create_customer", methods=["GET", "POST"])
def create_customer():
    if request.method == "POST":
        # Get data from the form
        given_name = request.form.get("given_name")
        surname = request.form.get("surname")
        streetaddress = request.form.get("streetaddress")
        city = request.form.get("city")
        zipcode = request.form.get("zipcode")
        country = request.form.get("country")
        country_code = request.form.get("country_code")
        birthday = request.form.get("birthday")
        national_id = request.form.get("national_id")
        telephone_country_code = request.form.get("telephone_country_code")
        telephone = request.form.get("telephone")
        email_address = request.form.get("email_address")

        # Server-side validation
        if not all([given_name, surname, streetaddress, city, zipcode, country, country_code, birthday, national_id, telephone_country_code, telephone, email_address]):
            flash('Alla fält måste fyllas in!', 'danger')
            return redirect(url_for('create_customer'))

        # Validate that the length of the input fields doesn't exceed the maximum lengths defined in the model
        if len(given_name) > 50 or len(surname) > 50:
            flash('Namn och efternamn kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        if len(streetaddress) > 50:
            flash('Adress kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        if len(city) > 70:
            flash('Stad kan inte vara mer än 70 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        if len(zipcode) > 15:
            flash('Postnummer kan inte vara mer än 15 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        if len(country) > 60:
            flash('Land kan inte vara mer än 60 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        if len(country_code) != 2:
            flash('Landskod kan inte vara mer än 2 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        if len(national_id) > 20:
            flash('personnummer kan inte vara mer än 20 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        if len(telephone_country_code) > 10:
            flash('Telefonkod kan inte vara mer än 10 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        if len(telephone) < 10 or len(telephone) > 15:
            flash('Telefon nummer måste vara 10 till 15 kärakerer', 'danger')
            return redirect(url_for('create_customer'))

        if len(email_address) > 50:
            flash('Email kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('create_customer'))

        # Validate email format
        if not validate_email(email_address):
            flash('Icke godkänd email format!', 'danger')
            return redirect(url_for('create_customer'))

        # Validate that the birthdate is not in the future
        birthday_date = datetime.strptime(birthday, '%Y-%m-%d')
        if birthday_date > datetime.now():
            flash('Födelsedag kan inte vara i framtid!', 'danger')
            return redirect(url_for('create_customer'))

        # Check if the email or national ID already exists
        customer_by_email = db.session.query(Customer).filter_by(email_address=email_address).first()
        customer_by_national_id = db.session.query(Customer).filter_by(national_id=national_id).first()

        if customer_by_email:
            flash('Email adress används redan.', 'danger')
            return redirect(url_for('create_customer'))

        if customer_by_national_id:
            flash('Personnummer används redan.', 'danger')
            return redirect(url_for('create_customer'))


        # Create a new Customer object
        new_customer = Customer(
            given_name=given_name,
            surname=surname,
            streetaddress=streetaddress,
            city=city,
            zipcode=zipcode,
            country=country,
            country_code=country_code,
            birthday=birthday_date,
            national_id=national_id,
            telephone_country_code=telephone_country_code,
            telephone=telephone,
            email_address=email_address
        )

        # Add the new customer to the database
        db.session.add(new_customer)
        db.session.commit()  # Commit so the customer id is assigned

        # Create a transaction account for the new customer
        new_account = Account(
            customer_id=new_customer.id,  # Link the account to the new customer
            created=datetime.now(),  # Set the account creation time
            balance=0.0,  # Starting balance is 0
            account_type=AccountType.PERSONAL  # Set a default account type (e.g., PERSONAL)
        )

        # Add the new account to the database
        db.session.add(new_account)
        db.session.commit()

        # Success message
        flash('Kund har skapats!', 'success')

        return redirect(url_for('create_customer'))

    # If it's a GET request, render the form
    return render_template("cashierwork/create_customer.html")


# Helper function to validate email format
def validate_email(email):
    import re
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None





#Deposit money into account
@app.route("/cashierwork/deposit", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def deposit_page():
    search_query = request.args.get("search", "").strip()
    customer_id = request.args.get("customer_id")
    account_id = request.args.get("account_id")

    customers = []
    selected_customer = None
    selected_account = None

    # Search for customers
    if search_query:
        customers = Customer.query.filter(
            Customer.given_name.ilike(f"%{search_query}%")
        ).all()

    # Get the selected customer
    if customer_id:
        selected_customer = Customer.query.get(customer_id)

    # Get the selected account
    if account_id and selected_customer:
        selected_account = Account.query.get(account_id)

    # Handle deposit request
    if request.method == "POST" and selected_account:
        try:
            amount_str = request.form.get("amount", "0").strip()

            # Check if amount is a valid decimal number
            try:
                amount = decimal.Decimal(amount_str)
            except:
                flash("Ogiltigt belopp, ange ett korrekt nummer.", "danger")
                return redirect(url_for("deposit_page", customer_id=customer_id, account_id=account_id))

            if amount <= 0:
                flash("Beloppet måste vara större än 0.", "danger")
                return redirect(url_for("deposit_page", customer_id=customer_id, account_id=account_id))
            

            # Calculate new balance
            new_balance = selected_account.balance + amount

            # Create a transaction record
            transaction = Transaction(
                type=TransactionType.CREDIT,
                operation=TransactionOperation.DEPOSIT_CASH,
                date=datetime.utcnow(),
                amount=amount,
                new_balance=new_balance,
                account_id=selected_account.id
            )

            # Update account balance
            selected_account.balance = new_balance

            # Commit to database
            db.session.add(transaction)
            db.session.commit()

            flash(f"Insättning på {amount} kr lyckades!", "success")
            return redirect(url_for("deposit_page", customer_id=customer_id))

        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            flash("Något gick fel. Försök igen.", "danger")
            print(f"Error during deposit: {e}")  # Debugging output

    return render_template(
        "cashierwork/deposit.html",
        customers=customers,
        search_query=search_query,
        selected_customer=selected_customer,
        selected_account=selected_account
    )


#withdraw money from account
@app.route("/cashierwork/withdraw", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def withdraw_page():
    search_query = request.args.get("search", "").strip()
    customer_id = request.args.get("customer_id")
    account_id = request.args.get("account_id")

    customers = []
    selected_customer = None
    selected_account = None

    # Search for customers
    if search_query:
        customers = Customer.query.filter(
            Customer.given_name.ilike(f"%{search_query}%")
        ).all()

    # Get the selected customer
    if customer_id:
        selected_customer = Customer.query.get(customer_id)

    # Get the selected account
    if account_id and selected_customer:
        selected_account = Account.query.get(account_id)

    # Handle withdrawal request
    if request.method == "POST" and selected_account:
        try:
            amount_str = request.form.get("amount", "0").strip()
            account_str= request.form.get("account_id", type=int)
            selected_account = Account.query.filter_by(id=account_str).first()
            
            # Check if amount is a valid decimal number
            try:
                amount = decimal.Decimal(amount_str)
            except:
                flash("Ogiltigt belopp, ange ett korrekt nummer.", "danger")
                return redirect(url_for("withdraw_page", customer_id=customer_id, account_id=account_id))

            if amount <= 0:
                flash("Beloppet måste vara större än 0.", "danger")
                return redirect(url_for("withdraw_page", customer_id=customer_id, account_id=account_id))

            # Ensure there's enough balance
            if amount > selected_account.balance:
                flash("Otillräckligt saldo för uttag.", "danger")
                return redirect(url_for("withdraw_page", customer_id=customer_id, account_id=account_id))

            # Calculate new balance (subtract amount for withdrawal)
            new_balance = selected_account.balance - amount

            # Create a transaction record
            transaction = Transaction(
                type=TransactionType.DEBIT,  # Use DEBIT for withdrawals
                operation=TransactionOperation.BANK_WITHDRAWL,
                date=datetime.utcnow(),
                amount=-amount,
                new_balance=new_balance,
                account_id=selected_account.id
            )
            
            

            # Update account balance
            selected_account.balance = new_balance

            # Commit to database
            db.session.add(transaction)
            db.session.commit()

            flash(f"Uttag på {amount} kr lyckades!", "success")
            return redirect(url_for(
              "withdraw_page", customers=customers,
               search_query=search_query,
               selected_customer=selected_customer,
               selected_account=selected_account))

        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            flash("Något gick fel. Försök igen.", "danger")
            print(f"Error during withdrawal: {e}")  # Debugging output

    return render_template(
        "cashierwork/withdraw.html",
        customers=customers,
        search_query=search_query,
        selected_customer=selected_customer,
        selected_account=selected_account
    )
    
 
#transfer money between accounts and customers    
@app.route('/cashierwork/transfer', methods=['GET', 'POST'])
@login_required
@roles_required("Cashier")
def transfer_page():
    
    
    from_search_query = request.args.get("from_search", "") 
    to_search_query = request.args.get("to_search", "") 
    from_accounts = [] #variabler för att spara sökreultat
    to_accounts = [] #variabler för att spara sökreultat
    from_account = None
    to_account = None

   #söker i databasen för att see om det finns customers som matchar sökresultaet (Från-konto) 
    if from_search_query:
        from_accounts = Account.query.join(Customer).filter(
            (Account.id.ilike(f"%{from_search_query}%")) |
            (Customer.given_name.ilike(f"%{from_search_query}%")) |
            (Customer.surname.ilike(f"%{from_search_query}%"))
        ).all()

    #söker i databasen för att see om det finns customers som matchar sökresultaet (Till-konto)
    if to_search_query:
        to_accounts = Account.query.join(Customer).filter(
            (Account.id.ilike(f"%{to_search_query}%")) |
            (Customer.given_name.ilike(f"%{to_search_query}%")) |
            (Customer.surname.ilike(f"%{to_search_query}%"))
        ).all()

    # Hämta de valda kontona baserat på ID:n i URL-parametrarna
    from_account_id = request.args.get("from_account_id")
    to_account_id = request.args.get("to_account_id")

     # Kontrollera om ett Från-konto är valt och hämta det
    if from_account_id:
        from_account = Account.query.get(from_account_id)
    # Kontrollera om ett Till-konto är valt och hämta det
    if to_account_id:
        to_account = Account.query.get(to_account_id)


     # Hantera POST-begäran för överföring aktiveras när cashier klickar på 'Överför'
    if request.method == "POST":
        amount = Decimal(request.form.get("amount")) # Hämta det belopp som ska överföras (som en Decimal)

         # Kontrollera att båda kontona är valda och att Från-kontot har tillräckligt med saldo
        if from_account and to_account and from_account.balance >= amount:
            # Genomför överföring: dra beloppet från Från-kontot och lägg till på Till-kontot
            from_account.balance -= amount  # Minska saldo på Från-kontot
            to_account.balance += amount    # Öka saldo på Till-kontot
             
             
             # Skapa transaktioner för både Från- och Till-konton och spara i databasen
            # Debit för Från-konto
            transaction_from = Transaction(
                type=TransactionType.DEBIT,
                operation=TransactionOperation.TRANSFER,
                date=datetime.utcnow(),
                amount=-amount,
                new_balance=from_account.balance,
                account_id=from_account.id
            )
            
             # Kredit för Till-konto
            transaction_to = Transaction(
                type=TransactionType.CREDIT,
                operation=TransactionOperation.TRANSFER,
                date=datetime.utcnow(),
                amount=amount,
                new_balance=to_account.balance,
                account_id=to_account.id
            )
            
            # Lägg till transaktionerna i databasen
            db.session.add(transaction_from)
            db.session.add(transaction_to)
            db.session.commit()

            #skicka feedback message till user. 
            flash("Överföringen genomfördes!", "success")
            return redirect(url_for("transfer_page", from_account_id=from_account.id, to_account_id=to_account.id))

        else:
            flash("Fel: Otillräckligt saldo eller ogiltiga konton!", "danger")
            
# Rendera sidan med alla variabler för att visa sökresultat, valda konton och hantera formulärdata
    return render_template(
        "cashierwork/transfer.html",  # HTML-sidan som ska renderas
        from_search_query=from_search_query,  # Skickar sökfrågan för Från-konto
        to_search_query=to_search_query,  # Skickar sökfrågan för Till-konto
        from_accounts=from_accounts,  # Skickar listan av Från-konton som matchar sökningen
        to_accounts=to_accounts,  # Skickar listan av Till-konton som matchar sökningen
        from_account=from_account,  # Skickar det valda Från-kontot
        to_account=to_account,  # Skickar det valda Till-kontot
        from_account_id=from_account_id,  # Skickar ID för det valda Från-kontot
        to_account_id=to_account_id   # Skickar ID för det valda Till-kontot
    )




@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    # Kolla om kunden har konton
    if customer.accounts:  
        flash('Kan inte ta bort kund med activa konton!', 'danger')
        return redirect(url_for("customer_page"))   # Ändra till rätt vy

    db.session.delete(customer)
    db.session.commit()
    flash('Kund har tagits bort!', 'success')
    return redirect(url_for("customer_page"))  # Ändra till rätt vy



# ---------- Admin work pages ---------------------

@app.route("/admin")
@login_required
@roles_required("Admin")
def admin_page():
    return render_template("admin.html")

@app.route('/manageUsers', methods=['GET', 'POST'])
def manage_users():
    search_query = request.args.get('search', '')  # Get the search query
    sort_field = request.args.get('sort', 'email')  # Default sorting by email
    sort_order = request.args.get('order', 'asc')  # Default order (asc or desc)

    # Search and filter by email or role (case-insensitive)
    users_query = User.query.filter(
        (User.email.ilike(f'%{search_query}%')) |  # Case-insensitive search by email
        (User.roles.any(Role.name.ilike(f'%{search_query}%')))  # Case-insensitive search by role name
    )

    # Sort the results based on the selected field (email or role)
    if sort_order == 'asc':
        users_query = users_query.order_by(getattr(User, sort_field).asc())
    else:
        users_query = users_query.order_by(getattr(User, sort_field).desc())

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Number of users per page
    users = users_query.paginate(page=page, per_page=per_page, error_out=False)

    # Send data to the template
    return render_template('adminwork/manageUsers.html', users=users.items, 
                           search_query=search_query, sort_field=sort_field, 
                           sort_order=sort_order, page=page, total_pages=users.pages)


@app.route('/update_role/<int:user_id>', methods=['POST'])
def update_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role_name = request.form.get('role')

    # Get the role object corresponding to the new role name
    new_role = Role.query.filter_by(name=new_role_name).first()

    if new_role:
        # Remove all roles assigned to the user
        user.roles.clear()

        # Add the new role to the user
        user.roles.append(new_role)
        
        # Commit the changes
        db.session.commit()

        flash('Användar roll har uppdaterats!', 'success')
    else:
        flash('icke godkönd roll.', 'danger')
    
    return redirect(url_for('manage_users'))


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Användar har tagits bort!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/adminwork/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role_name = request.form.get('role')

        # Check if role exists
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash('Roll hittas inte!', 'danger')
            return redirect(url_for('manage_users'))

        # Use email as fs_uniquifier (simpler)
        user = User(
            email=email,
            password=password,
            fs_uniquifier=email  # Just use email as unique identifier
        )
        user.roles.append(role)

        db.session.add(user)
        db.session.commit()

        flash('Användare har skaptas!', 'success')
        return redirect(url_for('manage_users'))  

    return render_template('adminwork/create_user.html')




# Route for bank statistics
@app.route('/adminwork/bank_statistics', methods=['GET'])
def bank_statistics():
    stat_type = request.args.get('stat_type', 'overview')  # Default to 'overview'

    # Overview Statistics (Total Customers, Accounts, Balance)
    if stat_type == 'overview':
        total_customers = Customer.query.count()  # Total unique customers
        total_accounts = Account.query.count()  # Total accounts
        total_balance = db.session.query(db.func.sum(Account.balance)).scalar()  # Summing all account balances

        return render_template('adminwork/bank_statistics.html', 
                               stat_type=stat_type, 
                               total_customers=total_customers,
                               total_accounts=total_accounts, 
                               total_balance=total_balance)

    # Country-specific Statistics
    elif stat_type == 'country':
        # Use DISTINCT to count unique customers in each country
        country_stats = db.session.query(
            Customer.country,
            db.func.count(db.distinct(Customer.id)).label('total_customers'),  # Count unique customers
            db.func.count(Account.id).label('total_accounts'),  # Count all accounts
            db.func.sum(Account.balance).label('total_balance')  # Sum of all account balances
        ).join(Account).group_by(Customer.country).all()

        return render_template('adminwork/bank_statistics.html', 
                               stat_type=stat_type, 
                               country_stats=country_stats)

    return render_template('adminwork/bank_statistics.html', stat_type=stat_type)



@app.route('/top_customers/<country>')
def top_customers(country):
    # Get the top 10 customers in the country by total balance
    top_customers = db.session.query(
        Customer.given_name,
        db.func.sum(Account.balance).label('total_balance'),
        db.func.count(Account.id).label('num_accounts')
    ).join(Account).filter(Customer.country == country).group_by(Customer.id).order_by(db.func.sum(Account.balance).desc()).limit(10).all()

    return render_template('top_customers.html', country=country, top_customers=top_customers)



#Route for fradulent activity
@app.route('/adminwork/fraud_detection')
def fraud_detection():
    return render_template('adminwork/fraud_detection.html')





if __name__  == "__main__":
    with app.app_context():
        upgrade()
        seedData(db)
    app.run(debug=True)