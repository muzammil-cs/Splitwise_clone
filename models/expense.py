from extensions import db

class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(), server_default=db.func.now())
    currency = db.Column(db.String(8), default='PKR', nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    note = db.Column(db.Text, nullable=True)

    payer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    payer = db.relationship('User', back_populates='paid_expenses')
    participants = db.relationship('ExpenseParticipant', back_populates='expense',
                                   cascade='all, delete-orphan', lazy='dynamic')
