from flask import Flask, request, Blueprint
from flask_security import login_required, roles_required
from models import Customer, Account,Transaction 
from flask import jsonify


mobileBluePrint = Blueprint('mobile', __name__)


@mobileBluePrint .route('/api/<int:customer_id>', methods=['GET'])
@login_required
@roles_required("Cashier")
def get_customer(customer_id):
    # Hämta kund från databasen
    customer = Customer.query.filter_by(id=customer_id).first()

    # Om kunden inte hittas, returnera ett felmeddelande
    if not customer:
        return jsonify({"error": "Kunden hittades inte"}), 404

    # Konvertera kunddata till JSON-format
    customer_data = {
        "customer_id": customer.id,
        "given_name": customer.given_name,
        "surname": customer.surname,
        "address": customer.streetaddress,
        "city": customer.city,
        "zipcode": customer.zipcode,
        "country": customer.country,
        "email": customer.email_address,
        "phone": customer.telephone,
        "accounts": [{"id": acc.id, "balance": acc.balance} for acc in customer.accounts]  # Listar alla kundens konton
    }

    return jsonify(customer_data)


@mobileBluePrint.route('/api/accounts/<int:account_id>', methods=['GET'])
@login_required
@roles_required("Cashier")
def get_account_transactions(account_id):
    # Hämta parametervärden från URL (default: limit=20, offset=0)
    limit = request.args.get('limit', default=20, type=int)
    offset = request.args.get('offset', default=0, type=int)

    # Hämta kontot
    account = Account.query.filter_by(id=account_id).first()

    # Kontrollera om kontot existerar
    if not account:
        return jsonify({"error": "Konto hittades inte"}), 404

    # Hämta transaktioner med limit och offset
    transactions = Transaction.query.filter_by(account_id=account_id)\
        .order_by(Transaction.date.desc())\
        .offset(offset).limit(limit).all()

    # Konvertera transaktionerna till JSON
    transaction_data = [
        {
            "transaction_id": t.id,
            "type": t.type.value,
            "amount": t.amount,
            "date": t.date.strftime('%Y-%m-%d %H:%M')
        }
        for t in transactions
    ]

    return jsonify(transaction_data)

