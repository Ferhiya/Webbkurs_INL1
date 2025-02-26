from flask import  render_template, request, redirect, url_for, flash, Blueprint
from flask_security import  login_required, roles_required
from models import db, Customer, Account, Transaction, AccountType
from sqlalchemy import or_, func, String
import datetime
from datetime import datetime
from forms import AccountForm
from flask import jsonify


CustomerPageBluePrint = Blueprint('CustomerPage', __name__)

#search customer
@CustomerPageBluePrint.route("/cashierwork/customer", methods=["GET", "POST"])
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
@CustomerPageBluePrint.route("/cashierwork/view_account", methods=["GET"])
@login_required
@roles_required("Cashier")
def view_account():
    customer_id = request.args.get('customer_id', type=int)

    if not customer_id:
        flash("Kund-ID saknas!", "danger")
        return redirect(url_for("CustomerPage.cashier_page"))

    customer = Customer.query.get(customer_id)

    if not customer:
        flash("Kunden hittades inte!", "danger")
        return redirect(url_for("CustomerPage.cashier_page"))

    return render_template("cashierwork/view_account.html", customer=customer)


#transactions record/history for accounts
@CustomerPageBluePrint.route('/cashierwork/account_details/<int:account_id>')
@login_required
@roles_required("Cashier")
def account_details(account_id):
    # Fetch the account by its ID
    account = Account.query.filter_by(id=account_id).first()

    # Check if the account exists
    if account is None:
        # If no account is found
        flash("Konto hittades inte", "danger")
        return redirect(url_for('CustomerPage.account_details'))  

    # Fetch all transactions for this account and order them by date descending
    transactions = account.transactions  

    # Sort transactions by date in descending order manually
    transactions = sorted(transactions, key=lambda t: t.date, reverse=True)
    
    

    return render_template(
        'cashierwork/account_details.html', 
        account=account, 
        transactions=transactions
    )
    
@CustomerPageBluePrint.route('/cashierwork/account_transactions/<int:account_id>/<int:offset>', methods=['GET'])
@login_required
@roles_required("Cashier")
def load_more_transactions(account_id, offset):
    # Fetch additional transactions with limit and offset for pagination
    transactions = (
        Transaction.query.filter_by(account_id=account_id)
        .order_by(Transaction.date.desc())
        .offset(offset)
        .limit(20)
        .all()
    )

    # Convert transactions to JSON format
    transactions_data = [
        {
            "type": transaction.type.value,
            "amount": transaction.amount,
            "date": transaction.date.strftime('%Y-%m-%d %H:%M')
        }
        for transaction in transactions
    ]

    return jsonify(transactions_data)




#Edit customer   
@CustomerPageBluePrint.route('/cashierwork/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
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
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        # Validate that the length of the input fields doesn't exceed the maximum lengths defined in the model
        if len(customer.given_name) > 50 or len(customer.surname) > 50:
            flash('Namn och efter namn kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        if len(customer.streetaddress) > 50:
            flash('Adress kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        if len(customer.city) > 70:
            flash('Stad kan inte vara mer än 70 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        if len(customer.zipcode) > 15:
            flash('Postnummer kan inte vara mer än 15 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        if len(customer.country) > 60:
            flash('Land kan inte vara mer än 60 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        if len(customer.country_code) != 2:
            flash('Landskod kan inte kan inte vara mer än 2 kärkaterer.', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))




        if len(customer.telephone_country_code) > 10:
            flash('Telefonkod kan inte vara mer än 10 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        if len(customer.telephone) < 10 or len(customer.telephone) > 20:
            flash('Telefon kan inte vara mer än 10 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        if len(customer.email_address) > 50:
            flash('Email kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


        # Validate email format
        if not validate_email(customer.email_address):
            flash('Icke godkänd email format', 'danger')
            return redirect(url_for('CustomerPage.edit_customer', customer_id=customer.id))


       

        db.session.commit()
        flash('Kundinformation uppdaterad!', 'success')
        return redirect(url_for('CustomerPage.view_account', customer_id=customer.id))

    return render_template('cashierwork/edit_customer.html', customer=customer)


#search customer
@CustomerPageBluePrint.route("/cashierwork/search_customer_for_account", methods=["GET"])
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
@CustomerPageBluePrint.route("/cashierwork/create_account", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def create_account():
    customer_id = request.args.get('customer_id')
    customer = Customer.query.get(customer_id)
    if not customer:
        flash("Kunden hittades inte!", "danger")
        return redirect(url_for('CustomerPage.create_account'))

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
        return redirect(url_for('CustomerPage.search_customer_for_account'))  # Redirect to the cashier page or wherever you want

    return render_template("cashierwork/create_account.html", form=form, customer=customer)





#Create customer
@CustomerPageBluePrint.route("/cashierwork/create_customer", methods=["GET", "POST"])
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
            return redirect(url_for('CustomerPage.create_customer'))

        # Validate that the length of the input fields doesn't exceed the maximum lengths defined in the model
        if len(given_name) > 50 or len(surname) > 50:
            flash('Namn och efternamn kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(streetaddress) > 50:
            flash('Adress kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(city) > 70:
            flash('Stad kan inte vara mer än 70 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(zipcode) > 15:
            flash('Postnummer kan inte vara mer än 15 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(country) > 60:
            flash('Land kan inte vara mer än 60 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(country_code) != 2:
            flash('Landskod kan inte vara mer än 2 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(national_id) > 20:
            flash('personnummer kan inte vara mer än 20 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(telephone_country_code) > 10:
            flash('Telefonkod kan inte vara mer än 10 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(telephone) < 10 or len(telephone) > 15:
            flash('Telefon nummer måste vara 10 till 15 kärakerer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if len(email_address) > 50:
            flash('Email kan inte vara mer än 50 kärkaterer', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        # Validate email format
        if not validate_email(email_address):
            flash('Icke godkänd email format!', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        # Validate that the birthdate is not in the future
        birthday_date = datetime.strptime(birthday, '%Y-%m-%d')
        if birthday_date > datetime.now():
            flash('Födelsedag kan inte vara i framtid!', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        # Check if the email or national ID already exists
        customer_by_email = db.session.query(Customer).filter_by(email_address=email_address).first()
        customer_by_national_id = db.session.query(Customer).filter_by(national_id=national_id).first()

        if customer_by_email:
            flash('Email adress används redan.', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))

        if customer_by_national_id:
            flash('Personnummer används redan.', 'danger')
            return redirect(url_for('CustomerPage.create_customer'))


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

        return redirect(url_for('CustomerPage.create_customer'))

    # If it's a GET request, render the form
    return render_template("cashierwork/create_customer.html")


# Helper function to validate email format
def validate_email(email):
    import re
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None




@CustomerPageBluePrint.route('/delete_customer/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    # Kolla om kunden har konton
    if customer.accounts:  
        flash('Kan inte ta bort kund med activa konton!', 'danger')
        return redirect(url_for("CustomerPage.customer_page"))   # Ändra till rätt vy

    db.session.delete(customer)
    db.session.commit()
    flash('Kund har tagits bort!', 'success')
    return redirect(url_for("CustomerPage.customer_page"))  # Ändra till rätt vy

