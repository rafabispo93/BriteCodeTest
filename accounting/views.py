# You will probably need more methods from flask but this one is a good start.
from flask import render_template, request

# Import things from Flask that we need.
from accounting import app, db

from accounting.utils import *

# Import our models
from models import Contact, Invoice, Policy

# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')

@app.route("/policy", methods=['POST'])
def get_policy():
    try:

        policy_id = request.form['id']
        date_list = request.form['date'].split("-")
        if date_list and policy_id:
            date_ = date(int(date_list[0]), int(date_list[1]), int(date_list[2]))

            policy = Policy.query.filter_by(id=policy_id).first()
            
            if not policy:
                return render_template('index.html', data={'error': 'Policy not found'})

            invoices = Invoice.query.filter_by(policy_id=policy_id).all()
            pa = PolicyAccounting(policy.id)

            balance = pa.return_account_balance(date_)

            return render_template('index.html', data={'invoices': invoices, 'balance': balance, 'policy': policy})
        else:
            return render_template('index.html', data={'error': 'Policy number or date empty'})

    except Exception as error:
        print(error)
        return render_template('index.html', data={'error': 'Internal Server error'})
