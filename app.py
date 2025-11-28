from flask import Flask, render_template, request, redirect, url_for, flash , current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_mail import Message
from decimal import Decimal
from threading import Thread

import os

from extensions import db, login_manager, mail
from models import User, Expense, ExpenseParticipant, Notification

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@db:5432/{os.getenv('POSTGRES_DB')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('App_mail') 
app.config['MAIL_PASSWORD'] = os.getenv('App_pass') 
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('App_mail') 

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)
mail.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            return redirect(url_for('signup'))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome {user.username}, you logged in successfully", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You logged out successfully", "success")
    return redirect(url_for('home'))


@app.route("/")
def home():
    recent_expenses = []
    if current_user.is_authenticated:
        recent_expenses = Expense.query.order_by(Expense.id.desc()).limit(5).all()
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Prepare paid expenses (created by current user)
    paid_expenses = []
    for e in current_user.paid_expenses.order_by(Expense.created_at.desc()).all():
        participants_list = []
        num_participants = e.participants.count()
        split_amount = float(e.total_amount) / num_participants if num_participants else 0
        for p in e.participants:
            participants_list.append({
                "id": p.id,
                "username": p.user.username,
                "amount": float(p.amount),  
                "paid": p.paid
            })
        paid_expenses.append({
            "id": e.id,
            "title": e.title,
            "total_amount": float(e.total_amount),
            "currency": e.currency,
            "note": e.note,
            "participants": participants_list
        })

    # Prepare owes expenses (expenses where current_user is a participant)
    owes_expenses = []
    for p in current_user.participations.order_by(ExpenseParticipant.added_at.desc()).all():
        e = p.expense
        owes_expenses.append({
            "expense_id": e.id,
            "title": e.title,
            "amount": float(p.amount),
            "currency": e.currency,
            "payer": e.payer.username,
            "paid": p.paid,
            "note": e.note
        })

    # Calculate totals
    you_are_owed = sum(p['amount'] for e in paid_expenses for p in e['participants'] if not p['paid'])
    you_owe = sum(o['amount'] for o in owes_expenses if not o['paid'])

    unread = Notification.query.filter_by(user_id=current_user.id, read=False).order_by(Notification.created_at.asc()).all()
    for n in unread:
    
        flash(n.message, 'info')
        n.read = True
    if unread:
        db.session.commit()

    return render_template(
        'dashboard.html',
        paid_expenses=paid_expenses,
        owes_expenses=owes_expenses,
        you_are_owed=you_are_owed,
        you_owe=you_owe
    )


@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    all_users = User.query.filter(User.id != current_user.id).all()

    if request.method == 'POST':
        title = request.form['title']
        currency = request.form.get('currency', 'PKR')
        total_amount = Decimal(request.form['total_amount'])
        note = request.form.get('note', '')

        participants_ids = request.form.getlist('participants')

        expense = Expense(
            title=title,
            currency=currency,
            total_amount=total_amount,
            note=note,
            payer=current_user
        )
        db.session.add(expense)
        db.session.flush()  

        num_participants = len(participants_ids)
        if num_participants > 0:
            split_amount = total_amount / num_participants
            for user_id in participants_ids:
                participant = ExpenseParticipant(
                    user_id=int(user_id),
                    expense_id=expense.id,
                    amount=split_amount
                )
                db.session.add(participant)

        db.session.commit()
        flash("Expense added successfully!", "success")

        for uid in participants_ids:
            user=User.query.get(int(uid))

            msg=Message(
                subject=f"{title} added ",
                recipients=[user.email],
                body=f"Hi {user.username},\n\n"
                         f"You have been added to the expense '{title}' worth {total_amount} {currency}.\n"
                         f"Note: {note}\n\n"
                         f"Check your dashboard for details.")
            
            Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
        flash("email sent successfully to participants", "success")

        return redirect(url_for('dashboard'))

    return render_template('add_expense.html', users=all_users)


@app.route('/update_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def update_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.payer_id != current_user.id:
        flash("You are not allowed to update this expense.", "danger")
        return redirect(url_for('dashboard'))

    all_users = User.query.filter(User.id != current_user.id).all()

    if request.method == 'POST':
        expense.title = request.form['title']
        expense.currency = request.form['currency']
        expense.total_amount = Decimal(request.form['total_amount'])
        expense.note = request.form.get('note', '')

        participants_ids = request.form.getlist('participants')
        num_participants = len(participants_ids)
        split_amount = expense.total_amount / num_participants if num_participants else 0

        # Track existing participants
        existing_participants = {p.user_id: p for p in expense.participants}

        # Update or add participants
        for user_id in participants_ids:
            user_id = int(user_id)
            if user_id in existing_participants:
                existing_participants[user_id].amount = split_amount
            else:
                db.session.add(
                    ExpenseParticipant(
                        user_id=user_id,
                        expense_id=expense.id,
                        amount=split_amount,
                        paid=False
                    )
                )

        # Remove participants that are no longer selected
        for user_id, participant in existing_participants.items():
            if str(user_id) not in participants_ids:
                db.session.delete(participant)

        db.session.commit()
        flash("Expense updated successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('update_expense.html', expense=expense, users=all_users)



@app.route('/delete_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    if expense.payer_id != current_user.id:
        flash("You are not allowed to delete this expense.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        db.session.delete(expense)
        db.session.commit()
        flash("Expense deleted successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('delete_expense.html', expense=expense)


@app.route('/expense/<int:expense_id>/remind' , methods = ['POST'])
@login_required
def remind_participants(expense_id):
    expense=Expense.query.get_or_404(expense_id)

    if current_user.id != expense.payer_id:
        flash("you are not allowed to send notification")
        return redirect('dashboard')
    created=0
    for p in expense.participants:

        if p.user_id == expense.payer_id:
            continue
        msg = f"Reminder: please settle your share for '{expense.title}' — amount: {p.amount} {expense.currency}."
        notif = Notification(user_id=p.user_id, message=msg , read=False)
        db.session.add(notif)
        created += 1

    db.session.commit()
    flash(f"Reminder sent to {created} participant(s).", "success")
    return redirect(url_for('dashboard'))






@app.route('/expense/<int:expense_id>/pay', methods=['POST'])
@login_required
def mark_paid(expense_id):
    participant = ExpenseParticipant.query.filter_by(
        expense_id=expense_id, user_id=current_user.id
    ).first_or_404()

    participant.paid = True
    db.session.commit()
    flash("Marked as paid successfully", "success")
    return redirect(url_for('dashboard'))


with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)





# @app.route('/list_paid_expenses', methods=['GET'])
# @login_required
# def list_paid_expenses():
#     expenses = current_user.paid_expenses.all()
#     return render_template('list_expenses.html', expenses=expenses)



# @app.route('/list_participating_expenses', methods=['GET'])
# @login_required
# def list_participating_expenses():
#     participations = current_user.participations.all()
#     result = []
#     for p in participations:
#         e = p.expense
#         result.append({
#             "expense": e,
#             "amount_owed": p.amount,
#             "paid": p.paid
#         })
#     return render_template('list_participating.html', participations=result)

