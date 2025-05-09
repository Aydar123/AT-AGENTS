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
from werkzeug.utils import secure_filename
import xmltodict
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
load_dotenv()

AGENTS = json.load(open(os.getenv('AGENTS')))
# KB_XML_FILE_PATH = os.getenv('KB_XML_FILE_PATH')
RAO_XML_FILE_PATH = os.getenv('RAO_XML_FILE_PATH')
RAO_PROGON_XML_FILE_PATH = os.getenv('RESOURCE_PARAMETERS_PATH')
SELECTED_RULES_FILE = os.getenv('SELECTED_RULES_FILE')
PLANNING_BASE_PATH = os.getenv('PLANNING_BASE_PATH')

UPLOAD_FOLDER_KB = os.getenv('UPLOAD_FOLDER_KB')
UPLOAD_FOLDER_AT_SIM_SUB = os.getenv('UPLOAD_FOLDER_AT_SIM_SUB')
UPLOAD_FOLDER_PB = os.getenv('UPLOAD_FOLDER_PB')
EXP_FOLDER_PATH = os.getenv('EXP_FOLDER_PATH')
EXP_SELECTED_FILE_PATH = os.getenv('EXP_SELECTED_FILE_PATH')

tasks = {
    "create_knowledge_base": {"checked": False},
    "create_environment": {"checked": False},
    "create_plan_base": {"checked": False},
}

logger = logging.getLogger(__name__)

CONFIG_YAML = os.getenv('CONFIG_YAML')
with open(CONFIG_YAML, "r") as config_file:
    config = yaml.safe_load(config_file)
connection_url = config["connection"]["url"]

app = Flask(__name__)
# Знаю, что лучше такой "секрет" хранить в .env, но в рамках прототипа и установки для "коллег" оставлю так...
app.secret_key = "NO_SECRET_KEY"
app.config['UPLOAD_FOLDER_KB'] = UPLOAD_FOLDER_KB
app.config['UPLOAD_FOLDER_AT_SIM_SUB'] = UPLOAD_FOLDER_AT_SIM_SUB
app.config['UPLOAD_FOLDER_PB'] = UPLOAD_FOLDER_PB


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
        # Инициализируем базу планов
        planning_base = {'HLA': [], 'steps': [], 'precond': [], 'effect': []}

        # Получаем HLA переменные
        hla_var1 = request.form.getlist('hla_var1[]')  # Начальные состояния HLA
        hla_var2 = request.form.getlist('hla_var2[]')  # Конечные состояния HLA

        if not hla_var1 or not hla_var2:
            return jsonify({'error': 'Должны быть заполнены все поля HLA.'}), 400

        # Создаем список HLA-операций
        hla_actions = [f"Go({start}, {end})" for start, end in zip(hla_var1, hla_var2)]

        # Обрабатываем шаги для каждой HLA-операции
        steps = []
        for i, hla_action in enumerate(hla_actions):
            # Получаем шаги для текущей HLA
            step_vars = request.form.getlist(f"step_vars[{i + 1}][]")  # Список шагов
            if len(step_vars) < 2:
                return jsonify({'error': f'Для refinements {i + 1} должно быть как минимум два шага.'}), 400

            # Формируем шаги Driver(StepN, StepN+1)
            formatted_steps = [
                f"Driver({step_vars[j]}, {step_vars[j + 1]})"
                for j in range(len(step_vars) - 1)
            ]
            steps.append(formatted_steps)

            # Обновляем planning_base для текущей HLA
            create_planning_base(planning_base, hla_action, formatted_steps)

        # Сохраняем обновленный planning_base
        with open(PLANNING_BASE_PATH, 'w') as f:
            json.dump(planning_base, f, indent=2)

        return render_template('base_results.html', planning_base=planning_base)

    except Exception as e:
        print(f"Error in add_hla: {e}")
        return jsonify({'error': f'Ошибка при обработке запроса: {str(e)}'}), 500


# @app.route("/get/rules", methods=["GET"])
# def get_rules():
#     # Загружаем XML-файл
#     tree = ET.parse(KB_XML_FILE_PATH)
#     root = tree.getroot()
#
#     # Извлекаем правила из тега <rules>
#     rules = []
#     for rule in root.findall(".//rules/rule"):
#         rule_id = rule.get("id")
#         if rule_id:
#             rules.append(rule_id)
#
#     # Возвращаем JSON с правилами
#     return jsonify(rules)


# @app.route("/save/selected_rules", methods=["POST"])
# def save_selected_rules():
#     # Проверяем, что запрос содержит данные
#     if not request.json or 'selected_rules' not in request.json:
#         return jsonify({"error": "Данные отсутствуют или некорректны"}), 400
#
#     selected_rules_ids = request.json['selected_rules']  # Получаем список выбранных правил (id)
#
#     # Загружаем XML-файл
#     if not os.path.exists(KB_XML_FILE_PATH):
#         return jsonify({"error": f"Файл {KB_XML_FILE_PATH} не найден"}), 500
#
#     tree = ET.parse(KB_XML_FILE_PATH)
#     root = tree.getroot()
#
#     # Создаём структуру для выбранных правил
#     selected_rules_data = {}
#
#     for rule_id in selected_rules_ids:
#         rule = root.find(f".//rules/rule[@id='{rule_id}']")
#         if rule is not None:
#             # Конвертируем XML в словарь
#             rule_dict = xmltodict.parse(ET.tostring(rule, encoding="unicode"))
#             rule_dict = rule_dict.get("rule", {})  # Извлекаем содержимое тега <rule>
#
#             # Добавляем id как ключ
#             selected_rules_data[rule_id] = rule_dict
#
#     try:
#         with open(SELECTED_RULES_FILE, "w", encoding="utf-8") as json_file:
#             json.dump(selected_rules_data, json_file, ensure_ascii=False, indent=2)
#     except Exception as e:
#         return jsonify({"error": f"Не удалось сохранить файл: {str(e)}"}), 500
#
#     return jsonify({"message": "Выбранные правила успешно сохранены", "data": selected_rules_data}), 200


@app.route('/upload/kb', methods=['POST'])
def upload_kb_file():
    if 'file' not in request.files:
        return jsonify({"message": "Файл не найден"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Файл не выбран"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER_KB'], filename)
        file.save(filepath)

        # Обновление статуса задачи
        tasks["create_knowledge_base"]["checked"] = True
        return jsonify({"message": "Файл успешно загружен", "task": "create_knowledge_base"}), 200


@app.route('/upload/at/simulation/subsystem', methods=['POST'])
def upload_at_sim_subsystem_file():
    if 'file' not in request.files:
        return jsonify({"message": "Файл не найден"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Файл не выбран"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER_AT_SIM_SUB'], filename)
        file.save(filepath)

        # Обновление статуса задачи
        tasks["create_environment"]["checked"] = True
        return jsonify({"message": "Файл успешно загружен", "task": "create_environment"}), 200


@app.route('/upload/plan/base', methods=['POST'])
def upload_plan_base_file():
    if 'file' not in request.files:
        return jsonify({"message": "Файл не найден"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Файл не выбран"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER_PB'], filename)
        file.save(filepath)

        # Обновление статуса задачи
        tasks["create_plan_base"]["checked"] = True
        return jsonify({"message": "Файл успешно загружен", "task": "create_plan_base"}), 200


@app.route('/rao/view')
def display_resources():
    # Парсинг XML
    resources, actions, operations = rao_parse_xml(RAO_XML_FILE_PATH)

    # Рендеринг HTML
    return render_template('rao_view.html', resources=resources, actions=actions, operations=operations)


@app.route('/rao/view/progon')
def resources_view():
    resources = rao_progon_xml_parse(RAO_PROGON_XML_FILE_PATH)
    return render_template('rao_view_progon.html', resources=resources)


@app.route('/state/space', methods=['GET'])
def get_state_spaces():
    return render_template('create_state_space.html')


STATE_SPACES_FILE = os.path.join(UPLOAD_FOLDER_PB, "state_spaces.json")
def load_state_spaces():
    """Загружает сохраненные пространства состояний из файла, если он существует."""
    if os.path.exists(STATE_SPACES_FILE):
        with open(STATE_SPACES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


EXP_FILE = os.path.join(EXP_FOLDER_PATH, "exp.json")
def load_experiments():
    """Загружает заданные эксперименты из файла, если он существует."""
    if os.path.exists(EXP_FILE):
        with open(EXP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.route('/save_state_spaces', methods=['POST'])
def save_state_spaces():
    """Сохраняет пространства состояний."""
    try:
        state_spaces = request.get_json()
        if not state_spaces:
            return jsonify({"message": "Нет данных в запросе"}), 400

        with open(STATE_SPACES_FILE, "w", encoding="utf-8") as f:
            json.dump(state_spaces, f, ensure_ascii=False, indent=4)

        return jsonify({"message": "State spaces сохранены", "filename": STATE_SPACES_FILE}), 200

    except Exception as e:
        return jsonify({"message": f"Ошибка: {str(e)}"}), 500


@app.route('/get_list_state_spaces', methods=['GET'])
def get_list_state_spaces():
    """Возвращает сохраненные пространства состояний."""
    try:
        state_spaces = load_state_spaces()
        return jsonify({"state_spaces": state_spaces}), 200

    except Exception as e:
        return jsonify({"message": f"Ошибка: {str(e)}"}), 500


@app.route('/get_experiments', methods=['GET'])
def get_list_experiments():
    """Возвращает сохраненные эксперименты в формате: {name: description}"""
    try:
        experiments = load_experiments()
        return jsonify(experiments), 200
    except Exception as e:
        return jsonify({"message": f"Ошибка: {str(e)}"}), 500


@app.route('/delete_state_space', methods=['POST'])
def delete_state_space():
    """Удаляет выбранное пространство состояний по индексу."""
    try:
        data = request.get_json()
        index = data.get("index")
        if index is None:
            return jsonify({"message": "Индекс не передан"}), 400

        state_spaces = load_state_spaces()
        if 0 <= index < len(state_spaces):
            deleted = state_spaces.pop(index)
            with open(STATE_SPACES_FILE, "w", encoding="utf-8") as f:
                json.dump(state_spaces, f, ensure_ascii=False, indent=4)
            return jsonify({"message": f"Удалено пространство: {deleted['name']}"}), 200
        else:
            return jsonify({"message": "Недопустимый индекс"}), 400

    except Exception as e:
        return jsonify({"message": f"Ошибка: {str(e)}"}), 500


@app.route('/save_selected_experiments', methods=['POST'])
def save_selected_experiments():
    selected = request.json.get("selected", [])
    with open(EXP_SELECTED_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)
    return jsonify({"message": "Сохранено успешно."})


@app.route('/get_selected_experiments', methods=['GET'])
def get_selected_experiments():
    if os.path.exists(EXP_SELECTED_FILE_PATH):
        with open(EXP_SELECTED_FILE_PATH, "r", encoding="utf-8") as f:
            selected = json.load(f)
        return jsonify({"selected": selected})
    return jsonify({"selected": []})


@app.route('/save_action_templates', methods=['POST'])
def save_action_templates():
    data = request.get_json()
    name = data.get("name")
    new_templates = data.get("action_templates")

    if not name or not isinstance(new_templates, list):
        return jsonify({"error": "Invalid input"}), 400

    # Загружаем текущее состояние
    if not os.path.exists(STATE_SPACES_FILE):
        return jsonify({"error": "state_spaces.json not found"}), 404

    with open(STATE_SPACES_FILE, 'r', encoding='utf-8') as f:
        spaces = json.load(f)

    # Ищем нужное пространство
    found = False
    for space in spaces:
        if space.get("name") == name:
            space["action_templates"] = new_templates
            found = True
            break

    if not found:
        return jsonify({"error": f"Space with name '{name}' not found"}), 404

    # Сохраняем изменения
    with open(STATE_SPACES_FILE, 'w', encoding='utf-8') as f:
        json.dump(spaces, f, ensure_ascii=False, indent=2)

    return jsonify({"message": f"Templates saved for space '{name}'."}), 200


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
    results_cache = await interaction_component.interact_many_times(agent=agent)
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
