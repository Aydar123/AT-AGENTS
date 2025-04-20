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

########################### Исходные данные для 1 эксперимента ###########################
initial='Инцидент(Снегопад, ул_Толстого_2) & Свободна(С1) & Автомобиль(ТС1) & Автомобиль(ТС2) & ПарковкаДоступна(ул_Пушкина_1) & ПарковкаДоступна(ул_Толстого_2)'
goals='Вызвана_служба(С1, ул_Толстого_2, Снегопад) & МашинаНаПарковке(ТС1, Парковка1, ул_Пушкина_1) & МашинаНаПарковке(ТС2, Парковка2, ул_Толстого_2)'
domain='ТипИнцидента(Снегопад) & Локация(ул_Пушкина_1) & Локация(ул_Толстого_2) & Автомобиль(ТС1) & Автомобиль(ТС2) & Парковка(Парковка1) & Парковка(Парковка2) & Служба(С1)'

goal_mapping_dict = {
    'Вызвать_парковочные_службы_для_уборки_снега': 'Вызвана_служба(С1, ул_Толстого_2, Снегопад)',
    'Отправить_на_парковку': 'МашинаНаПарковке(ТС1, Парковка1, ул_Пушкина_1)',
    'Отправить_на_альтернативную_парковку': 'МашинаНаПарковке(ТС2, Парковка2, ул_Толстого_2)'
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
    def process_agent_goal(self, at_solver_goal):
        if at_solver_goal not in goal_mapping_dict:
            raise ValueError(f"Неизвестная цель: {at_solver_goal}")

        current_goal = goal_mapping_dict[at_solver_goal]
        print(f'goal_str: {current_goal}')

        with open(STATE_SPACE_JSON, "r", encoding="utf-8") as f:
            state_space_data = json.load(f)

        action_templates_raw = state_space_data[0]["action_templates"]

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

        print(f"Цель: {at_solver_goal} => {current_goal}")

        final_plan = self.generate_plan(
            initial,
            current_goal,
            action_templates,
            domain
        )

        print(f"Generated Plan: {final_plan}")

        return final_plan


    @component_method
    def simple_process_agent_goal(self):
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

        final_plan = self.generate_plan(
            initial,
            goals,
            action_templates,
            domain
        )

        print(f'Generated Plan: {final_plan}')

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