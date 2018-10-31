from wtforms import Form, BooleanField, TextField, PasswordField, validators, widgets
from wtforms.fields import simple, html5

class LoginForm(Form):
    username = simple.StringField(label = 'User',
                                  validators = [
                                      validators.data_required(message = '用户名必填'),
                                  ],
                                  widget = widgets.TextInput(),
                                  render_kw = {'class':'form-control',"placeholder":"请输入账号"}
                                  )
    password = simple.PasswordField(
        label = '密码',
        validators = [
            validators.data_required(message = '密码不能为空'),
        ],
        widget = widgets.PasswordInput(),
        render_kw = {'class':'form-control', "placeholder":"请输入密码"}
    )