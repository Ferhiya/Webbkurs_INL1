# Simple base for a webapp
This is a simple skeleton for a webapp that uses flask.

## Setup
### Create an isolated environment
```bash
# Create a virtual environment
python -m venv venv

# For macOS/Linux, activate environment:
source venv/bin/activate

# For Windows, activate environment:
venv\Scripts\activate

# remember that powershell might not allow you to run scripts. You have to use CMD instead then
```
### Install requirements
```bash
# Install dependencies
pip install -r requirements.txt
```

### Database
In app.py you find 
```python
app.config['SQLALCHEMY_DATABASE_URI']
```
Use the current configuration by creating a database "Bank" och change to your own preference.

To change the number of customers that seeds to the database, change variables in models.py
```python
MAX_NR_OF_CUSTOMERS = 50
MAX_NR_OF_ACCOUNTS = 4
MINIMUM_NR_OF_ACCOUNTS = 1
MAX_NR_OF_TRANSACTIONS = 30
MINIMUM_NR_OF_TRANSACTIONS = 3
```

### Migrations
To test that migrations works fine, run:
```bash
flask db upgrade
```

In case of problems, delete the migrations-map and run
```bash
flask db init

flask db migrations -m "First migration"

flask db upgrade
```

## To run the app
```bash
py app.py

# Alternative 
flask run
# remember that this will not execute the seed-function!
```

