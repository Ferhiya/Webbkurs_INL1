import datetime
from flask_mail import Message
from app import app, db
from sqlalchemy import func
from datetime import timedelta
from dotenv import load_dotenv
from flask_mail import Mail
from models import Customer, Account, Transaction
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import datetime
from time import sleep
import os

load_dotenv()  # Load environment variables from .env file

# Mail configuration
app.config['MAIL_SERVER'] = 'localhost'
app.config['MAIL_PORT'] = 1025  # MailHog port
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = None
app.config['MAIL_PASSWORD'] = None
app.config['MAIL_DEFAULT_SENDER'] = 'no-reply@testbanken.se'


# Mail configuration (for sending emails)
mail = Mail(app)

# Rules for suspicious transactions
TRANSACTION_LIMIT = 15000  
TOTAL_TRANSACTION_LIMIT_72H = 23000  
CHECK_PERIOD = timedelta(days=3) 

def send_email(subject, body, recipients):
    """
    Send an email with a given subject, body, and list of recipients.
    """
    try:
        # Ensure recipients is a list of email addresses (strings)
        if isinstance(recipients, list) and all(isinstance(recipient, str) for recipient in recipients):
            with app.app_context():  # Push app context for mail functionality
                message = Message(subject, recipients=recipients)  # Create the email message
                message.body = body  # Set the body of the email
                mail.send(message)  # Send the email
                print(f"Sent email to {', '.join(recipients)}")  # Log the recipients
        else:
            raise ValueError("Recipients must be a list of email addresses.")
    except Exception as e:
        # Handle any errors during the email sending process
        print(f"Error sending email: {e}")


def check_suspicious_transactions():
    """
    Check suspicious transactions for each customer in every country.
    If any transaction exceeds the threshold or if the total amount of transactions
    over the past 72 hours exceeds the limit, it sends a report email for that country.
    """
    today = datetime.datetime.now()  # Get the current date and time

    # Push the app context manually to allow database operations and mail sending
    with app.app_context():
        # Loop through each country to process customers in that country
        for country in Customer.query.with_entities(Customer.country).distinct():
            country_name = country[0]  # Get country name from query result
            print(f"Checking transactions for country: {country_name}")

            # Fetch all customers from the specific country
            customers = Customer.query.filter_by(country=country_name).all()

            suspicious_report = []  # Initialize a list to store suspicious reports

            for customer in customers:
                print(f"Checking transactions for customer: {customer.given_name} {customer.surname}")

                # Fetch transactions for the last 3 days for the customer
                three_days_ago = today - CHECK_PERIOD
                transactions = Transaction.query.join(Account).filter(Account.customer_id == customer.id).filter(
                    Transaction.date >= three_days_ago
                ).all()

                total_transaction_amount = 0  # Variable to track the total amount in the last 72 hours
                suspicious_transactions = []  # List to store suspicious transactions

                for transaction in transactions:
                    # Check if any single transaction exceeds the threshold
                    if transaction.amount > TRANSACTION_LIMIT:
                        suspicious_transactions.append(f"Transaction ID {transaction.id} exceeds the limit: {transaction.amount} SEK")

                    # Add transaction amount to total to calculate the total over the last 72 hours
                    total_transaction_amount += transaction.amount

                # Check if the total amount in the last 72 hours exceeds the threshold
                if total_transaction_amount > TOTAL_TRANSACTION_LIMIT_72H:
                    suspicious_transactions.append(f"Total transactions in the last 72 hours exceeded the limit: {total_transaction_amount} SEK")

                if suspicious_transactions:
                    # Add the suspicious transactions report for the customer if any suspicious transactions were found
                    suspicious_report.append({
                        'customer_name': f"{customer.given_name} {customer.surname}",
                        'account_number': customer.id,  # Assuming the customer's ID represents the account number
                        'suspicious_transactions': suspicious_transactions
                    })

            # If any suspicious transactions were found for any customer in the country, prepare an email report
            if suspicious_report:
                report_body = "Suspicious Transactions Report:\n\n"
                for report in suspicious_report:
                    report_body += f"Customer: {report['customer_name']}, Account: {report['account_number']}\n"
                    for transaction in report['suspicious_transactions']:
                        report_body += f"  - {transaction}\n"
                    report_body += "\n"
                
                # Send the report via email to the respective country address
                send_email(
                    subject=f"Suspicious Transactions Report for {country_name}",
                    body=report_body,
                    recipients=[f"{country_name.lower()}@testbanken.se"]  # Send to the country-specific email address
                )
                print(f"Report sent to {country_name.lower()}@testbanken.se")


# Setup the scheduler using APScheduler to run the batch process every 24 hours
scheduler = BackgroundScheduler()
scheduler.add_job(check_suspicious_transactions, 'interval', hours=24)  # Schedule the task to run every 24 hours
scheduler.start()  # Start the scheduler to begin checking

try:
    # Keep the main thread running to allow the scheduler to run in the background
    while True:
        sleep(60)  # Wait for 60 seconds before checking again
except (KeyboardInterrupt, SystemExit):
    # Gracefully shutdown the scheduler when the script is interrupted (e.g., via Ctrl+C)
    scheduler.shutdown()

if __name__ == "__main__":
    check_suspicious_transactions()  # Run immediately if executed as the main program