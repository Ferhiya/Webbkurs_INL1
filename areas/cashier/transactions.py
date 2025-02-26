from flask import Flask, render_template, request, redirect, url_for, flash, Blueprint
from flask_security import login_required, roles_required
from models import db, Customer, Account, Transaction, TransactionOperation, TransactionType
from decimal import Decimal
import decimal
import datetime
from datetime import datetime

TransactionBluePrint = Blueprint('Transaction', __name__)


#Deposit money into account
@TransactionBluePrint.route("/cashierwork/deposit", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def deposit_page():
    selected_account = None

    # Handle deposit request
    if request.method == "POST":
        try:
            # Get account and amount from the form
            amount_str = request.form.get("amount", "0").strip()
            account_str = request.form.get("account_id", type=int)

            # Fetch the selected account by ID
            selected_account = Account.query.filter_by(id=account_str).first()

            if not selected_account:
                flash("Konto hittades inte!. Kontrollera kontonumret.", "danger")
                return redirect(url_for("Transaction.deposit_page"))

            # Validate the deposit amount
            try:
                amount = decimal.Decimal(amount_str)
            except:
                flash("Ogiltigt belopp, ange ett korrekt nummer.", "danger")
                return redirect(url_for("Transaction.deposit_page"))

            if amount <= 0:
                flash("Beloppet måste vara större än 0.", "danger")
                return redirect(url_for("Transaction.deposit_page"))

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
            return redirect(url_for("Transaction.deposit_page"))

        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            flash("Något gick fel. Försök igen. Fel: {e}", "danger")
            print(f"Error during deposit: {e}")  # Debugging output

    return render_template("cashierwork/deposit.html", selected_account=selected_account)




#withdraw money from account
@TransactionBluePrint.route("/cashierwork/withdraw", methods=["GET", "POST"])
@login_required
@roles_required("Cashier")
def withdraw_page():
    selected_account = None

    # Handle withdrawal request
    if request.method == "POST":
        try:
            # Get account and amount from the form
            amount_str = request.form.get("amount", "0").strip()
            account_str = request.form.get("account_id", type=int)

            # Fetch the selected account by ID
            selected_account = Account.query.filter_by(id=account_str).first()

            if not selected_account:
                flash("Konto hittades inte!. Kontrollera kontonumret.", "danger")
                return redirect(url_for("Transaction.withdraw_page"))

            # Validate the withdrawal amount
            try:
                amount = decimal.Decimal(amount_str)
            except:
                flash("Ogiltigt belopp, ange ett korrekt nummer.", "danger")
                return redirect(url_for("Transaction.withdraw_page"))

            if amount <= 0:
                flash("Beloppet måste vara större än 0.", "danger")
                return redirect(url_for("Transaction.withdraw_page"))

            # check that there's enough balance in the account
            if amount > selected_account.balance:
                flash("Otillräckligt saldo för uttag.", "danger")
                return redirect(url_for("Transaction.withdraw_page"))

            # Calculate new balance (subtract amount for withdrawal)
            new_balance = selected_account.balance - amount

            # Create a transaction record
            transaction = Transaction(
                type=TransactionType.DEBIT,  
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
            return redirect(url_for("Transaction.withdraw_page"))

        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            flash("Något gick fel. Försök igen.", "danger")
            print(f"Error during withdrawal: {e}")  # Debugging output

    return render_template("cashierwork/withdraw.html", selected_account=selected_account)

 
#transfer money between accounts and customers    
@TransactionBluePrint.route('/cashierwork/transfer', methods=['GET', 'POST'])
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
            return redirect(url_for("Transaction.transfer_page", from_account_id=from_account.id, to_account_id=to_account.id))

        else:
            flash("Fel: Otillräckligt saldo eller ogiltiga konton!", "danger")
            
# Rendera sidan med alla variabler för att visa sökresultat, valda konton 
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


