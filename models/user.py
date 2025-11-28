from extensions import db
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False, unique=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime(), server_default=db.func.now())

    paid_expenses = db.relationship("Expense", back_populates="payer", lazy="dynamic")
    participations = db.relationship(
        "ExpenseParticipant", back_populates="user", lazy="dynamic"
    )
    notifications = db.relationship(
        "Notification",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
