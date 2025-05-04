from at_queue.utils.decorators import component_method

from planning import *
from search import *
from at_queue.core.at_component import ATComponent
from at_queue.core.session import ConnectionParameters
import asyncio
import logging
import yaml
import json
import os
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

########################### Исходные данные для 1 эксперимента ###########################
initial='Инцидент(Стоит_на_газоне, Каширское_шоссе) & Инцидент(Не_проходит_оплата, Окская_ул) & Инцидент(Снегопад, Каширское_шоссе) & Инцидент(Уборка, Окская_ул) & Инцидент(Ремонт, Каширское_шоссе) & Свободна(Парковочные_службы_1) & Свободна(Городские_службы_1) & Свободна(Парковочные_службы_2) & Свободна(С4) & Автомобиль(Транспортное_средство_1) & Автомобиль(Транспортное_средство_2) & ПарковкаДоступна(Окская_ул) & ПарковкаДоступна(Каширское_шоссе)'
goals='Вызвана_служба(Парковочные_службы_2, Каширское_шоссе, Снегопад) & МашинаНаПарковке(Транспортное_средство_1, Парковка_1, Окская_ул) & МашинаНаПарковке(Транспортное_средство_2, Парковка_2, Каширское_шоссе)'
domain='ТипИнцидента(Стоит_на_газоне) & ТипИнцидента(Снегопад) & ТипИнцидента(Не_проходит_оплата) & ТипИнцидента(Уборка) & ТипИнцидента(Ремонт) & Локация(Окская_ул) & Локация(Каширское_шоссе) & Автомобиль(Транспортное_средство_1) & Автомобиль(Транспортное_средство_2) & Парковка(Парковка_1) & Парковка(Парковка_2) & Служба(Парковочные_службы_1) & Служба(Городские_службы_1) & Служба(Парковочные_службы_2) & Служба(С4)'

# initial='Инцидент(Стоит_на_газоне, Каширское_шоссе) & Инцидент(Не_проходит_оплата, Окская_ул) & Инцидент(Неправильная_парковка, Каширское_шоссе) & Инцидент(Уборка, Окская_ул) & Инцидент(Ремонт, Каширское_шоссе) & Свободна(Парковочные_службы_1) & Свободна(Городские_службы_1) & Свободна(Парковочные_службы_2) & Свободна(С4) & Автомобиль(Транспортное_средство_1) & Автомобиль(Транспортное_средство_2) & ПарковкаДоступна(Окская_ул) & ПарковкаДоступна(Каширское_шоссе)',
# goals='Вызвана_служба(Городские_службы_1, Каширское_шоссе, Ремонт) & Вызвана_служба(Парковочные_службы_1, Окская_ул, Не_проходит_оплата) & Вызвана_служба(Парковочные_службы_2, Каширское_шоссе, Неправильная_парковка) & МашинаНаПарковке(Транспортное_средство_1, Парковка_1, Окская_ул) & МашинаНаПарковке(Транспортное_средство_2, Парковка_2, Каширское_шоссе) & ПредупреждениеОтправлено(Транспортное_средство_2, Каширское_шоссе, Стоит_на_газоне)',
# domain='ТипИнцидента(Стоит_на_газоне) & ТипИнцидента(Неправильная_парковка) & ТипИнцидента(Не_проходит_оплата) & ТипИнцидента(Уборка) & ТипИнцидента(Ремонт) & Локация(Окская_ул) & Локация(Каширское_шоссе) & Автомобиль(Транспортное_средство_1) & Автомобиль(Транспортное_средство_2) & Парковка(Парковка_1) & Парковка(Парковка_2) & Служба(Парковочные_службы_1) & Служба(Городские_службы_1) & Служба(Парковочные_службы_2) & Служба(С4)',
# goal_mapping_dict = {
#     'Вызвать_парковочные_службы_из_за_неправильной_парковки': 'Вызвана_служба(Парковочные_службы_2, Каширское_шоссе, Неправильная_парковка)',
#     'Вызвать_парковочные_службы_для_устранения_неисправностей': 'Вызвана_служба(Парковочные_службы_1, Окская_ул, Не_проходит_оплата)',
#     'Вызвать_городские_службы': 'Вызвана_служба(Городские_службы_1, Каширское_шоссе, Ремонт)',
#     'Отправить_предупреждение': 'ПредупреждениеОтправлено(Транспортное_средство_1, Каширское_шоссе, Стоит_на_газоне)',
#     'Отправить_на_альтернативную_парковку': 'МашинаНаПарковке(Транспортное_средство_1, Парковка_1, Окская_ул)',
#     # 'Вызвать_парковочные_службы_для_уборки': 'Вызвана_служба(С1, Локация1, Пожар)',
#     # 'Вызов_ГС_из_за_прорыва_водопровода': 'Вызвана_служба(С1, Локация1, Пожар)'
# }

goal_mapping_dict = {
    'Вызвать_парковочные_службы_для_уборки_снега': 'Вызвана_служба(Парковочные_службы_2, Каширское_шоссе, Снегопад)',
    'Отправить_на_парковку': 'МашинаНаПарковке(Транспортное_средство_1, Парковка_1, Окская_ул)',
    'Отправить_на_альтернативную_парковку': 'МашинаНаПарковке(Транспортное_средство_2, Парковка_2, Каширское_шоссе)',
}


CONFIG_YAML = os.getenv('CONFIG_YAML')
PLANNING_BASE_PATH = os.getenv('PLANNING_BASE_PATH')
SELECTED_RULES_FILE = os.getenv('SELECTED_RULES_FILE')
STATE_SPACE_JSON = os.getenv('STATE_SPACE_JSON')

with open(CONFIG_YAML, "r") as config_file:
    config = yaml.safe_load(config_file)

connection_url = config["connection"]["url"]

class StateSpacePlanning(ATComponent):
    def __init__(self, connection_parameters: ConnectionParameters, *args, **kwargs):
        super().__init__(connection_parameters, *args, **kwargs)
        self._action_base = None
        self._goal_state_mapping = None


    @property
    def planning_base(self):
        with open(PLANNING_BASE_PATH) as f:
            return json.load(f)


    def generate_plan(self, init, go, act_temp, dom):
        # Создаем список объектов Action на основе шаблонов
        actions = []
        for template in act_temp:
            action_str = f"{template['name']}({', '.join(template['params'])})"
            action = Action(
                action_str,
                precond=template['precond'],
                effect=template['effect'],
                domain=template['domain']
            )
            actions.append(action)

        print(f"ACTIONS: {actions}")

        # Создаем общую задачу планирования с несколькими действиями
        planning_problem = PlanningProblem(
            initial=init,
            goals=go,
            actions=actions,
            domain=dom
        )

        result = astar_search(BackwardPlan(planning_problem), display=True).solution()
        plan = list(map(lambda action: Expr(action.name, *action.args), result))

        return str(plan[::-1])


    @component_method
    def mapping_at_goal_and_action(self, at_solver_goal):
        if at_solver_goal not in goal_mapping_dict:
            raise ValueError(f"Неизвестная цель: {at_solver_goal}")

        current_goal = goal_mapping_dict[at_solver_goal]
        logger.info(f'goal_str: {current_goal}')

        return current_goal


    @component_method
    def general_generated_plan(self):
        # 1. Загружаем action_templates из файла state_spaces.json
        with open(STATE_SPACE_JSON, "r", encoding="utf-8") as f:
            state_space_data = json.load(f)

        # 2. Предположим, что мы берём первый элемент (или можно фильтровать по нужному имени/типу эксперимента)
        action_templates_raw = state_space_data[0]["action_templates"]

        # 3. Приводим action_templates к нужному формату: исправим поля и уберем лишние кавычки
        action_templates = []
        for action in action_templates_raw:
            cleaned_action = {
                'name': action['name'],
                'params': [param.strip("'") for param in action['parameters']],
                'precond': action['preconditions'],
                'effect': action['effects'],
                'domain': action['domain']
            }
            action_templates.append(cleaned_action)

        # 4. Генерируем глобальный план (то есть план на основе всего пространства состояний)
        final_plan = self.generate_plan(
            initial,
            goals,
            action_templates,
            domain
        )

        logger.info(f'Generated Plan: {final_plan}')

        return final_plan


async def main():
    connection_parameters = ConnectionParameters(connection_url) # Параметры подключения к RabbitMQ
    at_planner = StateSpacePlanning(connection_parameters=connection_parameters) # Создание компонента
    await at_planner.initialize() # Подключение компонента к RabbitMQ
    await at_planner.register() # Отправка сообщения на регистрацию в брокер

    if not os.path.exists('/var/run/planner/'):
        os.makedirs('/var/run/planner/')

    with open('/var/run/planner/pidfile.pid', 'w') as f:
        f.write(str(os.getpid()))

    await at_planner.start() # Запуск компонента в режиме ожидания сообщений


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())