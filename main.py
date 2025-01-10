from flask import *
from data import *
import datetime
import os
import yaml
import logging
import asyncio
from logic.main import InteractionComponent
from at_queue.core.session import ConnectionParameters
import argparse
import json
from asgiref.wsgi import WsgiToAsgi
from uvicorn import Config, Server
from typing import Optional

AGENTS = json.load(open('/package/src/agents_config/AGENTS.json'))

logger = logging.getLogger(__name__)

with open("/package/src/config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)
connection_url = config["connection"]["url"]

app = Flask(__name__)
app.secret_key = "SECRET_KEY"

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


@app.route('/editor', methods=['GET'])
def get_editors():
    return render_template('base_editor.html')


@app.route('/editor', methods=['POST'])
def add_hla():
    try:
        planning_base = {'HLA': [], 'steps': [], 'precond': [], 'effect': []}

        # Получаем HLA переменные
        hla_var1 = request.form.getlist('hla_var1[]')  # Список значений для переменной 1
        hla_var2 = request.form.getlist('hla_var2[]')  # Список значений для переменной 2

        # Собираем шаги
        steps = []
        for i in range(len(hla_var1)):  # Для каждого блока HLA
            step_var1 = request.form.getlist(f'step_var1_{i + 1}[]')  # Переменная шагов 1
            step_var2 = request.form.getlist(f'step_var2_{i + 1}[]')  # Переменная шагов 2
            steps.append({'step_var1': step_var1, 'step_var2': step_var2})

        # Проверяем заполненность данных
        if not hla_var1 or not hla_var2 or not steps:
            return jsonify({'error': 'Не все данные заполнены.'}), 400

        # Создаем список HLA-операций
        hla_actions = [f"Go({var1}, {var2})" for var1, var2 in zip(hla_var1, hla_var2)]

        # Обрабатываем шаги для каждой HLA-операции
        for i, hla_action in enumerate(hla_actions):
            # Формируем formatted_steps для текущего HLA
            step_group = steps[i]  # Берем шаги, соответствующие текущей HLA-операции
            formatted_steps = [
                f"Driver({var1}, {var2})"
                for var1, var2 in zip(step_group['step_var1'], step_group['step_var2'])
            ]

            create_planning_base(planning_base, hla_action, formatted_steps)

        # Сохраняем обновленный planning_base
        save_path = "/package/src/planning_base/planning_base.json"
        with open(save_path, 'w') as f:
            json.dump(planning_base, f, indent=2)

        return jsonify({'message': 'Planning base successful created', 'planning_base': planning_base}), 200

    except Exception as e:
        print(f"Error in add_hla: {e}")
        return jsonify({'error': f'Ошибка при обработке запроса: {str(e)}'}), 500


# --------------------------------------------------
# Глобальная переменная для хранения инициализированного компонента
interaction_component: Optional[InteractionComponent] = None
# component_initialized = False  # Флаг для проверки инициализации


@app.route('/api/results', methods=['GET'])
async def get_results():
    """
    Возвращает результаты работы interact_once.
    """
    global interaction_component
    if interaction_component is None:
        return jsonify({"error": "Results not yet available"}), 425
    if not interaction_component.registered:
        return jsonify({"error": "Results not yet registered"}), 425

    await interaction_component.configure_components(agents=AGENTS)  # Укажите ваших агентов
    logger.info('Component loaded agents')
    # Выполнение interact_once и сохранение результата
    agent = 'agent1'
    logger.info('Starting interaction component interact_once')
    results_cache = await interaction_component.interact_once(agent=agent)
    logger.info(results_cache)
    print(f"Results cache updated: {results_cache}")

    if results_cache:
        return jsonify(results_cache)
    return jsonify({"error": "Results not yet available"}), 404


parser = argparse.ArgumentParser(
                    prog='main_file',
                    description='Парсер хоста для корректной работы в сети докера',
                    epilog='См. реализацию парсера в файле main.py')

parser.add_argument('-H', '--host', help="Хост для работы в сети докера", required=False, default="localhost")


async def main():
    logger.info('Starting')
    args = parser.parse_args()
    # Получаем значение хоста
    host = args.host

    # Run the app with the custom loop
    config = Config(WsgiToAsgi(app), host=host, port=5050, log_level="info")
    server = Server(config)

    connection_parameters = ConnectionParameters(connection_url)
    global interaction_component
    interaction_component = InteractionComponent(connection_parameters=connection_parameters)

    await interaction_component.initialize()
    logger.info('Component initialized')
    await interaction_component.register()
    logger.info('Component registered')

    # Запуск в режиме ожидания сообщений, не блокируя выполнение
    loop = asyncio.get_event_loop()
    task = loop.create_task(interaction_component.start())
    logger.info('Component started')
    logger.info(f"Starting server at: {host}:5050")
    await server.serve()
    await task


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists('/var/run/web_main/'):
        os.makedirs('/var/run/web_main/')

    with open('/var/run/web_main/pidfile.pid', 'w') as f:
        f.write(str(os.getpid()))

    asyncio.run(main())
