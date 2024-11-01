import json
import uuid


data = []
try:
    with open('data/data.json', 'r') as file:
        data = json.loads(file.read())
except Exception as error:
    pass


def save_data():
    with open('data/data.json', 'w') as file:
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