from extensions import db

class ExpenseParticipant(db.Model):
    __tablename__ = 'expense_participants'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    paid = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)
    added_at = db.Column(db.DateTime(), server_default=db.func.now())

    expense = db.relationship('Expense', back_populates='participants')
    user = db.relationship('User', back_populates='participations')

    __table_args__ = (db.UniqueConstraint('user_id', 'expense_id', name='uq_expense_user'),)
