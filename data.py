import json
import uuid
import xml.etree.ElementTree as ET

data = []
try:
    with open('userdata/user_data.json', 'r') as file:
        data = json.loads(file.read())
except Exception as error:
    pass


def save_data():
    with open('userdata/user_data.json', 'w') as file:
        file.write(json.dumps(data, ensure_ascii=False))


# Для входа в аккаунт
def check_user_login(mail, password):
    for d in data:
        if d['mail'] == mail:
            if d['password'] == password:
                return True, "Успешная авторизация"
            return False, "Пароль неверный"
    return False, "Пользователь не найден"


# Для регистрации
def check_if_user_exist(mail):
    for d in data:
        if d['mail'] == mail:
            return True
    return False


def create_new_user(mail, password):
    if not check_if_user_exist(mail):
        data.append({
            "mail": mail,
            "password": password,
            "list": []
        })
        save_data()
        return True, "Успешная регистрация"
    else:
        return False, "Такой email уже есть"


def add_agent_name_for_user(mail, text, date):
    for d in data:
        if d['mail'] == mail:
            todo_id = str(uuid.uuid4())
            d['agents_list'].append({
                'id': str(todo_id),
                'text': text,
                'date': date,
                'checked': False
            })
            save_data()


def get_user_agents_list(mail):
    for d in data:
        if d['mail'] == mail:
            return True, d['agents_list']
    return False, "Ошибка при получении данных"


def get_user_todo(mail):
    for d in data:
        if d['mail'] == mail:
            return True, d['agents_list']
    return False, "Ошибка при получении данных"


def update_agent_name_status(mail, id):
    for d in data:
        if d['mail'] == mail:
            for l in d['agents_list']:
                if l['id'] == id:
                    l['checked'] = not l['checked']
                    save_data()


def delete_agent_name(mail, id):
    for d in data:
        if d['mail'] == mail:
            for l in d['agents_list']:
                if l['id'] == id:
                    d['agents_list'].remove(l)
                    save_data()


def generate_precond_effect(hla_action):
    if hla_action is None:
        raise ValueError("hla_action is None. Ensure it is correctly passed and initialized.")

    # Проверяем, что строка в правильном формате
    if not (hla_action.startswith("Go(") and hla_action.endswith(")")):
        raise ValueError(f"Invalid format for hla_action: {hla_action}. Expected format 'Go(param1, param2)'.")

    params = hla_action[3:-1].split(", ")
    if len(params) != 2:
        raise ValueError(f"Invalid number of parameters in hla_action: {hla_action}. Expected 2 parameters.")

    precond = f"At({params[0]})"
    effect = f"At({params[1]}) & ~At({params[0]})"

    return precond, effect


def create_planning_base(planning_base, hla_action, steps):
    if not isinstance(planning_base, dict):
        raise TypeError("planning_base must be a dictionary.")
    if hla_action is None:
        raise ValueError("hla_action cannot be None.")
    if not isinstance(steps, list):
        raise TypeError("steps must be a list.")

    # Генерируем предусловия и эффекты для HLA
    precond, effect = generate_precond_effect(hla_action)
    planning_base['HLA'].append(hla_action)
    planning_base['steps'].append(steps)
    planning_base['precond'].append([precond])
    planning_base['effect'].append([effect])

    # Обрабатываем шаги
    for step in steps:
        if not (step.startswith("Driver(") and step.endswith(")")):
            raise ValueError(f"Invalid format for step: {step}. Expected format 'Driver(param1, param2)'.")

        step_params = step[7:-1].split(", ")
        if len(step_params) != 2:
            raise ValueError(f"Invalid number of parameters in step: {step}. Expected 2 parameters.")

        step_precond = f"At({step_params[0]})"
        step_effect = f"At({step_params[1]}) & ~At({step_params[0]})"
        planning_base['HLA'].append(step)
        planning_base['precond'].append([step_precond])
        planning_base['effect'].append([step_effect])
        planning_base['steps'].append([])

    return planning_base

def rao_parse_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Извлечение ресурсов
    resources = []
    for resource_type in root.findall('Тип_ресурсов'):
        resource_name = resource_type.attrib.get('Имя_типа_ресурсов')
        resource_kind = resource_type.attrib.get('Вид_типа_ресурсов')
        params = []
        for param in resource_type.findall('Параметр_типа'):
            params.append({
                'name': param.attrib.get('Имя_параметра'),
                'type': param.attrib.get('Тип_параметра'),
                'default': param.attrib.get('Умолчание'),
            })
        resources.append({'name': resource_name, 'type': resource_kind, 'params': params})

    # Извлечение действий
    actions = [action.attrib.get('Имя_образца') for action in root.findall('Образец_операции')]

    # Извлечение операций
    operations = [operation.attrib.get('Имя_операции') for operation in root.findall('Операция')]

    return resources, actions, operations


def rao_progon_xml_parse(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    resources = []

    for resource in root.findall('Ресурс'):
        resource_data = {
            'Имя_ресурса': resource.get('Имя_ресурса'),
            'Имя_типа_ресурса': resource.get('Имя_типа_ресурса'),
            'Трассировка': resource.get('Трассировка'),
            'Номер_такта': resource.get('Номер_такта'),
            'Параметры': []
        }

        for param in resource.findall('Параметр_ресурса'):
            param_data = {
                'Имя_параметра': param.get('Имя_параметра'),
                'Значение': param.text
            }
            resource_data['Параметры'].append(param_data)

        resources.append(resource_data)

    return resources
