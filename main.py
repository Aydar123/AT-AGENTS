import eventlet
eventlet.monkey_patch()

from flask import *
from data import *
import datetime
import subprocess
from flask_socketio import SocketIO
import time
import os

import logging

logger = logging.getLogger(__name__)

# from logic.main import pause_output


app = Flask(__name__)
app.secret_key = "SECRET_KEY"
socketio = SocketIO(app)

@app.route('/')
def main_root():
    return render_template('index.html')


@app.route('/create', methods=['GET', 'POST'])
def post_create_root():
    if request.method == 'POST':
        form = request.form
        mail = form.get('mail')
        password = form.get('password')

        status, res = create_new_user(mail, password)

        if status is True:
            session['login'] = mail
            return redirect('/list/agents')
        else:
            msg = {"text": res, "type": "danger"}
    else:
        msg = None
    return render_template('login.html', msg=msg, no_account=True)


@app.route('/login', methods=['GET', 'POST'])
def post_login_root():
    if request.method == 'POST':
        form = request.form
        mail = form.get('mail')
        password = form.get('password')

        status, res = check_user_login(mail, password)

        if status is True:
            session['login'] = mail
            return redirect('/list/agents')
        else:
            msg = {"text": res, "type": "danger"}
    else:
        msg = None
    return render_template('login.html', msg=msg, no_account=False)


@app.route('/list/agents')
def list_agents_root():
    if not session.get('login', False):
        msg = {"text": "Вы не вошли в аккаунт", "type": "warning"}
        return render_template('login.html', msg=msg, no_account=False)

    mail = session['login']
    status, res = get_user_agents_list(mail)

    if status is False:
        msg = {"text": res, "type": "warning"}
        return render_template('login.html', msg=msg, no_account=False)
    else:
        return render_template('list_agents.html', todo=res)


@app.route('/create/agent')
def agents_create_root():
    if not session.get('login', False):
        msg = {"text": "Вы не вошли в аккаунт", "type": "warning"}
        return render_template('login.html', msg=msg, no_account=False)

    now_date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    return render_template('create_agent.html', now_date=now_date)


@app.route('/create/agent', methods=['POST'])
def post_create_agents_root():
    form = request.form
    text = form.get('text')
    date = form.get('date')
    add_agent_name_for_user(session['login'], text, date)

    return redirect('/list/agents')


@app.route('/agent/update/<id>')
def update_agent_name_root(id):
    update_agent_name_status(session['login'], id)
    return redirect('/list/agents')


@app.route('/agent/delete/<id>')
def delete_agent_name_root(id):
    delete_agent_name(session['login'], id)
    return redirect('/list/agents')


@app.route('/todo')
def todo_root():
    if not session.get('login', False):
        msg = {"text": "Вы не вошли в аккаунт", "type": "warning"}
        return render_template('login.html', msg=msg, no_account=False)

    mail = session['login']
    status, res = get_user_todo(mail)

    if status is False:
        msg = {"text": res, "type": "warning"}
        return render_template('login.html', msg=msg, no_account=False)
    else:
        return render_template('todo.html', todo=res)


@app.route('/todoOutput')
def todo_output_root():
    if not session.get('login', False):
        msg = {"text": "Вы не вошли в аккаунт", "type": "warning"}
        return render_template('login.html', msg=msg, no_account=False)

    mail = session['login']
    status, res = get_user_todo(mail)

    if status is False:
        msg = {"text": res, "type": "warning"}
        return render_template('todo_output.html', msg=msg, no_account=False)
    else:
        return render_template('todo_output.html', todo=res)


@app.route('/input/experiment/param')
def input_experiment_param_root():
    if not session.get('login', False):
        msg = {"text": "Вы не вошли в аккаунт", "type": "warning"}
        return render_template('login.html', msg=msg, no_account=False)

    return render_template('input_experiment_param.html')


@app.route('/at/solver')
def index():
    return render_template('at_solver.html')


@socketio.on('run_script')
async def handle_run_script():
    try:
        # Запускаем скрипт и захватываем вывод построчно
        process = subprocess.Popen(['python3', './logic/main.py'], stdout=subprocess.PIPE, text=True)

        # Чтение вывода по одной строке и отправка данных на клиент

        logger.info('---------------ВЫВОД РЕЗУЛЬТАТОВ-----------------')
        # result = await interaction_component.interact_once()
        # for something in result ....
        for line in iter(process.stdout.readline, ''):
            output = line.strip()
            logger.info(output)
            socketio.emit('console_output', output)  # Отправляем на клиент
            time.sleep(0.1)  # Имитируем задержку для наглядности
        process.stdout.close()
    except Exception as e:
        socketio.emit('console_output', f"Ошибка: {str(e)}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists('/var/run/web_main/'):
        os.makedirs('/var/run/web_main/')

    with open('/var/run/web_main/pidfile.pid', 'w') as f:
        f.write(str(os.getpid()))

    socketio.run(app, debug=True, port=5050, host="0.0.0.0")
    # app.run(port="5050", debug=True)
