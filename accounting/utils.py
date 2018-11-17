#!/user/bin/env python2.7

import logging
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy

"""
#######################################################
This is the base code for the engineer project.
#######################################################
"""

class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):

        self.policy = Policy.query.filter_by(id=policy_id).one()

        logging.basicConfig(level=logging.INFO)

        if not self.policy.invoices:
            logging.info('Invoices not found, make the new invoices')
            self.make_invoices()

    """Returns the the current amount that certain account still have left to be paid starting from a specific Invoice

    Parameters
    ----------
    date_cursor : date
        The initial date to start counting the amount left to pay

    Returns
    -------
    due_now
        Amount left to be paid
    """
    def return_account_balance(self, date_cursor=None):

        logging.info('Calculating account balance')
        # In case a date is not passed the current date is used
        if not date_cursor:
            date_cursor = datetime.now().date()

        # Selects all the invoices from a policy that have to be paid
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        # For each invoice selected the due amount is added to the total amount
        for invoice in invoices:
            due_now += invoice.amount_due

        # Selects all the payments made to a specific policy
        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()

        # Decreses the amount already paid from the the total amount
        for payment in payments:
            due_now -= payment.amount_paid

        return due_now


    """Makes a new payment to a policy

    Parameters
    ----------
    contact_id : int
        The id of the Contact from the policy (The Agent and the person insured)
    date_cursor : date
        The date of the payment
    amount : float
        The amount of the payment

    Returns
    -------
    payment
        The payment made
    """
    def make_payment(self, contact_id=None, date_cursor=None, amount=0):

        # In case a date is not passed the current date is used
        if not date_cursor:
            date_cursor = datetime.now().date()

        # In case the contact id is not passed it uses the id referenced in the Policy table
        if not contact_id:
            try:

                if self.policy.named_insured:
                    contact_id = self.policy.named_insured
                else:
                    contact_id = self.policy.agent
            except:
                logging.info('No contact found during the payment')

        try:
            # Creates the payment object
            payment = Payment(self.policy.id,
                              contact_id,
                              amount,
                              date_cursor)
            db.session.add(payment)
            db.session.commit()

            logging.info('Payment made')
            return payment

        except Exception as error:

            db.session.rollback()
            logging.error(error)

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """
        logging.info('Evaluation cancellation due non pay')
        try:
            if not date_cursor:
                date_cursor = datetime.now().date()

            # Gets all invoices associate to a policy from the beginning to a desired date
            invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                    .filter(Invoice.due_date < date_cursor)\
                                    .filter(Invoice.cancel_date < date_cursor)\
                                    .order_by(Invoice.bill_date)\
                                    .all()
            if len(invoices) > 0:
                return True

            return False
        except Exception as error:
            logging.info(error)



    """Evaluates if a Policy should be or should not be canceled

    Parameters
    ----------
    date_cursor : date
        The date to be used as reference
    description: string
        The description about why the policy the policy cancelled
    force_cancel: boolean
        To cancel the policy for other motivation
    """
    def evaluate_cancel(self, description='No account Balance', date_cursor=None, force_cancel=False):

        logging.info('Evaluating policy')

        if not date_cursor:
            date_cursor = datetime.now().date()

        if force_cancel is False:
            # Gets all invoices associate to a policy from the beginning to a desired date
            invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                    .filter(Invoice.cancel_date <= date_cursor)\
                                    .order_by(Invoice.bill_date)\
                                    .all()

            # For each invoice is tested if it was paid before the cancel date
            for invoice in invoices:
                if not self.return_account_balance(invoice.cancel_date):
                    continue
                else:
                    self.policy.status = "Canceled"
                    self.policy.cancellation_date = date_cursor
                    self.policy.cancellation_description = description
                    db.session.add(self.policy)
                    db.session.commit()
                    logging.info('Policy should be canceled')
                    break
        else:
            self.policy.status = "Canceled"
            self.policy.cancellation_date = date_cursor
            self.policy.cancellation_description = description
            db.session.add(self.policy)
            db.session.commit()




    """Creates the invoices based on the total amount and the billing schedules
    """
    def make_invoices(self):
        for invoice in self.policy.invoices:
            invoice.deleted = 1

        # Set the types of billing schedules that can be created
        billing_schedules = {'Annual': None, 'Semi-Annual': 3, 'Quarterly': 4, 'Monthly': 12}

        invoices = []

        logging.info('making first invoice')
        # Creates the first invoice  that corresponds to the date of the policy's effectivation
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date, #bill_date
                                self.policy.effective_date + relativedelta(months=1), #due
                                self.policy.effective_date + relativedelta(months=1, days=14), #cancel
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        # The annual billing schedule just have 1 invoice, the first invoice.
        if self.policy.billing_schedule == "Annual":
            logging.info('making annual invoice')
            pass
        # The two-pay billing schedule creates 2 invoices, the first invoice and the second 6 months ahead
        elif self.policy.billing_schedule == "Two-Pay":

            logging.info('making Two-Pay invoices')
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i*6
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        # The Quarterly billing schedule creates 4 invoices, the first invoice and 3 more separating every invoice by 3 months
        elif self.policy.billing_schedule == "Quarterly":

            logging.info('making Quarterly invoices')
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i*3
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        # The Monthly billing schedule creates 12 invoices, the first invoice and 11. One invoice per month.
        elif self.policy.billing_schedule == "Monthly":

            logging.info('making Monthly invoices')
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)

            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):

                months_after_eff_date = i

                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))

                invoices.append(invoice)
        else:
            logging.warning('You have chosen a bad billing schedule.')
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()


    """Changes the billing schedule in the middle of a policy

    Parameters
    ----------
    new_method : string
        The new billing_schedule
    date_cursor: date
        The date to be used as reference

    Returns
    -------
        True is the operation was succesful and False if it wasn't
    """
    def change_policy_schedule(self, new_method, date_cursor=None):
        try:

            if not date_cursor:
                date_cursor = datetime.now().date()

            total_amount_left = self.return_account_balance(date_cursor)
            payments = Payment.query.filter_by(policy_id=self.policy.id).all()

            for payment in payments:
                db.session.delete(payment)

            self.policy.annual_premium = total_amount_left
            self.policy.billing_schedule = new_method
            db.session.add(self.policy)

            self.make_invoices()

            db.session.commit()
            return True

        except Exception as error:

            return False
            logging.info(error)


"""Creates a new policy

Parameters
----------
policy_number : string
    The name of the policy
effective_date : date
    the start date of the policy
billing_schedule: string
    the type of billing
agent: string
    The name of the agent
named_insured: string
    The name of the insured
annual_premium: float
    The value of the policy
"""
def new_policy(policy_number, effective_date, annual_premium, billing_schedule, agent=None, named_insured=None):

    try:

        # makes a new policy object
        new_policy = Policy(policy_number, effective_date, annual_premium)
        new_policy.billing_schedule = billing_schedule

        # check if a named_insured was passed, if it was passed get the reference object from the db
        if named_insured:
            named_insured_ = Contact.query.filter_by(name=named_insured, role="Named Insured").first()

            # if there is not a contact with this name a new one is created
            if not named_insured_:
                contact = Contact(named_insured, 'Named Insured')
                named_insured_ = contact
                db.session.add(contact)
                db.session.commit()
            named_insured = named_insured_.id

        # check if a agent was passed, if it was passed get the reference object from the db
        if agent:
            agent_ = Contact.query.filter_by(name=agent, role="Agent").first()

            # if there is not a contact with this name a new one is created
            if not agent_:
                contact = Contact(agent, 'Agent')
                agent_ = contact
                db.session.add(contact)
                db.session.commit()

            agent = agent_.id

        new_policy.named_insured = named_insured
        new_policy.agent = agent
        db.session.add(new_policy)
        db.session.commit()

    except Exception as error:
        logging.error(error)


"""Show a guide to make an action in the shell

Parameters
----------
action : string
    The name of the action
"""
def user_help(action=""):

    if 'payment' in action:
        print '''
            Follow the steps below:
                1- Create a Policy Accounting using this command: pa = PolicyAccounting(1) - The number inside the PolicyAccounting corresponds to the number of the policy to be paid.
                2- Use the follow command: pa.make_payment(contact_id=2, date_cursor=date(2015, 2, 1), amount=365)

                Ps: In case you do not know the contact_id, you can leave it blank
        '''

    else:
        print "Explanation for this action is not implemented yet. Please get in contact and We will be happy to help you out."

################################
# The functions below are for the db and
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()
