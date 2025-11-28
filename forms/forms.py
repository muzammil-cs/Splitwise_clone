from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class RegistrationForm(FlaskForm):
    username = StringField(
        "username", validators=[DataRequired(), Length(min=3, max=20)]
    )
    email = StringField("email", validators=[DataRequired, Email])
    password = PasswordField("password", validators=[DataRequired, Length(min=8)])
    confirmPassword = PasswordField(
        "confirm Password", validators=[DataRequired, Length(min=8)]
    )
    submit = SubmitField("sign up")
