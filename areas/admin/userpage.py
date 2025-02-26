from flask import render_template, request, redirect, url_for, flash, Blueprint
from models import db, Customer, Account, User, Role


userPageBluePrint = Blueprint('UserPage', __name__)


@userPageBluePrint.route('/manageUsers', methods=['GET', 'POST'])
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


@userPageBluePrint.route('/update_role/<int:user_id>', methods=['POST'])
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
    
    return redirect(url_for('UserPage.manage_users'))


@userPageBluePrint.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Användar har tagits bort!', 'success')
    return redirect(url_for('UserPage.manage_users'))

@userPageBluePrint.route('/adminwork/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role_name = request.form.get('role')

        # Check if role exists
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash('Roll hittas inte!', 'danger')
            return redirect(url_for('UserPage.manage_users'))

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
        return redirect(url_for('UserPage.manage_users'))  

    return render_template('adminwork/create_user.html')




# Route for bank statistics
@userPageBluePrint.route('/adminwork/bank_statistics', methods=['GET'])
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



@userPageBluePrint.route('/top_customers/<country>')
def top_customers(country):
    # Get the top 10 customers in the country by total balance
    top_customers = db.session.query(
        Customer.given_name,
        db.func.sum(Account.balance).label('total_balance'),
        db.func.count(Account.id).label('num_accounts')
    ).join(Account).filter(Customer.country == country).group_by(Customer.id).order_by(db.func.sum(Account.balance).desc()).limit(10).all()

    return render_template('top_customers.html', country=country, top_customers=top_customers)




